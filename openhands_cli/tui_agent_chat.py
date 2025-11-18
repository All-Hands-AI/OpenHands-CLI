#!/usr/bin/env python3
"""
TUI Agent chat functionality for OpenHands CLI with pinned input.
Provides a conversation interface with an AI agent using a pinned input box.
"""

import sys
import uuid
from datetime import datetime
from typing import Any

from prompt_toolkit.formatted_text import HTML

from openhands.sdk import (
    Message,
    TextContent,
)
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands_cli.runner import ConversationRunner
from openhands_cli.setup import (
    MissingAgentSpec,
    setup_conversation,
    verify_agent_exists_or_setup_agent,
)
from openhands_cli.tui.pinned_input_tui import PinnedInputTUI
from openhands_cli.tui.settings.mcp_screen import MCPScreen
from openhands_cli.tui.settings.settings_screen import SettingsScreen
from openhands_cli.tui.status import display_status
from openhands_cli.tui.tui import (
    display_help,
)
from openhands_cli.user_actions import UserConfirmation, exit_session_confirmation


class TUIAgentChat:
    """Agent chat with pinned input TUI interface."""
    
    def __init__(self, resume_conversation_id: str | None = None):
        """Initialize the TUI agent chat.
        
        Args:
            resume_conversation_id: Optional conversation ID to resume
        """
        self.conversation_id = uuid.uuid4()
        self.resume_conversation_id = resume_conversation_id
        self.session_start_time = datetime.now()
        self.runner: ConversationRunner | None = None
        self.conversation = None
        self.initialized_agent = None
        self.tui: PinnedInputTUI | None = None
        self._should_exit = False
        
        # Initialize conversation ID
        if resume_conversation_id:
            try:
                self.conversation_id = uuid.UUID(resume_conversation_id)
            except ValueError:
                self.tui.add_html_output(
                    f"<yellow>Warning: '{resume_conversation_id}' is not a valid UUID.</yellow>"
                )
                return
    
    def _setup_agent(self) -> bool:
        """Setup the agent and return True if successful."""
        try:
            self.initialized_agent = verify_agent_exists_or_setup_agent()
            return True
        except MissingAgentSpec:
            if self.tui:
                self.tui.add_html_output(
                    "<yellow>Setup is required to use OpenHands CLI.</yellow>"
                )
                self.tui.add_html_output("<yellow>Goodbye! 👋</yellow>")
            return False
    
    def _display_welcome(self) -> None:
        """Display welcome message in the TUI."""
        if not self.tui:
            return
            
        # Clear screen and show banner
        self.tui.clear_output()
        
        # ASCII banner
        banner = r"""<gold>
     ___                    _   _                 _
    /  _ \ _ __   ___ _ __ | | | | __ _ _ __   __| |___
    | | | | '_ \ / _ \ '_ \| |_| |/ _` | '_ \ / _` / __|
    | |_| | |_) |  __/ | | |  _  | (_| | | | | (_| \__ \
    \___ /| .__/ \___|_| |_|_| |_|\__,_|_| |_|\__,_|___/
          |_|
</gold>"""
        self.tui.add_html_output(banner)
        self.tui.add_html_output("")
        
        if not self.resume_conversation_id:
            self.tui.add_html_output(
                f"<grey>Initialized conversation {self.conversation_id}</grey>"
            )
        else:
            self.tui.add_html_output(
                f"<grey>Resumed conversation {self.conversation_id}</grey>"
            )
        
        self.tui.add_html_output("")
        self.tui.add_html_output("<gold>Let's start building!</gold>")
        self.tui.add_html_output(
            "<green>What do you want to build? <grey>Type /help for help</grey></green>"
        )
        self.tui.add_html_output("")
    
    def _handle_input(self, user_input: str) -> None:
        """Handle user input from the TUI.
        
        Args:
            user_input: The input text from the user
        """
        if not user_input.strip():
            return
        
        # Handle special control signals
        if user_input == "__CTRL_C__":
            if self.runner and self.runner.is_running:
                self.runner.conversation.pause()
                self.tui.add_html_output("<yellow>Agent paused by user</yellow>")
                self.tui.set_agent_running(False)
            else:
                self._should_exit = True
                self.tui.exit()
            return
        
        # Handle commands when agent is not running
        if not (self.runner and self.runner.is_running):
            if self._handle_command(user_input):
                return
        
        # Create message
        message = Message(
            role="user",
            content=[TextContent(text=user_input)],
        )
        
        # Handle message based on agent state
        if self.runner and self.runner.is_running:
            # Send message to running agent
            try:
                self.runner.send_message_while_running(message)
            except RuntimeError:
                # Agent stopped running, process normally
                self._process_message(message)
        else:
            # Process message normally
            self._process_message(message)
    
    def _handle_command(self, command: str) -> bool:
        """Handle command input. Returns True if it was a command."""
        command_lower = command.strip().lower()
        
        if command_lower == "/exit":
            exit_confirmation = exit_session_confirmation()
            if exit_confirmation == UserConfirmation.ACCEPT:
                self.tui.add_html_output("<yellow>Goodbye! 👋</yellow>")
                self._print_exit_hint()
                self._should_exit = True
                self.tui.exit()
            return True
        
        elif command_lower == "/settings":
            # Note: This will temporarily exit the TUI to show settings
            # In a full implementation, we'd want to integrate settings into the TUI
            self.tui.add_html_output("<yellow>Settings screen not yet integrated with pinned input TUI</yellow>")
            return True
        
        elif command_lower == "/mcp":
            # Note: Similar to settings, this would need TUI integration
            self.tui.add_html_output("<yellow>MCP screen not yet integrated with pinned input TUI</yellow>")
            return True
        
        elif command_lower == "/clear":
            self._display_welcome()
            return True
        
        elif command_lower == "/new":
            try:
                self.conversation_id = uuid.uuid4()
                self.runner = None
                self.conversation = None
                self._display_welcome()
                self.tui.add_html_output("<green>✓ Started fresh conversation</green>")
            except Exception as e:
                self.tui.add_html_output(f"<red>Error starting fresh conversation: {e}</red>")
            return True
        
        elif command_lower == "/help":
            self._display_help()
            return True
        
        elif command_lower == "/status":
            if self.conversation is not None:
                # Note: This would need to be adapted for TUI output
                self.tui.add_html_output("<yellow>Status display not yet integrated with pinned input TUI</yellow>")
            else:
                self.tui.add_html_output("<yellow>No active conversation</yellow>")
            return True
        
        elif command_lower == "/confirm":
            if self.runner is not None:
                self.runner.toggle_confirmation_mode()
                new_status = (
                    "enabled" if self.runner.is_confirmation_mode_active else "disabled"
                )
            else:
                new_status = "disabled (no active conversation)"
            self.tui.add_html_output(f"<yellow>Confirmation mode {new_status}</yellow>")
            return True
        
        elif command_lower == "/resume":
            if not self.runner:
                self.tui.add_html_output("<yellow>No active conversation running...</yellow>")
                return True
            
            conversation = self.runner.conversation
            if not (
                conversation.state.execution_status == ConversationExecutionStatus.PAUSED
                or conversation.state.execution_status == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
            ):
                self.tui.add_html_output("<red>No paused conversation to resume...</red>")
                return True
            
            # Resume without new message
            self._process_message(None)
            return True
        
        # Not a command
        return False
    
    def _display_help(self) -> None:
        """Display help information."""
        self.tui.add_html_output("")
        self.tui.add_html_output("<gold>🤖 OpenHands CLI Help</gold>")
        self.tui.add_html_output("<grey>Available commands:</grey>")
        self.tui.add_html_output("")
        
        commands = {
            "/exit": "Exit the application",
            "/help": "Display available commands",
            "/clear": "Clear the screen",
            "/new": "Start a fresh conversation",
            "/status": "Display conversation details",
            "/confirm": "Toggle confirmation mode on/off",
            "/resume": "Resume a paused conversation",
            "/settings": "Display and modify current settings",
            "/mcp": "View MCP (Model Context Protocol) server configuration",
        }
        
        for command, description in commands.items():
            self.tui.add_html_output(f"  <white>{command}</white> - {description}")
        
        self.tui.add_html_output("")
        self.tui.add_html_output("<grey>Tips:</grey>")
        self.tui.add_html_output("  • Type / and press Tab to see command suggestions")
        self.tui.add_html_output("  • Use arrow keys to navigate through suggestions")
        self.tui.add_html_output("  • Press Enter to select a command")
        self.tui.add_html_output("  • Press \\ + Enter to insert a newline")
        self.tui.add_html_output("  • Input box is always available at the bottom")
        self.tui.add_html_output("")
    
    def _process_message(self, message: Message | None) -> None:
        """Process a message through the conversation runner."""
        if not self.runner or not self.conversation:
            self.conversation = setup_conversation(self.conversation_id)
            self.runner = ConversationRunner(
                self.conversation, 
                on_agent_finished=self._on_agent_finished
            )
        
        # Update TUI state
        self.tui.set_agent_running(True)
        
        # Show agent running status
        self.tui.add_html_output("")
        if (
            self.conversation.state.execution_status == ConversationExecutionStatus.PAUSED
        ):
            self.tui.add_html_output(
                "<yellow>Resuming paused conversation...</yellow> <grey>(Press Ctrl-C to pause)</grey>"
            )
        else:
            self.tui.add_html_output(
                "<yellow>Agent running...</yellow> <grey>(Press Ctrl-C to pause)</grey>"
            )
        self.tui.add_html_output("")
        
        # Process the message
        self.runner.process_message(message)
    
    def _on_agent_finished(self) -> None:
        """Callback when agent finishes running."""
        if self.tui:
            self.tui.set_agent_running(False)
            self.tui.add_html_output("<green>✅ Agent finished. You can now use commands again.</green>")
    
    def _print_exit_hint(self) -> None:
        """Print a resume hint with the current conversation ID."""
        self.tui.add_html_output(
            f"<grey>Conversation ID:</grey> <yellow>{self.conversation_id}</yellow>"
        )
        self.tui.add_html_output(
            f"<grey>Hint:</grey> run <gold>openhands --resume {self.conversation_id}</gold> "
            "to resume this conversation."
        )
    
    def run(self) -> None:
        """Run the TUI agent chat."""
        # Setup agent
        if not self._setup_agent():
            return
        
        # Create TUI
        self.tui = PinnedInputTUI(
            on_input=self._handle_input,
            agent_running=False,
        )
        
        # Display welcome
        self._display_welcome()
        
        # Run the TUI
        try:
            self.tui.run()
        except (KeyboardInterrupt, EOFError):
            if not self._should_exit:
                self.tui.add_html_output("<yellow>Goodbye! 👋</yellow>")
                self._print_exit_hint()
        
        # Clean up terminal state
        self._restore_tty()
    
    def _restore_tty(self) -> None:
        """Ensure terminal modes are reset."""
        try:
            sys.stdout.write("\x1b[?1l\x1b[?2004l")
            sys.stdout.flush()
        except Exception:
            pass


def run_tui_cli_entry(resume_conversation_id: str | None = None) -> None:
    """Run the TUI CLI entry point.
    
    Args:
        resume_conversation_id: Optional conversation ID to resume
    """
    chat = TUIAgentChat(resume_conversation_id)
    chat.run()