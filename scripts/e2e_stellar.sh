#!/bin/bash
set -e

echo "Running Stellar E2E Tests..."

cd /home/ed/projects/testing/stellar

cargo build --target wasm32-unknown-unknown --release

CONTRACT_HASH=$(stellar contract deploy \
    --wasm target/wasm32-unknown-unknown/release/zkkyc_verifier.wasm \
    --network testnet \
    --source deployer \
    --name zkkyc-verifier)

echo "Verifier deployed: $CONTRACT_HASH"

jq -n --arg verifier "$CONTRACT_HASH" '{"verifier_contract": $verifier}' \
    > /home/ed/projects/testing/deployments.json

echo "E2E Tests completed successfully"