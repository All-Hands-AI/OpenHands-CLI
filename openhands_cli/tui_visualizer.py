"""TUI-compatible visualizer that captures agent events for display in the TUI."""

from typing import Callable

from openhands.sdk.conversation.visualizer.base import (
    ConversationVisualizerBase,
)
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
    PauseEvent,
    SystemPromptEvent,
    UserRejectObservation,
)
from openhands.sdk.event.base import Event
from openhands.sdk.event.condenser import Condensation





class TUIVisualizer(ConversationVisualizerBase):
    """TUI-compatible visualizer that captures agent events for display in the TUI."""

    _skip_user_messages: bool
    _output_callback: Callable[[str], None]

    def __init__(
        self,
        output_callback: Callable[[str], None],
        name: str | None = None,
        skip_user_messages: bool = False,
    ):
        """Initialize the TUI visualizer.

        Args:
            output_callback: Function to call with formatted output for the TUI
            name: Optional name to prefix in panel titles to identify
                                  which agent/conversation is speaking.
            skip_user_messages: If True, skip displaying user messages. Useful for
                                scenarios where user input is not relevant to show.
        """
        super().__init__(
            name=name,
        )
        self._skip_user_messages = skip_user_messages
        self._output_callback = output_callback

    def on_event(self, event: Event) -> None:
        """Main event handler that displays events in plain text format."""
        formatted_output = self._format_event_for_tui(event)
        if formatted_output:
            self._output_callback(formatted_output)

    def _format_event_for_tui(self, event: Event) -> str | None:
        """Format event as plain text for TUI display."""
        # Use the event's visualize property for content
        content = event.visualize
        
        if not content.plain.strip():
            return None
        
        # Get plain text content
        text_content = content.plain
        
        # Create simple text-based formatting
        agent_name = f"{self._name} " if self._name else ""
        
        # Don't emit system prompt in CLI
        if isinstance(event, SystemPromptEvent):
            return None
        elif isinstance(event, ActionEvent):
            if event.action is None:
                title = f"🤖 {agent_name}Agent Action (Not Executed)"
            else:
                title = f"🤖 {agent_name}Agent Action"
            return self._create_text_box(title, text_content)
        elif isinstance(event, ObservationEvent):
            title = f"👁️  {agent_name}Observation"
            return self._create_text_box(title, text_content)
        elif isinstance(event, UserRejectObservation):
            title = f"❌ {agent_name}User Rejected Action"
            return self._create_text_box(title, text_content)
        elif isinstance(event, MessageEvent):
            if (
                self._skip_user_messages
                and event.llm_message
                and event.llm_message.role == "user"
            ):
                return None
            assert event.llm_message is not None
            
            if event.llm_message.role == "user":
                title = f"👤 User Message to {agent_name}Agent"
            else:
                title = f"🤖 Message from {agent_name}Agent"
            return self._create_text_box(title, text_content)
        elif isinstance(event, AgentErrorEvent):
            title = f"💥 {agent_name}Agent Error"
            return self._create_text_box(title, text_content)
        elif isinstance(event, PauseEvent):
            title = f"⏸️  {agent_name}User Paused"
            return self._create_text_box(title, text_content)
        elif isinstance(event, Condensation):
            title = f"📦 {agent_name}Condensation"
            return self._create_text_box(title, text_content)
        else:
            # Fallback for unknown event types
            title = f"❓ {agent_name}UNKNOWN Event: {event.__class__.__name__}"
            return self._create_text_box(title, text_content)
    
    def _create_text_box(self, title: str, content: str) -> str:
        """Create a simple text box with title and content."""
        # Create a simple border
        border_char = "─"
        corner_char = "┌┐└┘"
        side_char = "│"
        
        # Split content into lines and limit width
        max_width = 100
        lines = []
        for line in content.split('\n'):
            if len(line) <= max_width:
                lines.append(line)
            else:
                # Wrap long lines
                while line:
                    lines.append(line[:max_width])
                    line = line[max_width:]
        
        # Calculate box width
        content_width = max(len(title), max((len(line) for line in lines), default=0))
        box_width = min(content_width + 4, max_width + 4)
        
        # Build the box
        result = []
        result.append(f"┌{border_char * (box_width - 2)}┐")
        result.append(f"│ {title:<{box_width - 4}} │")
        result.append(f"├{border_char * (box_width - 2)}┤")
        
        for line in lines:
            result.append(f"│ {line:<{box_width - 4}} │")
        
        result.append(f"└{border_char * (box_width - 2)}┘")
        result.append("")  # Add spacing
        
        return "\n".join(result)