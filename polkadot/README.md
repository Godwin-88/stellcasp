# Polkadot Smart Contracts

ZK-KYC Passport smart contracts for Polkadot parachains (ink! 4.3, Wasm).

## Contracts

- `ComplianceVerifier` — ZK proof verification pallet
- `CompliancePassport` — Soulbound passport pallet

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  ComplianceVerifier                                          │
│  - verify(proof, public_inputs) → Result<bool, Error>        │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for ink!      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CompliancePassport                                          │
│  - mint_passport(subject) → Result<u32, Error>               │
│  - revoke_passport(subject) → Result<(), Error>              │
│  - verify_credential(subject) → Result<bool, Error>          │
│  SPEC: EP-08 F-08.4 — Polkadot Passport Adapter             │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for Polkadot)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via ComplianceVerifier
3. `mint_passport()` called by contract owner
4. `verify_credential()` callable by any downstream parachain pallet
5. `revoke_passport()` callable by contract owner

## Grant Pipeline

- **Web3 Foundation Grants** — "Bring DeFi compliance infrastructure to Polkadot parachains"
- **Polkadot Treasury** — "ZK compliance verifier for parachain ecosystems"

## Prerequisites

- Rust 1.75+
- [cargo-contract](https://github.com/paritytech/cargo-contract) 3.0+
- Substrate node (rococo-dev, paseo, or custom parachain)

## Setup

```bash
cargo install cargo-contract --force
```

## Build

```bash
cd contracts
cargo contract build --release
```

## Test

```bash
cargo test
```

## Deploy

```bash
export SURI=//Alice
bash scripts/deploy.sh rococo-dev
```

## Supported Chains

- Rococo Development
- Paseo Testnet
- Polkadot Relay Chain (via parachain)
- Custom parachains
