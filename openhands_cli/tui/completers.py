"""Auto-completion functionality for TUI components."""

from abc import ABC
from collections.abc import Callable, Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from .styles import COMPLETION_STYLE


class BaseCompleter(Completer, ABC):
    """Base class for all completers with common completion logic."""

    def __init__(
        self,
        options: dict[str, str],
        prefix_filter: str | None = None,
        text_preprocessor: Callable[[str], str] = str.strip,
    ):
        """Initialize the completer.

        Args:
            options: Dictionary mapping option keys to descriptions
            prefix_filter: Optional prefix that must be present (e.g., "/")
            text_preprocessor: Function to preprocess text (strip, lstrip, etc.)
        """
        self.options = options
        self.prefix_filter = prefix_filter
        self.text_preprocessor = text_preprocessor

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """Generate completions based on current document text."""
        text = document.text_before_cursor

        # Apply prefix filter if specified
        if self.prefix_filter and not text.startswith(self.prefix_filter):
            return

        # Preprocess text
        processed_text = self.text_preprocessor(text)

        # Generate completions for matching options
        for option, description in self.options.items():
            if option.startswith(processed_text):
                yield Completion(
                    text=option,
                    start_position=-len(processed_text),
                    display=f"{option} - {description}",
                    style=COMPLETION_STYLE,
                )


class CommandCompleter(BaseCompleter):
    """Completer for main CLI commands."""

    def __init__(self, commands: dict[str, str]):
        """Initialize with commands dictionary."""
        super().__init__(
            options=commands,
            prefix_filter="/",
            text_preprocessor=str.lstrip,
        )
