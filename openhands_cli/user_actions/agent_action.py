import html

from prompt_toolkit import HTML, print_formatted_text
from prompt_toolkit.shortcuts import input_dialog

from openhands.sdk.security.confirmation_policy import (
    ConfirmRisky,
    NeverConfirm,
)
from openhands.sdk.security.risk import SecurityRisk
from openhands_cli.user_actions.types import ConfirmationResult, UserConfirmation
from openhands_cli.user_actions.utils import cli_confirm, cli_text_input


def ask_user_confirmation(
    pending_actions: list, using_risk_based_policy: bool = False
) -> ConfirmationResult:
    """Ask user to confirm pending actions.

    Args:
        pending_actions: List of pending actions from the agent

    Returns:
        ConfirmationResult with decision, optional policy_change, and reason
    """

    if not pending_actions:
        return ConfirmationResult(decision=UserConfirmation.ACCEPT)

    print_formatted_text(
        HTML(
            f"<yellow>🔍 Agent created {len(pending_actions)} action(s) and is "
            f"waiting for confirmation:</yellow>"
        )
    )

    for i, action in enumerate(pending_actions, 1):
        tool_name = getattr(action, "tool_name", "[unknown tool]")
        action_content = (
            str(getattr(action, "action", ""))[:100].replace("\n", " ")
            or "[unknown action]"
        )
        print_formatted_text(
            HTML(f"<grey>  {i}. {tool_name}: {html.escape(action_content)}...</grey>")
        )

    question = "Choose an option:"
    options = [
        "Yes, proceed",
        "Reject",
        "Always proceed (don't ask again)",
    ]

    if not using_risk_based_policy:
        options.append("Auto-confirm LOW/MEDIUM risk, ask for HIGH risk")

    try:
        index = cli_confirm(question, options, escapable=True)
    except (EOFError, KeyboardInterrupt):
        print_formatted_text(HTML("\n<red>No input received; pausing agent.</red>"))
        return ConfirmationResult(decision=UserConfirmation.DEFER)

    if index == 0:
        return ConfirmationResult(decision=UserConfirmation.ACCEPT)
    elif index == 1:
        # Handle "Reject" option with optional reason
        try:
            reason = cli_text_input("Reason (and let OpenHands know why): ").strip()
        except (EOFError, KeyboardInterrupt):
            return ConfirmationResult(decision=UserConfirmation.DEFER)

        return ConfirmationResult(decision=UserConfirmation.REJECT, reason=reason)
    elif index == 2:
        return ConfirmationResult(
            decision=UserConfirmation.ACCEPT, policy_change=NeverConfirm()
        )
    elif index == 3:
        return ConfirmationResult(
            decision=UserConfirmation.ACCEPT,
            policy_change=ConfirmRisky(threshold=SecurityRisk.HIGH),
        )

    return ConfirmationResult(decision=UserConfirmation.REJECT)


def ask_user_confirmation_tui(
    pending_actions: list, using_risk_based_policy: bool = False, tui_instance=None
) -> ConfirmationResult:
    """Ask user to confirm pending actions using TUI native dialog.

    Args:
        pending_actions: List of pending actions from the agent
        using_risk_based_policy: Whether using risk-based policy
        tui_instance: The TUI instance to show dialog on

    Returns:
        ConfirmationResult with decision, optional policy_change, and reason
    """
    if not pending_actions:
        return ConfirmationResult(decision=UserConfirmation.ACCEPT)

    question = "Choose an option:"
    options = [
        "Yes, proceed",
        "Reject",
        "Always proceed (don't ask again)",
    ]

    if not using_risk_based_policy:
        options.append("Auto-confirm LOW/MEDIUM risk, ask for HIGH risk")

    # Use TUI's native dialog if available, otherwise fall back to CLI
    if tui_instance and hasattr(tui_instance, "show_confirmation_dialog"):
        try:
            index = tui_instance.show_confirmation_dialog(
                question, options, pending_actions
            )
        except (EOFError, KeyboardInterrupt):
            return ConfirmationResult(decision=UserConfirmation.DEFER)
    else:
        # Fallback to CLI version
        try:
            index = cli_confirm(question, options, escapable=True)
        except (EOFError, KeyboardInterrupt):
            return ConfirmationResult(decision=UserConfirmation.DEFER)

    if index is None:
        return ConfirmationResult(decision=UserConfirmation.DEFER)

    if index == 0:
        return ConfirmationResult(decision=UserConfirmation.ACCEPT)
    elif index == 1:
        # Handle "Reject" option with optional reason
        try:
            if tui_instance:
                reason = (
                    input_dialog(
                        title="Rejection Reason",
                        text="Reason (and let OpenHands know why):",
                    ).run()
                    or ""
                )
            else:
                reason = cli_text_input("Reason (and let OpenHands know why): ").strip()
        except (EOFError, KeyboardInterrupt):
            return ConfirmationResult(decision=UserConfirmation.DEFER)

        return ConfirmationResult(decision=UserConfirmation.REJECT, reason=reason)
    elif index == 2:
        return ConfirmationResult(
            decision=UserConfirmation.ACCEPT, policy_change=NeverConfirm()
        )
    elif index == 3:
        return ConfirmationResult(
            decision=UserConfirmation.ACCEPT,
            policy_change=ConfirmRisky(threshold=SecurityRisk.HIGH),
        )

    return ConfirmationResult(decision=UserConfirmation.REJECT)
