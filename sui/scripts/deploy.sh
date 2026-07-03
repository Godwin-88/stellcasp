#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env" 2>/dev/null || true

NETWORK=${1:-testnet}

echo "Deploying ZK Passport to Sui $NETWORK..."

cd "$ROOT_DIR"

sui move build --skip-fetch-latest-git-deps

if [ "$NETWORK" = "testnet" ]; then
    sui client publish --gas-budget 100000000 --skip-future-compatibility-check
else
    sui client publish --gas-budget 100000000 --skip-future-compatibility-check --rpc-url https://fullnode.mainnet.sui.io:443
fi

echo "Deployment complete!"
