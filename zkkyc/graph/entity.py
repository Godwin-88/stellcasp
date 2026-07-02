"""
Entity/Relationship graph service — ZK-KYC Compliance Agent (zkkyc.graph.entity)

Responsibilities
-----------------
- CRUD for :Entity nodes and :TRANSACTED_WITH relationships in Neo4j Aura.
- PII minimisation (spec US-06.1.2): raw entity IDs are NEVER persisted to,
  or returned from, Neo4j. Every node/relationship is keyed by
  entity_hash = SHA256(raw_id + ENTITY_SALT). The raw_id <-> entity_hash
  mapping belongs in the encrypted PostgreSQL `entity_mappings` table
  (a separate concern, outside this module).
- Schema enforcement — uniqueness constraint + composite index (US-01.1.3).
- Submission deduplication within a rolling window (US-01.1.1).

Spec references: EP-01 (F-01.1, F-01.2), EP-06 (F-06.1 / US-06.1.2)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field, field_validator

from ..config import Settings, get_settings

logger = logging.getLogger("zkkyc.graph.entity")


# --------------------------------------------------------------------------- #
# Domain exceptions
#
# These carry enough structure (a `field` pointer, a fixed message) for the
# FastAPI layer to build the exact HTTP status codes and error bodies the
# spec's acceptance criteria demand, instead of leaking raw ValueError text.
# --------------------------------------------------------------------------- #

class EntityServiceError(Exception):
    """Base class for all entity-service domain errors."""


class EntityValidationError(EntityServiceError):
    """Maps to HTTP 422 with a structured, field-level error body."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class DuplicateSubmissionError(EntityServiceError):
    """Maps to HTTP 409 (or 202/200-idempotent, per API layer's choice)."""


class ZeroValueTransactionError(EntityServiceError):
    """Maps to HTTP 400. Message text is spec-mandated — do not change it."""

    def __init__(self):
        super().__init__("Zero-value transactions are not indexed")


class BatchSizeExceededError(EntityServiceError):
    """Maps to HTTP 422."""

    def __init__(self, size: int, limit: int = 1000):
        self.size = size
        self.limit = limit
        super().__init__(f"Batch size {size} exceeds {limit} limit")


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

class EntityType(str, Enum):
    WALLET = "wallet"
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class EntityCreate(BaseModel):
    id: str = Field(
        ...,
        min_length=1,
        description="Raw entity identifier (wallet address or hashed national ID). Never persisted in plaintext.",
    )
    type: EntityType = Field(default=EntityType.UNKNOWN, description="Entity type")

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank or whitespace-only")
        if len(v) > 512:
            raise ValueError("exceeds maximum length of 512 characters")
        return v


class RelationshipCreate(BaseModel):
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    # NOTE: `ge=0`, not `gt=0`, is intentional.
    # Zero-value transactions are a *business-rule* rejection (HTTP 400,
    # spec-mandated message) per US-01.1.2 — not a schema validation
    # failure. `gt=0` would let Pydantic/FastAPI 422 the request before
    # this module ever runs, silently producing the wrong status code and
    # the wrong error message. Zero is validated explicitly below instead.
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(default="XLM")
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    tx_hash: str = Field(..., min_length=1)


class EntityResponse(BaseModel):
    entity_hash: str
    type: EntityType
    created: bool  # True -> API layer should return 201; False -> 200
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RelationshipResponse(BaseModel):
    source_hash: str
    target_hash: str
    tx_hash: str


class GraphHealth(BaseModel):
    status: str
    node_count: int
    relationship_count: int
    neo4j_connected: bool
    response_time_ms: float


# --------------------------------------------------------------------------- #
# Dedupe bookkeeping
# --------------------------------------------------------------------------- #

@dataclass
class _DedupeEntry:
    expires_at: float


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #

