"""
Stellar Soroban Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.stellar)

Spec reference: EP-08 (F-08.1 — US-08.1.1), EP-02 (F-02.2), EP-03 (F-03.1)

Implements the PassportAdapterBase interface for Stellar testnet / mainnet
using Soroban smart contracts. The adapter wraps the existing proof dispatch
logic from `zkkyc.zk.stellar` and adds the full five-operation interface
required by the Settlement Agent (EP-06 F-06.1.5).

Deployed contracts (testnet):
  - ComplianceVerifier: verifies Noir UltraHonk proofs
  - CompliancePassport: mints and manages non-transferable passport tokens

The adapter is auto-registered with AdapterRegistry under key "stellar"
when stellar-sdk >= 9.0 is installed.
"""

from __future__ import annotations

import logging
import struct
from datetime import datetime, timezone
from typing import Any

from ..config import Settings, get_settings
from .base import (
    AdapterDeploymentError,
    DeploymentInfo,
    PassportAdapterBase,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class StellarAdapter(PassportAdapterBase):
    """Stellar Soroban Compliance Passport Adapter.

    Environment variables consumed:
      STELLAR_HORIZON_URL, STELLAR_NETWORK_PASSPHRASE,
      STELLAR_VERIFIER_CONTRACT_ID, STELLAR_PASSPORT_CONTRACT_ID,
      STELLAR_SOURCE_SECRET, STELLAR_ORACLE_AUTHORITY, STELLAR_BASE_FEE

    Spec reference: US-02.2.1, US-02.2.2, US-02.2.3, US-03.1.1, US-03.1.2,
                    US-03.1.3, US-08.1.1
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # verify_proof — submit proof to Soroban verifier contract
    # ------------------------------------------------------------------

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Verify a Noir UltraHonk proof on Stellar Soroban.

        Calls `verify_and_attest(proof, public_inputs, entity_hash)` on the
        deployed ComplianceVerifier contract. Returns True if the contract
        accepts the proof and emits the attestation event.

        Args:
            proof_hex: hex-encoded proof bytes.
            public_inputs: [ci_threshold_scaled, manifold_threshold_scaled, policy_id_int].

        Returns:
            True if proof verification succeeded on-chain.
        """
        try:
            tx_hash = await self._submit_proof(proof_hex, public_inputs, entity_hash="")
        except AdapterDeploymentError:
            return False
        return bool(tx_hash)

    # ------------------------------------------------------------------
    # mint_passport — mint CompliancePassport on Soroban
    # ------------------------------------------------------------------

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Mint a non-transferable Compliance Passport for `wallet`.

        Calls `mint_passport(wallet, policy_id, expires_at, proof_hash)` on the
        CompliancePassport Soroban contract. Only callable by the oracle authority.

        Args:
            wallet: Stellar address string (e.g. "G...").
            policy_id: policy identifier symbol.
            expires_at: UNIX timestamp for passport expiry.
            proof_hash: 64-char hex SHA-256 of the ZK proof.

        Returns:
            Stellar transaction hash.
        """
        passport_contract = getattr(self.settings, "stellar_passport_contract_id", None)
        if not passport_contract:
            raise AdapterDeploymentError(
                "stellar", "STELLAR_PASSPORT_CONTRACT_ID is not configured"
            )

        oracle_authority = getattr(self.settings, "stellar_oracle_authority", None)
        source_secret = getattr(self.settings, "stellar_source_secret", None)
        if not oracle_authority or not source_secret:
            raise AdapterDeploymentError(
                "stellar", "STELLAR_ORACLE_AUTHORITY and STELLAR_SOURCE_SECRET must be set"
            )

        try:
            from stellar_sdk import Keypair, Network, TransactionBuilder
            from stellar_sdk import xdr as stellar_xdr
            from stellar_sdk.soroban_server import SorobanServer
        except ImportError as exc:
            raise AdapterDeploymentError(
                "stellar", "stellar-sdk not installed; run: pip install 'stellar-sdk>=9.0'", cause=exc
            ) from exc

        horizon_url = getattr(self.settings, "stellar_horizon_url", "https://soroban-testnet.stellar.org")
        network_passphrase = getattr(
            self.settings, "stellar_network_passphrase", Network.TESTNET_NETWORK_PASSPHRASE
        )
        base_fee = int(getattr(self.settings, "stellar_base_fee", 100))

        loop = __import__("asyncio").get_event_loop()
        try:
            server = SorobanServer(horizon_url)
            source_kp = Keypair.from_secret(source_secret)
            source_account = await loop.run_in_executor(
                None, lambda: server.load_account(source_kp.public_key)
            )

            # Build mint_passport invocation
            wallet_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_BYTES,
                bytes=stellar_xdr.SCBytes(__import__("base64").b64decode(wallet)),
            )
            policy_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_SYMBOL,
                sym=stellar_xdr.SCSymbol(policy_id.encode()[:31]),
            )
            expires_scval = stellar_xdr.SCVal(type=stellar_xdr.SCValType.SCV_U64, u64=stellar_xdr.Uint64(expires_at))
            proof_hash_bytes = bytes.fromhex(proof_hash)
            proof_hash_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_BYTES,
                bytes=stellar_xdr.SCBytes(proof_hash_bytes),
            )

            builder = TransactionBuilder(
                source_account=source_account,
                network_passphrase=network_passphrase,
                base_fee=base_fee,
            )
            builder.append_invoke_contract_function_op(
                contract_id=passport_contract,
                function_name="mint_passport",
                parameters=[wallet_scval, policy_scval, expires_scval, proof_hash_scval],
            )
            builder.set_timeout(300)
            tx = builder.build()

            simulation = await loop.run_in_executor(None, lambda: server.simulate_transaction(tx))
            if simulation.error:
                raise AdapterDeploymentError("stellar", f"mint simulation failed: {simulation.error}")

            from stellar_sdk import assemble_transaction
            tx = assemble_transaction(tx, simulation)
            tx.sign(source_kp)
            response = await loop.run_in_executor(None, lambda: server.send_transaction(tx))
            if not response.successful:
                raise AdapterDeploymentError("stellar", f"mint rejected: {response.result_xdr}")

            tx_hash = tx.hash().hex()
            logger.info("stellar passport minted", extra={"tx_hash": tx_hash, "wallet": wallet, "policy_id": policy_id})
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("stellar", f"mint_passport failed: {exc}", cause=exc) from exc

    # ------------------------------------------------------------------
    # revoke_passport — revoke a CompliancePassport
    # ------------------------------------------------------------------

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke an active Compliance Passport.

        Calls `revoke_passport(wallet, policy_id, reason)` on the
        CompliancePassport contract. Only callable by the oracle authority.
        """
        passport_contract = getattr(self.settings, "stellar_passport_contract_id", None)
        if not passport_contract:
            raise AdapterDeploymentError("stellar", "STELLAR_PASSPORT_CONTRACT_ID is not configured")
        source_secret = getattr(self.settings, "stellar_source_secret", None)
        if not source_secret:
            raise AdapterDeploymentError("stellar", "STELLAR_SOURCE_SECRET is not configured")

        try:
            from stellar_sdk import Keypair, Network, TransactionBuilder
            from stellar_sdk import xdr as stellar_xdr
            from stellar_sdk.soroban_server import SorobanServer
        except ImportError as exc:
            raise AdapterDeploymentError("stellar", "stellar-sdk not installed", cause=exc) from exc

        horizon_url = getattr(self.settings, "stellar_horizon_url", "https://soroban-testnet.stellar.org")
        network_passphrase = getattr(self.settings, "stellar_network_passphrase", Network.TESTNET_NETWORK_PASSPHRASE)
        base_fee = int(getattr(self.settings, "stellar_base_fee", 100))
        loop = __import__("asyncio").get_event_loop()

        try:
            server = SorobanServer(horizon_url)
            source_kp = Keypair.from_secret(source_secret)
            source_account = await loop.run_in_executor(None, lambda: server.load_account(source_kp.public_key))

            wallet_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_BYTES,
                bytes=stellar_xdr.SCBytes(__import__("base64").b64decode(wallet)),
            )
            policy_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_SYMBOL,
                sym=stellar_xdr.SCSymbol(policy_id.encode()[:31]),
            )
            reason_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_SYMBOL,
                sym=stellar_xdr.SCSymbol(reason.encode()[:31]),
            )

            builder = TransactionBuilder(source_account=source_account, network_passphrase=network_passphrase, base_fee=base_fee)
            builder.append_invoke_contract_function_op(
                contract_id=passport_contract,
                function_name="revoke_passport",
                parameters=[wallet_scval, policy_scval, reason_scval],
            )
            builder.set_timeout(300)
            tx = builder.build()
            simulation = await loop.run_in_executor(None, lambda: server.simulate_transaction(tx))
            if simulation.error:
                raise AdapterDeploymentError("stellar", f"revoke simulation failed: {simulation.error}")
            from stellar_sdk import assemble_transaction
            tx = assemble_transaction(tx, simulation)
            tx.sign(source_kp)
            response = await loop.run_in_executor(None, lambda: server.send_transaction(tx))
            if not response.successful:
                raise AdapterDeploymentError("stellar", f"revoke rejected: {response.result_xdr}")

            tx_hash = tx.hash().hex()
            logger.info("stellar passport revoked", extra={"tx_hash": tx_hash, "wallet": wallet, "reason": reason})
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("stellar", f"revoke_passport failed: {exc}", cause=exc) from exc

    # ------------------------------------------------------------------
    # verify_credential — read-only credential check
    # ------------------------------------------------------------------

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Check if `wallet` holds a valid Compliance Passport on Stellar.

        Calls `verify_credential(wallet, policy_id)` on the CompliancePassport
        contract. Returns the on-chain record or a sentinel for missing/expired.
        """
        passport_contract = getattr(self.settings, "stellar_passport_contract_id", None)
        if not passport_contract:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        try:
            from stellar_sdk import Keypair, Network, TransactionBuilder
            from stellar_sdk import xdr as stellar_xdr
            from stellar_sdk.soroban_server import SorobanServer
        except ImportError:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        horizon_url = getattr(self.settings, "stellar_horizon_url", "https://soroban-testnet.stellar.org")
        network_passphrase = getattr(self.settings, "stellar_network_passphrase", Network.TESTNET_NETWORK_PASSPHRASE)
        loop = __import__("asyncio").get_event_loop()

        try:
            server = SorobanServer(horizon_url)
            source_kp = Keypair.random()
            source_account = await loop.run_in_executor(None, lambda: server.load_account(source_kp.public_key))

            wallet_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_BYTES,
                bytes=stellar_xdr.SCBytes(__import__("base64").b64decode(wallet)),
            )
            policy_scval = stellar_xdr.SCVal(
                type=stellar_xdr.SCValType.SCV_SYMBOL,
                sym=stellar_xdr.SCSymbol(policy_id.encode()[:31]),
            )

            builder = TransactionBuilder(source_account=source_account, network_passphrase=network_passphrase, base_fee=100)
            builder.append_invoke_contract_function_op(
                contract_id=passport_contract,
                function_name="verify_credential",
                parameters=[wallet_scval, policy_scval],
            )
            builder.set_timeout(30)
            tx = builder.build()
            simulation = await loop.run_in_executor(None, lambda: server.simulate_transaction(tx))
            if simulation.error:
                logger.warning("stellar verify_credential simulation error", extra={"error": simulation.error})
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}

            result = simulation.return_value
            if result.type == stellar_xdr.SCValType.SCV_VOID:
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}

            # Parse SCV_MAP result: {valid: bool, expires_at: u64}
            valid = False
            expires_at = 0
            if result.type == stellar_xdr.SCValType.SCV_MAP:
                for entry in result.map.map:
                    key = entry.key.sym.sc_symbol.decode() if hasattr(entry.key, "sym") else str(entry.key)
                    if key == "valid":
                        valid = entry.val.b
                    elif key == "expires_at":
                        expires_at = entry.val.u64.u64

            return {"valid": valid, "expires_at": expires_at, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("stellar verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    # ------------------------------------------------------------------
    # get_deployment_info
    # ------------------------------------------------------------------

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Stellar deployment metadata."""
        verifier = getattr(self.settings, "stellar_verifier_contract_id", "")
        passport = getattr(self.settings, "stellar_passport_contract_id", "")
        network = "testnet" if "testnet" in getattr(self.settings, "stellar_horizon_url", "") else "unknown"

        return DeploymentInfo(
            chain_id="stellar",
            contract_address=passport or verifier,
            deployed_at=datetime.now(timezone.utc),  # Placeholder; real deploy time stored in deployments.json
            network=network,
            extra={
                "verifier_contract_id": verifier,
                "passport_contract_id": passport,
                "horizon_url": getattr(self.settings, "stellar_horizon_url", ""),
            },
        )

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    async def _submit_proof(self, proof_hex: str, public_inputs: list[int], entity_hash: str) -> str | None:
        """Submit proof to the Stellar verifier contract.

        Returns the tx_hash on success, or None on failure.
        """
        verifier_contract = getattr(self.settings, "stellar_verifier_contract_id", None)
        if not verifier_contract:
            raise AdapterDeploymentError("stellar", "STELLAR_VERIFIER_CONTRACT_ID is not configured")
        source_secret = getattr(self.settings, "stellar_source_secret", None)
        if not source_secret:
            raise AdapterDeploymentError("stellar", "STELLAR_SOURCE_SECRET is not configured")

        try:
            from stellar_sdk import Keypair, Network, TransactionBuilder
            from stellar_sdk import xdr as stellar_xdr
            from stellar_sdk.soroban_server import SorobanServer
            from stellar_sdk import assemble_transaction
        except ImportError as exc:
            raise AdapterDeploymentError("stellar", "stellar-sdk not installed", cause=exc) from exc

        horizon_url = getattr(self.settings, "stellar_horizon_url", "https://soroban-testnet.stellar.org")
        network_passphrase = getattr(self.settings, "stellar_network_passphrase", Network.TESTNET_NETWORK_PASSPHRASE)
        base_fee = int(getattr(self.settings, "stellar_base_fee", 100))
        loop = __import__("asyncio").get_event_loop()

        try:
            proof_bytes = bytes.fromhex(proof_hex)
        except ValueError as exc:
            raise AdapterDeploymentError("stellar", f"proof_hex is not valid hex: {exc}", cause=exc) from exc

        if len(public_inputs) != 3:
            raise AdapterDeploymentError("stellar", f"public_inputs must have 3 elements; got {len(public_inputs)}")

        ci_threshold_scaled, manifold_threshold_scaled, policy_id_int = public_inputs
        pi_blob = bytearray(48)
        pi_blob[0:8] = struct.pack("<Q", ci_threshold_scaled)
        pi_blob[8:16] = struct.pack("<Q", manifold_threshold_scaled)
        pi_blob[16:48] = policy_id_int.to_bytes(32, byteorder="big")
        pi_bytes = bytes(pi_blob)

        entity_hash_bytes = bytes.fromhex(entity_hash) if entity_hash else bytes(32)

        try:
            server = SorobanServer(horizon_url)
            source_kp = Keypair.from_secret(source_secret)
            source_account = await loop.run_in_executor(None, lambda: server.load_account(source_kp.public_key))

            proof_scval = stellar_xdr.SCVal(type=stellar_xdr.SCValType.SCV_BYTES, bytes=stellar_xdr.SCBytes(proof_bytes))
            pi_scval = stellar_xdr.SCVal(type=stellar_xdr.SCValType.SCV_BYTES, bytes=stellar_xdr.SCBytes(pi_bytes))
            hash_scval = stellar_xdr.SCVal(type=stellar_xdr.SCValType.SCV_BYTES, bytes=stellar_xdr.SCBytes(entity_hash_bytes))

            builder = TransactionBuilder(source_account=source_account, network_passphrase=network_passphrase, base_fee=base_fee)
            builder.append_invoke_contract_function_op(
                contract_id=verifier_contract,
                function_name="verify_and_attest",
                parameters=[proof_scval, pi_scval, hash_scval],
            )
            builder.set_timeout(300)
            tx = builder.build()
            simulation = await loop.run_in_executor(None, lambda: server.simulate_transaction(tx))
            if simulation.error:
                raise AdapterDeploymentError("stellar", f"verify simulation failed: {simulation.error}")
            tx = assemble_transaction(tx, simulation)
            tx.sign(source_kp)
            response = await loop.run_in_executor(None, lambda: server.send_transaction(tx))
            if not response.successful:
                raise AdapterDeploymentError("stellar", f"verify rejected: {response.result_xdr}")

            tx_hash = tx.hash().hex()
            logger.info("stellar proof verified", extra={"tx_hash": tx_hash, "verifier": verifier_contract})
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("stellar", f"proof submission failed: {exc}", cause=exc) from exc
