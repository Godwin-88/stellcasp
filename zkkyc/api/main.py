"""
FastAPI REST gateway — ZK-KYC Compliance Agent (zkkyc.api.main)

Spec reference: EP-04, F-04.1 / F-04.2

Known gaps NOT addressed in this pass (flagged, not silently dropped):
- `get_current_api_key` checks header *presence* only — it does not validate
  against a bcrypt hash in the `api_keys` table (US-04.1.1), because no DB
  session/pool is visible from this module. Anything is currently accepted
  as a valid key. Wire a real lookup before this goes anywhere near a judge
  or the public internet.
- `POST /api/v1/keys`, `POST /api/v1/keys/{key_id}/limit`,
  `GET /api/v1/entity/{id}/credential`, `GET /api/v1/casper/verdict/{hash}`,
  and `GET /api/v1/payments/summary` are not implemented — US-04.1.2 lists
  them, but they weren't in scope for this pass.
- Rate limit events are not written to `api_rate_events` (US-04.1.3) for the
  same DB-visibility reason as above.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import bcrypt
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..graph.entity import (
    BatchSizeExceededError,
    DuplicateSubmissionError,
    EntityCreate,
    EntityService,
    EntityServiceError,
    EntityValidationError,
    RelationshipCreate,
    ZeroValueTransactionError,
)
from ..graph.nrs import NRSEngine
from ..payments.x402 import PaymentVerificationError, X402PaymentService
from ..zk.proof import ProofGenerationError, generate_zk_proof, verify_proof_local

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_secret_header = APIKeyHeader(name="X-Admin-Secret", auto_error=False)


class ErrorResponse(BaseModel):
    error: str
    field: str | None = None


# --------------------------------------------------------------------------- #
# Rate limiting
#
# LIMITATION (unchanged from before, documented rather than silently kept):
# in-memory, per-process token bucket. Behind more than one API replica this
# only enforces a per-replica limit, not a global one. No Redis in this
# platform's stack currently — see entity.py's dedupe-cache note for the
# same caveat pattern.
# --------------------------------------------------------------------------- #

_rate_limit_buckets: dict[str, dict[str, float]] = {}


def check_rate_limit(api_key: str, settings: Settings) -> None:
    now = time.time()
    window = 60.0
    limit = float(settings.api_rate_limit_default)

    bucket = _rate_limit_buckets.get(api_key, {"tokens": limit, "last_update": now})
    tokens_to_add = (now - bucket["last_update"]) * (limit / window)
    bucket["tokens"] = min(limit, bucket["tokens"] + tokens_to_add)
    bucket["last_update"] = now

    if bucket["tokens"] < 1:
        _rate_limit_buckets[api_key] = bucket
        raise _RateLimitExceeded()

    bucket["tokens"] -= 1
    _rate_limit_buckets[api_key] = bucket


class _RateLimitExceeded(Exception):
    retry_after_seconds = 60


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #

def hash_api_key(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_api_key(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(plaintext.encode(), hashed.encode())


async def get_current_api_key(request: Request) -> str:
    """See module docstring: presence-only check today. Not real
    authentication until an `api_keys` lookup is wired in."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise _AuthError()
    return api_key


class _AuthError(Exception):
    pass


