#!/usr/bin/env python3
"""
Agent chat functionality for OpenHands CLI.
Provides a conversation interface with an AI agent using OpenHands patterns.
"""

import logging
import os
from enum import Enum

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    EventType,
    Message,
    TextContent,
    Tool,
)
from openhands.sdk.event.utils import get_unmatched_actions
from openhands.tools import (
    BashExecutor,
    FileEditorExecutor,
    execute_bash_tool,
    str_replace_editor_tool,
)
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from pydantic import SecretStr

from openhands_cli.listeners.pause_listener import PauseListener, pause_listener
from openhands_cli.tui import (
    CommandCompleter,
    display_help,
    display_welcome,
)

logger = logging.getLogger(__name__)


class AgentSetupError(Exception):
    """Exception raised when agent setup fails."""

    pass


class UserConfirmation(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"


def setup_agent() -> Conversation:
    """
    Setup the agent with environment variables.
    """
    # Get API configuration from environment
    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("LITELLM_MODEL", "gpt-4o-mini")
    base_url = os.getenv("LITELLM_BASE_URL")

    if not api_key:
        print_formatted_text(
            HTML(
                "<red>Error: No API key found. Please set LITELLM_API_KEY or OPENAI_API_KEY environment variable.</red>"
            )
        )
        raise AgentSetupError(
            "No API key found. Please set LITELLM_API_KEY or OPENAI_API_KEY environment variable."
        )

    llm = LLM(
        model=model,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=base_url,
    )

    # Setup tools
    cwd = os.getcwd()
    bash = BashExecutor(working_dir=cwd)
    file_editor = FileEditorExecutor()
    tools: list[Tool] = [
        execute_bash_tool.set_executor(executor=bash),
        str_replace_editor_tool.set_executor(executor=file_editor),
    ]

    # Create agent
    agent = Agent(llm=llm, tools=tools)

    # Setup conversation with callback
    def conversation_callback(event: EventType) -> None:
        logger.debug(f"Conversation event: {str(event)[:200]}...")

    conversation = Conversation(agent=agent, callbacks=[conversation_callback])

    # Check for confirmation mode
    confirmation_mode = os.getenv("CONFIRMATION_MODE", "").lower() in ("true", "1")
    if confirmation_mode:
        conversation.set_confirmation_mode(True)
        print_formatted_text(
            HTML(
                "<yellow>⚠️  Confirmation mode enabled - you will be asked to approve actions</yellow>"
            )
        )

    print_formatted_text(
        HTML(f"<green>✓ Agent initialized with model: {model}</green>")
    )
    return conversation


def ask_user_confirmation(pending_actions: list) -> UserConfirmation:
    """Ask user to confirm pending actions.

    Args:
        pending_actions: List of pending actions from the agent

    Returns:
        True if user approves, False if user rejects
    """
    if not pending_actions:
        return UserConfirmation.ACCEPT

    print_formatted_text(
        HTML(
            f"<yellow>🔍 Agent created {len(pending_actions)} action(s) and is waiting for confirmation:</yellow>"
        )
    )

    for i, action in enumerate(pending_actions, 1):
        tool_name = getattr(action, "tool_name", "<unknown tool>")
        action_content = str(getattr(action, "action", ""))[:100].replace("\n", " ")
        print_formatted_text(
            HTML(f"<grey>  {i}. {tool_name}: {action_content}...</grey>")
        )

    session = PromptSession()
    while True:
        try:
            user_input = (
                session.prompt(
                    HTML(
                        "<gold>Do you want to execute these actions? (yes/no): </gold>"
                    )
                )
                .strip()
                .lower()
            )

            if user_input in ("yes", "y"):
                print_formatted_text(
                    HTML("<green>✅ Approved — executing actions…</green>")
                )
                return UserConfirmation.ACCEPT
            elif user_input in ("no", "n"):
                print_formatted_text(HTML("<red>❌ Rejected — skipping actions…</red>"))
                return UserConfirmation.REJECT
            else:
                print_formatted_text(
                    HTML("<yellow>Please enter 'yes' or 'no'.</yellow>")
                )
        except (EOFError, KeyboardInterrupt):
            print_formatted_text(HTML("\n<red>No input received; pausing agent.</red>"))
            return UserConfirmation.DEFER


class ConversationRunner:
    """Handles the conversation state machine logic cleanly."""

    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.confirmation_mode = False

    def set_confirmation_mode(self, confirmation_mode: bool) -> None:
        self.confirmation_mode = confirmation_mode
        self.conversation.set_confirmation_mode(confirmation_mode)

    def _start_listener(self) -> None:
        self.listener = PauseListener(on_pause=self.conversation.pause)
        self.listener.start()

    def process_message(self, message: Message | None) -> None:
        """Process a user message through the conversation.

        Args:
            message: The user message to process
        """
        # Send message to conversation
        if message:
            self.conversation.send_message(message)

        if self.confirmation_mode:
            self._run_with_confirmation()
        else:
            self._run_without_confirmation()

    def _run_without_confirmation(self) -> None:
        with pause_listener(self.conversation):
            self.conversation.run()

    def _run_with_confirmation(self) -> None:
        # If agent was paused, resume with confirmation request
        print(
            "should be waiting", self.conversation.state.agent_waiting_for_confirmation
        )
        if self.conversation.state.agent_waiting_for_confirmation:
            print("showing options")
            self._handle_confirmation_request()

        while True:
            with pause_listener(self.conversation) as listener:
                self.conversation.run()

                if listener.is_paused():
                    break

            # In confirmation mode, agent either finishes or waits for user confirmation
            if self.conversation.state.agent_finished:
                break

            elif self.conversation.state.agent_waiting_for_confirmation:
                user_confirmation = self._handle_confirmation_request()
                if user_confirmation == UserConfirmation.DEFER:
                    return
            else:
                raise Exception("Infinite loop")

    def _handle_confirmation_request(self) -> UserConfirmation:
        """Handle confirmation request from user.

        Returns:
            True if user approved actions, False if rejected
        """
        pending_actions = get_unmatched_actions(self.conversation.state.events)

        if pending_actions:
            user_confirmation = ask_user_confirmation(pending_actions)
            if user_confirmation == UserConfirmation.REJECT:
                self.conversation.reject_pending_actions("User rejected the actions")
            elif user_confirmation == UserConfirmation.DEFER:
                self.conversation.pause()

            return user_confirmation

        return UserConfirmation.ACCEPT


def run_agent_chat() -> None:
    """Run the agent chat session using the agent SDK.

    Raises:
        AgentSetupError: If agent setup fails
        KeyboardInterrupt: If user interrupts the session
        EOFError: If EOF is encountered
    """
    # Setup agent - let exceptions bubble up
    conversation = setup_agent()

    # Generate session ID
    import uuid

    session_id = str(uuid.uuid4())[:8]

    display_welcome(session_id)

    # Create prompt session with command completer
    session = PromptSession(completer=CommandCompleter())

    # Create conversation runner to handle state machine logic
    runner = ConversationRunner(conversation)

    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = session.prompt(
                HTML("<gold>> </gold>"),
                multiline=False,
            )

            if not user_input.strip():
                continue

            # Handle commands
            command = user_input.strip().lower()

            message = Message(
                role="user",
                content=[TextContent(text=user_input)],
            )

            if command == "/exit":
                print_formatted_text(HTML("<yellow>Goodbye! 👋</yellow>"))
                break
            elif command == "/clear":
                display_welcome(session_id)
                continue
            elif command == "/help":
                display_help()
                continue
            elif command == "/status":
                print_formatted_text(HTML(f"<grey>Session ID: {session_id}</grey>"))
                print_formatted_text(HTML("<grey>Status: Active</grey>"))
                confirmation_status = (
                    "enabled" if conversation.state.confirmation_mode else "disabled"
                )
                print_formatted_text(
                    HTML(f"<grey>Confirmation mode: {confirmation_status}</grey>")
                )
                continue
            elif command == "/confirm":
                current_mode = runner.confirmation_mode
                runner.set_confirmation_mode(not current_mode)
                new_status = "enabled" if not current_mode else "disabled"
                print_formatted_text(
                    HTML(f"<yellow>Confirmation mode {new_status}</yellow>")
                )
                continue
            elif command == "/new":
                print_formatted_text(
                    HTML("<yellow>Starting new conversation...</yellow>")
                )
                session_id = str(uuid.uuid4())[:8]
                display_welcome(session_id)
                continue
            elif command == "/resume":
                if not conversation.state.agent_paused:
                    print_formatted_text(
                        HTML("<red>No paused conversation to resume...</red>")
                    )

                    continue

                # Resume without new message
                message = None

            # Send message to agent
            print_formatted_text(HTML("<green>Agent: </green>"), end="")

            # Check if conversation is paused and resume it for any user input
            if conversation.state.agent_paused:
                print_formatted_text(
                    HTML("<yellow>Resuming paused conversation...</yellow>")
                )

            runner.process_message(message)
            print_formatted_text(
                HTML("<green>✓ Agent has processed your request.</green>")
            )

            print()  # Add spacing

        except KeyboardInterrupt:
            print_formatted_text(
                HTML("\n<yellow>Chat interrupted. Type /exit to quit.</yellow>")
            )
            continue
        except EOFError:
            print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
            break


def main() -> None:
    """Main entry point for agent chat.

    Raises:
        AgentSetupError: If agent setup fails
        Exception: On unexpected errors
    """
    try:
        run_agent_chat()
    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
    except Exception as e:
        print_formatted_text(HTML(f"<red>Unexpected error: {str(e)}</red>"))
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    main()
