"""Utility functions for ACP implementation."""

from collections.abc import Sequence
from typing import Any

from uuid import uuid4
import base64
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from acp.schema import (
    HttpMcpServer,
    SseMcpServer,
    StdioMcpServer,
    EnvVariable,
    TextContentBlock as ACPTextContentBlock,
    ImageContentBlock as ACPImageContentBlock,
    AudioContentBlock as ACPAudioContentBlock,
    ResourceContentBlock as ACPResourceContentBlock,
    EmbeddedResourceContentBlock as ACPEmbeddedResourceContentBlock,
    TextResourceContents as ACPTextResourceContents,
    BlobResourceContents as ACPBlobResourceContents
)

from openhands.sdk import (
    ImageContent, 
    TextContent,
    get_logger
)
from openhands_cli.acp_impl.utils.resources import convert_resources_to_content



def convert_acp_prompt_to_message_content(
    acp_prompt: list[
        ACPTextContentBlock
                |ACPImageContentBlock
                |ACPAudioContentBlock
                |ACPResourceContentBlock
                |ACPEmbeddedResourceContentBlock,
        ]
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
        List of TextContent and ImageContent objects supported by SDK
    """
    message_content: list[TextContent | ImageContent] = []
    for block in acp_prompt:
        if isinstance(block, ACPTextContentBlock):
            message_content.append(
                TextContent(text=block.text)
            )
        elif isinstance(block, ACPImageContentBlock):
            message_content.append(
                ImageContent(image_urls=[f"data:{block.mimeType};base64,{block.data}"])
            )
        elif isinstance(block, (ACPResourceContentBlock, ACPEmbeddedResourceContentBlock)):
            # https://agentclientprotocol.com/protocol/content#resource-link
            # https://agentclientprotocol.com/protocol/content#embedded-resource
            message_content.append(
                convert_resources_to_content(block)
            )
    return message_content
