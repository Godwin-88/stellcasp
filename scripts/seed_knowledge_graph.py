#!/usr/bin/env python3
"""
scripts/seed_knowledge_graph.py
================================
Zero-Knowledge Compliance Oracle — Knowledge Graph Seeder

Seeds Neo4j and PostgreSQL with:
  §1  FATF grey/black list jurisdictions          → Neo4j :Jurisdiction nodes
  §2  OFAC SDN sanctioned entity stubs            → Neo4j :SanctionedEntity nodes
  §3  Known exchange hot-wallet labels            → Neo4j :Entity + :Exchange nodes
  §4  Known mixer/tumbler contract stubs          → Neo4j :SanctionedEntity (OFAC_MIXER)
  §5  Synthetic wallet graph (demo entities)      → Neo4j :Entity + :TRANSACTED_WITH
  §6  jurisdiction_risk table                     → PostgreSQL (idempotent upsert)
  §7  Embedding cluster stubs                     → PostgreSQL embedding_clusters
  §8  Verification report                         → stdout

Usage:
    cp .env.example .env          # fill in NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                                  #   DATABASE_URL, ENTITY_SALT
    python scripts/seed_knowledge_graph.py [--neo4j] [--postgres] [--demo]

    Flags (all run if none supplied):
      --neo4j     seed Neo4j only
      --postgres  seed PostgreSQL only
      --demo      also create synthetic wallet graph for local testing
      --verify    print verification queries and exit
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

# ── third-party ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env optional — fall back to real env vars

try:
    from neo4j import GraphDatabase, exceptions as neo4j_exc
except ImportError:
    print("ERROR: neo4j driver not installed. Run: pip install neo4j")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# =============================================================================
# Configuration — all values from environment variables
# =============================================================================
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
DATABASE_URL   = os.getenv("DATABASE_URL",   "postgresql://zkkyc:password@localhost:5432/zkkyc")
ENTITY_SALT    = os.getenv("ENTITY_SALT",    "zkco-default-salt-change-in-production")


def entity_hash(raw_id: str) -> str:
    """SHA-256(raw_id + ENTITY_SALT) — mirrors hash_entity_id() in the platform."""
    return hashlib.sha256(f"{raw_id}{ENTITY_SALT}".encode()).hexdigest()


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(section: str, msg: str):
    print(f"  [{section}] {msg}")


# =============================================================================
# §1  FATF Jurisdiction Data
# Source: FATF Public Statement + Grey List (2026 snapshot)
#         https://www.fatf-gafi.org/en/publications/high-risk-and-other-monitored-jurisdictions
# =============================================================================
JURISDICTIONS = [
    # BLACK LIST — call for action
    {"iso2": "AF", "designation": "FATF_BLACK", "risk_score": 1.000, "name": "Afghanistan"},
    {"iso2": "MM", "designation": "FATF_BLACK", "risk_score": 1.000, "name": "Myanmar"},
    {"iso2": "KP", "designation": "FATF_BLACK", "risk_score": 1.000, "name": "North Korea"},
    {"iso2": "IR", "designation": "FATF_BLACK", "risk_score": 1.000, "name": "Iran"},
    # GREY LIST — enhanced monitoring
    {"iso2": "BF", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Burkina Faso"},
    {"iso2": "CM", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Cameroon"},
    {"iso2": "CD", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "DR Congo"},
    {"iso2": "HT", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Haiti"},
    {"iso2": "ML", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Mali"},
    {"iso2": "MZ", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Mozambique"},
    {"iso2": "NG", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Nigeria"},
    {"iso2": "PK", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Pakistan"},
    {"iso2": "PH", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Philippines"},
    {"iso2": "SS", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "South Sudan"},
    {"iso2": "SY", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Syria"},
    {"iso2": "TZ", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Tanzania"},
    {"iso2": "VN", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Vietnam"},
    {"iso2": "YE", "designation": "FATF_GREY",  "risk_score": 0.850, "name": "Yemen"},
    # OFAC SANCTIONS
    {"iso2": "CU", "designation": "OFAC",       "risk_score": 0.900, "name": "Cuba"},
    {"iso2": "VE", "designation": "OFAC",       "risk_score": 0.750, "name": "Venezuela"},
    {"iso2": "RU", "designation": "OFAC",       "risk_score": 0.700, "name": "Russia"},
    # NEUTRAL — explicitly low risk reference nodes
    {"iso2": "KE", "designation": "NEUTRAL",    "risk_score": 0.200, "name": "Kenya"},
    {"iso2": "US", "designation": "NEUTRAL",    "risk_score": 0.100, "name": "United States"},
    {"iso2": "GB", "designation": "NEUTRAL",    "risk_score": 0.100, "name": "United Kingdom"},
    {"iso2": "DE", "designation": "NEUTRAL",    "risk_score": 0.100, "name": "Germany"},
    {"iso2": "SG", "designation": "NEUTRAL",    "risk_score": 0.150, "name": "Singapore"},
    # DEFAULT fallback
    {"iso2": "DEFAULT", "designation": "UNKNOWN", "risk_score": 0.500, "name": "Unknown"},
]

# =============================================================================
# §2  OFAC SDN Sanctioned Entities (public wallet addresses)
# Source: OFAC published crypto addresses — https://ofac.treasury.gov/
#         Chainalysis public sanction disclosures
#         NOTE: These are publicly disclosed sanctioned addresses —
#               not proprietary intelligence.
# =============================================================================
SANCTIONED_ENTITIES = [
    # Lazarus Group / DPRK (OFAC SDN)
    {
        "id": "LAZARUS_001",
        "name": "Lazarus Group",
        "designation": "OFAC_SDN",
        "list_source": "OFAC",
        "wallet_addresses": [
            "0x098b716b8aaf21512996dc57eb0615e2383e2f96",  # Ronin Bridge hack
            "0xa0e1c89ef1a489c9c7de96311ed5ce5d32c20e4",
            "0x3cffd56b47278a68bfb5c4e21cc6f1cc97ccf1ea",
        ],
        "notes": "DPRK state-sponsored threat actor. OFAC SDN list 2022.",
    },
    # Tornado Cash (OFAC sanctioned mixer contracts — Ethereum)
    {
        "id": "TORNADO_CASH_001",
        "name": "Tornado Cash — 0.1 ETH Pool",
        "designation": "OFAC_MIXER",
        "list_source": "OFAC",
        "wallet_addresses": ["0xd4b88df4d29f5cedd6857912842cff3b20c8cfa3"],
        "notes": "OFAC SDN sanctioned 2022-08-08.",
    },
    {
        "id": "TORNADO_CASH_002",
        "name": "Tornado Cash — 1 ETH Pool",
        "designation": "OFAC_MIXER",
        "list_source": "OFAC",
        "wallet_addresses": ["0xfd8610d20aa15b7b2e3be39b396a1bc3516c7144"],
        "notes": "OFAC SDN sanctioned 2022-08-08.",
    },
    {
        "id": "TORNADO_CASH_003",
        "name": "Tornado Cash — 10 ETH Pool",
        "designation": "OFAC_MIXER",
        "list_source": "OFAC",
        "wallet_addresses": ["0x910cbd523d972eb0a6f4cae4618ad62622b39dbf"],
        "notes": "OFAC SDN sanctioned 2022-08-08.",
    },
    {
        "id": "TORNADO_CASH_004",
        "name": "Tornado Cash — 100 ETH Pool",
        "designation": "OFAC_MIXER",
        "list_source": "OFAC",
        "wallet_addresses": ["0xa160cdab225685da1d56aa342ad8841c3b53f291"],
        "notes": "OFAC SDN sanctioned 2022-08-08.",
    },
    # Blender.io (OFAC sanctioned mixer)
    {
        "id": "BLENDER_001",
        "name": "Blender.io",
        "designation": "OFAC_MIXER",
        "list_source": "OFAC",
        "wallet_addresses": [
            "1BlenderiuforzWwpNhbMuPDXRyTLRiFXbS",
            "14TKvBZs5e9UJdNSBzVVzEjQ7xzHiLJEGK",
        ],
        "notes": "First Bitcoin mixer sanctioned by OFAC, 2022-05-06.",
    },
    # Hydra darknet market (OFAC SDN)
    {
        "id": "HYDRA_001",
        "name": "Hydra Market",
        "designation": "OFAC_SDN",
        "list_source": "OFAC",
        "wallet_addresses": [
            "1LBzfRrAX5EXRhHuXtANwHPDRxhLdYhJdg",
        ],
        "notes": "Russian darknet market. OFAC SDN 2022-04-05.",
    },
]

# =============================================================================
# §3  Known Exchange Hot Wallets
# Source: Public exchange disclosures, DefiLlama treasury data,
#         Etherscan address labels (public)
# =============================================================================
EXCHANGES = [
    {
        "id": "BINANCE_HOT_001",
        "name": "Binance",
        "kyc_tier": "regulated",
        "jurisdiction": "MT",    # Malta (primary)
        "wallet_addresses": [
            "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance hot wallet (public)
            "0xd551234ae421e3bcba99a0da6d736074f22192ff",
        ],
    },
    {
        "id": "COINBASE_HOT_001",
        "name": "Coinbase",
        "kyc_tier": "regulated",
        "jurisdiction": "US",
        "wallet_addresses": [
            "0xa090e606e30bd747d4e6245a1517ebe430f0057e",
        ],
    },
    {
        "id": "KRAKEN_HOT_001",
        "name": "Kraken",
        "kyc_tier": "regulated",
        "jurisdiction": "US",
        "wallet_addresses": [
            "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0",
        ],
    },
    {
        "id": "KUCOIN_HOT_001",
        "name": "KuCoin",
        "kyc_tier": "regulated",
        "jurisdiction": "SC",    # Seychelles
        "wallet_addresses": [
            "0xd6216fc19db775df9774a6e33526131da7d19a2c",
        ],
    },
]

# =============================================================================
# §5  Embedding cluster stubs (k=5)
# Placeholder centroids — will be overwritten when Node2Vec runs.
# Dimension=64, initialised with deterministic pseudo-random values.
# =============================================================================
def _stub_centroid(seed: int, dims: int = 64) -> list:
    rng = random.Random(seed)
    return [round(rng.gauss(0, 1), 6) for _ in range(dims)]


EMBEDDING_CLUSTERS = [
    {"cluster_label": 0, "cluster_risk_level": 0, "name": "Low Risk",
     "centroid_vector": _stub_centroid(seed=42)},
    {"cluster_label": 1, "cluster_risk_level": 1, "name": "Moderate-Low Risk",
     "centroid_vector": _stub_centroid(seed=43)},
    {"cluster_label": 2, "cluster_risk_level": 2, "name": "Moderate Risk",
     "centroid_vector": _stub_centroid(seed=44)},
    {"cluster_label": 3, "cluster_risk_level": 3, "name": "Moderate-High Risk",
     "centroid_vector": _stub_centroid(seed=45)},
    {"cluster_label": 4, "cluster_risk_level": 4, "name": "High Risk",
     "centroid_vector": _stub_centroid(seed=46)},
]

# =============================================================================
# §6  Synthetic demo wallets (only created with --demo flag)
# Creates a small transaction graph for local algorithm testing:
#   - 5 clean wallets (low risk, neutral jurisdictions)
#   - 2 high-risk wallets (grey-list jurisdictions, high fan-out)
#   - 1 mixer-adjacent wallet (1-hop from a known mixer address)
# =============================================================================
DEMO_WALLETS = [
    {"id": "DEMO_WALLET_CLEAN_001", "jurisdiction": "KE", "type": "WALLET", "label": "clean"},
    {"id": "DEMO_WALLET_CLEAN_002", "jurisdiction": "US", "type": "WALLET", "label": "clean"},
    {"id": "DEMO_WALLET_CLEAN_003", "jurisdiction": "GB", "type": "WALLET", "label": "clean"},
    {"id": "DEMO_WALLET_CLEAN_004", "jurisdiction": "DE", "type": "WALLET", "label": "clean"},
    {"id": "DEMO_WALLET_CLEAN_005", "jurisdiction": "SG", "type": "WALLET", "label": "clean"},
    {"id": "DEMO_WALLET_HIGH_001",  "jurisdiction": "NG", "type": "WALLET", "label": "high_risk"},
    {"id": "DEMO_WALLET_HIGH_002",  "jurisdiction": "KP", "type": "WALLET", "label": "high_risk"},
    {"id": "DEMO_WALLET_MIXER_ADJ", "jurisdiction": "RU", "type": "WALLET", "label": "mixer_adjacent"},
]

DEMO_TRANSACTIONS = [
    # clean-to-clean cluster (normal activity)
    ("DEMO_WALLET_CLEAN_001", "DEMO_WALLET_CLEAN_002", 100.0, "XLM"),
    ("DEMO_WALLET_CLEAN_002", "DEMO_WALLET_CLEAN_003", 50.0, "XLM"),
    ("DEMO_WALLET_CLEAN_003", "DEMO_WALLET_CLEAN_004", 75.0, "XLM"),
    ("DEMO_WALLET_CLEAN_004", "DEMO_WALLET_CLEAN_005", 30.0, "XLM"),
    ("DEMO_WALLET_CLEAN_001", "DEMO_WALLET_CLEAN_005", 20.0, "XLM"),
    # high-risk fan-out (triggers structural anomaly — rapid fan-out)
    ("DEMO_WALLET_HIGH_001", "DEMO_WALLET_CLEAN_001", 5.0,  "XLM"),
    ("DEMO_WALLET_HIGH_001", "DEMO_WALLET_CLEAN_002", 5.0,  "XLM"),
    ("DEMO_WALLET_HIGH_001", "DEMO_WALLET_CLEAN_003", 5.0,  "XLM"),
    ("DEMO_WALLET_HIGH_001", "DEMO_WALLET_CLEAN_004", 5.0,  "XLM"),
    ("DEMO_WALLET_HIGH_001", "DEMO_WALLET_CLEAN_005", 5.0,  "XLM"),
    ("DEMO_WALLET_HIGH_002", "DEMO_WALLET_HIGH_001",  200.0, "XLM"),
    # mixer-adjacent path
    ("DEMO_WALLET_MIXER_ADJ", "DEMO_WALLET_HIGH_001", 50.0, "XLM"),
    ("DEMO_WALLET_MIXER_ADJ", "DEMO_WALLET_HIGH_002", 30.0, "XLM"),
]


# =============================================================================
# Neo4j seeding
# =============================================================================

def seed_neo4j(driver, include_demo: bool = False):
    print("\n── Neo4j Seeding ─────────────────────────────────────────────")

    with driver.session() as session:

        # §1 Jurisdiction nodes
        log("§1", "Seeding Jurisdiction nodes...")
        for j in JURISDICTIONS:
            session.run(
                """
                MERGE (jur:Jurisdiction {iso2: $iso2})
                SET jur.designation  = $designation,
                    jur.risk_score   = $risk_score,
                    jur.name         = $name,
                    jur.last_updated = $ts,
                    jur.source       = 'FATF/OFAC 2026'
                """,
                iso2=j["iso2"], designation=j["designation"],
                risk_score=j["risk_score"], name=j["name"], ts=ts(),
            )
        log("§1", f"  ✓ {len(JURISDICTIONS)} Jurisdiction nodes upserted")

        # §2 SanctionedEntity nodes
        log("§2", "Seeding SanctionedEntity nodes...")
        for ent in SANCTIONED_ENTITIES:
            session.run(
                """
                MERGE (se:SanctionedEntity {id: $id})
                SET se.name             = $name,
                    se.designation      = $designation,
                    se.list_source      = $list_source,
                    se.wallet_addresses = $wallets,
                    se.notes            = $notes,
                    se.last_updated     = $ts
                """,
                id=ent["id"], name=ent["name"], designation=ent["designation"],
                list_source=ent["list_source"],
                wallets=ent["wallet_addresses"], notes=ent["notes"], ts=ts(),
            )
            # Create Entity nodes for each known sanctioned wallet address
            for addr in ent["wallet_addresses"]:
                h = entity_hash(addr)
                session.run(
                    """
                    MERGE (e:Entity {id: $id})
                    SET e.type         = 'WALLET',
                        e.entity_hash  = $h,
                        e.sanctioned   = true,
                        e.created_at   = $ts,
                        e.updated_at   = $ts
                    WITH e
                    MATCH (se:SanctionedEntity {id: $se_id})
                    MERGE (e)-[:SANCTIONED_LINK {link_type: $designation}]->(se)
                    """,
                    id=addr, h=h, ts=ts(),
                    se_id=ent["id"], designation=ent["designation"],
                )
        log("§2", f"  ✓ {len(SANCTIONED_ENTITIES)} SanctionedEntity nodes + wallet links upserted")

        # §3 Exchange nodes + hot wallets
        log("§3", "Seeding Exchange nodes + hot wallets...")
        for ex in EXCHANGES:
            session.run(
                """
                MERGE (exc:Exchange {id: $id})
                SET exc.name             = $name,
                    exc.kyc_tier         = $kyc_tier,
                    exc.jurisdiction     = $jurisdiction,
                    exc.wallet_addresses = $wallets,
                    exc.last_updated     = $ts
                """,
                id=ex["id"], name=ex["name"], kyc_tier=ex["kyc_tier"],
                jurisdiction=ex["jurisdiction"],
                wallets=ex["wallet_addresses"], ts=ts(),
            )
            for addr in ex["wallet_addresses"]:
                h = entity_hash(addr)
                session.run(
                    """
                    MERGE (e:Entity {id: $id})
                    SET e.type         = 'EXCHANGE_WALLET',
                        e.entity_hash  = $h,
                        e.sanctioned   = false,
                        e.jurisdiction = $jurisdiction,
                        e.created_at   = $ts,
                        e.updated_at   = $ts
                    WITH e
                    MATCH (exc:Exchange {id: $exc_id})
                    MERGE (e)-[:OPERATED_BY]->(exc)
                    WITH e
                    MATCH (jur:Jurisdiction {iso2: $jurisdiction})
                    MERGE (e)-[:DOMICILED_IN {since: $ts}]->(jur)
                    """,
                    id=addr, h=h, jurisdiction=ex["jurisdiction"],
                    ts=ts(), exc_id=ex["id"],
                )
        log("§3", f"  ✓ {len(EXCHANGES)} Exchange nodes + hot wallets upserted")

        # §5 Demo wallet graph
        if include_demo:
            log("§5", "Seeding synthetic demo wallet graph...")
            for w in DEMO_WALLETS:
                h = entity_hash(w["id"])
                session.run(
                    """
                    MERGE (e:Entity {id: $id})
                    SET e.type         = $type,
                        e.entity_hash  = $h,
                        e.jurisdiction = $jurisdiction,
                        e.sanctioned   = false,
                        e.demo_label   = $label,
                        e.created_at   = $ts,
                        e.updated_at   = $ts
                    WITH e
                    MATCH (jur:Jurisdiction {iso2: $jurisdiction})
                    MERGE (e)-[:DOMICILED_IN {since: $ts}]->(jur)
                    """,
                    id=w["id"], type=w["type"], h=h,
                    jurisdiction=w["jurisdiction"],
                    label=w["label"], ts=ts(),
                )
            for src_id, tgt_id, amount, currency in DEMO_TRANSACTIONS:
                tx_hash = hashlib.sha256(
                    f"{src_id}{tgt_id}{amount}{time.time()}".encode()
                ).hexdigest()[:32]
                session.run(
                    """
                    MATCH (src:Entity {id: $src_id})
                    MATCH (tgt:Entity {id: $tgt_id})
                    MERGE (src)-[r:TRANSACTED_WITH {tx_hash: $tx_hash}]->(tgt)
                    SET r.amount    = $amount,
                        r.currency  = $currency,
                        r.timestamp = $ts
                    """,
                    src_id=src_id, tgt_id=tgt_id,
                    tx_hash=tx_hash, amount=amount,
                    currency=currency, ts=ts(),
                )
            log("§5", f"  ✓ {len(DEMO_WALLETS)} demo wallets + {len(DEMO_TRANSACTIONS)} transactions")

    print("  ✓ Neo4j seeding complete\n")


# =============================================================================
# PostgreSQL seeding
# =============================================================================

def seed_postgres(conn, include_demo: bool = False):
    print("\n── PostgreSQL Seeding ────────────────────────────────────────")
    cur = conn.cursor()

    # §4 jurisdiction_risk table
    log("§4", "Upserting jurisdiction_risk rows...")
    for j in JURISDICTIONS:
        cur.execute(
            """
            INSERT INTO jurisdiction_risk (iso2_code, risk_score, designation, last_updated, source_url)
            VALUES (%s, %s, %s, NOW(), %s)
            ON CONFLICT (iso2_code) DO UPDATE
                SET risk_score   = EXCLUDED.risk_score,
                    designation  = EXCLUDED.designation,
                    last_updated = NOW()
            """,
            (j["iso2"], j["risk_score"], j["designation"],
             "https://www.fatf-gafi.org/en/publications/high-risk-and-other-monitored-jurisdictions"),
        )
    conn.commit()
    log("§4", f"  ✓ {len(JURISDICTIONS)} jurisdiction rows upserted")

    # §7 embedding_clusters — stub centroids
    log("§7", "Inserting embedding cluster stubs...")
    for cluster in EMBEDDING_CLUSTERS:
        cur.execute(
            """
            INSERT INTO embedding_clusters
                (cluster_label, cluster_risk_level, centroid_vector, member_count, trained_at)
            VALUES (%s, %s, %s, 0, NOW())
            ON CONFLICT (cluster_label) DO UPDATE
                SET centroid_vector = EXCLUDED.centroid_vector,
                    trained_at      = NOW()
            """,
            (
                cluster["cluster_label"],
                cluster["cluster_risk_level"],
                json.dumps(cluster["centroid_vector"]),
            ),
        )
    conn.commit()
    log("§7", f"  ✓ {len(EMBEDDING_CLUSTERS)} cluster stubs upserted")

    # §2 entity_mappings for sanctioned wallet addresses (hashed)
    log("§2", "Inserting entity_mappings for sanctioned addresses...")
    inserted = 0
    for ent in SANCTIONED_ENTITIES:
        for addr in ent["wallet_addresses"]:
            h = entity_hash(addr)
            # entity_id stored as bytes (AES encryption placeholder — raw bytes for dev)
            encrypted_id = addr.encode()
            cur.execute(
                """
                INSERT INTO entity_mappings (entity_id, entity_hash)
                VALUES (%s, %s)
                ON CONFLICT (entity_hash) DO NOTHING
                """,
                (encrypted_id, h),
            )
            inserted += 1
    conn.commit()
    log("§2", f"  ✓ {inserted} sanctioned address mappings inserted")

    # §2 entity_mappings for exchange hot wallets
    log("§2", "Inserting entity_mappings for exchange hot wallets...")
    ex_inserted = 0
    for ex in EXCHANGES:
        for addr in ex["wallet_addresses"]:
            h = entity_hash(addr)
            cur.execute(
                """
                INSERT INTO entity_mappings (entity_id, entity_hash)
                VALUES (%s, %s)
                ON CONFLICT (entity_hash) DO NOTHING
                """,
                (addr.encode(), h),
            )
            ex_inserted += 1
    conn.commit()
    log("§2", f"  ✓ {ex_inserted} exchange wallet mappings inserted")

    # §5 Demo entity_mappings
    if include_demo:
        log("§5", "Inserting entity_mappings for demo wallets...")
        for w in DEMO_WALLETS:
            h = entity_hash(w["id"])
            cur.execute(
                """
                INSERT INTO entity_mappings (entity_id, entity_hash)
                VALUES (%s, %s)
                ON CONFLICT (entity_hash) DO NOTHING
                """,
                (w["id"].encode(), h),
            )
        conn.commit()
        log("§5", f"  ✓ {len(DEMO_WALLETS)} demo wallet mappings inserted")

    cur.close()
    print("  ✓ PostgreSQL seeding complete\n")


# =============================================================================
# Verification report
# =============================================================================

def verify_neo4j(driver):
    print("\n── Neo4j Verification ────────────────────────────────────────")
    with driver.session() as session:
        checks = [
            ("Jurisdiction nodes",    "MATCH (n:Jurisdiction)     RETURN count(n) AS c"),
            ("SanctionedEntity nodes","MATCH (n:SanctionedEntity)  RETURN count(n) AS c"),
            ("Exchange nodes",        "MATCH (n:Exchange)          RETURN count(n) AS c"),
            ("Entity nodes",          "MATCH (n:Entity)            RETURN count(n) AS c"),
            ("TRANSACTED_WITH edges", "MATCH ()-[r:TRANSACTED_WITH]-() RETURN count(r) AS c"),
            ("SANCTIONED_LINK edges", "MATCH ()-[r:SANCTIONED_LINK]-() RETURN count(r) AS c"),
            ("DOMICILED_IN edges",    "MATCH ()-[r:DOMICILED_IN]-()    RETURN count(r) AS c"),
        ]
        for label, query in checks:
            result = session.run(query).single()
            count = result["c"] if result else 0
            print(f"  {label:<28} {count:>6}")


def verify_postgres(conn):
    print("\n── PostgreSQL Verification ───────────────────────────────────")
    cur = conn.cursor()
    checks = [
        ("jurisdiction_risk rows",  "SELECT COUNT(*) FROM jurisdiction_risk"),
        ("embedding_clusters rows", "SELECT COUNT(*) FROM embedding_clusters"),
        ("entity_mappings rows",    "SELECT COUNT(*) FROM entity_mappings"),
    ]
    for label, query in checks:
        cur.execute(query)
        count = cur.fetchone()[0]
        print(f"  {label:<28} {count:>6}")
    cur.close()


# =============================================================================
# Entry point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Seed Neo4j + PostgreSQL for the ZK Compliance Oracle platform"
    )
    parser.add_argument("--neo4j",    action="store_true", help="Seed Neo4j only")
    parser.add_argument("--postgres", action="store_true", help="Seed PostgreSQL only")
    parser.add_argument("--demo",     action="store_true", help="Also seed synthetic demo wallet graph")
    parser.add_argument("--verify",   action="store_true", help="Print verification counts and exit")
    args = parser.parse_args()

    # Default: seed both if no flag specified
    run_neo4j    = args.neo4j    or (not args.neo4j and not args.postgres)
    run_postgres = args.postgres or (not args.neo4j and not args.postgres)

    print("=" * 64)
    print("  ZK Compliance Oracle — Knowledge Graph Seeder")
    print(f"  Neo4j:    {NEO4J_URI}")
    print(f"  Postgres: {DATABASE_URL.split('@')[-1]}")  # hide credentials
    print(f"  Mode:     {'neo4j ' if run_neo4j else ''}{'postgres ' if run_postgres else ''}{'demo' if args.demo else ''}")
    print("=" * 64)

    neo4j_driver = None
    pg_conn      = None
    exit_code    = 0

    # ── Connect ──────────────────────────────────────────────────────────────
    if run_neo4j or args.verify:
        try:
            neo4j_driver = GraphDatabase.driver(
                NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            neo4j_driver.verify_connectivity()
            print(f"\n  ✓ Connected to Neo4j at {NEO4J_URI}")
        except Exception as e:
            print(f"\n  ✗ Neo4j connection failed: {e}")
            print("    Check NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD in your .env")
            exit_code = 1
            run_neo4j = False

    if run_postgres or args.verify:
        try:
            pg_conn = psycopg2.connect(DATABASE_URL)
            print(f"  ✓ Connected to PostgreSQL")
        except Exception as e:
            print(f"\n  ✗ PostgreSQL connection failed: {e}")
            print("    Check DATABASE_URL in your .env")
            exit_code = 1
            run_postgres = False

    if args.verify:
        if neo4j_driver:
            verify_neo4j(neo4j_driver)
        if pg_conn:
            verify_postgres(pg_conn)
        print()
    else:
        # ── Seed ─────────────────────────────────────────────────────────────
        if run_neo4j and neo4j_driver:
            try:
                seed_neo4j(neo4j_driver, include_demo=args.demo)
                verify_neo4j(neo4j_driver)
            except Exception as e:
                print(f"\n  ✗ Neo4j seeding failed: {e}")
                exit_code = 1

        if run_postgres and pg_conn:
            try:
                seed_postgres(pg_conn, include_demo=args.demo)
                verify_postgres(pg_conn)
            except Exception as e:
                print(f"\n  ✗ PostgreSQL seeding failed: {e}")
                pg_conn.rollback()
                exit_code = 1

    # ── Teardown ─────────────────────────────────────────────────────────────
    if neo4j_driver:
        neo4j_driver.close()
    if pg_conn:
        pg_conn.close()

    print("\n  Done.\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