async def rate_limited_api_key(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> str:
    api_key = await get_current_api_key(request)
    try:
        check_rate_limit(api_key, settings)
    except _RateLimitExceeded as exc:
        raise exc
    return api_key


def add_security_headers(response: Response) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = get_settings()
    app.state.entity_service = EntityService()
    app.state.nrs_engine = NRSEngine(entity_service=app.state.entity_service)
    app.state.x402_service = X402PaymentService(settings=app.state.settings)

    # US-01.1.3 — idempotent, safe on every startup. Nothing was calling
    # this before, so the uniqueness constraint / composite index this
    # relies on never actually got created.
    await app.state.entity_service.ensure_schema()

    yield
    await app.state.entity_service.close()


def create_app() -> FastAPI:
    app = FastAPI(title="ZK-KYC Compliance Agent", version="0.1.0", lifespan=lifespan)

    # ------------------------------------------------------------------ #
    # Centralised exception -> HTTP mapping.
    #
    # entity.py's domain exceptions do NOT subclass ValueError, so the
    # previous per-route `except ValueError` blocks stopped catching
    # anything as soon as entity.py moved to its own exception hierarchy.
    # Handling this centrally also means new routes get correct status
    # codes for free instead of needing their own try/except.
    # ------------------------------------------------------------------ #

    @app.exception_handler(EntityValidationError)
    async def _handle_entity_validation(request: Request, exc: EntityValidationError):
        return JSONResponse(status_code=422, content={"error": exc.message, "field": exc.field})

    @app.exception_handler(DuplicateSubmissionError)
    async def _handle_duplicate(request: Request, exc: DuplicateSubmissionError):
        return JSONResponse(status_code=409, content={"error": str(exc)})

    @app.exception_handler(ZeroValueTransactionError)
    async def _handle_zero_value(request: Request, exc: ZeroValueTransactionError):
        # Message text is spec-mandated ("Zero-value transactions are not
        # indexed") and already exact on the exception itself.
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @app.exception_handler(BatchSizeExceededError)
    async def _handle_batch_size(request: Request, exc: BatchSizeExceededError):
        return JSONResponse(status_code=422, content={"error": str(exc)})

    @app.exception_handler(EntityServiceError)
    async def _handle_entity_generic(request: Request, exc: EntityServiceError):
        logger.exception("unhandled entity service error")
        return JSONResponse(status_code=500, content={"error": "internal graph service error"})

    @app.exception_handler(PaymentVerificationError)
    async def _handle_payment_error(request: Request, exc: PaymentVerificationError):
        content: dict[str, Any] = {"error": str(exc)}
        if exc.status_code == 202:
            content = {"status": "PAYMENT_PENDING", "detail": str(exc)}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(_AuthError)
    async def _handle_auth_error(request: Request, exc: _AuthError):
        return JSONResponse(status_code=401, content={"error": "Invalid or missing API key"})

    @app.exception_handler(_RateLimitExceeded)
    async def _handle_rate_limit(request: Request, exc: _RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "rate limit exceeded"},
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )

    @app.exception_handler(ProofGenerationError)
    async def _handle_proof_error(request: Request, exc: ProofGenerationError):
        return JSONResponse(status_code=500, content={"error": str(exc)})

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        add_security_headers(response)
        return response

    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/api/v1/graph/health")
    async def graph_health(request: Request):
        # US-01.1.3 — was defined on EntityService but never exposed.
        return (await request.app.state.entity_service.get_graph_health()).model_dump()

    @app.post("/api/v1/entity")
    async def create_entity_route(
        entity: EntityCreate,
        request: Request,
        response: Response,
        api_key: str = Depends(rate_limited_api_key),
    ):
        result = await request.app.state.entity_service.create_entity(entity)
        # 201 on creation, 200 on upsert (US-01.1.1) — previously hardcoded
        # to 201 in the route decorator regardless of outcome.
        response.status_code = 201 if result.created else 200
        return result.model_dump()

    @app.post("/api/v1/relationship", status_code=201)
    async def create_relationship_route(
        rel: RelationshipCreate,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        result = await request.app.state.entity_service.create_relationship(rel)
        return result.model_dump()

    @app.post("/api/v1/relationships/batch", status_code=201)
    async def create_relationships_batch_route(
        relationships: list[RelationshipCreate],
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        # entity_service already had a working batch method with nothing
        # routing to it — US-01.1.2 requires this endpoint to exist.
        count = await request.app.state.entity_service.create_relationships_batch(relationships)
        return {"created": count}

    @app.get("/api/v1/entity/{id}/relationships")
    async def get_relationships_route(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        return await request.app.state.entity_service.get_relationships(id)

    @app.get("/api/v1/entity/{id}/nrs")
    async def get_nrs_route(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-04.2.1 / US-04.2.2 — the spec's monetised endpoint. Previously
        this had no payment gate at all; anyone with any non-empty API key
        could call it for free."""
        x402_service: X402PaymentService = request.app.state.x402_service
        entity_service: EntityService = request.app.state.entity_service

        payment_proof_b64 = request.headers.get("X-Payment-Proof")
        if not payment_proof_b64:
            # Raw JSONResponse, not HTTPException, so the body matches the
            # spec's exact shape rather than being wrapped in {"detail": ...}.
            return JSONResponse(status_code=402, content=x402_service.create_payment_challenge())

        import base64

        try:
            deploy_hash = base64.b64decode(payment_proof_b64).decode()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "malformed X-Payment-Proof header"})

        entity_hash = entity_service.hash_entity_id(id)
        # Raises PaymentVerificationError / PaymentReplayError /
        # PaymentPendingError on failure — handled by the centralised
        # exception handler above.
        await x402_service.verify_payment(deploy_hash, entity_hash=entity_hash, api_key_id=api_key)

        nrs_details = await request.app.state.nrs_engine.compute_nrs(id)
        return nrs_details.model_dump()

    @app.post("/api/v1/prove/{id}")
    async def prove_compliance_route(
        id: str,
        request: Request,
        threshold: float = 0.75,
        chain: str = "stellar",
        api_key: str = Depends(rate_limited_api_key),
    ):
        entity_service: EntityService = request.app.state.entity_service
        entity_hash = entity_service.hash_entity_id(id)

        nrs_details = await request.app.state.nrs_engine.compute_nrs(id)
        proof = generate_zk_proof(nrs_details.raw_nrs, threshold)
        verified = verify_proof_local(proof["proof_hex"], proof["public_inputs"])
        return {
            # PII fix: was returning the raw `id` in the response body.
            "entity_hash": entity_hash,
            "nrs": nrs_details.raw_nrs,
            "proof_generated": True,
            "verified": verified,
            "chain_target": chain,
        }

    return app