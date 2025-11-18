"""Utility functions for ACP implementation."""

from typing import Any

from acp.schema import EnvVariable, HttpMcpServer, SseMcpServer, StdioMcpServer

# Union type for all MCP server types from ACP
ACPMCPServerType = StdioMcpServer | HttpMcpServer | SseMcpServer


def _transform_env_to_dict(env: list[dict[str, str]]) -> dict[str, str]:
    """
    Transform environment variables from serialized EnvVariable format to a dictionary.

    When Pydantic models are dumped to dict, EnvVariable objects become dicts
    with 'name' and 'value' keys.

    Args:
        env: List of dicts with 'name' and 'value' keys (serialized EnvVariable objects)

    Returns:
        Dictionary mapping environment variable names to values
    """
    env_dict: dict[str, str] = {}
    for env_var in env:
        # Serialized EnvVariable has 'name' and 'value' keys
        env_dict[env_var["name"]] = env_var["value"]

    return env_dict


def transform_acp_mcp_servers_to_agent_format(
    mcp_servers: list[ACPMCPServerType],
) -> dict[str, dict[str, Any]]:
    """
    Transform MCP servers from ACP format to Agent format.

    ACP and Agent use different formats for MCP server configurations:
    - ACP: List of Pydantic server models with 'name' field, env as array of EnvVariable
    - Agent: Dict keyed by server name, env as dict

    Args:
        mcp_servers: List of MCP server Pydantic models from ACP

    Returns:
        Dictionary of MCP servers in Agent format (keyed by name)
    """
    transformed_servers: dict[str, dict[str, Any]] = {}

    for server in mcp_servers:
        # Convert Pydantic model to dict
        server_dict = server.model_dump()

        server_name: str = server_dict["name"]

        # Create config without the name field
        server_config: dict[str, Any] = {k: v for k, v in server_dict.items() if k != "name"}

        # Transform env from array to dict format if present
        # ACP sends env as array of EnvVariable objects, but Agent expects dict
        if "env" in server_config:
            server_config["env"] = _transform_env_to_dict(server_config["env"])

        transformed_servers[server_name] = server_config

    return transformed_servers
