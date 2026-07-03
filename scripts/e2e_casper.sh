#!/bin/bash
set -e

echo "Running Casper E2E Tests..."

cd /home/ed/projects/stellcasp/casper

# Build contracts
cargo build --target wasm32-unknown-unknown --release

# Deploy ComplianceOracle
COMPLIANCE_HASH=$(casper-client put-deploy \
    --session-path target/wasm32-unknown-unknown/release/compliance_oracle.wasm \
    --address-hash $(cat /run/secrets/casper-deploy-key) \
    --chain-name casper-test \
    --node-address https://rpc.testnet.cspr.network \
    --secret-key-file /run/secrets/casper-deploy-key \
    --payment-amount 100000000 \
    --session-entry-point constructor \
    --session-arg "mint_authority:string='$(cat /run/secrets/casper-deploy-key)'" \
    | jq -r '.result.blockHash')

echo "ComplianceOracle deployed: $COMPLIANCE_HASH"

# Deploy IdentityRegistry
REGISTRY_HASH=$(casper-client put-deploy \
    --session-path target/wasm32-unknown-unknown/release/identity_registry.wasm \
    --address-hash $(cat /run/secrets/casper-deploy-key) \
    --chain-name casper-test \
    --node-address https://rpc.testnet.cspr.network \
    --secret-key-file /run/secrets/casper-deploy-key \
    --payment-amount 100000000 \
    --session-entry-point constructor \
    --session-arg "compliance_oracle_address:string='$COMPLIANCE_HASH'" \
    | jq -r '.result.blockHash')

echo "IdentityRegistry deployed: $REGISTRY_HASH"

# Record results
jq -n --arg oracle "$COMPLIANCE_HASH" --arg registry "$REGISTRY_HASH" \
    '{compliance_oracle_contract: $oracle, identity_registry_contract: $registry}' \
    > /home/ed/projects/stellcasp/deployments.json

echo "E2E Tests completed successfully"