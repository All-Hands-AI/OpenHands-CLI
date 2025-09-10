"""MCP Session Manager for in-memory server configuration management."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPSessionManager:
    """Manages MCP server configurations in memory during the CLI session."""

    def __init__(self) -> None:
        """Initialize the session manager with empty server storage."""
        self.servers: dict[str, dict[str, Any]] = {}

    def add_server(
        self,
        name: str,
        command: str,
        args: list | None = None,
        env: dict[str, str] | None = None,
    ) -> bool:
        """
        Add an MCP server configuration.

        Args:
            name: Unique server name
            command: Command to run the server
            args: Optional command arguments
            env: Optional environment variables

        Returns:
            True if server was added successfully, False if name already exists
        """
        if name in self.servers:
            logger.warning(f"MCP server '{name}' already exists")
            return False

        server_config = {"command": command, "args": args or [], "env": env or {}}

        self.servers[name] = server_config
        logger.info(f"Added MCP server '{name}' with command '{command}'")
        return True

    def get_server(self, name: str) -> dict[str, Any] | None:
        """Get server configuration by name."""
        return self.servers.get(name)

    def list_servers(self) -> dict[str, dict[str, Any]]:
        """Get all configured servers."""
        return self.servers.copy()

    def get_config(self) -> dict[str, Any]:
        """
        Get FastMCP-compatible configuration format.

        Returns:
            Configuration dict in the format expected by create_mcp_tools()
        """
        if not self.servers:
            return {}

        return {"mcpServers": self.servers}

    def has_servers(self) -> bool:
        """Check if any servers are configured."""
        return len(self.servers) > 0

    def server_count(self) -> int:
        """Get the number of configured servers."""
        return len(self.servers)
