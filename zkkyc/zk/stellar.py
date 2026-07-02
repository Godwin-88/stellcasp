"""
Stellar Soroban proof dispatch — ZK-KYC Compliance Agent
(zkkyc.zk.stellar)

Spec reference: EP-02, F-02.2 (US-02.2.1, US-02.2.2)
                EP-03, F-03.1 (US-03.1.1 — passport mint trigger)

Architecture
------------
This module is the bridge between the Python ZK platform and the on-chain
Soroban verifier contract (`stellar/src/lib.rs`). It takes a generated
Noir UltraHonk proof and dispatches it to the deployed ComplianceVerifier
contract via a Soroban transaction on Stellar testnet.

The function returns the Stellar transaction hash on success. The same
hash is used by the Settlement Agent (EP-06 F-06.1.5) to populate
`state.on_chain_tx_hash` and by the demo script (P5) to show the
verifier → passport mint → dual-protocol verify flow.

Public-input encoding
---------------------
The verifier contract expects a 48-byte `public_inputs` blob:
  bytes 0..8   — ci_threshold as u64 little-endian
  bytes 8..16  — manifold_threshold as u64 little-endian
  bytes 16..48 — policy_id as 32-byte field element (big-endian)

This matches `read_u64_le` / `read_bytes32` in verifier_lib.rs exactly.
Any deviation will cause `ERR_MALFORMED_PUBLIC_INPUTS` on-chain.

PII guarantee
-------------
`entity_hash` is SHA-256(raw_id + ENTITY_SALT), computed upstream in
`entity.hash_entity_id()`. Raw entity IDs never reach this module.
The proof bytes and public inputs contain no PII — only the scaled
threshold values and the policy identifier. (US-02.2.2, US-06.1.2)

Dependencies
------------
Requires `stellar-sdk` (PyPI) >= 9.0 with Soroban support.
Install:  pip install "stellar-sdk>=9.0"

The `stellar_sdk.soroban_server.SorobanServer` class is used for
testnet RPC. For mainnet, swap the horizon URL and network passphrase.
"""
from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class StellarDispatchError(Exception):
    """Raised when proof submission to Stellar Soroban fails at any stage.

    Wraps network errors, simulation failures, and transaction rejections
    into a single exception type the Settlement Agent can retry on.
    """
    pass


# ---------------------------------------------------------------------------
# Public-input encoding (must match verifier_lib.rs byte layout exactly)
# ---------------------------------------------------------------------------

def encode_public_inputs(
    ci_threshold_scaled: int,
    manifold_threshold_scaled: int,
    policy_id_int: int,
) -> bytes:
    """Encode public inputs as the 48-byte blob the verifier contract expects.

    Layout (matches `read_u64_le` / `read_bytes32` in verifier_lib.rs):
      bytes 0..8   — ci_threshold as u64 little-endian
      bytes 8..16  — manifold_threshold as u64 little-endian
      bytes 16..48 — policy_id as 32-byte big-endian field element

    Args:
        ci_threshold_scaled: CI ceiling × 1_000_000 (e.g. 750_000 for CI < 0.75)
        manifold_threshold_scaled: minimum manifold score × 1_000_000
        policy_id_int: policy version as integer (e.g. 1 for policy_v1)

    Returns:
        48-byte `bytes` blob ready to pass as the `public_inputs` parameter
        to `verify_and_attest`.

    Raises:
        StellarDispatchError: if any value is out of range for its field.
    """
    if not (0 <= ci_threshold_scaled < 2**64):
        raise StellarDispatchError(
            f"ci_threshold_scaled out of u64 range: {ci_threshold_scaled}"
        )
    if not (0 <= manifold_threshold_scaled < 2**64):
        raise StellarDispatchError(
            f"manifold_threshold_scaled out of u64 range: {manifold_threshold_scaled}"
        )
    if not (0 <= policy_id_int < 2**256):
        raise StellarDispatchError(
            f"policy_id_int out of Field range: {policy_id_int}"
        )

    buf = bytearray(48)
    # bytes 0..8 — ci_threshold, u64 little-endian
    buf[0:8] = struct.pack("<Q", ci_threshold_scaled)
    # bytes 8..16 — manifold_threshold, u64 little-endian
    buf[8:16] = struct.pack("<Q", manifold_threshold_scaled)
    # bytes 16..48 — policy_id as 32-byte big-endian field element
    policy_bytes = policy_id_int.to_bytes(32, byteorder="big")
    buf[16:48] = policy_bytes

    return bytes(buf)


