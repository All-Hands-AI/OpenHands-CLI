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

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear
from pydantic import SecretStr

from openhands_cli.tui import CommandCompleter, display_banner, display_help

try:
    from openhands.sdk import (
        LLM,
        Agent,
        Conversation,
        EventType,
        LLMConfig,
        Message,
        TextContent,
        Tool,
    )
    from openhands.tools import (
        BashExecutor,
        FileEditorExecutor,
        execute_bash_tool,
        str_replace_editor_tool,
    )
except ImportError as e:
    print_formatted_text(HTML(f"<red>Error importing OpenHands SDK: {e}</red>"))
    print_formatted_text(
        HTML("<yellow>Please ensure the openhands-sdk is properly installed.</yellow>")
    )
    raise


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

        # Configure LLM
        llm_config = LLMConfig(
            model=model,
            api_key=SecretStr(api_key) if api_key else None,
        )

        if base_url:
            llm_config.base_url = base_url

        llm = LLM(config=llm_config)

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
                continue
            elif command == "/new":
                print_formatted_text(
                    HTML("<yellow>Starting new conversation...</yellow>")
                )
                session_id = str(uuid.uuid4())[:8]
                display_welcome(session_id)
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
