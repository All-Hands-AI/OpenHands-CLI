#!/usr/bin/env python3
"""
Full-screen TUI main interface for OpenHands CLI.
This replaces the traditional CLI with a modern terminal user interface.
"""

import asyncio
import sys
import uuid
from datetime import datetime
from typing import Any, Callable

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.layout.containers import Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.widgets import Frame
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.filters import Condition

from openhands.sdk import Message, TextContent
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands_cli.runner import ConversationRunner
from openhands_cli.setup import (
    MissingAgentSpec,
    setup_conversation,
    verify_agent_exists_or_setup_agent,
)
from openhands_cli.tui_visualizer import TUIVisualizer
from openhands_cli.tui.settings.mcp_screen import MCPScreen
from openhands_cli.tui.settings.settings_screen import SettingsScreen
from openhands_cli.tui.status import display_status
from openhands_cli.tui.tui import display_help, display_welcome
from openhands_cli.user_actions import UserConfirmation, exit_session_confirmation


class OpenHandsTUI:
    """Full-screen TUI for OpenHands CLI."""
    
    def __init__(self, resume_conversation_id: str | None = None):
        self.resume_conversation_id = resume_conversation_id
        self.conversation_id = uuid.uuid4()
        if resume_conversation_id:
            try:
                self.conversation_id = uuid.UUID(resume_conversation_id)
            except ValueError:
                print_formatted_text(
                    HTML(f"<yellow>Warning: '{resume_conversation_id}' is not a valid UUID.</yellow>")
                )
                return
        
        # Initialize agent
        try:
            self.initialized_agent = verify_agent_exists_or_setup_agent()
        except MissingAgentSpec:
            print_formatted_text(HTML("\n<yellow>Setup is required to use OpenHands CLI.</yellow>"))
            print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
            return
        
        # Session tracking
        self.session_start_time = datetime.now()
        self.runner: ConversationRunner | None = None
        self.conversation = None
        
        # UI state
        self.output_content: list[str] = []
        self.input_buffer = Buffer()
        self.output_buffer = Buffer()  # Regular buffer for output with text selection (editing controlled by key bindings)
        self.app: Application | None = None
        
        # Initialize UI
        self._setup_ui()
        self._add_welcome_message()
    
    def _setup_ui(self) -> None:
        """Set up the TUI layout and key bindings."""
        
        # Create layout
        layout = Layout(
            HSplit([
                # Main output area (expandable) - now uses BufferControl for text selection
                Frame(
                    Window(
                        BufferControl(buffer=self.output_buffer),
                        wrap_lines=True,
                    ),
                    title="OpenHands CLI (Tab to focus, mouse/Shift+arrows to select, Ctrl+C to copy)"
                ),
                # Input area (fixed height)
                Frame(
                    Window(
                        BufferControl(buffer=self.input_buffer),
                        height=1,
                    ),
                    title="Input (Press Enter to send, Tab to switch focus, Ctrl+D to exit)"
                ),
            ])
        )
        
        # Set initial focus to input buffer
        layout.focus(self.input_buffer)
        
        # Create custom key bindings
        custom_kb = KeyBindings()
        
        @custom_kb.add('enter')
        def handle_enter(event):
            """Handle Enter key - process user input only if in input buffer."""
            if event.app.layout.current_buffer == self.input_buffer:
                asyncio.create_task(self._handle_user_input())
        
        @custom_kb.add('c-d')
        def handle_ctrl_d(event):
            """Handle Ctrl+D - exit with confirmation."""
            asyncio.create_task(self._handle_exit())
        
        # Tab to switch between buffers
        @custom_kb.add('tab')
        def switch_buffer(event):
            """Switch focus between output and input buffers."""
            if event.app.layout.current_buffer == self.input_buffer:
                event.app.layout.focus(self.output_buffer)
            else:
                event.app.layout.focus(self.input_buffer)
        
        # Create condition for when output buffer is focused
        output_focused = Condition(lambda: self.app and self.app.layout.current_buffer == self.output_buffer)
        
        # Prevent common editing keys in output buffer (but allow selection and copy)
        editing_keys = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                       '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'space', 'backspace', 'delete']
        
        for key in editing_keys:
            @custom_kb.add(key, filter=output_focused)
            def prevent_output_edit(event, key=key):
                """Prevent editing in the output buffer - redirect focus to input."""
                self.app.layout.focus(self.input_buffer)
                # Re-send the key to the input buffer
                if key == 'space':
                    self.input_buffer.insert_text(' ')
                elif len(key) == 1:  # Single character
                    self.input_buffer.insert_text(key)
        
        # Load default key bindings (includes text selection with Shift+arrows, Ctrl+C for copy, etc.)
        default_kb = load_key_bindings()
        
        # Merge custom and default key bindings
        from prompt_toolkit.key_binding.key_bindings import merge_key_bindings
        kb = merge_key_bindings([default_kb, custom_kb])
        
        # Create application
        self.app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=True,
        )
    
    def _add_welcome_message(self) -> None:
        """Add welcome message to output."""
        self.output_content.extend([
            "╭─────────────────────────────────────────────────────────────────╮",
            "│                     🤖 OpenHands CLI                           │",
            "│                                                                 │",
            f"│  Conversation ID: {str(self.conversation_id):<36} │",
            "│                                                                 │",
            "│  Available commands:                                            │",
            "│    /help     - Show help information                           │",
            "│    /exit     - Exit the application                            │",
            "│    /clear    - Clear the screen                                │",
            "│    /new      - Start a new conversation                        │",
            "│    /status   - Show conversation status                        │",
            "│    /settings - Open settings                                   │",
            "│    /mcp      - Show MCP information                            │",
            "│    /confirm  - Toggle confirmation mode                        │",
            "│    /resume   - Resume paused conversation                      │",
            "│                                                                 │",
            "│  Controls:                                                      │",
            "│    Enter     - Send message to agent                           │",
            "│    Tab       - Switch focus between output and input           │",
            "│    Ctrl+C    - Copy selected text to clipboard                 │",
            "│    Ctrl+D    - Exit the application                            │",
            "│    Mouse     - Select text for copying                         │",
            "│                                                                 │",
            "│  Type your message and press Enter to send it to the agent.    │",
            "╰─────────────────────────────────────────────────────────────────╯",
            "",
        ])
        if self.resume_conversation_id:
            self.output_content.append("📂 Resuming previous conversation...")
        else:
            self.output_content.append("🚀 Ready to start a new conversation!")
        self.output_content.append("")
        
        # Update the buffer with the welcome message
        self._update_output_buffer()
    
    def _add_output(self, text: str, style: str = "") -> None:
        """Add text to output area."""
        if style:
            # For now, just add the text - we can enhance styling later
            self.output_content.append(text)
        else:
            self.output_content.append(text)
        
        # Update the output buffer with all content
        self._update_output_buffer()
        
        # Trigger UI refresh
        if self.app:
            self.app.invalidate()
    
    def _update_output_buffer(self) -> None:
        """Update the output buffer with current content."""
        content = "\n".join(self.output_content)
        self.output_buffer.document = Document(content, cursor_position=len(content))
    

    
    def _clear_output(self) -> None:
        """Clear the output area."""
        self.output_content.clear()
        self._add_welcome_message()
        self._update_output_buffer()
    
    async def _handle_user_input(self) -> None:
        """Handle user input from the input buffer."""
        user_input = self.input_buffer.text.strip()
        if not user_input:
            return
        
        # Clear input buffer
        self.input_buffer.text = ""
        
        # Add user input to output
        self._add_output(f"> {user_input}")
        
        # Handle commands
        command = user_input.lower()
        
        if command == "/exit":
            await self._handle_exit()
            return
        
        elif command == "/help":
            self._add_output("Available commands:")
            self._add_output("  /help     - Show this help")
            self._add_output("  /exit     - Exit the application")
            self._add_output("  /clear    - Clear the screen")
            self._add_output("  /new      - Start a new conversation")
            self._add_output("  /status   - Show conversation status")
            self._add_output("  /settings - Open settings")
            self._add_output("  /mcp      - Show MCP information")
            self._add_output("  /confirm  - Toggle confirmation mode")
            self._add_output("  /resume   - Resume paused conversation")
            self._add_output("")
            return
        
        elif command == "/clear":
            self._clear_output()
            return
        
        elif command == "/new":
            try:
                self.conversation_id = uuid.uuid4()
                self.runner = None
                self.conversation = None
                self._clear_output()
                self._add_output("✓ Started fresh conversation")
                self._add_output("")
            except Exception as e:
                self._add_output(f"❌ Error starting fresh conversation: {e}")
            return
        
        elif command == "/status":
            if self.conversation is not None:
                # For now, show basic status - can be enhanced later
                status = self.conversation.state.execution_status
                self._add_output(f"📊 Conversation Status: {status}")
                self._add_output(f"🕐 Session started: {self.session_start_time}")
            else:
                self._add_output("⚠️  No active conversation")
            return
        
        elif command == "/settings":
            self._add_output("⚙️  Settings screen would open here (not implemented in TUI yet)")
            return
        
        elif command == "/mcp":
            self._add_output("🔌 MCP information would be shown here (not implemented in TUI yet)")
            return
        
        elif command == "/confirm":
            if self.runner is not None:
                self.runner.toggle_confirmation_mode()
                new_status = "enabled" if self.runner.is_confirmation_mode_active else "disabled"
            else:
                new_status = "disabled (no active conversation)"
            self._add_output(f"🔄 Confirmation mode {new_status}")
            return
        
        elif command == "/resume":
            if not self.runner:
                self._add_output("⚠️  No active conversation running...")
                return
            
            conversation = self.runner.conversation
            if not (
                conversation.state.execution_status == ConversationExecutionStatus.PAUSED
                or conversation.state.execution_status == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
            ):
                self._add_output("❌ No paused conversation to resume...")
                return
            
            # Resume without new message
            await self._process_message(None)
            return
        
        # Regular message - send to agent
        message = Message(
            role="user",
            content=[TextContent(text=user_input)],
        )
        
        await self._process_message(message)
    
    async def _process_message(self, message: Message | None) -> None:
        """Process a message with the agent."""
        try:
            # Initialize conversation if needed
            if not self.runner or not self.conversation:
                self.conversation = self._setup_conversation_with_tui_visualizer(self.conversation_id)
                self.runner = ConversationRunner(
                    self.conversation,
                    output_callback=self._add_output,
                    error_callback=lambda msg: self._add_output(f"❌ {msg}")
                )
            
            # Check if agent is currently running
            if self.runner.is_running and message:
                try:
                    self.runner.send_message_while_running(message)
                    self._add_output("📤 Message sent to running agent...")
                except RuntimeError:
                    # Agent stopped running, process normally
                    self.runner.process_message(message)
            else:
                # Process message normally
                if message:
                    self.runner.process_message(message)
                else:
                    # Resume case
                    self.runner.conversation.resume()
                    self._add_output("▶️  Conversation resumed")
            
            self._add_output("")  # Add spacing
            
        except Exception as e:
            self._add_output(f"❌ Error processing message: {e}")
            import traceback
            self._add_output(f"🔍 Details: {traceback.format_exc()}")
    
    async def _handle_exit(self) -> None:
        """Handle exit request with confirmation."""
        # For now, just exit - can add confirmation dialog later
        self._add_output("👋 Goodbye!")
        self._add_output(f"💡 Conversation ID: {self.conversation_id}")
        self._add_output(f"💡 Resume with: openhands --resume {self.conversation_id}")
        
        if self.app:
            self.app.exit()
    
    def _setup_conversation_with_tui_visualizer(self, conversation_id):
        """Setup conversation with TUI-compatible visualizer."""
        from uuid import UUID
        from openhands.sdk import Agent, BaseConversation, Conversation, Workspace
        from openhands.sdk.security.confirmation_policy import AlwaysConfirm
        from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
        from openhands_cli.locations import CONVERSATIONS_DIR, WORK_DIR
        from openhands_cli.setup import load_agent_specs

        self._add_output("🔧 Initializing agent...")

        agent = load_agent_specs(str(conversation_id))

        # Create TUI visualizer that sends output to our TUI
        tui_visualizer = TUIVisualizer(output_callback=self._add_output)

        # Create conversation with TUI visualizer
        conversation: BaseConversation = Conversation(
            agent=agent,
            workspace=Workspace(working_dir=WORK_DIR),
            persistence_dir=CONVERSATIONS_DIR,
            conversation_id=conversation_id,
            visualizer=tui_visualizer,
        )

        # Set up security analyzer
        conversation.set_security_analyzer(LLMSecurityAnalyzer())
        conversation.set_confirmation_policy(AlwaysConfirm())

        self._add_output(f"✅ Agent initialized with model: {agent.llm.model}")
        return conversation
    
    async def run_async(self) -> None:
        """Run the TUI application asynchronously."""
        if not self.app:
            return
        
        try:
            await self.app.run_async()
        except Exception as e:
            print_formatted_text(HTML(f"<red>TUI Error: {e}</red>"))
            import traceback
            traceback.print_exc()
        finally:
            self._restore_tty()
    
    def _restore_tty(self) -> None:
        """Restore terminal state."""
        try:
            sys.stdout.write("\x1b[?1l\x1b[?2004l")
            sys.stdout.flush()
        except Exception:
            pass


async def run_tui_async(resume_conversation_id: str | None = None) -> None:
    """Run the TUI application asynchronously."""
    tui = OpenHandsTUI(resume_conversation_id)
    await tui.run_async()


def run_tui_cli_entry(resume_conversation_id: str | None = None) -> None:
    """Entry point for TUI CLI - runs the async TUI."""
    try:
        asyncio.run(run_tui_async(resume_conversation_id))
    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
    except EOFError:
        print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))