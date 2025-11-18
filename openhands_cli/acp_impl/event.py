"""Utility functions for ACP implementation."""

from typing import TYPE_CHECKING, Any

from acp import SessionNotification
from acp.schema import (
    TextContentBlock,
    ImageContentBlock,
    AgentThoughtChunk,
    AgentMessageChunk,
    ToolCallStart,
    ToolCallProgress,
    ContentToolCallContent,
    ToolCallLocation,
    TerminalToolCallContent,
    TerminalToolCallContent,
    ToolKind,
)

from openhands.sdk import ImageContent, TextContent, Action
from openhands.sdk.event import (
    Event,
    ActionEvent,
    AgentErrorEvent,
    LLMConvertibleEvent,
    ObservationBaseEvent,
    ObservationEvent,
    UserRejectObservation,
)


if TYPE_CHECKING:
    from acp import AgentSideConnection


from openhands.sdk import get_logger
from openhands.tools.file_editor.definition import FileEditorAction

logger = get_logger(__name__)


def get_tool_kind(tool_name: str, action: Action | None) -> ToolKind:
    """Map tool names to ACP ToolKind values.

    Args:
        tool_name: Name of the tool

    Returns:
        ACP ToolKind string ("execute", "edit", "fetch", "think", or "other")
    """
    tool_kind_mapping: dict[str, ToolKind] = {
        "terminal": "execute",
        "browser_use": "fetch",
        "browser": "fetch",
    }
    
    # Special handling for file_editor tool
    if tool_name == "file_editor":
        assert isinstance(action, FileEditorAction)
        if action.command == "view":
            return "read"
        return "edit"

    return tool_kind_mapping.get(tool_name, "other")


def extract_action_locations(action: Action) -> list[ToolCallLocation] | None:
    """Extract file locations from an action if available.

    Returns a list of ToolCallLocation objects if the action contains location
    information (e.g., file paths, directories), otherwise returns None.

    Supports:
    - file_editor: path, view_range, insert_line
    - Other tools with 'path' or 'directory' attributes

    Args:
        action: Action to extract locations from
    
    Returns:
        List of ToolCallLocation objects or None
    """
    locations = []
    if isinstance(action, FileEditorAction):
        # Handle FileEditorAction specifically
        if action.path:
            location = ToolCallLocation(path=action.path)
            if action.view_range and len(action.view_range) > 0:
                location.line = action.view_range[0]
            elif action.insert_line is not None:
                location.line = action.insert_line
            locations.append(location)
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

    async def __call__(self, event: Event):
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

            if event.reasoning_content and event.reasoning_content.strip():
                await self.conn.sessionUpdate(
                    SessionNotification(
                        sessionId=self.session_id,
                        update=AgentThoughtChunk(
                            sessionUpdate="agent_thought_chunk",
                            content=TextContentBlock(
                                type="text",
                                text="**Reasoning**:\n" + event.reasoning_content.strip() + "\n",
                            ),
                        ),
                    )
                )

            if thought_text.strip():
                await self.conn.sessionUpdate(
                    SessionNotification(
                        sessionId=self.session_id,
                        update=AgentThoughtChunk(
                            sessionUpdate="agent_thought_chunk",
                            content=TextContentBlock(
                                type="text",
                                text="\n**Thought**:\n" + thought_text.strip() + "\n",
                            ),
                        ),
                    )
                )

            # Now send the tool_call with event.visualize content
            tool_kind = get_tool_kind(event.tool_name, event.action)

            # Use event.visualize for comprehensive tool display
            action_viz = None
            if event.action:
                action_viz = _rich_text_to_plain(event.action.visualize)

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=ToolCallStart(
                        sessionUpdate="tool_call",
                        toolCallId=event.tool_call_id,
                        title=action_viz if action_viz is not None else event.tool_name,
                        kind=tool_kind,
                        status="in_progress",
                        content=[
                            ContentToolCallContent(
                                type="content",
                                content=TextContentBlock(
                                    type="text",
                                    text=action_viz,
                                ),
                            )
                        ]
                        if action_viz is not None and action_viz.strip()
                        else None,
                        locations=extract_action_locations(event.action) if event.action else None,
                        rawInput=event.action.model_dump() if event.action else None,
                    ),
                )
            )
        except Exception as e:
            logger.debug(f"Error processing ActionEvent: {e}", exc_info=True)

    async def _handle_observation_event(
        self, event: ObservationBaseEvent
    ):
        """Handle observation events by sending tool_call_update notification.

        Args:
            event: ObservationEvent, UserRejectObservation, or AgentErrorEvent
        """
        try:
            viz_text = _rich_text_to_plain(event.visualize)

            if isinstance(event, ObservationEvent):
                status = "completed"
            else:  # UserRejectObservation or AgentErrorEvent
                status = "failed"

            await self.conn.sessionUpdate(
                SessionNotification(
                    sessionId=self.session_id,
                    update=ToolCallProgress(
                        sessionUpdate="tool_call_update",
                        toolCallId=event.tool_call_id,
                        status=status,
                        content=[
                            ContentToolCallContent(
                                type="content",
                                content=TextContentBlock(
                                    type="text",
                                    text=viz_text,
                                ),
                            )
                        ]
                        if viz_text.strip()
                        else None,
                        rawOutput=event.model_dump(),
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
                                    update=AgentMessageChunk(
                                        sessionUpdate="agent_message_chunk",
                                        content=TextContentBlock(
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
                                    update=AgentMessageChunk(
                                        sessionUpdate="agent_message_chunk",
                                        content=ImageContentBlock(
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
                                    update=AgentMessageChunk(
                                        sessionUpdate="agent_message_chunk",
                                        content=TextContentBlock(
                                            type="text",
                                            text=content_item,
                                        ),
                                    ),
                                )
                            )
        except Exception as e:
            logger.debug(f"Error processing LLMConvertibleEvent: {e}", exc_info=True)
