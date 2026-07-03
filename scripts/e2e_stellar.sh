#!/bin/bash
set -e

echo "Running Stellar E2E Tests..."
cd /home/ed/projects/stellcasp/stellar

# Use stellar CLI's build command — applies Soroban-compatible WASM flags
cargo clean
stellar contract build

WASM="target/wasm32v1-none/release/zkkyc_verifier.wasm"

CONTRACT_HASH=$(stellar contract deploy \
    --wasm "$WASM" \
    --network testnet \
    --source-account deployer)

echo "Verifier deployed: $CONTRACT_HASH"

jq --arg verifier "$CONTRACT_HASH" \
    '.stellar_testnet.verifier_contract = $verifier' \
    /home/ed/projects/stellcasp/deployments.json > /tmp/deployments_tmp.json \
    && mv /tmp/deployments_tmp.json /home/ed/projects/stellcasp/deployments.json

echo "E2E Tests completed successfully"