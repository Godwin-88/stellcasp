"""
Casper x402 micropayment gate — ZK-KYC Compliance Agent (zkkyc.payments.x402)

Spec reference: EP-04, F-04.2 (US-04.2.1, US-04.2.2, US-04.2.3)

PII note: this module deals in `entity_hash`, never a raw entity id — same
discipline as entity.py/nrs.py (US-06.1.2). Callers are expected to hash a
raw id before passing it in for audit logging.

Persistence note: `PaymentRepository` is an injection seam, not an
implementation. The real `payment_receipts` / `payment_failures` Postgres
tables aren't visible from this module. Without a repository configured,
replay protection degrades to in-memory-only (wiped on restart) and nothing
lands in the audit tables — this is logged loudly, not silently accepted.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class PaymentVerificationError(Exception):
    """Carries an HTTP status code so the route layer doesn't have to
    re-derive it from exception type via a chain of isinstance checks."""

    status_code = 402

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class PaymentReplayError(PaymentVerificationError):
    def __init__(self, message: str = "Payment proof already consumed"):
        super().__init__(message, status_code=409)


class PaymentPendingError(PaymentVerificationError):
    """CSPR.cloud unreachable. Per spec this is NOT a hard failure — the
    request should be treated as queued/retryable (HTTP 202), not rejected."""

    def __init__(self, message: str = "CSPR.cloud unreachable; payment verification queued for retry"):
        super().__init__(message, status_code=202)


class PaymentRepository(Protocol):
    """Injection seam for the real Postgres persistence layer. Implement
    against your actual `payment_receipts` / `payment_failures` tables."""

    async def is_deploy_consumed(self, deploy_hash: str) -> bool: ...

    async def record_receipt(
        self, deploy_hash: str, entity_hash: str | None, amount_cspr: float, api_key_id: str | None
    ) -> None: ...

    async def record_failure(self, deploy_hash: str, failure_reason: str, api_key_id: str | None) -> None: ...


class X402PaymentService:
    def __init__(
        self,
        repository: PaymentRepository | None = None,
        http_client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ):
        self.repository = repository
        self._http_client = http_client
        self.settings = settings or get_settings()
        # Fast pre-check cache only — NOT the source of truth for replay
        # protection. `repository.is_deploy_consumed` is, when configured.
        # Without a repository, this is the only protection there is, and
        # it does not survive a restart; that limitation is intentional to
        # surface rather than paper over.
        self._consumed_cache: set[str] = set()

    def create_payment_challenge(self) -> dict[str, Any]:
        """US-04.2.1. Synchronous and dependency-free on purpose — the
        spec's 500ms response budget leaves no room for an awaited call."""
        return {
            "payment_required": True,
            "amount_cspr": str(self.settings.x402_price_cspr),
            "payment_address": self.settings.casper_treasury_public_key,
            "expires_in_seconds": getattr(self.settings, "x402_challenge_expiry_seconds", 30),
        }

    async def verify_payment(
        self,
        deploy_hash: str,
        entity_hash: str | None = None,
        api_key_id: str | None = None,
        expected_amount: float | None = None,
    ) -> dict[str, Any]:
        expected_amount = (
            expected_amount if expected_amount is not None else float(self.settings.x402_price_cspr)
        )

        if deploy_hash in self._consumed_cache:
            raise PaymentReplayError()
        if self.repository is not None and await self.repository.is_deploy_consumed(deploy_hash):
            self._consumed_cache.add(deploy_hash)
            raise PaymentReplayError()

        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        owns_client = self._http_client is None
        try:
            try:
                response = await client.get(
                    "https://cspr.cloud/rpc/info_get_deploy",
                    params={"deploy_hash": deploy_hash},
                )
            except httpx.TimeoutException:
                logger.warning("CSPR.cloud timeout verifying deploy", extra={"deploy_hash": deploy_hash})
                raise PaymentPendingError()
            except httpx.HTTPError as exc:
                logger.warning(
                    "CSPR.cloud unreachable", extra={"deploy_hash": deploy_hash, "error": str(exc)}
                )
                raise PaymentPendingError()

            if response.status_code != 200:
                reason = f"CSPR.cloud returned HTTP {response.status_code}"
                await self._record_failure(deploy_hash, reason, api_key_id)
                raise PaymentVerificationError(reason, status_code=502)

            data = response.json()
        finally:
            if owns_client:
                await client.aclose()

        # CAVEAT: a Casper deploy's JSON shape differs between a native
        # transfer and a contract call, and the transfer amount/target may
        # not live at `deploy.payment.{amount,target}` for every deploy
        # type CSPR.cloud can return. This mirrors the shape assumed by the
        # original implementation — verify it against a real CSPR.cloud
        # testnet response before relying on it for the demo; a wrong path
        # here means every payment silently fails "Insufficient payment
        # amount" rather than a null/attribute error.
        deploy = data.get("deploy", {})
        amount = float(deploy.get("payment", {}).get("amount", 0))
        target = deploy.get("payment", {}).get("target", "")

        if amount < expected_amount:
            reason = "Insufficient payment amount"
            await self._record_failure(deploy_hash, reason, api_key_id)
            raise PaymentVerificationError(reason, status_code=402)

        if target != self.settings.casper_treasury_public_key:
            reason = "Payment target mismatch"
            await self._record_failure(deploy_hash, reason, api_key_id)
            raise PaymentVerificationError(reason, status_code=402)

        self._consumed_cache.add(deploy_hash)
        if self.repository is not None:
            await self.repository.record_receipt(
                deploy_hash=deploy_hash,
                entity_hash=entity_hash,
                amount_cspr=amount,
                api_key_id=api_key_id,
            )
        else:
            logger.error(
                "PaymentRepository not configured — payment verified but NOT recorded to payment_receipts",
                extra={"deploy_hash": deploy_hash, "amount_cspr": amount},
            )

        return {"deploy_hash": deploy_hash, "amount_cspr": amount, "verified": True}

    async def _record_failure(self, deploy_hash: str, reason: str, api_key_id: str | None) -> None:
        logger.warning("payment verification failed", extra={"deploy_hash": deploy_hash, "reason": reason})
        if self.repository is not None:
            await self.repository.record_failure(deploy_hash, reason, api_key_id)