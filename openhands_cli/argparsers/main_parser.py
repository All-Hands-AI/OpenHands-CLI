"""Main argument parser for OpenHands CLI."""

import argparse


def create_main_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with CLI as default and serve as subcommand.

    Returns:
        The configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="OpenHands CLI - Terminal User Interface for OpenHands AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
By default, OpenHands runs in CLI mode (terminal interface).
Use 'serve' subcommand to launch the GUI server instead.

Examples:
  openhands                           # Start CLI mode
  openhands --resume conversation-id  # Resume a conversation in CLI mode
  openhands -t "Build a Flask app"    # Start with an initial task message
  openhands -f path/to/task.txt       # Start with file contents as the first message
  openhands serve                     # Launch GUI server
  openhands serve --gpu               # Launch GUI server with GPU support
""",
    )

    # CLI arguments at top level (default mode)
    parser.add_argument("--resume", type=str, help="Conversation ID to resume")

    # Initial message options (mutually exclusive)
    initial_group = parser.add_mutually_exclusive_group()
    initial_group.add_argument(
        "-t",
        "--task",
        type=str,
        help="Initial task prompt to start the conversation with",
    )
    initial_group.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to a file whose contents are used as the initial user message",
    )

    # Only serve as subcommand
    subparsers = parser.add_subparsers(dest="command", help="Additional commands")

    # Add serve subcommand
    serve_parser = subparsers.add_parser(
        "serve", help="Launch the OpenHands GUI server using Docker (web interface)"
    )
    serve_parser.add_argument(
        "--mount-cwd",
        action="store_true",
        help="Mount the current working directory in the Docker container",
    )
    serve_parser.add_argument(
        "--gpu", action="store_true", help="Enable GPU support in the Docker container"
    )

    return parser
