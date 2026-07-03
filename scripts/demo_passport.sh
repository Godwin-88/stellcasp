#!/usr/bin/env bash
# --------------------------------------------------------------------------
# Compliance Passport — End-to-End Demo Script
# scripts/demo_passport.sh
#
# Spec: EP-03, F-03.1 (US-03.1.3)
#       EP-02, F-02.2 (US-02.2.1, US-02.2.2)
#
# Demonstrates the full Compliance Passport flow on Stellar testnet:
#   1. Multi-factor CI computation + 3-condition ZK proof generation
#   2. Soroban verify_and_attest on the ComplianceVerifier contract
#   3. CompliancePassport mint (non-transferable, policy-bound)
#   4. Dual-protocol verify: same passport checked from DEX + lending contexts
#
# Usage:
#   ./scripts/demo_passport.sh [entity_id]
#
# Environment variables (required):
#   ENTITY_ID              — demo wallet identifier (default: demo_wallet_001)
#   CI_THRESHOLD           — policy CI ceiling (default: 0.75)
#   MANIFOLD_THRESHOLD     — minimum manifold score (default: 0.20)
#   POLICY_ID              — policy version identifier (default: policy_v1)
#   STELLAR_VERIFIER_CONTRACT_ID  — deployed ComplianceVerifier address
#   STELLAR_PASSPORT_CONTRACT_ID  — deployed CompliancePassport address
#   STELLAR_SOURCE_SECRET         — S... secret key for tx signing
#   STELLAR_ORACLE_AUTHORITY      — Address of the oracle authority
#
# Exit codes:
#   0 — success (all four steps completed, dual-protocol verify returned valid=true)
#   1 — proof generation or verification failed
#   2 — on-chain dispatch failed
#   3 — prerequisites missing
# --------------------------------------------------------------------------
set -euo pipefail

# --------------------------------------------------------------------------
# Constants & colours
# --------------------------------------------------------------------------
readonly SCRIPT_NAME="$(basename "$0")"
readonly TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------
ENTITY_ID="${ENTITY_ID:-${1:-demo_wallet_001}}"
CI_THRESHOLD="${CI_THRESHOLD:-0.75}"
MANIFOLD_THRESHOLD="${MANIFOLD_THRESHOLD:-0.20}"
POLICY_ID="${POLICY_ID:-policy_v1}"
PASSPORT_EXPIRY_HOURS="${PASSPORT_EXPIRY_HOURS:-24}"

# Tx hash accumulator — printed in the final summary
declare -a TX_HASHES=()
declare -a STEP_LABELS=()

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }

record_tx() {
    # record_tx <label> <tx_hash>
    local label="$1" tx_hash="$2"
    TX_HASHES+=("$tx_hash")
    STEP_LABELS+=("$label")
    log_ok "$label → $tx_hash"
}

die() { log_error "$*"; exit 1; }

require_env() {
    local var="$1"
    if [[ -z "${!var:-}" ]]; then
        die "Required environment variable not set: $var"
    fi
}

check_prereqs() {
    log_step "Step 0 / Pre-flight checks"
    command -v python3 >/dev/null 2>&1 || die "python3 not found on PATH"
    python3 -c "import zkkyc" 2>/dev/null || \
        die "zkkyc package not importable — run 'pip install -e .' first"

    # stellar CLI is optional — Python fallback handles on-chain calls
    if command -v stellar >/dev/null 2>&1; then
        log_ok "stellar CLI detected: $(stellar --version 2>/dev/null || echo 'unknown')"
        USE_STELLAR_CLI=1
    else
        log_warn "stellar CLI not found — using Python stellar-sdk fallback"
        USE_STELLAR_CLI=0
    fi

    require_env STELLAR_VERIFIER_CONTRACT_ID
    require_env STELLAR_PASSPORT_CONTRACT_ID
    require_env STELLAR_SOURCE_SECRET
    require_env STELLAR_ORACLE_AUTHORITY
    log_ok "All required env vars present"
}

