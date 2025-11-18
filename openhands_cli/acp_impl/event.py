"""Utility functions for ACP implementation."""

from typing import TYPE_CHECKING, Any

from acp import SessionNotification
from acp.schema import (
    ContentBlock1,
    ContentBlock2,
    SessionUpdate2,
    SessionUpdate4,
    SessionUpdate5,
    ToolCallContent1,
    ToolCallLocation,
    ToolKind,
)

from openhands.sdk import ImageContent, TextContent
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    LLMConvertibleEvent,
    ObservationEvent,
    UserRejectObservation,
)


if TYPE_CHECKING:
    from acp import AgentSideConnection


from openhands.sdk import get_logger


logger = get_logger(__name__)


def get_tool_kind(tool_name: str) -> ToolKind:
    """Map tool names to ACP ToolKind values.

    Args:
        tool_name: Name of the tool

    Returns:
        ACP ToolKind string ("execute", "edit", "fetch", "think", or "other")
    """
    tool_kind_mapping: dict[str, ToolKind] = {
        "execute_bash": "execute",
        "terminal": "execute",
        "str_replace_editor": "edit",
        "file_editor": "edit",
        "browser_use": "fetch",
        "browser": "fetch",
        "task_tracker": "think",
        "bash": "execute",
    }
    return tool_kind_mapping.get(tool_name, "other")


def _extract_locations(event: ActionEvent) -> list[ToolCallLocation] | None:
    """Extract file locations from an action event if available.

    Returns a list of ToolCallLocation objects if the action contains location
    information (e.g., file paths, directories), otherwise returns None.

    Supports:
    - str_replace_editor: path, view_range, insert_line
    - file_editor: path, view_range, insert_line
    - Other tools with 'path' or 'directory' attributes

    Args:
        event: ActionEvent to extract locations from

    Returns:
        List of ToolCallLocation objects or None
    """
    if not event.action:
        return None

    locations = []

    # Check if action has a 'path' field (e.g., str_replace_editor, file_editor)
    if hasattr(event.action, "path"):
        path = getattr(event.action, "path", None)
        if path:
            location = ToolCallLocation(path=path)

            # Check for line number information
            if hasattr(event.action, "view_range"):
                view_range = getattr(event.action, "view_range", None)
                if view_range and isinstance(view_range, list) and len(view_range) > 0:
                    location.line = view_range[0]
            elif hasattr(event.action, "insert_line"):
                insert_line = getattr(event.action, "insert_line", None)
                if insert_line is not None:
                    location.line = insert_line

            locations.append(location)

    # Check if action has a 'directory' field
    elif hasattr(event.action, "directory"):
        directory = getattr(event.action, "directory", None)
        if directory:
            locations.append(ToolCallLocation(path=directory))

    return locations if locations else None


def _rich_text_to_plain(text: Any) -> str:
    """Convert Rich Text object to plain string.

    Args:
        text: Rich Text object or string

    Returns:
        Plain text string
    """
    if hasattr(text, "plain"):
        return text.plain
    return str(text)


