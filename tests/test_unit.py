import pytest
import hashlib

from zkkyc.graph.entity import EntityService, EntityCreate, RelationshipCreate
from zkkyc.graph.nrs import NRSEngine, NRSDetails
from zkkyc.config import Settings


class TestEntityHashing:
    def test_hash_entity_id_consistent(self):
        settings = Settings(entity_salt="test_salt")
        service = EntityService(settings)
        
        id1 = "wallet_abc123"
        id2 = "wallet_abc123"
        
        hash1 = service._hash_entity_id(id1)
        hash2 = service._hash_entity_id(id2)
        
        assert hash1 == hash2

    def test_hash_entity_id_unique(self):
        settings = Settings(entity_salt="test_salt")
        service = EntityService(settings)
        
        hash1 = service._hash_entity_id("wallet_abc")
        hash2 = service._hash_entity_id("wallet_xyz")
        
        assert hash1 != hash2

    def test_hash_entity_id_sha256_format(self):
        settings = Settings(entity_salt="test_salt")
        service = EntityService(settings)
        
        result = service._hash_entity_id("test_id")
        
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestDeduplication:
    def test_dedupe_within_window(self):
        service = EntityService()
        
        service._dedupe_cache["entity_1"] = 1000000000.0
        
        result = service._check_dedupe("entity_1")
        
        assert result is True

    def test_dedupe_outside_window(self):
        service = EntityService()
        
        service._dedupe_cache["entity_1"] = 0.0
        
        import time
        result = service._check_dedupe("entity_1")
        
        assert result is False


class TestNRSDetails:
    def test_nrs_details_structure(self):
        details = NRSDetails(
            pagerank_score=0.5,
            betweenness_score=0.3,
            community_risk_score=0.0,
            raw_nrs=0.42,
        )
        
        assert details.raw_nrs == 0.42
        assert 0.0 <= details.raw_nrs <= 1.0


class TestNRSEngineNormalization:
    def test_normalize_scores_single_value(self):
        engine = NRSEngine()
        
        scores = {"a": 0.5, "b": 0.5}
        result = engine._normalize_scores(scores)
        
        assert all(v == 0.5 for v in result.values())

    def test_normalize_scores_range(self):
        engine = NRSEngine()
        
        scores = {"a": 0.1, "b": 0.2, "c": 0.3}
        result = engine._normalize_scores(scores)
        
        assert result["a"] == 0.0
        assert result["c"] == 1.0