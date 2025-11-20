"""Advanced tests for ACP implementation."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from acp import CancelNotification, LoadSessionRequest

from openhands.sdk import BaseConversation
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
)
from openhands.tools.file_editor.definition import FileEditorAction
from openhands_cli.acp_impl.agent import OpenHandsACPAgent
from openhands_cli.acp_impl.event import extract_action_locations


@pytest.fixture
def mock_connection():
    """Create a mock ACP connection."""
    conn = AsyncMock()
    return conn


@pytest.fixture
def acp_agent(mock_connection):
    """Create an OpenHands ACP agent instance."""
    return OpenHandsACPAgent(mock_connection)


@pytest.mark.asyncio
async def test_determine_stop_reason_cancelled(acp_agent):
    """Test _determine_stop_reason when session is cancelled."""
    session_id = str(uuid4())
    mock_conversation = MagicMock(spec=BaseConversation)
    mock_state = MagicMock()
    mock_state.execution_status = ConversationExecutionStatus.PAUSED
    mock_conversation.state = mock_state

    # Mark session as cancelled
    acp_agent._cancelled_sessions.add(session_id)

    stop_reason = acp_agent._determine_stop_reason(session_id, mock_conversation)

    assert stop_reason == "cancelled"
    # Session should be removed from cancelled set
    assert session_id not in acp_agent._cancelled_sessions


@pytest.mark.asyncio
async def test_determine_stop_reason_stuck(acp_agent):
    """Test _determine_stop_reason when conversation is stuck."""
    session_id = str(uuid4())
    mock_conversation = MagicMock(spec=BaseConversation)
    mock_state = MagicMock()
    mock_state.execution_status = ConversationExecutionStatus.STUCK
    mock_conversation.state = mock_state

    stop_reason = acp_agent._determine_stop_reason(session_id, mock_conversation)

    assert stop_reason == "max_turn_requests"


@pytest.mark.asyncio
async def test_determine_stop_reason_error(acp_agent):
    """Test _determine_stop_reason when conversation has error."""
    session_id = str(uuid4())
    mock_conversation = MagicMock(spec=BaseConversation)
    mock_state = MagicMock()
    mock_state.execution_status = ConversationExecutionStatus.ERROR
    mock_conversation.state = mock_state

    stop_reason = acp_agent._determine_stop_reason(session_id, mock_conversation)

    assert stop_reason == "end_turn"


@pytest.mark.asyncio
async def test_determine_stop_reason_finished(acp_agent):
    """Test _determine_stop_reason when conversation finishes normally."""
    session_id = str(uuid4())
    mock_conversation = MagicMock(spec=BaseConversation)
    mock_state = MagicMock()
    mock_state.execution_status = ConversationExecutionStatus.FINISHED
    mock_conversation.state = mock_state

    stop_reason = acp_agent._determine_stop_reason(session_id, mock_conversation)

    assert stop_reason == "end_turn"


@pytest.mark.asyncio
async def test_get_or_create_conversation_caching(acp_agent, tmp_path):
    """Test that _get_or_create_conversation caches conversations."""
    session_id = str(uuid4())

    with (
        patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load,
        patch("openhands_cli.acp_impl.agent.Conversation") as mock_conv,
    ):
        mock_agent = MagicMock()
        mock_load.return_value = mock_agent

        mock_conversation = MagicMock()
        mock_conv.return_value = mock_conversation

        # First call should create a new conversation
        conv1 = acp_agent._get_or_create_conversation(
            session_id=session_id, working_dir=str(tmp_path)
        )

        assert conv1 == mock_conversation
        assert session_id in acp_agent._active_sessions

        # Second call should return cached conversation
        conv2 = acp_agent._get_or_create_conversation(session_id=session_id)

        assert conv2 == conv1
        assert conv2 == mock_conversation
        # Conversation should only be created once
        mock_conv.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_unknown_session(acp_agent):
    """Test cancelling a session that doesn't exist."""
    session_id = str(uuid4())
    notification = CancelNotification(sessionId=session_id)

    # Mock _setup_acp_conversation to return a conversation
    with patch.object(acp_agent, "_setup_acp_conversation") as mock_setup:
        mock_conversation = MagicMock()
        mock_setup.return_value = mock_conversation

        # Should not raise an error
        await acp_agent.cancel(notification)

        # Session should be marked as cancelled
        assert session_id in acp_agent._cancelled_sessions


