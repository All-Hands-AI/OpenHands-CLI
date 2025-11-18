"""Utility functions for ACP implementation."""

from collections.abc import Sequence
from typing import Any

from acp.schema import (
    HttpMcpServer,
    SseMcpServer,
    StdioMcpServer,
)

from openhands.sdk import ImageContent, TextContent, get_logger


logger = get_logger(__name__)


# Union type for all MCP server types from ACP
ACPMCPServerType = StdioMcpServer | HttpMcpServer | SseMcpServer


def _transform_env_to_dict(env: Sequence[dict[str, str]]) -> dict[str, str]:
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
    mcp_servers: Sequence[ACPMCPServerType],
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
        server_config: dict[str, Any] = {
            k: v for k, v in server_dict.items() if k != "name"
        }

        # Transform env from array to dict format if present
        # ACP sends env as array of EnvVariable objects, but Agent expects dict
        if "env" in server_config:
            server_config["env"] = _transform_env_to_dict(server_config["env"])

        transformed_servers[server_name] = server_config

    return transformed_servers


def _process_text_block(block: dict | Any) -> TextContent | None:
    """Process a text block and return TextContent."""
    text = ""
    if isinstance(block, dict):
        text = block.get("text", "")
    elif hasattr(block, "text"):
        text = getattr(block, "text", "")
    return TextContent(text=text) if text else None


def _process_image_block(block: dict | Any) -> ImageContent | None:
    """Process an image block and return ImageContent."""
    image_data = None
    if isinstance(block, dict):
        image_data = block.get("data")
    elif hasattr(block, "data"):
        image_data = block.data

    if image_data:
        logger.info(f"Added image to message: {image_data[:100]}...")
        return ImageContent(image_urls=[image_data])
    return None


def _process_content_block(block: dict | Any) -> TextContent | ImageContent | None:
    """Process a single content block (text or image)."""
    block_type = None
    if isinstance(block, dict):
        block_type = block.get("type")
    elif hasattr(block, "type"):
        block_type = block.type

    if block_type == "text":
        return _process_text_block(block)
    elif block_type == "image":
        return _process_image_block(block)
    raise ValueError(f"Unsupported content block type: {block_type}")


def convert_acp_prompt_to_message_content(
    prompt: str | list | Any,
) -> list[TextContent | ImageContent]:
    """
    Convert ACP prompt to OpenHands message content format.

    Handles various ACP prompt formats:
    - Simple string
    - List of content blocks (text/image)
    - Single ContentBlock object

    Args:
        prompt: ACP prompt in various formats (string, list, or ContentBlock)

    Returns:
        List of TextContent and ImageContent objects
    """
    message_content: list[TextContent | ImageContent] = []

    if isinstance(prompt, str):
        # Simple string prompt
        message_content.append(TextContent(text=prompt))
    elif isinstance(prompt, list):
        # List of content blocks
        for block in prompt:
            content = _process_content_block(block)
            if content:
                message_content.append(content)
    else:
        # Single ContentBlock object
        content = _process_content_block(prompt)
        if content:
            message_content.append(content)

    return message_content
