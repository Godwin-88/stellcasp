# Hedera Smart Contracts

ZK-KYC Passport smart contracts for Hedera (HSCS + HTS).

## Contracts

- `HederaZKVerifier.sol` — UltraHonk verifier for Hedera Smart Contract Service
- `ZKPassport.sol` — HTS NFT soulbound Compliance Passport
- `UltraVerifier.sol` — Interface for the UltraHonk verifier

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  HederaZKVerifier.sol                                        │
│  - verifyProof(proof, publicInputs) → bool                   │
│  - Delegates to pre-deployed UltraVerifier on HSCS          │
│  SPEC: EP-02 F-02.2 — Soroban Verifier adapted for HSCS      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ZKPassport.sol (HTS NFT)                                    │
│  - mintPassport(subject) → tokenId                           │
│  - revokePassport(subject)                                   │
│  - verifyCredential(subject) → bool                          │
│  - Uses HTS precompile for NFT minting                       │
│  SPEC: EP-08 F-08.5 — Hedera Passport Adapter               │
└─────────────────────────────────────────────────────────────┘
```

## SPEC REF

- **EP-08** — Chain-Agnostic Passport Adapter & Grant Pipeline (`zk_kyc_platform_spec.md`)
- **EP-02** — Zero-Knowledge Compliance Oracle Circuit
- **EP-03** — Stellar Compliance Passport & Protocol Gateway (adapted for Hedera)

## Lifecycle

1. ZK proof generated off-chain (Noir circuit, EP-02)
2. Proof verified on-chain via HederaZKVerifier
3. `mintPassport()` mints HTS NFT via precompile
4. `verifyCredential()` checks passport status
5. `revokePassport()` marks passport as revoked

## Grant Pipeline

- **HBAR Foundation** — "Compliance infrastructure for Hedera enterprise DeFi"
- **Hedera Foundation Grants** — "ZK-verified identity on Hedera"

## Prerequisites

- [Hardhat](https://hardhat.org/)
- [Hedera SDK](https://github.com/hashgraph/hedera-sdk-js)
- [OpenZeppelin Contracts](https://www.openzeppelin.com/contracts)

## Setup

```bash
npm install
cp .env.example .env
```

## Build

```bash
npx hardhat compile
```

## Test

```bash
npx hardhat test
```

## Deploy

```bash
bash scripts/deploy.sh
```

## Supported Networks

- Hedera Testnet
- Hedera Previewnet
- Hedera Mainnet
