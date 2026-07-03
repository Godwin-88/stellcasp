# HBAR Foundation Grant Documentation

**Spec reference:** EP-08 (F-08.4 — US-08.4.2)

## Program Overview

| Field | Detail |
|---|---|
| Program | HBAR Foundation Grants Programme |
| Grant Size | Up to $250M pool (enterprise compliance track) |
| Application URL | https://www.hbarfoundation.org/grants |
| Status | Planned |
| Track | Enterprise Compliance & Regulated DeFi |

## ZKCO Alignment with HBAR Foundation Priorities

The HBAR Foundation explicitly prioritises:
1. **Financial inclusion** — enabling unbanked/underbanked populations to access
   regulated financial services
2. **Regulated DeFi** — bringing real-world financial institutions onto
   Hedera in compliance with FATF, MiCA, and local regulations
3. **Enterprise identity** — verifiable credentials and digital identity
   infrastructure for enterprises
4. **Cross-border payments** — compliant remittance corridors

ZKCO satisfies all four priorities natively.

## Infrastructure Positioning

ZKCO is not a DeFi application — it is **compliance infrastructure**. The
framing for HBAR Foundation:

> Any Hedera-based protocol calls `verifyCredential()` — they never run KYC,
> they never touch PII, they inherit compliance from the oracle. The ZK proof
> is the trust mechanism.

This positions ZKCO as a foundational layer that every Hedera DeFi protocol
depends on, rather than a competitive application. Foundation-level concerns
unlock enterprise deployment funds rather than hackathon prizes alone.

## Technical Approach

### Hedera Smart Contract Service (HSCS) Verifier

The EVM-compatible `Verifier.sol` (F-08.2.1) deploys directly to Hedera testnet
via HSCS using the Hedera JavaScript SDK. No code changes are required — Hedera
supports standard Solidity contracts through its EVM compatibility layer.

### Hedera Token Service (HTS) Compliance Passport

The Compliance Passport is implemented as an HTS non-fungible token (NFT) with:
- `freezeKey` set to the oracle authority — prevents transfer
- `supplyKey` set to the oracle authority — controls minting
- NFT serial metadata encodes `policy_id`, `expires_at`, and `proof_hash`
- Mirror Node REST API queries replace direct contract calls for credential
  verification (HTS-native pattern)

### East African Financial Inclusion Narrative

Hedera has an active East African presence through partnerships with mobile money
operators and central bank digital currency (CBDC) pilots. ZKCO's Compliance
Passport directly enables:
- **Remittance corridors:** compliant cross-border transfers from East African
  diaspora workers without re-KYC at each corridor hop
- **SACCO compliance:** Kenyan and Ugandan SACCOs can verify member compliance
  via ZK proof, satisfying CBK and FSD Kenya regulatory requirements
- **Mobile money integration:** M-Pesa and Airtel Money users can prove
  compliance to Hedera DeFi protocols without exposing transaction history

## Milestone Deliverables

| Milestone | Deliverable | Acceptance Criterion |
|---|---|---|
| M1 (Weeks 1-2) | HSCS verifier deployed to Hedera testnet | `cast call` returns `true` for valid proof |
| M2 (Weeks 3-4) | HTS Compliance Passport token created | Conformance suite passes (8/8) |
| M3 (Weeks 5-6) | Python `HederaAdapter` + demo | `python -m zkkyc.run --chain hedera` succeeds |
| M4 (Weeks 7-8) | East African partner demo | Live demo with Hedera + mobile money API mock |

## Competitive Positioning

ZKCO is the only ZK compliance solution targeting Hedera specifically. Existing
ZK identity solutions (e.g. Polygon ID, Sismo) are designed for EVM ecosystems
and do not leverage Hedera's unique HTS + HSCS architecture. By building
natively on Hedera, ZKCO becomes the de facto compliance layer for the Hedera
DeFi ecosystem — a first-mover advantage in a $250M grant programme.
