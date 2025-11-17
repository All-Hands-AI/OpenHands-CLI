"""
OpenHands ACP Agent Implementation.

This module implements the Agent Client Protocol (ACP) interface for OpenHands,
allowing it to work with ACP-compatible editors like Zed.
"""

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from acp import (
    Agent,
    AgentSideConnection,
    AuthenticateRequest,
    AuthenticateResponse,
    CancelNotification,
    InitializeRequest,
    InitializeResponse,
    LoadSessionRequest,
    LoadSessionResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    session_notification,
    text_block,
    update_agent_message,
    PROTOCOL_VERSION,
)
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    FileSystemCapability,
    Implementation,
    PromptCapabilities,
    StopReason,
)

from .bridge import OpenHandsBridge
from .session import SessionManager


logger = logging.getLogger(__name__)


class OpenHandsACPAgent(Agent):
    """
    OpenHands Agent Client Protocol implementation.
    
    This class implements the ACP Agent interface and bridges communication
    between ACP-compatible editors and the OpenHands agent system.
    """

    def __init__(self, conn: AgentSideConnection) -> None:
        """Initialize the OpenHands ACP Agent.
        
        Args:
            conn: The ACP connection to the client (editor)
        """
        self._conn = conn
        self._session_manager = SessionManager()
        self._bridge: Optional[OpenHandsBridge] = None
        self._working_directory: Optional[str] = None
        
        logger.info("OpenHands ACP Agent initialized")

    async def _send_agent_message(self, session_id: str, content: Any) -> None:
        """Send an agent message to the client.
        
        Args:
            session_id: The session ID
            content: The message content
        """
        update = (
            content 
            if isinstance(content, AgentMessageChunk) 
            else update_agent_message(content)
        )
        await self._conn.sessionUpdate(session_notification(session_id, update))

    async def initialize(self, params: InitializeRequest) -> InitializeResponse:
        """Initialize the ACP connection and negotiate capabilities.
        
        Args:
            params: The initialization request parameters
            
        Returns:
            The initialization response with agent capabilities
        """
        logger.info(
            "Received initialize request from client: %s v%s", 
            params.clientInfo.name if params.clientInfo else "Unknown",
            params.clientInfo.version if params.clientInfo else "Unknown"
        )
        
        # Validate protocol version
        if params.protocolVersion != PROTOCOL_VERSION:
            logger.warning(
                "Client requested protocol version %d, we support %d",
                params.protocolVersion,
                PROTOCOL_VERSION
            )
        
        # Define our capabilities
        agent_capabilities = AgentCapabilities(
            loadSession=True,  # We support session loading
            promptCapabilities=PromptCapabilities(
                image=False,  # TODO: Add image support later
                audio=False,  # TODO: Add audio support later
                embeddedContext=True,  # We support embedded context
            ),
            # MCP capabilities can be added later if needed
        )
        
        agent_info = Implementation(
            name="openhands-acp",
            title="OpenHands ACP Agent",
            version="1.0.6",
        )
        
        return InitializeResponse(
            protocolVersion=PROTOCOL_VERSION,
            agentCapabilities=agent_capabilities,
            agentInfo=agent_info,
            authMethods=[],  # No authentication required for now
        )

    async def authenticate(
        self, params: AuthenticateRequest
    ) -> Optional[AuthenticateResponse]:
        """Handle authentication request.
        
        Args:
            params: The authentication request parameters
            
        Returns:
            Authentication response or None if not supported
        """
        logger.info("Received authenticate request: %s", params.methodId)
        # For now, we don't require authentication
        return AuthenticateResponse()

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session.
        
        Args:
            params: The new session request parameters
            
        Returns:
            The new session response with session ID
        """
        logger.info("Creating new session with cwd: %s", params.cwd)
        
        # Store working directory
        self._working_directory = params.cwd
        
        # Create new session
        session_id = str(uuid.uuid4())
        session = await self._session_manager.create_session(
            session_id=session_id,
            working_directory=params.cwd,
            mcp_servers=params.mcpServers or [],
        )
        
        # Initialize OpenHands bridge for this session
        if not self._bridge:
            self._bridge = OpenHandsBridge(
                connection=self._conn,
                working_directory=params.cwd,
            )
        
        logger.info("Created new session: %s", session_id)
        return NewSessionResponse(sessionId=session_id)

    async def loadSession(
        self, params: LoadSessionRequest
    ) -> Optional[LoadSessionResponse]:
        """Load an existing conversation session.
        
        Args:
            params: The load session request parameters
            
        Returns:
            Load session response or None if session not found
        """
        logger.info("Loading session: %s", params.sessionId)
        
        # Store working directory
        self._working_directory = params.cwd
        
        # Try to load the session
        session = await self._session_manager.load_session(
            session_id=params.sessionId,
            working_directory=params.cwd,
            mcp_servers=params.mcpServers or [],
        )
        
        if not session:
            logger.warning("Session not found: %s", params.sessionId)
            return None
        
        # Initialize OpenHands bridge for this session
        if not self._bridge:
            self._bridge = OpenHandsBridge(
                connection=self._conn,
                working_directory=params.cwd,
            )
        
        # Replay conversation history
        await self._replay_session_history(params.sessionId, session)
        
        logger.info("Loaded session: %s", params.sessionId)
        return LoadSessionResponse()

    async def prompt(self, params: PromptRequest) -> PromptResponse:
        """Process a user prompt and generate a response.
        
        Args:
            params: The prompt request parameters
            
        Returns:
            The prompt response
        """
        logger.info("Processing prompt for session: %s", params.sessionId)
        
        if not self._bridge:
            logger.error("No bridge initialized for session")
            return PromptResponse(stopReason=StopReason.error)
        
        try:
            # Process the prompt through OpenHands
            stop_reason = await self._bridge.process_prompt(
                session_id=params.sessionId,
                content_blocks=params.content,
            )
            
            return PromptResponse(stopReason=stop_reason)
            
        except Exception as e:
            logger.error("Error processing prompt: %s", e)
            return PromptResponse(stopReason=StopReason.error)

    async def cancel(self, params: CancelNotification) -> None:
        """Cancel an ongoing operation.
        
        Args:
            params: The cancel notification parameters
        """
        logger.info("Cancelling operation for session: %s", params.sessionId)
        
        if self._bridge:
            await self._bridge.cancel_operation(params.sessionId)

    async def _replay_session_history(
        self, session_id: str, session: Dict[str, Any]
    ) -> None:
        """Replay the conversation history for a loaded session.
        
        Args:
            session_id: The session ID
            session: The session data
        """
        # TODO: Implement session history replay
        # This would involve sending session_update notifications
        # for each message in the conversation history
        logger.info("Replaying session history for: %s", session_id)
        
        # For now, just send a welcome message
        await self._send_agent_message(
            session_id,
            text_block("Session loaded successfully. How can I help you?")
        )