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
    RequestPermissionRequest,
    SessionNotification,
    stdio_streams,
)
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AuthenticateRequest,
    AuthenticateResponse,
    CancelNotification,
    Implementation,
    LoadSessionRequest,
    McpCapabilities,
    PermissionOption,
    PromptCapabilities,
    SetSessionModelRequest,
    SetSessionModelResponse,
    SetSessionModeRequest,
    SetSessionModeResponse,
    StopReason,
    TextContentBlock,
    ToolCall,
)

from openhands.sdk import (
    BaseConversation,
    Conversation,
    Message,
    Workspace,
)
from openhands.sdk.conversation.state import (
    ConversationExecutionStatus,
    ConversationState,
)
from openhands.sdk.event import Event
from openhands.sdk.security.confirmation_policy import ConfirmRisky
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands_cli import __version__
from openhands_cli.acp_impl.event import EventSubscriber
from openhands_cli.acp_impl.utils import (
    RESOURCE_SKILL,
    convert_acp_prompt_to_message_content,
    transform_acp_mcp_servers_to_agent_format,
)
from openhands_cli.locations import CONVERSATIONS_DIR, WORK_DIR
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
        # Cache of active conversations to preserve state (pause, confirmation, etc.)
        # across multiple operations on the same session
        self._active_sessions: dict[str, BaseConversation] = {}
        # Track cancellation state per session
        self._cancelled_sessions: set[str] = set()

        logger.info("OpenHands ACP Agent initialized")

    def _get_or_create_conversation(
        self,
        session_id: str,
        working_dir: str | None = None,
        mcp_servers: dict[str, dict[str, Any]] | None = None,
    ) -> BaseConversation:
        """Get an active conversation from cache or create/load it.

        This maintains conversation state (pause, confirmation, etc.) across
        multiple operations on the same session.

        Args:
            session_id: Session/conversation ID (UUID string)
            working_dir: Working directory for workspace (only for new sessions)
            mcp_servers: MCP servers config (only for new sessions)

        Returns:
            Cached or newly created/loaded conversation
        """
        # Check if we already have this conversation active
        if session_id in self._active_sessions:
            logger.debug(f"Using cached conversation for session {session_id}")
            return self._active_sessions[session_id]

        # Create/load new conversation
        logger.debug(f"Creating new conversation for session {session_id}")
        conversation = self._setup_acp_conversation(
            session_id=session_id,
            working_dir=working_dir,
            mcp_servers=mcp_servers,
        )

        # Cache it for future operations
        self._active_sessions[session_id] = conversation
        return conversation

    def _setup_acp_conversation(
        self,
        session_id: str,
        working_dir: str | None = None,
        mcp_servers: dict[str, dict[str, Any]] | None = None,
    ) -> BaseConversation:
        """Set up a conversation for ACP with event streaming support.

        The SDK's Conversation class automatically:
        - Loads from disk if conversation_id exists in persistence_dir
        - Creates a new conversation if it doesn't exist

        Args:
            session_id: Session/conversation ID (UUID string)
            working_dir: Working directory for the workspace. Defaults to WORK_DIR.
            mcp_servers: Optional MCP servers configuration

        Returns:
            Configured conversation that's either loaded from disk or newly created

        Raises:
            MissingAgentSpec: If agent configuration is missing
        """
        # Load agent specs
        agent = load_agent_specs(
            conversation_id=session_id,
            mcp_servers=mcp_servers,
            skills=[RESOURCE_SKILL],
        )

        # Setup workspace
        working_path = Path(working_dir) if working_dir else Path(WORK_DIR)
        if not working_path.exists():
            logger.warning(f"Working directory {working_path} doesn't exist, creating")
            working_path.mkdir(parents=True, exist_ok=True)
        if not working_path.is_dir():
            raise ValueError(
                f"Working directory path is not a directory: {working_path}"
            )

        # Create event subscriber for streaming updates (ACP-specific)
        subscriber = EventSubscriber(session_id, self._conn)
        loop = asyncio.get_event_loop()

        def sync_callback(event: Event) -> None:
            """Synchronous wrapper that schedules async event handling."""
            asyncio.run_coroutine_threadsafe(subscriber(event), loop)

        # Create conversation with ACP-specific configuration
        conversation = Conversation(
            agent=agent,
            workspace=Workspace(working_dir=str(working_path)),
            persistence_dir=CONVERSATIONS_DIR,
            conversation_id=UUID(session_id),
            callbacks=[sync_callback],
        )

        # Set up security analyzer and confirmation policy
        conversation.set_security_analyzer(LLMSecurityAnalyzer())
        conversation.set_confirmation_policy(ConfirmRisky(threshold=SecurityRisk.HIGH))

        return conversation

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
                    embeddedContext=True,
                    image=True,
                ),
            ),
            agentInfo=Implementation(
                name="OpenHands CLI ACP Agent",
                version=__version__,
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

            # Validate working directory
            working_dir = params.cwd or str(Path.cwd())
            logger.info(f"Using working directory: {working_dir}")

            # Create conversation and cache it for future operations
            # This reuses the same pattern as openhands --resume
            conversation = self._get_or_create_conversation(
                session_id=session_id,
                working_dir=working_dir,
                mcp_servers=mcp_servers_dict,
            )

            logger.info(
                f"Created new session {session_id} with model: "
                f"{conversation.agent.llm.model}"  # type: ignore[attr-defined]
            )

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
        """Handle a prompt request.

        Per ACP spec: Runs the agent until completion or a stop condition is met.
        Returns appropriate stopReason based on why the turn ended.

        This method handles the confirmation loop if confirmation policy is active.
        """
        session_id = params.sessionId

        try:
            # Validate session ID
            if session_id not in self._active_sessions:
                raise ValueError(f"Unknown session: {session_id}")

            # Clear cancellation state for this session (new prompt turn)
            self._cancelled_sessions.discard(session_id)

            # Get conversation from active sessions
            conversation = self._active_sessions[session_id]

            # Convert ACP prompt format to OpenHands message content
            message_content = convert_acp_prompt_to_message_content(params.prompt)

            if not message_content:
                return PromptResponse(stopReason="end_turn")

            # Send the message with potentially multiple content types
            # (text + images)
            message = Message(role="user", content=message_content)
            conversation.send_message(message)

            # Run conversation with confirmation handling loop
            stop_reason = await self._run_with_confirmations(session_id, conversation)
            return PromptResponse(stopReason=stop_reason)

        except ValueError as e:
            # Re-raise ValueError for invalid session IDs
            logger.error(f"Error processing prompt: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error processing prompt: {e}", exc_info=True)
            # Send error notification
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=AgentMessageChunk(
                        sessionUpdate="agent_message_chunk",
                        content=TextContentBlock(type="text", text=f"Error: {str(e)}"),
                    ),
                )
            )
            # Check if error was due to cancellation
            if session_id in self._cancelled_sessions:
                return PromptResponse(stopReason="cancelled")
            return PromptResponse(stopReason="end_turn")

    async def _run_with_confirmations(
        self, session_id: str, conversation: BaseConversation
    ) -> StopReason:
        """Run the conversation with confirmation handling loop.

        Args:
            session_id: The session ID
            conversation: The conversation to run

        Returns:
            Stop reason (one of: end_turn, max_tokens, max_turn_requests,
            refusal, cancelled)
        """

        # Handle resumed conversation waiting for confirmation
        if (
            conversation.state.execution_status
            == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            should_continue = await self._handle_acp_confirmation(
                session_id, conversation
            )
            if not should_continue:
                return self._determine_stop_reason(session_id, conversation)

        # Main confirmation loop
        while True:
            # Check cancellation before running
            if session_id in self._cancelled_sessions:
                return "cancelled"

            # Run conversation in thread pool (blocking)
            await asyncio.to_thread(conversation.run)

            status = conversation.state.execution_status

            # Check completion states
            if status == ConversationExecutionStatus.FINISHED:
                return "end_turn"
            elif status == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION:
                should_continue = await self._handle_acp_confirmation(
                    session_id, conversation
                )
                if not should_continue:
                    return self._determine_stop_reason(session_id, conversation)
            elif status in [
                ConversationExecutionStatus.PAUSED,
                ConversationExecutionStatus.STUCK,
                ConversationExecutionStatus.ERROR,
            ]:
                return self._determine_stop_reason(session_id, conversation)
            else:
                return "end_turn"

    async def _handle_acp_confirmation(
        self, session_id: str, conversation: BaseConversation
    ) -> bool:
        """Handle ACP permission request for pending actions.

        Args:
            session_id: The session ID
            conversation: The conversation waiting for confirmation

        Returns:
            True if permission granted, False if denied/cancelled
        """
        pending_actions = ConversationState.get_unmatched_actions(
            conversation.state.events
        )
        if not pending_actions:
            return True

        try:
            # Build permission request
            title = f"Confirm {len(pending_actions)} action(s)"
            logger.info(f"Requesting permission for {len(pending_actions)} actions")

            response = await self._conn.requestPermission(
                RequestPermissionRequest(
                    sessionId=session_id,
                    toolCall=ToolCall(
                        toolCallId=f"confirm-{uuid.uuid4().hex[:8]}",
                        title=title,
                        kind="other",
                        status="pending",
                    ),
                    options=[
                        PermissionOption(
                            optionId="allow_once",
                            kind="allow_once",
                            name="Allow Once",
                        ),
                        PermissionOption(
                            optionId="reject_once",
                            kind="reject_once",
                            name="Reject Once",
                        ),
                    ],
                )
            )

            # Handle response
            if response.outcome.outcome == "cancelled":
                logger.info("Permission cancelled")
                self._cancelled_sessions.add(session_id)
                conversation.pause()
                return False
            elif (
                response.outcome.outcome == "selected"
                and response.outcome.optionId == "allow_once"
            ):
                return True
            else:
                conversation.reject_pending_actions("User rejected the actions")
                return False

        except Exception as e:
            logger.error(f"Error handling confirmation: {e}", exc_info=True)
            conversation.reject_pending_actions("Error processing permission request")
            return False

    def _determine_stop_reason(
        self, session_id: str, conversation: BaseConversation
    ) -> StopReason:
        """Determine the stop reason based on conversation state.

        Args:
            session_id: The session ID
            conversation: The conversation that just finished

        Returns:
            Stop reason (one of: end_turn, max_tokens, max_turn_requests,
            refusal, cancelled)
        """

        # Check if session was cancelled
        if session_id in self._cancelled_sessions:
            self._cancelled_sessions.discard(session_id)
            return "cancelled"

        # Check execution status
        status = conversation.state.execution_status

        if status == ConversationExecutionStatus.PAUSED:
            # If paused and in cancelled set, it was cancelled
            if session_id in self._cancelled_sessions:
                self._cancelled_sessions.discard(session_id)
                return "cancelled"
            # Otherwise it was manually paused (treat as end of turn)
            return "end_turn"

        elif status == ConversationExecutionStatus.STUCK:
            # Stuck detection triggered - treat as max iterations
            return "max_turn_requests"

        elif status == ConversationExecutionStatus.ERROR:
            # Error state - check if it's a refusal or other error
            # For now, treat as end_turn (could be refined)
            return "end_turn"

        elif status == ConversationExecutionStatus.FINISHED:
            # Normal completion
            return "end_turn"

        # Default to end_turn for any other status
        return "end_turn"

    async def cancel(self, params: CancelNotification) -> None:
        """Cancel the current operation.

        Per ACP spec: Agent SHOULD stop all LLM requests and tool invocations
        as soon as possible. The prompt() method will return "cancelled" stopReason.
        """
        logger.info(f"Cancel requested for session: {params.sessionId}")

        try:
            # Mark this session as cancelled
            self._cancelled_sessions.add(params.sessionId)

            # Get active conversation and pause it
            conversation = self._get_or_create_conversation(session_id=params.sessionId)
            # Pause the conversation (stops execution immediately)
            conversation.pause()

            logger.info(f"Successfully cancelled session {params.sessionId}")
        except Exception as e:
            logger.warning(f"Failed to cancel session {params.sessionId}: {e}")

    async def loadSession(self, params: LoadSessionRequest) -> None:
        """Load an existing session and replay conversation history.

        This implements the same logic as 'openhands --resume <session_id>':
        - Uses _setup_acp_conversation which calls the SDK's Conversation constructor
        - The SDK automatically loads from persistence_dir if conversation_id exists
        - Streams the loaded history back to the client

        Per ACP spec (https://agentclientprotocol.com/protocol/session-setup#loading-sessions):
        - Server should load the session state from persistent storage
        - Replay the conversation history to the client via sessionUpdate notifications
        """
        session_id = params.sessionId
        logger.info(f"Loading session: {session_id}")

        try:
            # Validate session ID format
            try:
                UUID(session_id)
            except ValueError:
                raise ValueError(f"Session not found: {session_id}")

            # Get or create conversation (loads from disk if not in cache)
            # The SDK's Conversation class automatically loads from disk if the
            # conversation_id exists in persistence_dir
            conversation = self._get_or_create_conversation(session_id=session_id)

            # Check if there's actually any history to load
            if not conversation.state.events:
                logger.warning(
                    f"Session {session_id} has no history (new or empty session)"
                )
                return

            # Stream conversation history to client by reusing EventSubscriber
            # This ensures consistent event handling with live conversations
            logger.info(
                f"Streaming {len(conversation.state.events)} events from "
                f"conversation history"
            )
            subscriber = EventSubscriber(session_id, self._conn)
            for event in conversation.state.events:
                await subscriber(event)

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
