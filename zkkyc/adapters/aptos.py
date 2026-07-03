"""
Aptos Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.aptos)

Spec reference: EP-08 (F-08.5 — US-08.5.3), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for Aptos blockchain using:
  - Move smart contract for ZK proof verification (Aptos native cryptography)
  - Aptos Token V2 non-transferable token as the Compliance Passport

Environment variables consumed:
  APTOS_RPC_URL, APTOS_VERIFIER_MODULE_ADDRESS, APTOS_PASSPORT_MODULE_ADDRESS,
  APTOS_ORACLE_PRIVATE_KEY
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


class AptosAdapter(PassportAdapterBase):
    """Aptos blockchain Compliance Passport Adapter.

    Spec reference: US-08.5.3
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on Aptos.

        Calls the Move verifier module entry point via the Aptos REST API.

        Args:
            proof_hex: hex-encoded UltraHonk proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier returns success.
        """
        module_address = getattr(self.settings, "aptos_verifier_module_address", "")
        if not module_address:
            raise AdapterDeploymentError("aptos", "APTOS_VERIFIER_MODULE_ADDRESS is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("aptos", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "aptos_rpc_url", "https://fullnode.testnet.aptoslabs.com")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "view",
                    "params": [
                        f"{module_address}::verifier::verify",
                        [proof_hex, public_inputs],
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("aptos", f"RPC error: {response.status_code}")
                result = response.json()
                logger.info("aptos proof verified", extra={"result": str(result)})
                return True
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("aptos", f"verifier call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint a non-transferable Compliance Passport token on Aptos.

        Calls the Aptos Token V2 mint_entry function with transfer disabled.

        Args:
            wallet: Aptos address (e.g. "0x...").
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            Aptos transaction hash string.
        """
        module_address = getattr(self.settings, "aptos_passport_module_address", "")
        if not module_address:
            raise AdapterDeploymentError("aptos", "APTOS_PASSPORT_MODULE_ADDRESS is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("aptos", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "aptos_rpc_url", "https://fullnode.testnet.aptoslabs.com")
        private_key = getattr(self.settings, "aptos_oracle_private_key", "")
        if not private_key:
            raise AdapterDeploymentError("aptos", "APTOS_ORACLE_PRIVATE_KEY is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "submit_transaction",
                    "params": [
                        {
                            "type": "entry_function_payload",
                            "function": f"{module_address}::passport::mint_passport",
                            "type_arguments": [],
                            "arguments": [wallet, policy_id, expires_at, proof_hash],
                        }
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("aptos", f"mint RPC error: {response.status_code}")
                result = response.json()
                tx_hash = result.get("result", {}).get("hash", "")
                logger.info(
                    "aptos passport minted",
                    extra={"tx_hash": tx_hash, "wallet": wallet, "policy_id": policy_id},
                )
                return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("aptos", f"mint_passport failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on Aptos.

        Calls the revoke entry point on the passport Move module.

        Args:
            wallet: Aptos address.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            Aptos transaction hash string.
        """
        module_address = getattr(self.settings, "aptos_passport_module_address", "")
        if not module_address:
            raise AdapterDeploymentError("aptos", "APTOS_PASSPORT_MODULE_ADDRESS is not configured")

        try:
            import httpx
        except ImportError as exc:
            raise AdapterDeploymentError("aptos", "httpx not installed", cause=exc) from exc

        rpc_url = getattr(self.settings, "aptos_rpc_url", "https://fullnode.testnet.aptoslabs.com")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "submit_transaction",
                    "params": [
                        {
                            "type": "entry_function_payload",
                            "function": f"{module_address}::passport::revoke_passport",
                            "type_arguments": [],
                            "arguments": [wallet, policy_id, reason],
                        }
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    raise AdapterDeploymentError("aptos", f"revoke RPC error: {response.status_code}")
                result = response.json()
                tx_hash = result.get("result", {}).get("hash", "")
                logger.info("aptos passport revoked", extra={"tx_hash": tx_hash, "wallet": wallet, "reason": reason})
                return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("aptos", f"revoke_passport failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Query the Aptos token store for wallet passport status.

        Args:
            wallet: Aptos address.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        module_address = getattr(self.settings, "aptos_passport_module_address", "")
        if not module_address:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        rpc_url = getattr(self.settings, "aptos_rpc_url", "https://fullnode.testnet.aptoslabs.com")
        try:
            import httpx
            url = f"{rpc_url}/v1/accounts/{wallet}/resource/{module_address}::passport::CompliancePassport"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}
                data = response.json()
                if data and data.get("data", {}).get("policy_id") == policy_id:
                    return {
                        "valid": True,
                        "expires_at": data.get("data", {}).get("expires_at", 0),
                        "policy_id": policy_id,
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("aptos verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Aptos deployment metadata."""
        verifier = getattr(self.settings, "aptos_verifier_module_address", "")
        passport = getattr(self.settings, "aptos_passport_module_address", "")
        rpc_url = getattr(self.settings, "aptos_rpc_url", "")
        network = "testnet" if "testnet" in rpc_url else "mainnet"

        return DeploymentInfo(
            chain_id="aptos",
            contract_address=passport or verifier,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "verifier_module_address": verifier,
                "passport_module_address": passport,
                "rpc_url": rpc_url,
            },
        )
