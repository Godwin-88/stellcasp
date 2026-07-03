# Passport Adapter Specification

**Spec reference:** EP-08, F-08.1 (US-08.1.1)

## Purpose

This document defines the chain-agnostic Passport Adapter interface that every
target chain deployment must implement. The Settlement Agent (EP-06 F-06.1.5)
dispatches exclusively through this interface — no `if/elif chain_target ==`
branching exists in agent code. Adding a new chain requires only implementing
the adapter, not modifying any shared platform code.

## Interface Contract

Every adapter **must** implement the following five operations:

### 1. `verify_proof(proof_hex, public_inputs) → bool`

Verify a Noir UltraHonk proof against the on-chain verifier contract.

| Parameter | Type | Description |
|---|---|---|
| `proof_hex` | `str` | Hex-encoded UltraHonk proof bytes |
| `public_inputs` | `list[int]` | Public inputs matching the circuit signature |

**Returns:** `True` if the proof is valid and accepted by the verifier contract.
**Behaviour:** Must never raise for an invalid proof — return `False` instead.

### 2. `mint_passport(wallet, policy_id, expires_at, proof_hash) → str`

Mint a non-transferable Compliance Passport for a wallet.

| Parameter | Type | Description |
|---|---|---|
| `wallet` | `str` | Target wallet address in chain-native format |
| `policy_id` | `str` | Human-readable compliance policy identifier |
| `expires_at` | `int` | UNIX timestamp when the passport expires |
| `proof_hash` | `str` | SHA-256 hash of the ZK proof for on-chain reference |

**Returns:** On-chain transaction hash as a hex string.
**Raises:** `AdapterDeploymentError` if the on-chain mint fails.

### 3. `revoke_passport(wallet, policy_id, reason) → str`

Revoke an active Compliance Passport.

| Parameter | Type | Description |
|---|---|---|
| `wallet` | `str` | Wallet address holding the passport |
| `policy_id` | `str` | Policy identifier of the passport to revoke |
| `reason` | `str` | Short reason code (e.g. `"HIGH_RISK_UPDATE"`) |

**Returns:** On-chain transaction hash as a hex string.
**Raises:** `AdapterDeploymentError` if the on-chain revoke fails.

### 4. `verify_credential(wallet, policy_id) → dict`

Check whether a wallet holds a valid, non-expired Compliance Passport.

| Parameter | Type | Description |
|---|---|---|
| `wallet` | `str` | Wallet address to query |
| `policy_id` | `str` | Policy identifier to check |

**Returns:** Dict with keys:
- `valid` (`bool`): `True` if a non-expired passport exists.
- `expires_at` (`int`): UNIX timestamp of expiry, or `0` if invalid.
- `policy_id` (`str`): Echo of the requested policy.

**Behaviour:** Must never panic or raise on missing records — return
`{"valid": False, "expires_at": 0, policy_id}` instead.

### 5. `get_deployment_info() → DeploymentInfo`

Return structured metadata about the current adapter deployment.

**Returns:** `DeploymentInfo` dataclass with fields:
- `chain_id` (`str`): Chain identifier (e.g. `"stellar"`, `"ethereum:11155111"`).
- `contract_address` (`str`): Primary contract address.
- `deployed_at` (`datetime`): UTC timestamp of deployment.
- `network` (`str`): `"testnet"`, `"mainnet"`, or `"devnet"`.
- `extra` (`dict[str, Any]`): Chain-specific additional metadata.

## Registration

Adapters register themselves with `AdapterRegistry`:

```python
from zkkyc.adapters.registry import get_adapter_registry

registry = get_adapter_registry()
await registry.register("my-chain", MyChainAdapter)
```

The Settlement Agent resolves adapters through:

```python
adapter = registry.get(state.chain_target)
```

## Conformance Tests

Every adapter must pass the `PassportAdapterConformanceTests` mixin (8 tests)
before a grant submission is made:

```python
from tests.conformance.test_adapter_conformance import PassportAdapterConformanceTests

class TestMyChainAdapter(PassportAdapterConformanceTests):
    ADAPTER_CLASS = MyChainAdapter
    ADAPTER_KWARGS = {"settings": my_settings}
```

Run: `pytest tests/conformance/test_adapter_conformance.py -k TestMyChainAdapter -v`

## Supported Adapters

| Chain | Adapter Class | Status | Grant Target |
|---|---|---|---|
| Stellar | `StellarAdapter` | Production | Stellar Community Fund (Jul 3) |
| Casper | `CasperAdapter` | Production | Casper Ecosystem Fund (Jul 8) |
| Ethereum/L2s | `EVMAdapter` | Planned | EF ESP, Base, Arbitrum, Optimism RPGF |
| Polkadot | `PolkadotAdapter` | Planned | Web3 Foundation Grants |
| Hedera | `HederaAdapter` | Planned | HBAR Foundation |
| Algorand | — | Spec only | Algorand Foundation |
| Sui | — | Spec only | Sui Foundation |
| Aptos | — | Spec only | Aptos Foundation |
| ICP | — | Spec only | DFINITY Foundation |

## PII Guarantees

All adapters must follow the platform's PII minimisation rules:
- Raw entity IDs are never passed to on-chain contracts.
- `entity_hash` (SHA-256 of raw ID + salt) is used for all on-chain references.
- Factor values and weights are never included in on-chain transactions.

## Error Handling

- `AdapterDeploymentError`: raised when on-chain contract calls fail. Carries
  `chain_target`, `message`, and optional `cause`. The Settlement Agent retries
  once after 5 seconds on this exception before routing to the error terminal.
- `AdapterConformanceError`: raised when an adapter violates the conformance
  contract. Used by the registry at registration time and by the conformance
  test suite.
