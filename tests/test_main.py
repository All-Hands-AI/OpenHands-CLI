"""Tests for main entry point functionality."""

from unittest.mock import MagicMock, patch

from openhands_cli import simple_main


class TestMainEntryPoint:
    """Test the main entry point behavior."""

    @patch("openhands_cli.agent_chat.main")
    def test_main_starts_agent_chat_directly(
        self, mock_run_agent_chat: MagicMock
    ) -> None:
        """Test that main() starts agent chat directly without menu."""
        mock_run_agent_chat.return_value = None

        result = simple_main.main()

        # Should call run_agent_chat directly
        mock_run_agent_chat.assert_called_once()
        assert result == 0

    @patch("openhands_cli.agent_chat.main")
    def test_main_handles_import_error(self, mock_run_agent_chat: MagicMock) -> None:
        """Test that main() handles ImportError gracefully."""
        mock_run_agent_chat.side_effect = ImportError("Missing dependency")

        result = simple_main.main()

        # Should return error code 1
        assert result == 1

    @patch("openhands_cli.agent_chat.main")
    def test_main_handles_keyboard_interrupt(
        self, mock_run_agent_chat: MagicMock
    ) -> None:
        """Test that main() handles KeyboardInterrupt gracefully."""
        mock_run_agent_chat.side_effect = KeyboardInterrupt()

        result = simple_main.main()

        # Should return success code 0 for graceful exit
        assert result == 0

    @patch("openhands_cli.agent_chat.main")
    def test_main_handles_eof_error(self, mock_run_agent_chat: MagicMock) -> None:
        """Test that main() handles EOFError gracefully."""
        mock_run_agent_chat.side_effect = EOFError()

        result = simple_main.main()

        # Should return success code 0 for graceful exit
        assert result == 0

    @patch("openhands_cli.agent_chat.main")
    def test_main_handles_general_exception(
        self, mock_run_agent_chat: MagicMock
    ) -> None:
        """Test that main() handles general exceptions."""
        mock_run_agent_chat.side_effect = Exception("Unexpected error")

        result = simple_main.main()

        # Should return error code 1
        assert result == 1
