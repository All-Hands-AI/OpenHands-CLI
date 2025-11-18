"""
Textual-based dialog widgets to replace prompt_toolkit dialogs.
"""

from typing import Any, Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static


class ConfirmationDialog(ModalScreen[bool]):
    """A modal confirmation dialog."""

    def __init__(
        self,
        question: str,
        choices: list[str] | None = None,
        initial_selection: int = 0,
    ):
        super().__init__()
        self.question = question
        self.choices = choices or ["Yes", "No"]
        self.initial_selection = initial_selection

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="dialog"):
                yield Static(self.question, id="question")
                with Horizontal(id="buttons"):
                    for i, choice in enumerate(self.choices):
                        variant = "primary" if i == self.initial_selection else "default"
                        yield Button(choice, id=f"choice_{i}", variant=variant)

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id and event.button.id.startswith("choice_"):
            choice_index = int(event.button.id.split("_")[1])
            self.dismiss(choice_index)

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.dismiss(False)
        elif event.key == "enter":
            self.dismiss(self.initial_selection)


class TextInputDialog(ModalScreen[str]):
    """A modal text input dialog."""

    def __init__(
        self,
        question: str,
        placeholder: str = "",
        is_password: bool = False,
        validator: Callable[[str], bool] | None = None,
    ):
        super().__init__()
        self.question = question
        self.placeholder = placeholder
        self.is_password = is_password
        self.validator = validator

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="dialog"):
                yield Static(self.question, id="question")
                yield Input(
                    placeholder=self.placeholder,
                    password=self.is_password,
                    id="text_input"
                )
                with Horizontal(id="buttons"):
                    yield Button("OK", id="ok", variant="primary")
                    yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        self.query_one("#text_input", Input).focus()

    @on(Button.Pressed, "#ok")
    def handle_ok(self) -> None:
        """Handle OK button press."""
        text_input = self.query_one("#text_input", Input)
        value = text_input.value.strip()
        
        if self.validator and not self.validator(value):
            # Could show error message here
            return
            
        self.dismiss(value)

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        """Handle Cancel button press."""
        self.dismiss("")

    @on(Input.Submitted, "#text_input")
    def handle_input_submit(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        value = event.value.strip()
        
        if self.validator and not self.validator(value):
            return
            
        self.dismiss(value)

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.dismiss("")


class SelectionDialog(ModalScreen[int]):
    """A modal selection dialog."""

    def __init__(
        self,
        question: str,
        choices: list[tuple[str, str]],  # (value, display_name) pairs
        initial_selection: int = 0,
    ):
        super().__init__()
        self.question = question
        self.choices = choices
        self.initial_selection = initial_selection

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="dialog"):
                yield Static(self.question, id="question")
                yield Select(
                    options=[(display, value) for value, display in self.choices],
                    value=self.choices[self.initial_selection][0],
                    id="selection"
                )
                with Horizontal(id="buttons"):
                    yield Button("OK", id="ok", variant="primary")
                    yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#ok")
    def handle_ok(self) -> None:
        """Handle OK button press."""
        selection = self.query_one("#selection", Select)
        # Find the index of the selected value
        selected_value = selection.value
        for i, (value, _) in enumerate(self.choices):
            if value == selected_value:
                self.dismiss(i)
                return
        self.dismiss(0)

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        """Handle Cancel button press."""
        self.dismiss(-1)

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.dismiss(-1)
        elif event.key == "enter":
            self.handle_ok()


# CSS for the dialogs
DIALOG_CSS = """
#dialog {
    width: 60;
    height: auto;
    background: $surface;
    border: thick $primary;
    padding: 1;
}

#question {
    text-align: center;
    margin-bottom: 1;
}

#buttons {
    align: center middle;
    margin-top: 1;
}

#buttons Button {
    margin: 0 1;
}

#text_input {
    margin: 1 0;
}

#selection {
    margin: 1 0;
}
"""