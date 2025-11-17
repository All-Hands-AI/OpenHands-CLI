"""Tests for ACP session management."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openhands_acp.session import SessionManager


@pytest.fixture
def temp_sessions_dir():
    """Create a temporary directory for session storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def session_manager(temp_sessions_dir):
    """Create a session manager."""
    return SessionManager(temp_sessions_dir)


@pytest.mark.asyncio
async def test_create_session(session_manager):
    """Test creating a new session."""
    session_id = "test-session-123"
    working_dir = "/test/path"
    mcp_servers = []
    
    session_data = await session_manager.create_session(
        session_id=session_id,
        working_directory=working_dir,
        mcp_servers=mcp_servers,
    )
    
    assert session_data["session_id"] == session_id
    assert session_data["working_directory"] == working_dir
    assert "created_at" in session_data
    assert session_data["conversation_history"] == []


@pytest.mark.asyncio
async def test_load_session_not_found(session_manager):
    """Test loading a non-existent session."""
    result = await session_manager.load_session(
        session_id="non-existent",
        working_directory="/test/path",
        mcp_servers=[],
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_load_session_success(session_manager, temp_sessions_dir):
    """Test loading an existing session."""
    session_id = "existing-session"
    session_data = {
        "session_id": session_id,
        "created_at": "2023-01-01T00:00:00",
        "working_directory": "/old/path",
        "mcp_servers": [],
        "conversation_history": [{"type": "user", "content": "Hello"}],
        "metadata": {},
    }
    
    # Create session file
    session_file = Path(temp_sessions_dir) / f"{session_id}.json"
    with open(session_file, 'w') as f:
        json.dump(session_data, f)
    
    # Load session
    loaded_data = await session_manager.load_session(
        session_id=session_id,
        working_directory="/new/path",
        mcp_servers=[],
    )
    
    assert loaded_data is not None
    assert loaded_data["session_id"] == session_id
    assert loaded_data["working_directory"] == "/new/path"  # Updated
    assert "last_loaded_at" in loaded_data


@pytest.mark.asyncio
async def test_add_message_to_session(session_manager):
    """Test adding a message to session history."""
    session_id = "test-session"
    
    # Create session first
    await session_manager.create_session(
        session_id=session_id,
        working_directory="/test/path",
        mcp_servers=[],
    )
    
    # Add message
    await session_manager.add_message_to_session(
        session_id=session_id,
        message_type="user",
        content="Hello, world!",
        metadata={"source": "test"},
    )
    
    # Verify message was added
    history = await session_manager.get_conversation_history(session_id)
    assert len(history) == 1
    assert history[0]["type"] == "user"
    assert history[0]["content"] == "Hello, world!"
    assert history[0]["metadata"]["source"] == "test"


@pytest.mark.asyncio
async def test_get_conversation_history_empty(session_manager):
    """Test getting conversation history for non-existent session."""
    history = await session_manager.get_conversation_history("non-existent")
    assert history == []


@pytest.mark.asyncio
async def test_update_session_metadata(session_manager):
    """Test updating session metadata."""
    session_id = "test-session"
    
    # Create session first
    await session_manager.create_session(
        session_id=session_id,
        working_directory="/test/path",
        mcp_servers=[],
    )
    
    # Update metadata
    await session_manager.update_session_metadata(
        session_id=session_id,
        metadata={"key1": "value1", "key2": "value2"},
    )
    
    # Verify metadata was updated
    session_data = await session_manager._load_session_data(session_id)
    assert session_data["metadata"]["key1"] == "value1"
    assert session_data["metadata"]["key2"] == "value2"


@pytest.mark.asyncio
async def test_delete_session(session_manager):
    """Test deleting a session."""
    session_id = "test-session"
    
    # Create session first
    await session_manager.create_session(
        session_id=session_id,
        working_directory="/test/path",
        mcp_servers=[],
    )
    
    # Verify session exists
    session_data = await session_manager._load_session_data(session_id)
    assert session_data is not None
    
    # Delete session
    result = await session_manager.delete_session(session_id)
    assert result is True
    
    # Verify session is gone
    session_data = await session_manager._load_session_data(session_id)
    assert session_data is None


@pytest.mark.asyncio
async def test_delete_session_not_found(session_manager):
    """Test deleting a non-existent session."""
    result = await session_manager.delete_session("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_list_sessions(session_manager):
    """Test listing all sessions."""
    # Create multiple sessions
    session_ids = ["session-1", "session-2", "session-3"]
    
    for session_id in session_ids:
        await session_manager.create_session(
            session_id=session_id,
            working_directory="/test/path",
            mcp_servers=[],
        )
        
        # Add some messages to vary message counts
        for i in range(len(session_id)):  # Different number of messages
            await session_manager.add_message_to_session(
                session_id=session_id,
                message_type="user",
                content=f"Message {i}",
            )
    
    # List sessions
    sessions = await session_manager.list_sessions()
    
    assert len(sessions) == 3
    
    # Verify session summaries
    session_ids_found = {s["session_id"] for s in sessions}
    assert session_ids_found == set(session_ids)
    
    # Verify sessions are sorted by creation time (newest first)
    creation_times = [s["created_at"] for s in sessions]
    assert creation_times == sorted(creation_times, reverse=True)


def test_serialize_mcp_server(session_manager):
    """Test MCP server serialization."""
    mock_server = MagicMock()
    mock_server.name = "test-server"
    mock_server.uri = "http://example.com"
    
    serialized = session_manager._serialize_mcp_server(mock_server)
    
    assert serialized["name"] == "test-server"
    assert serialized["uri"] == "http://example.com"