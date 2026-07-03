"""
Pydantic request/response schemas for the FastAPI gateway.

Spec reference: EP-04, EP-05, EP-02, EP-03, EP-01, EP-06, EP-07
US-04.1.1, US-04.1.3, US-04.2.3, US-02.2.3, US-03.1.3, US-03.2.2,
US-01.2.3, US-01.3.1, US-01.3.2, US-01.4.1, US-01.4.3, US-01.5.2
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Admin — API Key Management (US-04.1.1, US-04.1.3)
# --------------------------------------------------------------------------- #

class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable key label")
    rate_limit: int = Field(default=60, ge=1, le=600, description="Requests per minute")


class APIKeyCreateResponse(BaseModel):
    key_id: str
    plaintext_key: str
    name: str
    rate_limit: int
    created_at: datetime


class APIKeyLimitUpdate(BaseModel):
    rate_limit: int = Field(..., ge=1, le=600, description="New per-minute limit")


# --------------------------------------------------------------------------- #
# Payments (US-04.2.3)
# --------------------------------------------------------------------------- #

class PaymentSummaryDay(BaseModel):
    date: str
    count: int
    total_cspr: float


class PaymentSummaryResponse(BaseModel):
    days: list[PaymentSummaryDay]
    total_cspr: float
    total_count: int


# --------------------------------------------------------------------------- #
# Incidents (US-01.3.1)
# --------------------------------------------------------------------------- #

class IncidentResponse(BaseModel):
    incident_id: str
    entity_hash: str
    ci: float
    threshold: float
    status: str
    webhook_status: str | None = None
    created_at: datetime


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    limit: int
    offset: int
    total: int


# --------------------------------------------------------------------------- #
# Graph / Risk Intelligence (US-01.4.1, US-01.5.2)
# --------------------------------------------------------------------------- #

class FactorResponse(BaseModel):
    L: float
    C: float
    J: float
    S: float
    A: float
    B: float
    B_is_stub: bool = True


class ManifoldResponse(BaseModel):
    cluster_label: int
    cluster_risk_level: int
    manifold_score: float


# --------------------------------------------------------------------------- #
# Credential / Verification (US-02.2.3)
# --------------------------------------------------------------------------- #

class CredentialResponse(BaseModel):
    stellar_tx_hash: str | None
    entity_hash: str
    threshold_public: float
    verified_at: datetime
    proof_hex: str | None = None
    status: str = "VALID"


# --------------------------------------------------------------------------- #
# Casper Verdict Proxy (US-03.1.3)
# --------------------------------------------------------------------------- #

class CasperVerdictResponse(BaseModel):
    verdict: bool | None
    expires_at: int
    status: str


# --------------------------------------------------------------------------- #
# Audit (EP-06, EP-07)
# --------------------------------------------------------------------------- #

class AuditResponse(BaseModel):
    entity_hash: str
    nrs_history: list[dict[str, Any]]
    proof_events: list[dict[str, Any]]
    on_chain_records: list[dict[str, Any]]


# --------------------------------------------------------------------------- #
# Selective Disclosure (US-03.2.2)
# --------------------------------------------------------------------------- #

class DiscloseRequest(BaseModel):
    institution: str = Field(default="", description="Requesting institution name")
    signature: str = Field(..., min_length=1, description="Signed disclosure request")
    factors: list[str] = Field(default_factory=list, description="Requested factor labels")


class DiscloseResponse(BaseModel):
    factors: list[str]


# --------------------------------------------------------------------------- #
# Jurisdiction Refresh (US-01.4.3)
# --------------------------------------------------------------------------- #

class JurisdictionRefreshRequest(BaseModel):
    updates: dict[str, float] = Field(
        ...,
        description="Map of ISO-2 country codes to new risk scores in [0.0, 1.0]",
    )


# --------------------------------------------------------------------------- #
# Run Trace (EP-06)
# --------------------------------------------------------------------------- #

class RunStateResponse(BaseModel):
    run_id: str
    entity_id: str
    state: dict[str, Any]
    created_at: datetime
