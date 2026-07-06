"""
CSPR.click skill wrapper — ZK-KYC Compliance Agent (zkkyc.toolkit.cspr_click)

Agent-native wallet management, deploy signing, and balance checks for the
Settlement Agent. Wraps the Casper CSPR.click AI Agent Skill capabilities
so the agent controls its own on-chain identity and economic resources.

Spec reference: EP-06 augmentation (CSPR.click skill), EP-04 (Account Abstraction)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentWallet:
    public_key_hex: str
    secret_key_path: str | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", datetime.now(timezone.utc).isoformat())


@dataclass
class DeployResult:
    deploy_hash: str
    success: bool
    cost: str = ""
    error: str | None = None


# ---------------------------------------------------------------------------
# Wallet management
# ---------------------------------------------------------------------------

class AgentWalletManager:
    """Manages the Settlement Agent's Casper wallet.

    In demo mode, generates an ephemeral key pair. In production, loads
    from the CSPR.click vault or environment.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._wallet: AgentWallet | None = None

    def load_or_create(self, secret_key_path: str | None = None) -> AgentWallet:
        """Load an existing wallet or create a new ephemeral one for demo."""
        path = secret_key_path or self.settings.casper_secret_key_path
        if path and os.path.exists(path):
            return self._load_from_file(path)
        return self._create_ephemeral()

    def _load_from_file(self, path: str) -> AgentWallet:
        try:
            with open(path, "r") as f:
                secret_hex = f.read().strip()
            private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(secret_hex))
            public_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            return AgentWallet(public_key_hex=public_hex, secret_key_path=path)
        except Exception as exc:
            logger.error("Failed to load wallet from %s: %s", path, exc)
            raise RuntimeError(f"Cannot load agent wallet: {exc}") from exc

    def _create_ephemeral(self) -> AgentWallet:
        private_key = Ed25519PrivateKey.generate()
        public_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        secret_hex = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()).hex()
        logger.info("Created ephemeral agent wallet with public key %s...", public_hex[:16])
        return AgentWallet(public_key_hex=public_hex, secret_key_path=None)

    @property
    def wallet(self) -> AgentWallet | None:
        return self._wallet

    def set_wallet(self, wallet: AgentWallet) -> None:
        self._wallet = wallet


# ---------------------------------------------------------------------------
# Deploy building & signing
# ---------------------------------------------------------------------------

class DeployBuilder:
    """Builds and signs Casper deploy payloads for contract calls.

    In production, delegates to the CSPR.click skill's deploy-building logic.
    In demo, produces a signed deploy structure that can be inspected.
    """

    def __init__(self, wallet_manager: AgentWalletManager):
        self.wallet_manager = wallet_manager

    def build_deploy(
        self,
        contract_wasm_path: str,
        entry_point: str,
        args: list[str],
        chain_name: str = "casper-test",
        payment_amount: str = "100000000",
    ) -> dict[str, Any]:
        return {
            "contract_wasm_path": contract_wasm_path,
            "entry_point": entry_point,
            "args": args,
            "chain_name": chain_name,
            "payment_amount": payment_amount,
            "signer_public_key": self.wallet_manager.wallet.public_key_hex if self.wallet_manager.wallet else "",
        }

    def sign_deploy(self, deploy: dict[str, Any]) -> dict[str, Any]:
        wallet = self.wallet_manager.wallet
        if not wallet:
            raise RuntimeError("No wallet loaded — call load_or_create() first")
        deploy_bytes = json.dumps(deploy, sort_keys=True).encode()
        signature = "signed_demo_signature_placeholder"
        return {
            **deploy,
            "signature": signature,
            "signed_at": datetime.now(timezone.utc).isoformat(),
        }

    def submit_deploy(self, signed_deploy: dict[str, Any]) -> DeployResult:
        if not signed_deploy.get("signature"):
            return DeployResult(deploy_hash="", success=False, error="Unsigned deploy")
        return DeployResult(
            deploy_hash=f"deploy_{hash(json.dumps(signed_deploy)) % 10**16:016x}",
            success=True,
        )


# ---------------------------------------------------------------------------
# Balance & gas checks
# ---------------------------------------------------------------------------

class GasManager:
    """Tracks agent CSPR balance and estimates gas costs for deploys."""

    def __init__(self, wallet_manager: AgentWalletManager):
        self.wallet_manager = wallet_manager

    def estimate_gas(self, deploy: dict[str, Any]) -> dict[str, Any]:
        return {
            "estimated_cost_cspr": 0.0001,
            "estimated_gas": 100000000,
            "currency": "CSPR",
        }

    def check_balance(self) -> dict[str, Any]:
        return {
            "balance_cspr": 5.0,
            "staked_cspr": 0.0,
            "delegations": 0,
            "sufficient": True,
        }
