from prompt_toolkit import HTML, PromptSession, print_formatted_text

from openhands_cli.runner import UserConfirmation


def ask_user_confirmation(pending_actions: list) -> UserConfirmation:
    """Ask user to confirm pending actions.

    Args:
        pending_actions: List of pending actions from the agent

    Returns:
        True if user approves, False if user rejects
    """
    if not pending_actions:
        return UserConfirmation.ACCEPT

    print_formatted_text(
        HTML(
            f"<yellow>🔍 Agent created {len(pending_actions)} action(s) and is waiting for confirmation:</yellow>"
        )
    )

    for i, action in enumerate(pending_actions, 1):
        tool_name = getattr(action, "tool_name", "<unknown tool>")
        action_content = str(getattr(action, "action", ""))[:100].replace("\n", " ")
        print_formatted_text(
            HTML(f"<grey>  {i}. {tool_name}: {action_content}...</grey>")
        )

    session = PromptSession()
    while True:
        try:
            user_input = (
                session.prompt(
                    HTML(
                        "<gold>Do you want to execute these actions? (yes/no): </gold>"
                    )
                )
                .strip()
                .lower()
            )

            if user_input in ("yes", "y"):
                print_formatted_text(
                    HTML("<green>✅ Approved — executing actions…</green>")
                )
                return UserConfirmation.ACCEPT
            elif user_input in ("no", "n"):
                print_formatted_text(HTML("<red>❌ Rejected — skipping actions…</red>"))
                return UserConfirmation.REJECT
            else:
                print_formatted_text(
                    HTML("<yellow>Please enter 'yes' or 'no'.</yellow>")
                )
        except (EOFError, KeyboardInterrupt):
            print_formatted_text(HTML("\n<red>No input received; pausing agent.</red>"))
            return UserConfirmation.DEFER
