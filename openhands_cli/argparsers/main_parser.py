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
Use subcommands for additional functionality.

Examples:
  openhands                           # Start CLI mode
  openhands --resume conversation-id  # Resume a conversation in CLI mode
  openhands serve                     # Launch GUI server
  openhands serve --gpu               # Launch GUI server with GPU support
  openhands acp                       # Start as ACP agent for editors like Zed
  openhands acp --log-level DEBUG     # Start ACP agent with debug logging
""",
    )

    # CLI arguments at top level (default mode)
    parser.add_argument("--resume", type=str, help="Conversation ID to resume")

    # Subcommands
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

    # Add ACP subcommand
    acp_parser = subparsers.add_parser(
        "acp", help="Start OpenHands as an Agent Client Protocol (ACP) agent"
    )
    acp_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level",
    )

    return parser
