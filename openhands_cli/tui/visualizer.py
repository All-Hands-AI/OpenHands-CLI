import logging
import re

from rich.console import Console, Group
from rich.text import Text

from openhands.sdk.conversation.visualizer.base import (
    ConversationVisualizerBase,
)
from openhands.sdk.conversation.visualizer.default import (
    EVENT_VISUALIZATION_CONFIG,
    build_event_block,
)
from openhands.sdk.event import (
    ConversationStateUpdateEvent,
    MessageEvent,
    SystemPromptEvent,
)
from openhands.sdk.event.base import Event


logger = logging.getLogger(__name__)


# Color constants for highlighting
_THOUGHT_COLOR = "bright_black"
_ACTION_COLOR = "blue"
_OBSERVATION_COLOR = "yellow"
_ERROR_COLOR = "red"

DEFAULT_HIGHLIGHT_REGEX = {
    r"^Reasoning:": f"bold {_THOUGHT_COLOR}",
    r"^Thought:": f"bold {_THOUGHT_COLOR}",
    r"^Action:": f"bold {_ACTION_COLOR}",
    r"^Arguments:": f"bold {_ACTION_COLOR}",
    r"^Tool:": f"bold {_OBSERVATION_COLOR}",
    r"^Result:": f"bold {_OBSERVATION_COLOR}",
    r"^Rejection Reason:": f"bold {_ERROR_COLOR}",
    # Markdown-style
    r"\*\*(.*?)\*\*": "bold",
    r"\*(.*?)\*": "italic",
}


class CLIVisualizer(ConversationVisualizerBase):
    """Handles visualization of conversation events with Rich formatting.

    Provides Rich-formatted output with horizontal rules and complete content display.
    """

    _console: Console
    _skip_user_messages: bool
    _highlight_patterns: dict[str, str]

    def __init__(
        self,
        highlight_regex: dict[str, str] | None = DEFAULT_HIGHLIGHT_REGEX,
        skip_user_messages: bool = False,
    ):
        """Initialize the visualizer.

        Args:
            highlight_regex: Dictionary mapping regex patterns to Rich color styles
                           for highlighting keywords in the visualizer.
                           For example: {"Reasoning:": "bold blue",
                           "Thought:": "bold green"}
            skip_user_messages: If True, skip displaying user messages. Useful for
                                scenarios where user input is not relevant to show.
        """
        super().__init__()
        self._console = Console()
        self._skip_user_messages = skip_user_messages
        self._highlight_patterns = highlight_regex or {}

    def on_event(self, event: Event) -> None:
        """Main event handler that displays events with Rich formatting."""
        output = self._create_event_block(event)
        if output:
            self._console.print(output)

    def _apply_highlighting(self, text: Text) -> Text:
        """Apply regex-based highlighting to text content.

        Args:
            text: The Rich Text object to highlight

        Returns:
            A new Text object with highlighting applied
        """
        if not self._highlight_patterns:
            return text

        # Create a copy to avoid modifying the original
        highlighted = text.copy()

        # Apply each pattern using Rich's built-in highlight_regex method
        for pattern, style in self._highlight_patterns.items():
            pattern_compiled = re.compile(pattern, re.MULTILINE)
            highlighted.highlight_regex(pattern_compiled, style)

        return highlighted

    def _create_event_block(self, event: Event) -> Group | None:
        """Create a Rich event block for the event with full detail."""
        # Look up visualization config for this event type
        config = EVENT_VISUALIZATION_CONFIG.get(type(event))

        if not config:
            # Warn about unknown event types and skip
            logger.warning(
                "Event type %s is not registered in EVENT_VISUALIZATION_CONFIG. "
                "Skipping visualization.",
                event.__class__.__name__,
            )
            return None

        # Check if this event type should be skipped
        # CLI skips SystemPromptEvent and ConversationStateUpdateEvent
        if config.skip or isinstance(
            event, SystemPromptEvent | ConversationStateUpdateEvent
        ):
            return None

        # Check if we should skip user messages based on runtime configuration
        if (
            self._skip_user_messages
            and isinstance(event, MessageEvent)
            and event.llm_message
            and event.llm_message.role == "user"
        ):
            return None

        # Use the event's visualize property for content
        content = event.visualize

        if not content.plain.strip():
            return None

        # Apply highlighting if configured
        if self._highlight_patterns:
            content = self._apply_highlighting(content)

        # Resolve title (may be a string or callable)
        if callable(config.title):
            title = config.title(event)
        else:
            title = config.title

        # Resolve color (may be a string or callable)
        title_color = config.color(event) if callable(config.color) else config.color

        # Build subtitle if needed
        subtitle = self._format_metrics_subtitle() if config.show_metrics else None

        return build_event_block(
            content=content,
            title=title,
            title_color=title_color,
            subtitle=subtitle,
        )

    def _format_metrics_subtitle(self) -> str | None:
        """Format LLM metrics as a visually appealing subtitle string with icons,
        colors, and k/m abbreviations using conversation stats."""
        stats = self.conversation_stats
        if not stats:
            return None

        combined_metrics = stats.get_combined_metrics()
        if not combined_metrics or not combined_metrics.accumulated_token_usage:
            return None

        usage = combined_metrics.accumulated_token_usage
        cost = combined_metrics.accumulated_cost or 0.0

        # helper: 1234 -> "1.2K", 1200000 -> "1.2M"
        def abbr(n: int | float) -> str:
            n = int(n or 0)
            if n >= 1_000_000_000:
                val, suffix = n / 1_000_000_000, "B"
            elif n >= 1_000_000:
                val, suffix = n / 1_000_000, "M"
            elif n >= 1_000:
                val, suffix = n / 1_000, "K"
            else:
                return str(n)
            return f"{val:.2f}".rstrip("0").rstrip(".") + suffix

        input_tokens = abbr(usage.prompt_tokens or 0)
        output_tokens = abbr(usage.completion_tokens or 0)

        # Cache hit rate (prompt + cache)
        prompt = usage.prompt_tokens or 0
        cache_read = usage.cache_read_tokens or 0
        cache_rate = f"{(cache_read / prompt * 100):.2f}%" if prompt > 0 else "N/A"
        reasoning_tokens = usage.reasoning_tokens or 0

        # Cost
        cost_str = f"{cost:.4f}" if cost > 0 else "0.00"

        # Build with fixed color scheme
        parts: list[str] = []
        parts.append(f"[cyan]↑ input {input_tokens}[/cyan]")
        parts.append(f"[magenta]cache hit {cache_rate}[/magenta]")
        if reasoning_tokens > 0:
            parts.append(f"[yellow] reasoning {abbr(reasoning_tokens)}[/yellow]")
        parts.append(f"[blue]↓ output {output_tokens}[/blue]")
        parts.append(f"[green]$ {cost_str}[/green]")

        return "Tokens: " + " • ".join(parts)
