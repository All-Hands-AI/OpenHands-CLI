"""
Session Management for ACP Integration.

This module handles session persistence and management for ACP conversations,
including saving and loading conversation history.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from acp.schema import McpServer1


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages ACP session persistence and conversation history.
    
    This class handles the creation, loading, and persistence of ACP sessions,
    including conversation history and session metadata.
    """

    def __init__(self, sessions_dir: Optional[str] = None) -> None:
        """Initialize the session manager.
        
        Args:
            sessions_dir: Directory to store session data (defaults to ~/.openhands/acp_sessions)
        """
        if sessions_dir:
            self._sessions_dir = Path(sessions_dir)
        else:
            self._sessions_dir = Path.home() / ".openhands" / "acp_sessions"
        
        # Create sessions directory if it doesn't exist
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Session manager initialized with sessions dir: %s", self._sessions_dir)

    async def create_session(
        self,
        session_id: str,
        working_directory: str,
        mcp_servers: List[McpServer1],
    ) -> Dict[str, Any]:
        """Create a new session.
        
        Args:
            session_id: The unique session ID
            working_directory: The working directory for the session
            mcp_servers: List of MCP servers for the session
            
        Returns:
            The created session data
        """
        session_data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "working_directory": working_directory,
            "mcp_servers": [self._serialize_mcp_server(server) for server in mcp_servers],
            "conversation_history": [],
            "metadata": {},
        }
        
        # Save session to disk
        await self._save_session(session_id, session_data)
        
        logger.info("Created new session: %s", session_id)
        return session_data

    async def load_session(
        self,
        session_id: str,
        working_directory: str,
        mcp_servers: List[McpServer1],
    ) -> Optional[Dict[str, Any]]:
        """Load an existing session.
        
        Args:
            session_id: The session ID to load
            working_directory: The working directory for the session
            mcp_servers: List of MCP servers for the session
            
        Returns:
            The loaded session data or None if not found
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            logger.warning("Session file not found: %s", session_file)
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Update session with current parameters
            session_data["working_directory"] = working_directory
            session_data["mcp_servers"] = [
                self._serialize_mcp_server(server) for server in mcp_servers
            ]
            session_data["last_loaded_at"] = datetime.utcnow().isoformat()
            
            # Save updated session
            await self._save_session(session_id, session_data)
            
            logger.info("Loaded session: %s", session_id)
            return session_data
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Error loading session %s: %s", session_id, e)
            return None

    async def add_message_to_session(
        self,
        session_id: str,
        message_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a message to the session conversation history.
        
        Args:
            session_id: The session ID
            message_type: The type of message (user, agent, system)
            content: The message content
            metadata: Optional message metadata
        """
        session_data = await self._load_session_data(session_id)
        if not session_data:
            logger.warning("Cannot add message to non-existent session: %s", session_id)
            return
        
        message = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": message_type,
            "content": content,
            "metadata": metadata or {},
        }
        
        session_data["conversation_history"].append(message)
        await self._save_session(session_id, session_data)
        
        logger.debug("Added message to session %s: %s", session_id, message_type)

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The conversation history
        """
        session_data = await self._load_session_data(session_id)
        if not session_data:
            return []
        
        return session_data.get("conversation_history", [])

    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Update session metadata.
        
        Args:
            session_id: The session ID
            metadata: The metadata to update
        """
        session_data = await self._load_session_data(session_id)
        if not session_data:
            logger.warning("Cannot update metadata for non-existent session: %s", session_id)
            return
        
        session_data["metadata"].update(metadata)
        await self._save_session(session_id, session_data)
        
        logger.debug("Updated metadata for session: %s", session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            True if the session was deleted, False if it didn't exist
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return False
        
        try:
            session_file.unlink()
            logger.info("Deleted session: %s", session_id)
            return True
        except OSError as e:
            logger.error("Error deleting session %s: %s", session_id, e)
            return False

    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available sessions.
        
        Returns:
            List of session summaries
        """
        sessions = []
        
        for session_file in self._sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                # Create session summary
                summary = {
                    "session_id": session_data["session_id"],
                    "created_at": session_data["created_at"],
                    "working_directory": session_data["working_directory"],
                    "message_count": len(session_data.get("conversation_history", [])),
                    "last_loaded_at": session_data.get("last_loaded_at"),
                }
                
                sessions.append(summary)
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Error reading session file %s: %s", session_file, e)
                continue
        
        # Sort by creation time (newest first)
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        
        return sessions

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session file path
        """
        return self._sessions_dir / f"{session_id}.json"

    async def _load_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from disk.
        
        Args:
            session_id: The session ID
            
        Returns:
            The session data or None if not found
        """
        session_file = self._get_session_file(session_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Error loading session data %s: %s", session_id, e)
            return None

    async def _save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to disk.
        
        Args:
            session_id: The session ID
            session_data: The session data to save
        """
        session_file = self._get_session_file(session_id)
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Error saving session %s: %s", session_id, e)

    def _serialize_mcp_server(self, server: McpServer1) -> Dict[str, Any]:
        """Serialize an MCP server for storage.
        
        Args:
            server: The MCP server to serialize
            
        Returns:
            The serialized server data
        """
        # TODO: Implement proper MCP server serialization
        # For now, return a placeholder
        return {
            "name": getattr(server, "name", "unknown"),
            "uri": getattr(server, "uri", ""),
        }