# ---------------------------------------------------------------------------
# Main dispatch function
# ---------------------------------------------------------------------------

async def submit_proof_stellar(
    proof_hex: str,
    public_inputs: list[int],
    entity_hash: str,
    policy_id: str,
    settings: Settings | None = None,
) -> str:
    """Submit a ZK proof to the Stellar Soroban ComplianceVerifier contract.

    Orchestrates:
      1. Validate inputs (proof_hex, public_inputs length, entity_hash format)
      2. Encode public_inputs into the 48-byte blob the contract expects
      3. Build a Soroban transaction invoking `verify_and_attest`
      4. Simulate the transaction to estimate resource fees
      5. Sign with the configured source keypair
      6. Submit to testnet and wait for confirmation
      7. Return the transaction hash

    Args:
        proof_hex: hex-encoded UltraHonk proof bytes from `generate_zk_proof`
        public_inputs: list of three ints:
            [ci_threshold_scaled, manifold_threshold_scaled, policy_id_int]
        entity_hash: 64-char hex string (SHA-256 of raw entity ID + salt)
        policy_id: human-readable policy identifier (e.g. "policy_v1") —
            used for logging only; the on-chain policy_id is the integer
            in public_inputs[2]
        settings: optional Settings override; defaults to get_settings()

    Returns:
        The Stellar transaction hash (hex string) on success.

    Raises:
        StellarDispatchError: on any failure — malformed inputs, network
            error, simulation failure, or transaction rejection. The
            Settlement Agent (EP-06 F-06.1.5) retries once after 5s on
            this exception before routing to the error terminal.
    """
    settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    if not proof_hex:
        raise StellarDispatchError("proof_hex is empty")
    try:
        proof_bytes = bytes.fromhex(proof_hex)
    except ValueError as exc:
        raise StellarDispatchError(f"proof_hex is not valid hex: {exc}") from exc

    if len(public_inputs) != 3:
        raise StellarDispatchError(
            f"public_inputs must have exactly 3 elements "
            f"[ci_threshold, manifold_threshold, policy_id_int]; got {len(public_inputs)}"
        )
    if len(entity_hash) != 64:
        raise StellarDispatchError(
            f"entity_hash must be 64 hex chars (32 bytes); got {len(entity_hash)}"
        )
    try:
        entity_hash_bytes = bytes.fromhex(entity_hash)
    except ValueError as exc:
        raise StellarDispatchError(f"entity_hash is not valid hex: {exc}") from exc

    ci_threshold_scaled, manifold_threshold_scaled, policy_id_int = public_inputs

    # ------------------------------------------------------------------
    # Encode the 48-byte public_inputs blob
    # ------------------------------------------------------------------
    pi_blob = encode_public_inputs(
        ci_threshold_scaled=ci_threshold_scaled,
        manifold_threshold_scaled=manifold_threshold_scaled,
        policy_id_int=policy_id_int,
    )

    # ------------------------------------------------------------------
    # Stellar SDK imports — deferred so the module imports cleanly even
    # if stellar-sdk is not installed (graceful degradation for local dev)
    # ------------------------------------------------------------------
    try:
        from stellar_sdk import (
            Keypair,
            Network,
            TransactionBuilder,
            assemble_transaction,
        )
        from stellar_sdk import xdr as stellar_xdr
        from stellar_sdk.soroban_server import SorobanServer
    except ImportError as exc:
        raise StellarDispatchError(
            "stellar-sdk is not installed. Run: pip install 'stellar-sdk>=9.0'"
        ) from exc

    # ------------------------------------------------------------------
    # Network configuration from settings
    # ------------------------------------------------------------------
    horizon_url = getattr(
        settings, "stellar_horizon_url",
        "https://soroban-testnet.stellar.org",
    )
    network_passphrase = getattr(
        settings, "stellar_network_passphrase",
        Network.TESTNET_NETWORK_PASSPHRASE,
    )
    verifier_contract_id = getattr(
        settings, "stellar_verifier_contract_id", None,
    )
    source_secret = getattr(settings, "stellar_source_secret", None)

    if not verifier_contract_id:
        raise StellarDispatchError(
            "STELLAR_VERIFIER_CONTRACT_ID is not set in environment / settings"
        )
    if not source_secret:
        raise StellarDispatchError(
            "STELLAR_SOURCE_SECRET is not set in environment / settings"
        )

    base_fee = int(getattr(settings, "stellar_base_fee", 100))

    # ------------------------------------------------------------------
    # Build the Soroban server and load the source account
    # ------------------------------------------------------------------
    loop = asyncio.get_event_loop()
    try:
        server = SorobanServer(horizon_url)
        source_kp = Keypair.from_secret(source_secret)
        # load_account is synchronous in stellar_sdk — run in executor
        # to avoid blocking the event loop (matches proof.py pattern)
        source_account = await loop.run_in_executor(
            None, lambda: server.load_account(source_kp.public_key),
        )
    except Exception as exc:
        raise StellarDispatchError(
            f"Failed to load source account from {horizon_url}: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # Build the contract invocation transaction
    # ------------------------------------------------------------------
    # Function parameters for verify_and_attest(proof, public_inputs, entity_hash):
    #   - proof:           Bytes      → SCV_BYTES
    #   - public_inputs:   Bytes      → SCV_BYTES (48 bytes)
    #   - entity_hash:     BytesN<32> → SCV_BYTES (32 bytes)
    try:
        proof_scval = stellar_xdr.SCVal(
            type=stellar_xdr.SCValType.SCV_BYTES,
            bytes=stellar_xdr.SCBytes(proof_bytes),
        )
        pi_scval = stellar_xdr.SCVal(
            type=stellar_xdr.SCValType.SCV_BYTES,
            bytes=stellar_xdr.SCBytes(pi_blob),
        )
        hash_scval = stellar_xdr.SCVal(
            type=stellar_xdr.SCValType.SCV_BYTES,
            bytes=stellar_xdr.SCBytes(entity_hash_bytes),
        )
    except Exception as exc:
        raise StellarDispatchError(f"Failed to build XDR SCVals: {exc}") from exc

    try:
        builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=base_fee,
        )
        builder.append_invoke_contract_function_op(
            contract_id=verifier_contract_id,
            function_name="verify_and_attest",
            parameters=[proof_scval, pi_scval, hash_scval],
        )
        builder.set_timeout(300)
        tx = builder.build()
    except Exception as exc:
        raise StellarDispatchError(
            f"Failed to build Soroban transaction: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # Simulate to estimate resource fees and ledger footprint
    # ------------------------------------------------------------------
    try:
        simulation = await loop.run_in_executor(
            None, lambda: server.simulate_transaction(tx),
        )
        if simulation.error:
            raise StellarDispatchError(
                f"Transaction simulation failed: {simulation.error}"
            )
        # assemble_transaction applies the simulation result (resource fees,
        # Soroban data footprint, min resource fee) to the unsigned tx.
        tx = assemble_transaction(tx, simulation)
    except StellarDispatchError:
        raise
    except Exception as exc:
        raise StellarDispatchError(
            f"Transaction simulation raised an unexpected error: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # Sign and submit
    # ------------------------------------------------------------------
    try:
        tx.sign(source_kp)
        tx_hash = tx.hash().hex()

        response = await loop.run_in_executor(
            None, lambda: server.send_transaction(tx),
        )

        if not response.successful:
            raise StellarDispatchError(
                f"Transaction rejected by network: {response.result_xdr}"
            )

        logger.info(
            "stellar proof submitted",
            extra={
                "tx_hash": tx_hash,
                "entity_hash": entity_hash,
                "policy_id": policy_id,
                "verifier_contract": verifier_contract_id,
            },
        )
        return tx_hash

    except StellarDispatchError:
        raise
    except Exception as exc:
        raise StellarDispatchError(
            f"Failed to sign/submit transaction: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Convenience: query attestation from the verifier contract
# ---------------------------------------------------------------------------

async def get_attestation_from_stellar(
    entity_hash: str,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    """Query the on-chain attestation record for `entity_hash`.

    Calls `get_attestation(entity_hash)` on the deployed verifier contract.
    Returns None if no attestation exists, or a dict with the record fields
    if one does.

    Used by the demo script (P5) and the Settlement Agent to confirm
    that `verify_and_attest` actually persisted the record before
    proceeding to passport minting.

    Args:
        entity_hash: 64-char hex string (SHA-256 of raw entity ID + salt)
        settings: optional Settings override

    Returns:
        Dict with keys {entity_hash, ci_threshold, manifold_threshold,
        policy_id, verified_at, proof_hash} or None if not found.

    Raises:
        StellarDispatchError: on network or contract call failure.
    """
    settings = settings or get_settings()

    try:
        from stellar_sdk import Keypair, Network, TransactionBuilder
        from stellar_sdk import xdr as stellar_xdr
        from stellar_sdk.soroban_server import SorobanServer
    except ImportError as exc:
        raise StellarDispatchError(
            "stellar-sdk is not installed. Run: pip install 'stellar-sdk>=9.0'"
        ) from exc

    horizon_url = getattr(
        settings, "stellar_horizon_url",
        "https://soroban-testnet.stellar.org",
    )
    network_passphrase = getattr(
        settings, "stellar_network_passphrase",
        Network.TESTNET_NETWORK_PASSPHRASE,
    )
    verifier_contract_id = getattr(
        settings, "stellar_verifier_contract_id", None,
    )

    if not verifier_contract_id:
        raise StellarDispatchError("STELLAR_VERIFIER_CONTRACT_ID is not set")
    if len(entity_hash) != 64:
        raise StellarDispatchError(
            f"entity_hash must be 64 hex chars; got {len(entity_hash)}"
        )

    try:
        entity_hash_bytes = bytes.fromhex(entity_hash)
    except ValueError as exc:
        raise StellarDispatchError(f"entity_hash is not valid hex: {exc}") from exc

    loop = asyncio.get_event_loop()
    try:
        server = SorobanServer(horizon_url)

        # Read-only view call — use a throwaway keypair as source account.
        # The simulation returns the return value without actually submitting.
        source_kp = Keypair.random()
        source_account = await loop.run_in_executor(
            None, lambda: server.load_account(source_kp.public_key),
        )

        builder = TransactionBuilder(
            source_account=source_account,
            network_passphrase=network_passphrase,
            base_fee=100,
        )
        builder.append_invoke_contract_function_op(
            contract_id=verifier_contract_id,
            function_name="get_attestation",
            parameters=[
                stellar_xdr.SCVal(
                    type=stellar_xdr.SCValType.SCV_BYTES,
                    bytes=stellar_xdr.SCBytes(entity_hash_bytes),
                ),
            ],
        )
        builder.set_timeout(30)
        tx = builder.build()

        simulation = await loop.run_in_executor(
            None, lambda: server.simulate_transaction(tx),
        )
        if simulation.error:
            raise StellarDispatchError(
                f"get_attestation simulation failed: {simulation.error}"
            )
        return _parse_attestation_result(simulation)

    except StellarDispatchError:
        raise
    except Exception as exc:
        raise StellarDispatchError(
            f"Failed to query attestation from Stellar: {exc}"
        ) from exc


def _parse_attestation_result(result: Any) -> dict[str, Any] | None:
    """Parse the SCVal result from get_attestation into a Python dict.

    Returns None if the contract returned SCV_VOID (no attestation exists).
    Otherwise returns a dict with the AttestationRecord fields.
    """
    try:
        from stellar_sdk import xdr as stellar_xdr
    except ImportError:
        return None

    # The result may be wrapped in different ways depending on SDK version.
    scval = None
    if hasattr(result, "return_value"):
        scval = result.return_value
    elif hasattr(result, "result"):
        scval = result.result
    elif isinstance(result, stellar_xdr.SCVal):
        scval = result

    if scval is None:
        return None

    # SCV_VOID means no attestation found (Option<AttestationRecord> = None)
    if scval.type == stellar_xdr.SCValType.SCV_VOID:
        return None

    # SCV_MAP or SCV_STRUCTURE — parse the AttestationRecord fields
    try:
        if scval.type == stellar_xdr.SCValType.SCV_MAP:
            fields = {}
            for entry in scval.map.map:
                key = (
                    entry.key.sym.sc_symbol.decode()
                    if hasattr(entry.key, "sym")
                    else str(entry.key)
                )
                fields[key] = _scval_to_python(entry.val)
            return fields
        # Fallback: return the raw SCVal representation
        return {"raw": str(scval)}
    except Exception:
        return {"raw": str(scval)}


def _scval_to_python(scval: Any) -> Any:
    """Convert an SCVal to a Python primitive for logging/demo output."""
    try:
        from stellar_sdk import xdr as stellar_xdr
    except ImportError:
        return str(scval)

    t = scval.type
    if t == stellar_xdr.SCValType.SCV_U64:
        return scval.u64.u64
    if t == stellar_xdr.SCValType.SCV_U32:
        return scval.u32.u32
    if t == stellar_xdr.SCValType.SCV_BYTES:
        return scval.bytes.sc_bytes.hex()
    if t == stellar_xdr.SCValType.SCV_BOOL:
        return scval.b
    if t == stellar_xdr.SCValType.SCV_SYMBOL:
        return scval.sym.sc_symbol.decode()
    return str(scval)