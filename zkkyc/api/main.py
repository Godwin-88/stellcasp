"""
FastAPI REST gateway — ZK-KYC Compliance Agent (zkkyc.api.main)

Spec reference: EP-01 (F-01.1.3, F-01.2.3, F-01.3.x, F-01.4.x, F-01.5.x),
                 EP-02 (F-02.2.3), EP-03 (F-03.1.3, F-03.2.2),
                 EP-04 (F-04.1.1, F-04.1.3, F-04.2.3),
                 EP-05, EP-06, EP-07

Endpoints implemented in this module:
  GET  /health                                      — liveness probe
  GET  /api/v1/graph/health                        — Neo4j health (US-01.1.3)
  POST /api/v1/entity                              — create/upsert entity (US-01.1.1)
  POST /api/v1/relationship                        — create relationship (US-01.1.2)
  POST /api/v1/relationships/batch                 — batch relationships (US-01.1.2)
  GET  /api/v1/entity/{id}/relationships           — entity relationships (US-01.1.2)
  GET  /api/v1/entity/{id}/nrs                     — x402-gated NRS (US-04.2.1/2)
  POST /api/v1/prove/{id}                          — ZK proof generation (US-02.1.2)

  POST /api/v1/keys                                — admin: create API key (US-04.1.1)
  POST /api/v1/keys/{key_id}/limit                 — admin: update rate limit (US-04.1.3)
  GET  /api/v1/entity/{id}/credential              — compliance credential (US-02.2.3)
  GET  /api/v1/casper/verdict/{hash}               — Casper verdict proxy (US-03.1.3)
  GET  /api/v1/payments/summary                    — payment audit summary (US-04.2.3)
  GET  /api/v1/incidents                           — paginated incidents (US-01.3.1)
  GET  /api/v1/entity/{id}/anomalies               — structural anomalies (US-01.3.2)
  GET  /api/v1/entity/{id}/factors                 — six-factor breakdown (US-01.4.1)
  GET  /api/v1/entity/{id}/manifold                — manifold classification (US-01.5.2)
  POST /api/v1/admin/jurisdiction/refresh           — admin: refresh jurisdiction (US-01.4.3)
  GET  /api/v1/runs/{run_id}                       — LangGraph execution trace
  GET  /api/v1/audit/{entity_hash}                 — admin: full audit trail
  POST /api/v1/entity/{entity_hash}/disclose       — selective disclosure (US-03.2.2)
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import bcrypt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..db import get_db
from ..db.repos import (
    APIKeyRepository,
    CasperVerdictCacheRepository,
    CIComputationRepository,
    DisclosureAuditRepository,
    EntityMappingRepository,
    IncidentRepository,
    PaymentRepository,
    RiskFactorRepository,
    RunTraceRepository,
    VerificationRepository,
)
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
from ..graph.nrs import CIEngine, NRSEngine, refresh_jurisdiction_table
from ..payments.x402 import PaymentVerificationError, X402PaymentService
from ..zk.proof import ProofGenerationError, generate_zk_proof, verify_proof_local
from .schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyLimitUpdate,
    AuditResponse,
    CasperVerdictResponse,
    CredentialResponse,
    DiscloseRequest,
    DiscloseResponse,
    FactorResponse,
    IncidentListResponse,
    IncidentResponse,
    JurisdictionRefreshRequest,
    ManifoldResponse,
    PaymentSummaryDay,
    PaymentSummaryResponse,
    RunStateResponse,
)

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_secret_header = APIKeyHeader(name="X-Admin-Secret", auto_error=False)
disclosure_header = APIKeyHeader(name="X-Disclosure-Key", auto_error=False)


# --------------------------------------------------------------------------- #
# Error response
# --------------------------------------------------------------------------- #

class ErrorResponse(BaseModel):
    error: str
    field: str | None = None


# --------------------------------------------------------------------------- #
# Rate limiting
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


class _AuthError(Exception):
    pass


class _AdminError(Exception):
    pass


class _DisclosureAuthError(Exception):
    pass


async def get_current_api_key(request: Request) -> str:
    """US-04.1.1 — validate X-API-Key against api_keys table.

    Bootstrap mode: if the table is completely empty, any non-empty key is
    accepted so the first admin call to POST /api/v1/keys can succeed.
    Once at least one key exists, strict bcrypt validation applies.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise _AuthError()

    db = get_db()
    repo = APIKeyRepository(db)
    active_count = await repo.count_active()
    if active_count == 0:
        # First-key bootstrap: accept any non-empty value so the platform
        # is bootstrappable without pre-seeded credentials.
        return api_key

    key_hash = hash_api_key(api_key)
    record = await repo.get_by_hash(key_hash)
    if not record or not record["is_active"]:
        raise _AuthError()
    return api_key


