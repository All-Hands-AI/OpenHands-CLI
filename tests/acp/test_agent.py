"""Tests for the OpenHands ACP Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from acp import InitializeRequest, NewSessionRequest, PromptRequest
from acp.schema import AgentCapabilities, TextContentBlock, Implementation

from openhands_acp.agent import OpenHandsACPAgent


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
async def test_initialize(acp_agent):
    """Test agent initialization."""
    request = InitializeRequest(
        protocolVersion=1,
        clientInfo=Implementation(name="test-client", version="1.0.0"),
    )
    
    response = await acp_agent.initialize(request)
    
    assert response.protocolVersion == 1
    assert response.agentInfo.name == "openhands-acp"
    assert response.agentInfo.title == "OpenHands ACP Agent"
    assert isinstance(response.agentCapabilities, AgentCapabilities)


@pytest.mark.asyncio
async def test_authenticate(acp_agent):
    """Test authentication."""
    from acp import AuthenticateRequest
    
    request = AuthenticateRequest(methodId="test-method")
    response = await acp_agent.authenticate(request)
    
    assert response is not None


@pytest.mark.asyncio
async def test_new_session(acp_agent):
    """Test creating a new session."""
    request = NewSessionRequest(cwd="/test/path")
    
    with patch.object(acp_agent._session_manager, 'create_session') as mock_create:
        mock_create.return_value = {"session_id": "test-session"}
        
        response = await acp_agent.newSession(request)
        
        assert response.sessionId is not None
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_load_session_not_found(acp_agent):
    """Test loading a non-existent session."""
    from acp import LoadSessionRequest
    
    request = LoadSessionRequest(sessionId="non-existent", cwd="/test/path")
    
    with patch.object(acp_agent._session_manager, 'load_session') as mock_load:
        mock_load.return_value = None
        
        response = await acp_agent.loadSession(request)
        
        assert response is None


@pytest.mark.asyncio
async def test_load_session_success(acp_agent):
    """Test loading an existing session."""
    from acp import LoadSessionRequest
    
    request = LoadSessionRequest(sessionId="existing-session", cwd="/test/path")
    
    with patch.object(acp_agent._session_manager, 'load_session') as mock_load:
        mock_load.return_value = {"session_id": "existing-session"}
        
        response = await acp_agent.loadSession(request)
        
        assert response is not None


@pytest.mark.asyncio
async def test_prompt_no_bridge(acp_agent):
    """Test prompt processing without bridge."""
    content_blocks = [MagicMock(type="text", text="Hello")]
    request = PromptRequest(sessionId="test-session", content=content_blocks)
    
    response = await acp_agent.prompt(request)
    
    from acp.schema import StopReason
    assert response.stopReason == StopReason.error


@pytest.mark.asyncio
async def test_prompt_with_bridge(acp_agent, mock_connection):
    """Test prompt processing with bridge."""
    from acp.schema import StopReason
    
    content_blocks = [MagicMock(type="text", text="Hello")]
    request = PromptRequest(sessionId="test-session", content=content_blocks)
    
    # Mock the bridge
    mock_bridge = AsyncMock()
    mock_bridge.process_prompt.return_value = StopReason.endTurn
    acp_agent._bridge = mock_bridge
    
    response = await acp_agent.prompt(request)
    
    assert response.stopReason == StopReason.endTurn
    mock_bridge.process_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_cancel(acp_agent):
    """Test cancelling an operation."""
    from acp import CancelNotification
    
    notification = CancelNotification(sessionId="test-session")
    
    # Mock the bridge
    mock_bridge = AsyncMock()
    acp_agent._bridge = mock_bridge
    
    await acp_agent.cancel(notification)
    
    mock_bridge.cancel_operation.assert_called_once_with("test-session")