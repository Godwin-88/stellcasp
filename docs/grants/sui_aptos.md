# Sui / Aptos Adapter Specifications

**Spec reference:** EP-08 (F-08.5.3 — US-08.5.3)

## Overview

Both Sui and Aptos have active ZK working groups and large ecosystem funds
($200M+ each). This document provides technical approach sketches for both
chains, sufficient for foundation exploratory conversations.

## Sui Adapter

### Technical Approach

- **Move language adapter**: Sui's Move smart contracts implement the
  PassportAdapter interface natively.
- **Soulbound passport**: Sui's `transfer::freeze_object` capability enforces
  non-transferability. The Compliance Passport is a `sui::object::UID`-based
  object with `transfer` frozen at the module level.
- **ZK verifier**: Sui's native cryptography modules (`sui::zk::groth16`) support
  Groth16 proofs natively. The Noir UltraHonk proof would need conversion to
  Groth16 format, or a custom Sui verifier module for UltraHonk would be
  developed.
- **Shared strategy**: A shared Rust crate implements the UltraHonk verification
  logic, compiled to both Sui Move bytecode and Aptos Move bytecode.

### ZK Working Group Contact

Sui Foundation ZK Working Group: zk@suifoundation.org (public channel)

## Aptos Adapter

### Technical Approach

- **Move language adapter**: Aptos Move smart contracts implement the
  PassportAdapter interface.
- **Soulbound passport**: Aptos `TokenV2` non-transferable token standard provides
  the soulbound credential pattern natively.
- **ZK verifier**: Aptos supports custom ZK verifier logic via `aptos_framework::voting`
  and `aptos_framework::aptos_coin` patterns. UltraHonk verification can be
  implemented as a Move module function.
- **Shared strategy**: Same shared Rust crate as Sui for UltraHonk verification.

### ZK Working Group Contact

Aptos Foundation Developer Relations: devrel@aptoslabs.com

## Implementation Timeline (both chains)

| Phase | Duration | Deliverable |
|---|---|---|
| Shared Rust UltraHonk crate | 4 weeks | `zk-verifier` crate compiling to both Move targets |
| Sui Move adapter | 3 weeks | Deployed Sui testnet contract |
| Aptos Move adapter | 3 weeks | Deployed Aptos testnet contract |
| Python adapters + conformance | 3 weeks | Both adapters pass 8/8 conformance tests |
| **Total** | **13 weeks** | Both chains on testnet |