class EventSubscriber:
    """Subscriber for handling OpenHands events and converting them to ACP
    notifications.

    This class subscribes to events from an OpenHands conversation and converts
    them to ACP session update notifications that are streamed back to the client.
    """

    def __init__(self, session_id: str, conn: "AgentSideConnection"):
        """Initialize the event subscriber.

        Args:
            session_id: The ACP session ID
            conn: The ACP connection for sending notifications
        """
        self.session_id = session_id
        self.conn = conn

    async def __call__(self, event: Any):
        """Handle incoming events and convert them to ACP notifications.

        Args:
            event: Event to process (ActionEvent, ObservationEvent, etc.)
        """
        # Handle different event types
        if isinstance(event, ActionEvent):
            await self._handle_action_event(event)
        elif isinstance(
            event, ObservationEvent | UserRejectObservation | AgentErrorEvent
        ):
            await self._handle_observation_event(event)
        elif isinstance(event, LLMConvertibleEvent):
            await self._handle_llm_convertible_event(event)

    async def _handle_action_event(self, event: ActionEvent):
        """Handle ActionEvent: send thought as agent_message_chunk, then tool_call.

        Args:
            event: ActionEvent to process
        """
        try:
            # First, send thoughts/reasoning as agent_message_chunk if available
            thought_text = " ".join([t.text for t in event.thought])

            # Send reasoning content first if available
            if event.reasoning_content and event.reasoning_content.strip():
                await self.conn.sessionUpdate(
                    SessionNotification(
                        sessionId=self.session_id,
                        update=SessionUpdate2(
                            sessionUpdate="agent_message_chunk",
                            content=ContentBlock1(
                                type="text",
                                text=event.reasoning_content,
                            ),
                        ),
                    )
                )

            # Then send thought as agent_message_chunk
            if thought_text.strip():
                await self.conn.sessionUpdate(
                    SessionNotification(
                        sessionId=self.session_id,
                        update=SessionUpdate2(
                            sessionUpdate="agent_message_chunk",
                            content=ContentBlock1(
                                type="text",
                                text=thought_text,
                            ),
                        ),
                    )
                )

            # Now send the tool_call with event.visualize content
            tool_kind = get_tool_kind(event.tool_name)

            # Use event.visualize for comprehensive tool display
            action_viz = _rich_text_to_plain(event.visualize)

            # Use action.title for a brief summary if available
            title = (
                event.action.title  # type: ignore[attr-defined]
                if event.action and hasattr(event.action, "title")
                else event.tool_name
            )

            # Extract locations if available
            locations = _extract_locations(event)

            # Get raw input from tool call if available
            raw_input = None
            if (
                event.tool_call
                and hasattr(event.tool_call, "function")
                and hasattr(event.tool_call.function, "arguments")  # type: ignore[attr-defined]
            ):
                raw_input = event.tool_call.function.arguments  # type: ignore[attr-defined]

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=SessionUpdate4(
                        sessionUpdate="tool_call",
                        toolCallId=event.tool_call_id,
                        title=title,
                        kind=tool_kind,
                        status="pending",
                        content=[
                            ToolCallContent1(
                                type="content",
                                content=ContentBlock1(
                                    type="text",
                                    text=action_viz,
                                ),
                            )
                        ]
                        if action_viz.strip()
                        else None,
                        locations=locations,
                        rawInput=raw_input,
                    ),
                )
            )
        except Exception as e:
            logger.debug(f"Error processing ActionEvent: {e}", exc_info=True)

    async def _handle_observation_event(
        self, event: ObservationEvent | UserRejectObservation | AgentErrorEvent
    ):
        """Handle observation events by sending tool_call_update notification.

        Args:
            event: ObservationEvent, UserRejectObservation, or AgentErrorEvent
        """
        try:
            # Use visualize property for rich content
            viz_text = _rich_text_to_plain(event.visualize)

            # Determine status
            if isinstance(event, ObservationEvent):
                status = "completed"
            else:  # UserRejectObservation or AgentErrorEvent
                status = "failed"

            # Extract raw output for structured data
            raw_output = None
            if isinstance(event, ObservationEvent):
                # Extract content from observation for raw output
                content_parts = []
                for item in event.observation.to_llm_content:
                    if isinstance(item, TextContent):
                        content_parts.append(item.text)
                    elif hasattr(item, "text") and not isinstance(item, ImageContent):
                        content_parts.append(getattr(item, "text"))
                    else:
                        content_parts.append(str(item))
                content_text = "".join(content_parts)
                if content_text.strip():
                    raw_output = {"result": content_text}
            elif isinstance(event, UserRejectObservation):
                raw_output = {"rejection_reason": event.rejection_reason}
            else:  # AgentErrorEvent
                raw_output = {"error": event.error}

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=SessionUpdate5(
                        sessionUpdate="tool_call_update",
                        toolCallId=event.tool_call_id,
                        status=status,
                        content=[
                            ToolCallContent1(
                                type="content",
                                content=ContentBlock1(
                                    type="text",
                                    text=viz_text,
                                ),
                            )
                        ]
                        if viz_text.strip()
                        else None,
                        rawOutput=raw_output,
                    ),
                )
            )
        except Exception as e:
            logger.debug(f"Error processing observation event: {e}", exc_info=True)

    async def _handle_llm_convertible_event(self, event: LLMConvertibleEvent):
        """Handle other LLMConvertibleEvent events.

        Args:
            event: LLMConvertibleEvent to process
        """
        try:
            llm_message = event.to_llm_message()

            # Send the event as a session update
            if llm_message.role == "assistant":
                # Send all content items from the LLM message
                for content_item in llm_message.content:
                    if isinstance(content_item, TextContent):
                        if content_item.text.strip():
                            # Send text content
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock1(
                                            type="text",
                                            text=content_item.text,
                                        ),
                                    ),
                                )
                            )
                    elif isinstance(content_item, ImageContent):
                        # Send each image URL as separate content
                        for image_url in content_item.image_urls:
                            # Determine if it's a URI or base64 data
                            is_uri = image_url.startswith(("http://", "https://"))
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock2(
                                            type="image",
                                            data=image_url,
                                            mimeType="image/png",
                                            uri=image_url if is_uri else None,
                                        ),
                                    ),
                                )
                            )
                    elif isinstance(content_item, str):
                        if content_item.strip():
                            # Send string content as text
                            await self.conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=self.session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock1(
                                            type="text",
                                            text=content_item,
                                        ),
                                    ),
                                )
                            )
        except Exception as e:
            logger.debug(f"Error processing LLMConvertibleEvent: {e}", exc_info=True)
