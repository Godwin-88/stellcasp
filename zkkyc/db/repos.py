"""
Async repository implementations over asyncpg (PostgreSQL).

Spec reference: EP-04, EP-05, EP-06, EP-07
US-04.1.1, US-01.2.3, US-01.3.1, US-01.4.1, US-04.2.3, EP-03.2.2, EP-03.1.3

Each repository encapsulates SQL for one domain table. All methods are async
and expect an active Database connection obtained via get_db().
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from . import Database

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

class APIKeyRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, key_id: str, key_hash: str, name: str, rate_limit: int) -> None:
        await self.db.execute(
            "INSERT INTO api_keys (id, key_hash, name, rate_limit_rpm) VALUES ($1, $2, $3, $4)",
            key_id, key_hash, name, rate_limit,
        )

    async def get(self, key_id: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM api_keys WHERE id = $1", key_id,
        )

    async def get_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM api_keys WHERE key_hash = $1", key_hash,
        )

    async def update_rate_limit(self, key_id: str, rate_limit: int) -> None:
        await self.db.execute(
            "UPDATE api_keys SET rate_limit_rpm = $1 WHERE id = $2",
            rate_limit, key_id,
        )

    async def count_active(self) -> int:
        row = await self.db.fetchone(
            "SELECT COUNT(*) AS cnt FROM api_keys WHERE is_active = TRUE"
        )
        return row["cnt"] if row else 0

    async def list_all(self) -> list[dict[str, Any]]:
        return await self.db.fetchall(
            "SELECT id, name, rate_limit_rpm, is_active, created_at FROM api_keys"
        )


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

class PaymentRepository:
    def __init__(self, db: Database):
        self.db = db

    async def record_receipt(
        self,
        deploy_hash: str,
        entity_hash: str | None,
        amount_cspr: float,
        api_key_id: str | None,
        verified_at: str | None = None,
    ) -> None:
        verified_at = verified_at or _now()
        await self.db.execute(
            "INSERT INTO payment_receipts (deploy_hash, entity_hash, amount_cspr, api_key_id, verified_at) "
            "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (deploy_hash) DO NOTHING",
            deploy_hash, entity_hash, amount_cspr, api_key_id, verified_at,
        )

    async def is_deploy_consumed(self, deploy_hash: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM payment_receipts WHERE deploy_hash = $1", deploy_hash
        )
        return row is not None

    async def record_failure(
        self,
        deploy_hash: str,
        failure_reason: str,
        api_key_id: str | None,
    ) -> None:
        failure_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO payment_failures (id, deploy_hash, failure_reason, api_key_id) "
            "VALUES ($1, $2, $3, $4)",
            failure_id, deploy_hash, failure_reason, api_key_id,
        )

    async def get_summary(self, days: int = 30) -> list[dict[str, Any]]:
        rows = await self.db.fetchall(
            "SELECT DATE(verified_at) AS day, COUNT(*) AS count, SUM(amount_cspr) AS total_cspr "
            "FROM payment_receipts "
            "WHERE verified_at >= NOW() - ($1 || ' days')::INTERVAL "
            "GROUP BY DATE(verified_at) ORDER BY day DESC",
            str(days),
        )
        return [
            {"date": str(r["day"]), "count": r["count"], "total_cspr": float(r["total_cspr"] or 0.0)}
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class IncidentRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        entity_hash: str,
        ci: float,
        threshold: float,
        status: str = "PENDING_REVIEW",
    ) -> str:
        incident_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO incidents (id, entity_hash, ci, threshold, status) VALUES ($1, $2, $3, $4, $5)",
            incident_id, entity_hash, ci, threshold, status,
        )
        return incident_id

    async def create_incident(self, entity_hash: str, ci: float, threshold: float, status: str) -> str:
        return await self.create(entity_hash, ci, threshold, status)

    async def update_status(self, incident_id: str, status: str) -> None:
        await self.db.execute(
            "UPDATE incidents SET status = $1 WHERE id = $2",
            status, incident_id,
        )

    async def update_incident_status(self, incident_id: str, status: str) -> None:
        await self.update_status(incident_id, status)

    async def list(
        self,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        where = []
        params: list[Any] = []
        if status:
            where.append("status = $1")
            params.append(status)
        where_clause = ("WHERE " + " AND ".join(where)) if where else ""
        total_row = await self.db.fetchone(
            f"SELECT COUNT(*) AS cnt FROM incidents {where_clause}", *params
        )
        total = total_row["cnt"] if total_row else 0
        positional = list(params) + [limit, offset]
        rows = await self.db.fetchall(
            f"SELECT * FROM incidents {where_clause} ORDER BY created_at DESC LIMIT ${len(positional) - 1} OFFSET ${len(positional)}",
            *positional,
        )
        items = []
        for row in rows:
            row["incident_id"] = row.pop("id")
            items.append(row)
        return items, total

    async def get(self, incident_id: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM incidents WHERE id = $1", incident_id,
        )


# ---------------------------------------------------------------------------
# CI Computations (v2.0 — replaces NRSComputationRepository)
# ---------------------------------------------------------------------------

class CIComputationRepository:
    """Persists Compliance Index computations to the v2.0 audit table."""

    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        entity_hash: str,
        compliance_index: float,
        manifold_score: float,
        jurisdiction_flag: int,
        weights_used: dict[str, float],
        factor_breakdown: dict[str, float],
        triggered_by: str | None = None,
    ) -> str:
        comp_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO compliance_index_computations "
            "(id, entity_hash, compliance_index, manifold_score, jurisdiction_flag, "
            "weights_used, factor_breakdown, triggered_by) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            comp_id, entity_hash, compliance_index, manifold_score, jurisdiction_flag,
            json.dumps(weights_used), json.dumps(factor_breakdown), triggered_by,
        )
        return comp_id

    async def get_history(self, entity_hash: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self.db.fetchall(
            "SELECT * FROM compliance_index_computations WHERE entity_hash = $1 "
            "ORDER BY computed_at DESC LIMIT $2",
            entity_hash, limit,
        )


# Legacy alias for backward compatibility
NRSComputationRepository = CIComputationRepository


# ---------------------------------------------------------------------------
# Risk Factors
# ---------------------------------------------------------------------------

class RiskFactorRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        entity_hash: str,
        L: float,
        C: float,
        J: float,
        S: float,
        A: float,
        B: float,
    ) -> str:
        factor_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO risk_factors (id, entity_hash, L, C, J, S, A, B, b_is_stub) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)",
            factor_id, entity_hash, L, C, J, S, A, B,
        )
        return factor_id

    async def get_latest(self, entity_hash: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM risk_factors WHERE entity_hash = $1 ORDER BY computed_at DESC LIMIT 1",
            entity_hash,
        )


# ---------------------------------------------------------------------------
# Disclosure Audit
# ---------------------------------------------------------------------------

class DisclosureAuditRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        requestor_key_hash: str,
        entity_hash: str,
        factors_disclosed: list[str],
        request_signature: str,
    ) -> str:
        audit_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO disclosure_audit (id, requestor_key_hash, entity_hash, factors_disclosed, request_signature) "
            "VALUES ($1, $2, $3, $4, $5)",
            audit_id, requestor_key_hash, entity_hash, json.dumps(factors_disclosed), request_signature,
        )
        return audit_id

    async def get_for_entity(self, entity_hash: str) -> list[dict[str, Any]]:
        return await self.db.fetchall(
            "SELECT * FROM disclosure_audit WHERE entity_hash = $1 ORDER BY disclosed_at DESC",
            entity_hash,
        )


# ---------------------------------------------------------------------------
# Verifications (credential store)
# ---------------------------------------------------------------------------

class VerificationRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(
        self,
        entity_hash: str,
        stellar_tx_hash: str | None,
        proof_hex: str | None,
        threshold_public: float,
        status: str = "VALID",
    ) -> str:
        vid = str(uuid.uuid4())
        now = _now()
        await self.db.execute(
            "INSERT INTO verifications (id, entity_hash, stellar_tx_hash, proof_hex, threshold_public, status, verified_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)",
            vid, entity_hash, stellar_tx_hash, proof_hex, threshold_public, status, now,
        )
        return vid

    async def get_latest(self, entity_hash: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM verifications WHERE entity_hash = $1 ORDER BY verified_at DESC LIMIT 1",
            entity_hash,
        )

    async def update_status(self, verification_id: str, status: str) -> None:
        await self.db.execute(
            "UPDATE verifications SET status = $1 WHERE id = $2",
            status, verification_id,
        )


# ---------------------------------------------------------------------------
# Casper Verdict Cache
# ---------------------------------------------------------------------------

class CasperVerdictCacheRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, entity_hash: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            "SELECT * FROM casper_verdicts WHERE entity_hash = $1", entity_hash,
        )

    async def upsert(
        self,
        entity_hash: str,
        verdict: bool | None,
        expires_at: int,
        status: str,
    ) -> None:
        await self.db.execute(
            "INSERT INTO casper_verdicts (entity_hash, verdict, expires_at, status) "
            "VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (entity_hash) DO UPDATE SET verdict = EXCLUDED.verdict, expires_at = EXCLUDED.expires_at, "
            "status = EXCLUDED.status, cached_at = NOW()",
            entity_hash, verdict, expires_at, status,
        )


# ---------------------------------------------------------------------------
# Run Trace (LangGraph state)
# ---------------------------------------------------------------------------

class RunTraceRepository:
    def __init__(self, db: Database):
        self.db = db

    async def save(self, run_id: str, entity_id: str, state: dict[str, Any]) -> None:
        await self.db.execute(
            "INSERT INTO run_trace (run_id, entity_id, state_json) VALUES ($1, $2, $3) "
            "ON CONFLICT (run_id) DO UPDATE SET state_json = EXCLUDED.state_json",
            run_id, entity_id, json.dumps(state),
        )

    async def get(self, run_id: str) -> dict[str, Any] | None:
        row = await self.db.fetchone(
            "SELECT * FROM run_trace WHERE run_id = $1", run_id,
        )
        if not row:
            return None
        return {
            "run_id": row["run_id"],
            "entity_id": row["entity_id"],
            "state": json.loads(row["state_json"]),
            "created_at": row["created_at"],
        }


# ---------------------------------------------------------------------------
# Entity Mappings
# ---------------------------------------------------------------------------

class EntityMappingRepository:
    def __init__(self, db: Database):
        self.db = db

    async def put(self, entity_hash: str, raw_id: str) -> None:
        await self.db.execute(
            "INSERT INTO entity_mappings (entity_hash, entity_id, raw_id) VALUES ($1, $2::bytea, $3) "
            "ON CONFLICT (entity_hash) DO NOTHING",
            entity_hash, raw_id.encode(), raw_id,
        )

    async def get_raw_id(self, entity_hash: str) -> str | None:
        row = await self.db.fetchone(
            "SELECT raw_id FROM entity_mappings WHERE entity_hash = $1", entity_hash,
        )
        return row["raw_id"] if row else None