# --------------------------------------------------------------------------
# Step 1 — Generate ZK proof (3-condition: CI + manifold + jurisdiction)
# --------------------------------------------------------------------------
step_generate_proof() {
    log_step "Step 1 / Generate 3-condition ZK proof"
    log_info "entity_id          = $ENTITY_ID"
    log_info "ci_threshold       = $CI_THRESHOLD"
    log_info "manifold_threshold = $MANIFOLD_THRESHOLD"
    log_info "policy_id          = $POLICY_ID"

    # The Python helper returns a JSON blob with proof_hex, public_inputs,
    # entity_hash, and the computed CI/manifold/jurisdiction values (for
    # logging only — the private witnesses are never written to disk).
    local py_script
    py_script="$(mktemp /tmp/demo_proof_XXXXXX.py)"
    cat > "$py_script" <<'PYEOF'
import asyncio
import json
import sys
from zkkyc.graph.nrs import CIEngine
from zkkyc.zk.proof import generate_zk_proof
from zkkyc.graph.entity import EntityService

async def main():
    entity_id, ci_thr, man_thr, policy_id = sys.argv[1:5]
    engine = CIEngine(entity_service=EntityService())
    ci_result = await engine.compute_compliance_index(entity_id)
    proof = await generate_zk_proof(
        ci=ci_result.compliance_index,
        manifold_score=ci_result.manifold_score,
        jurisdiction_flag=ci_result.jurisdiction_flag,
        ci_threshold=float(ci_thr),
        manifold_threshold=float(man_thr),
        policy_id=policy_id,
    )
    from zkkyc.graph.entity import hash_entity_id
    entity_hash = hash_entity_id(entity_id)
    out = {
        "proof_hex": proof["proof_hex"],
        "public_inputs": proof["public_inputs"],
        "entity_hash": entity_hash,
        "policy_id": policy_id,
        "ci": ci_result.compliance_index,
        "manifold_score": ci_result.manifold_score,
        "jurisdiction_flag": ci_result.jurisdiction_flag,
    }
    print(json.dumps(out))

asyncio.run(main())
PYEOF
    local proof_json
    proof_json="$(python3 "$py_script" "$ENTITY_ID" "$CI_THRESHOLD" "$MANIFOLD_THRESHOLD" "$POLICY_ID")" || die "Proof generation failed"
    rm -f "$py_script"

    # Parse the JSON into shell variables using python (jq-free)
    PROOF_HEX="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['proof_hex'])" "$proof_json")"
    PUBLIC_INPUTS_JSON="$(python3 -c "import json,sys; print(json.dumps(json.loads(sys.argv[1])['public_inputs']))" "$proof_json")"
    ENTITY_HASH="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['entity_hash'])" "$proof_json")"

    log_ok "Proof generated (${#PROOF_HEX} hex chars)"
    log_info "entity_hash        = $ENTITY_HASH"
    log_info "public_inputs      = $PUBLIC_INPUTS_JSON"
    log_info "NOTE: CI, manifold_score, jurisdiction_flag are PRIVATE witnesses"
    log_info "      and are NOT included in the proof or any log output."
}

# --------------------------------------------------------------------------
# Step 2 — Submit proof to Stellar Soroban verifier
# --------------------------------------------------------------------------
step_verify_on_chain() {
    log_step "Step 2 / Soroban verify_and_attest"
    log_info "verifier_contract  = $STELLAR_VERIFIER_CONTRACT_ID"

    local py_script
    py_script="$(mktemp /tmp/demo_verify_XXXXXX.py)"
    cat > "$py_script" <<'PYEOF'
import asyncio
import json
import sys
from zkkyc.zk.stellar import submit_proof_stellar

async def main():
    proof_hex, pi_json, entity_hash, policy_id = sys.argv[1:5]
    public_inputs = json.loads(pi_json)
    tx_hash = await submit_proof_stellar(
        proof_hex=proof_hex,
        public_inputs=public_inputs,
        entity_hash=entity_hash,
        policy_id=policy_id,
    )
    print(tx_hash)

asyncio.run(main())
PYEOF
    local tx_hash
    tx_hash="$(python3 "$py_script" "$PROOF_HEX" "$PUBLIC_INPUTS_JSON" "$ENTITY_HASH" "$POLICY_ID")" || die "Soroban verify_and_attest failed"
    rm -f "$py_script"

    VERIFIER_TX_HASH="$tx_hash"
    record_tx "verify_and_attest" "$VERIFIER_TX_HASH"
}

