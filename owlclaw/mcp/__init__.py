"""MCP server integration for OwlClaw."""

from owlclaw.mcp.governance_tools import register_governance_mcp_tools
from owlclaw.mcp.server import McpProtocolServer

__all__ = ["McpProtocolServer", "register_governance_mcp_tools"]
