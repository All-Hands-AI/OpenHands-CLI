#!/usr/bin/env python3

from textual.app import App, ComposeResult
from textual.widgets import Input, Static


class TestInputApp(App):
    """Simple test app to check Input widget visibility."""
    
    CSS = """
    Input {
        background: black;
        color: white;
        border: solid blue;
        height: 1;
        margin: 1;
    }
    
    Input:focus {
        border: solid cyan;
        background: #111111;
        color: white;
    }
    
    Static {
        color: green;
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Test Input Widget - Type something below:")
        yield Input(placeholder="Type here...", id="test_input")
        yield Static("If you can see what you type above, the input works!")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.query_one(Static).update(f"You typed: {event.value}")


if __name__ == "__main__":
    app = TestInputApp()
    app.run()