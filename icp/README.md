# ICP Compliance Passport Canister

ZK-KYC Passport canister for ICP/DFINITY (Internet Computer).

## Contracts

- `src/lib.rs` — Rust canister with verifier and passport functions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  lib.rs (Rust Canister)                                      │
│  - verify_proof(proof, public_inputs) → bool                 │
│  - mint_passport(principal) → passport_id                    │
│  - revoke_passport(passport_id)                              │
│  - verify_credential(principal) → bool                       │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for ICP       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Internet Identity-Linked Passport                           │
│  - Compliance passport linked to II principal                │
│  - verify_credential(principal) → passport status            │
│  SPEC: EP-08 F-08.9 — ICP Passport Adapter                  │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for ICP)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via canister verifier
3. `mint_passport()` creates a passport record linked to II principal
4. `verify_credential()` checks passport status
5. `revoke_passport()` marks passport as revoked

## Grant Pipeline

- **DFINITY Foundation** — "ZK-verified compliance on Internet Computer"
- **ICP Developer Grants** — "Canister-based ZK compliance infrastructure"

## Prerequisites

- [DFX](https://internetcomputer.org/docs/current/developer-docs/setup/install/) 0.14+
- Rust 1.75+
- Cargo

## Setup

```bash
dfx start --background
dfx identity new zkkyc
```

## Build

```bash
cargo build --target wasm32-unknown-unknown --release
```

## Test

```bash
dfx deploy --playground
```

## Deploy

```bash
bash scripts/deploy.sh local
```

## Supported Networks

- ICP Local (dfx)
- ICP Mainnet
