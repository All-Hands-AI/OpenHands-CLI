#!/usr/bin/env python3
"""
Agent chat functionality for OpenHands CLI.
Provides a conversation interface with an AI agent using OpenHands patterns.
"""

import logging
import os
import sys
import traceback

# Ensure we use the agent-sdk openhands package, not the main OpenHands package
# Remove the main OpenHands code path if it exists
if "/openhands/code" in sys.path:
    sys.path.remove("/openhands/code")

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
from prompt_toolkit.shortcuts import clear
from pydantic import SecretStr

from openhands_cli.listeners import PauseListener
from openhands_cli.tui import CommandCompleter, display_banner, display_help

logger = logging.getLogger(__name__)


class AgentSetupError(Exception):
    """Exception raised when agent setup fails."""

    pass


def setup_agent() -> tuple[LLM, Agent, Conversation]:
    """Setup the agent with environment variables.

    Returns:
        tuple: (llm, agent, conversation)

    Raises:
        AgentSetupError: If agent setup fails
    """
    try:
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
        return llm, agent, conversation

    except AgentSetupError:
        # Re-raise AgentSetupError as-is
        raise
    except Exception as e:
        print_formatted_text(HTML(f"<red>Error setting up agent: {str(e)}</red>"))
        traceback.print_exc()
        raise AgentSetupError(f"Error setting up agent: {str(e)}") from e


def ask_user_confirmation(pending_actions: list) -> bool:
    """Ask user to confirm pending actions.

    Args:
        pending_actions: List of pending actions from the agent

    Returns:
        True if user approves, False if user rejects
    """
    if not pending_actions:
        return True

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
                return True
            elif user_input in ("no", "n"):
                print_formatted_text(HTML("<red>❌ Rejected — skipping actions…</red>"))
                return False
            else:
                print_formatted_text(
                    HTML("<yellow>Please enter 'yes' or 'no'.</yellow>")
                )
        except (EOFError, KeyboardInterrupt):
            print_formatted_text(
                HTML("\n<red>❌ No input received; rejecting by default.</red>")
            )
            return False


class ConversationRunner:
    """Handles the conversation state machine logic cleanly."""

    def __init__(self, conversation: Conversation, agent: Agent | None = None):
        self.conversation = conversation
        self.agent = agent

    def process_message(self, message: Message) -> None:
        """Process a user message through the conversation.

        Args:
            message: The user message to process
        """
        # Send message to conversation
        self.conversation.send_message(message)

        # Run conversation until completion or confirmation needed
        self._run_until_completion_or_confirmation()

    def _conditions_to_run_loop_are_met(self, resume: bool) -> bool:
        if resume:
            return True

        if not self.conversation.state.agent_finished:
            return True

        if not self.conversation.state.agent_paused:
            return True

        return False

    def _run_until_completion_or_confirmation(self) -> None:
        """Run conversation until agent finishes or needs confirmation."""
        resume = True  # invoking this method always reumes conversation
        listener: PauseListener = PauseListener(on_pause=self.conversation.pause)
        try:
            while self._conditions_to_run_loop_are_met(resume):
                resume = False  # loop has been resumed, can reset

                # ensure listener is active during run cycles so Ctrl-P can pause
                if not listener.is_alive():
                    listener = PauseListener(on_pause=self.conversation.pause)
                    listener.start()

                self.conversation.run()

                listener.stop()

                # Check if agent is waiting for confirmation: stop listener before prompting
                if self.conversation.state.agent_waiting_for_confirmation:
                    if not self._handle_confirmation_request():
                        # User rejected - continue the loop as agent may produce new actions or finish
                        continue
                    # If approved, continue to run() which will execute the actions
                else:
                    break

        except Exception:
            pass
        finally:
            listener.stop()

    def _handle_confirmation_request(self) -> bool:
        """Handle confirmation request from user.

        Returns:
            True if user approved actions, False if rejected
        """
        pending_actions = get_unmatched_actions(self.conversation.state.events)

        if pending_actions:
            approved = ask_user_confirmation(pending_actions)
            if not approved:
                self.conversation.reject_pending_actions("User rejected the actions")
                return False
        return True

    def resume_conversation(self) -> bool:
        """Resume a paused conversation.

        Returns:
            True if conversation was resumed, False if not paused or failed to resume
        """
        if not self.conversation.state.agent_paused:
            return False

        self._run_until_completion_or_confirmation()
        return True


def display_welcome(session_id: str = "chat") -> None:
    """Display welcome message."""
    clear()
    display_banner(session_id)
    print_formatted_text(HTML("<gold>Let's start building!</gold>"))
    print_formatted_text(
        HTML(
            "<green>What do you want to build? <grey>Type /help for help</grey></green>"
        )
    )
    print()


def run_agent_chat() -> None:
    """Run the agent chat session using the agent SDK.

    Raises:
        AgentSetupError: If agent setup fails
        KeyboardInterrupt: If user interrupts the session
        EOFError: If EOF is encountered
    """
    # Setup agent - let exceptions bubble up
    llm, agent, conversation = setup_agent()

    # Generate session ID
    import uuid

    session_id = str(uuid.uuid4())[:8]

    display_welcome(session_id)

    # Create prompt session with command completer
    session = PromptSession(completer=CommandCompleter())

    # Create conversation runner to handle state machine logic
    runner = ConversationRunner(conversation, agent)

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
                current_mode = conversation.state.confirmation_mode
                conversation.set_confirmation_mode(not current_mode)
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
                if conversation.state.agent_paused:
                    print_formatted_text(
                        HTML("<yellow>Resuming paused conversation...</yellow>")
                    )
                    if runner.resume_conversation():
                        print_formatted_text(
                            HTML("<green>✓ Conversation resumed successfully.</green>")
                        )
                    else:
                        print_formatted_text(
                            HTML("<red>Failed to resume conversation.</red>")
                        )
                else:
                    print_formatted_text(
                        HTML("<yellow>No paused conversation to resume.</yellow>")
                    )
                continue

            # Send message to agent
            print_formatted_text(HTML("<green>Agent: </green>"), end="")

            try:
                # Create message and process through conversation runner
                message = Message(
                    role="user",
                    content=[TextContent(text=user_input)],
                )

                # Check if conversation is paused and resume it for any user input
                if conversation.state.agent_paused:
                    print_formatted_text(
                        HTML("<yellow>Resuming paused conversation...</yellow>")
                    )

                runner.process_message(message)
                print_formatted_text(
                    HTML("<green>✓ Agent has processed your request.</green>")
                )

            except Exception as e:
                print_formatted_text(HTML(f"<red>Error: {str(e)}</red>"))

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
    except AgentSetupError as e:
        # Agent setup errors are already printed in setup_agent()
        logger.error(f"Agent setup failed: {e}")
        raise
    except Exception as e:
        print_formatted_text(HTML(f"<red>Unexpected error: {str(e)}</red>"))
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    main()