class EntityService:
    """
    Neo4j-backed entity/relationship graph service.

    All persisted node/relationship keys are `entity_hash`, never raw IDs.
    Callers pass raw IDs in; this service hashes them before any Neo4j read
    or write and returns hashes only (US-06.1.2 — PII Minimisation).
    """

    _DEDUPE_WINDOW_SECONDS = 60

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.driver = AsyncGraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        # Instance-level (not class-level) dedupe cache. See LIMITATION note
        # on _check_and_mark_dedupe re: multi-replica deployments.
        self._dedupe_cache: dict[str, _DedupeEntry] = {}
        self._dedupe_lock = asyncio.Lock()

    async def close(self) -> None:
        await self.driver.close()

    async def __aenter__(self) -> "EntityService":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------ #
    # PII minimisation
    # ------------------------------------------------------------------ #

    def hash_entity_id(self, entity_id: str) -> str:
        """SHA256(entity_id + ENTITY_SALT).

        Public on purpose: the API layer, audit logger, and on-chain dispatch
        code all need to compute this same hash independently, so that raw
        entity IDs never have to be logged or passed around just to derive it.
        """
        salted = entity_id.strip() + self.settings.entity_salt
        return hashlib.sha256(salted.encode()).hexdigest()

    # ------------------------------------------------------------------ #
    # Dedupe
    #
    # LIMITATION: this cache is per-process / in-memory. Behind more than
    # one API replica, dedupe only holds within a single replica's own
    # 60s window. This platform's stack has no Redis; if multi-replica
    # deployment is needed before the hackathon deadline, back this with a
    # PostgreSQL table keyed on (entity_hash, window_bucket) with a unique
    # constraint instead. Fine for a single-instance staging deployment.
    # ------------------------------------------------------------------ #

    async def _check_and_mark_dedupe(self, key_hash: str) -> bool:
        """Return True if `key_hash` was already seen within the window.
        Otherwise record it and return False. Lazily evicts expired entries
        on every call so the cache can't grow unbounded."""
        now = time.time()
        async with self._dedupe_lock:
            expired = [k for k, v in self._dedupe_cache.items() if v.expires_at <= now]
            for k in expired:
                del self._dedupe_cache[k]

            entry = self._dedupe_cache.get(key_hash)
            if entry and entry.expires_at > now:
                return True

            self._dedupe_cache[key_hash] = _DedupeEntry(
                expires_at=now + self._DEDUPE_WINDOW_SECONDS
            )
            return False

    # ------------------------------------------------------------------ #
    # Schema (US-01.1.3)
    # ------------------------------------------------------------------ #

    async def ensure_schema(self) -> None:
        """Idempotent schema setup. Safe to call on every service startup —
        `IF NOT EXISTS` constraints/indexes are no-ops when already present.
        Call this from the FastAPI app's startup event."""
        async with self.driver.session() as session:
            await session.run(
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
                "FOR (e:Entity) REQUIRE e.id IS UNIQUE"
            )
            await session.run(
                "CREATE INDEX transacted_with_composite IF NOT EXISTS "
                "FOR ()-[r:TRANSACTED_WITH]-() ON (r.source_id, r.target_id, r.tx_hash)"
            )

    # ------------------------------------------------------------------ #
    # Entities
    # ------------------------------------------------------------------ #

    async def create_entity(self, entity: EntityCreate) -> EntityResponse:
        entity_hash = self.hash_entity_id(entity.id)

        if await self._check_and_mark_dedupe(entity_hash):
            logger.info("duplicate submission suppressed", extra={"entity_hash": entity_hash})
            raise DuplicateSubmissionError(
                f"Duplicate submission within {self._DEDUPE_WINDOW_SECONDS}s dedupe window"
            )

        now = datetime.now(timezone.utc).isoformat()

        async def _create_entity_tx(tx: Any):
            cypher = """
            MERGE (e:Entity {id: $id})
            ON CREATE SET e.type = $type, e.created_at = $now, e.updated_at = $now,
                          e.was_created = true
            ON MATCH SET e.type = $type, e.updated_at = $now, e.was_created = false
            RETURN e.id AS id, e.type AS type, e.created_at AS created_at,
                   e.updated_at AS updated_at, e.was_created AS was_created
            """
            result = await tx.run(cypher, id=entity_hash, type=entity.type.value, now=now)
            return await result.single()

        async with self.driver.session() as session:
            record = await session.execute_write(_create_entity_tx)

        logger.info(
            "entity upserted",
            extra={"entity_hash": entity_hash, "created": bool(record["was_created"])},
        )

        return EntityResponse(
            entity_hash=record["id"],
            type=EntityType(record["type"]),
            created=bool(record["was_created"]),
            created_at=datetime.fromisoformat(record["created_at"]) if record.get("created_at") else None,
            updated_at=datetime.fromisoformat(record["updated_at"]) if record.get("updated_at") else None,
        )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #

    async def create_relationship(self, rel: RelationshipCreate) -> RelationshipResponse:
        if rel.amount == 0:
            raise ZeroValueTransactionError()

        source_hash = self.hash_entity_id(rel.source_id)
        target_hash = self.hash_entity_id(rel.target_id)
        now = datetime.now(timezone.utc).isoformat()

        async def _create_relationship_tx(tx: Any):
            cypher = """
            MERGE (s:Entity {id: $source_id})
            ON CREATE SET s.type = 'unknown', s.created_at = $now, s.updated_at = $now
            MERGE (t:Entity {id: $target_id})
            ON CREATE SET t.type = 'unknown', t.created_at = $now, t.updated_at = $now
            MERGE (s)-[r:TRANSACTED_WITH {tx_hash: $tx_hash}]->(t)
            ON CREATE SET r.amount = $amount, r.currency = $currency, r.timestamp = $timestamp
            ON MATCH SET r.amount = $amount, r.currency = $currency, r.timestamp = $timestamp
            """
            await tx.run(
                cypher,
                source_id=source_hash,
                target_id=target_hash,
                amount=rel.amount,
                currency=rel.currency,
                timestamp=rel.timestamp,
                tx_hash=rel.tx_hash,
                now=now,
            )

        async with self.driver.session() as session:
            await session.execute_write(_create_relationship_tx)

        return RelationshipResponse(
            source_hash=source_hash, target_hash=target_hash, tx_hash=rel.tx_hash
        )

    async def create_relationships_batch(self, relationships: list[RelationshipCreate]) -> int:
        """Single UNWIND round-trip instead of one write per relationship —
        the previous per-item loop could not plausibly hit the spec's
        "1000 relationships within 10 seconds" requirement on a free-tier
        Neo4j Aura instance (US-01.1.2)."""
        if len(relationships) > 1000:
            raise BatchSizeExceededError(len(relationships))

        if any(r.amount == 0 for r in relationships):
            raise ZeroValueTransactionError()

        now = datetime.now(timezone.utc).isoformat()
        payload = [
            {
                "source_id": self.hash_entity_id(r.source_id),
                "target_id": self.hash_entity_id(r.target_id),
                "amount": r.amount,
                "currency": r.currency,
                "timestamp": r.timestamp,
                "tx_hash": r.tx_hash,
            }
            for r in relationships
        ]

        async def _create_batch_tx(tx: Any):
            cypher = """
            UNWIND $rels AS rel
            MERGE (s:Entity {id: rel.source_id})
            ON CREATE SET s.type = 'unknown', s.created_at = $now, s.updated_at = $now
            MERGE (t:Entity {id: rel.target_id})
            ON CREATE SET t.type = 'unknown', t.created_at = $now, t.updated_at = $now
            MERGE (s)-[r:TRANSACTED_WITH {tx_hash: rel.tx_hash}]->(t)
            ON CREATE SET r.amount = rel.amount, r.currency = rel.currency, r.timestamp = rel.timestamp
            ON MATCH SET r.amount = rel.amount, r.currency = rel.currency, r.timestamp = rel.timestamp
            """
            await tx.run(cypher, rels=payload, now=now)

        async with self.driver.session() as session:
            await session.execute_write(_create_batch_tx)

        return len(relationships)

    async def get_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        entity_hash = self.hash_entity_id(entity_id)
        async with self.driver.session() as session:
            cypher = """
            MATCH (e:Entity {id: $id})-[r:TRANSACTED_WITH]->(t:Entity)
            RETURN t.id AS target_hash, r.amount AS amount, r.currency AS currency,
                   r.timestamp AS timestamp, r.tx_hash AS tx_hash
            """
            result = await session.run(cypher, id=entity_hash)
            return [dict(record) async for record in result]

    # ------------------------------------------------------------------ #
    # Health / observability (US-01.1.3)
    # ------------------------------------------------------------------ #

    async def get_graph_health(self) -> GraphHealth:
        start = time.perf_counter()
        try:
            async with self.driver.session() as session:
                node_result = await session.run("MATCH (n:Entity) RETURN count(n) AS count")
                node_record = await node_result.single()
                node_count = node_record["count"] if node_record else 0

                rel_result = await session.run(
                    "MATCH ()-[r:TRANSACTED_WITH]->() RETURN count(r) AS count"
                )
                rel_record = await rel_result.single()
                rel_count = rel_record["count"] if rel_record else 0

            elapsed_ms = (time.perf_counter() - start) * 1000
            return GraphHealth(
                status="healthy",
                node_count=node_count,
                relationship_count=rel_count,
                neo4j_connected=True,
                response_time_ms=round(elapsed_ms, 2),
            )
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception("graph health check failed")
            return GraphHealth(
                status="unhealthy",
                node_count=0,
                relationship_count=0,
                neo4j_connected=False,
                response_time_ms=round(elapsed_ms, 2),
            )

    # ------------------------------------------------------------------ #
    # Subgraph export (feeds NetworkX / NRS engine)
    # ------------------------------------------------------------------ #

    async def export_subgraph(self, entity_id: str, hops: int = 3) -> dict[str, list[dict]]:
        # `hops` is interpolated into the Cypher string below because Neo4j
        # does not support parameterising variable-length path bounds.
        # That makes strict validation mandatory here: an unvalidated hops
        # value is both a Cypher-injection surface and an unbounded-traversal
        # DoS risk on a shared free-tier instance.
        try:
            hops = int(hops)
        except (TypeError, ValueError):
            raise EntityValidationError("hops", "must be an integer")
        if not 1 <= hops <= 5:
            raise EntityValidationError("hops", "must be between 1 and 5")

        entity_hash = self.hash_entity_id(entity_id)
        async with self.driver.session() as session:
            cypher = f"""
            MATCH (start:Entity {{id: $id}})
            MATCH path = (start)-[:TRANSACTED_WITH*1..{hops}]->(n)
            RETURN DISTINCT n.id AS id
            """
            result = await session.run(cypher, id=entity_hash)
            node_ids = [record["id"] async for record in result]

            all_ids = set(node_ids) | {entity_hash}

            edges_cypher = """
            MATCH (s:Entity)-[r:TRANSACTED_WITH]->(t:Entity)
            WHERE s.id IN $ids AND t.id IN $ids
            RETURN s.id AS source, t.id AS target, r.amount AS amount, r.tx_hash AS tx_hash
            """
            edges_result = await session.run(edges_cypher, ids=list(all_ids))
            edges = [dict(record) async for record in edges_result]

            nodes = [{"id": nid} for nid in all_ids]
            return {"nodes": nodes, "edges": edges}

    async def update_community_id(self, entity_id: str, community_id: int) -> None:
        """Takes a RAW entity id and hashes it internally. Use this from
        external/API callers that only ever deal in raw ids."""
        if community_id < 0:
            raise EntityValidationError("community_id", "must be non-negative")

        entity_hash = self.hash_entity_id(entity_id)
        await self.set_community_id_by_hash(entity_hash, community_id)

    async def set_community_id_by_hash(self, entity_hash: str, community_id: int) -> None:
        """Takes an already-hashed entity id and writes it as-is — no
        re-hashing. Use this from internal callers (e.g. NRSEngine) that
        already hold entity_hash values sourced from export_subgraph(),
        since re-hashing an already-hashed value would target the wrong
        node in Neo4j."""
        if community_id < 0:
            raise EntityValidationError("community_id", "must be non-negative")

        async with self.driver.session() as session:
            await session.run(
                "MATCH (e:Entity {id: $id}) SET e.community_id = $community_id",
                id=entity_hash,
                community_id=community_id,
            )