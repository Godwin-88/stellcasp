#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env" 2>/dev/null || true

NETWORK=${1:-local}

echo "Deploying ZK Passport to ICP $NETWORK..."

if [ "$NETWORK" = "local" ]; then
    dfx start --background --clean
    dfx deploy
else
    dfx deploy --network ic
fi

echo "Deployment complete!"
