"""
Multi-Factor Compliance Index (CI) engine and AML incident detection —
ZK-KYC Compliance Agent (zkkyc.graph.nrs)

Spec references:
  EP-01 F-01.2 (NRS — retained as AML Topology Risk factor A)
  EP-01 F-01.3 (AML Incident Detection)
  EP-01 F-01.4 (Six-Factor CI: L, C, J, S, A, B)
  EP-01 F-01.5 (Behavioural manifold — B factor stub, see STUB note)

v2.0 Architecture Change
-------------------------
The previous single NRS scalar (0.4*PageRank + 0.35*Betweenness + 0.25*Community)
is replaced by a six-factor Compliance Index:

  CI = w1*L + w2*C + w3*J + w4*S + w5*A + w6*B

where:
  L  Liquidity Risk        — transaction volume volatility (30-day trailing)
  C  Counterparty Risk     — PageRank-weighted avg risk of 1-hop counterparties
  J  Jurisdiction Risk     — fraction of counterparties in FATF grey/non-cooperative list
  S  Sanctions Exposure    — betweenness overlap with sanctioned-entity nodes
  A  AML Topology Risk     — Louvain community risk + structural anomaly penalty
  B  Behavioural Risk      — deviation from entity's historical baseline (manifold stub)

Weights are configurable via env vars CI_WEIGHT_L/C/J/S/A/B (default sum = 1.0).
The CI and all factor values are PRIVATE — never returned to API callers.
Only the proof that CI < ci_threshold is exposed (US-01.4.2).

Cross-module hash contract
---------------------------
export_subgraph() returns nodes/edges keyed by entity_hash (SHA-256 of raw id).
All lookups in this module use entity_hash; raw ids never appear after the
hash_entity_id() call at the top of compute_compliance_index(). (US-06.1.2)

STUB: Behavioural Risk (B factor) and Node2Vec manifold score
--------------------------------------------------------------
Full Node2Vec + k-means clustering (EP-01 F-01.5) requires `node2vec` (PyPI)
and a trained cluster model. Until entity_embeddings and embedding_clusters
tables are seeded, B and manifold_score are computed from a lightweight
z-score heuristic on recent vs trailing transaction volume.
Replace _compute_behavioural_risk() and compute_manifold_score() with the
full Node2Vec implementation once EP-01 F-01.5 is completed.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx
import networkx as nx
from pydantic import BaseModel

from .entity import EntityService
from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #

class NRSEngineError(Exception):
    pass


class IncidentServiceError(Exception):
    pass


class WeightConfigError(NRSEngineError):
    pass


# --------------------------------------------------------------------------- #
# Jurisdiction Risk Lookup (US-01.4.3)
# --------------------------------------------------------------------------- #

_DEFAULT_JURISDICTION_RISK: dict[str, float] = {
    "AF": 1.0, "MM": 1.0, "KP": 1.0, "IR": 1.0,
    "BF": 0.85, "CM": 0.85, "CD": 0.85, "HT": 0.85, "ML": 0.85,
    "MZ": 0.85, "NG": 0.85, "PK": 0.85, "PH": 0.85, "SS": 0.85,
    "SY": 0.85, "TZ": 0.85, "VN": 0.85, "YE": 0.85,
    "CU": 0.90, "VE": 0.75, "RU": 0.70,
    "__DEFAULT__": 0.5,
}

_jurisdiction_risk_table: dict[str, float] = dict(_DEFAULT_JURISDICTION_RISK)


def get_jurisdiction_risk(iso2: str | None) -> tuple[float, bool]:
    """Returns (risk_score, unknown_flag)."""
    if not iso2:
        return _jurisdiction_risk_table["__DEFAULT__"], True
    score = _jurisdiction_risk_table.get(iso2.upper())
    if score is None:
        return _jurisdiction_risk_table["__DEFAULT__"], True
    return score, False


def refresh_jurisdiction_table(updates: dict[str, float]) -> None:
    """US-01.4.3: Called by admin refresh endpoint. Validates before writing."""
    bad = {k: v for k, v in updates.items() if not 0.0 <= v <= 1.0}
    if bad:
        raise NRSEngineError(f"Jurisdiction scores must be in [0.0, 1.0]. Bad: {bad}")
    _jurisdiction_risk_table.update(updates)
    logger.info("jurisdiction_risk_table refreshed", extra={"count": len(updates)})


# --------------------------------------------------------------------------- #
# Result models
# --------------------------------------------------------------------------- #

class FactorBreakdown(BaseModel):
    L: float
    C: float
    J: float
    S: float
    A: float
    B: float
    B_is_stub: bool = True


class ComplianceIndexResult(BaseModel):
    """PRIVATE — never serialised to API responses (US-01.4.2).
    This is the private witness fed into the ZK circuit."""
    compliance_index: float
    factor_breakdown: FactorBreakdown
    manifold_score: float
    jurisdiction_flag: int
    weights_used: dict[str, float]
    density_floor_applied: bool = False
    anomaly_penalty_applied: bool = False
    computed_at: datetime | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.computed_at is None:
            object.__setattr__(self, "computed_at", datetime.now(timezone.utc))


class NRSDetails(BaseModel):
    """Backward-compatibility shim — maps CI components to old NRS field names."""
    pagerank_score: float
    betweenness_score: float
    community_risk_score: float
    raw_nrs: float
    density_floor_applied: bool = False
    anomaly_penalty_applied: bool = False


# --------------------------------------------------------------------------- #
# CI Engine
# --------------------------------------------------------------------------- #

class CIEngine:
    """Computes the six-factor Compliance Index.

    Default weights (US-01.4.2):
      w1=0.10 (L), w2=0.20 (C), w3=0.15 (J),
      w4=0.25 (S), w5=0.20 (A), w6=0.10 (B)

    Override via CI_WEIGHT_L/C/J/S/A/B env vars. Must sum to 1.0.
    """

    _LOUVAIN_SEED = 42
    _DENSITY_FLOOR = 0.05
    _MIN_NEIGHBOURS = 3
    _COMMUNITY_RISK_PERCENTILE = 90
    _COMMUNITY_RISK_RATIO = 0.3
    _ANOMALY_PENALTY = 0.15
    _WEIGHT_TOL = 1e-6

    def __init__(
        self,
        entity_service: EntityService | None = None,
        settings: Settings | None = None,
    ):
        self.entity_service = entity_service or EntityService()
        self.settings = settings or get_settings()
        self._weights = self._load_and_validate_weights()

    def _load_and_validate_weights(self) -> dict[str, float]:
        s = self.settings
        w = {
            "L": float(getattr(s, "ci_weight_l", 0.10)),
            "C": float(getattr(s, "ci_weight_c", 0.20)),
            "J": float(getattr(s, "ci_weight_j", 0.15)),
            "S": float(getattr(s, "ci_weight_s", 0.25)),
            "A": float(getattr(s, "ci_weight_a", 0.20)),
            "B": float(getattr(s, "ci_weight_b", 0.10)),
        }
        total = sum(w.values())
        if abs(total - 1.0) > self._WEIGHT_TOL:
            raise WeightConfigError(
                f"CI weights must sum to 1.0; got {total:.6f}. "
                "Check CI_WEIGHT_L/C/J/S/A/B env vars."
            )
        return w

    # ------------------------------------------------------------------ #
    # Graph construction
    # ------------------------------------------------------------------ #

    def _build_graph(self, subgraph: dict) -> nx.DiGraph:
        G = nx.DiGraph()
        for node in subgraph.get("nodes", []):
            G.add_node(node["id"])
        for edge in subgraph.get("edges", []):
            G.add_edge(
                edge["source"], edge["target"],
                amount=edge.get("amount", 0.0),
                tx_hash=edge.get("tx_hash", ""),
                timestamp=edge.get("timestamp", 0),
            )
        return G

    # ------------------------------------------------------------------ #
    # Shared primitives
    # ------------------------------------------------------------------ #

    def _normalize(self, scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}
        lo, hi = min(scores.values()), max(scores.values())
        if hi == lo:
            return {k: 0.5 for k in scores}
        return {k: (v - lo) / (hi - lo) for k, v in scores.items()}

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        if len(s) == 1:
            return s[0]
        rank = (pct / 100.0) * (len(s) - 1)
        lo = int(rank)
        hi = min(lo + 1, len(s) - 1)
        return s[lo] + (s[hi] - s[lo]) * (rank - lo)

    def _compute_pagerank(self, G: nx.DiGraph, target: str) -> tuple[dict[str, float], bool]:
        if G.number_of_nodes() == 0:
            return {}, False
        try:
            raw = nx.pagerank(G, alpha=0.85, max_iter=100)
        except nx.PowerIterationFailedConvergence:
            n = G.number_of_nodes()
            raw = {node: 1.0 / n for node in G.nodes()}
        norm = self._normalize(raw)
        floor_applied = False
        if target in G:
            nbrs = set(G.predecessors(target)) | set(G.successors(target))
            if len(nbrs) < self._MIN_NEIGHBOURS:
                logger.warning("insufficient_graph_density",
                               extra={"entity_hash": target, "neighbours": len(nbrs)})
                norm[target] = max(norm.get(target, 0.0), self._DENSITY_FLOOR)
                floor_applied = True
        return norm, floor_applied

    def _compute_betweenness(self, G: nx.DiGraph) -> dict[str, float]:
        if G.number_of_nodes() == 0:
            return {}
        return self._normalize(nx.betweenness_centrality(G))

    def _compute_communities(self, G: nx.DiGraph) -> list[set[str]]:
        if G.number_of_nodes() == 0:
            return []
        return list(nx.community.louvain_communities(G.to_undirected(), seed=self._LOUVAIN_SEED))

    def _compute_community_risk(
        self, G: nx.DiGraph, pagerank: dict[str, float], communities: list[set[str]]
    ) -> dict[str, float]:
        if not pagerank or not communities:
            return {n: 0.0 for n in G.nodes()}
        threshold = self._percentile(list(pagerank.values()), self._COMMUNITY_RISK_PERCENTILE)
        node_to_comm = {node: i for i, comm in enumerate(communities) for node in comm}
        result: dict[str, float] = {}
        for node in G.nodes():
            cid = node_to_comm.get(node)
            if cid is None:
                result[node] = 0.0
                continue
            comm = communities[cid]
            high = sum(1 for n in comm if pagerank.get(n, 0.0) > threshold)
            result[node] = 1.0 if (high / len(comm) if comm else 0.0) > self._COMMUNITY_RISK_RATIO else 0.0
        return result

    # ------------------------------------------------------------------ #
    # Factor L — Liquidity Risk
    # Coefficient of variation of transaction amounts on 1-hop edges.
    # ------------------------------------------------------------------ #

    def _compute_L(self, G: nx.DiGraph, target: str) -> float:
        amounts = [
            G[u][v].get("amount", 0.0)
            for u, v in list(G.out_edges(target)) + list(G.in_edges(target))
            if G[u][v].get("amount", 0.0) > 0
        ]
        if len(amounts) < 2:
            return self._DENSITY_FLOOR
        mean = statistics.mean(amounts)
        if mean == 0:
            return self._DENSITY_FLOOR
        return min(1.0, statistics.stdev(amounts) / mean / 2.0)

    # ------------------------------------------------------------------ #
    # Factor C — Counterparty Risk
    # PR-weighted average PR of 1-hop counterparties.
    # ------------------------------------------------------------------ #

    def _compute_C(self, G: nx.DiGraph, target: str, pagerank: dict[str, float]) -> float:
        nbrs = list(G.successors(target)) + list(G.predecessors(target))
        if not nbrs:
            return self._DENSITY_FLOOR
        total_w = sum(pagerank.get(n, 0.0) for n in nbrs)
        if total_w == 0:
            return statistics.mean(pagerank.get(n, 0.0) for n in nbrs)
        return sum(pagerank.get(n, 0.0) ** 2 for n in nbrs) / total_w

    # ------------------------------------------------------------------ #
    # Factor J — Jurisdiction Risk  (US-01.4.3)
    # ------------------------------------------------------------------ #

    async def _compute_J(
        self, G: nx.DiGraph, target: str, entity_hash: str
    ) -> tuple[float, int]:
        """Returns (J_score, jurisdiction_flag: 0|1)."""
        nbrs = list(set(G.successors(target)) | set(G.predecessors(target)))
        if not nbrs:
            return self._DENSITY_FLOOR, 0

        ids = list(set(nbrs) | {target})
        async with self.entity_service.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity) WHERE e.id IN $ids "
                "RETURN e.id AS id, e.jurisdiction AS jur",
                ids=ids,
            )
            jur_map = {r["id"]: r.get("jur") async for r in result}

        scores, unknown, restricted = [], 0, False
        for n in nbrs:
            score, is_unknown = get_jurisdiction_risk(jur_map.get(n))
            scores.append(score)
            if is_unknown:
                unknown += 1
            if score >= 0.85:
                restricted = True

        if unknown:
            logger.info("JURISDICTION_UNKNOWN",
                        extra={"entity_hash": entity_hash, "unknown": unknown})

        return statistics.mean(scores) if scores else self._DENSITY_FLOOR, int(restricted)

    # ------------------------------------------------------------------ #
    # Factor S — Sanctions Exposure (betweenness proxy)
    # ------------------------------------------------------------------ #

    def _compute_S(self, betweenness: dict[str, float], target: str) -> float:
        return betweenness.get(target, self._DENSITY_FLOOR)

    # ------------------------------------------------------------------ #
    # Factor A — AML Topology Risk
    # (Old NRS formula, now one factor among six)
    # ------------------------------------------------------------------ #

    def _compute_A(
        self,
        target: str,
        pagerank: dict[str, float],
        betweenness: dict[str, float],
        community_risk: dict[str, float],
    ) -> float:
        return min(1.0, max(0.0,
            0.4 * pagerank.get(target, 0.0)
            + 0.35 * betweenness.get(target, 0.0)
            + 0.25 * community_risk.get(target, 0.0)
        ))

    # ------------------------------------------------------------------ #
    # Factor B — Behavioural Risk (STUB)
    # Z-score of recent vs trailing transaction volume.
    # ------------------------------------------------------------------ #

    def _compute_B(self, G: nx.DiGraph, target: str) -> float:
        now = int(time.time())
        week_ago, month_ago = now - 7 * 86400, now - 30 * 86400
        recent, trailing = [], []
        for u, v, data in list(G.out_edges(target, data=True)) + list(G.in_edges(target, data=True)):
            ts = data.get("timestamp", 0)
            amt = data.get("amount", 0.0)
            if ts >= week_ago:
                recent.append(amt)
            elif ts >= month_ago:
                trailing.append(amt)
        if len(trailing) < 2:
            return self._DENSITY_FLOOR
        mean_t = statistics.mean(trailing)
        std_t = statistics.stdev(trailing)
        if std_t == 0:
            return self._DENSITY_FLOOR
        z = abs((statistics.mean(recent) if recent else mean_t) - mean_t) / std_t
        return min(1.0, z / 3.0)

    def compute_manifold_score(self, B: float) -> float:
        """STUB: inverse of B. Replace with Node2Vec cosine distance (US-01.5.2)."""
        return round(1.0 - B, 6)

    # ------------------------------------------------------------------ #
    # Anomaly flag
    # ------------------------------------------------------------------ #

    async def _has_anomaly(self, entity_hash: str) -> bool:
        async with self.entity_service.driver.session() as session:
            result = await session.run(
                "MATCH (e:Entity {id: $id}) RETURN e.anomaly_type AS t",
                id=entity_hash,
            )
            record = await result.single()
            return bool(record and record.get("t"))

    # ------------------------------------------------------------------ #
    # Main computation
    # ------------------------------------------------------------------ #

    async def compute_compliance_index(self, entity_id: str) -> ComplianceIndexResult:
        target_hash = self.entity_service.hash_entity_id(entity_id)
        subgraph = await self.entity_service.export_subgraph(entity_id, hops=3)
        G = self._build_graph(subgraph)

        pagerank, floor_applied = self._compute_pagerank(G, target=target_hash)
        betweenness = self._compute_betweenness(G)
        communities = self._compute_communities(G)
        community_risk = self._compute_community_risk(G, pagerank, communities)

        L = self._compute_L(G, target_hash)
        C = self._compute_C(G, target_hash, pagerank)
        J, jurisdiction_flag = await self._compute_J(G, target_hash, target_hash)
        S = self._compute_S(betweenness, target_hash)
        A = self._compute_A(target_hash, pagerank, betweenness, community_risk)
        B = self._compute_B(G, target_hash)

        anomaly_applied = False
        if await self._has_anomaly(target_hash):
            A = min(1.0, A + self._ANOMALY_PENALTY)
            anomaly_applied = True

        factors = {k: min(1.0, max(0.0, v)) for k, v in
                   {"L": L, "C": C, "J": J, "S": S, "A": A, "B": B}.items()}
        w = self._weights
        ci = sum(w[k] * factors[k] for k in w)
        ci = min(1.0, max(0.0, ci))

        manifold = self.compute_manifold_score(factors["B"])

        # Persist community partition used for A factor (deterministic seed)
        for i, comm in enumerate(communities):
            for node_hash in comm:
                try:
                    await self.entity_service.set_community_id_by_hash(node_hash, i)
                except Exception:
                    logger.warning("community_id persist failed",
                                   extra={"node_hash": node_hash}, exc_info=True)

        logger.info("ci_computed", extra={
            "entity_hash": target_hash,
            "ci": round(ci, 6),
            "jurisdiction_flag": jurisdiction_flag,
        })

        return ComplianceIndexResult(
            compliance_index=round(ci, 6),
            factor_breakdown=FactorBreakdown(
                L=round(factors["L"], 6), C=round(factors["C"], 6),
                J=round(factors["J"], 6), S=round(factors["S"], 6),
                A=round(factors["A"], 6), B=round(factors["B"], 6),
                B_is_stub=True,
            ),
            manifold_score=manifold,
            jurisdiction_flag=jurisdiction_flag,
            weights_used=dict(w),
            density_floor_applied=floor_applied,
            anomaly_penalty_applied=anomaly_applied,
        )

    def compute_compliance_index_sync(
        self, entity_id: str, subgraph: dict | None = None
    ) -> ComplianceIndexResult:
        """Offline/test variant — no Neo4j, no anomaly check, J defaults to 0.5."""
        if subgraph is None:
            subgraph = {"nodes": [{"id": entity_id}], "edges": []}
        G = self._build_graph(subgraph)
        pagerank, floor_applied = self._compute_pagerank(G, target=entity_id)
        betweenness = self._compute_betweenness(G)
        communities = self._compute_communities(G)
        community_risk = self._compute_community_risk(G, pagerank, communities)

        factors = {
            "L": self._compute_L(G, entity_id),
            "C": self._compute_C(G, entity_id, pagerank),
            "J": 0.5,
            "S": self._compute_S(betweenness, entity_id),
            "A": self._compute_A(entity_id, pagerank, betweenness, community_risk),
            "B": self._compute_B(G, entity_id),
        }
        factors = {k: min(1.0, max(0.0, v)) for k, v in factors.items()}
        w = self._weights
        ci = min(1.0, max(0.0, sum(w[k] * factors[k] for k in w)))

        return ComplianceIndexResult(
            compliance_index=round(ci, 6),
            factor_breakdown=FactorBreakdown(
                **{k: round(v, 6) for k, v in factors.items()}, B_is_stub=True
            ),
            manifold_score=self.compute_manifold_score(factors["B"]),
            jurisdiction_flag=0,
            weights_used=dict(w),
            density_floor_applied=floor_applied,
        )


# --------------------------------------------------------------------------- #
# Backward-compatibility shim — migrate callers to CIEngine
# --------------------------------------------------------------------------- #

class NRSEngine:
    """Deprecated — wraps CIEngine to avoid breaking existing callers.
    raw_nrs == compliance_index. Remove once agent/api layers are updated."""

    def __init__(self, entity_service: EntityService | None = None, settings: Settings | None = None):
        self._ci = CIEngine(entity_service=entity_service, settings=settings)

    @property
    def entity_service(self) -> EntityService:
        return self._ci.entity_service

    async def compute_nrs(self, entity_id: str) -> NRSDetails:
        r = await self._ci.compute_compliance_index(entity_id)
        f = r.factor_breakdown
        return NRSDetails(pagerank_score=f.C, betweenness_score=f.S,
                          community_risk_score=f.A, raw_nrs=r.compliance_index,
                          density_floor_applied=r.density_floor_applied,
                          anomaly_penalty_applied=r.anomaly_penalty_applied)

    def compute_nrs_sync(self, entity_id: str | None = None, subgraph: dict | None = None) -> NRSDetails:
        r = self._ci.compute_compliance_index_sync(entity_id or "", subgraph)
        f = r.factor_breakdown
        return NRSDetails(pagerank_score=f.C, betweenness_score=f.S,
                          community_risk_score=f.A, raw_nrs=r.compliance_index,
                          density_floor_applied=r.density_floor_applied)


# --------------------------------------------------------------------------- #
# Incident detection (US-01.3.1, US-01.3.2)
# --------------------------------------------------------------------------- #

class IncidentRepository(Protocol):
    async def create_incident(self, entity_hash: str, ci: float, threshold: float, status: str) -> str: ...
    async def update_incident_status(self, incident_id: str, status: str) -> None: ...


class IncidentService:
    _RETRY_DELAYS = (1, 2, 4)

    def __init__(
        self,
        entity_service: EntityService | None = None,
        repository: IncidentRepository | None = None,
        http_client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
    ):
        self.entity_service = entity_service
        self.repository = repository
        self._http_client = http_client
        self.settings = settings or get_settings()

    async def check_threshold_incident(self, entity_hash: str, ci: float) -> dict[str, Any] | None:
        threshold = self.settings.high_risk_nrs_threshold
        if ci < threshold:
            return None
        incident_id = None
        if self.repository is not None:
            incident_id = await self.repository.create_incident(
                entity_hash=entity_hash, ci=ci, threshold=threshold, status="PENDING_REVIEW"
            )
        else:
            logger.error("IncidentRepository not configured — NOT persisted",
                         extra={"entity_hash": entity_hash, "ci": ci})
        webhook_status = await self._dispatch_webhook(entity_hash, ci, threshold)
        final = "ALERT_FAILED" if webhook_status == "ALERT_FAILED" else "PENDING_REVIEW"
        if incident_id and self.repository and final == "ALERT_FAILED":
            await self.repository.update_incident_status(incident_id, "ALERT_FAILED")
        return {"incident_id": incident_id, "entity_hash": entity_hash,
                "ci": ci, "threshold": threshold, "status": final,
                "webhook_status": webhook_status}

    async def _dispatch_webhook(self, entity_hash: str, ci: float, threshold: float) -> str:
        url = getattr(self.settings, "alert_webhook_url", None)
        if not url:
            return "SKIPPED"
        payload = {"entity_hash": entity_hash, "ci": ci,
                   "threshold": threshold, "status": "PENDING_REVIEW"}
        client = self._http_client or httpx.AsyncClient(timeout=10.0)
        owns = self._http_client is None
        try:
            for attempt, delay in enumerate((0, *self._RETRY_DELAYS)):
                if delay:
                    await asyncio.sleep(delay)
                try:
                    r = await client.post(url, json=payload)
                    if r.status_code < 300:
                        return "DELIVERED"
                    logger.warning("webhook non-2xx",
                                   extra={"attempt": attempt, "status": r.status_code})
                except httpx.HTTPError as exc:
                    logger.warning("webhook failed",
                                   extra={"attempt": attempt, "error": str(exc)})
            logger.error("webhook exhausted retries", extra={"entity_hash": entity_hash})
            return "ALERT_FAILED"
        finally:
            if owns:
                await client.aclose()

    async def detect_anomalies(
        self, window_hours: int = 24, fan_out_threshold: int = 20
    ) -> list[dict[str, Any]]:
        if self.entity_service is None:
            raise IncidentServiceError("entity_service required")
        since = int(time.time()) - window_hours * 3600
        cypher = """
        MATCH (s:Entity)-[r:TRANSACTED_WITH]->(t:Entity)
        WHERE r.timestamp >= $since
        WITH s, count(DISTINCT t) AS fan_out
        WHERE fan_out > $threshold
        SET s.anomaly_type = 'STRUCTURAL_ANOMALY'
        RETURN s.id AS entity_hash, fan_out
        """
        async with self.entity_service.driver.session() as session:
            result = await session.run(cypher, since=since, threshold=fan_out_threshold)
            anomalies = [dict(r) async for r in result]
        for a in anomalies:
            logger.info("structural_anomaly_flagged", extra=a)
        return anomalies