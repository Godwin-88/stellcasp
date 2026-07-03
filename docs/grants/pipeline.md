# Grant Pipeline Registry

**Spec reference:** EP-08 (F-08.5.1 — US-08.5.1)

## Overview

This document is the single source of truth for all active and planned grant
applications. It tracks status, deadlines, funding amounts, and adapter
dependencies across the full multi-chain expansion roadmap.

## Pipeline Registry

| Chain | Program | Fund Size | Priority | Status | Adapter Epic | Deadline | Link |
|---|---|---|---|---|---|---|---|
| Stellar | Stellar Community Fund (SCF) | Variable | P0 — Jul 3 | **Active** | EP-03 | 3 Jul 2026 | [docs/grants/stellar_scf.md](#) |
| Casper | Casper Ecosystem Fund | Variable | P0 — Jul 8 | **Active** | EP-04 | 8 Jul 2026 | [docs/grants/casper_ecosystem.md](#) |
| Ethereum | EF ESP (Privacy & ZK track) | Up to $1M | P1 — Q3 2026 | Planned | F-08.2 | Rolling | [docs/grants/evm_grants.md](evm_grants.md) |
| Base | Base Builder Grants | Up to $50K | P1 — Q3 2026 | Planned | F-08.2 | Rolling | [docs/grants/evm_grants.md](evm_grants.md) |
| Arbitrum | Arbitrum Foundation Grants | Variable | P1 — Q3 2026 | Planned | F-08.2 | Rolling | [docs/grants/evm_grants.md](evm_grants.md) |
| Optimism | Optimism RPGF | Retroactive | P1 — Q3 2026 | Planned | F-08.2 | Rolling | [docs/grants/evm_grants.md](evm_grants.md) |
| Polkadot | Web3 Foundation Grants | Up to $30K | P1 — Open year-round | Planned | F-08.3 | Rolling | [docs/grants/web3_foundation.md](web3_foundation.md) |
| Hedera | HBAR Foundation | Up to $250M pool | P1 — Open year-round | Planned | F-08.4 | Rolling | [docs/grants/hbar_foundation.md](hbar_foundation.md) |
| Algorand | Algorand Foundation | Variable | P2 — Q4 2026 | Planned | F-08.5 | TBD | [docs/grants/algorand.md](algorand.md) |
| Sui | Sui Foundation | $200M+ pool | P2 — Q4 2026 | Planned | F-08.5 | TBD | [docs/grants/sui_aptos.md](sui_aptos.md) |
| Aptos | Aptos Foundation | $200M+ pool | P2 — Q4 2026 | Planned | F-08.5 | TBD | [docs/grants/sui_aptos.md](sui_aptos.md) |
| ICP | DFINITY Foundation | Variable | P3 — 2027 | Backlog | F-08.5 | TBD | [docs/grants/icp.md](icp.md) |

## Status Lifecycle

```
Planned → In Progress → Submitted → Under Review → Approved / Rejected
```

- **Planned**: Grant identified, narrative drafted, not yet submitted
- **In Progress**: Adapter implementation underway, application being prepared
- **Submitted**: Application submitted, awaiting initial response
- **Under Review**: Reviewer feedback received, responding to revisions
- **Approved**: Grant awarded, milestone tracking active
- **Rejected**: Application declined, feedback logged for re-submission or pivot

## Update Policy

This registry is updated within 48 hours of any submission, approval, or
rejection event. The `STATUS` field is the authoritative source of truth for
platform grant progress. Do not update `PRIORITY` without team consensus.

## Conformance Dependency

No grant is submitted until the corresponding adapter passes the full
conformance suite (8/8 tests in `tests/conformance/test_adapter_conformance.py`).
The conformance suite is the acceptance gate for each adapter milestone.