# --------------------------------------------------------------------------
# Step 3 — Mint Compliance Passport
# --------------------------------------------------------------------------
step_mint_passport() {
    log_step "Step 3 / Mint Compliance Passport"
    log_info "passport_contract  = $STELLAR_PASSPORT_CONTRACT_ID"
    log_info "wallet             = $STELLAR_ORACLE_AUTHORITY"
    log_info "policy_id          = $POLICY_ID"
    log_info "expiry_hours       = $PASSPORT_EXPIRY_HOURS"

    # Compute expires_at as UNIX timestamp (now + N hours)
    local expires_at
    expires_at="$(python3 -c "import time; print(int(time.time()) + $PASSPORT_EXPIRY_HOURS * 3600)")"

    # Compute proof_hash = SHA-256(proof_hex bytes) — matches verifier_lib.rs
    local proof_hash
    proof_hash="$(python3 -c "import hashlib,sys; print(hashlib.sha256(bytes.fromhex(sys.argv[1])).hexdigest())" "$PROOF_HEX")"

    local tx_hash
    if [[ "$USE_STELLAR_CLI" == "1" ]]; then
        tx_hash="$(stellar contract invoke \
            --id "$STELLAR_PASSPORT_CONTRACT_ID" \
            --network testnet \
            --source-account "$STELLAR_SOURCE_SECRET" \
            -- \
            mint_passport \
            --wallet "$STELLAR_ORACLE_AUTHORITY" \
            --policy_id "$POLICY_ID" \
            --expires_at "$expires_at" \
            --proof_hash "$proof_hash" \
            --entity_hash "$ENTITY_HASH" \
            | python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('hash',''))" \
        )" || die "mint_passport invocation failed"
    else
        # Python fallback via stellar-sdk
        local py_script
        py_script="$(mktemp /tmp/demo_mint_XXXXXX.py)"
        cat > "$py_script" <<'PYEOF'
import asyncio
import sys
from zkkyc.zk.stellar import _mint_passport_fallback

async def main():
    contract_id, wallet, policy_id, expires_at, proof_hash, entity_hash = sys.argv[1:7]
    tx_hash = await _mint_passport_fallback(
        contract_id=contract_id,
        wallet=wallet,
        policy_id=policy_id,
        expires_at=int(expires_at),
        proof_hash=proof_hash,
        entity_hash=entity_hash,
    )
    print(tx_hash)

asyncio.run(main())
PYEOF
        tx_hash="$(python3 "$py_script" "$STELLAR_PASSPORT_CONTRACT_ID" "$STELLAR_ORACLE_AUTHORITY" \
                       "$POLICY_ID" "$expires_at" "$proof_hash" "$ENTITY_HASH")" || die "mint_passport (Python fallback) failed"
        rm -f "$py_script"
    fi

    PASSPORT_MINT_TX_HASH="$tx_hash"
    record_tx "mint_passport" "$PASSPORT_MINT_TX_HASH"
}

# --------------------------------------------------------------------------
# Step 4 — Dual-protocol verify (DEX + lending contexts)
# --------------------------------------------------------------------------
step_dual_protocol_verify() {
    log_step "Step 4 / Dual-protocol credential verification"

    # The SAME passport is verified from two simulated protocol contexts.
    # This is the load-bearing demo of US-03.1.3 — one proof, many protocols.
    local contexts=("DEX" "LENDING")
    local results=()

    for ctx in "${contexts[@]}"; do
        log_info "Simulating $ctx protocol context..."

        local valid expires_at
        if [[ "$USE_STELLAR_CLI" == "1" ]]; then
            local invoke_out
            invoke_out="$(stellar contract invoke \
                --id "$STELLAR_PASSPORT_CONTRACT_ID" \
                --network testnet \
                -- \
                verify_credential \
                --wallet "$STELLAR_ORACLE_AUTHORITY" \
                --policy_id "$POLICY_ID" \
            )" || die "verify_credential invocation failed for $ctx"
            valid="$(echo "$invoke_out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d[0] if isinstance(d,list) else d.get('valid',False))")"
            expires_at="$(echo "$invoke_out" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d[1] if isinstance(d,list) else d.get('expires_at',0))")"
        else
            # Python fallback — read-only view call via simulation
            local py_script
            py_script="$(mktemp /tmp/demo_verify_cred_XXXXXX.py)"
            cat > "$py_script" <<'PYEOF'
import asyncio
import json
import sys
from zkkyc.zk.stellar import _verify_credential_fallback

