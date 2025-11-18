"""Tests for the EventSubscriber class."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from acp import SessionNotification
from acp.schema import SessionUpdate2, SessionUpdate4, SessionUpdate5

from openhands.sdk import Message, TextContent
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
)
from openhands_cli.acp_impl.utils import EventSubscriber


@pytest.fixture
def mock_connection():
    """Create a mock ACP connection."""
    conn = AsyncMock()
    return conn


@pytest.fixture
def event_subscriber(mock_connection):
    """Create an EventSubscriber instance."""
    return EventSubscriber("test-session", mock_connection)


@pytest.mark.asyncio
async def test_handle_message_event(event_subscriber, mock_connection):
    """Test handling of MessageEvent from assistant."""
    # Create a mock MessageEvent
    message = Message(role="assistant", content=[TextContent(text="Test response")])
    event = MessageEvent(source="agent", llm_message=message)

    # Process the event
    await event_subscriber(event)

    # Verify sessionUpdate was called
    assert mock_connection.sessionUpdate.called
    call_args = mock_connection.sessionUpdate.call_args[0][0]
    assert isinstance(call_args, SessionNotification)
    assert call_args.sessionId == "test-session"
    assert isinstance(call_args.update, SessionUpdate2)
    assert call_args.update.sessionUpdate == "agent_message_chunk"


@pytest.mark.asyncio
async def test_handle_action_event(event_subscriber, mock_connection):
    """Test handling of ActionEvent."""
    # Create a mock ActionEvent with proper structure
    from rich.text import Text

    # Create a simple object for the action with only needed attributes
    class MockAction:
        title = "Test Action"
        visualize = Text("Executing test action")

    # Create a simple object for tool_call
    class MockToolCall:
        class MockFunction:
            arguments = '{"arg": "value"}'

        function = MockFunction()

    # Create event (use a simple object to avoid MagicMock's hasattr behavior)
    class MockEvent:
        thought = [TextContent(text="Thinking about the task")]
        reasoning_content = "This is my reasoning"
        tool_name = "terminal"
        tool_call_id = "test-call-123"
        action = MockAction()
        tool_call = MockToolCall()

    event = MockEvent()

    # Process the event
    await event_subscriber._handle_action_event(event)

    # Verify sessionUpdate was called multiple times (reasoning, thought, tool_call)
    assert mock_connection.sessionUpdate.call_count >= 3

    # Check that tool_call notification was sent
    calls = mock_connection.sessionUpdate.call_args_list
    tool_call_found = False
    for call in calls:
        notification = call[0][0]
        if isinstance(notification.update, SessionUpdate4):
            tool_call_found = True
            assert notification.update.sessionUpdate == "tool_call"
            assert notification.update.toolCallId == "test-call-123"
            assert notification.update.kind == "execute"  # terminal maps to execute
            assert notification.update.status == "pending"

    assert tool_call_found, "tool_call notification should be sent"


@pytest.mark.asyncio
async def test_handle_observation_event(event_subscriber, mock_connection):
    """Test handling of ObservationEvent."""
    from rich.text import Text

    # Create a mock observation
    mock_observation = MagicMock()
    mock_observation.to_llm_content = [
        TextContent(text="Command executed successfully")
    ]

    # Create ObservationEvent
    event = MagicMock(spec=ObservationEvent)
    event.visualize = Text("Result: success")
    event.tool_call_id = "test-call-123"
    event.observation = mock_observation

    # Process the event
    await event_subscriber._handle_observation_event(event)

    # Verify sessionUpdate was called
    assert mock_connection.sessionUpdate.called
    call_args = mock_connection.sessionUpdate.call_args[0][0]
    assert isinstance(call_args, SessionNotification)
    assert isinstance(call_args.update, SessionUpdate5)
    assert call_args.update.sessionUpdate == "tool_call_update"
    assert call_args.update.toolCallId == "test-call-123"
    assert call_args.update.status == "completed"


@pytest.mark.asyncio
async def test_handle_agent_error_event(event_subscriber, mock_connection):
    """Test handling of AgentErrorEvent."""
    from rich.text import Text

    # Create AgentErrorEvent
    event = MagicMock(spec=AgentErrorEvent)
    event.visualize = Text("Error: Something went wrong")
    event.tool_call_id = "test-call-123"
    event.error = "Something went wrong"

    # Process the event
    await event_subscriber._handle_observation_event(event)

    # Verify sessionUpdate was called
    assert mock_connection.sessionUpdate.called
    call_args = mock_connection.sessionUpdate.call_args[0][0]
    assert isinstance(call_args, SessionNotification)
    assert isinstance(call_args.update, SessionUpdate5)
    assert call_args.update.sessionUpdate == "tool_call_update"
    assert call_args.update.status == "failed"
    assert call_args.update.rawOutput == {"error": "Something went wrong"}


@pytest.mark.asyncio
async def test_event_subscriber_with_empty_text(event_subscriber, mock_connection):
    """Test that events with empty text don't trigger updates."""
    # Create a MessageEvent with empty text
    message = Message(role="assistant", content=[TextContent(text="")])
    event = MessageEvent(source="agent", llm_message=message)

    # Process the event
    await event_subscriber(event)

    # Verify sessionUpdate was not called for empty text
    assert not mock_connection.sessionUpdate.called


@pytest.mark.asyncio
async def test_event_subscriber_with_user_message(event_subscriber, mock_connection):
    """Test that user messages are not processed."""
    # Create a MessageEvent from user (not agent)
    message = Message(role="user", content=[TextContent(text="User message")])
    event = MessageEvent(source="user", llm_message=message)

    # Process the event
    await event_subscriber(event)

    # Verify sessionUpdate was not called for user messages
    assert not mock_connection.sessionUpdate.called
