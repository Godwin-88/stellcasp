# EVM / L2 Grant Documentation

**Spec reference:** EP-08 (F-08.2 — US-08.2.3)

## Target Programs

| Program | Ecosystem | Grant Size | Application URL | Status |
|---|---|---|---|---|
| Ethereum Foundation ESP | Ethereum | Variable (up to $1M) | https://esp.ethereum.foundation/apply | Planned |
| Base Builder Grants | Base (Coinbase L2) | Up to $50K | https://base.org/build | Planned |
| Arbitrum Foundation Grants | Arbitrum | Variable | https://arbitrum.foundation/grants | Planned |
| Optimism RPGF | Optimism | Retroactive, variable | https://retropgf.optimism.io | Planned |

## ZKCO Submission Narrative (per program)

### Ethereum Foundation ESP — Privacy & ZK Tooling Track

The Ethereum Foundation Ecosystem Support Programme explicitly funds privacy
infrastructure and ZK tooling that broadens Ethereum's utility for regulated
use cases. ZKCO addresses a critical gap: today, regulated financial protocols
on Ethereum must either run their own KYC (expensive, siloed, PII-exposing) or
rely on oracles that leak financial intelligence. ZKCO's Noir UltraHonk circuit
proves multi-factor compliance correctness without revealing any underlying
data — the first time a multi-factor financial risk model has been
cryptographically attested on Ethereum. The ERC-721 soulbound Compliance
Passport turns this into a reusable, protocol-agnostic credential: any EVM
DeFi protocol can call `verifyCredential(address, string)` and inherit
compliance without running KYC. This is infrastructure, not an application.

### Base Builder Grants — DeFi Infrastructure Track

Base's builder grants prioritise DeFi infrastructure that unlocks new user
cohorts. ZKCO's Compliance Passport directly enables regulated institutions
(neobanks, SACCOs, remittance operators) to participate in Base DeFi without
building bespoke compliance stacks. The EVM adapter (`EVMAdapter`) uses Noir's
native Solidity verifier output, meaning the exact same ZK circuit that secures
Stellar and Casper deployments secures Base — one proof, five chains. The
Sepolia testnet deployment is already verifiable; mainnet deployment is a
single contract deployment and RPC URL change.

### Arbitrum Foundation Grants — Compliance Infrastructure Track

Arbitrum's grant programme explicitly supports compliance and identity
infrastructure for its growing DeFi ecosystem. ZKCO's Compliance Passport
solves the "KYC duplication problem" that every Arbitrum protocol currently
faces independently. By providing a shared, ZK-proved compliance oracle,
ZKCO reduces per-protocol compliance cost from $50K–$200K/year to near-zero
while giving users a portable credential that works across all Arbitrum DeFi.
The `EVMAdapter` is fully compatible with Arbitrum Sepolia and Stylus.

### Optimism RPGF — Financial Inclusion Retroactive Public Goods Funding

Optimism's RPGF rewards public goods that have already generated collective
value. ZKCO's compliance infrastructure has clear network effects: every
protocol that adopts the Compliance Passport reduces duplicate KYC spend
ecosystem-wide. The retroactive case is strong — ZKCO has already demonstrated
working testnet deployments on Stellar and Casper, the Noir circuit is
production-grade, and the multi-factor CI engine is a genuine financial
engineering innovation (not a wrapper around a single risk score). The East
African remittance corridor narrative (financial inclusion for unbanked mobile
money users) aligns well with Optimism's public goods mandate.

## Implementation Checklist (per grant)

- [ ] Testnet deployment of `Verifier.sol` on target chain
- [ ] Testnet deployment of `CompliancePassport.sol` on target chain
- [ ] Conformance suite passes (`pytest tests/conformance/ -k TestEVM`)
- [ ] Open-source repo with MIT/Apache-2.0 license
- [ ] Demo video (≤3 min) showing full flow
- [ ] `docs/grants/evm_grants.md` updated with submission link
- [ ] `deployments.json` updated with target chain contract addresses

## Technical Approach

### Noir → Solidity Verifier

Noir ≥ v0.30 compiles the compliance circuit (`circuits/src/main.nr`) to
Solidity using `nargo compile --target evm`. The output is a standalone
`Verifier.sol` contract that implements `verify(bytes proof, uint256[] publicInputs)`
returning `bool`. No custom cryptography is required — Noir handles the
UltraHonk proof-to-EVM mapping.

### ERC-721 Soulbound Passport

`CompliancePassport.sol` implements:
- ERC-721 with EIP-5192 (`Locked` event on every mint)
- `locked(tokenId)` returns `true` unconditionally
- `transferFrom` / `safeTransferFrom` revert with `"SoulboundToken: non-transferable"`
- `mintPassport(address, string, uint256, bytes32)` callable only by `oracleAuthority`
- `verifyCredential(address, string)` view function returning `(bool, uint256)`

The contract is verified on Etherscan after deployment so grant reviewers can
inspect the source code.

### One-Codebase, Five-Chain Deployment

The same `Verifier.sol` and `CompliancePassport.sol` source code deploys to
Ethereum Sepolia, Base Sepolia, Arbitrum Sepolia, and Optimism Sepolia with
only the RPC URL and deployer private key changed. This means the engineering
cost of adding a new L2 is measured in hours, not weeks — a strong argument for
grant efficiency.
