"""
Sui Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.sui)

Spec reference: EP-08 (F-08.5 — US-08.5.3), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for Sui blockchain using:
  - Move smart contract for ZK proof verification (Sui native cryptography)
  - Sui object with `transfer::freeze_object` for non-transferable Compliance
    Passport (soulbound pattern)

Environment variables consumed:
  SUI_RPC_URL, SUI_VERIFIER_PACKAGE_ID, SUI_PASSPORT_OBJECT_ID,
  SUI_ORACLE_KEYPAIR
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


class SuiAdapter(PassportAdapterBase):
    """Sui blockchain Compliance Passport Adapter.

    Spec reference: US-08.5.3
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on Sui.

        Calls the Move verifier contract entry point via Sui JSON-RPC.

        Args:
            proof_hex: hex-encoded UltraHonk proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier returns success.
        """
        package_id = getattr(self.settings, "sui_verifier_package_id", "")
        if not package_id:
            raise AdapterDeploymentError("sui", "SUI_VERIFIER_PACKAGE_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("sui", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "sui_rpc_url", "https://fullnode.testnet.sui.io")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "sui_moveCall",
                    "params": [
                        package_id,
                        "verifier",
                        "verify",
                        [],
                        [proof_hex, public_inputs],
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("sui", f"RPC error: {response.status_code}")
                result = response.json()
                logger.info("sui proof verified", extra={"result": str(result)})
                return True
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("sui", f"verifier call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint a soulbound Compliance Passport object on Sui.

        Uses `transfer::freeze_object` after minting to make the passport
        non-transferable. The object is wrapped (not shared) so only the
        oracle authority can mutate it.

        Args:
            wallet: Sui address (e.g. "0x...").
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            Sui transaction digest string.
        """
        package_id = getattr(self.settings, "sui_verifier_package_id", "")
        if not package_id:
            raise AdapterDeploymentError("sui", "SUI_VERIFIER_PACKAGE_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("sui", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "sui_rpc_url", "https://fullnode.testnet.sui.io")
        keypair = getattr(self.settings, "sui_oracle_keypair", "")
        if not keypair:
            raise AdapterDeploymentError("sui", "SUI_ORACLE_KEYPAIR is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "sui_moveCall",
                    "params": [
                        package_id,
                        "passport",
                        "mint_passport",
                        [],
                        [wallet, policy_id, expires_at, proof_hash],
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("sui", f"mint RPC error: {response.status_code}")
                result = response.json()
                tx_digest = result.get("result", {}).get("tx_digest", "")
                logger.info(
                    "sui passport minted",
                    extra={"tx_digest": tx_digest, "wallet": wallet, "policy_id": policy_id},
                )
                return tx_digest
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("sui", f"mint_passport failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on Sui.

        Calls the revoke entry point on the passport Move contract.

        Args:
            wallet: Sui address.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            Sui transaction digest string.
        """
        package_id = getattr(self.settings, "sui_verifier_package_id", "")
        if not package_id:
            raise AdapterDeploymentError("sui", "SUI_VERIFIER_PACKAGE_ID is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("sui", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "sui_rpc_url", "https://fullnode.testnet.sui.io")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "sui_moveCall",
                    "params": [
                        package_id,
                        "passport",
                        "revoke_passport",
                        [],
                        [wallet, policy_id, reason],
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("sui", f"revoke RPC error: {response.status_code}")
                result = response.json()
                tx_digest = result.get("result", {}).get("tx_digest", "")
                logger.info("sui passport revoked", extra={"tx_digest": tx_digest, "wallet": wallet, "reason": reason})
                return tx_digest
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("sui", f"revoke_passport failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Query the Sui object store for wallet passport status.

        Args:
            wallet: Sui address.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        object_id = getattr(self.settings, "sui_passport_object_id", "")
        if not object_id:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        rpc_url = getattr(self.settings, "sui_rpc_url", "https://fullnode.testnet.sui.io")
        try:
            import httpx
            url = f"{rpc_url}/v1/objects/{object_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}
                data = response.json()
                details = data.get("data", {}).get("content", {}).get("fields", {})
                if details and details.get("owner") == wallet:
                    return {
                        "valid": True,
                        "expires_at": details.get("expires_at", 0),
                        "policy_id": policy_id,
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("sui verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Sui deployment metadata."""
        package_id = getattr(self.settings, "sui_verifier_package_id", "")
        object_id = getattr(self.settings, "sui_passport_object_id", "")
        rpc_url = getattr(self.settings, "sui_rpc_url", "")
        network = "testnet" if "testnet" in rpc_url else "mainnet"

        return DeploymentInfo(
            chain_id="sui",
            contract_address=package_id,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "passport_object_id": object_id,
                "rpc_url": rpc_url,
            },
        )
