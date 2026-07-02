#!/usr/bin/env python3
"""
Neo4j schema migration runner — ZK-KYC Compliance Agent
scripts/run_neo4j_migrations.py

Reads all .cypher files from migrations/neo4j/ in sorted order and executes
them against the configured Neo4j instance. Idempotent — safe to re-run.

Usage:
    python scripts/run_neo4j_migrations.py

Environment:
    NEO4J_URI       — bolt://localhost:7687 (default)
    NEO4J_USER      — neo4j (default)
    NEO4J_PASSWORD  — password (default)
"""
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

from zkkyc.config import get_settings


def run_migrations():
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    migrations_dir = Path(__file__).parent.parent / "migrations" / "neo4j"
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        sys.exit(1)

    cypher_files = sorted(migrations_dir.glob("*.cypher"))
    if not cypher_files:
        print(f"⚠️  No .cypher files found in {migrations_dir}")
        sys.exit(0)

    print(f"🔧 Found {len(cypher_files)} Neo4j migration(s)")

    with driver.session() as session:
        for cypher_file in cypher_files:
            print(f"\n▶  Running {cypher_file.name}...")
            cypher_content = cypher_file.read_text()

            # Split on semicolons to execute each statement separately
            # (Neo4j doesn't support multi-statement transactions in one call)
            statements = [s.strip() for s in cypher_content.split(";") if s.strip()]

            for i, stmt in enumerate(statements, 1):
                # Skip comments and empty lines
                if stmt.startswith("//") or not stmt:
                    continue

                try:
                    session.run(stmt)
                    print(f"   ✓ Statement {i}/{len(statements)} executed")
                except Exception as e:
                    # Idempotent migrations may fail if constraint/index already exists
                    if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                        print(f"   ⚠  Statement {i} skipped (already exists)")
                    else:
                        print(f"   ❌ Statement {i} failed: {e}")
                        raise

    driver.close()
    print("\n✅ All Neo4j migrations completed successfully")


if __name__ == "__main__":
    run_migrations()