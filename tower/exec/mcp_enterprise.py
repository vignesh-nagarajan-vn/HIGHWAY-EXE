"""MCP server that exposes the enterprise tools (proxying POST /act).

The agents reach the company systems only through this MCP server, so tool execution is MCP
in the literal sense. It can also run standalone over stdio for any MCP client:

    python -m tower.exec.mcp_enterprise
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ..vendor import TOOLS
from .client import EnterpriseHTTP


def tool_name(enterprise_tool: str) -> str:
    return enterprise_tool.replace(".", "_")


def build_server(http: EnterpriseHTTP | None = None) -> MCPServer:
    http = http or EnterpriseHTTP()
    server = MCPServer(name="wacky-wheels-enterprise",
                       instructions="Wacky Wheels Co. enterprise systems: MES, dealer portal, CRM, quality. "
                                    "Every call needs the event_id it is made for.")

    def register(name: str, spec: dict):
        arg_doc = ", ".join(f"{k}: {v}" for k, v in spec["args"].items())

        def call(event_id: str, args: dict) -> dict:
            return http.act(event_id, name, args)

        server.tool(name=tool_name(name),
                    description=f"{spec['desc']} args: {{{arg_doc}}}. "
                                f"{'Write' if spec['writes'] else 'Read-only'} tool.")(call)

    for name, spec in TOOLS.items():
        register(name, spec)
    return server


if __name__ == "__main__":
    build_server().run("stdio")