@pytest.mark.asyncio
async def test_cancel_pauses_conversation(acp_agent):
    """Test that cancelling a session pauses the conversation."""
    session_id = str(uuid4())
    notification = CancelNotification(sessionId=session_id)

    # Create a mock conversation and add it to active sessions
    mock_conversation = MagicMock()
    acp_agent._active_sessions[session_id] = mock_conversation

    await acp_agent.cancel(notification)

    # Verify pause was called
    mock_conversation.pause.assert_called_once()
    # Verify session is marked as cancelled
    assert session_id in acp_agent._cancelled_sessions


@pytest.mark.asyncio
async def test_load_session_with_no_history(acp_agent, mock_connection):
    """Test loading a session with no history."""
    session_id = str(uuid4())
    request = LoadSessionRequest(sessionId=session_id, cwd="/test/path", mcpServers=[])

    # Create mock conversation with empty history
    mock_conversation = MagicMock()
    mock_conversation.state.events = []

    with patch.object(acp_agent, "_get_or_create_conversation") as mock_get:
        mock_get.return_value = mock_conversation

        await acp_agent.loadSession(request)

        # Verify no sessionUpdate was called
        mock_connection.sessionUpdate.assert_not_called()


def test_extract_action_locations_file_editor():
    """Test extracting locations from FileEditorAction."""
    # Test with path and view_range
    action = FileEditorAction(command="view", path="/test/file.py", view_range=[10, 20])

    locations = extract_action_locations(action)

    assert locations is not None
    assert len(locations) == 1
    assert locations[0].path == "/test/file.py"
    assert locations[0].line == 10


def test_extract_action_locations_file_editor_insert():
    """Test extracting locations from FileEditorAction with insert_line."""
    action = FileEditorAction(
        command="insert",
        path="/test/file.py",
        insert_line=5,
        new_str="print('hello')",
    )

    locations = extract_action_locations(action)

    assert locations is not None
    assert len(locations) == 1
    assert locations[0].path == "/test/file.py"
    assert locations[0].line == 5


def test_extract_action_locations_no_location():
    """Test extracting locations from action with no location info."""
    # Mock action that doesn't have location info
    mock_action = MagicMock()
    mock_action.path = None

    locations = extract_action_locations(mock_action)

    assert locations is None


def test_extract_action_locations_file_editor_no_range():
    """Test extracting locations from FileEditorAction without view_range."""
    action = FileEditorAction(command="view", path="/test/file.py")

    locations = extract_action_locations(action)

    assert locations is not None
    assert len(locations) == 1
    assert locations[0].path == "/test/file.py"
    # Line should not be set if no view_range or insert_line
    assert not hasattr(locations[0], "line") or locations[0].line is None


@pytest.mark.asyncio
async def test_handle_acp_confirmation_allow_once(acp_agent, mock_connection):
    """Test handling ACP confirmation with allow_once."""
    session_id = str(uuid4())

    # Mock conversation with state containing events
    mock_conversation = MagicMock()
    mock_conversation.state.events = ["mock_event"]

    # Mock requestPermission response (allow_once)
    mock_outcome = MagicMock()
    mock_outcome.outcome = "selected"
    mock_outcome.optionId = "allow_once"

    mock_response = MagicMock()
    mock_response.outcome = mock_outcome

    mock_connection.requestPermission = AsyncMock(return_value=mock_response)

    # Mock ConversationState.get_unmatched_actions to return pending actions
    with patch(
        "openhands_cli.acp_impl.agent.ConversationState.get_unmatched_actions"
    ) as mock_get_unmatched:
        mock_action = MagicMock()
        mock_action.visualize.plain = "Test action"
        mock_get_unmatched.return_value = [mock_action]

        result = await acp_agent._handle_acp_confirmation(
            session_id=session_id,
            conversation=mock_conversation,
        )

        assert result is True
        # Verify requestPermission was called
        mock_connection.requestPermission.assert_called_once()


