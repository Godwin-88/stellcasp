#!/bin/bash
set -e

echo "Running Stellar E2E Tests..."

cd /home/ed/projects/stellcasp/stellar

cargo build --target wasm32-unknown-unknown --release

# Strip reference-types from the WASM binary (Stellar testnet runtime doesn't
# support that feature).  wasm2wat/wat2wasm are both distributed with wabt.
WASM_SRC="target/wasm32-unknown-unknown/release/zkkyc_verifier.wasm"
WASM_CLEAN="target/wasm32-unknown-unknown/release/zkkyc_verifier_clean.wasm"
wasm2wat "$WASM_SRC" -o /tmp/zkkyc_no_ref.wat
wat2wasm /tmp/zkkyc_no_ref.wat -o "$WASM_CLEAN"

CONTRACT_HASH=$(stellar contract deploy \
    --wasm "$WASM_CLEAN" \
    --network testnet \
    --source-account deployer)

echo "Verifier deployed: $CONTRACT_HASH"

jq -n --arg verifier "$CONTRACT_HASH" '{"verifier_contract": $verifier}' \
    > /home/ed/projects/testing/deployments.json

echo "E2E Tests completed successfully"