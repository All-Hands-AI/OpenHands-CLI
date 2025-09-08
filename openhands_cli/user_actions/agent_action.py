from prompt_toolkit import HTML, print_formatted_text

from openhands_cli.user_actions.types import UserConfirmation
from openhands_cli.user_actions.utils import cli_confirm, prompt_for_reason


def ask_user_confirmation(pending_actions: list) -> tuple[UserConfirmation, str]:
    """Ask user to confirm pending actions.

    Args:
        pending_actions: List of pending actions from the agent

    Returns:
        Tuple of (UserConfirmation, reason) where reason is provided when rejecting with reason
    """

    if not pending_actions:
        return UserConfirmation.ACCEPT, ""

    print_formatted_text(
        HTML(
            f"<yellow>🔍 Agent created {len(pending_actions)} action(s) and is waiting for confirmation:</yellow>"
        )
    )

    for i, action in enumerate(pending_actions, 1):
        tool_name = getattr(action, "tool_name", "[unknown tool]")
        print("tool name", tool_name)
        action_content = (
            str(getattr(action, "action", ""))[:100].replace("\n", " ")
            or "[unknown action]"
        )
        print("action_content", action_content)
        print_formatted_text(
            HTML(f"<grey>  {i}. {tool_name}: {action_content}...</grey>")
        )

    question = "Choose an option:"
    options = ["Yes, proceed", "No, reject", "No (with reason)"]

    try:
        index = cli_confirm(question, options, escapable=True)
    except (EOFError, KeyboardInterrupt):
        print_formatted_text(HTML("\n<red>No input received; pausing agent.</red>"))
        return UserConfirmation.DEFER, ""

    if index == 0:
        return UserConfirmation.ACCEPT, ""
    elif index == 1:
        return UserConfirmation.REJECT, ""
    elif index == 2:
        reason = prompt_for_reason()
        if reason:
            return UserConfirmation.REJECT_WITH_REASON, reason
        else:
            # If user cancels reason input, treat as regular reject
            return UserConfirmation.REJECT, ""
    else:
        return UserConfirmation.REJECT, ""
