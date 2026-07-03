cd /home/ed/projects/stellcasp/stellar/passport

# Clean any failed artifacts
cargo clean

# Build with Soroban-safe flags
stellar contract build

# Verify the WASM was created
ls -lh target/wasm32v1-none/release/zkkyc_passport.wasm

# Deploy to testnet
PASSPORT_HASH=$(stellar contract deploy \
    --wasm target/wasm32v1-none/release/zkkyc_passport.wasm \
    --network testnet \
    --source-account deployer)

echo "✅ Passport deployed: $PASSPORT_HASH"

# Initialize with oracle authority and verifier address
ORACLE_AUTHORITY=$(stellar keys show deployer)
VERIFIER_ADDRESS="CAMJ7HBLEV2655BDEDCBEOHULD6Y2SUZKGHLFXWE3CBDIWR3STMQSOMI"

stellar contract invoke \
    --id "$PASSPORT_HASH" \
    --network testnet \
    --source-account deployer \
    -- \
    initialise \
    --oracle_authority "$ORACLE_AUTHORITY" \
    --verifier_contract "$VERIFIER_ADDRESS"

echo "✅ Passport initialized"

# Update deployments.json
cd /home/ed/projects/stellcasp
jq --arg passport "$PASSPORT_HASH" \
   '.stellar_testnet.passport_contract = $passport' \
   deployments.json > /tmp/deployments_tmp.json \
   && mv /tmp/deployments_tmp.json deployments.json

echo "✅ deployments.json updated"

# Test the deployment
stellar contract invoke \
    --id "$PASSPORT_HASH" \
    --network testnet \
    --source-account deployer \
    -- \
    verify_credential \
    --wallet "$ORACLE_AUTHORITY" \
    --policy_id policy_v1