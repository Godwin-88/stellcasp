# EVM Smart Contracts

ZK-KYC Passport smart contracts for EVM-compatible chains (Ethereum, Base, Arbitrum, Optimism, Polygon, etc.).

## Contracts

- `UltraHonkVerifier.sol` — Wrapper around a pre-deployed UltraHonk verifier contract
- `ZKPassport.sol` — Soulbound ERC-721 token representing a verified identity passport
- `UltraVerifier.sol` — Interface for the UltraHonk verifier

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  UltraHonkVerifier.sol                                       │
│  - verifyProof(proof, publicInputs) → bool                   │
│  - Delegates to pre-deployed UltraVerifier contract          │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for EVM       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ZKPassport.sol                                              │
│  - mintPassport(subject) → tokenId                           │
│  - revokePassport(subject)                                   │
│  - verifyCredential(subject) → bool                          │
│  - Non-transferable ERC-721 (soulbound)                      │
│  SPEC: EP-08 F-08.3 — EVM Passport Adapter                  │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for EVM)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via UltraHonkVerifier
3. `mintPassport()` called by oracle authority
4. `verifyCredential()` callable by any downstream protocol
5. `revokePassport()` callable by oracle authority

## Grant Pipeline

- **Ethereum Foundation** — "ZK-verified compliance infrastructure for DeFi"
- **Base Builder Grants** — "On-chain compliance passports for Base ecosystem"
- **Arbitrum Foundation** — "ZK compliance layer for L2 DeFi"

## Prerequisites

- [Foundry](https://getfoundry.sh/)
- [OpenZeppelin Contracts](https://www.openzeppelin.com/contracts)

## Setup

```bash
forge install OpenZeppelin/openzeppelin-contracts --no-commit
cp .env.example .env
```

## Build

```bash
forge build
```

## Test

```bash
forge test
```

## Deploy

```bash
bash scripts/deploy.sh sepolia
```

## Verify

```bash
forge verify-contract <address> src/UltraHonkVerifier.sol:UltraHonkVerifier \
  --chain sepolia --watch
```

## Supported Chains

- Ethereum Mainnet / Sepolia
- Base / Base Sepolia
- Arbitrum One / Sepolia
- Optimism / Sepolia
- Polygon Mainnet / Amoy
