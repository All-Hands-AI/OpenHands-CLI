"""Integration tests for OpenHands ACP implementation."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from openhands_acp.main import run_acp_agent


@pytest.mark.asyncio
async def test_acp_agent_startup():
    """Test that the ACP agent can start up without errors."""
    # Mock the stdio streams
    mock_read_stream = AsyncMock()
    mock_write_stream = AsyncMock()
    
    # Mock the agent run method to avoid infinite loop
    async def mock_run_agent(agent):
        # Just verify the agent was created properly
        assert agent is not None
        assert hasattr(agent, '_session_manager')
        assert hasattr(agent, '_bridge')
    
    mock_read_stream.run_agent = mock_run_agent
    
    with patch('openhands_acp.main.stdio_streams') as mock_stdio:
        mock_stdio.return_value.__aenter__.return_value = (mock_read_stream, mock_write_stream)
        
        # This should complete without errors
        await run_acp_agent()


def test_main_entry_point():
    """Test that the main entry point can be imported and called."""
    from openhands_acp.main import main
    
    # Just verify the function exists and is callable
    assert callable(main)


@pytest.mark.asyncio
async def test_agent_protocol_flow():
    """Test a basic ACP protocol flow."""
    from openhands_acp.agent import OpenHandsACPAgent
    from acp import InitializeRequest, NewSessionRequest
    from acp.schema import Implementation
    
    # Create mock connection
    mock_connection = AsyncMock()
    
    # Create agent
    agent = OpenHandsACPAgent(mock_connection)
    
    # Test initialization
    init_request = InitializeRequest(
        protocolVersion=1,
        clientInfo=Implementation(name="test-client", version="1.0.0"),
    )
    
    init_response = await agent.initialize(init_request)
    assert init_response.protocolVersion == 1
    assert init_response.agentInfo.name == "openhands-acp"
    
    # Test session creation
    session_request = NewSessionRequest(cwd="/test/path")
    
    with patch.object(agent._session_manager, 'create_session') as mock_create:
        mock_create.return_value = {"session_id": "test-session"}
        
        session_response = await agent.newSession(session_request)
        assert session_response.sessionId is not None