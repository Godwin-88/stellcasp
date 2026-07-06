"""
Mock Casper MCP Server for local development and hackathon demos.

Provides a minimal JSON-RPC 2.0 / MCP-compatible endpoint that the
CasperMCPClient can call during testing without a real Casper node.

Start with: uvicorn mcp_mock:app --host 0.0.0.0 --port 3001
"""

from __future__ import annotations

import json as _json
import logging
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Casper MCP Server")

_STATE: dict[str, Any] = {}


def json_dumps(obj):
    return _json.dumps(obj)


@app.get("/health")
async def health():
    return {"status": "ok", "mcp": "mock"}


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    body = await request.json()
    method = body.get("method", "")
    params = body.get("params", {})
    request_id = body.get("id", 1)

    if method == "tools/list":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {"name": "get_verdict", "description": "Query ComplianceOracle"},
                    {"name": "record_verdict", "description": "Record verdict"},
                    {"name": "revoke_verdict", "description": "Revoke verdict"},
                    {"name": "register_identity", "description": "Register identity"},
                    {"name": "mint_compliance_token", "description": "Mint token"},
                    {"name": "get_identity", "description": "Query identity"},
                ]
            },
        })

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "get_verdict":
            entity_hash = arguments.get("entity_hash", "")
            record = _STATE.get(entity_hash)
            if record:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json_dumps({
                            "verdict": record.get("verdict"),
                            "status": "VALID",
                            "expires_at": record.get("expires_at"),
                        })}],
                    },
                })
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json_dumps({
                        "verdict": None,
                        "status": "NOT_FOUND",
                        "expires_at": 0,
                    })}],
                },
            })

        if tool_name == "record_verdict":
            entity_hash = arguments.get("entity_hash", "")
            _STATE[entity_hash] = {
                "verdict": arguments.get("verdict", True),
                "expires_at": arguments.get("expires_at", 0),
                "recorded_at": int(time.time()),
            }
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json_dumps({
                        "deploy_hash": f"mock_deploy_{hash(entity_hash) % 10**16:016x}",
                        "status": "SUCCESS",
                    })}],
                },
            })

        if tool_name == "mint_compliance_token":
            wallet = arguments.get("wallet", "")
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json_dumps({
                        "deploy_hash": f"mock_mint_{hash(wallet) % 10**16:016x}",
                        "status": "SUCCESS",
                    })}],
                },
            })

        if tool_name == "get_identity":
            wallet = arguments.get("wallet", "")
            key = f"identity_{wallet}"
            record = _STATE.get(key)
            if record:
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json_dumps(record)}],
                    },
                })
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json_dumps(None)}],
                },
            })

        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
        })

    return JSONResponse(content={
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    })
