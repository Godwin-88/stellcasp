"""
Unit tests for Casper AI Toolkit augmentations.

Spec reference: casper.md augmentations 1–8
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from zkkyc.config import Settings
from zkkyc.signing import (
    ComplianceAttestationSigner,
    EIP712Domain,
    TypedData,
    TypedDataField,
    build_message_hash,
    compute_domain_separator,
)
from zkkyc.toolkit import cspr_click, events, mcp_server, x402_facilitator
from zkkyc.agents.settlement import SettlementAgent


# ===========================================================================
# Helpers
# ===========================================================================

def _settings() -> Settings:
    return Settings(
        entity_salt="toolkit_test_salt",
        casper_treasury_public_key="01" * 32,
        x402_price_cspr=0.001,
    )


# ===========================================================================
# EIP-712 / signing
# ===========================================================================

class TestEIP712:
    def test_domain_separator_deterministic(self):
        domain = EIP712Domain(name="ZKCO", version="1", chain_id=1, verifying_contract="0xabc")
        ds1 = compute_domain_separator(domain)
        ds2 = compute_domain_separator(domain)
        assert ds1 == ds2
        assert len(ds1) == 32

    def test_domain_separator_changes_with_chain(self):
        d1 = EIP712Domain(name="ZKCO", version="1", chain_id=1, verifying_contract="0xabc")
        d2 = EIP712Domain(name="ZKCO", version="1", chain_id=2, verifying_contract="0xabc")
        assert compute_domain_separator(d1) != compute_domain_separator(d2)

    def test_build_message_hash(self):
        td = TypedData(
            domain=EIP712Domain(name="ZKCO", version="1", chain_id=1, verifying_contract="0xabc"),
            types={"Attestation": [TypedDataField("data", "string")]},
            primary_type="Attestation",
            message={"data": "hello"},
        )
        h = build_message_hash(td)
        assert len(h) == 32

    def test_sign_compliance_attestation(self):
        signer = ComplianceAttestationSigner(
            private_key_hex="a" * 64,
            domain=EIP712Domain(name="ZKCO", version="1", chain_id=1, verifying_contract="0xabc"),
        )
        result = signer.sign_compliance_attestation(
            entity_hash="0" * 64,
            policy_id="standard",
            expires_at=2000000000,
            chain_target="casper",
            decision="PASS",
            confidence=0.95,
        )
        assert result.signature
        assert result.domain_separator
        assert result.signer_public_key
        assert "PASS" in result.signed_payload or len(result.signed_payload) == 64


# ===========================================================================
# x402 Facilitator
# ===========================================================================

class TestX402Facilitator:
    def test_create_payment_challenge_shape(self):
        settings = _settings()
        fac = x402_facilitator.X402Facilitator(
            base_url="http://localhost:3000", settings=settings
        )
        with patch.object(fac._client, "post", return_value=MagicMock(
            status_code=200, json=MagicMock(return_value={"payment_required": True, "amount_cspr": "0.001"})
        )) as mock_post:
            result = fac.create_payment_challenge()
            mock_post.assert_called_once()
        assert result["payment_required"] is True

    def test_facilitator_fallback_on_unreachable(self):
        settings = _settings()
        fac = x402_facilitator.X402Facilitator(
            base_url="http://localhost:3000", settings=settings
        )
        with patch.object(fac._client, "post", side_effect=Exception("connection refused")):
            result = fac.create_payment_challenge()
        assert result["payment_required"] is True
        assert result["facilitator_fallback"] is True

    def test_verify_payment_success(self):
        settings = _settings()
        fac = x402_facilitator.X402Facilitator(
            base_url="http://localhost:3000", settings=settings
        )
        with patch.object(fac._client, "post", return_value=MagicMock(
            status_code=200, json=MagicMock(return_value={"verified": True, "amount_cspr": 0.001})
        )):
            result = fac.verify_payment("deploy_hash_123")
        assert result["verified"] is True
        assert result["amount_cspr"] == 0.001

    def test_verify_payment_rejected(self):
        settings = _settings()
        fac = x402_facilitator.X402Facilitator(
            base_url="http://localhost:3000", settings=settings
        )
        mock_response = MagicMock(status_code=402, text="rejected")
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rejected", request=None, response=mock_response
        )
        with patch.object(fac._client, "post", return_value=mock_response):
            with pytest.raises(x402_facilitator.X402FacilitatorError) as exc_info:
                fac.verify_payment("deploy_hash_123")
            assert exc_info.value.status_code == 402


# ===========================================================================
# Casper MCP Server
# ===========================================================================

class TestCasperMCP:
    def test_call_tool_success(self):
        client = mcp_server.CasperMCPClient(base_url="http://localhost:3001")
        with patch.object(client._client, "post", return_value=MagicMock(
            status_code=200, json=MagicMock(return_value={
                "result": {"content": [{"type": "text", "text": '{"ok": true}'}]}
            })
        )):
            result = client.call_tool("get_verdict", {"entity_hash": "abc"})
        assert result["ok"] is True

    def test_call_tool_error(self):
        client = mcp_server.CasperMCPClient(base_url="http://localhost:3001")
        with patch.object(client._client, "post", return_value=MagicMock(
            status_code=200, json=MagicMock(return_value={
                "result": {"error": {"message": "not found"}}
            })
        )):
            with pytest.raises(mcp_server.MCPToolError) as exc_info:
                client.call_tool("get_verdict", {"entity_hash": "abc"})
            assert "get_verdict" in str(exc_info.value)

    def test_wrapper_methods(self):
        client = mcp_server.CasperMCPClient(base_url="http://localhost:3001")
        with patch.object(client, "call_tool", return_value={"ok": True}) as mock_call:
            client.record_verdict("eh", True, 999)
            client.get_identity("01" * 32)
            client.mint_compliance_token("01" * 32, "eh")
            assert mock_call.call_count == 3


# ===========================================================================
# CSPR.click skill wrapper
# ===========================================================================

class TestCSPRClick:
    def test_create_ephemeral_wallet(self):
        wm = cspr_click.AgentWalletManager(settings=_settings())
        wallet = wm._create_ephemeral()
        assert len(wallet.public_key_hex) == 64
        assert wallet.secret_key_path is None

    def test_deploy_builder(self):
        wm = cspr_click.AgentWalletManager(settings=_settings())
        wm.load_or_create()
        builder = cspr_click.DeployBuilder(wallet_manager=wm)
        deploy = builder.build_deploy(
            contract_wasm_path="test.wasm",
            entry_point="record_verdict",
            args=["entity_hash:string='test'"],
        )
        assert deploy["entry_point"] == "record_verdict"
        assert "signature" not in deploy

    def test_sign_deploy_requires_wallet(self):
        wm = cspr_click.AgentWalletManager(settings=_settings())
        builder = cspr_click.DeployBuilder(wallet_manager=wm)
        with pytest.raises(RuntimeError, match="No wallet loaded"):
            builder.sign_deploy({})

    def test_gas_manager(self):
        wm = cspr_click.AgentWalletManager(settings=_settings())
        gm = cspr_click.GasManager(wallet_manager=wm)
        assert gm.estimate_gas({})["estimated_cost_cspr"] > 0
        assert gm.check_balance()["sufficient"] is True


# ===========================================================================
# SSE events
# ===========================================================================

class TestSSEEvents:
    def test_event_creation(self):
        ev = events.CasperEvent(event_type="VerdictRecorded", data={"ok": True})
        assert ev.event_type == "VerdictRecorded"
        assert ev.data["ok"] is True
        assert ev.received_at

    def test_event_processor_registers(self):
        stream = events.CSPRCloudEventStream(settings=_settings())
        handler_called = False

        async def fake_handler(event: events.CasperEvent) -> None:
            nonlocal handler_called
            handler_called = True

        stream.register("VerdictRecorded", fake_handler)
        import asyncio
        asyncio.run(stream.simulate_event("VerdictRecorded", {"ok": True}))
        assert handler_called is True


# ===========================================================================
# Settlement Agent
# ===========================================================================

class TestSettlementAgent:
    async def test_settle_casper_success(self):
        mock_adapter = MagicMock()
        mock_adapter.mint_passport = AsyncMock(return_value="tx_123")
        agent = SettlementAgent(settings=_settings(), adapter=mock_adapter)
        result = await agent.settle(
            chain_target="casper",
            wallet="01" * 32,
            policy_id="standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert result.chain_target == "casper"
        assert result.success is True
        assert result.agent_key
        assert result.tx_hash == "tx_123"

    async def test_settle_stellar(self):
        agent = SettlementAgent(settings=_settings())
        result = await agent.settle(
            chain_target="stellar",
            wallet="G" * 56,
            policy_id="stellar-standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert result.chain_target == "stellar"
        assert result.success is True

    async def test_tool_calls_logged(self):
        agent = SettlementAgent(settings=_settings())
        result = await agent.settle(
            chain_target="casper",
            wallet="01" * 32,
            policy_id="standard",
            expires_at=2000000000,
            proof_hash="0" * 64,
        )
        assert result.tool_calls is not None
        assert len(result.tool_calls) > 0
        assert any("cspr_click" in tc["tool"] for tc in result.tool_calls)