@pytest.mark.asyncio
async def test_handle_acp_confirmation_reject_once(acp_agent, mock_connection):
    """Test handling ACP confirmation with reject_once."""
    session_id = str(uuid4())

    # Mock conversation with state containing events
    mock_conversation = MagicMock()
    mock_conversation.state.events = ["mock_event"]

    # Mock requestPermission response (reject_once)
    mock_outcome = MagicMock()
    mock_outcome.outcome = "selected"
    mock_outcome.optionId = "reject_once"

    mock_response = MagicMock()
    mock_response.outcome = mock_outcome

    mock_connection.requestPermission = AsyncMock(return_value=mock_response)

    # Mock ConversationState.get_unmatched_actions to return pending actions
    with patch(
        "openhands_cli.acp_impl.agent.ConversationState.get_unmatched_actions"
    ) as mock_get_unmatched:
        mock_action = MagicMock()
        mock_action.visualize.plain = "Test action"
        mock_get_unmatched.return_value = [mock_action]

        result = await acp_agent._handle_acp_confirmation(
            session_id=session_id,
            conversation=mock_conversation,
        )

        assert result is False
        # Verify reject_pending_actions was called
        mock_conversation.reject_pending_actions.assert_called_once()


@pytest.mark.asyncio
async def test_handle_acp_confirmation_cancelled(acp_agent, mock_connection):
    """Test handling ACP confirmation when cancelled."""
    session_id = str(uuid4())

    # Mock conversation with state containing events
    mock_conversation = MagicMock()
    mock_conversation.state.events = ["mock_event"]

    # Mock requestPermission response (cancelled)
    mock_outcome = MagicMock()
    mock_outcome.outcome = "cancelled"

    mock_response = MagicMock()
    mock_response.outcome = mock_outcome

    mock_connection.requestPermission = AsyncMock(return_value=mock_response)

    # Mock ConversationState.get_unmatched_actions to return pending actions
    with patch(
        "openhands_cli.acp_impl.agent.ConversationState.get_unmatched_actions"
    ) as mock_get_unmatched:
        mock_action = MagicMock()
        mock_action.visualize.plain = "Test action"
        mock_get_unmatched.return_value = [mock_action]

        result = await acp_agent._handle_acp_confirmation(
            session_id=session_id,
            conversation=mock_conversation,
        )

        assert result is False
        # Verify session was marked as cancelled
        assert session_id in acp_agent._cancelled_sessions
        # Verify conversation was paused
        mock_conversation.pause.assert_called_once()


@pytest.mark.asyncio
async def test_handle_acp_confirmation_error(acp_agent, mock_connection):
    """Test handling ACP confirmation when an error occurs."""
    session_id = str(uuid4())

    # Mock conversation with state containing events
    mock_conversation = MagicMock()
    mock_conversation.state.events = ["mock_event"]

    # Mock requestPermission to raise an exception
    mock_connection.requestPermission = AsyncMock(
        side_effect=Exception("Connection error")
    )

    # Mock ConversationState.get_unmatched_actions to return pending actions
    with patch(
        "openhands_cli.acp_impl.agent.ConversationState.get_unmatched_actions"
    ) as mock_get_unmatched:
        mock_action = MagicMock()
        mock_action.visualize.plain = "Test action"
        mock_get_unmatched.return_value = [mock_action]

        result = await acp_agent._handle_acp_confirmation(
            session_id=session_id,
            conversation=mock_conversation,
        )

        assert result is False
        # Verify reject_pending_actions was called due to error
        mock_conversation.reject_pending_actions.assert_called_once_with(
            "Error processing permission request"
        )
