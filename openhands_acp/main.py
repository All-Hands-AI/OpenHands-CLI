"""
OpenHands ACP Main Entry Point.

This module provides the main entry point for the OpenHands Agent Client Protocol
implementation, allowing OpenHands to work as an agent with ACP-compatible editors.
"""

import asyncio
import logging
import sys
from typing import Optional

import typer
from acp import stdio_streams

from .agent import OpenHandsACPAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/openhands-acp.log"),
        logging.StreamHandler(sys.stderr),
    ],
)

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="openhands-acp",
    help="OpenHands Agent Client Protocol implementation",
    no_args_is_help=True,
)


@app.command()
def serve(
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
    sessions_dir: Optional[str] = typer.Option(
        None,
        "--sessions-dir",
        help="Directory to store session data",
    ),
) -> None:
    """
    Start the OpenHands ACP agent server.
    
    This command starts the ACP agent server that communicates with editors
    via stdin/stdout using the Agent Client Protocol.
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        typer.echo(f"Invalid log level: {log_level}", err=True)
        raise typer.Exit(1)
    
    logging.getLogger().setLevel(numeric_level)
    
    logger.info("Starting OpenHands ACP agent server")
    logger.info("Log level: %s", log_level)
    if sessions_dir:
        logger.info("Sessions directory: %s", sessions_dir)
    
    try:
        # Run the ACP agent
        asyncio.run(run_acp_agent(sessions_dir))
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.error("Fatal error: %s", e)
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__
    typer.echo(f"OpenHands ACP Agent v{__version__}")


async def run_acp_agent(sessions_dir: Optional[str] = None) -> None:
    """
    Run the OpenHands ACP agent.
    
    Args:
        sessions_dir: Optional directory for session storage
    """
    logger.info("Initializing ACP agent")
    
    try:
        # Create stdio streams for ACP communication
        async with stdio_streams() as (read_stream, write_stream):
            logger.info("ACP stdio streams established")
            
            # Create the ACP agent
            agent = OpenHandsACPAgent(write_stream)
            
            # Set sessions directory if provided
            if sessions_dir:
                agent._session_manager = agent._session_manager.__class__(sessions_dir)
            
            logger.info("OpenHands ACP agent created, starting message loop")
            
            # Start the ACP message loop
            await read_stream.run_agent(agent)
            
    except Exception as e:
        logger.error("Error running ACP agent: %s", e)
        raise


def main() -> None:
    """Main entry point for the OpenHands ACP CLI."""
    try:
        app()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()