"""
ICP / DFINITY Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.icp)

Spec reference: EP-08 (F-08.5 — US-08.5.3), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for ICP / DFINITY using:
  - Canister-based ZK verifier (ic-verify-bls-signature or custom canister)
  - Internet Identity-linked Compliance Passport credential stored as a
    canister record keyed by wallet principal

Environment variables consumed:
  ICP_CANISTER_URL, ICP_VERIFIER_CANISTER_ID, ICP_PASSPORT_CANISTER_ID,
  ICP_IDENTITY_PRINCIPAL
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..config import Settings, get_settings
from .base import (
    AdapterDeploymentError,
    DeploymentInfo,
    PassportAdapterBase,
)

logger = logging.getLogger(__name__)


class ICPAdapter(PassportAdapterBase):
    """ICP / DFINITY Compliance Passport Adapter.

    Spec reference: US-08.5.3
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on ICP.

        Calls the deployed verifier canister via the ICP HTTP API.

        Args:
            proof_hex: hex-encoded UltraHonk proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier canister returns success.
        """
        canister_id = getattr(self.settings, "icp_verifier_canister_id", "")
        if not canister_id:
            raise AdapterDeploymentError("icp", "ICP_VERIFIER_CANISTER_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("icp", "httpx not installed", cause=exc) from exc

        canister_url = getattr(self.settings, "icp_canister_url", "")
        if not canister_url:
            raise AdapterDeploymentError("icp", "ICP_CANISTER_URL is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{canister_url}/v2/verify",
                    json={"proof": proof_hex, "public_inputs": public_inputs},
                )
                if response.status_code != 200:
                    raise AdapterDeploymentError("icp", f"canister error: {response.status_code}")
                result = response.json()
                logger.info("icp proof verified", extra={"valid": result.get("valid"), "canister": canister_id})
                return bool(result.get("valid", False))
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("icp", f"verifier canister call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint an Internet Identity-linked Compliance Passport on ICP.

        Stores a passport record in the passport canister keyed by the
        wallet's principal.

        Args:
            wallet: ICP principal string (e.g. "rrkah-fqaaa-...").
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            ICP transaction hash / request ID string.
        """
        canister_id = getattr(self.settings, "icp_passport_canister_id", "")
        if not canister_id:
            raise AdapterDeploymentError("icp", "ICP_PASSPORT_CANISTER_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("icp", "httpx not installed", cause=exc) from exc

        canister_url = getattr(self.settings, "icp_canister_url", "")
        if not canister_url:
            raise AdapterDeploymentError("icp", "ICP_CANISTER_URL is not configured")

        identity_principal = getattr(self.settings, "icp_identity_principal", "")
        if not identity_principal:
            raise AdapterDeploymentError("icp", "ICP_IDENTITY_PRINCIPAL is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{canister_url}/v2/mint_passport",
                    json={
                        "wallet": wallet,
                        "policy_id": policy_id,
                        "expires_at": expires_at,
                        "proof_hash": proof_hash,
                        "identity_principal": identity_principal,
                    },
                )
                if response.status_code != 200:
                    raise AdapterDeploymentError("icp", f"mint canister error: {response.status_code}")
                result = response.json()
                tx_hash = result.get("tx_hash", "")
                logger.info(
                    "icp passport minted",
                    extra={"tx_hash": tx_hash, "wallet": wallet, "policy_id": policy_id},
                )
                return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("icp", f"mint_passport failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on ICP.

        Calls the revoke entry point on the passport canister.

        Args:
            wallet: ICP principal string.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            ICP transaction hash / request ID string.
        """
        canister_id = getattr(self.settings, "icp_passport_canister_id", "")
        if not canister_id:
            raise AdapterDeploymentError("icp", "ICP_PASSPORT_CANISTER_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("icp", "httpx not installed", cause=exc) from exc

        canister_url = getattr(self.settings, "icp_canister_url", "")
        if not canister_url:
            raise AdapterDeploymentError("icp", "ICP_CANISTER_URL is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{canister_url}/v2/revoke_passport",
                    json={"wallet": wallet, "policy_id": policy_id, "reason": reason},
                )
                if response.status_code != 200:
                    raise AdapterDeploymentError("icp", f"revoke canister error: {response.status_code}")
                result = response.json()
                tx_hash = result.get("tx_hash", "")
                logger.info("icp passport revoked", extra={"tx_hash": tx_hash, "wallet": wallet, "reason": reason})
                return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("icp", f"revoke_passport failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Query the ICP passport canister for wallet status.

        Args:
            wallet: ICP principal string.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        canister_id = getattr(self.settings, "icp_passport_canister_id", "")
        if not canister_id:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        canister_url = getattr(self.settings, "icp_canister_url", "")
        if not canister_url:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        try:
            import httpx
            url = f"{canister_url}/v2/get_passport"
            params = {"wallet": wallet, "policy_id": policy_id}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}
                data = response.json()
                if data and data.get("policy_id") == policy_id:
                    return {
                        "valid": True,
                        "expires_at": data.get("expires_at", 0),
                        "policy_id": policy_id,
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("icp verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return ICP deployment metadata."""
        verifier = getattr(self.settings, "icp_verifier_canister_id", "")
        passport = getattr(self.settings, "icp_passport_canister_id", "")
        canister_url = getattr(self.settings, "icp_canister_url", "")
        network = "mainnet" if canister_url and "ic0.app" in canister_url else "testnet"

        return DeploymentInfo(
            chain_id="icp",
            contract_address=passport or verifier,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "verifier_canister_id": verifier,
                "passport_canister_id": passport,
                "canister_url": canister_url,
            },
        )
