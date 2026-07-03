"""
Async PostgreSQL-backed persistence layer for the FastAPI gateway.

Spec reference: EP-04, EP-05, EP-06, EP-07
US-04.1.1, US-01.2.3, US-01.3.1, US-01.4.1, US-04.2.3, EP-03.2.2, EP-03.1.3

Uses asyncpg against the Postgres instance defined in config.py
(postgres_dsn). Migrations are loaded idempotently from
migrations/001_initial_schema.sql on connect, plus a small bootstrap block
for tables appended after that migration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import asyncpg

from ..config import get_settings

logger = logging.getLogger(__name__)

_MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "migrations" / "001_initial_schema.sql"

# Auxiliary tables not in the v2.0 migration but required by the API layer.
# These are created idempotently after the main migration runs.
_BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS verifications (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    entity_hash     TEXT NOT NULL,
    stellar_tx_hash TEXT,
    proof_hex       TEXT,
    threshold_public NUMERIC NOT NULL,
    status          TEXT NOT NULL DEFAULT 'VALID',
    verified_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS casper_verdicts (
    entity_hash     TEXT PRIMARY KEY,
    verdict         BOOLEAN,
    expires_at      BIGINT,
    status          TEXT NOT NULL DEFAULT 'NOT_FOUND',
    cached_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS run_trace (
    run_id          TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL,
    state_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS incidents (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    entity_hash     TEXT NOT NULL,
    ci              NUMERIC NOT NULL,
    threshold       NUMERIC NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    webhook_status  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_entity ON incidents (entity_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents (status);
"""


class Database:
    """Thin wrapper over an asyncpg connection pool."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn: str = dsn or get_settings().postgres_dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        await self._apply_schema()
        logger.info("postgres database connected", extra={"dsn": self.dsn})

    async def _apply_schema(self) -> None:
        if not self._pool:
            return
        sql = _MIGRATIONS_PATH.read_text()
        async with self._pool.acquire() as conn:
            await conn.execute(sql)
            await conn.execute(_BOOTSTRAP_SQL)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database not connected")
        return self._pool

    async def execute(self, sql: str, *args: Any) -> str:
        if not self._pool:
            raise RuntimeError("Database not connected")
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    async def fetchone(self, sql: str, *args: Any) -> dict[str, Any] | None:
        if not self._pool:
            raise RuntimeError("Database not connected")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
            return dict(row) if row else None

    async def fetchall(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        if not self._pool:
            raise RuntimeError("Database not connected")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]

    async def truncate_all(self) -> None:
        if not self._pool:
            raise RuntimeError("Database not connected")
        tables = [
            "api_rate_events",
            "disclosure_audit",
            "run_trace",
            "casper_verdicts",
            "verifications",
            "risk_factors",
            "nrs_computations",
            "compliance_incidents",
            "payment_failures",
            "payment_receipts",
            "api_keys",
            "incidents",
            "entity_mappings",
        ]
        async with self._pool.acquire() as conn:
            await conn.execute(
                "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
            )


_db: Database | None = None


def get_db(dsn: str | None = None) -> Database:
    global _db
    if _db is None:
        _db = Database(dsn)
    return _db


def reset_db() -> None:
    """Reset global DB instance (primarily for tests)."""
    global _db
    if _db is not None:
        try:
            import asyncio
            asyncio.get_event_loop().run_until_complete(_db.close())
        except Exception:
            pass
        _db = None