"""
Integration test — graph intelligence to ZK proof pipeline.

Spec reference: EP-01 (F-01.2, F-01.3, F-01.4), EP-02 (F-02.1)
US-02.1.2, US-02.1.3

Mocks Neo4j (no live instance needed) and patches the nargo subprocess
so this test is fully offline while validating the end-to-end data flow:
  Entity → subgraph export → CI computation → proof generation → local verify.

Run with: pytest tests/integration/test_graph_to_zk.py -v -m integration
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zkkyc.graph.entity import EntityService
from zkkyc.graph.nrs import CIEngine
from zkkyc.zk.proof import generate_zk_proof, verify_proof_local


# ===========================================================================
# Helpers
# ===========================================================================

def _make_fake_subgraph():
    """Small synthetic subgraph mimicking Neo4j export_subgraph output."""
    return {
        "nodes": [
            {"id": "eh_src"},
            {"id": "eh_mid_a"},
            {"id": "eh_mid_b"},
            {"id": "eh_dst"},
        ],
        "edges": [
            {"source": "eh_src", "target": "eh_mid_a", "amount": 100.0, "tx_hash": "t1", "timestamp": int(time.time()) - 100},
            {"source": "eh_src", "target": "eh_mid_b", "amount": 200.0, "tx_hash": "t2", "timestamp": int(time.time()) - 200},
            {"source": "eh_mid_a", "target": "eh_dst", "amount": 50.0,  "tx_hash": "t3", "timestamp": int(time.time()) - 300},
            {"source": "eh_mid_b", "target": "eh_dst", "amount": 75.0,  "tx_hash": "t4", "timestamp": int(time.time()) - 400},
        ],
    }


async def _fake_export_subgraph(self, entity_id, hops=3):
    return _make_fake_subgraph()


def _make_mock_entity_service():
    svc = MagicMock(spec=EntityService)
    svc.settings = None
    svc._weights = {
        "L": 0.10, "C": 0.20, "J": 0.15,
        "S": 0.25, "A": 0.20, "B": 0.10,
    }
    svc._DENSITY_FLOOR = 0.05
    svc._MIN_NEIGHBOURS = 3
    svc.driver = MagicMock()
    svc.export_subgraph = _fake_export_subgraph
    svc.hash_entity_id = MagicMock(side_effect=lambda eid: f"eh_{eid}")
    return svc


# ===========================================================================
# CIEngine tests with mocked subgraph
# ===========================================================================

class TestCIEngineWithMockedGraph:
    """CIEngine.compute_compliance_index *without* a live Neo4j instance."""

    @pytest.fixture()
    def engine(self):
        svc = _make_mock_entity_service()
        return CIEngine(entity_service=svc)

    def test_ci_in_valid_range(self, engine):
        result = asyncio.get_event_loop().run_until_complete(
            engine.compute_compliance_index("eh_src")
        )
        assert 0.0 <= result.compliance_index <= 1.0

    def test_factor_breakdown_non_negative(self, engine):
        result = asyncio.get_event_loop().run_until_complete(
            engine.compute_compliance_index("eh_src")
        )
        for dim in ("L", "C", "J", "S", "A", "B"):
            val = getattr(result.factor_breakdown, dim)
            assert 0.0 <= val <= 1.0, f"{dim} out of range: {val}"

    def test_jurisdiction_flag_is_binary(self, engine):
        result = asyncio.get_event_loop().run_until_complete(
            engine.compute_compliance_index("eh_src")
        )
        assert result.jurisdiction_flag in (0, 1)

    def test_weights_sum_to_one(self, engine):
        total = sum(engine._weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_manifold_score_in_range(self, engine):
        result = asyncio.get_event_loop().run_until_complete(
            engine.compute_compliance_index("eh_src")
        )
        assert 0.0 <= result.manifold_score <= 1.0

    def test_community_id_persist_called(self):
        engine = CIEngine(entity_service=_make_mock_entity_service())
        calls = []

        async def fake_set(self, entity_hash, community_id):
            calls.append((entity_hash, community_id))

        import zkkyc.graph.entity as entity_mod
        original = entity_mod.EntityService.set_community_id_by_hash
        entity_mod.EntityService.set_community_id_by_hash = fake_set

        try:
            asyncio.get_event_loop().run_until_complete(
                engine.compute_compliance_index("eh_src")
            )
            assert len(calls) > 0, "set_community_id_by_hash was never called"
        finally:
            entity_mod.EntityService.set_community_id_by_hash = original


# ===========================================================================
# ZK proof pipeline (EP-02 F-02.1)
# ===========================================================================

class TestZKProofPipeline:
    """End-to-end: NRS → proof → verify (with mocked subprocess)."""

    @pytest.fixture(autouse=True)
    def _patch_subprocess(self, monkeypatch):
        """Replace the internal _run_subprocess with a fake that produces
        a valid-looking proof and returns success on verify."""


        async def fake_run(cmd, cwd, timeout):
            assert cmd[0] == "nargo"
            if cmd[1] == "prove":
                proof_file = Path(cwd) / "proofs" / "proof"
                proof_file.parent.mkdir(parents=True, exist_ok=True)
                proof_file.write_bytes(b"\xab\xcd" * 32)
                return 0, "", ""
            elif cmd[1] == "verify":
                return 0, "Proof verified successfully\n", ""
            return 1, "", f"unknown command: {cmd}"

        monkeypatch.setattr("zkkyc.zk.proof._run_subprocess", fake_run)

    @pytest.mark.integration
    async def test_prove_and_verify(self):
        nrs_value = 0.42
        threshold = 0.75

        proof = await generate_zk_proof(nrs_value, threshold)
        assert "proof_hex" in proof
        assert "public_inputs" in proof
        assert proof["proof_hex"]
        assert len(proof["proof_hex"]) > 0

        verified = await verify_proof_local(proof["proof_hex"], proof["public_inputs"])
        assert verified is True

    @pytest.mark.integration
    async def test_proof_hex_is_hex_string(self):
        proof = await generate_zk_proof(0.1, 0.5)
        hex_str = proof["proof_hex"]
        assert all(c in "0123456789abcdef" for c in hex_str)

    @pytest.mark.integration
    async def test_verify_rejects_empty_proof(self):
        result = await verify_proof_local("", [75_000])
        assert result is False

    @pytest.mark.integration
    async def test_verify_rejects_empty_inputs(self):
        result = await verify_proof_local("abcd" * 10, [])
        assert result is False

    @pytest.mark.integration
    async def test_verify_rejects_non_hex(self):
        result = await verify_proof_local("not-hex-at-all", [75_000])
        assert result is False

    @pytest.mark.integration
    async def test_generate_returns_required_keys(self):
        proof = await generate_zk_proof(0.3, 0.75)
        assert set(proof.keys()) == {"proof_hex", "public_inputs", "generated_at"}
        assert isinstance(proof["public_inputs"], list)
        assert len(proof["public_inputs"]) >= 1


# ===========================================================================
# CIEngine backward-compat NRSEngine shim
# ===========================================================================

class TestNRSEngineShim:
    """NRSEngine wraps CIEngine; verify the mapping is correct."""

    def test_sync_variant(self):
        from zkkyc.graph.nrs import NRSEngine

        engine = NRSEngine(entity_service=_make_mock_entity_service())
        subgraph = _make_fake_subgraph()
        result = engine.compute_nrs_sync(subgraph=subgraph)
        assert 0.0 <= result.raw_nrs <= 1.0

    def test_nrs_maps_to_compliance_index(self):
        from zkkyc.graph.nrs import NRSEngine

        engine = NRSEngine(entity_service=_make_mock_entity_service())
        subgraph = _make_fake_subgraph()
        nrs = engine.compute_nrs_sync(subgraph=subgraph)
        ci_result = engine._ci.compute_compliance_index_sync(
            entity_id="eh_src", subgraph=subgraph
        )
        assert abs(nrs.raw_nrs - ci_result.compliance_index) < 1e-6
