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

from openhands_cli.runner import ConversationRunner
from openhands_cli.setup import setup_agent
from openhands_cli.tui import (
    CommandCompleter,
    display_help,
    display_welcome,
)

logger = logging.getLogger(__name__)


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


# def main() -> None:
#     """Main entry point for agent chat.

#     Raises:
#         AgentSetupError: If agent setup fails
#         Exception: On unexpected errors
#     """
#     try:
#         run_cli_entry()
#     except KeyboardInterrupt:
#         print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
#     except Exception as e:
#         print_formatted_text(HTML(f"<red>Unexpected error: {str(e)}</red>"))
#         logger.error(f"Main error: {e}")
#         raise


# if __name__ == "__main__":
#     main()
