"""
Tests for all FastAPI endpoints implemented in zkkyc.api.main.

Spec reference: EP-01 (F-01.1.3, F-01.3.1, F-01.3.2, F-01.4.1, F-01.4.3,
                        F-01.5.2),
                EP-02 (F-02.2.3),
                EP-03 (F-03.1.3, F-03.2.2),
                EP-04 (F-04.1.1, F-04.1.3, F-04.2.1, F-04.2.2, F-04.2.3,
                        F-03.1.3),
                EP-05, EP-06, EP-07

All HTTP-level behaviour tested through httpx.AsyncClient with ASGITransport,
backed by the running Postgres instance (dockerized) with mocked service layers.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import json  # Add at top of file
from zkkyc.api.main import create_app, hash_api_key
from zkkyc.config import Settings
from zkkyc.db import Database, reset_db
from zkkyc.db.repos import (
    APIKeyRepository,
    CasperVerdictCacheRepository,
    EntityMappingRepository,
    IncidentRepository,
    RiskFactorRepository,
    RunTraceRepository,
)
from zkkyc.graph.entity import (
    EntityService,
    EntityResponse,
    GraphHealth,
    RelationshipResponse,
    ZeroValueTransactionError,
    BatchSizeExceededError,
)
from zkkyc.graph.nrs import CIEngine, FactorBreakdown, NRSDetails

# ===========================================================================
# Helpers / fixtures
# ===========================================================================

TEST_API_KEY = "test-api-key-123"
TEST_ADMIN_SECRET = "admin-secret-456"
TEST_DISCLOSURE_KEY = "disclosure-key-789"


def _make_settings() -> Settings:
    return Settings(
        entity_salt="test_salt",
        admin_secret=TEST_ADMIN_SECRET,
        disclosure_api_key=TEST_DISCLOSURE_KEY,
        api_rate_limit_default=600,
        x402_price_cspr=0.001,
        casper_treasury_public_key="casper_treasury",
        high_risk_nrs_threshold=0.75,
        manifold_threshold=0.20,
        platform_signing_key="",
    )


@pytest.fixture()
async def app():
    settings = _make_settings()

    reset_db()
    test_db = Database()
    await test_db.connect()
    await test_db.truncate_all()
    print("DEBUG: test_db._pool =", test_db._pool is not None)

    api_key_repo = APIKeyRepository(test_db)
    await api_key_repo.create(
        key_id="99d93bb1-baa8-45ff-8280-317073bd17fb",
        key_hash=hash_api_key(TEST_API_KEY),
        name="test-automation",
        rate_limit=settings.api_rate_limit_default,
    )

    _created_entities: dict[str, dict] = {}

    async def _mock_create_entity(entity):
        eid = entity.id
        if eid in _created_entities:
            return EntityResponse(
                entity_hash=f"eh_{eid}",
                type=entity.type,
                created=False,
                created_at=_created_entities[eid]["created_at"],
                updated_at=datetime.now(timezone.utc),
            )
        now = datetime.now(timezone.utc)
        _created_entities[eid] = {"created_at": now, "type": entity.type}
        return EntityResponse(
            entity_hash=f"eh_{eid}",
            type=entity.type,
            created=True,
            created_at=now,
            updated_at=now,
        )

    async def _mock_create_relationship(rel):
        if rel.amount == 0:
            raise ZeroValueTransactionError()
        return RelationshipResponse(
            source_hash=f"eh_{rel.source_id}",
            target_hash=f"eh_{rel.target_id}",
            tx_hash=rel.tx_hash,
        )

    async def _mock_create_relationships_batch(rels):
        if len(rels) > 1000:
            raise BatchSizeExceededError(len(rels))
        if any(r.amount == 0 for r in rels):
            raise ZeroValueTransactionError()
        return len(rels)

    mock_entity_svc = MagicMock(spec=EntityService)
    mock_entity_svc.driver = MagicMock()
    mock_entity_svc.hash_entity_id = MagicMock(side_effect=lambda eid: f"eh_{eid}")
    mock_entity_svc.ensure_schema = AsyncMock()
    mock_entity_svc.get_graph_health = AsyncMock(
        return_value=GraphHealth(
            status="healthy", node_count=0, relationship_count=0,
            neo4j_connected=False, response_time_ms=0.0,
        )
    )
    mock_entity_svc.create_entity = AsyncMock(side_effect=_mock_create_entity)
    mock_entity_svc.create_relationship = AsyncMock(side_effect=_mock_create_relationship)
    mock_entity_svc.create_relationships_batch = AsyncMock(side_effect=_mock_create_relationships_batch)
    mock_entity_svc.get_relationships = AsyncMock(
        return_value=[
            {"source_hash": "eh_a", "target_hash": "eh_b", "amount": 5.0, "currency": "XLM", "timestamp": 0, "tx_hash": "rel-1"}
        ]
    )

    mock_nrs_engine = MagicMock()
    mock_nrs_engine.compute_nrs = AsyncMock(
        return_value=NRSDetails(
            pagerank_score=0.3, betweenness_score=0.2,
            community_risk_score=0.15, raw_nrs=0.42,
        )
    )

    mock_ci_engine = MagicMock(spec=CIEngine)
    mock_ci_engine.entity_service = mock_entity_svc
    mock_ci_engine.compute_compliance_index = AsyncMock(
        return_value=MagicMock(
            compliance_index=0.42,
            factor_breakdown=FactorBreakdown(
                L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6
            ),
            manifold_score=0.8,
            jurisdiction_flag=0,
            weights_used={"L": 0.10, "C": 0.20, "J": 0.15, "S": 0.25, "A": 0.20, "B": 0.10},
            model_dump_json=MagicMock(return_value='{"CI": 0.42}'),
        )
    )

    mock_x402 = MagicMock()
    mock_x402.create_payment_challenge = MagicMock(
        return_value={
            "payment_required": True,
            "amount_cspr": "0.001",
            "payment_address": "casper_treasury",
            "expires_in_seconds": 30,
        }
    )
    mock_x402.verify_payment = AsyncMock(
        return_value={
            "deploy_hash": "fake_hash",
            "amount_cspr": 0.001,
            "verified": True,
        }
    )

    import zkkyc.api.main as main_module
    from zkkyc.config import get_settings as original_get_settings
    from zkkyc.db import get_db as original_get_db

    original_lifespan = main_module.lifespan

    async def fake_lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.entity_service = mock_entity_svc
        app.state.nrs_engine = mock_nrs_engine
        app.state.ci_engine = mock_ci_engine
        app.state.x402_service = mock_x402
        app.state.db = test_db
        main_module.get_db = lambda dsn=None: test_db
        import logging; logging.getLogger("test").warning("fake_lifespan: test_db._pool=%s", test_db._pool is not None)
        app.dependency_overrides[original_get_settings] = lambda: settings
        yield
        main_module.get_db = original_get_db

    main_module.lifespan = fake_lifespan
    app_instance = create_app()

    yield app_instance

    main_module.lifespan = original_lifespan
    await test_db.truncate_all()
    await test_db.close()
    reset_db()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture()
def authed_headers():
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture()
def admin_headers(authed_headers):
    return {**authed_headers, "X-Admin-Secret": TEST_ADMIN_SECRET}


# ===========================================================================
# Helpers
# ===========================================================================

def _patch_nrs(mock_nrs_engine, raw_nrs=0.42):
    mock_nrs_engine.compute_nrs.return_value = NRSDetails(
        pagerank_score=0.3,
        betweenness_score=0.2,
        community_risk_score=0.15,
        raw_nrs=raw_nrs,
    )


def _patch_ci(mock_ci_engine, ci=0.42):
    mock_ci_engine.compute_compliance_index.return_value = MagicMock(
        compliance_index=ci,
        factor_breakdown=FactorBreakdown(
            L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6
        ),
        manifold_score=0.8,
        jurisdiction_flag=0,
        model_dump_json=MagicMock(return_value='{"CI": 0.42}'),
    )


# ===========================================================================
# Health (no spec section — liveness probe)
# ===========================================================================


class TestHealth:
    """GET /health — unauthenticated."""

    async def test_health_returns_200(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert "timestamp" in body

    async def test_graph_health(self, client, authed_headers):
        """US-01.1.3"""
        r = await client.get("/api/v1/graph/health", headers=authed_headers)
        assert r.status_code == 200
        for key in (
            "status",
            "node_count",
            "relationship_count",
            "neo4j_connected",
            "response_time_ms",
        ):
            assert key in r.json()

    async def test_graph_health_no_auth_401(self, client):
        r = await client.get("/api/v1/graph/health")
        assert r.status_code == 401


# ===========================================================================
# Entity & Relationship CRUD (EP-01 F-01.1, F-01.2)
# ===========================================================================


class TestEntityRoutes:
    """POST /api/v1/entity, POST /api/v1/relationship,
       POST /api/v1/relationships/batch, GET /api/v1/entity/{id}/relationships"""

    async def test_create_entity_201(self, client, authed_headers):
        r = await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "wallet-1", "type": "wallet"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["entity_hash"] == "eh_wallet-1"
        assert body["type"] == "wallet"
        assert body["created"] is True
        assert "created_at" in body

    async def test_create_entity_upsert_200(self, client, authed_headers):
        payload = {"id": "wallet-dup", "type": "wallet"}
        r1 = await client.post("/api/v1/entity", headers=authed_headers, json=payload)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/entity", headers=authed_headers, json=payload)
        assert r2.status_code == 200
        assert r2.json()["created"] is False

    async def test_create_entity_blank_id_422(self, client, authed_headers):
        r = await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "   ", "type": "wallet"},
        )
        assert r.status_code == 422

    async def test_create_entity_defaults_to_unknown(self, client, authed_headers):
        r = await client.post(
            "/api/v1/entity", headers=authed_headers, json={"id": "w-no-type"}
        )
        assert r.status_code == 201
        assert r.json()["type"] == "unknown"

    async def test_relationship_201(self, client, authed_headers):
        for wid in ("src", "dst"):
            await client.post(
                "/api/v1/entity",
                headers=authed_headers,
                json={"id": wid, "type": "wallet"},
            )
        r = await client.post(
            "/api/v1/relationship",
            headers=authed_headers,
            json={
                "source_id": "src",
                "target_id": "dst",
                "amount": 10.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": "tx-1",
            },
        )
        assert r.status_code == 201

    async def test_relationship_zero_amount_400(self, client, authed_headers):
        r = await client.post(
            "/api/v1/relationship",
            headers=authed_headers,
            json={
                "source_id": "a",
                "target_id": "b",
                "amount": 0.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": "tx0",
            },
        )
        assert r.status_code == 400
        assert r.json()["error"] == "Zero-value transactions are not indexed"

    async def test_batch_relationships_201(self, client, authed_headers):
        for wid in ("s1", "d1"):
            await client.post(
                "/api/v1/entity", headers=authed_headers, json={"id": wid}
            )
        payload = [
            {
                "source_id": "s1",
                "target_id": "d1",
                "amount": float(i + 1),
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": f"b-{i}",
            }
            for i in range(5)
        ]
        r = await client.post(
            "/api/v1/relationships/batch",
            headers=authed_headers,
            json=payload,
        )
        assert r.status_code == 201
        assert r.json()["created"] == 5

    async def test_batch_over_limit_422(self, client, authed_headers):
        payload = [
            {
                "source_id": "s",
                "target_id": "d",
                "amount": 1.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": f"t{i}",
            }
            for i in range(1001)
        ]
        r = await client.post(
            "/api/v1/relationships/batch",
            headers=authed_headers,
            json=payload,
        )
        assert r.status_code == 422
        assert "exceeds" in r.json()["error"]

    async def test_batch_rejects_zero_mid_batch(self, client, authed_headers):
        payload = [
            {
                "source_id": "s",
                "target_id": "d",
                "amount": 1.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": "good",
            },
            {
                "source_id": "s",
                "target_id": "d",
                "amount": 0.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": "zero",
            },
        ]
        r = await client.post(
            "/api/v1/relationships/batch",
            headers=authed_headers,
            json=payload,
        )
        assert r.status_code == 400

    async def test_get_relationships(self, client, authed_headers):
        for wid in ("a", "b"):
            await client.post(
                "/api/v1/entity", headers=authed_headers, json={"id": wid}
            )
        await client.post(
            "/api/v1/relationship",
            headers=authed_headers,
            json={
                "source_id": "a",
                "target_id": "b",
                "amount": 5.0,
                "currency": "XLM",
                "timestamp": int(time.time()),
                "tx_hash": "rel-1",
            },
        )
        r = await client.get(
            "/api/v1/entity/a/relationships", headers=authed_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["target_hash"] == "eh_b"
        assert body[0]["amount"] == 5.0


# ===========================================================================
# Admin — API Key Management (EP-05 US-04.1.1, US-04.1.3)
# ===========================================================================


class TestAdminAPIKeys:
    """POST /api/v1/keys, POST /api/v1/keys/{key_id}/limit"""

    async def test_create_key(self, client, admin_headers):
        r = await client.post(
            "/api/v1/keys",
            headers=admin_headers,
            json={"name": "dev-key", "rate_limit": 120},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "dev-key"
        assert body["rate_limit"] == 120
        key = body["plaintext_key"]
        assert isinstance(key, str) and len(key) >= 20

    async def test_create_key_default_rate_limit(self, client, admin_headers):
        r = await client.post(
            "/api/v1/keys",
            headers=admin_headers,
            json={"name": "default-limit"},
        )
        assert r.status_code == 201
        assert r.json()["rate_limit"] == 60

    async def test_create_key_requires_admin_secret(self, client, authed_headers):
        r = await client.post(
            "/api/v1/keys", headers=authed_headers, json={"name": "x"}
        )
        assert r.status_code == 403

    async def test_create_key_requires_valid_api_key(self, client):
        r = await client.post(
            "/api/v1/keys",
            headers={"X-API-Key": "bogus", "X-Admin-Secret": TEST_ADMIN_SECRET},
            json={"name": "x"},
        )
        assert r.status_code == 401

    async def test_update_rate_limit(self, client, admin_headers):
        create = await client.post(
            "/api/v1/keys",
            headers=admin_headers,
            json={"name": "rl-key", "rate_limit": 60},
        )
        key_id = create.json()["key_id"]

        r = await client.post(
            f"/api/v1/keys/{key_id}/limit",
            headers=admin_headers,
            json={"rate_limit": 300},
        )
        assert r.status_code == 200
        assert r.json() == {"key_id": key_id, "rate_limit": 300}

    async def test_update_rate_limit_not_found(self, client, admin_headers):
        r = await client.post(
            "/api/v1/keys/missing-id/limit",
            headers=admin_headers,
            json={"rate_limit": 1},
        )
        assert r.status_code == 404

    async def test_update_rate_limit_above_max(self, client, admin_headers):
        r = await client.post(
            "/api/v1/keys/some-id/limit",
            headers=admin_headers,
            json={"rate_limit": 601},
        )
        assert r.status_code == 422

    async def test_update_rate_limit_below_min(self, client, admin_headers):
        r = await client.post(
            "/api/v1/keys/some-id/limit",
            headers=admin_headers,
            json={"rate_limit": 0},
        )
        assert r.status_code == 422

    async def test_create_key_missing_admin_secret(self, client, authed_headers):
        r = await client.post(
            "/api/v1/keys",
            headers=authed_headers,
            json={"name": "x", "rate_limit": 10},
        )
        assert r.status_code == 403


# ===========================================================================
# NRS / x402 (EP-04 F-04.2)
# ===========================================================================


class TestNRSAndPayments:
    """GET /api/v1/entity/{id}/nrs — payment-gated."""

    async def test_returns_402_without_payment(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "ent-1", "type": "wallet"},
        )
        r = await client.get("/api/v1/entity/ent-1/nrs", headers=authed_headers)
        assert r.status_code == 402
        body = r.json()
        assert body["payment_required"] is True
        assert "amount_cspr" in body
        assert "payment_address" in body
        assert "expires_in_seconds" in body

    async def test_challenge_response_fast(self, client, authed_headers):
        start = time.monotonic()
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "timeout-entity", "type": "wallet"},
        )
        r = await client.get(
            "/api/v1/entity/timeout-entity/nrs", headers=authed_headers
        )
        elapsed = time.monotonic() - start
        assert r.status_code == 402
        assert elapsed < 2.0

    async def test_malformed_base64_proof_400(self, client, authed_headers):
        r = await client.get(
            "/api/v1/entity/ent-1/nrs",
            headers={**authed_headers, "X-Payment-Proof": "not-valid-base64!!"},
        )
        assert r.status_code == 400

    async def test_payment_verified_returns_nrs(self, client, authed_headers):
        import base64

        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "paid-entity", "type": "wallet"},
        )
        proof_b64 = base64.b64encode(b"a_valid_casper_deploy_hash").decode()
        r = await client.get(
            "/api/v1/entity/paid-entity/nrs",
            headers={**authed_headers, "X-Payment-Proof": proof_b64},
        )
        assert r.status_code == 200


# ===========================================================================
# ZK Proof (EP-02 F-02.1.2)
# ===========================================================================


class TestZKProve:
    """POST /api/v1/prove/{id}"""

    async def test_prove_response_shape(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "prove-1", "type": "wallet"},
        )
        with patch(
            "zkkyc.zk.proof._run_subprocess",
            new_callable=AsyncMock,
            return_value=(0, "", ""),
        ):
            r = await client.post(
                "/api/v1/prove/prove-1",
                headers=authed_headers,
                params={"threshold": 0.75, "chain": "stellar"},
            )
        assert r.status_code == 200
        body = r.json()
        for key in (
            "entity_hash",
            "nrs",
            "proof_generated",
            "verified",
            "chain_target",
        ):
            assert key in body
        assert body["proof_generated"] is True
        assert body["chain_target"] == "stellar"

    async def test_prove_hides_raw_entity_id(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "private-1", "type": "wallet"},
        )
        with patch(
            "zkkyc.zk.proof._run_subprocess",
            new_callable=AsyncMock,
            return_value=(0, "", ""),
        ):
            r = await client.post(
                "/api/v1/prove/private-1",
                headers=authed_headers,
            )
        body = r.json()
        assert body["entity_hash"] == "eh_private-1"
        assert "private-1" not in json.dumps(body)


# ===========================================================================
# Incidents (EP-01 F-01.3.1)
# ===========================================================================


class TestIncidents:
    """GET /api/v1/incidents — paginated, filterable by status."""

    async def test_empty_list(self, client, authed_headers):
        r = await client.get("/api/v1/incidents", headers=authed_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["limit"] == 20
        assert body["offset"] == 0

    async def test_default_pagination_fields(self, client, authed_headers):
        r = await client.get("/api/v1/incidents", headers=authed_headers)
        assert r.status_code == 200
        assert "limit" in r.json()
        assert "offset" in r.json()

    async def test_list_filter_by_status(self, client, authed_headers, app):
        repo = IncidentRepository(app.state.db)
        await repo.create("eh_i1", 0.95, 0.75, "PENDING_REVIEW")
        await repo.create("eh_i2", 0.85, 0.75, "REVIEWED")

        r = await client.get(
            "/api/v1/incidents?status=PENDING_REVIEW", headers=authed_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(i["status"] == "PENDING_REVIEW" for i in data["items"])

    async def test_pagination(self, client, authed_headers, app):
        repo = IncidentRepository(app.state.db)
        for i in range(5):
            await repo.create(f"eh_p{i}", 0.9, 0.75, "PENDING_REVIEW")

        r0 = await client.get(
            "/api/v1/incidents?limit=2&offset=0", headers=authed_headers
        )
        r1 = await client.get(
            "/api/v1/incidents?limit=2&offset=1", headers=authed_headers
        )
        assert len(r0.json()["items"]) == 2
        assert len(r1.json()["items"]) == 2


# ===========================================================================
# Risk Intelligence (EP-01 F-01.3.2, F-01.4.1, F-01.5.2)
# ===========================================================================


class TestRiskIntelligence:
    """GET /api/v1/entity/{id}/anomalies
       GET /api/v1/entity/{id}/factors
       GET /api/v1/entity/{id}/manifold"""

    async def test_anomalies_empty_when_none(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "anom-clean", "type": "wallet"},
        )
        r = await client.get(
            "/api/v1/entity/anom-clean/anomalies", headers=authed_headers
        )
        assert r.status_code == 200
        assert r.json()["anomalies"] == []

    async def test_anomalies_persists_flag(self, client, app, authed_headers):
        svc = app.state.entity_service
        svc.driver.session.return_value.__aenter__.return_value.run = AsyncMock(
            return_value=MagicMock(
                single=AsyncMock(return_value={"anomaly_type": "STRUCTURAL_ANOMALY"})
            )
        )
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "anom-flagged"},
        )
        r = await client.get(
            "/api/v1/entity/anom-flagged/anomalies", headers=authed_headers
        )
        assert r.status_code == 200
        assert "STRUCTURAL_ANOMALY" in r.json()["anomalies"]

    async def test_factors_returns_breakdown(self, client, authed_headers, app):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "fact-1", "type": "wallet"},
        )
        _patch_ci(app.state.ci_engine)
        r = await client.get(
            "/api/v1/entity/fact-1/factors", headers=authed_headers
        )
        assert r.status_code == 200
        for key in ("L", "C", "J", "S", "A", "B"):
            assert key in r.json()

    async def test_factors_persists_to_db(self, client, authed_headers, app):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "fact-db", "type": "wallet"},
        )
        _patch_ci(app.state.ci_engine)
        r = await client.get(
            "/api/v1/entity/fact-db/factors", headers=authed_headers
        )
        assert r.status_code == 200

        factors_repo = RiskFactorRepository(app.state.db)
        f = await factors_repo.get_latest("eh_fact-db")
        assert f is not None
        assert f["L"] == 0.1

    async def test_manifold_returns_cluster(self, client, authed_headers, app):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "man-1", "type": "wallet"},
        )
        _patch_ci(app.state.ci_engine)
        r = await client.get(
            "/api/v1/entity/man-1/manifold", headers=authed_headers
        )
        assert r.status_code == 200
        for key in ("cluster_label", "cluster_risk_level", "manifold_score"):
            assert key in r.json()


# ===========================================================================
# Casper Verdict Proxy (EP-04 US-03.1.3)
# ===========================================================================


class TestCasperVerdict:
    """GET /api/v1/casper/verdict/{hash}"""

    async def test_verdict_proxy_shape(self, client, authed_headers):
        r = await client.get(
            "/api/v1/casper/verdict/pass-abc123", headers=authed_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert "verdict" in body
        assert "expires_at" in body
        assert "status" in body

    async def test_pass_prefix_returns_true(self, client, authed_headers):
        r = await client.get(
            "/api/v1/casper/verdict/pass-tx", headers=authed_headers
        )
        assert r.json()["verdict"] is True

    async def test_valid_prefix_returns_true(self, client, authed_headers):
        r = await client.get(
            "/api/v1/casper/verdict/valid-tx", headers=authed_headers
        )
        assert r.json()["verdict"] is True

    async def test_negative_hash_returns_false(self, client, authed_headers):
        r = await client.get(
            "/api/v1/casper/verdict/other-hash", headers=authed_headers
        )
        assert r.json()["verdict"] is False

    async def test_cache_hit(self, client, authed_headers, app):
        repo = CasperVerdictCacheRepository(app.state.db)
        await repo.upsert("cached-h", True, 999, "VALID")
        r = await client.get(
            "/api/v1/casper/verdict/cached-h", headers=authed_headers
        )
        assert r.status_code == 200
        assert r.json()["verdict"] is True


# ===========================================================================
# Payment Summary (EP-05 US-04.2.3)
# ===========================================================================


class TestPaymentSummary:
    """GET /api/v1/payments/summary"""

    async def test_admin_required(self, client, authed_headers):
        r = await client.get("/api/v1/payments/summary", headers=authed_headers)
        assert r.status_code == 403

    async def test_empty_summary(self, client, admin_headers):
        r = await client.get("/api/v1/payments/summary", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert "days" in body
        assert "total_cspr" in body
        assert "total_count" in body


# ===========================================================================
# Compliance Credential (EP-02 F-02.2.3)
# ===========================================================================


class TestCredential:
    """GET /api/v1/entity/{id}/credential"""

    async def test_credential_generated_on_demand(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "cred-1", "type": "wallet"},
        )
        r = await client.get(
            "/api/v1/entity/cred-1/credential", headers=authed_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert "entity_hash" in body
        assert "threshold_public" in body
        assert "status" in body


# ===========================================================================
# Run trace and audit (EP-06, EP-07)
# ===========================================================================


class TestRunTrace:
    """GET /api/v1/runs/{run_id}"""

    async def test_get_run_state(self, client, authed_headers, app):
        repo = RunTraceRepository(app.state.db)
        await repo.save(state={"step": "done"}, entity_id="e-1", run_id="run-1")

        r = await client.get("/api/v1/runs/run-1", headers=authed_headers)
        assert r.status_code == 200
        assert r.json()["run_id"] == "run-1"

    async def test_get_run_state_404(self, client, authed_headers):
        r = await client.get("/api/v1/runs/missing", headers=authed_headers)
        assert r.status_code == 404


# ===========================================================================
# Admin endpoints (US-01.4.3, EP-07)
# ===========================================================================


class TestAdminRoutes:
    """POST /api/v1/admin/jurisdiction/refresh
       GET /api/v1/audit/{entity_hash}"""

    async def test_jurisdiction_refresh(self, client, admin_headers):
        r = await client.post(
            "/api/v1/admin/jurisdiction/refresh",
            headers=admin_headers,
            json={"updates": {"XX": 0.99}},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "refreshed"

    async def test_audit_admin_only(self, client, authed_headers):
        r = await client.get("/api/v1/audit/some-hash", headers=authed_headers)
        assert r.status_code == 403


# ===========================================================================
# Selective Disclosure (EP-03 F-03.2.2)
# ===========================================================================


class TestDisclosure:
    """POST /api/v1/entity/{entity_hash}/disclose"""

    async def test_disclose_requires_disclosure_key(self, client, authed_headers):
        await client.post(
            "/api/v1/entity",
            headers=authed_headers,
            json={"id": "disc-1", "type": "wallet"},
        )
        r = await client.post(
            "/api/v1/entity/disc-1/disclose",
            headers=authed_headers,
            json={"signature": "sig"},
        )
        assert r.status_code == 403

    async def test_disclose_with_key(self, client, app, authed_headers):
        db = app.state.db
        mapping_repo = EntityMappingRepository(db)
        await mapping_repo.put(entity_hash="eh-disc", raw_id="disc-1")

        headers = {**authed_headers, "X-Disclosure-Key": TEST_DISCLOSURE_KEY}
        r = await client.post(
            "/api/v1/entity/eh-disc/disclose",
            headers=headers,
            json={"signature": "sig-123"},
        )
        assert r.status_code == 200
        assert "factors" in r.json()
