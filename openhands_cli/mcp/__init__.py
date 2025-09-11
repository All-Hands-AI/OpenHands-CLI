"""MCP (Model Context Protocol) integration module."""

from .session_manager import MCPSessionManager

# Global session manager instance
mcp_session = MCPSessionManager()

__all__ = ["mcp_session", "MCPSessionManager"]
