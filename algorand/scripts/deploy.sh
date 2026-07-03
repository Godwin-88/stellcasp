#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env"

CHAIN=${1:-testnet}

echo "Deploying ZK Passport to Algorand $CHAIN..."

python3 "$SCRIPT_DIR/deploy.py"

echo "Deployment complete!"
