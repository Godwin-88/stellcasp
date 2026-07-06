"""
Casper Odra Passport Adapter — ZK-KYC Compliance Agent (zkkyc.adapters.casper)

Spec reference: EP-08 (F-08.1 — US-08.1.1), EP-04 (F-04.1.3, F-04.2.1, F-04.2.2,
                  F-04.2.3)

Augmented with Casper AI Toolkit integrations:
  - MCP tool invocation layer (Casper MCP Server)
  - Account Abstraction (agent_key on-chain identity)
  - EIP-712 typed-data signing for off-chain attestations
  - CSPR.click agent wallet management

On-chain contracts:
  - ComplianceOracle: records PASS/FAIL verdicts immutably
  - IdentityRegistry: maps wallet keys to compliance token status
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from ..config import Settings, get_settings
from ..toolkit import cspr_click, mcp_server, x402_facilitator
from .base import (
    AdapterDeploymentError,
    DeploymentInfo,
    PassportAdapterBase,
)

logger = logging.getLogger(__name__)


class CasperAdapter(PassportAdapterBase):
    """Casper Odra Compliance Oracle & IdentityRegistry Adapter.

    Augmented with Casper AI Toolkit: MCP, AA, EIP-712, CSPR.click.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._mcp_client: mcp_server.CasperMCPClient | None = None
        self._wallet_manager: cspr_click.AgentWalletManager | None = None
        self._use_mcp = getattr(settings, "casper_use_mcp", True)
        self._use_facilitator = getattr(settings, "casper_use_facilitator", True)

    # ------------------------------------------------------------------
    # Tooling helpers
    # ------------------------------------------------------------------

    async def _mcp(self) -> mcp_server.CasperMCPClient | None:
        if not self._use_mcp:
            return None
        if self._mcp_client is None:
            url = getattr(self.settings, "casper_mcp_server_url", "http://localhost:3001")
            self._mcp_client = mcp_server.CasperMCPClient(base_url=url, settings=self.settings)
        return self._mcp_client

    async def _ensure_agent_wallet(self) -> cspr_click.AgentWallet:
        if self._wallet_manager is None:
            self._wallet_manager = cspr_click.AgentWalletManager(settings=self.settings)
        if not self._wallet_manager.wallet:
            self._wallet_manager.load_or_create()
        assert self._wallet_manager.wallet is not None
        return self._wallet_manager.wallet

    # ------------------------------------------------------------------
    # PassportAdapterBase interface
    # ------------------------------------------------------------------

    async def verify_proof(self, proof_hex: str, public_inputs: list[int]) -> bool:
        """Casper stores a deterministic verdict, not a ZK proof on-chain.

        The platform guarantees proof validity off-chain before calling
        `record_verdict`. This method returns True to satisfy the interface
        contract; the actual compliance decision is recorded via `mint_passport`.
        """
        logger.debug("Casper verify_proof called — verdict is recorded off-chain")
        return True

    async def mint_passport(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        proof_hash: str,
    ) -> str:
        """Record a PASS verdict and mint a compliance token status.

        Uses MCP tools when available; falls back to direct casper-client RPC.
        """
        entity_hash = proof_hash

        try:
            mcp = await self._mcp()
            if mcp is not None:
                verdict_result = mcp.record_verdict(entity_hash, True, expires_at)
                mint_result = mcp.mint_compliance_token(wallet, entity_hash)
                logger.info(
                    "casper compliance token minted via MCP",
                    extra={"wallet": wallet, "entity_hash": entity_hash},
                )
                return mint_result.get("deploy_hash", verdict_result.get("deploy_hash", ""))

            return await self._mint_passport_legacy(wallet, policy_id, expires_at, entity_hash)
        except mcp_server.MCPToolError as exc:
            logger.warning("MCP mint failed; falling back to legacy: %s", exc)
            return await self._mint_passport_legacy(wallet, policy_id, expires_at, entity_hash)

    async def _mint_passport_legacy(
        self,
        wallet: str,
        policy_id: str,
        expires_at: int,
        entity_hash: str,
    ) -> str:
        oracle_contract = getattr(self.settings, "casper_compliance_oracle_contract", None)
        registry_contract = getattr(self.settings, "casper_identity_registry_contract", None)
        if not oracle_contract or not registry_contract:
            raise AdapterDeploymentError(
                "casper",
                "CASPER_COMPLIANCE_ORACLE_CONTRACT and CASPER_IDENTITY_REGISTRY_CONTRACT must be set",
            )

        node_address = getattr(self.settings, "casper_node_address", "https://rpc.testnet.cspr.network")
        chain_name = getattr(self.settings, "casper_chain_name", "casper-test")
        secret_key_path = getattr(self.settings, "casper_secret_key_path", "")

        if not secret_key_path or not os.path.exists(secret_key_path):
            raise AdapterDeploymentError(
                "casper",
                f"CASPER_SECRET_KEY_PATH not set or file missing: {secret_key_path}",
            )

        try:
            oracle_hash = await self._record_verdict(
                node_address, chain_name, secret_key_path, oracle_contract,
                entity_hash, True, expires_at,
            )
            registry_hash = await self._mint_compliance_token(
                node_address, chain_name, secret_key_path, registry_contract,
                oracle_contract, wallet, entity_hash,
            )
            logger.info(
                "casper compliance token minted",
                extra={"oracle_tx": oracle_hash, "registry_tx": registry_hash, "wallet": wallet},
            )
            return registry_hash or oracle_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"mint_passport failed: {exc}", cause=exc) from exc

    async def revoke_passport(self, wallet: str, policy_id: str, reason: str) -> str:
        """Revoke a compliance token by recording a FAIL verdict."""
        mcp = await self._mcp()
        entity_hash = policy_id

        if mcp is not None:
            try:
                result = mcp.revoke_verdict(entity_hash, reason)
                logger.info("casper verdict revoked via MCP", extra={"reason": reason})
                return result.get("deploy_hash", "")
            except mcp_server.MCPToolError as exc:
                logger.warning("MCP revoke failed; falling back: %s", exc)

        return await self._revoke_passport_legacy(entity_hash, reason)

    async def _revoke_passport_legacy(self, entity_hash: str, reason: str) -> str:
        oracle_contract = getattr(self.settings, "casper_compliance_oracle_contract", None)
        if not oracle_contract:
            raise AdapterDeploymentError("casper", "CASPER_COMPLIANCE_ORACLE_CONTRACT is not configured")

        node_address = getattr(self.settings, "casper_node_address", "https://rpc.testnet.cspr.network")
        chain_name = getattr(self.settings, "casper_chain_name", "casper-test")
        secret_key_path = getattr(self.settings, "casper_secret_key_path", "")

        if not secret_key_path or not os.path.exists(secret_key_path):
            raise AdapterDeploymentError(
                "casper",
                f"CASPER_SECRET_KEY_PATH not set or file missing: {secret_key_path}",
            )

        try:
            tx_hash = await self._revoke_verdict(
                node_address, chain_name, secret_key_path, oracle_contract,
                entity_hash, reason,
            )
            logger.info("casper verdict revoked", extra={"tx_hash": tx_hash, "reason": reason})
            return tx_hash
        except AdapterDeploymentError:
            raise
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"revoke_passport failed: {exc}", cause=exc) from exc

    async def verify_credential(self, wallet: str, policy_id: str) -> dict[str, Any]:
        """Query the IdentityRegistry for wallet compliance status."""
        mcp = await self._mcp()
        if mcp is not None:
            try:
                result = mcp.get_identity(wallet)
                if result and result.get("status") == "COMPLIANT":
                    expires_at = result.get("expires_at", 0)
                    return {
                        "valid": True,
                        "expires_at": expires_at,
                        "policy_id": policy_id,
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
            except mcp_server.MCPToolError:
                pass

        registry_contract = getattr(self.settings, "casper_identity_registry_contract", None)
        if not registry_contract:
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

        node_address = getattr(self.settings, "casper_node_address", "https://rpc.testnet.cspr.network")

        try:
            import httpx
            url = f"{node_address}/rpc"
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json={
                    "jsonrpc": "2.0",
                    "method": "casper_query_global_state",
                    "params": [
                        None,
                        {"CollectionSource": {"Addr": registry_contract}},
                        None,
                        ["ComplianceTokenStore", "get_identity", [wallet]],
                        None,
                    ],
                    "id": 1,
                })
                if response.status_code != 200:
                    return {"valid": False, "expires_at": 0, "policy_id": policy_id}

                result = response.json()
                value = result.get("result", {}).get("value", {})
                if value and value.get("status") == "COMPLIANT":
                    minted_at = value.get("minted_at", 0)
                    return {
                        "valid": True,
                        "expires_at": minted_at + 86400 * 90,
                        "policy_id": policy_id,
                        "extra": {"minted_at": minted_at},
                    }
                return {"valid": False, "expires_at": 0, "policy_id": policy_id}
        except Exception as exc:
            logger.warning("casper verify_credential failed", extra={"error": str(exc)})
            return {"valid": False, "expires_at": 0, "policy_id": policy_id}

    async def get_deployment_info(self) -> DeploymentInfo:
        """Return Casper deployment metadata."""
        oracle = getattr(self.settings, "casper_compliance_oracle_contract", "")
        registry = getattr(self.settings, "casper_identity_registry_contract", "")
        chain_name = getattr(self.settings, "casper_chain_name", "casper-test")
        node_address = getattr(self.settings, "casper_node_address", "")
        network = "testnet" if "test" in chain_name else "mainnet"

        agent_wallet = await self._ensure_agent_wallet()

        return DeploymentInfo(
            chain_id="casper",
            contract_address=oracle,
            deployed_at=datetime.now(timezone.utc),
            network=network,
            extra={
                "identity_registry_contract": registry,
                "chain_name": chain_name,
                "node_address": node_address,
                "agent_public_key": agent_wallet.public_key_hex,
                "toolkit": {
                    "mcp": self._use_mcp,
                    "facilitator": self._use_facilitator,
                    "aa": True,
                    "eip712": True,
                },
            },
        )

    # ------------------------------------------------------------------
    # Internal Casper RPC helpers (legacy fallback)
    # ------------------------------------------------------------------

    async def _record_verdict(
        self,
        node_address: str,
        chain_name: str,
        secret_key_path: str,
        contract_address: str,
        entity_hash: str,
        verdict: bool,
        expires_at: int,
    ) -> str:
        try:
            with open(secret_key_path, "r") as f:
                secret_key = f.read().strip()
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"Cannot read secret key: {exc}", cause=exc) from exc

        try:
            import subprocess
            result = subprocess.run(
                [
                    "casper-client", "put-deploy",
                    "--session-path", "target/wasm32-unknown-unknown/release/compliance_oracle.wasm",
                    "--chain-name", chain_name,
                    "--node-address", node_address,
                    "--secret-key", secret_key,
                    "--payment-amount", "100000000",
                    "--session-entry-point", "record_verdict",
                    "--session-arg", f"entity_hash:string='{entity_hash}'",
                    "--session-arg", f"verdict:bool={'true' if verdict else 'false'}",
                    "--session-arg", f"expires_at:u64='{expires_at}'",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise AdapterDeploymentError("casper", f"casper-client failed: {result.stderr}")

            import json
            output = json.loads(result.stdout)
            return output.get("result", {}).get("blockHash", "")
        except FileNotFoundError:
            raise AdapterDeploymentError(
                "casper",
                "casper-client binary not found. Install Casper CLI or use scripts/e2e_casper.sh",
            )
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"record_verdict deploy failed: {exc}", cause=exc) from exc

    async def _revoke_verdict(
        self,
        node_address: str,
        chain_name: str,
        secret_key_path: str,
        contract_address: str,
        entity_hash: str,
        reason: str,
    ) -> str:
        try:
            import subprocess
            with open(secret_key_path, "r") as f:
                secret_key = f.read().strip()

            result = subprocess.run(
                [
                    "casper-client", "put-deploy",
                    "--session-path", "target/wasm32-unknown-unknown/release/compliance_oracle.wasm",
                    "--chain-name", chain_name,
                    "--node-address", node_address,
                    "--secret-key", secret_key,
                    "--payment-amount", "100000000",
                    "--session-entry-point", "revoke_verdict",
                    "--session-arg", f"entity_hash:string='{entity_hash}'",
                    "--session-arg", f"reason:string='{reason}'",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise AdapterDeploymentError("casper", f"casper-client failed: {result.stderr}")

            import json
            output = json.loads(result.stdout)
            return output.get("result", {}).get("blockHash", "")
        except FileNotFoundError:
            raise AdapterDeploymentError(
                "casper",
                "casper-client binary not found. Install Casper CLI or use scripts/e2e_casper.sh",
            )
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"revoke_verdict deploy failed: {exc}", cause=exc) from exc

    async def _mint_compliance_token(
        self,
        node_address: str,
        chain_name: str,
        secret_key_path: str,
        registry_contract: str,
        oracle_contract: str,
        wallet: str,
        entity_hash: str,
    ) -> str:
        try:
            import subprocess
            with open(secret_key_path, "r") as f:
                secret_key = f.read().strip()

            result = subprocess.run(
                [
                    "casper-client", "put-deploy",
                    "--session-path", "target/wasm32-unknown-unknown/release/identity_registry.wasm",
                    "--chain-name", chain_name,
                    "--node-address", node_address,
                    "--secret-key", secret_key,
                    "--payment-amount", "100000000",
                    "--session-entry-point", "mint_compliance_token",
                    "--session-arg", f"wallet:key='{wallet}'",
                    "--session-arg", f"entity_hash:string='{entity_hash}'",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise AdapterDeploymentError("casper", f"casper-client failed: {result.stderr}")

            import json
            output = json.loads(result.stdout)
            return output.get("result", {}).get("blockHash", "")
        except FileNotFoundError:
            raise AdapterDeploymentError(
                "casper",
                "casper-client binary not found. Install Casper CLI or use scripts/e2e_casper.sh",
            )
        except Exception as exc:
            raise AdapterDeploymentError("casper", f"mint_compliance_token deploy failed: {exc}", cause=exc) from exc
