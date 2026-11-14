"""MCP server exposing the founder tools.

Run standalone over stdio so any MCP client (Claude Desktop, an IDE, an
agent framework) can use it:

    python -m mcp_server.server

The backend also talks to this same server in-process through the MCP client,
so agents always call tools via the protocol."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from app.tools import registry


def build_server() -> MCPServer:
    server = MCPServer("venture-verse", instructions="Evidence, competitor, customer, lead and scenario tools for founders.")
    for fn in (
        registry.search_evidence,
        registry.competitors_search,
        registry.segments_discover,
        registry.leads_find,
        registry.scenario_simulate,
    ):
        server.add_tool(fn, name=fn.__name__, description=(fn.__doc__ or "").strip())
    return server


server = build_server()

if __name__ == "__main__":
    server.run("stdio")
