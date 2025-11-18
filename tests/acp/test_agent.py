"""Tests for the OpenHands ACP Agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from acp import InitializeRequest, NewSessionRequest, PromptRequest
from acp.schema import AgentCapabilities, Implementation, TextContentBlock

from openhands_cli.acp_impl.agent import OpenHandsACPAgent


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
async def test_initialize_with_configured_agent(acp_agent):
    """Test agent initialization when agent is configured."""
    request = InitializeRequest(
        protocolVersion=1,
        clientInfo=Implementation(name="test-client", version="1.0.0"),
    )

    # Mock load_agent_specs to succeed
    with patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load:
        mock_agent = MagicMock()
        mock_load.return_value = mock_agent

        response = await acp_agent.initialize(request)

        assert response.protocolVersion == 1
        assert isinstance(response.agentCapabilities, AgentCapabilities)
        assert response.agentCapabilities.loadSession is True
        assert len(response.authMethods) == 0  # No auth needed when configured


@pytest.mark.asyncio
async def test_initialize_without_configured_agent(acp_agent):
    """Test agent initialization when agent is not configured."""
    from openhands_cli.setup import MissingAgentSpec

    request = InitializeRequest(
        protocolVersion=1,
        clientInfo=Implementation(name="test-client", version="1.0.0"),
    )

    # Mock load_agent_specs to raise MissingAgentSpec
    with patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load:
        mock_load.side_effect = MissingAgentSpec("Not configured")

        response = await acp_agent.initialize(request)

        assert response.protocolVersion == 1
        assert len(response.authMethods) == 0  # No auth methods for now


@pytest.mark.asyncio
async def test_authenticate(acp_agent):
    """Test authentication."""
    from acp import AuthenticateRequest

    request = AuthenticateRequest(methodId="test-method")
    response = await acp_agent.authenticate(request)

    assert response is not None


@pytest.mark.asyncio
async def test_new_session_success(acp_agent, tmp_path):
    """Test creating a new session successfully."""
    request = NewSessionRequest(cwd=str(tmp_path), mcpServers=[])

    # Mock the CLI utilities
    with (
        patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load,
        patch("openhands_cli.acp_impl.agent.Conversation") as mock_conv,
    ):
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.llm.model = "test-model"
        mock_load.return_value = mock_agent

        # Mock conversation
        mock_conversation = MagicMock()
        mock_conv.return_value = mock_conversation

        response = await acp_agent.newSession(request)

        # Verify session was created
        assert response.sessionId is not None

        # Verify it's a valid UUID
        session_uuid = UUID(response.sessionId)
        assert str(session_uuid) == response.sessionId

        # Verify session is stored
        assert response.sessionId in acp_agent._sessions
        assert acp_agent._sessions[response.sessionId] == mock_conversation


@pytest.mark.asyncio
async def test_new_session_agent_not_configured(acp_agent, tmp_path):
    """Test creating a new session when agent is not configured."""
    from openhands_cli.setup import MissingAgentSpec

    request = NewSessionRequest(cwd=str(tmp_path), mcpServers=[])

    # Mock load_agent_specs to raise MissingAgentSpec
    with patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load:
        mock_load.side_effect = MissingAgentSpec("Not configured")

        with pytest.raises(ValueError, match="Agent not configured"):
            await acp_agent.newSession(request)


@pytest.mark.asyncio
async def test_new_session_creates_working_directory(acp_agent, tmp_path):
    """Test that new session creates working directory if it doesn't exist."""
    # Create a path that doesn't exist yet
    new_dir = tmp_path / "subdir" / "workdir"
    request = NewSessionRequest(cwd=str(new_dir), mcpServers=[])

    with (
        patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load,
        patch("openhands_cli.acp_impl.agent.Conversation") as mock_conv,
    ):
        mock_agent = MagicMock()
        mock_agent.llm.model = "test-model"
        mock_load.return_value = mock_agent

        mock_conversation = MagicMock()
        mock_conv.return_value = mock_conversation

        await acp_agent.newSession(request)

        # Verify directory was created
        assert new_dir.exists()
        assert new_dir.is_dir()


