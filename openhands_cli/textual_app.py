#!/usr/bin/env python3
"""
Textual-based TUI application for OpenHands CLI.
This replaces the prompt_toolkit implementation with a modern Textual interface.
"""

import uuid
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.theme import Theme
from textual.widgets import (
    Input,
    RichLog,
)
from textual_autocomplete import AutoComplete

from openhands.sdk import (
    BaseConversation,
    Conversation,
    Message,
    TextContent,
    Workspace,
)
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands_cli.locations import CONVERSATIONS_DIR, WORK_DIR
from openhands_cli.setup import (
    MissingAgentSpec,
    load_agent_specs,
    verify_agent_exists_or_setup_agent,
)
from openhands_cli.textual_runner import TextualConversationRunner
from openhands_cli.textual_settings import MCPScreen, SettingsScreen
from openhands_cli.textual_user_actions import (
    exit_session_confirmation_textual,
)
from openhands_cli.textual_visualizer import TextualVisualizer
from openhands_cli.user_actions import UserConfirmation


class OpenHandsApp(App):
    """Main Textual application for OpenHands CLI."""

    CSS = """
    Screen {
        layout: vertical;
        background: $background;
    }

    #main_display {
        height: 1fr;
        margin: 1 1 0 1;
        overflow-y: scroll;
        background: $background;
    }

    #input_area {
        height: 8;
        dock: bottom;
        background: $background;
        padding: 1;
        margin-bottom: 1;
    }

    #user_input {
        width: 100%;
        height: 3;
        background: $background;
        color: $text;
        border: solid $accent;
    }

    #user_input:focus {
        border: solid $primary;
        background: $background;
    }
    """

    BINDINGS: ClassVar = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+p", "pause", "Pause"),
        ("f1", "help", "Help"),
        ("f2", "settings", "Settings"),
        ("f3", "status", "Status"),
        ("f4", "clear", "Clear"),
        ("f5", "new", "New"),
    ]

    # Reactive variables
    conversation_id: reactive[str] = reactive("")
    session_start_time: reactive[datetime] = reactive(datetime.now)

    def __init__(self, resume_conversation_id: str | None = None):
        super().__init__()
        self.resume_conversation_id = resume_conversation_id
        self.runner: TextualConversationRunner | None = None
        self.conversation = None
        self.initialized_agent = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        # Main display area - takes up most of the screen
        main_display = RichLog(id="main_display", highlight=False, markup=True)
        main_display.can_focus = False
        yield main_display

        # Input area - docked to bottom
        with Container(id="input_area"):
            text_input = Input(
                placeholder=(
                    "Type your message… (tip: press \\ + Enter to insert a newline)"
                ),
                id="user_input",
            )

            yield text_input

            yield AutoComplete(text_input, candidates=["/help", "/exit", "/settings"])

    def _get_banner_text(self) -> str:
        """Get the OpenHands banner text."""
        return r"""
     ___                    _   _                 _
    /  _ \ _ __   ___ _ __ | | | | __ _ _ __   __| |___
    | | | | '_ \ / _ \ '_ \| |_| |/ _` | '_ \ / _` / __|
    | |_| | |_) |  __/ | | |  _  | (_| | | | | (_| \__ \
    \___ /| .__/ \___|_| |_|_| |_|\__,_|_| |_|\__,_|___/
          |_|
    """

    async def on_mount(self) -> None:
        """Initialize the application when mounted."""
        # Create and register custom theme
        openhands_theme = Theme(
            name="openhands",
            primary="#FFD700",  # Gold for primary elements (banner, titles)
            secondary="#808080",  # Grey for secondary text
            accent="#FFFFFF",  # White for commands and important text
            foreground="#D3D3D3",  # Light grey for default text
            background="#000000",  # Black background
            success="#00FF00",  # Bright green for success
            warning="#FFD700",  # Gold for warnings (same as primary)
            error="#FF0000",  # Bright red for errors
            surface="#1A1A1A",  # Dark grey for surfaces
            panel="#2A2A2A",  # Slightly lighter grey for panels
            dark=True,
            variables={
                # Custom variables for our specific use cases
                "banner-color": "#FFD700",  # Gold for ASCII banner
                "help-text-color": "#808080",  # Grey for help text
                "command-color": "#FFFFFF",  # White for commands
                "conversation-id-color": "#808080",  # Grey for conversation ID
            },
        )
        
        # Register and apply the theme
        self.register_theme(openhands_theme)
        self.theme = "openhands"

        # Set up conversation ID
        if self.resume_conversation_id:
            try:
                self.conversation_id = self.resume_conversation_id
                resume = True
            except ValueError:
                self.log_message(
                    f"[yellow]Warning: '{self.resume_conversation_id}' "
                    "is not a valid UUID.[/yellow]"
                )
                self.conversation_id = str(uuid.uuid4())
                resume = False
        else:
            self.conversation_id = str(uuid.uuid4())
            resume = False

        # Initialize agent
        try:
            self.initialized_agent = verify_agent_exists_or_setup_agent()
        except MissingAgentSpec:
            self.log_message("[yellow]Setup is required to use OpenHands CLI.[/yellow]")
            self.log_message("[yellow]Goodbye! 👋[/yellow]")
            self.exit()
            return

        # Display welcome message (this will show the banner and conversation info)
        self.display_welcome(resume)

        # Focus the input
        input_widget = self.query_one("#user_input", Input)
        input_widget.focus()

    def display_welcome(self, resume: bool = False) -> None:
        """Display the welcome message."""
        chat_log = self.query_one("#main_display", RichLog)

        # Display the banner first
        chat_log.write(f"[primary]{self._get_banner_text()}[/primary]")
        chat_log.write("")

        # Display conversation initialization message
        if not resume:
            chat_log.write(
                f"[secondary]Initialized conversation "
                f"{self.conversation_id}[/secondary]"
            )
        else:
            chat_log.write(
                f"[secondary]Resumed conversation "
                f"{self.conversation_id}[/secondary]"
            )

        chat_log.write("")
        chat_log.write("[primary]Let's start building![/primary]")
        chat_log.write(
            "[success]What do you want to build? "
            "[secondary]Type /help for help[/secondary][/success]"
        )
        chat_log.write("")

    def log_message(self, message: str) -> None:
        """Log a message to the chat area."""
        chat_log = self.query_one("#main_display", RichLog)
        chat_log.write(message)

    def setup_textual_conversation(
        self,
        conversation_id: UUID,
        visualizer: TextualVisualizer,
        include_security_analyzer: bool = True,
    ) -> BaseConversation:
        """Setup the conversation with agent and textual visualizer.

        This is a modified version of setup_conversation that accepts a
        visualizer instance.
        """
        agent = load_agent_specs(str(conversation_id))

        # Create conversation with our textual visualizer
        conversation: BaseConversation = Conversation(
            agent=agent,
            workspace=Workspace(working_dir=WORK_DIR),
            # Conversation will add /<conversation_id> to this path
            persistence_dir=CONVERSATIONS_DIR,
            conversation_id=conversation_id,
            visualizer=visualizer,
        )

        # Security analyzer is set though conversation API now
        if not include_security_analyzer:
            conversation.set_security_analyzer(None)
        else:
            conversation.set_security_analyzer(LLMSecurityAnalyzer())

        return conversation

    @on(Input.Submitted, "#user_input")
    async def handle_input(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()

        if not user_input:
            return

        # Clear the input
        event.input.value = ""

        # Handle commands
        if user_input.startswith("/"):
            await self.handle_command(user_input)
        else:
            # Regular message
            await self.process_user_message(user_input)

    async def handle_command(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower()

        if cmd == "/exit":
            await self.action_quit()
        elif cmd == "/help":
            self.action_help()
        elif cmd == "/clear":
            self.action_clear()
        elif cmd == "/new":
            await self.action_new()
        elif cmd == "/status":
            self.action_status()
        elif cmd == "/settings":
            await self.action_settings()
        elif cmd == "/mcp":
            await self.action_mcp()
        elif cmd == "/confirm":
            self.action_confirm()
        elif cmd == "/resume":
            await self.action_resume()
        else:
            self.log_message(f"[error]Unknown command: {command}[/error]")
            self.log_message(
                "[warning]Type [accent]/help[/accent] to see available "
                "commands[/warning]"
            )

    async def process_user_message(self, user_input: str) -> None:
        """Process a regular user message."""
        message = Message(
            role="user",
            content=[TextContent(text=user_input)],
        )

        # Initialize conversation if needed
        if not self.runner or not self.conversation:
            conversation_id = uuid.UUID(self.conversation_id)

            # Set up the visualizer to output to our chat log
            chat_log = self.query_one("#main_display", RichLog)
            visualizer = TextualVisualizer(chat_log, self)

            # Create conversation with our visualizer
            self.conversation = self.setup_textual_conversation(
                conversation_id, visualizer
            )
            self.runner = TextualConversationRunner(self.conversation, self)

        # Log user message
        self.log_message(f"[bold blue]User:[/bold blue] {user_input}")

        # Process the message
        try:
            await self.runner.process_message(message)
        except Exception as e:
            self.log_message(f"[red]Error processing message: {e}[/red]")

    def action_help(self) -> None:
        """Display help information."""
        self.log_message("")
        self.log_message("[primary]🤖 OpenHands CLI Help[/primary]")
        self.log_message("[secondary]Available commands:[/secondary]")
        self.log_message("")

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
            self.log_message(f"  [accent]{command}[/accent] - {description}")

        self.log_message("")
        self.log_message("[secondary]Tips:[/secondary]")
        self.log_message("  • Use F1-F5 for quick access to common functions")
        self.log_message("  • Press Ctrl+C to quit, Ctrl+P to pause")
        self.log_message("")

    def action_clear(self) -> None:
        """Clear the chat log."""
        chat_log = self.query_one("#main_display", RichLog)
        chat_log.clear()
        self.display_welcome()

    async def action_new(self) -> None:
        """Start a new conversation."""
        try:
            self.conversation_id = str(uuid.uuid4())
            self.runner = None
            self.conversation = None
            self.display_welcome(resume=False)
            self.log_message("[green]✓ Started fresh conversation[/green]")
        except Exception as e:
            self.log_message(f"[red]Error starting fresh conversation: {e}[/red]")

    def action_status(self) -> None:
        """Display conversation status."""
        if self.conversation is not None:
            # For now, just display basic info
            self.log_message(
                f"[yellow]Conversation ID:[/yellow] {self.conversation_id}"
            )
            self.log_message(
                f"[yellow]Session started:[/yellow] {self.session_start_time}"
            )
            if self.runner:
                confirmation_status = (
                    "enabled" if self.runner.is_confirmation_mode_active else "disabled"
                )
                self.log_message(
                    f"[yellow]Confirmation mode:[/yellow] {confirmation_status}"
                )
        else:
            self.log_message("[yellow]No active conversation[/yellow]")

    async def action_settings(self) -> None:
        """Open settings screen."""
        settings_screen = SettingsScreen(
            self.runner.conversation if self.runner else None
        )
        self.push_screen(settings_screen)

    async def action_mcp(self) -> None:
        """Open MCP screen."""
        if self.initialized_agent:
            mcp_screen = MCPScreen(self.initialized_agent)
            self.push_screen(mcp_screen)
        else:
            self.log_message("[red]No agent initialized yet[/red]")

    def action_confirm(self) -> None:
        """Toggle confirmation mode."""
        if self.runner is not None:
            self.runner.toggle_confirmation_mode()
            new_status = (
                "enabled" if self.runner.is_confirmation_mode_active else "disabled"
            )
        else:
            new_status = "disabled (no active conversation)"
        self.log_message(f"[yellow]Confirmation mode {new_status}[/yellow]")

    async def action_resume(self) -> None:
        """Resume a paused conversation."""
        if not self.runner:
            self.log_message("[yellow]No active conversation running...[/yellow]")
            return

        conversation = self.runner.conversation
        if not (
            conversation.state.execution_status == ConversationExecutionStatus.PAUSED
            or conversation.state.execution_status
            == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
        ):
            self.log_message("[red]No paused conversation to resume...[/red]")
            return

        # Resume without new message
        try:
            await self.runner.process_message(None)
        except Exception as e:
            self.log_message(f"[red]Error resuming conversation: {e}[/red]")

    async def action_quit(self) -> None:
        """Quit the application with confirmation."""
        confirmation = await exit_session_confirmation_textual(self)
        if confirmation == UserConfirmation.ACCEPT:
            self.log_message("[yellow]Goodbye! 👋[/yellow]")
            if self.conversation_id:
                self.log_message(
                    f"[grey]Conversation ID:[/grey] "
                    f"[yellow]{self.conversation_id}[/yellow]"
                )
                self.log_message(
                    f"[grey]Hint:[/grey] run [gold]openhands --resume "
                    f"{self.conversation_id}[/gold] to resume this conversation."
                )
            self.exit()

    def action_pause(self) -> None:
        """Pause the current conversation."""
        if self.runner and self.conversation:
            self.conversation.pause()
            self.log_message("[yellow]Conversation paused[/yellow]")
        else:
            self.log_message("[yellow]No active conversation to pause[/yellow]")


def run_textual_app(resume_conversation_id: str | None = None) -> None:
    """Run the Textual-based OpenHands CLI application."""
    app = OpenHandsApp(resume_conversation_id=resume_conversation_id)
    app.run()


if __name__ == "__main__":
    run_textual_app()
