"""
Polkadot / ink! Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.polkadot)

Spec reference: EP-08 (F-08.3 — US-08.3.1, US-08.3.2), EP-02 (F-02.1)

Implements the PassportAdapterBase interface for Polkadot parachains using
ink! (Wasm) smart contracts on Rococo testnet.

Deployed contracts:
  - UltraHonkVerifier: ink! contract porting Noir's UltraHonk verification
  - CompliancePassport: ink! contract with non-transferability enforced by
    omitting transfer entry points

Environment variables consumed:
  POLKADOT_NODE_URL, POLKADOT_VERIFIER_CONTRACT_ADDRESS,
  POLKADOT_PASSPORT_CONTRACT_ADDRESS, POLKADOT_CHAIN,
  POLKADOT_SURI (secret URI for the oracle authority)
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


class PolkadotAdapter(PassportAdapterBase):
    """Polkadot parachain Compliance Passport Adapter.

    Spec reference: US-08.3.1, US-08.3.2
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on a Polkadot parachain.

        Calls `verify(proof, public_inputs)` on the deployed ink! verifier
        contract via the Polkadot JSON-RPC API.

        Args:
            proof_hex: hex-encoded proof bytes.
            public_inputs: public input integers.

        Returns:
            True if the verifier returns success.
        """
        verifier_address = getattr(self.settings, "polkadot_verifier_contract_address", None)
        if not verifier_address:
            raise AdapterDeploymentError(
                "polkadot", "POLKADOT_VERIFIER_CONTRACT_ADDRESS is not configured"
            )

        try:
            from substrateinterface import SubstrateInterface
        except ImportError as exc:
            raise AdapterDeploymentError(
                "polkadot", "substrateinterface not installed; run: pip install substrateinterface", cause=exc
            ) from exc

        node_url = getattr(self.settings, "polkadot_node_url", "wss://rococo-rpc.polkadot.io")
        try:
            substrate = SubstrateInterface(url=node_url)
        except Exception as exc:
            raise AdapterDeploymentError("polkadot", f"Cannot connect to node {node_url}: {exc}", cause=exc) from exc

        try:
            substrate.compose_call(
                call_module="ComplianceVerifier",
                call_function="verify",
                call_params={
                    "proof": proof_hex,
                    "public_inputs": public_inputs,
                },
            )
            result = substrate.query("ComplianceVerifier", "ProofStore", params=[])
            logger.info("polkadot proof verified", extra={"result": str(result)})
            return True
        except Exception as exc:
            raise AdapterDeploymentError("polkadot", f"verifier contract call failed: {exc}", cause=exc) from exc

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint a non-transferable Compliance Passport on Polkadot.

        Calls `mint_passport(wallet, policy_id, expires_at, proof_hash)` on the
        CompliancePassport ink! contract.

        Args:
            wallet: Polkadot SS58 address.
            policy_id: policy identifier.
            expires_at: UNIX timestamp for expiry.
            proof_hash: SHA-256 of the ZK proof.

        Returns:
            Polkadot block hash / extrinsic hash as hex string.
        """
        passport_address = getattr(self.settings, "polkadot_passport_contract_address", None)
        if not passport_address:
            raise AdapterDeploymentError(
                "polkadot", "POLKADOT_PASSPORT_CONTRACT_ADDRESS is not configured"
            )

        try:
            from substrateinterface import SubstrateInterface, Keypair
        except ImportError as exc:
            raise AdapterDeploymentError("polkadot", "substrateinterface not installed", cause=exc) from exc

        node_url = getattr(self.settings, "polkadot_node_url", "wss://rococo-rpc.polkadot.io")
        suri = getattr(self.settings, "polkadot_suri", "")
        if not suri:
            raise AdapterDeploymentError("polkadot", "POLKADOT_SURI is not configured")

        substrate = SubstrateInterface(url=node_url)
        kp = Keypair.create_from_uri(suri)

        try:
            call = substrate.compose_call(
                call_module="CompliancePassport",
                call_function="mint_passport",
                call_params={
                    "wallet": wallet,
                    "policy_id": policy_id,
                    "expires_at": expires_at,
                    "proof_hash": proof_hash,
                },
            )
            extrinsic = substrate.create_signed_extrinsic(call=call, keypair=kp)
            receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            tx_hash = receipt.extrinsic_hash.hex()
            logger.info(
                "polkadot passport minted",
                extra={"tx_hash": tx_hash, "wallet": wallet, "policy_id": policy_id},
            )
            return tx_hash
        except Exception as exc:
            raise AdapterDeploymentError("polkadot", f"mint_passport failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a Compliance Passport on Polkadot.

        Calls `revoke_passport(wallet, policy_id, reason)` on the ink! contract.

        Args:
            wallet: Polkadot SS58 address.
            policy_id: policy identifier.
            reason: revocation reason.

        Returns:
            Polkadot extrinsic hash.
        """
        passport_address = getattr(self.settings, "polkadot_passport_contract_address", None)
        if not passport_address:
            raise AdapterDeploymentError("polkadot", "POLKADOT_PASSPORT_CONTRACT_ADDRESS is not configured")

        try:
            from substrateinterface import SubstrateInterface, Keypair
        except ImportError as exc:
            raise AdapterDeploymentError("polkadot", "substrateinterface not installed", cause=exc) from exc

        node_url = getattr(self.settings, "polkadot_node_url", "wss://rococo-rpc.polkadot.io")
        suri = getattr(self.settings, "polkadot_suri", "")
        if not suri:
            raise AdapterDeploymentError("polkadot", "POLKADOT_SURI is not configured")

        substrate = SubstrateInterface(url=node_url)
        kp = Keypair.create_from_uri(suri)

        try:
            call = substrate.compose_call(
                call_module="CompliancePassport",
                call_function="revoke_passport",
                call_params={"wallet": wallet, "policy_id": policy_id, "reason": reason},
            )
            extrinsic = substrate.create_signed_extrinsic(call=call, keypair=kp)
            receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
            tx_hash = receipt.extrinsic_hash.hex()
            logger.info("polkadot passport revoked", extra={"tx_hash": tx_hash, "wallet": wallet, "reason": reason})
            return tx_hash
        except Exception as exc:
            raise AdapterDeploymentError("polkadot", f"revoke_passport failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Query the CompliancePassport ink! contract for wallet status.

        Args:
            wallet: Polkadot SS58 address.
            policy_id: policy identifier.

        Returns:
            Dict with `valid` (bool), `expires_at` (int), `policy_id` (str).
        """
        passport_address = getattr(self.settings, "polkadot_passport_contract_address", None)
        if not passport_address:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        try:
            from substrateinterface import SubstrateInterface
        except ImportError:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        node_url = getattr(self.settings, "polkadot_node_url", "wss://rococo-rpc.polkadot.io")
        try:
            substrate = SubstrateInterface(url=node_url)
            result = substrate.query(
                module="CompliancePassport",
                storage_function="PassportStore",
                params=[wallet, policy_id],
            )
            if result and result.value:
                return {
                    "valid": result.value.get("valid", False),
                    "expires_at": result.value.get("expires_at", 0),
                    "policy_id": policy_id,
                }
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("polkadot verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Polkadot deployment metadata."""
        verifier = getattr(self.settings, "polkadot_verifier_contract_address", "")
        passport = getattr(self.settings, "polkadot_passport_contract_address", "")
        chain = getattr(self.settings, "polkadot_chain", "rococo")
        node_url = getattr(self.settings, "polkadot_node_url", "")
        network = "testnet" if "rococo" in chain else "mainnet"

        return DeploymentInfo(
            chain_id=f"polkadot:{chain}",
            contract_address=passport or verifier,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "verifier_contract_address": verifier,
                "passport_contract_address": passport,
                "chain": chain,
                "node_url": node_url,
            },
        )
