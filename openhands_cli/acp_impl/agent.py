"""OpenHands Agent Client Protocol (ACP) server implementation."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from acp import (
    Agent as ACPAgent,
    AgentSideConnection,
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    SessionNotification,
    stdio_streams,
)
from acp.schema import (
    AgentCapabilities,
    AuthenticateRequest,
    AuthenticateResponse,
    CancelNotification,
    ContentBlock1,
    LoadSessionRequest,
    McpCapabilities,
    PromptCapabilities,
    SessionUpdate1,
    SessionUpdate2,
    SetSessionModelRequest,
    SetSessionModelResponse,
    SetSessionModeRequest,
    SetSessionModeResponse,
)

from openhands.sdk import (
    BaseConversation,
    Conversation,
    Message,
    TextContent,
    Workspace,
)
from openhands.sdk.event import Event
from openhands.sdk.event.llm_convertible.message import MessageEvent
from openhands_cli.acp_impl.utils import (
    EventSubscriber,
    convert_acp_prompt_to_message_content,
    transform_acp_mcp_servers_to_agent_format,
)
from openhands_cli.locations import CONVERSATIONS_DIR
from openhands_cli.setup import MissingAgentSpec, load_agent_specs


logger = logging.getLogger(__name__)


class OpenHandsACPAgent(ACPAgent):
    """OpenHands Agent Client Protocol implementation."""

    def __init__(self, conn: AgentSideConnection):
        """Initialize the OpenHands ACP agent.

        Args:
            conn: ACP connection for sending notifications
        """
        self._conn = conn
        # session_id -> conversation
        self._sessions: dict[str, BaseConversation] = {}

        logger.info("OpenHands ACP Agent initialized")

    async def initialize(self, params: InitializeRequest) -> InitializeResponse:
        """Initialize the ACP protocol."""
        logger.info(f"Initializing ACP with protocol version: {params.protocolVersion}")

        # Check if agent is configured
        try:
            load_agent_specs()
            auth_methods = []
            logger.info("Agent configured, no authentication required")
        except MissingAgentSpec:
            # Agent not configured - this shouldn't happen in production
            # but we'll return empty auth methods for now
            auth_methods = []
            logger.warning("Agent not configured - users should run 'openhands' first")

        return InitializeResponse(
            protocolVersion=params.protocolVersion,
            authMethods=auth_methods,
            agentCapabilities=AgentCapabilities(
                loadSession=True,
                mcpCapabilities=McpCapabilities(http=True, sse=True),
                promptCapabilities=PromptCapabilities(
                    audio=False,
                    embeddedContext=False,
                    image=True,  # Enable image support
                ),
            ),
        )

    async def authenticate(
        self, params: AuthenticateRequest
    ) -> AuthenticateResponse | None:
        """Authenticate the client (no-op for now)."""
        logger.info(f"Authentication requested with method: {params.methodId}")
        return AuthenticateResponse()

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())

        try:
            # Transform ACP MCP servers to Agent format
            mcp_servers_dict = None
            if params.mcpServers:
                mcp_servers_dict = transform_acp_mcp_servers_to_agent_format(
                    params.mcpServers
                )

            # Load agent from CLI settings
            agent = load_agent_specs(
                conversation_id=session_id, mcp_servers=mcp_servers_dict
            )
            logger.info(f"Loaded agent with model: {agent.llm.model}")

            # Validate working directory
            working_dir = params.cwd or str(Path.cwd())
            working_path = Path(working_dir)

            logger.info(f"Using working directory: {working_dir}")

            # Create directory if it doesn't exist
            if not working_path.exists():
                logger.warning(
                    f"Working directory {working_dir} doesn't exist, creating it"
                )
                working_path.mkdir(parents=True, exist_ok=True)

            if not working_path.is_dir():
                raise ValueError(
                    f"Working directory path is not a directory: {working_dir}"
                )

            workspace = Workspace(working_dir=str(working_path))

            # Create event subscriber for streaming updates
            subscriber = EventSubscriber(session_id, self._conn)

            # Get the current event loop to use in the callback
            loop = asyncio.get_event_loop()

            # Create a synchronous wrapper for the async subscriber
            def sync_callback(event: Event) -> None:
                """Synchronous wrapper that schedules async event handling."""
                # Schedule the coroutine on the event loop thread-safely
                asyncio.run_coroutine_threadsafe(subscriber(event), loop)

            # Create conversation using CLI's persistence directory
            # Pass the callback at creation time
            conversation = Conversation(
                agent=agent,
                workspace=workspace,
                persistence_dir=CONVERSATIONS_DIR,
                conversation_id=UUID(session_id),
                callbacks=[sync_callback],
            )

            # Store conversation
            self._sessions[session_id] = conversation

            logger.info(f"Created new session {session_id}")

            return NewSessionResponse(sessionId=session_id)

        except MissingAgentSpec as e:
            logger.error(f"Agent not configured: {e}")
            raise ValueError(
                "Agent not configured. Please run 'openhands' to configure "
                "the agent first."
            )
        except Exception as e:
            logger.error(f"Failed to create new session: {e}", exc_info=True)
            raise

    async def prompt(self, params: PromptRequest) -> PromptResponse:
        """Handle a prompt request."""
        session_id = params.sessionId

        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        conversation = self._sessions[session_id]

        # Convert ACP prompt format to OpenHands message content
        message_content = convert_acp_prompt_to_message_content(params.prompt)

        if not message_content:
            return PromptResponse(stopReason="end_turn")

        try:
            # Send the message with potentially multiple content types
            # (text + images)
            message = Message(role="user", content=message_content)
            conversation.send_message(message)

            # Run the conversation asynchronously
            # Callbacks are already set up when conversation was created
            await asyncio.to_thread(conversation.run)

            # Return the final response
            return PromptResponse(stopReason="end_turn")

        except Exception as e:
            logger.error(f"Error processing prompt: {e}", exc_info=True)
            # Send error notification
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=SessionUpdate2(
                        sessionUpdate="agent_message_chunk",
                        content=ContentBlock1(type="text", text=f"Error: {str(e)}"),
                    ),
                )
            )
            return PromptResponse(stopReason="end_turn")

    async def cancel(self, params: CancelNotification) -> None:
        """Cancel the current operation."""
        logger.info(f"Cancel requested for session: {params.sessionId}")

        if params.sessionId in self._sessions:
            conversation = self._sessions[params.sessionId]
            # Pause the conversation
            conversation.pause()

    async def loadSession(self, params: LoadSessionRequest) -> None:
        """Load an existing session and replay conversation history."""
        session_id = params.sessionId
        logger.info(f"Loading session: {session_id}")

        try:
            # Check if session exists
            if session_id not in self._sessions:
                raise ValueError(f"Session not found: {session_id}")

            conversation = self._sessions[session_id]

            # Stream conversation history to client
            logger.info("Streaming conversation history to client")
            for event in conversation.state.events:
                if isinstance(event, MessageEvent):
                    # Convert MessageEvent to ACP session update
                    if event.source == "user":
                        # Stream user message
                        text_content = ""
                        for content in event.llm_message.content:
                            if isinstance(content, TextContent):
                                text_content += content.text

                        if text_content.strip():
                            await self._conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=session_id,
                                    update=SessionUpdate1(
                                        sessionUpdate="user_message_chunk",
                                        content=ContentBlock1(
                                            type="text", text=text_content
                                        ),
                                    ),
                                )
                            )

                    elif event.source == "agent":
                        # Stream agent message
                        text_content = ""
                        for content in event.llm_message.content:
                            if isinstance(content, TextContent):
                                text_content += content.text

                        if text_content.strip():
                            await self._conn.sessionUpdate(
                                SessionNotification(
                                    sessionId=session_id,
                                    update=SessionUpdate2(
                                        sessionUpdate="agent_message_chunk",
                                        content=ContentBlock1(
                                            type="text", text=text_content
                                        ),
                                    ),
                                )
                            )

            logger.info(f"Successfully loaded session {session_id}")

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}", exc_info=True)
            raise

    async def setSessionMode(
        self, params: SetSessionModeRequest
    ) -> SetSessionModeResponse | None:
        """Set session mode (no-op for now)."""
        logger.info(f"Set session mode requested: {params.sessionId}")
        return SetSessionModeResponse()

    async def setSessionModel(
        self, params: SetSessionModelRequest
    ) -> SetSessionModelResponse | None:
        """Set session model (no-op for now)."""
        logger.info(f"Set session model requested: {params.sessionId}")
        return SetSessionModelResponse()

    async def extMethod(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Extension method (not supported)."""
        logger.info(f"Extension method '{method}' requested with params: {params}")
        return {"error": "extMethod not supported"}

    async def extNotification(self, method: str, params: dict[str, Any]) -> None:
        """Extension notification (no-op for now)."""
        logger.info(f"Extension notification '{method}' received with params: {params}")


async def run_acp_server() -> None:
    """Run the OpenHands ACP server."""
    logger.info("Starting OpenHands ACP server...")

    reader, writer = await stdio_streams()

    def create_agent(conn: AgentSideConnection) -> OpenHandsACPAgent:
        return OpenHandsACPAgent(conn)

    AgentSideConnection(create_agent, writer, reader)

    # Keep the server running
    await asyncio.Event().wait()