@pytest.mark.asyncio
async def test_prompt_unknown_session(acp_agent):
    """Test prompt with unknown session ID."""

    content_blocks = [TextContentBlock(type="text", text="Hello")]
    request = PromptRequest(sessionId="unknown-session", prompt=content_blocks)

    with pytest.raises(ValueError, match="Unknown session"):
        await acp_agent.prompt(request)


@pytest.mark.asyncio
async def test_prompt_empty_text(acp_agent):
    """Test prompt with empty text."""

    session_id = "test-session"

    # Create mock conversation
    mock_conversation = MagicMock()
    acp_agent._sessions[session_id] = mock_conversation

    # Test with empty prompt
    request = PromptRequest(
        sessionId=session_id, prompt=[TextContentBlock(type="text", text="")]
    )
    response = await acp_agent.prompt(request)

    assert response.stopReason == "end_turn"


@pytest.mark.asyncio
async def test_prompt_success(acp_agent, mock_connection):
    """Test successful prompt processing."""
    from openhands.sdk import Message, TextContent
    from openhands.sdk.event.llm_convertible.message import MessageEvent

    session_id = "test-session"

    # Create mock conversation
    mock_conversation = MagicMock()
    mock_conversation.state.events = []
    acp_agent._sessions[session_id] = mock_conversation

    # Create a mock agent message event
    mock_message = Message(
        role="assistant", content=[TextContent(text="Hello, I can help!")]
    )
    mock_event = MessageEvent(source="agent", llm_message=mock_message)

    # Mock conversation.run to add the event
    async def mock_run(fn):
        # Call the real function which is conversation.run
        fn()
        mock_conversation.state.events.append(mock_event)

    with patch("asyncio.to_thread", side_effect=mock_run):
        request = PromptRequest(
            sessionId=session_id, prompt=[TextContentBlock(type="text", text="Hello")]
        )
        response = await acp_agent.prompt(request)

        assert response.stopReason == "end_turn"

        # Verify sessionUpdate was called
        mock_connection.sessionUpdate.assert_called_once()


@pytest.mark.asyncio
async def test_cancel(acp_agent):
    """Test cancelling an operation."""
    from acp import CancelNotification

    session_id = "test-session"
    notification = CancelNotification(sessionId=session_id)

    # Create mock conversation
    mock_conversation = MagicMock()
    acp_agent._sessions[session_id] = mock_conversation

    await acp_agent.cancel(notification)

    # Verify pause was called
    mock_conversation.pause.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_unknown_session(acp_agent):
    """Test cancelling an unknown session (should not raise error)."""
    from acp import CancelNotification

    notification = CancelNotification(sessionId="unknown-session")

    # Should not raise an error
    await acp_agent.cancel(notification)


@pytest.mark.asyncio
async def test_load_session_not_found(acp_agent):
    """Test loading a non-existent session."""
    from acp import LoadSessionRequest

    request = LoadSessionRequest(
        sessionId="non-existent", cwd="/test/path", mcpServers=[]
    )

    with pytest.raises(ValueError, match="Session not found"):
        await acp_agent.loadSession(request)


@pytest.mark.asyncio
async def test_load_session_success(acp_agent, mock_connection):
    """Test loading an existing session."""
    from acp import LoadSessionRequest

    from openhands.sdk import Message, TextContent
    from openhands.sdk.event.llm_convertible.message import MessageEvent

    session_id = "existing-session"
    request = LoadSessionRequest(sessionId=session_id, cwd="/test/path", mcpServers=[])

    # Create mock conversation with history
    mock_conversation = MagicMock()
    user_message = Message(role="user", content=[TextContent(text="Hello")])
    agent_message = Message(role="assistant", content=[TextContent(text="Hi there!")])

    mock_conversation.state.events = [
        MessageEvent(source="user", llm_message=user_message),
        MessageEvent(source="agent", llm_message=agent_message),
    ]

    acp_agent._sessions[session_id] = mock_conversation

    await acp_agent.loadSession(request)

    # Verify sessionUpdate was called for both messages
    assert mock_connection.sessionUpdate.call_count == 2


@pytest.mark.asyncio
async def test_set_session_mode(acp_agent):
    """Test setting session mode."""
    from acp.schema import SetSessionModeRequest

    request = SetSessionModeRequest(sessionId="test-session", modeId="default")
    response = await acp_agent.setSessionMode(request)

    assert response is not None


