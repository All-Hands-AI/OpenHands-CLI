from uuid import UUID

from prompt_toolkit import HTML, print_formatted_text

from openhands.sdk import Agent, BaseConversation, Conversation, Workspace
from openhands.sdk.security.confirmation_policy import (
    AlwaysConfirm,
    ConfirmRisky,
)
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk

# Register tools on import
from openhands.tools.file_editor import FileEditorTool  # noqa: F401
from openhands.tools.task_tracker import TaskTrackerTool  # noqa: F401
from openhands.tools.terminal import TerminalTool  # noqa: F401
from openhands_cli.locations import CONVERSATIONS_DIR, WORK_DIR
from openhands_cli.tui.settings.settings_screen import SettingsScreen
from openhands_cli.tui.settings.store import AgentStore
from openhands_cli.tui.visualizer import CLIVisualizer
from openhands_cli.user_actions.types import ConfirmationMode


class MissingAgentSpec(Exception):
    """Raised when agent specification is not found or invalid."""

    pass


def load_agent_specs(
    conversation_id: str | None = None,
) -> Agent:
    agent_store = AgentStore()
    agent = agent_store.load(session_id=conversation_id)
    if not agent:
        raise MissingAgentSpec(
            "Agent specification not found. Please configure your agent settings."
        )
    return agent


def verify_agent_exists_or_setup_agent() -> Agent:
    """Verify agent specs exists by attempting to load it."""
    settings_screen = SettingsScreen()
    try:
        agent = load_agent_specs()
        return agent
    except MissingAgentSpec:
        # For first-time users, show the full settings flow with choice
        # between basic/advanced
        settings_screen.configure_settings(first_time=True)

    # Try once again after settings setup attempt
    return load_agent_specs()


def setup_conversation(
    conversation_id: UUID,
    confirmation_mode: ConfirmationMode | None = None,
) -> BaseConversation:
    """
    Setup the conversation with agent.

    Args:
        conversation_id: conversation ID to use. If not provided, a random UUID
            will be generated.
        confirmation_mode: Confirmation mode to use. Options: None, "always", "llm"

    Raises:
        MissingAgentSpec: If agent specification is not found or invalid.
    """

    print_formatted_text(HTML("<white>Initializing agent...</white>"))

    agent = load_agent_specs(str(conversation_id))

    # Create conversation - agent context is now set in AgentStore.load()
    conversation: BaseConversation = Conversation(
        agent=agent,
        workspace=Workspace(working_dir=WORK_DIR),
        # Conversation will add /<conversation_id> to this path
        persistence_dir=CONVERSATIONS_DIR,
        conversation_id=conversation_id,
        visualizer=CLIVisualizer,
    )

    # Handle confirmation mode
    if confirmation_mode == "always":
        # Always ask for confirmation
        conversation.set_security_analyzer(LLMSecurityAnalyzer())
        conversation.set_confirmation_policy(AlwaysConfirm())
    elif confirmation_mode == "llm":
        # Use LLM-based risk analysis, only confirm high-risk actions
        conversation.set_security_analyzer(LLMSecurityAnalyzer())
        conversation.set_confirmation_policy(ConfirmRisky(threshold=SecurityRisk.HIGH))
    # When confirmation_mode is None, use default behavior
    # (no security analyzer, no confirmation)

    print_formatted_text(
        HTML(f"<green>✓ Agent initialized with model: {agent.llm.model}</green>")
    )
    return conversation
