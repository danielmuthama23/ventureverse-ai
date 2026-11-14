"""Agents never import tools directly: every call is a real MCP `tools/call`
made through the MCP client against the venture-verse MCP server."""
from __future__ import annotations

import json
from typing import Any

from mcp.client import Client

from mcp_server.server import server


class ToolError(RuntimeError):
    pass


async def call_tool(name: str, args: dict[str, Any]) -> Any:
    async with Client(server) as client:
        res = await client.call_tool(name, args)
    if res.is_error:
        text = res.content[0].text if res.content else "tool failed"
        raise ToolError(f"{name}: {text}")
    sc = getattr(res, "structured_content", None)
    if sc is not None:
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(res.content[0].text)
