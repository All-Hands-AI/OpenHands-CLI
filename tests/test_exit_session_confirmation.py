#!/usr/bin/env python3
"""
Tests for exit_session_confirmation functionality in OpenHands CLI.
"""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from openhands_cli.user_actions.exit_session_confirmation import exit_session_confirmation
from openhands_cli.user_actions.types import UserConfirmation


class TestExitSessionConfirmation:
    """Test suite for exit_session_confirmation functionality."""

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_accept(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation returns ACCEPT when user selects 'Yes, proceed'."""
        mock_cli_confirm.return_value = 0  # First option (Yes, proceed)

        result = exit_session_confirmation()
        
        assert result == UserConfirmation.ACCEPT
        mock_cli_confirm.assert_called_once_with(
            "Terminate session?", 
            ["Yes, proceed", "No, dismiss"]
        )

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_reject(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation returns REJECT when user selects 'No, dismiss'."""
        mock_cli_confirm.return_value = 1  # Second option (No, dismiss)

        result = exit_session_confirmation()
        
        assert result == UserConfirmation.REJECT
        mock_cli_confirm.assert_called_once_with(
            "Terminate session?", 
            ["Yes, proceed", "No, dismiss"]
        )

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_invalid_index_defaults_to_reject(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation returns REJECT for invalid index."""
        mock_cli_confirm.return_value = 999  # Invalid index

        result = exit_session_confirmation()
        
        assert result == UserConfirmation.REJECT
        mock_cli_confirm.assert_called_once_with(
            "Terminate session?", 
            ["Yes, proceed", "No, dismiss"]
        )

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_negative_index_defaults_to_reject(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation returns REJECT for negative index."""
        mock_cli_confirm.return_value = -1  # Negative index

        result = exit_session_confirmation()
        
        assert result == UserConfirmation.REJECT
        mock_cli_confirm.assert_called_once_with(
            "Terminate session?", 
            ["Yes, proceed", "No, dismiss"]
        )

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_keyboard_interrupt_handled(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation handles KeyboardInterrupt gracefully."""
        mock_cli_confirm.side_effect = KeyboardInterrupt()

        # KeyboardInterrupt should be raised since cli_confirm is not escapable
        with pytest.raises(KeyboardInterrupt):
            exit_session_confirmation()

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_eof_error_handled(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation handles EOFError gracefully."""
        mock_cli_confirm.side_effect = EOFError()

        # EOFError should be raised since cli_confirm is not escapable
        with pytest.raises(EOFError):
            exit_session_confirmation()

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_uses_non_escapable_mode(self, mock_cli_confirm: Any) -> None:
        """Test that exit_session_confirmation calls cli_confirm in non-escapable mode."""
        mock_cli_confirm.return_value = 0

        exit_session_confirmation()
        
        # Verify cli_confirm is called without escapable=True parameter
        # This means Control+C and Control+P should not be handled by cli_confirm
        mock_cli_confirm.assert_called_once_with(
            "Terminate session?", 
            ["Yes, proceed", "No, dismiss"]
        )
        
        # Verify that escapable parameter is not passed (defaults to False)
        call_args = mock_cli_confirm.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert "escapable" not in kwargs or kwargs.get("escapable") is False

    def test_exit_session_confirmation_options_mapping(self) -> None:
        """Test that the options mapping is correct."""
        with patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm") as mock_cli_confirm:
            # Test index 0 maps to ACCEPT
            mock_cli_confirm.return_value = 0
            result = exit_session_confirmation()
            assert result == UserConfirmation.ACCEPT

            # Test index 1 maps to REJECT
            mock_cli_confirm.return_value = 1
            result = exit_session_confirmation()
            assert result == UserConfirmation.REJECT

    def test_exit_session_confirmation_question_and_options(self) -> None:
        """Test that the correct question and options are passed to cli_confirm."""
        with patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm") as mock_cli_confirm:
            mock_cli_confirm.return_value = 0
            
            exit_session_confirmation()
            
            # Verify the exact question and options
            mock_cli_confirm.assert_called_once_with(
                "Terminate session?",
                ["Yes, proceed", "No, dismiss"]
            )

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_control_c_not_handled_by_default(self, mock_cli_confirm: Any) -> None:
        """Test that Control+C is not handled by cli_confirm when escapable=False (default)."""
        # Since exit_session_confirmation calls cli_confirm without escapable=True,
        # Control+C should not be handled by the key bindings in cli_confirm
        mock_cli_confirm.return_value = 0
        
        result = exit_session_confirmation()
        
        assert result == UserConfirmation.ACCEPT
        
        # Verify cli_confirm was called without escapable=True
        call_args = mock_cli_confirm.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert kwargs.get("escapable", False) is False

    @patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm")
    def test_exit_session_confirmation_control_p_not_handled_by_default(self, mock_cli_confirm: Any) -> None:
        """Test that Control+P is not handled by cli_confirm when escapable=False (default)."""
        # Since exit_session_confirmation calls cli_confirm without escapable=True,
        # Control+P should not be handled by the key bindings in cli_confirm
        mock_cli_confirm.return_value = 1
        
        result = exit_session_confirmation()
        
        assert result == UserConfirmation.REJECT
        
        # Verify cli_confirm was called without escapable=True
        call_args = mock_cli_confirm.call_args
        assert call_args is not None
        args, kwargs = call_args
        assert kwargs.get("escapable", False) is False

    def test_exit_session_confirmation_return_type(self) -> None:
        """Test that exit_session_confirmation returns UserConfirmation enum."""
        with patch("openhands_cli.user_actions.exit_session_confirmation.cli_confirm") as mock_cli_confirm:
            mock_cli_confirm.return_value = 0
            result = exit_session_confirmation()
            assert isinstance(result, UserConfirmation)
            
            mock_cli_confirm.return_value = 1
            result = exit_session_confirmation()
            assert isinstance(result, UserConfirmation)