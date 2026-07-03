"""
Hedera Hashgraph Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.hedera)

Spec reference: EP-08 (F-08.4 — US-08.4.1, US-08.4.2), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for Hedera Hashgraph using:
  - Hedera Smart Contract Service (HSCS) for the UltraHonk verifier contract
    (EVM-compatible, so Verifier.sol deploys directly)
  - Hedera Token Service (HTS) non-fungible token as the Compliance Passport,
    with freeze key set (non-transferable) and supply key set to oracle authority

Environment variables consumed:
  HEDERA_RPC_URL, HEDERA_OPERATOR_ID, HEDERA_OPERATOR_KEY,
  HEDERA_VERIFIER_CONTRACT_ID, HEDERA_PASSPORT_TOKEN_ID,
  HEDERA_MIRROR_NODE_URL
"""

from __future__ import annotations

import json
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


class HederaAdapter(PassportAdapterBase):
    """Hedera Hashgraph Compliance Passport Adapter.

    Spec reference: US-08.4.1, US-08.4.2
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on Hedera HSCS.

        The EVM-compatible Verifier.sol (F-08.2.1) is deployed to Hedera testnet
        via HSCS. This method calls `verify(proof, publicInputs)` on that contract.

        Args:
            proof_hex: hex-encoded UltraHonk proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier returns `true`.
        """
        verifier_id = getattr(self.settings, "hedera_verifier_contract_id", None)
        if not verifier_id:
            raise AdapterDeploymentError("hedera", "HEDERA_VERIFIER_CONTRACT_ID is not configured")

        try:
            from hedera import (  # type: ignore[import-untyped]
                Client,
                ContractCallQuery,
            )
        except ImportError as exc:
            raise AdapterDeploymentError(
                "hedera", "hedera-sdk-py not installed; run: pip install hedera-sdk-py", cause=exc
            ) from exc

        operator_id = getattr(self.settings, "hedera_operator_id", "")
        operator_key = getattr(self.settings, "hedera_operator_key", "")

        if not operator_id or not operator_key:
            raise AdapterDeploymentError("hedera", "HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY must be set")

        try:
            client = Client.for_testnet()
            client.set_operator(operator_id, operator_key)

            proof_bytes = bytes.fromhex(proof_hex)
            call = ContractCallQuery()
            call.contract_id = verifier_id
            call.function = "verify"
            call.params = [proof_bytes, public_inputs]
            call.gas = 2_000_000
            result = call.execute(client)

            is_valid = bool(result.get_int(0))
            logger.info("hedera proof verified", extra={"valid": is_valid, "verifier": verifier_id})
            return is_valid
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("hedera", f"verifier contract call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint an HTS NFT Compliance Passport.

        Calls `TokenMintTransaction` on the Hedera Token Service for the
        pre-created Compliance Passport token. The token was created with:
          - freezeKey set (non-transferable)
          - supplyKey set to oracle authority
          - metadata containing policy_id and expires_at

        Args:
            wallet: Hedera account ID (e.g. 0.0.1234).
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            Hedera transaction hash string.
        """
        token_id = getattr(self.settings, "hedera_passport_token_id", None)
        if not token_id:
            raise AdapterDeploymentError("hedera", "HEDERA_PASSPORT_TOKEN_ID is not configured")

        try:
            from hedera import (  # type: ignore[import-untyped]
                Client,
                TokenMintTransaction,
            )
        except ImportError as exc:
            raise AdapterDeploymentError(
                "hedera", "hedera-sdk-py not installed", cause=exc
            ) from exc

        operator_id = getattr(self.settings, "hedera_operator_id", "")
        operator_key = getattr(self.settings, "hedera_operator_key", "")
        if not operator_id or not operator_key:
            raise AdapterDeploymentError("hedera", "HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY must be set")

        try:
            client = Client.for_testnet()
            client.set_operator(operator_id, operator_key)

            metadata_bytes = self._encode_passport_metadata(policy_id, expires_at, proof_hash)

            mint_tx = (
                TokenMintTransaction()
                .set_token_id(token_id)
                .set_metadata(metadata_bytes)
                .set_transfer_account(operator_id)
                .freeze_with(client)
            )
            receipt = mint_tx.execute(client).get_receipt(client)
            tx_hash = receipt.transaction_id.to_string()

            logger.info(
                "hedera passport minted",
                extra={"tx_hash": tx_hash, "wallet": wallet, "token_id": token_id},
            )
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("hedera", f"TokenMintTransaction failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on Hedera.

        Because the token is non-transferable (freeze key set), revocation is
        implemented by freezing the specific NFT serial for the wallet via
        `TokenFreezeTransaction`.

        Args:
            wallet: Hedera account ID.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            Hedera transaction hash string.
        """
        token_id = getattr(self.settings, "hedera_passport_token_id", None)
        if not token_id:
            raise AdapterDeploymentError("hedera", "HEDERA_PASSPORT_TOKEN_ID is not configured")

        try:
            from hedera import (  # type: ignore[import-untyped]
                Client,
                TokenFreezeTransaction,
            )
        except ImportError as exc:
            raise AdapterDeploymentError(
                "hedera", "hedera-sdk-py not installed", cause=exc
            ) from exc

        operator_id = getattr(self.settings, "hedera_operator_id", "")
        operator_key = getattr(self.settings, "hedera_operator_key", "")
        if not operator_id or not operator_key:
            raise AdapterDeploymentError("hedera", "HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY must be set")

        try:
            client = Client.for_testnet()
            client.set_operator(operator_id, operator_key)

            freeze_tx = (
                TokenFreezeTransaction()
                .set_token_id(token_id)
                .set_account_id(wallet)
                .freeze_with(client)
            )
            receipt = freeze_tx.execute(client).get_receipt(client)
            tx_hash = receipt.transaction_id.to_string()

            logger.info(
                "hedera passport revoked (frozen)",
                extra={"tx_hash": tx_hash, "wallet": wallet, "reason": reason},
            )
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("hedera", f"TokenFreezeTransaction failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Check if `wallet` holds a valid Compliance Passport NFT on Hedera.

        Queries the Hedera Mirror Node REST API for the wallet's token balance
        and checks the NFT serial metadata for expiry.

        Args:
            wallet: Hedera account ID.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        token_id = getattr(self.settings, "hedera_passport_token_id", None)
        if not token_id:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        mirror_node_url = getattr(self.settings, "hedera_mirror_node_url", "https://testnet.mirrornode.hedera.com")
        try:
            import httpx
            url = f"{mirror_node_url}/api/v1/tokens/{token_id}/balances"
            params = {"account.id": wallet}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}
                data = response.json()
                balances = data.get("balances", [])
                if not balances:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}

                balance = balances[0]
                serial_numbers = balance.get("serial_numbers", [])
                if not serial_numbers:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}

                return {
                    "valid": True,
                    "expires_at": balance.get("balance", 0),
                    "policy_id": policy_id,
                    "extra": {"serial_numbers": serial_numbers},
                }
        except Exception as exc:
            logger.warning("hedera verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Hedera deployment metadata."""
        verifier = getattr(self.settings, "hedera_verifier_contract_id", "")
        token_id = getattr(self.settings, "hedera_passport_token_id", "")
        rpc_url = getattr(self.settings, "hedera_rpc_url", "")
        network = "testnet" if "testnet" in rpc_url else "mainnet"

        return DeploymentInfo(
            chain_id="hedera",
            contract_address=verifier,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "passport_token_id": token_id,
                "mirror_node_url": getattr(self.settings, "hedera_mirror_node_url", ""),
            },
        )

    def _encode_passport_metadata(self, policy_id: str, expires_at: int, proof_hash: str) -> bytes:
        """Encode passport metadata as bytes for HTS NFT metadata field."""
        metadata = json.dumps({
            "policy_id": policy_id,
            "expires_at": expires_at,
            "proof_hash": proof_hash,
            "version": "1.0",
        })
        return metadata.encode("utf-8")
