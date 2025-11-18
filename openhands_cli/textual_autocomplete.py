"""
Autocomplete Input widget for Textual with command completion support.
"""

from typing import List, Optional
from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.message import Message
from textual.widgets import Input, ListView, ListItem, Label
from textual.widget import Widget


class AutocompleteInput(Widget):
    """Input widget with autocomplete dropdown for commands."""
    
    # Available commands for autocomplete
    COMMANDS = [
        "/exit",
        "/help", 
        "/settings",
    ]
    
    class Submitted(Message):
        """Message sent when input is submitted."""
        
        def __init__(self, input: "AutocompleteInput", value: str) -> None:
            self.input = input
            self.value = value
            super().__init__()
        
        @property
        def control(self) -> "AutocompleteInput":
            """Alias for self.input."""
            return self.input
    
    def __init__(self, placeholder: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self._suggestions: List[str] = []
        self._show_dropdown = False
        self._selected_suggestion = 0
    
    def compose(self) -> ComposeResult:
        """Create the autocomplete input layout."""
        with Container(id="autocomplete_container"):
            yield Input(placeholder=self.placeholder, id="main_input")
            with Container(id="dropdown_container"):
                yield ListView(id="suggestions_list")
    
    async def on_mount(self) -> None:
        """Initialize the widget when mounted."""
        # Hide dropdown initially
        dropdown = self.query_one("#dropdown_container")
        dropdown.display = False
        
        # Focus the input
        input_widget = self.query_one("#main_input", Input)
        input_widget.focus()
    
    @on(Input.Changed, "#main_input")
    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input text changes for autocomplete."""
        text = event.value
        
        # Check if we should show autocomplete
        if text.startswith("/"):
            # Find matching commands
            self._suggestions = [
                cmd for cmd in self.COMMANDS 
                if cmd.lower().startswith(text.lower())
            ]
            
            if self._suggestions:
                await self._show_suggestions()
            else:
                await self._hide_suggestions()
        else:
            await self._hide_suggestions()
    
    @on(Input.Submitted, "#main_input")
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        # Clear the input
        event.input.value = ""
        
        # Hide suggestions
        await self._hide_suggestions()
        
        # Post the submitted message
        self.post_message(self.Submitted(self, event.value))
    
    @on(Key)
    async def on_key(self, event: Key) -> None:
        """Handle key events for dropdown navigation."""
        if not self._show_dropdown:
            return
        
        if event.key == "down":
            # Move down in suggestions
            if self._selected_suggestion < len(self._suggestions) - 1:
                self._selected_suggestion += 1
                await self._update_selection()
            event.prevent_default()
        
        elif event.key == "up":
            # Move up in suggestions
            if self._selected_suggestion > 0:
                self._selected_suggestion -= 1
                await self._update_selection()
            event.prevent_default()
        
        elif event.key == "tab" or event.key == "enter":
            # Accept selected suggestion
            if self._suggestions:
                selected_cmd = self._suggestions[self._selected_suggestion]
                input_widget = self.query_one("#main_input", Input)
                input_widget.value = selected_cmd
                input_widget.cursor_position = len(selected_cmd)
                await self._hide_suggestions()
            event.prevent_default()
        
        elif event.key == "escape":
            # Hide suggestions
            await self._hide_suggestions()
            event.prevent_default()
    
    async def _show_suggestions(self) -> None:
        """Show the autocomplete dropdown."""
        if not self._suggestions:
            return
        
        self._show_dropdown = True
        self._selected_suggestion = 0
        
        # Update the ListView with suggestions
        suggestions_list = self.query_one("#suggestions_list", ListView)
        suggestions_list.clear()
        
        for i, suggestion in enumerate(self._suggestions):
            item = ListItem(Label(suggestion))
            if i == self._selected_suggestion:
                item.add_class("selected")
            suggestions_list.append(item)
        
        # Show the dropdown
        dropdown = self.query_one("#dropdown_container")
        dropdown.display = True
    
    async def _hide_suggestions(self) -> None:
        """Hide the autocomplete dropdown."""
        self._show_dropdown = False
        dropdown = self.query_one("#dropdown_container")
        dropdown.display = False
    
    async def _update_selection(self) -> None:
        """Update the visual selection in the dropdown."""
        suggestions_list = self.query_one("#suggestions_list", ListView)
        
        # Remove selection from all items
        for item in suggestions_list.children:
            item.remove_class("selected")
        
        # Add selection to current item
        if 0 <= self._selected_suggestion < len(suggestions_list.children):
            suggestions_list.children[self._selected_suggestion].add_class("selected")
    
    @on(ListView.Selected, "#suggestions_list")
    async def on_suggestion_selected(self, event: ListView.Selected) -> None:
        """Handle suggestion selection from ListView."""
        if event.item and hasattr(event.item, 'children'):
            # Get the selected command text
            label = event.item.children[0]  # First child should be the Label
            if hasattr(label, 'renderable'):
                selected_cmd = str(label.renderable)
                
                # Set the input value
                input_widget = self.query_one("#main_input", Input)
                input_widget.value = selected_cmd
                input_widget.cursor_position = len(selected_cmd)
                
                # Hide suggestions
                await self._hide_suggestions()
                
                # Focus back to input
                input_widget.focus()
    
    def focus(self) -> None:
        """Focus the input widget."""
        input_widget = self.query_one("#main_input", Input)
        input_widget.focus()
    
    @property
    def value(self) -> str:
        """Get the current input value."""
        input_widget = self.query_one("#main_input", Input)
        return input_widget.value
    
    @value.setter
    def value(self, new_value: str) -> None:
        """Set the input value."""
        input_widget = self.query_one("#main_input", Input)
        input_widget.value = new_value