#!/usr/bin/env python3
"""
Simple main entry point for OpenHands CLI.
This is a simplified version that demonstrates the TUI functionality.
"""

import sys

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML

from openhands_cli.tui import display_banner


def show_menu() -> str:
    """Show the main menu and get user choice."""
    print_formatted_text(HTML("<gold>OpenHands CLI</gold>"))
    print_formatted_text(
        HTML("<grey>Terminal User Interface for OpenHands AI Agent</grey>")
    )
    print()

    print("🚀 Welcome to OpenHands CLI!")
    print()
    print("Available options:")
    print("  1. Start Agent Chat - Interactive conversation with AI agent")
    print("  2. Show TUI Demo - Display TUI components")
    print("  3. Exit")
    print()
    
    session = PromptSession()
    choice = session.prompt("Select an option (1-3): ")
    return choice.strip()


def show_tui_demo():
    """Show the TUI demo functionality."""
    print()
    print("📱 TUI Demo:")
    print("Available features:")
    print("  • Terminal User Interface (TUI) components")
    print("  • Prompt Toolkit integration")
    print("  • Agent SDK integration")
    print()
    print("To use the full functionality, ensure you have:")
    print("  1. OpenHands agent SDK properly configured")
    print("  2. Required environment variables set (LITELLM_API_KEY or OPENAI_API_KEY)")
    print("  3. Proper authentication tokens")
    print()

    # For now, just show that the CLI is working
    try:
        display_banner(session_id="demo")
    except ImportError as e:
        print(f"Note: Full TUI functionality requires additional setup: {e}")

    print("TUI demo complete! 🎉")


def main() -> int:
    """Main entry point for the OpenHands CLI."""
    while True:
        try:
            choice = show_menu()
            
            if choice == "1":
                # Start agent chat
                try:
                    from openhands_cli.agent_chat import main as run_agent_chat
                    run_agent_chat()
                except ImportError as e:
                    print_formatted_text(HTML(
                        f"<red>Error: Agent chat requires additional dependencies: {e}</red>"
                    ))
                    print_formatted_text(HTML(
                        "<yellow>Please ensure the agent SDK is properly installed.</yellow>"
                    ))
                except Exception as e:
                    print_formatted_text(HTML(
                        f"<red>Error starting agent chat: {e}</red>"
                    ))
                    
            elif choice == "2":
                # Show TUI demo
                show_tui_demo()
                
            elif choice == "3":
                # Exit
                print_formatted_text(HTML("<yellow>Goodbye! 👋</yellow>"))
                break
                
            else:
                print_formatted_text(HTML("<red>Invalid choice. Please select 1, 2, or 3.</red>"))
                
            print()  # Add spacing between menu iterations
            
        except KeyboardInterrupt:
            print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
            break
        except EOFError:
            print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
            break
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
