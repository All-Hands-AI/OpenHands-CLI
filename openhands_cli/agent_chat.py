#!/usr/bin/env python3
"""
Agent chat functionality for OpenHands CLI.
Provides a conversation interface with an AI agent using OpenHands patterns.
"""

import logging
import os
import sys
import threading
import traceback

# Ensure we use the agent-sdk openhands package, not the main OpenHands package
# Remove the main OpenHands code path if it exists
if "/openhands/code" in sys.path:
    sys.path.remove("/openhands/code")

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import clear
from pydantic import SecretStr

from openhands_cli.tui import CommandCompleter, display_banner, display_help

SDK_AVAILABLE = True
SDK_IMPORT_ERROR: Exception | None = None
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
    from openhands.sdk.event.utils import get_unmatched_actions
    from openhands.tools import (
        BashExecutor,
        FileEditorExecutor,
        execute_bash_tool,
        str_replace_editor_tool,
    )
except ImportError as e:
    # Do not fail module import — allow tests to patch these symbols.
    SDK_AVAILABLE = False
    SDK_IMPORT_ERROR = e

    class LLM:  # type: ignore
        pass

    class Agent:  # type: ignore
        def pause(self):  # noqa: D401
            pass

    class Conversation:  # type: ignore
        class State:
            agent_finished = True
            agent_waiting_for_confirmation = False
            confirmation_mode = False
            events: list = []

        state = State()

        def __init__(self, *args, **kwargs):
            pass

        def send_message(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            pass

        def set_confirmation_mode(self, *args, **kwargs):
            self.state.confirmation_mode = bool(args[0]) if args else False

        def reject_pending_actions(self, *args, **kwargs):
            pass

        def pause(self):  # noqa: D401
            pass

    class EventType:  # type: ignore
        pass

    class LLMConfig:  # type: ignore
        def __init__(self, *args, **kwargs):
            self.model = kwargs.get("model")
            self.api_key = kwargs.get("api_key")
            self.base_url = kwargs.get("base_url")

    class Message:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class TextContent:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class Tool:  # type: ignore
        def set_executor(self, *args, **kwargs):
            return self

    def get_unmatched_actions(events):  # type: ignore
        return []

    class BashExecutor:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class FileEditorExecutor:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class _DummyTool:  # type: ignore
        def set_executor(self, *args, **kwargs):
            return self

    execute_bash_tool = _DummyTool()  # type: ignore
    str_replace_editor_tool = _DummyTool()  # type: ignore

    # Informational print, but do not raise to keep tests importable
    print_formatted_text(HTML(f"<yellow>Note: {e}. Using stub SDK symbols for testing.</yellow>"))


logger = logging.getLogger(__name__)

# Serialize prints across threads to avoid interleaving
_print_lock = threading.Lock()


class AgentSetupError(Exception):
    """Exception raised when agent setup fails."""

    pass


class PauseListener(threading.Thread):
    """Background key listener that triggers pause on Ctrl-P.

    Starts and stops around agent run() loops to avoid interfering with user prompts.
    """

    def __init__(self, on_pause: callable):
        super().__init__(daemon=True)
        self.on_pause = on_pause
        self._stop_event = threading.Event()
        self._input = create_input()

    def run(self) -> None:
        try:
            with self._input.raw_mode():
                while not self._stop_event.is_set():
                    for key_press in self._input.read_keys():
                        if self._stop_event.is_set():
                            break
                        if key_press.key == Keys.ControlP:
                            with _print_lock:
                                print_formatted_text(HTML(""))
                                print_formatted_text(
                                    HTML("<gold>Pausing the agent...</gold>")
                                )
                            try:
                                self.on_pause()
                            except Exception:
                                # Best-effort; swallow pause errors to not crash UI
                                pass
        finally:
            try:
                self._input.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop_event.set()


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

    def _pause_callback(self) -> None:
        """Attempt to pause via conversation.pause() or agent.pause()."""
        try:
            if hasattr(self.conversation, "pause"):
                self.conversation.pause()  # type: ignore[attr-defined]
                return
        except Exception:
            pass
        if self.agent and hasattr(self.agent, "pause"):
            try:
                self.agent.pause()  # type: ignore[attr-defined]
            except Exception:
                pass

    def process_message(self, message: Message) -> None:
        """Process a user message through the conversation.

        Args:
            message: The user message to process
        """
        # Send message to conversation
        self.conversation.send_message(message)

        # Run conversation until completion or confirmation needed
        self._run_until_completion_or_confirmation()

    def _run_until_completion_or_confirmation(self) -> None:
        """Run conversation until agent finishes or needs confirmation."""
        listener: PauseListener | None = None
        try:
            while not self.conversation.state.agent_finished:
                # ensure listener is active during run cycles so Ctrl-P can pause
                if listener is None or not listener.is_alive():
                    listener = PauseListener(on_pause=self._pause_callback)
                    listener.start()

                self.conversation.run()

                # Check if agent is waiting for confirmation: stop listener before prompting
                if self.conversation.state.agent_waiting_for_confirmation:
                    if listener is not None:
                        listener.stop()
                        listener = None
                    if not self._handle_confirmation_request():
                        # User rejected - continue the loop as agent may produce new actions or finish
                        continue
                    # If approved, continue to run() which will execute the actions
                else:
                    # Agent finished normally
                    break
        finally:
            if listener is not None:
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

            # Send message to agent
            print_formatted_text(HTML("<green>Agent: </green>"), end="")

            try:
                # Create message and process through conversation runner
                message = Message(
                    role="user",
                    content=[TextContent(text=user_input)],
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
