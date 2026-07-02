import pytest

from zkkyc.graph.entity import EntityCreate, RelationshipCreate, EntityService
from zkkyc.graph.nrs import NRSEngine
from zkkyc.zk.proof import generate_zk_proof, verify_proof_local, ProofGenerationError


@pytest.mark.integration
async def test_graph_to_zk_flow(mocker):
    service = EntityService()
    engine = NRSEngine(service)

    mocker.patch.object(service, 'export_subgraph', return_value={
        "nodes": [{"id": "test_entity"}],
        "edges": []
    })

    nrs = await engine.compute_nrs("test_entity")
    assert nrs.raw_nrs >= 0.0
    assert nrs.raw_nrs <= 1.0

    mocker.patch('subprocess.run')

    proof = generate_zk_proof(nrs.raw_nrs, 0.75)
    assert "proof_hex" in proof
    assert "public_inputs" in proof

    verified = verify_proof_local(proof["proof_hex"], proof["public_inputs"])
    assert verified is True