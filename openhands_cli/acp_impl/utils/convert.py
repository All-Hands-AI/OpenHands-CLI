"""Utility functions for ACP implementation."""

from acp.schema import (
    AudioContentBlock as ACPAudioContentBlock,
    EmbeddedResourceContentBlock as ACPEmbeddedResourceContentBlock,
    ImageContentBlock as ACPImageContentBlock,
    ResourceContentBlock as ACPResourceContentBlock,
    TextContentBlock as ACPTextContentBlock,
)

from openhands.sdk import ImageContent, TextContent
from openhands_cli.acp_impl.utils.resources import convert_resources_to_content


def convert_acp_prompt_to_message_content(
    acp_prompt: list[
        ACPTextContentBlock
        | ACPImageContentBlock
        | ACPAudioContentBlock
        | ACPResourceContentBlock
        | ACPEmbeddedResourceContentBlock,
    ],
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
            message_content.append(TextContent(text=block.text))
        elif isinstance(block, ACPImageContentBlock):
            message_content.append(
                ImageContent(image_urls=[f"data:{block.mimeType};base64,{block.data}"])
            )
        elif isinstance(
            block, ACPResourceContentBlock | ACPEmbeddedResourceContentBlock
        ):
            # https://agentclientprotocol.com/protocol/content#resource-link
            # https://agentclientprotocol.com/protocol/content#embedded-resource
            message_content.append(convert_resources_to_content(block))
    return message_content
