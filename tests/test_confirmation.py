#!/usr/bin/env python3
"""
Tests for simplified confirmation mode functionality.
"""

from typing import Any
from unittest.mock import patch

import pytest

from openhands_cli.confirmation import (
    ConfirmationMode,
    display_action_info,
)


class TestConfirmationMode:
    """Test the confirmation mode functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.confirmation_mode = ConfirmationMode()

    def test_default_enabled(self) -> None:
        """Test that confirmation is enabled by default."""
        assert self.confirmation_mode.enabled is True
        assert self.confirmation_mode.should_confirm() is True

    def test_set_enabled_true(self) -> None:
        """Test enabling confirmation mode."""
        self.confirmation_mode.set_enabled(True)
        assert self.confirmation_mode.enabled is True
        assert self.confirmation_mode.should_confirm() is True

    def test_set_enabled_false(self) -> None:
        """Test disabling confirmation mode."""
        self.confirmation_mode.set_enabled(False)
        assert self.confirmation_mode.enabled is False
        assert self.confirmation_mode.should_confirm() is False


class TestConfirmationIntegration:
    """Test integration of confirmation functionality."""

    @patch("openhands_cli.confirmation.print_formatted_text")
    def test_display_action_info_bash(self, mock_print: Any) -> None:
        """Test action info display for bash commands."""
        display_action_info("execute_bash", {"command": "ls -la"})
        mock_print.assert_called_once()

        # Check that the call contains the command
        call_args = mock_print.call_args[0][0]
        assert "ls -la" in str(call_args)

    @patch("openhands_cli.confirmation.print_formatted_text")
    def test_display_action_info_file_editor(self, mock_print: Any) -> None:
        """Test action info display for file editor commands."""
        display_action_info(
            "str_replace_editor", {"command": "create", "path": "test.txt"}
        )
        mock_print.assert_called_once()

        # Check that the call contains the operation and path
        call_args = mock_print.call_args[0][0]
        assert "create" in str(call_args)
        assert "test.txt" in str(call_args)

    @patch("openhands_cli.confirmation.print_formatted_text")
    def test_display_action_info_unknown(self, mock_print: Any) -> None:
        """Test action info display for unknown action types."""
        display_action_info("unknown_action", {})
        mock_print.assert_called_once()

        # Check that the call contains the action type
        call_args = mock_print.call_args[0][0]
        assert "unknown_action" in str(call_args)


if __name__ == "__main__":
    pytest.main([__file__])
