#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env" 2>/dev/null || true

NETWORK=${1:-testnet}

echo "Deploying ZK Passport to Aptos $NETWORK..."

cd "$ROOT_DIR"

if [ "$NETWORK" = "testnet" ]; then
    aptos move publish --named-addresses zkkyc=default --profile default
else
    aptos move publish --named-addresses zkkyc=default --profile mainnet
fi

echo "Deployment complete!"
