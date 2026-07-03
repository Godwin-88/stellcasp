# Algorand Smart Contracts

ZK-KYC Passport smart contracts for Algorand (AVM — Algorand Virtual Machine).

## Contracts

- `passport.py` — PyTeal approval and clear state programs
- `deploy.py` — Deployment script for Algorand testnet/mainnet

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  approval.py (PyTeal)                                        │
│  - verify_proof(proof, public_inputs) → bool                 │
│  - mint_passport(subject) → asset_id                         │
│  - revoke_passport(subject) → clawback                       │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for AVM       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ASA Clawback Passport                                       │
│  - Compliance token as ASA with clawback address             │
│  - verify_credential(subject) → balance check                │
│  SPEC: EP-08 F-08.6 — Algorand Passport Adapter             │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for Algorand)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via PyTeal verifier
3. `mint_passport()` creates/transfers ASA to subject
4. `verify_credential()` checks ASA balance > 0
5. `revoke_passport()` claws back ASA from subject

## Grant Pipeline

- **Algorand Foundation** — "ZK-verified compliance tokens on Algorand"
- **Algorand DeFi Compliance Grants** — "PyTeal verifier + ASA passport"

## Prerequisites

- Python 3.9+
- [PyTeal](https://pyteal.io/)
- [Algorand SDK](https://developer.algorand.org/docs/sdks/python/)
- Algorand node (testnet or mainnet)

## Setup

```bash
pip install pyteal algosdk
cp .env.example .env
```

## Build

```bash
python3 -c "from passport import approval_program; print(approval_program())"
```

## Test

```bash
python3 -m pytest
```

## Deploy

```bash
bash scripts/deploy.sh
```

## Supported Networks

- Algorand Testnet
- Algorand Mainnet
