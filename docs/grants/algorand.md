# Algorand Adapter Specification

**Spec reference:** EP-08 (F-08.5.2 — US-08.5.2)

## Technical Approach

### AVM ZK Verifier

Algorand's Algorand Virtual Machine (AVM) supports custom ZK verifier logic
via PyTeal/Beaker smart contracts. The Compliance Passport is implemented as an
Algorand Standard Asset (ASA) with:
- `clawback` enabled — allows oracle authority to revoke non-compliant passports
- `manager` set to oracle authority — controls minting
- `reserve` frozen — total supply locked to minted passports only
- `metadata hash` encodes `policy_id` and `proof_hash`

### PyTeal Verifier Contract

The UltraHonk verification logic is wrapped in a PyTeal approval program that:
1. Accepts proof bytes and public inputs as application call arguments
2. Runs the UltraHonk verification (ported from Noir's Solidity output or via
   a Rust precompile if AVM supports it)
3. Stores the result in a global state keyed by `sender + policy_id`
4. Emits a `ComplianceVerified` log on success

### ASA Passport Issuance

Upon successful verifier confirmation, the oracle authority:
1. Calls `AssetConfigTransaction` to create the ASA (once, at deployment)
2. Calls `AssetTransferTransaction` with `clawback` to mint a single unit to the
   compliant wallet
3. The wallet holds exactly one Compliance Passport ASA per policy

### Python Adapter (`zkkyc/adapters/algorand.py`)

Uses `py-algorand-sdk` to:
- Call the PyTeal verifier contract
- Mint ASA passports via `AssetTransferTransaction`
- Query wallet balance for `verifyCredential`
- Revoke via `AssetClawbackTransaction`

## Regulatory Narrative Alignment

The Algorand Foundation has explicitly funded compliance use cases, including
their participation in the MIT Fintech Hackathon and the Algorand Europe
Compliance Accelerator. ZKCO's focus on FATF-regulated cross-border transfers
and financial inclusion aligns with the Foundation's stated priorities.

## Implementation Plan

| Phase | Task | Duration |
|---|---|---|
| 1 | Noir → AVM proof format investigation | 2 weeks |
| 2 | PyTeal verifier contract development | 3 weeks |
| 3 | ASA passport issuance + revocation | 2 weeks |
| 4 | Python adapter + conformance suite | 2 weeks |
| 5 | Testnet deployment + demo | 1 week |
| **Total** | | **10 weeks** |
