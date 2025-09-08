#!/usr/bin/env python3
"""
Agent chat functionality for OpenHands CLI.
Provides a conversation interface with an AI agent using OpenHands patterns.
"""

import logging

from openhands.sdk import (
    Message,
    TextContent,
)
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML

from openhands_cli.runner import ConversationRunner, UserConfirmation
from openhands_cli.setup import setup_agent
from openhands_cli.tui import (
    CommandCompleter,
    display_help,
    display_welcome,
)

logger = logging.getLogger(__name__)


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


def run_cli_entry() -> None:
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
        run_cli_entry()
    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
    except Exception as e:
        print_formatted_text(HTML(f"<red>Unexpected error: {str(e)}</red>"))
        logger.error(f"Main error: {e}")
        raise


if __name__ == "__main__":
    main()
