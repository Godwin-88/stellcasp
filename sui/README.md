# Sui Smart Contracts

ZK-KYC Passport smart contracts for Sui (Move VM).

## Contracts

- `zk_passport.move` — Move module with verifier and soulbound passport

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  zk_passport.move                                            │
│  - verify_proof(proof, public_inputs) → bool                 │
│  - mint_passport(subject) → UID                               │
│  - revoke_passport(subject)                                  │
│  - verify_credential(subject) → bool                         │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for Move       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Soulbound Passport Object                                   │
│  - Compliance passport as Sui object with freeze_object      │
│  - verify_credential(subject) → object ownership check       │
│  SPEC: EP-08 F-08.7 — Sui Passport Adapter                  │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for Sui)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via Move verifier
3. `mint_passport()` creates a soulbound object
4. `verify_credential()` checks object ownership
5. `revoke_passport()` transfers object to black hole

## Grant Pipeline

- **Sui Foundation ZK Working Group** — "Soulbound compliance credentials on Sui"
- **Sui Foundation DeFi Grants** — "ZK-verified compliance for Sui DeFi"

## Prerequisites

- Sui CLI 1.0+
- Move compiler

## Setup

```bash
sui --version
```

## Build

```bash
sui move build --skip-fetch-latest-git-deps
```

## Test

```bash
sui move test
```

## Deploy

```bash
bash scripts/deploy.sh testnet
```

## Supported Networks

- Sui Testnet
- Sui Mainnet
