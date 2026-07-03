# Web3 Foundation Grant Documentation

**Spec reference:** EP-08 (F-08.3 — US-08.3.2)

## Program Overview

| Field | Detail |
|---|---|
| Program | Web3 Foundation Grants Programme |
| Grant Size | Up to $30,000 |
| Application URL | https://github.com/w3f/Grants-Program/blob/master/applications/README.md |
| Status | Planned |
| Track | ZK Identity & Compliance Infrastructure |

## Project Overview

ZKCO (Zero-Knowledge Compliance Oracle) is the world's first AI-native,
graph-intelligence-driven compliance oracle that allows regulated financial
protocols to consume compliance decisions without ever accessing customer PII.
Rather than building another KYC system, ZKCO builds compliance infrastructure —
a shared oracle layer that any DeFi protocol, DEX, lending platform, or RWA
tokenizer can query to gate access using a single, portable, reusable Compliance
Passport.

## Problem Statement

Regulated DeFi on Polkadot parachains faces the same KYC duplication problem as
every other ecosystem: each protocol independently runs identity verification,
stores PII, and bears compliance costs. This is inefficient, siloed, and
creates unnecessary PII exposure vectors. There is no shared, ZK-proved
compliance layer that parachain protocols can trust without running their own
KYC infrastructure.

## Solution

ZKCO deploys two ink! smart contracts on any Polkadot parachain:
1. **UltraHonkVerifier** — verifies Noir ZK proofs on-chain
2. **CompliancePassport** — non-transferable soulbound credential

The same Noir circuit (`main.nr`) that produces proofs for Stellar and Casper
produces proofs for Polkadot. Only the verifier contract and passport contract
are chain-specific. The `PolkadotAdapter` (Python) wraps these contracts for
use by the Settlement Agent.

## Technical Approach

### ink! Verifier Contract

The UltraHonk verification logic is ported from Noir's Solidity output into an
ink! contract (`verifier/lib.rs`). The contract:
- Accepts proof bytes and public inputs via SCALE-encoded call parameters
- Runs the UltraHonk verification algorithm in Wasm
- Returns `Result<bool, VerifierError>`

Compiled with `cargo contract build` to `.wasm`.

### ink! Compliance Passport Contract

The `compliance_passport/lib.rs` contract implements the five PassportAdapter
operations:
- `mint_passport(wallet, policy_id, expires_at, proof_hash)` — only oracle authority
- `revoke_passport(wallet, policy_id, reason)` — only oracle authority
- `verify_credential(wallet, policy_id)` — read-only view
- No transfer entry points (non-transferable by design)

### Python Adapter

`zkkyc/adapters/polkadot.py` uses `substrateinterface` (PyPI) to call contract
entry points. The adapter passes the full `PassportAdapterConformanceTests`
suite (8 tests) against Rococo testnet.

## Milestone Breakdown (8 weeks from approval)

| Milestone | Deliverable | Acceptance Criterion |
|---|---|---|
| M1 (Weeks 1-2) | ink! UltraHonk verifier deployed to Rococo | `pytest tests/conformance/ -k Polkadot` passes for proof verification |
| M2 (Weeks 3-4) | ink! CompliancePassport deployed to Rococo | Full conformance suite passes (8/8 tests) |
| M3 (Weeks 5-6) | Python `PolkadotAdapter` + demo script | `python -m zkkyc.run --chain polkadot` succeeds end-to-end |
| M4 (Weeks 7-8) | Grant report + community demo | Demo video published; W3F review call completed |

## Team Background

Ed Godwin — AI Engineer & Digital Transformation Consultant with 15+ years
experience in financial services technology, regulatory compliance systems, and
distributed ledger infrastructure. Previously delivered compliance automation
platforms for East African SACCOs and European neobanks.

## East Africa / Polkadot Africa Alignment

Polkadot Africa is actively building parachain infrastructure for African
financial inclusion. ZKCO's compliance passport directly addresses the
regulatory gap that prevents African mobile money operators from participating
in cross-border DeFi. A Polkadot Africa parachain integration would position
ZKCO as the compliance layer for the entire African DeFi ecosystem — a narrative
strongly aligned with W3F's public goods mandate.

## Budget Justification

| Item | Cost | Purpose |
|---|---|---|
| ink! development | $8,000 | Verifier + passport contracts, testing |
| Rococo deployment | $2,000 | Testnet deployment, security audit |
| Python adapter + integration | $6,000 | substrateinterface integration, conformance suite |
| Documentation + demo | $4,000 | Spec docs, demo video, W3F reporting |
| **Total** | **$20,000** | Within W3F grant ceiling |
