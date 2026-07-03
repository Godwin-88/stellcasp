"""
Chain-agnostic Passport Adapter package — ZK-KYC Compliance Agent (zkkyc.adapters)

Spec reference: EP-08 (F-08.1 — US-08.1.1)

Each adapter implements the `PassportAdapterBase` interface for a specific
target chain. The Settlement Agent (EP-06 F-06.1.5) resolves adapters
exclusively through `AdapterRegistry.get(chain_target)` — no if/elif
chain_target branching exists in agent code.

Available adapters:
  - stellar   — Stellar Soroban (CompliancePassport contract)
  - casper    — Casper Odra (ComplianceOracle + IdentityRegistry)
  - ethereum  — EVM/L2 via Noir Solidity verifier + ERC-721 soulbound
  - polkadot  — Polkadot parachain via ink! Wasm contracts
  - hedera    — Hedera Hashgraph via HSCS verifier + HTS passport
"""

from .base import (
    AdapterConformanceError,
    AdapterDeploymentError,
    PassportAdapterBase,
)
from .registry import AdapterRegistry, get_adapter_registry

__all__ = [
    "AdapterConformanceError",
    "AdapterDeploymentError",
    "PassportAdapterBase",
    "AdapterRegistry",
    "get_adapter_registry",
]