async def main():
    contract_id, wallet, policy_id = sys.argv[1:4]
    result = await _verify_credential_fallback(
        contract_id=contract_id,
        wallet=wallet,
        policy_id=policy_id,
    )
    print(json.dumps(result))

asyncio.run(main())
PYEOF
            local view_out
            view_out="$(python3 "$py_script" "$STELLAR_PASSPORT_CONTRACT_ID" "$STELLAR_ORACLE_AUTHORITY" "$POLICY_ID")" || die "verify_credential (Python fallback) failed for $ctx"
            rm -f "$py_script"
            valid="$(echo "$view_out" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['valid'])")"
            expires_at="$(echo "$view_out" | python3 -c "import json,sys; print(json.loads(sys.stdin.read())['expires_at'])")"
        fi

        if [[ "$valid" == "True" || "$valid" == "true" ]]; then
            log_ok "$ctx context → {valid: true, expires_at: $expires_at}"
            results+=("$ctx:PASS")
        else
            log_error "$ctx context → {valid: false, expires_at: $expires_at}"
            results+=("$ctx:FAIL")
        fi
    done

    # Both contexts must return valid=true for the demo to succeed
    local fail_count=0
    for r in "${results[@]}"; do
        [[ "$r" == *":FAIL" ]] && ((fail_count++)) || true
    done
    if [[ $fail_count -gt 0 ]]; then
        die "Dual-protocol verify failed for $fail_count context(s)"
    fi
    log_ok "Same passport verified from both DEX and lending contexts — no re-KYC"
}

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
print_summary() {
    log_step "Demo Summary"
    echo ""
    echo -e "${CYAN}┌─────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│  Zero-Knowledge Compliance Oracle — Passport Demo                   │${NC}"
    echo -e "${CYAN}│  Stellar Testnet · $(date -u +%Y-%m-%d)                                       │${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────┤${NC}"
    printf "${CYAN}│${NC}  ${GREEN}%-22s${NC} %-48s ${CYAN}│${NC}\n" "entity_id" "$ENTITY_ID"
    printf "${CYAN}│${NC}  ${GREEN}%-22s${NC} %-48s ${CYAN}│${NC}\n" "entity_hash" "$ENTITY_HASH"
    printf "${CYAN}│${NC}  ${GREEN}%-22s${NC} %-48s ${CYAN}│${NC}\n" "policy_id" "$POLICY_ID"
    printf "${CYAN}│${NC}  ${GREEN}%-22s${NC} %-48s ${CYAN}│${NC}\n" "verifier_contract" "${STELLAR_VERIFIER_CONTRACT_ID:0:14}..."
    printf "${CYAN}│${NC}  ${GREEN}%-22s${NC} %-48s ${CYAN}│${NC}\n" "passport_contract" "${STELLAR_PASSPORT_CONTRACT_ID:0:14}..."
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}  ${YELLOW}Transaction hashes:${NC}                                                   ${CYAN}│${NC}"
    for i in "${!STEP_LABELS[@]}"; do
        printf "${CYAN}│${NC}    • %-18s %s ${CYAN}│${NC}\n" "${STEP_LABELS[$i]}" "${TX_HASHES[$i]}"
    done
    echo -e "${CYAN}├─────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC}  ${GREEN}✓${NC} 3-condition ZK proof: CI < threshold ∧ manifold ≥ threshold ∧ jurisdiction permitted"
    echo -e "${CYAN}│${NC}  ${GREEN}✓${NC} On-chain attestation persisted on Stellar Soroban"
    echo -e "${CYAN}│${NC}  ${GREEN}✓${NC} Compliance Passport minted (non-transferable, policy-bound)"
    echo -e "${CYAN}│${NC}  ${GREEN}✓${NC} Same passport verified from DEX + lending contexts (no re-KYC)"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
    echo -e "${YELLOW}PII guarantee:${NC} Only entity_hash (SHA-256) is on-chain. Raw entity ID,"
    echo -e "CI value, factor weights, and graph topology are never exposed."
    echo ""
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
main() {
    log_info "$SCRIPT_NAME started at $TIMESTAMP"
    check_prereqs
    step_generate_proof
    step_verify_on_chain
    step_mint_passport
    step_dual_protocol_verify
    print_summary
    log_ok "Demo completed successfully"
}

main "$@"