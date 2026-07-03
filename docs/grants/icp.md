# ICP Canister Adapter Specification

**Spec reference:** EP-08 (F-08.5.3 — US-08.5.3)

## Overview

The DFINITY Foundation Internet Computer (ICP) offers a unique deployment model
for ZK verification: canister-based smart contracts with native WebAssembly
support and Internet Identity integration. This document outlines the technical
approach for an ICP Compliance Passport adapter.

## Technical Approach

### Canister-Based ZK Verifier

- **ic-verify-bls-signature**: The DFINITY-maintained library for BLS signature
  verification in Motoko can serve as a starting point for a custom UltraHonk
  verifier canister.
- **Rust canister**: The UltraHonk verification logic is compiled to WebAssembly
  using Rust and deployed as an ICP canister. The canister exposes candid
  methods matching the PassportAdapter interface.
- **Internet Identity**: The Compliance Passport is linked to an Internet Identity
  principal, making the credential self-sovereign and recoverable.

### Compliance Passport Canister

The `compliance_passport` canister:
- Stores passport records keyed by `(principal, policy_id)`
- Exposes `mint_passport`, `revoke_passport`, `verify_credential` candid methods
- Internet Identity authentication gates administrative operations
- Non-transferability is enforced at the identity level — a passport is bound to
  a single II principal

### Python Adapter (`zkkyc/adapters/icp.py`)

Uses `ic-py` or `agent-py` to:
- Call candid methods on the verifier and passport canisters
- Authenticate via Internet Identity delegation
- Query credential status for downstream protocols

## Early Mover Positioning

Very few ZK compliance solutions target ICP. Building the first ZK verifier
canister on Internet Computer positions ZKCO as the compliance layer for the
entire ICP DeFi ecosystem — a strong narrative for DFINITY Foundation grants.

## Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| UltraHonk Rust canister | 6 weeks | Verifier canister deployed to ICP testnet |
| Compliance Passport canister | 4 weeks | II-linked passport canister |
| Python adapter + conformance | 3 weeks | Adapter passes 8/8 conformance tests |
| **Total** | **13 weeks** | ICP testnet deployment |
