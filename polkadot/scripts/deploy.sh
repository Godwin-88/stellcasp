#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

source "$ROOT_DIR/.env" 2>/dev/null || true

CHAIN=${1:-rococo-dev}

echo "Building Polkadot ink! contracts..."
cd "$ROOT_DIR/contracts"
cargo contract build --release

echo "Deploying ComplianceVerifier to $CHAIN..."
cargo contract instantiate \
  --suri "$SURI" \
  --url "wss://$CHAIN.api.onfinality.io/public-ws" \
  --constructor new \
  --salt 0x0000000000000000000000000000000000000000000000000000000000000001 \
  --gas 100000000000 \
  --proof-size 10000000 \
  --skip-confirm

echo "Deploying CompliancePassport to $CHAIN..."
cargo contract instantiate \
  --suri "$SURI" \
  --url "wss://$CHAIN.api.onfinality.io/public-ws" \
  --constructor new \
  --salt 0x0000000000000000000000000000000000000000000000000000000000000002 \
  --gas 100000000000 \
  --proof-size 10000000 \
  --skip-confirm

echo "Deployment complete!"