async def get_admin_api_key(request: Request, settings: Settings = Depends(get_settings)) -> str:
    """Admin endpoint guard: requires both a valid API key and X-Admin-Secret."""
    api_key = await get_current_api_key(request)
    admin_secret = request.headers.get("X-Admin-Secret")
    if not admin_secret or admin_secret != settings.admin_secret:
        raise _AdminError()
    return api_key


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


# --------------------------------------------------------------------------- #
# Security headers
# --------------------------------------------------------------------------- #

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
    app.state.ci_engine = CIEngine(entity_service=app.state.entity_service)
    app.state.db = get_db()
    await app.state.db.connect()

    # US-01.1.3 — idempotent schema setup for Neo4j
    await app.state.entity_service.ensure_schema()

    yield

    await app.state.entity_service.close()
    await app.state.db.close()


# --------------------------------------------------------------------------- #
# App factory
# --------------------------------------------------------------------------- #

def create_app() -> FastAPI:
    app = FastAPI(title="ZK-KYC Compliance Agent", version="0.1.0", lifespan=lifespan)

    # ------------------------------------------------------------------ #
    # Centralised exception -> HTTP mapping.
    # ------------------------------------------------------------------ #

    @app.exception_handler(EntityValidationError)
    async def _handle_entity_validation(request: Request, exc: EntityValidationError):
        return JSONResponse(status_code=422, content={"error": exc.message, "field": exc.field})

    @app.exception_handler(DuplicateSubmissionError)
    async def _handle_duplicate(request: Request, exc: DuplicateSubmissionError):
        return JSONResponse(status_code=409, content={"error": str(exc)})

    @app.exception_handler(ZeroValueTransactionError)
    async def _handle_zero_value(request: Request, exc: ZeroValueTransactionError):
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

    @app.exception_handler(_AdminError)
    async def _handle_admin_error(request: Request, exc: _AdminError):
        return JSONResponse(status_code=403, content={"error": "Admin secret required"})

    @app.exception_handler(_DisclosureAuthError)
    async def _handle_disclosure_auth_error(request: Request, exc: _DisclosureAuthError):
        return JSONResponse(status_code=403, content={"error": "Disclosure API key required"})

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

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #

    @app.get("/health")
    async def health():
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    # ------------------------------------------------------------------ #
    # Graph (EP-01 F-01.1, F-01.2, F-01.3)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/graph/health")
    async def graph_health(request: Request, api_key: str = Depends(rate_limited_api_key)):
        """US-01.1.3"""
        return (await request.app.state.entity_service.get_graph_health()).model_dump()

    @app.post("/api/v1/entity")
    async def create_entity_route(
        entity: EntityCreate,
        request: Request,
        response: Response,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.1.1 — create or upsert entity node in Neo4j."""
        result = await request.app.state.entity_service.create_entity(entity)
        response.status_code = 201 if result.created else 200
        return result.model_dump()

    @app.post("/api/v1/relationship", status_code=201)
    async def create_relationship_route(
        rel: RelationshipCreate,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.1.2 — create single TRANSACTED_WITH relationship."""
        result = await request.app.state.entity_service.create_relationship(rel)
        return result.model_dump()

    @app.post("/api/v1/relationships/batch", status_code=201)
    async def create_relationships_batch_route(
        relationships: list[RelationshipCreate],
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.1.2 — bulk ingestion of up to 1,000 relationships."""
        count = await request.app.state.entity_service.create_relationships_batch(relationships)
        return {"created": count}

    @app.get("/api/v1/entity/{id}/relationships")
    async def get_relationships_route(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.1.2 — retrieve all TRANSACTED_WITH edges for an entity."""
        return await request.app.state.entity_service.get_relationships(id)

    # ------------------------------------------------------------------ #
    # NRS / x402 / ZK (EP-01 F-01.2, EP-04 F-04.2, EP-02 F-02.1)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/entity/{id}/nrs")
    async def get_nrs_route(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-04.2.1 / US-04.2.2 — x402 payment-gated NRS query."""
        x402_service: X402PaymentService = request.app.state.x402_service
        entity_service: EntityService = request.app.state.entity_service

        payment_proof_b64 = request.headers.get("X-Payment-Proof")
        if not payment_proof_b64:
            return JSONResponse(status_code=402, content=x402_service.create_payment_challenge())

        try:
            deploy_hash = base64.b64decode(payment_proof_b64).decode()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "malformed X-Payment-Proof header"})

        entity_hash = entity_service.hash_entity_id(id)
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
        """US-02.1.2 — generate Noir UltraHonk ZK compliance proof."""
        entity_service: EntityService = request.app.state.entity_service
        entity_hash = entity_service.hash_entity_id(id)

        nrs_details = await request.app.state.nrs_engine.compute_nrs(id)
        # FIX: await the async proof functions
        proof = await generate_zk_proof(nrs_details.raw_nrs, threshold)
        verified = await verify_proof_local(proof["proof_hex"], proof["public_inputs"])

        # Persist verification record for credential endpoint
        db = get_db()
        verif_repo = VerificationRepository(db)
        await verif_repo.create(
            entity_hash=entity_hash,
            stellar_tx_hash=None,
            proof_hex=proof["proof_hex"] if verified else None,
            threshold_public=threshold,
            status="VALID" if verified else "INVALID",
        )

        return {
            "entity_hash": entity_hash,
            "nrs": nrs_details.raw_nrs,
            "proof_generated": True,
            "verified": verified,
            "chain_target": chain,
        }

    # ------------------------------------------------------------------ #
    # Admin — API Key Management (US-04.1.1, US-04.1.3)
    # ------------------------------------------------------------------ #

    @app.post("/api/v1/keys", status_code=201, response_model=APIKeyCreateResponse)
    async def create_api_key(
        req: APIKeyCreateRequest,
        request: Request,
        api_key: str = Depends(get_admin_api_key),
    ):
        """US-04.1.1 — generate a new plaintext API key; only the bcrypt
        hash is stored. The plaintext key is returned exactly once."""
        key_id = str(uuid.uuid4())
        # 36-char UUID + 36-char UUID = 72-char key; sufficient entropy.
        plaintext = f"{secrets.token_hex(16)}-{secrets.token_hex(16)}"
        key_hash = hash_api_key(plaintext)

        db = get_db()
        repo = APIKeyRepository(db)
        await repo.create(key_id=key_id, key_hash=key_hash, name=req.name, rate_limit=req.rate_limit)

        return APIKeyCreateResponse(
            key_id=key_id,
            plaintext_key=plaintext,
            name=req.name,
            rate_limit=req.rate_limit,
            created_at=datetime.now(timezone.utc),
        )

    @app.post("/api/v1/keys/{key_id}/limit")
    async def update_key_limit(
        key_id: str,
        req: APIKeyLimitUpdate,
        request: Request,
        api_key: str = Depends(get_admin_api_key),
    ):
        """US-04.1.3 — update per-key rate limit (max 600 RPM)."""
        db = get_db()
        repo = APIKeyRepository(db)
        existing = await repo.get(key_id)
        if not existing:
            return JSONResponse(status_code=404, content={"error": "API key not found"})
        await repo.update_rate_limit(key_id, req.rate_limit)
        return {"key_id": key_id, "rate_limit": req.rate_limit}

    # ------------------------------------------------------------------ #
    # Compliance Credential (EP-02 F-02.2.3)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/entity/{id}/credential", response_model=CredentialResponse)
    async def get_credential(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-02.2.3 — return the latest compliance credential for an entity.
        Credentials older than 24 hours are marked EXPIRED."""
        entity_service: EntityService = request.app.state.entity_service
        entity_hash = entity_service.hash_entity_id(id)

        db = get_db()
        repo = VerificationRepository(db)
        verification = await repo.get_latest(entity_hash)

        if not verification:
            # Auto-generate credential if none exists
            nrs_details = await request.app.state.nrs_engine.compute_nrs(id)
            # FIX: await the async proof functions
            proof = await generate_zk_proof(nrs_details.raw_nrs, 0.75)
            verified = await verify_proof_local(proof["proof_hex"], proof["public_inputs"])
            await repo.create(
                entity_hash=entity_hash,
                stellar_tx_hash=None,
                proof_hex=proof["proof_hex"] if verified else None,
                threshold_public=0.75,
                status="VALID" if verified else "INVALID",
            )
            verification = await repo.get_latest(entity_hash)

        if not verification:
            return JSONResponse(status_code=404, content={"error": "No credential found for entity"})

        verified_at = datetime.fromisoformat(verification["verified_at"])
        age_hours = (datetime.now(timezone.utc) - verified_at).total_seconds() / 3600.0
        status = "VALID" if age_hours < 24 else "EXPIRED"

        if status == "EXPIRED":
            await repo.update_status(verification["id"], "EXPIRED")

        # Sign payload if platform signing key is configured
        proof_hex = verification.get("proof_hex")
        if proof_hex and app.state.settings.platform_signing_key:
            try:
                private_key = Ed25519PrivateKey.from_private_bytes(
                    bytes.fromhex(app.state.settings.platform_signing_key)
                )
                payload = f"{verification['entity_hash']}:{proof_hex}:{verification['verified_at']}:{status}"
                private_key.sign(payload.encode())
            except Exception:
                pass

        return CredentialResponse(
            stellar_tx_hash=verification.get("stellar_tx_hash"),
            entity_hash=verification["entity_hash"],
            threshold_public=verification["threshold_public"],
            verified_at=verified_at,
            proof_hex=proof_hex,
            status=status,
        )

    # ------------------------------------------------------------------ #
    # Casper Verdict Proxy (EP-04 F-03.1.3)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/casper/verdict/{hash}", response_model=CasperVerdictResponse)
    async def get_casper_verdict(
        hash: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-03.1.3 — REST proxy for Casper ComplianceOracle query,
        cached for 60 seconds."""
        db = get_db()
        repo = CasperVerdictCacheRepository(db)
        cached = await repo.get(hash)

        if cached:
            cached_at = cached["cached_at"]
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at)
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < 60:
                return CasperVerdictResponse(
                    verdict=bool(cached["verdict"]) if cached["verdict"] is not None else None,
                    expires_at=cached["expires_at"],
                    status=cached["status"],
                )

        # In a full implementation this would call CSPR.cloud or the
        # ComplianceOracle contract directly. For the demo we derive a
        # deterministic verdict from the hash so the endpoint is functional.
        verdict = hash.startswith("pass") or hash.startswith("valid")
        expires_at = int(time.time()) + 86400

        await repo.upsert(
            entity_hash=hash,
            verdict=verdict,
            expires_at=expires_at,
            status="VALID",
        )

        return CasperVerdictResponse(verdict=verdict, expires_at=expires_at, status="VALID")

    # ------------------------------------------------------------------ #
    # Payment Audit (EP-05 US-04.2.3)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/payments/summary", response_model=PaymentSummaryResponse)
    async def get_payments_summary(
        request: Request,
        days: int = 30,
        api_key: str = Depends(get_admin_api_key),
    ):
        """US-04.2.3 — total CSPR received per day for the last 30 days."""
        db = get_db()
        repo = PaymentRepository(db)
        days_data = await repo.get_summary(days=min(days, 90))
        total_cspr = sum(d["total_cspr"] for d in days_data)
        total_count = sum(d["count"] for d in days_data)
        return PaymentSummaryResponse(
            days=[PaymentSummaryDay(**d) for d in days_data],
            total_cspr=total_cspr,
            total_count=total_count,
        )

    # ------------------------------------------------------------------ #
    # Incidents (EP-01 F-01.3.1)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/incidents", response_model=IncidentListResponse)
    async def list_incidents(
        request: Request,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.3.1 — paginated incidents, filterable by status."""
        db = get_db()
        repo = IncidentRepository(db)
        items, total = await repo.list(status=status, limit=min(limit, 100), offset=max(offset, 0))
        return IncidentListResponse(
            items=[IncidentResponse(**i) for i in items],
            limit=limit,
            offset=offset,
            total=total,
        )

    # ------------------------------------------------------------------ #
    # Risk Intelligence (EP-01 F-01.3.2, F-01.4.1, F-01.5.2)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/entity/{id}/anomalies")
    async def get_anomalies(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.3.2 — return structural anomaly flags for an entity."""
        entity_service: EntityService = request.app.state.entity_service
        entity_hash = entity_service.hash_entity_id(id)
        async with entity_service.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {id: $id}) RETURN e.anomaly_type AS anomaly_type",
                id=entity_hash,
            )
            record = await result.single()

        anomaly_type = record["anomaly_type"] if record and record.get("anomaly_type") else None
        return {
            "entity_hash": entity_hash,
            "anomalies": [anomaly_type] if anomaly_type else [],
        }

    @app.get("/api/v1/entity/{id}/factors", response_model=FactorResponse)
    async def get_factors(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.4.1 — six-factor breakdown (L, C, J, S, A, B).
        US-01.2.3 — computation is persisted to the audit tables."""
        ci_engine: CIEngine = request.app.state.ci_engine
        result = await ci_engine.compute_compliance_index(id)

        entity_hash = ci_engine.entity_service.hash_entity_id(id)
        db = get_db()

        # FIX: v2.0 schema — risk_factors doesn't have entity_id column
        factors_repo = RiskFactorRepository(db)
        await factors_repo.create(
            entity_hash=entity_hash,
            L=result.factor_breakdown.L,
            C=result.factor_breakdown.C,
            J=result.factor_breakdown.J,
            S=result.factor_breakdown.S,
            A=result.factor_breakdown.A,
            B=result.factor_breakdown.B,
        )

        # FIX: use CIComputationRepository instead of NRSComputationRepository
        ci_repo = CIComputationRepository(db)
        await ci_repo.create(
            entity_hash=entity_hash,
            compliance_index=result.compliance_index,
            manifold_score=result.manifold_score,
            jurisdiction_flag=result.jurisdiction_flag,
            weights_used=result.weights_used,
            factor_breakdown=result.factor_breakdown.model_dump(),
            triggered_by="api.factors",
        )

        return FactorResponse(
            L=result.factor_breakdown.L,
            C=result.factor_breakdown.C,
            J=result.factor_breakdown.J,
            S=result.factor_breakdown.S,
            A=result.factor_breakdown.A,
            B=result.factor_breakdown.B,
            B_is_stub=result.factor_breakdown.B_is_stub,
        )

    @app.get("/api/v1/entity/{id}/manifold", response_model=ManifoldResponse)
    async def get_manifold(
        id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-01.5.2 — behavioural manifold classification.

        Full Node2Vec k-means is stubbed pending EP-01 F-01.5 implementation.
        The current heuristic maps the Behavioural Risk (B) factor to a
        5-level risk cluster (0=Low .. 4=High)."""
        ci_engine: CIEngine = request.app.state.ci_engine
        result = await ci_engine.compute_compliance_index(id)
        B = result.factor_breakdown.B
        manifold_score = result.manifold_score

        cluster_risk_level = min(4, int(B * 5))
        cluster_label = 4 - cluster_risk_level  # Low risk → high label

        return ManifoldResponse(
            cluster_label=cluster_label,
            cluster_risk_level=cluster_risk_level,
            manifold_score=manifold_score,
        )

    # ------------------------------------------------------------------ #
    # Admin — Jurisdiction Refresh (US-01.4.3)
    # ------------------------------------------------------------------ #

    @app.post("/api/v1/admin/jurisdiction/refresh")
    async def refresh_jurisdiction(
        req: JurisdictionRefreshRequest,
        request: Request,
        api_key: str = Depends(get_admin_api_key),
    ):
        """US-01.4.3 — refresh in-memory jurisdiction risk table."""
        refresh_jurisdiction_table(req.updates)
        return {"status": "refreshed", "count": len(req.updates)}

    # ------------------------------------------------------------------ #
    # LangGraph Execution Trace (EP-06)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/runs/{run_id}", response_model=RunStateResponse)
    async def get_run_state(
        run_id: str,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """EP-06 — retrieve LangGraph execution trace."""
        db = get_db()
        repo = RunTraceRepository(db)
        run = await repo.get(run_id)
        if not run:
            return JSONResponse(status_code=404, content={"error": "Run not found"})
        return RunStateResponse(
            run_id=run["run_id"],
            entity_id=run["entity_id"],
            state=run["state"],
            created_at=run["created_at"] if isinstance(run["created_at"], datetime) else datetime.fromisoformat(run["created_at"]),
        )

    # ------------------------------------------------------------------ #
    # Admin — Audit Trail (EP-07)
    # ------------------------------------------------------------------ #

    @app.get("/api/v1/audit/{entity_hash}", response_model=AuditResponse)
    async def get_audit(
        entity_hash: str,
        request: Request,
        api_key: str = Depends(get_admin_api_key),
    ):
        """EP-07 — full audit trail: NRS history, proof events, on-chain records."""
        db = get_db()
        ci_repo = CIComputationRepository(db)
        #factors_repo = RiskFactorRepository(db)
        verif_repo = VerificationRepository(db)
        discl_repo = DisclosureAuditRepository(db)

        ci_history = await ci_repo.get_history(entity_hash)
        verifications = await verif_repo.get_latest(entity_hash)
        disclosures = await discl_repo.get_for_entity(entity_hash)

        proof_events = []
        for v in [verifications] if verifications else []:
            proof_events.append({
                "type": "proof_generated",
                "proof_hex": v.get("proof_hex"),
                "verified_at": v.get("verified_at"),
                "status": v.get("status"),
            })
        for d in disclosures:
            proof_events.append({
                "type": "selective_disclosure",
                "factors": json.loads(d["factors_disclosed"]),
                "disclosed_at": d["disclosed_at"],
            })

        on_chain_records = []
        if verifications and verifications.get("stellar_tx_hash"):
            on_chain_records.append({
                "chain": "stellar",
                "tx_hash": verifications["stellar_tx_hash"],
                "verified_at": verifications["verified_at"],
            })

        return AuditResponse(
            entity_hash=entity_hash,
            nrs_history=ci_history,
            proof_events=proof_events,
            on_chain_records=on_chain_records,
        )

    # ------------------------------------------------------------------ #
    # Selective Disclosure (EP-03 F-03.2.2)
    # ------------------------------------------------------------------ #

    @app.post("/api/v1/entity/{entity_hash}/disclose", response_model=DiscloseResponse)
    async def disclose_factors(
        entity_hash: str,
        req: DiscloseRequest,
        request: Request,
        api_key: str = Depends(rate_limited_api_key),
    ):
        """US-03.2.2 — return only boolean pass/fail per factor label for
        the PASS dimensions; factor values and weights are never disclosed."""
        # Validate separate disclosure API key
        disclosure_key = request.headers.get("X-Disclosure-Key")
        settings = request.app.state.settings
        if not disclosure_key or disclosure_key != settings.disclosure_api_key:
            raise _DisclosureAuthError()

        # Look up raw entity id for CI computation
        db = get_db()
        mapping_repo = EntityMappingRepository(db)
        raw_id = await mapping_repo.get_raw_id(entity_hash)
        if not raw_id:
            return JSONResponse(status_code=404, content={"error": "Entity not found"})

        # Compute current compliance state
        ci_engine: CIEngine = request.app.state.ci_engine
        result = await ci_engine.compute_compliance_index(raw_id)

        factors = result.factor_breakdown
        threshold = settings.high_risk_nrs_threshold
        manifold_threshold = settings.manifold_threshold
        ci_passes = result.compliance_index < threshold
        manifold_passes = result.manifold_score >= manifold_threshold
        jurisdiction_passes = result.jurisdiction_flag == 0

        disclosed_labels: list[str] = []
        if ci_passes:
            disclosed_labels.append("COMPLIANCE_INDEX_PASS")
        if manifold_passes:
            disclosed_labels.append("BEHAVIOURAL_MANIFOLD_PASS")
        if jurisdiction_passes:
            disclosed_labels.append("JURISDICTION_PERMITTED")

        for dim, val in [
            ("LIQUIDITY_RISK_PASS", factors.L),
            ("COUNTERPARTY_RISK_PASS", factors.C),
            ("JURISDICTION_RISK_PASS", factors.J),
            ("SANCTIONS_EXPOSURE_PASS", factors.S),
            ("AML_TOPOLOGY_RISK_PASS", factors.A),
            ("BEHAVIOURAL_RISK_PASS", factors.B),
        ]:
            if val < threshold:
                disclosed_labels.append(dim)

        # Persist audit record
        aud_repo = DisclosureAuditRepository(db)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        await aud_repo.create(
            requestor_key_hash=key_hash,
            entity_hash=entity_hash,
            factors_disclosed=disclosed_labels,
            request_signature=req.signature,
        )

        return DiscloseResponse(factors=disclosed_labels)

    return app