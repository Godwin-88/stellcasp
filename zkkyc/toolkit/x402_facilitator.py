"""
Official Casper x402 Facilitator client — ZK-KYC Compliance Agent (zkkyc.toolkit.x402_facilitator)

Wraps the official `casper-x402` facilitator service (github.com/make-software/casper-x402)
so the FastAPI gateway delegates challenge generation and payment verification to the
ecosystem reference implementation instead of bespoke logic.

Spec reference: EP-05 augmentation (official x402 facilitator)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class X402FacilitatorError(Exception):
    status_code = 502

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class X402Facilitator:
    """Client for the official Casper x402 Facilitator service.

    The facilitator handles:
      - POST /challenge — generate a 402 payment challenge
      - POST /verify — verify a payment proof and settle
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.settings = settings or get_settings()
        self._client = http_client or httpx.Client(timeout=10.0)
        self._owns_client = http_client is None

    def create_payment_challenge(self, resource: str = "/api/v1/entity/{id}/nrs") -> dict[str, Any]:
        """Return a 402 challenge dict matching the x402 facilitator schema.

        If the facilitator is unreachable, falls back to the platform's own
        challenge shape so the endpoint never returns a 500.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/challenge",
                json={
                    "resource": resource,
                    "amount": str(self.settings.x402_price_cspr),
                    "network": "casper-test",
                    "payment_address": self.settings.casper_treasury_public_key,
                    "expires_in_seconds": getattr(self.settings, "x402_challenge_expiry_seconds", 30),
                },
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, Exception) as exc:
            logger.warning("x402 facilitator unreachable; using local fallback: %s", exc)
            return {
                "payment_required": True,
                "amount_cspr": str(self.settings.x402_price_cspr),
                "payment_address": self.settings.casper_treasury_public_key,
                "expires_in_seconds": getattr(self.settings, "x402_challenge_expiry_seconds", 30),
                "network": "casper-test",
                "resource": resource,
                "facilitator_fallback": True,
            }

    def verify_payment(
        self,
        deploy_hash: str,
        entity_hash: str | None = None,
        api_key_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify a payment proof via the facilitator.

        Returns a dict with at least `{verified: bool, amount_cspr: float}`.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/verify",
                json={
                    "deploy_hash": deploy_hash,
                    "expected_amount": str(self.settings.x402_price_cspr),
                    "destination": self.settings.casper_treasury_public_key,
                    "network": "casper-test",
                    "entity_hash": entity_hash,
                    "api_key_id": api_key_id,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "verified": data.get("verified", False),
                "deploy_hash": deploy_hash,
                "amount_cspr": float(data.get("amount_cspr", 0)),
            }
        except httpx.HTTPStatusError as exc:
            body = exc.response.text if exc.response else ""
            logger.error("x402 facilitator verify failed: %s — %s", exc.response.status_code, body)
            raise X402FacilitatorError(
                f"x402 facilitator returned HTTP {exc.response.status_code}: {body}",
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("x402 facilitator unreachable during verify: %s", exc)
            raise X402FacilitatorError(
                "x402 facilitator unreachable; payment verification queued for retry",
                status_code=202,
            ) from exc

    def close(self) -> None:
        if self._owns_client:
            try:
                self._client.close()
            except Exception:
                pass

    def __enter__(self) -> X402Facilitator:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
