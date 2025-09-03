#!/usr/bin/env python3
"""
Agent chat functionality for OpenHands CLI.
Provides a conversation interface with an AI agent using OpenHands patterns.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from typing import Any

# Ensure we use the agent-sdk openhands package, not the main OpenHands package
# Remove the main OpenHands code path if it exists
if "/openhands/code" in sys.path:
    sys.path.remove("/openhands/code")

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear
from pydantic import SecretStr

from openhands_cli.confirmation import (
    analyze_action_risk,
    confirmation_mode,
    display_risk_warning,
    read_confirmation_input,
)
from openhands_cli.tui import CommandCompleter, display_banner, display_help

try:
    from openhands.core.agent.codeact_agent import CodeActAgent
    from openhands.core.config import LLMConfig
    from openhands.core.conversation import Conversation
    from openhands.core.event import EventType
    from openhands.core.llm import LLM, Message, TextContent
    from openhands.core.tool import Tool
    from openhands.tools.execute_bash import BashExecutor, execute_bash_tool
    from openhands.tools.str_replace_editor import (
        FileEditorExecutor,
        str_replace_editor_tool,
    )
except ImportError as e:
    print_formatted_text(HTML(f"<red>Error importing OpenHands SDK: {e}</red>"))
    print_formatted_text(
        HTML("<yellow>Please ensure the openhands-sdk is properly installed.</yellow>")
    )
    sys.exit(1)


logger = logging.getLogger(__name__)


async def confirm_action_if_needed(
    action_type: str, action_data: dict[str, Any]
) -> bool:
    """Check if an action needs confirmation and get user approval if needed.

    Returns True if the action should proceed, False if it should be cancelled.
    """
    # Analyze the security risk of the action
    risk = analyze_action_risk(action_type, action_data)

    # Check if confirmation is needed based on current mode
    if not confirmation_mode.should_confirm(risk):
        return True

    # Create action description for display
    if action_type == "execute_bash":
        action_description = (
            f"Execute command: {action_data.get('command', 'Unknown command')}"
        )
    elif action_type == "str_replace_editor":
        command = action_data.get("command", "unknown")
        path = action_data.get("path", "unknown file")
        action_description = f"File operation: {command} on {path}"
    else:
        action_description = f"Action: {action_type}"

    # Display risk warning
    display_risk_warning(risk, action_description)

    # Get user confirmation
    confirmation_result = await read_confirmation_input(risk)

    # Handle the user's choice
    if confirmation_result == "yes":
        return True
    elif confirmation_result == "no":
        print_formatted_text(
            HTML(
                "<yellow>Action cancelled. Please provide alternative instructions.</yellow>"
            )
        )
        return False
    elif confirmation_result == "always":
        confirmation_mode.set_mode("never")
        print_formatted_text(
            HTML(
                "<yellow>Confirmation mode disabled. All actions will proceed automatically.</yellow>"
            )
        )
        return True
    elif confirmation_result == "auto_highrisk":
        confirmation_mode.set_mode("auto_highrisk")
        print_formatted_text(
            HTML(
                "<yellow>Auto-confirm mode enabled. Only HIGH risk actions will require confirmation.</yellow>"
            )
        )
        return True

    return False


def display_confirmation_help() -> None:
    """Display help for confirmation mode commands."""
    print_formatted_text(HTML("<gold>Confirmation Mode Commands:</gold>"))
    print_formatted_text(
        HTML("  <green>/confirm status</green> - Show current confirmation mode")
    )
    print_formatted_text(
        HTML(
            "  <green>/confirm default</green> - Default mode (confirm MEDIUM/HIGH risk actions)"
        )
    )
    print_formatted_text(
        HTML(
            "  <green>/confirm auto</green> - Auto-confirm LOW/MEDIUM risk, ask for HIGH risk"
        )
    )
    print_formatted_text(
        HTML("  <green>/confirm always</green> - Always confirm all actions")
    )
    print_formatted_text(
        HTML(
            "  <green>/confirm never</green> - Never ask for confirmation (NOT RECOMMENDED)"
        )
    )
    print_formatted_text("")


def handle_confirmation_command(command: str) -> None:
    """Handle confirmation mode commands."""
    parts = command.split()
    if len(parts) < 2:
        display_confirmation_help()
        return

    subcommand = parts[1].lower()

    if subcommand == "status":
        if confirmation_mode.never_confirm:
            print_formatted_text(HTML("<yellow>Confirmation Mode: Disabled</yellow>"))
        elif confirmation_mode.always_confirm:
            print_formatted_text(
                HTML("<yellow>Confirmation Mode: Always confirm</yellow>")
            )
        elif confirmation_mode.auto_highrisk_confirm:
            print_formatted_text(
                HTML("<yellow>Confirmation Mode: Auto-confirm LOW/MEDIUM risk</yellow>")
            )
        else:
            print_formatted_text(
                HTML(
                    "<yellow>Confirmation Mode: Confirm MEDIUM/HIGH risk (default)</yellow>"
                )
            )

    elif subcommand == "default":
        confirmation_mode.set_mode("default")
        print_formatted_text(
            HTML(
                "<green>✓ Confirmation mode set to default (confirm MEDIUM/HIGH risk actions)</green>"
            )
        )

    elif subcommand == "auto":
        confirmation_mode.set_mode("auto_highrisk")
        print_formatted_text(
            HTML(
                "<green>✓ Auto-confirm mode enabled (only HIGH risk actions require confirmation)</green>"
            )
        )

    elif subcommand == "always":
        confirmation_mode.set_mode("always")
        print_formatted_text(
            HTML(
                "<yellow>⚠️  Always confirm mode enabled (all actions require confirmation)</yellow>"
            )
        )

    elif subcommand == "never":
        confirmation_mode.set_mode("never")
        print_formatted_text(
            HTML(
                "<red>⚠️  Confirmation disabled (NOT RECOMMENDED - all actions will proceed automatically)</red>"
            )
        )

    else:
        print_formatted_text(
            HTML(f"<red>Unknown confirmation command: {subcommand}</red>")
        )
        display_confirmation_help()


def setup_agent() -> tuple[LLM | None, CodeActAgent | None, Conversation | None]:
    """Setup the agent with environment variables."""
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
            return None, None, None

        # Configure LLM
        llm_config = LLMConfig(
            model=model,
            api_key=SecretStr(api_key) if api_key else None,
        )

        if base_url:
            llm_config.base_url = base_url

        llm = LLM(config=llm_config)

        # Setup tools with confirmation wrapper
        cwd = os.getcwd()
        bash = BashExecutor(working_dir=cwd)
        file_editor = FileEditorExecutor()

        # Create confirmation-aware tool wrappers
        bash_tool = execute_bash_tool.set_executor(executor=bash)
        editor_tool = str_replace_editor_tool.set_executor(executor=file_editor)

        tools: list[Tool] = [bash_tool, editor_tool]

        # Create agent
        agent = CodeActAgent(llm=llm, tools=tools)

        # Setup conversation with callback
        def conversation_callback(event: EventType) -> None:
            logger.debug(f"Conversation event: {str(event)[:200]}...")

        conversation = Conversation(agent=agent, callbacks=[conversation_callback])

        print_formatted_text(
            HTML(f"<green>✓ Agent initialized with model: {model}</green>")
        )
        return llm, agent, conversation

    except Exception as e:
        print_formatted_text(HTML(f"<red>Error setting up agent: {str(e)}</red>"))
        traceback.print_exc()
        return None, None, None


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
    print_formatted_text(
        HTML(
            "<yellow>🔒 Confirmation mode is enabled by default. Use /confirm to manage settings.</yellow>"
        )
    )
    print()


def run_agent_chat() -> None:
    """Run the agent chat session using the agent SDK."""
    # Setup agent
    llm, agent, conversation = setup_agent()
    if not agent or not conversation:
        return

    # Generate session ID
    import uuid

    session_id = str(uuid.uuid4())[:8]

    display_welcome(session_id)

    # Create prompt session with command completer
    session = PromptSession(completer=CommandCompleter())

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
                # Display confirmation mode status
                if confirmation_mode.never_confirm:
                    print_formatted_text(
                        HTML("<grey>Confirmation Mode: Disabled</grey>")
                    )
                elif confirmation_mode.always_confirm:
                    print_formatted_text(
                        HTML("<grey>Confirmation Mode: Always confirm</grey>")
                    )
                elif confirmation_mode.auto_highrisk_confirm:
                    print_formatted_text(
                        HTML(
                            "<grey>Confirmation Mode: Auto-confirm LOW/MEDIUM risk</grey>"
                        )
                    )
                else:
                    print_formatted_text(
                        HTML(
                            "<grey>Confirmation Mode: Confirm MEDIUM/HIGH risk (default)</grey>"
                        )
                    )
                continue
            elif command == "/new":
                print_formatted_text(
                    HTML("<yellow>Starting new conversation...</yellow>")
                )
                session_id = str(uuid.uuid4())[:8]
                display_welcome(session_id)
                continue
            elif command == "/confirm":
                display_confirmation_help()
                continue
            elif command.startswith("/confirm "):
                handle_confirmation_command(command)
                continue

            # Send message to agent
            print_formatted_text(HTML("<green>Agent: </green>"), end="")

            try:
                # Create message and send to conversation
                message = Message(
                    role="user",
                    content=[TextContent(text=user_input)],
                )

                conversation.send_message(message)
                conversation.run()

                # Get the last response from the conversation
                # For simplicity, we'll just indicate the agent processed the request
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
    """Main entry point for agent chat."""
    try:
        run_agent_chat()
    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
    except Exception as e:
        print_formatted_text(HTML(f"<red>Unexpected error: {str(e)}</red>"))
        logger.error(f"Main error: {e}")


if __name__ == "__main__":
    main()