@pytest.mark.asyncio
async def test_set_session_model(acp_agent):
    """Test setting session model."""
    from acp.schema import SetSessionModelRequest

    request = SetSessionModelRequest(sessionId="test-session", modelId="default")
    response = await acp_agent.setSessionModel(request)

    assert response is not None


@pytest.mark.asyncio
async def test_ext_method(acp_agent):
    """Test extension method."""
    result = await acp_agent.extMethod("test-method", {"key": "value"})

    assert "error" in result


@pytest.mark.asyncio
async def test_ext_notification(acp_agent):
    """Test extension notification."""
    # Should not raise any errors
    await acp_agent.extNotification("test-notification", {"key": "value"})


@pytest.mark.asyncio
async def test_prompt_with_image(acp_agent, mock_connection):
    """Test prompt with image content."""
    from acp.schema import ImageContentBlock

    from openhands.sdk import Message, TextContent
    from openhands.sdk.event.llm_convertible.message import MessageEvent

    session_id = "test-session"

    # Create mock conversation
    mock_conversation = MagicMock()
    mock_conversation.state.events = []
    acp_agent._sessions[session_id] = mock_conversation

    # Create a mock agent message event
    mock_message = Message(
        role="assistant", content=[TextContent(text="I see an OpenHands logo!")]
    )
    mock_event = MessageEvent(source="agent", llm_message=mock_message)

    # Mock conversation.run to add the event
    async def mock_run(fn):
        fn()
        mock_conversation.state.events.append(mock_event)

    with patch("asyncio.to_thread", side_effect=mock_run):
        # Create request with both text and image
        # Note: ACP ImageContentBlock uses 'data' field which can be a URL
        # or base64 data
        request = PromptRequest(
            sessionId=session_id,
            prompt=[
                TextContentBlock(type="text", text="What do you see in this image?"),
                ImageContentBlock(
                    type="image",
                    data="https://example.com/image.png",
                    mimeType="image/png",
                ),
            ],
        )
        response = await acp_agent.prompt(request)

        assert response.stopReason == "end_turn"

        # Verify sessionUpdate was called
        mock_connection.sessionUpdate.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_reports_image_capability(acp_agent):
    """Test that initialization reports image capability."""
    from acp.schema import Implementation

    request = InitializeRequest(
        protocolVersion=1,
        clientInfo=Implementation(name="test-client", version="1.0.0"),
    )

    with patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load:
        mock_agent = MagicMock()
        mock_load.return_value = mock_agent

        response = await acp_agent.initialize(request)

        # Verify image capability is enabled
        assert response.agentCapabilities.promptCapabilities.image is True


@pytest.mark.asyncio
async def test_new_session_with_mcp_servers(acp_agent, tmp_path):
    """Test creating a new session with MCP servers transforms env correctly."""
    from acp.schema import StdioMcpServer

    # Create MCP server with env as array (ACP format)
    mcp_server = StdioMcpServer(
        name="test-server",
        command="/usr/bin/node",
        args=["server.js"],
        env=[],  # Empty array - should be converted to {}
    )

    request = NewSessionRequest(cwd=str(tmp_path), mcpServers=[mcp_server])

    with (
        patch("openhands_cli.acp_impl.agent.load_agent_specs") as mock_load,
        patch("openhands_cli.acp_impl.agent.Conversation") as mock_conv,
    ):
        mock_agent = MagicMock()
        mock_agent.llm.model = "test-model"
        mock_load.return_value = mock_agent

        mock_conversation = MagicMock()
        mock_conv.return_value = mock_conversation

        response = await acp_agent.newSession(request)

        # Verify session was created
        assert response.sessionId is not None

        # Verify load_agent_specs was called with transformed MCP servers dict
        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args[1]
        assert "mcp_servers" in call_kwargs
        mcp_servers_dict = call_kwargs["mcp_servers"]

        # Verify it's a dict in Agent format (not ACP Pydantic models)
        assert isinstance(mcp_servers_dict, dict)
        assert "test-server" in mcp_servers_dict
        assert mcp_servers_dict["test-server"]["command"] == "/usr/bin/node"
        assert mcp_servers_dict["test-server"]["args"] == ["server.js"]
        assert mcp_servers_dict["test-server"]["env"] == {}  # Transformed from []
        assert "name" not in mcp_servers_dict["test-server"]  # Name used as key
