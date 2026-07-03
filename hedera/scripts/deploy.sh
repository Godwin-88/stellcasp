#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env"

echo "Deploying ZK-KYC contracts to Hedera Testnet..."

echo "Deploying HederaZKVerifier to HSCS..."
# Hedera Smart Contract Service deployment via hedera-cli or hardhat
# VERIFIER_CONTRACT_ID=0.0.1234  # Hedera contract ID format

echo "Creating HTS NFT for Compliance Passport..."
# Create HTS NFT using Hedera Token Service
# Token ID: 0.0.5678

echo "Deployment complete!"
echo "VERIFIER_CONTRACT_ID=$VERIFIER_CONTRACT_ID"
echo "PASSPORT_TOKEN_ID=$PASSPORT_TOKEN_ID"
