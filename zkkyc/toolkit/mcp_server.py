"""
Casper MCP Server client — ZK-KYC Compliance Agent (zkkyc.toolkit.mcp_server)

Provides an MCP (Model Context Protocol) client that invokes structured
tools on a Casper MCP Server instance. The Settlement Agent routes all
Casper contract interactions through this interface rather than raw REST.

Spec reference: EP-06 augmentation (Casper MCP Server)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


class MCPToolError(Exception):
    def __init__(self, tool: str, message: str):
        self.tool = tool
        super().__init__(f"MCP tool '{tool}' failed: {message}")


class CasperMCPClient:
    """JSON-RPC 2.0 client for the Casper MCP Server.

    The Casper MCP Server exposes contract operations as `tools/call` invocations.
    This client wraps those calls with structured error handling and logging.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3001",
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.settings = settings or get_settings()
        self._client = http_client or httpx.Client(timeout=30.0)
        self._owns_client = http_client is None

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke an MCP tool and return the parsed result.

        Args:
            tool_name: Name of the MCP tool (e.g. ``record_verdict``).
            arguments: Tool-specific arguments dict.

        Returns:
            Parsed tool result from the MCP server.

        Raises:
            MCPToolError: if the tool call fails or returns an error.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
        }
        try:
            response = self._client.post(
                f"{self.base_url}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("MCP server unreachable for tool %s: %s", tool_name, exc)
            raise MCPToolError(tool_name, f"HTTP error: {exc}") from exc

        result = data.get("result", {})
        if "error" in result:
            err = result["error"]
            raise MCPToolError(tool_name, err.get("message", str(err)))

        content = result.get("content", [])
        if content and isinstance(content, list):
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            try:
                return json.loads("".join(text_parts))
            except json.JSONDecodeError:
                return {"raw": "".join(text_parts)}
        return result

    # ------------------------------------------------------------------
    # ComplianceOracle tools
    # ------------------------------------------------------------------

    def get_verdict(self, entity_hash: str) -> dict[str, Any]:
        return self.call_tool("get_verdict", {"entity_hash": entity_hash})

    def record_verdict(
        self,
        entity_hash: str,
        verdict: bool,
        expires_at: int,
        nrs_threshold: int = 750000,
    ) -> dict[str, Any]:
        return self.call_tool(
            "record_verdict",
            {
                "entity_hash": entity_hash,
                "verdict": verdict,
                "expires_at": expires_at,
                "nrs_threshold": nrs_threshold,
            },
        )

    def revoke_verdict(self, entity_hash: str, reason: str) -> dict[str, Any]:
        return self.call_tool("revoke_verdict", {"entity_hash": entity_hash, "reason": reason})

    # ------------------------------------------------------------------
    # IdentityRegistry tools
    # ------------------------------------------------------------------

    def register_identity(self, wallet: str, entity_hash: str) -> dict[str, Any]:
        return self.call_tool(
            "register_identity", {"wallet": wallet, "entity_hash": entity_hash}
        )

    def get_identity(self, wallet: str) -> dict[str, Any]:
        return self.call_tool("get_identity", {"wallet": wallet})

    def mint_compliance_token(self, wallet: str, entity_hash: str) -> dict[str, Any]:
        return self.call_tool(
            "mint_compliance_token", {"wallet": wallet, "entity_hash": entity_hash}
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        if self._owns_client:
            try:
                self._client.close()
            except Exception:
                pass

    def __enter__(self) -> CasperMCPClient:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
