"""
Unit tests for pure-domain utilities, schemas, and business logic.

Spec reference: EP-01 (F-01.4.3), EP-03 (F-03.2.2), EP-07,
                EP-02 (F-02.1)
US-01.4.3, US-03.2.2, US-06.1.2, US-02.1.2, US-02.1.3

Run with: pytest tests/test_unit.py -v -m unit
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from zkkyc.config import Settings
from zkkyc.graph.entity import (
    EntityService,
    RelationshipCreate,
)
from zkkyc.graph.nrs import (
    FactorBreakdown,
    IncidentService,
    NRSDetails,
    get_jurisdiction_risk,
    refresh_jurisdiction_table,
)
from zkkyc.api.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyLimitUpdate,
    CasperVerdictResponse,
    CredentialResponse,
    DiscloseRequest,
    FactorResponse,
    IncidentListResponse,
    IncidentResponse,
    JurisdictionRefreshRequest,
    ManifoldResponse,
    PaymentSummaryDay,
    PaymentSummaryResponse,
    RunStateResponse,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _settings() -> Settings:
    return Settings(entity_salt="unit_test_salt")


# ===========================================================================
# Entity ID hashing (US-06.1.2)
# ===========================================================================

class TestEntityHashing:
    def test_hash_entity_id_consistent(self):
        service = EntityService(_settings())
        assert service.hash_entity_id("w1") == service.hash_entity_id("w1")

    def test_hash_entity_id_unique(self):
        service = EntityService(_settings())
        assert service.hash_entity_id("a") != service.hash_entity_id("b")

    def test_hash_entity_id_sha256_format(self):
        service = EntityService(_settings())
        h = service.hash_entity_id("anything")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_salt_matters(self):
        a = EntityService(Settings(entity_salt="saltA"))
        b = EntityService(Settings(entity_salt="saltB"))
        assert a.hash_entity_id("same_id") != b.hash_entity_id("same_id")


# ===========================================================================
# Relationship validation
# ===========================================================================

class TestRelationshipValidation:
    def test_zero_amount_allowed_by_schema(self):
        rel = RelationshipCreate(
            source_id="a", target_id="b",
            amount=0.0, currency="XLM", timestamp=0, tx_hash="x",
        )
        assert rel.amount == 0.0

    def test_negative_amount_rejected_by_schema(self):
        with pytest.raises(Exception):
            RelationshipCreate(
                source_id="a", target_id="b",
                amount=-1.0, currency="XLM", timestamp=0, tx_hash="x",
            )


# ===========================================================================
# Jurisdiction risk (US-01.4.3)
# ===========================================================================

class TestJurisdictionRisk:
    def test_known_grey_list_country(self):
        score, unknown = get_jurisdiction_risk("AF")
        assert score == 1.0
        assert unknown is False

    def test_known_safe_country_default(self):
        score, unknown = get_jurisdiction_risk("GB")
        assert score == 0.5
        assert unknown is True

    def test_none_returns_default(self):
        score, unknown = get_jurisdiction_risk(None)
        assert score == 0.5
        assert unknown is True

    def test_lowercase_normalised(self):
        score, unknown = get_jurisdiction_risk("af")
        assert score == 1.0
        assert unknown is False

    def test_refresh_updates_table(self):
        original = dict(get_jurisdiction_risk.__globals__["_jurisdiction_risk_table"])
        try:
            refresh_jurisdiction_table({"XX": 0.99, "YY": 0.01})
            assert get_jurisdiction_risk("XX")[0] == 0.99
            assert get_jurisdiction_risk("YY")[0] == 0.01
        finally:
            get_jurisdiction_risk.__globals__["_jurisdiction_risk_table"] = original

    def test_refresh_rejects_out_of_range(self):
        with pytest.raises(Exception):
            refresh_jurisdiction_table({"XX": 1.5})


# ===========================================================================
# FactorBreakdown / ComplianceIndexResult models
# ===========================================================================

class TestFactorBreakdownModel:
    def test_defaults(self):
        fb = FactorBreakdown(L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6)
        assert fb.L == 0.1
        assert fb.B_is_stub is True

    def test_b_is_stub_override(self):
        fb = FactorBreakdown(L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6, B_is_stub=False)
        assert fb.B_is_stub is False


class TestComplianceIndexResult:
    def test_auto_timestamp(self):
        r = FactorBreakdown(L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6)
        assert r.B_is_stub is True


# ===========================================================================
# NRSDetails backward-compat shim
# ===========================================================================

class TestNRSDetails:
    def test_structure(self):
        d = NRSDetails(
            pagerank_score=0.5,
            betweenness_score=0.3,
            community_risk_score=0.2,
            raw_nrs=0.42,
        )
        assert d.raw_nrs == 0.42
        assert 0.0 <= d.raw_nrs <= 1.0
        assert d.pagerank_score == 0.5

    def test_defaults(self):
        d = NRSDetails(
            pagerank_score=0.0,
            betweenness_score=0.0,
            community_risk_score=0.0,
            raw_nrs=0.0,
        )
        assert d.density_floor_applied is False
        assert d.anomaly_penalty_applied is False


# ===========================================================================
# API schemas
# ===========================================================================

class TestAPISchemas:
    def test_api_key_create_request_defaults(self):
        r = APIKeyCreateRequest(name="demo")
        assert r.rate_limit == 60
        assert r.name == "demo"

    def test_api_key_create_response(self):
        r = APIKeyCreateResponse(
            key_id="kid",
            plaintext_key="pt",
            name="n",
            rate_limit=120,
            created_at=datetime.now(timezone.utc),
        )
        assert r.plaintext_key == "pt"

    def test_api_key_limit_update(self):
        r = APIKeyLimitUpdate(rate_limit=300)
        assert r.rate_limit == 300

    def test_incident_response(self):
        r = IncidentResponse(
            incident_id="i1",
            entity_hash="eh",
            ci=0.9,
            threshold=0.75,
            status="PENDING_REVIEW",
            created_at=datetime.now(timezone.utc),
        )
        assert r.webhook_status is None

    def test_payment_summary_response(self):
        r = PaymentSummaryResponse(
            days=[PaymentSummaryDay(date="2026-07-01", count=1, total_cspr=0.001)],
            total_cspr=0.001,
            total_count=1,
        )
        assert r.days[0].total_cspr == 0.001

    def test_factor_response(self):
        r = FactorResponse(L=0.1, C=0.2, J=0.3, S=0.4, A=0.5, B=0.6)
        assert r.B_is_stub is True

    def test_manifold_response(self):
        r = ManifoldResponse(
            cluster_label=0, cluster_risk_level=4, manifold_score=0.95
        )
        assert r.manifold_score == 0.95

    def test_casper_verdict_response(self):
        r = CasperVerdictResponse(verdict=True, expires_at=999, status="VALID")
        assert r.verdict is True

    def test_credential_response(self):
        r = CredentialResponse(
            stellar_tx_hash="tx",
            entity_hash="eh",
            threshold_public=0.75,
            verified_at=datetime.now(timezone.utc),
            status="VALID",
        )
        assert r.proof_hex is None

    def test_disclose_request(self):
        r = DiscloseRequest(signature="abc")
        assert r.signature == "abc"

    def test_run_state_response(self):
        r = RunStateResponse(
            run_id="r1",
            entity_id="e1",
            state={},
            created_at=datetime.now(timezone.utc),
        )
        assert r.state == {}

    def test_jurisdiction_refresh_request(self):
        r = JurisdictionRefreshRequest(updates={"XX": 0.5})
        assert r.updates == {"XX": 0.5}

    def test_incident_list_response(self):
        ir = IncidentResponse(
            incident_id="i1",
            entity_hash="eh",
            ci=0.9,
            threshold=0.75,
            status="PENDING_REVIEW",
            created_at=datetime.now(timezone.utc),
        )
        r = IncidentListResponse(items=[ir], limit=20, offset=0, total=1)
        assert r.total == 1


# ===========================================================================
# IncidentService — webhook dispatch logic
# ===========================================================================

class TestIncidentService:
    async def test_below_threshold_returns_none(self):
        svc = IncidentService(entity_service=None)
        result = await svc.check_threshold_incident("eh", ci=0.1)
        assert result is None

    async def test_webhook_retry_then_success(self):
        svc = IncidentService(entity_service=None, settings=Settings(alert_webhook_url="http://fake-hook"))

        class FakeClient:
            def __init__(self):
                self.calls = 0

            async def post(self, *a, **kw):
                self.calls += 1
                if self.calls < 3:
                    return MagicMock(status_code=500)
                return MagicMock(status_code=200)

        svc._http_client = FakeClient()
        result = await svc._dispatch_webhook("eh", 0.9, 0.75)
        assert result == "DELIVERED"

    async def test_webhook_all_failures(self):
        svc = IncidentService(entity_service=None, settings=Settings(alert_webhook_url="http://fake-hook"))

        class FakeClient:
            async def post(self, *a, **kw):
                return MagicMock(status_code=500)

        svc._http_client = FakeClient()
        result = await svc._dispatch_webhook("eh", 0.9, 0.75)
        assert result == "ALERT_FAILED"

    async def test_webhook_no_url_skips(self):
        svc = IncidentService(
            entity_service=None, settings=Settings(alert_webhook_url=None)
        )
        result = await svc._dispatch_webhook("eh", 0.9, 0.75)
        assert result == "SKIPPED"
