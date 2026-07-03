"""
Algorand Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.algorand)

Spec reference: EP-08 (F-08.5 — US-08.5.2), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for Algorand using:
  - PyTeal/Beaker smart contract for ZK proof verification (AVM ZK support)
  - Algorand Standard Asset (ASA) with clawback as the Compliance Passport,
    where the oracle authority is the manager and clawback enables revocation

Environment variables consumed:
  ALGORAND_NODE_URL, ALGORAND_INDEXER_URL, ALGORAND_VERIFIER_APP_ID,
  ALGORAND_PASSPORT_ASA_ID, ALGORAND_ORACLE_PRIVATE_KEY
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


class AlgorandAdapter(PassportAdapterBase):
    """Algorand Compliance Passport Adapter.

    Spec reference: US-08.5.2
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on Algorand.

        Calls the deployed PyTeal verifier application via the Algorand
        node REST API. The application returns a boolean result.

        Args:
            proof_hex: hex-encoded UltraHonk proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier application returns success.
        """
        app_id = getattr(self.settings, "algorand_verifier_app_id", 0)
        if not app_id:
            raise AdapterDeploymentError("algorand", "ALGORAND_VERIFIER_APP_ID is not configured")

        try:
            from algosdk import algod
        except ImportError as exc:
            raise AdapterDeploymentError(
                "algorand", "py-algorand-sdk not installed; run: pip install py-algorand-sdk", cause=exc
            ) from exc

        node_url = getattr(self.settings, "algorand_node_url", "https://testnet-api.algonode.cloud")
        try:
            client = algod.AlgodClient("", node_url)
            proof_bytes = bytes.fromhex(proof_hex)
            result = client.app_abi_call(
                app_id,
                method_signature="verify(byte[], uint64[])bool",
                method_args=[proof_bytes, public_inputs],
            )
            logger.info("algorand proof verified", extra={"valid": result, "app_id": app_id})
            return bool(result.get("return-value", False))
        except Exception as exc:
            raise AdapterDeploymentError("algorand", f"verifier app call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint an ASA Compliance Passport for `wallet`.

        Calls the Algorand Asset Config transaction to opt-in the wallet
        to the Compliance Passport ASA and records the mint on-chain.

        Args:
            wallet: Algorand address (e.g. "ABCD...").
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            Algorand transaction ID string.
        """
        asa_id = getattr(self.settings, "algorand_passport_asa_id", 0)
        if not asa_id:
            raise AdapterDeploymentError("algorand", "ALGORAND_PASSPORT_ASA_ID is not configured")

        try:
            from algosdk import algod, transaction, account
        except ImportError as exc:
            raise AdapterDeploymentError("algorand", "py-algorand-sdk not installed", cause=exc) from exc

        node_url = getattr(self.settings, "algorand_node_url", "https://testnet-api.algonode.cloud")
        private_key = getattr(self.settings, "algorand_oracle_private_key", "")
        if not private_key:
            raise AdapterDeploymentError("algorand", "ALGORAND_ORACLE_PRIVATE_KEY is not configured")

        try:
            client = algod.AlgodClient("", node_url)
            sender = account.address_from_private_key(private_key)

            txn = transaction.AssetTransferTxn(
                sender=sender,
                receiver=wallet,
                amt=1,
                index=asa_id,
                revocation_target=wallet,
                note=policy_id.encode()[:32],
            )
            signed = txn.sign(private_key)
            txid = client.send_transaction(signed)
            transaction.wait_for_confirmation(client, txid, 4)

            logger.info(
                "algorand passport minted",
                extra={"txid": txid, "wallet": wallet, "asa_id": asa_id},
            )
            return txid
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("algorand", f"ASA mint failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on Algorand.

        Uses the ASA clawback feature to revoke the token from the wallet.

        Args:
            wallet: Algorand address.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            Algorand transaction ID string.
        """
        asa_id = getattr(self.settings, "algorand_passport_asa_id", 0)
        if not asa_id:
            raise AdapterDeploymentError("algorand", "ALGORAND_PASSPORT_ASA_ID is not configured")

        try:
            from algosdk import algod, transaction, account
        except ImportError as exc:
            raise AdapterDeploymentError("algorand", "py-algorand-sdk not installed", cause=exc) from exc

        node_url = getattr(self.settings, "algorand_node_url", "https://testnet-api.algonode.cloud")
        private_key = getattr(self.settings, "algorand_oracle_private_key", "")
        if not private_key:
            raise AdapterDeploymentError("algorand", "ALGORAND_ORACLE_PRIVATE_KEY is not configured")

        try:
            client = algod.AlgodClient("", node_url)
            sender = account.address_from_private_key(private_key)
            txn = transaction.AssetTransferTxn(
                sender=sender,
                receiver=sender,
                amt=1,
                index=asa_id,
                revocation_target=wallet,
            )
            signed = txn.sign(private_key)
            txid = client.send_transaction(signed)
            transaction.wait_for_confirmation(client, txid, 4)

            logger.info("algorand passport revoked", extra={"txid": txid, "wallet": wallet, "reason": reason})
            return txid
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("algorand", f"ASA clawback failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Check if `wallet` holds a valid Compliance Passport ASA.

        Queries the Algorand Indexer for the wallet's ASA balance.

        Args:
            wallet: Algorand address.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        asa_id = getattr(self.settings, "algorand_passport_asa_id", 0)
        if not asa_id:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        indexer_url = getattr(self.settings, "algorand_indexer_url", "https://testnet-idx.algonode.cloud")
        try:
            import httpx
            url = f"{indexer_url}/v2/accounts/{wallet}/assets/{asa_id}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}
                data = response.json()
                balance = data.get("balance", 0)
                if balance > 0:
                    return {
                        "valid": True,
                        "expires_at": 0,
                        "policy_id": policy_id,
                        "extra": {"balance": balance},
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("algorand verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Algorand deployment metadata."""
        app_id = getattr(self.settings, "algorand_verifier_app_id", 0)
        asa_id = getattr(self.settings, "algorand_passport_asa_id", 0)
        node_url = getattr(self.settings, "algorand_node_url", "")
        network = "testnet" if "testnet" in node_url else "mainnet"

        return DeploymentInfo(
            chain_id="algorand",
            contract_address=str(app_id),
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "verifier_app_id": app_id,
                "passport_asa_id": asa_id,
                "node_url": node_url,
            },
        )
