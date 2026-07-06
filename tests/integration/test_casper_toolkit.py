"""
Integration tests for Casper AI Toolkit flow.

Spec reference: casper.md augmentation end-to-end
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zkkyc.adapters.casper import CasperAdapter
from zkkyc.agents.settlement import SettlementAgent, SettlementResult
from zkkyc.config import Settings
from zkkyc.toolkit import cspr_click, events, mcp_server
from zkkyc.toolkit.events import CasperEvent


# ===========================================================================
# Helpers
# ===========================================================================

def _settings() -> Settings:
    return Settings(
        entity_salt="integration_salt",
        casper_treasury_public_key="01" * 32,
        casper_compliance_oracle_contract="oracle_contract_hash",
        casper_identity_registry_contract="registry_contract_hash",
        x402_price_cspr=0.001,
    )


# ===========================================================================
# Casper adapter with toolkit
# ===========================================================================

class TestCasperAdapterToolkit:
    async def test_mint_passport_via_mcp(self):
        settings = _settings()
        adapter = CasperAdapter(settings=settings)

        mock_mcp = MagicMock(spec=mcp_server.CasperMCPClient)
        mock_mcp.record_verdict.return_value = {"deploy_hash": "tx_abc"}
        mock_mcp.mint_compliance_token.return_value = {"deploy_hash": "tx_def"}
        adapter._mcp_client = mock_mcp

        tx_hash = await adapter.mint_passport(
            wallet="01" * 32,
            policy_id="standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert tx_hash == "tx_def"
        mock_mcp.record_verdict.assert_called_once()
        mock_mcp.mint_compliance_token.assert_called_once()

    async def test_mint_passport_falls_back_on_mcp_error(self):
        settings = _settings()
        adapter = CasperAdapter(settings=settings)

        mock_mcp = MagicMock(spec=mcp_server.CasperMCPClient)
        mock_mcp.record_verdict.side_effect = mcp_server.MCPToolError("record_verdict", "fail")
        adapter._mcp_client = mock_mcp

        with patch.object(adapter, "_mint_passport_legacy", new_callable=AsyncMock, return_value="tx_legacy"):
            tx_hash = await adapter.mint_passport(
                wallet="01" * 32,
                policy_id="standard",
                expires_at=2000000000,
                proof_hash="0" * 64,
            )
        assert tx_hash == "tx_legacy"

    async def test_get_deployment_info_includes_toolkit(self):
        settings = _settings()
        adapter = CasperAdapter(settings=settings)
        info = await adapter.get_deployment_info()
        assert info.extra["toolkit"]["mcp"] is True
        assert info.extra["toolkit"]["aa"] is True
        assert info.extra["toolkit"]["eip712"] is True
        assert "agent_public_key" in info.extra


# ===========================================================================
# Settlement Agent end-to-end
# ===========================================================================

class TestSettlementAgentE2E:
    async def test_full_casper_flow(self):
        settings = _settings()
        adapter = CasperAdapter(settings=settings)
        agent = SettlementAgent(settings=settings, adapter=adapter)

        result = await agent.settle(
            chain_target="casper",
            wallet="01" * 32,
            policy_id="standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert isinstance(result, SettlementResult)
        assert result.chain_target == "casper"
        assert result.success is True
        assert result.agent_key
        assert result.tx_hash
        assert any("cspr_click" in tc["tool"] for tc in (result.tool_calls or []))

    async def test_full_stellar_flow(self):
        settings = _settings()
        adapter = CasperAdapter(settings=settings)
        agent = SettlementAgent(settings=settings, adapter=adapter)

        result = await agent.settle(
            chain_target="stellar",
            wallet="G" * 56,
            policy_id="stellar-standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert result.chain_target == "stellar"
        assert result.success is True


# ===========================================================================
# x402 payment flow
# ===========================================================================

class TestX402Flow:
    async def test_facilitator_integration_in_x402(self):
        settings = _settings()
        from zkkyc.payments.x402 import X402PaymentService

        svc = X402PaymentService(settings=settings)

        mock_fac = MagicMock()
        mock_fac.verify_payment.return_value = {
            "verified": True,
            "amount_cspr": 0.001,
        }
        svc._facilitator = mock_fac

        result = await svc.verify_payment(
            deploy_hash="deploy_123",
            entity_hash="eh_123",
            api_key_id="key_123",
        )
        assert result["verified"] is True
        mock_fac.verify_payment.assert_called_once_with(
            "deploy_123", entity_hash="eh_123", api_key_id="key_123"
        )

    async def test_x402_challenge_delegates_to_facilitator(self):
        settings = _settings()
        from zkkyc.payments.x402 import X402PaymentService

        svc = X402PaymentService(settings=settings)
        mock_fac = MagicMock()
        mock_fac.create_payment_challenge.return_value = {
            "payment_required": True,
            "amount_cspr": "0.001",
        }
        svc._facilitator = mock_fac

        result = svc.create_payment_challenge()
        assert result["payment_required"] is True
        mock_fac.create_payment_challenge.assert_called_once()


# ===========================================================================
# Signing flow
# ===========================================================================

class TestSigningFlow:
    async def test_end_to_end_sign_and_verify_structure(self):
        domain = EIP712Domain(
            name="ZKCO Compliance Oracle",
            version="1",
            chain_id=1,
            verifying_contract="0xabc123",
        )
        signer = ComplianceAttestationSigner(
            private_key_hex="a" * 64,
            domain=domain,
        )
        attestation = signer.sign_compliance_attestation(
            entity_hash="entity_hash_123",
            policy_id="standard",
            expires_at=2000000000,
            chain_target="casper",
            decision="PASS",
            confidence=0.95,
        )
        assert attestation.signature
        assert attestation.domain_separator
        assert attestation.signer_public_key == "a" * 64
