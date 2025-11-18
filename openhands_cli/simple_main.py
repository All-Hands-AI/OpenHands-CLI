#!/usr/bin/env python3
"""
Simple main entry point for OpenHands CLI.
This is a simplified version that demonstrates the TUI functionality.
"""

import logging
import os
import warnings

# Removed prompt_toolkit imports - using regular print instead
from openhands_cli.argparsers.main_parser import create_main_parser


debug_env = os.getenv("DEBUG", "false").lower()
if debug_env != "1" and debug_env != "true":
    logging.disable(logging.WARNING)
    warnings.filterwarnings("ignore")


def main() -> None:
    """Main entry point for the OpenHands CLI.

    Raises:
        ImportError: If agent chat dependencies are missing
        Exception: On other error conditions
    """
    parser = create_main_parser()
    args = parser.parse_args()

    try:
        if args.command == "serve":
            # Import gui_launcher only when needed
            from openhands_cli.gui_launcher import launch_gui_server

            launch_gui_server(mount_cwd=args.mount_cwd, gpu=args.gpu)
        else:
            # Default CLI behavior - no subcommand needed
            # Import textual_app only when needed
            from openhands_cli.textual_app import run_textual_app

            # Start textual app
            run_textual_app(resume_conversation_id=args.resume)
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
    except EOFError:
        print("\nGoodbye! 👋")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
