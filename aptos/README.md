# Aptos Smart Contracts

ZK-KYC Passport smart contracts for Aptos (Move VM — Token V2).

## Contracts

- `zk_passport.move` — Move module with verifier and non-transferable token

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  zk_passport.move                                            │
│  - verify_proof(proof, public_inputs) → bool                 │
│  - mint_passport(subject) → TokenId                          │
│  - revoke_passport(subject)                                  │
│  - verify_credential(subject) → bool                         │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for Move       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Token V2 Non-Transferable Passport                          │
│  - Compliance token via Aptos Token V2 framework             │
│  - verify_credential(subject) → token ownership check        │
│  SPEC: EP-08 F-08.8 — Aptos Passport Adapter                │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for Aptos)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via Move verifier
3. `mint_passport()` mints a non-transferable Token V2 token
4. `verify_credential()` checks token ownership
5. `revoke_passport()` burns or freezes the token

## Grant Pipeline

- **Aptos Foundation ZK Working Group** — "Non-transferable compliance tokens on Aptos"
- **Aptos DeFi Grants** — "Move verifier + Token V2 soulbound passport"

## Prerequisites

- Aptos CLI 1.0+
- Move compiler

## Setup

```bash
aptos --version
```

## Build

```bash
aptos move compile --named-addresses zkkyc=default
```

## Test

```bash
aptos move test --named-addresses zkkyc=default
```

## Deploy

```bash
bash scripts/deploy.sh testnet
```

## Supported Networks

- Aptos Testnet
- Aptos Mainnet
