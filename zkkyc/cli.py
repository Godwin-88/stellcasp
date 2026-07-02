import json
import sys
import time

from .agents.graph import compliance_graph
from .config import get_settings


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ZK-KYC Compliance Agent CLI")
    parser.add_argument("--entity-id", required=True, help="Entity identifier")
    parser.add_argument("--chain", choices=["stellar", "casper"], default="stellar", help="Target chain")
    parser.add_argument("--prove", action="store_true", help="Generate ZK proof after compliance check")
    args = parser.parse_args()

    settings = get_settings()
    start_time = time.time()

    state = {
        "entity_id": args.entity_id,
        "nrs": 0.0,
        "nrs_details": {},
        "compliance_decision": "",
        "decision_rationale": "",
        "proof_hex": "",
        "chain_target": args.chain,
        "on_chain_tx_hash": "",
        "errors": [],
        "step_log": [],
    }

    graph = compliance_graph.compile()
    result = graph.invoke(state)

    elapsed = time.time() - start_time
    exit_code = 0 if result.get("compliance_decision") == "PASS" else 1

    print(json.dumps({
        "entity_id": args.entity_id,
        "nrs": result.get("nrs"),
        "compliance_decision": result.get("compliance_decision"),
        "chain_target": result.get("chain_target"),
        "on_chain_tx_hash": result.get("on_chain_tx_hash"),
        "total_elapsed_seconds": round(elapsed, 3),
    }))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()