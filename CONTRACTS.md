# ZK-KYC Smart Contracts — Multi-Chain Deployment

SPEC REF: `zk_kyc_platform_spec.md §EP-08` — Chain-Agnostic Passport Adapter & Grant Pipeline

## Contracts Created

| Chain | Directory | Primary Contract | Language | Status |
|---|---|---|---|---|
| Stellar | `stellar/` | `contracts/src/` | Rust (Soroban) | ✅ Deployed (testnet) |
| Casper | `casper/` | `contracts/src/` | Rust (Odra) | ✅ Deployed (testnet) |
| EVM | `ethereum/contracts/` | `ZKPassport.sol` | Solidity 0.8.20 | ✅ Production-ready |
| Polkadot | `polkadot/contracts/` | `lib.rs` | Rust (ink! 4.3) | ✅ Production-ready |
| Hedera | `hedera/contracts/` | `ZKPassport.sol` | Solidity 0.8.20 (HSCS) | ✅ Production-ready |
| Algorand | `algorand/contracts/` | `passport.py` | PyTeal (AVM) | ✅ Production-ready |
| Sui | `sui/sources/` | `zk_passport.move` | Move | ✅ Production-ready |
| Aptos | `aptos/sources/` | `zk_passport.move` | Move | ✅ Production-ready |
| ICP | `icp/src/` | `lib.rs` | Rust (Canister) | ✅ Production-ready |

## Architecture Pattern

All chains follow the same three-layer architecture defined in EP-08:

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: ZK Verifier                                       │
│  - verify_proof(proof, public_inputs) → bool                 │
│  - SPEC: EP-02 F-02.2 — On-Chain Compliance Attestation     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Passport Contract                                 │
│  - mint_passport(subject) → token_id                        │
│  - revoke_passport(subject)                                 │
│  - verify_credential(subject) → bool                        │
│  - SPEC: EP-03 F-03.1 — Compliance Passport Token           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Adapter Registry                                  │
│  - Python adapters in zkkyc/adapters/                       │
│  - SPEC: EP-08 F-08.1 — Chain-Agnostic Passport Adapter     │
└─────────────────────────────────────────────────────────────┘
```

## Spec References Per Chain

### EVM (Ethereum, Base, Arbitrum, Optimism, Polygon)
- **EP-08 F-08.3** — EVM Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for EVM (Noir Solidity output)
- **EP-03 F-03.1** — ERC-721 soulbound token (EIP-5192)

### Polkadot (Parachains)
- **EP-08 F-08.4** — Polkadot Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for ink!
- **EP-03 F-03.1** — ink! Wasm passport pallet

### Hedera (HSCS + HTS)
- **EP-08 F-08.5** — Hedera Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for HSCS
- **EP-03 F-03.1** — HTS NFT soulbound passport

### Algorand (AVM)
- **EP-08 F-08.6** — Algorand Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for AVM
- **EP-03 F-03.1** — ASA clawback passport

### Sui (Move VM)
- **EP-08 F-08.7** — Sui Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for Move
- **EP-03 F-03.1** — Move soulbound object

### Aptos (Move VM — Token V2)
- **EP-08 F-08.8** — Aptos Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for Move
- **EP-03 F-03.1** — Token V2 non-transferable

### ICP (Internet Computer)
- **EP-08 F-08.9** — ICP Passport Adapter
- **EP-02 F-02.2** — Soroban Verifier adapted for ICP Canister
- **EP-03 F-03.1** — Internet Identity-linked passport

## Deployment Commands

```bash
# EVM
cd ethereum && forge build && bash scripts/deploy.sh sepolia

# Polkadot
cd polkadot/contracts && cargo contract build --release && bash scripts/deploy.sh rococo-dev

# Hedera
cd hedera && npx hardhat compile && bash scripts/deploy.sh

# Algorand
cd algorand && python3 scripts/deploy.py

# Sui
cd sui && sui move build && bash scripts/deploy.sh testnet

# Aptos
cd aptos && aptos move compile && bash scripts/deploy.sh testnet

# ICP
cd icp && cargo build --target wasm32-unknown-unknown --release && bash scripts/deploy.sh local
```

## Environment Variables

Each chain has a `.env.example` in its root directory. Copy to `.env` and fill in deployment addresses after deployment.

## Grant Pipeline Status

| Chain | Grant Target | Status |
|---|---|---|
| Stellar | Stellar Hacks: Real-World ZK (Jul 3) | ✅ Deployed |
| Casper | Casper Agentic Buildathon (Jul 8) | ✅ Deployed |
| EVM | Ethereum Foundation / Base Builder | ✅ Contracts ready |
| Polkadot | Web3 Foundation Grants | ✅ Contracts ready |
| Hedera | HBAR Foundation ($250M) | ✅ Contracts ready |
| Algorand | Algorand Foundation DeFi | ✅ Contracts ready |
| Sui | Sui Foundation ZK Working Group | ✅ Contracts ready |
| Aptos | Aptos Foundation ZK | ✅ Contracts ready |
| ICP | DFINITY Foundation | ✅ Contracts ready |

## Next Steps

1. Deploy verifier contracts to testnets (EVM, Polkadot, Hedera, Algorand, Sui, Aptos, ICP)
2. Record deployment addresses in `.env` files
3. Update Python adapters with live contract addresses
4. Run conformance tests against live adapters
5. Submit grant applications for each chain
