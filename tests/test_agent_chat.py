"""Tests for agent chat error handling and setup behavior."""

import os
from unittest.mock import MagicMock, patch

import pytest
from libtmux.exc import TmuxCommandNotFound


class TestAgentChatTmuxHandling:
    """Test friendly error handling when tmux is missing."""

    @patch.dict(os.environ, {"LITELLM_API_KEY": "dummy-key"}, clear=False)
    @patch("openhands_cli.agent_chat.print_formatted_text")
    @patch("openhands_cli.agent_chat.BashExecutor", side_effect=TmuxCommandNotFound)
    @patch("openhands_cli.agent_chat.LLM")
    def test_setup_agent_handles_missing_tmux(
        self,
        mock_llm: MagicMock,
        _mock_bash: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        """setup_agent should catch TmuxCommandNotFound and print helpful guidance."""
        from openhands_cli.agent_chat import setup_agent

        llm, agent, conv = setup_agent()

        assert (llm, agent, conv) == (None, None, None)

        # Combine printed HTML strings for assertion
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        assert "tmux is not installed or not found in PATH" in printed
        assert "requires tmux" in printed
        assert "Install examples" in printed

    @patch.dict(os.environ, {"LITELLM_API_KEY": "dummy-key"}, clear=False)
    @patch("openhands_cli.agent_chat.print_formatted_text")
    @patch(
        "openhands_cli.agent_chat.BashExecutor",
        side_effect=Exception("TmuxCommandNotFound"),
    )
    @patch("openhands_cli.agent_chat.LLM")
    def test_setup_agent_handles_missing_tmux_by_name(
        self,
        mock_llm: MagicMock,
        _mock_bash: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        """Also handle when only the exception class name matches (defensive)."""
        from openhands_cli.agent_chat import setup_agent

        llm, agent, conv = setup_agent()

        assert (llm, agent, conv) == (None, None, None)
        printed = "\n".join(str(call.args[0]) for call in mock_print.call_args_list)
        assert "tmux is not installed or not found in PATH" in printed
