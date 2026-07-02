"""
Noir ZK proof generation & local verification — ZK-KYC Compliance Agent
(zkkyc.zk.proof)

Spec reference: EP-02, F-02.1 (US-02.1.1, US-02.1.2, US-02.1.3)

*** VERIFY THE TOOLCHAIN BEFORE RELYING ON THIS FOR THE DEMO ***
This module (and the spec text it implements) assumes `nargo prove` /
`nargo verify` exist as subcommands. Depending on your installed Noir
version, proving may instead require `nargo execute` (witness generation)
followed by a separate Barretenberg `bb prove -s ultra_honk` / `bb verify`
step — especially likely given this platform's UltraHonk verifier
(`rs-soroban-ultrahonk`). Run `nargo prove --help` on the actual toolchain
you'll demo with and confirm before the submission deadline. If the
subcommands differ, swap the two `_run_subprocess` calls below — the
directory-isolation and proof-round-tripping logic around them stays valid
either way.

Fixes versus the previous implementation
-----------------------------------------
1. CRITICAL correctness bug: `Prover.toml` was written to a throwaway
   tempdir while `nargo prove` ran with `cwd=circuit_path` — nargo never
   saw the witness values just computed. Fixed by copying the whole
   circuit project into an isolated per-call temp directory and writing
   Prover.toml there, so `cwd` and the file location always match.
2. CRITICAL correctness/security bug: `verify_proof_local` never wrote its
   `proof_hex` argument to disk — it ran `nargo verify` against whatever
   proof file already existed in the shared `circuits/proofs/` directory,
   independent of the proof actually passed in. Fixed by round-tripping
   `proof_hex` back into the isolated directory before verifying.
3. Silent failure: a successful `nargo prove` with a missing output file
   returned the literal string `"generated"` as `proof_hex`. Now raises.
4. Blocking event loop: both functions ran subprocess.run synchronously in
   what's called from an async FastAPI route with a 30s SLA — that blocked
   the entire server, not just this request, for up to 30s per call.
   Converted to async subprocess execution.
5. Float truncation: `int(nrs * scale_factor)` truncates rather than
   rounds; floating-point representation error near an exact boundary can
   shift the scaled value down by 1, which matters because the circuit's
   assertion is a strict `<`. Changed to `round()`.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

_PROVE_TIMEOUT_SECONDS = 30  # US-02.1.2 SLA
_VERIFY_TIMEOUT_SECONDS = 10  # US-02.1.3 SLA
# Confirm this matches the actual filename your installed nargo writes
# under proofs/ — historically Noir tooling has used <package_name>.proof
# rather than a bare "proof" in some versions.
_PROOF_FILENAME = "proof"


class ProofGenerationError(Exception):
    pass


def _circuit_source_path() -> Path:
    return Path(__file__).parent.parent.parent / "circuits"


async def _run_subprocess(cmd: list[str], cwd: Path, timeout: float) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"{' '.join(cmd)} timed out after {timeout}s")
    return proc.returncode, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _isolated_circuit_copy(tmp_root: Path) -> Path:
    """Copies the circuit project into an isolated directory per call, so
    concurrent proof generation/verification requests never race on a
    shared Prover.toml / Verifier.toml / proofs/ directory."""
    dest = tmp_root / "circuit"
    shutil.copytree(
        _circuit_source_path(),
        dest,
        ignore=shutil.ignore_patterns("target", "proofs", ".git", "__pycache__"),
    )
    return dest


def _scale(value: float, scale_factor: int, field_name: str) -> int:
    if value < 0:
        raise ProofGenerationError(f"{field_name} must be non-negative, got {value}")
    return round(value * scale_factor)


async def generate_zk_proof(nrs: float, threshold: float, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    scale_factor = getattr(settings, "nrs_scale_factor", 1_000_000)

    nrs_scaled = _scale(nrs, scale_factor, "nrs")
    threshold_scaled = _scale(threshold, scale_factor, "threshold")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            circuit_dir = _isolated_circuit_copy(Path(tmpdir))
            (circuit_dir / "Prover.toml").write_text(
                f"risk_score = {nrs_scaled}\nthreshold = {threshold_scaled}\n"
            )

            returncode, _stdout, stderr = await _run_subprocess(
                ["nargo", "prove"], cwd=circuit_dir, timeout=_PROVE_TIMEOUT_SECONDS
            )
            if returncode != 0:
                raise ProofGenerationError(f"nargo prove failed: {stderr[:2000]}")

            proof_path = circuit_dir / "proofs" / _PROOF_FILENAME
            if not proof_path.exists():
                raise ProofGenerationError(
                    "nargo prove reported success but no proof file was found at "
                    f"proofs/{_PROOF_FILENAME} — confirm the output filename your "
                    "installed nargo actually writes and update _PROOF_FILENAME."
                )
            proof_hex = proof_path.read_bytes().hex()

        logger.info("zk proof generated", extra={"threshold_scaled": threshold_scaled})
        return {
            "proof_hex": proof_hex,
            "public_inputs": [threshold_scaled],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except FileNotFoundError:
        raise ProofGenerationError("nargo not installed or not on PATH")
    except TimeoutError as exc:
        raise ProofGenerationError(
            f"Proof generation timed out after {_PROVE_TIMEOUT_SECONDS} seconds"
        ) from exc


async def verify_proof_local(proof_hex: str, public_inputs: list[int]) -> bool:
    if not public_inputs:
        logger.error("verify_proof_local called with empty public_inputs")
        return False
    if not proof_hex:
        logger.error("verify_proof_local called with empty proof_hex")
        return False

    try:
        proof_bytes = bytes.fromhex(proof_hex)
    except ValueError:
        logger.error("verify_proof_local called with non-hex proof_hex")
        return False

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            circuit_dir = _isolated_circuit_copy(Path(tmpdir))
            (circuit_dir / "Verifier.toml").write_text(f"threshold = {public_inputs[0]}\n")

            proofs_dir = circuit_dir / "proofs"
            proofs_dir.mkdir(exist_ok=True)
            # Round-trip the actual proof being checked back onto disk —
            # previously this never happened, so `nargo verify` checked
            # whatever proof file happened to already exist in the shared
            # circuits/ directory instead of the one passed in here.
            (proofs_dir / _PROOF_FILENAME).write_bytes(proof_bytes)

            returncode, _stdout, stderr = await _run_subprocess(
                ["nargo", "verify"], cwd=circuit_dir, timeout=_VERIFY_TIMEOUT_SECONDS
            )

        if returncode == 0:
            logger.info("zk proof verified locally")
            return True

        logger.warning("proof verification failed", extra={"stderr": stderr[:2000]})
        return False

    except FileNotFoundError:
        logger.error("nargo not installed or not on PATH")
        return False
    except TimeoutError:
        logger.error("verification timed out after %s seconds", _VERIFY_TIMEOUT_SECONDS)
        return False