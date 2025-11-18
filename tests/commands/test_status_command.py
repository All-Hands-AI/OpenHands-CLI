"""Simplified tests for the /status command functionality."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output.base import DummyOutput

from openhands.sdk.llm.utils.metrics import Metrics, TokenUsage
from openhands_cli.tui.status import display_status
from openhands_cli.user_actions import UserConfirmation


# ---------- Fixtures & helpers ----------


@pytest.fixture
def conversation():
    """Minimal conversation with empty events and pluggable stats."""
    conv = Mock()
    conv.id = uuid4()
    conv.state = Mock(events=[])
    conv.conversation_stats = Mock()
    return conv


def make_metrics(cost=None, usage=None) -> Metrics:
    m = Metrics()
    if cost is not None:
        m.accumulated_cost = cost
    m.accumulated_token_usage = usage
    return m


def call_display_status(conversation, session_start):
    """Call display_status with prints patched; return (mock_pf, mock_pc, text)."""
    with (
        patch("openhands_cli.tui.status.print_formatted_text") as pf,
        patch("openhands_cli.tui.status.print_container") as pc,
    ):
        display_status(conversation, session_start_time=session_start)
        # First container call; extract the Frame/TextArea text
        container = pc.call_args_list[0][0][0]
        text = getattr(container.body, "text", "")
        return pf, pc, str(text)


# ---------- Tests ----------


def test_display_status_box_title(conversation):
    session_start = datetime.now()
    conversation.conversation_stats.get_combined_metrics.return_value = make_metrics()

    with (
        patch("openhands_cli.tui.status.print_formatted_text") as pf,
        patch("openhands_cli.tui.status.print_container") as pc,
    ):
        display_status(conversation, session_start_time=session_start)

        assert pf.called and pc.called

        container = pc.call_args_list[0][0][0]
        assert hasattr(container, "title")
        assert "Usage Metrics" in container.title


@pytest.mark.parametrize(
    "delta,expected",
    [
        (timedelta(seconds=0), "0h 0m"),
        (timedelta(minutes=5, seconds=30), "5m"),
        (timedelta(hours=1, minutes=30, seconds=45), "1h 30m"),
        (timedelta(hours=2, minutes=15, seconds=30), "2h 15m"),
    ],
)
def test_display_status_uptime(conversation, delta, expected):
    session_start = datetime.now() - delta
    conversation.conversation_stats.get_combined_metrics.return_value = make_metrics()

    with (
        patch("openhands_cli.tui.status.print_formatted_text") as pf,
        patch("openhands_cli.tui.status.print_container"),
    ):
        display_status(conversation, session_start_time=session_start)
        # uptime is printed in the 2nd print_formatted_text call
        uptime_call_str = str(pf.call_args_list[1])
        assert expected in uptime_call_str
        # conversation id appears in the first print call
        id_call_str = str(pf.call_args_list[0])
        assert str(conversation.id) in id_call_str


@pytest.mark.parametrize(
    "cost,usage,expecteds",
    [
        # Empty/zero case
        (None, None, ["$0.000000", "0", "0", "0", "0", "0"]),
        # Only cost, usage=None
        (0.05, None, ["$0.050000", "0", "0", "0", "0", "0"]),
        # Full metrics
        (
            0.123456,
            TokenUsage(
                prompt_tokens=1500,
                completion_tokens=800,
                cache_read_tokens=200,
                cache_write_tokens=100,
            ),
            ["$0.123456", "1,500", "800", "200", "100", "2,300"],
        ),
        # Larger numbers (comprehensive)
        (
            1.234567,
            TokenUsage(
                prompt_tokens=5000,
                completion_tokens=3000,
                cache_read_tokens=500,
                cache_write_tokens=250,
            ),
            ["$1.234567", "5,000", "3,000", "500", "250", "8,000"],
        ),
    ],
)
def test_display_status_metrics(conversation, cost, usage, expecteds):
    session_start = datetime.now()
    conversation.conversation_stats.get_combined_metrics.return_value = make_metrics(
        cost, usage
    )

    pf, pc, text = call_display_status(conversation, session_start)

    assert pf.called and pc.called
    for expected in expecteds:
        assert expected in text


def test_status_command_no_active_conversation():
    """Test /status command when no conversation is active.

    Prevents UnboundLocalError.
    """
    with (
        patch(
            "openhands_cli.agent_chat.exit_session_confirmation"
        ) as mock_exit_confirm,
        patch(
            "openhands_cli.agent_chat.get_session_prompter"
        ) as mock_get_session_prompter,
        patch("openhands_cli.agent_chat.setup_conversation") as mock_setup_conversation,
        patch(
            "openhands_cli.agent_chat.verify_agent_exists_or_setup_agent"
        ) as mock_verify_agent,
        patch("openhands_cli.agent_chat.ConversationRunner") as mock_runner_cls,
    ):
        # Auto-accept the exit prompt to avoid interactive UI
        mock_exit_confirm.return_value = UserConfirmation.ACCEPT

        # Mock agent verification to succeed
        mock_agent = MagicMock()
        mock_verify_agent.return_value = mock_agent

        # Mock conversation setup (won't be called for /status without a message first)
        conv = MagicMock()
        conv.id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_setup_conversation.return_value = conv

        # Mock runner
        runner = MagicMock()
        runner.conversation = conv
        mock_runner_cls.return_value = runner

        # Real session fed by a pipe
        from openhands_cli.user_actions.utils import (
            get_session_prompter as real_get_session_prompter,
        )

        with create_pipe_input() as pipe:
            output = DummyOutput()
            session = real_get_session_prompter(input=pipe, output=output)
            mock_get_session_prompter.return_value = session

            from openhands_cli.agent_chat import run_cli_entry

            # Send /status command immediately without any prior message
            # This tests the scenario where conversation is still None
            pipe.send_text("/status\r/exit\r")

            # Capture printed output
            with patch("openhands_cli.agent_chat.print_formatted_text") as mock_print:
                run_cli_entry(None)

            # Verify "No active conversation" warning was printed
            warning_calls = [
                call
                for call in mock_print.call_args_list
                if "No active conversation" in str(call)
            ]
            assert len(warning_calls) > 0, (
                "Expected warning about no active conversation"
            )

            # Verify that setup_conversation was NOT called (no conversation started)
            assert mock_setup_conversation.call_count == 0, (
                "setup_conversation should not be called for /status without message"
            )
