#!/usr/bin/env python3
"""
Simple agent chat functionality for OpenHands CLI.
Provides a basic conversation interface with an AI agent with confirmation mode.
"""

import asyncio
import os
import sys
from typing import Optional

# Ensure we use the agent-sdk openhands package, not the main OpenHands package
# Remove the main OpenHands code path if it exists
if '/openhands/code' in sys.path:
    sys.path.remove('/openhands/code')

from pydantic import SecretStr
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import clear, confirm

try:
    from openhands.core import (
        LLM,
        CodeActAgent,
        Conversation,
        EventType,
        LLMConfig,
        LLMConvertibleEvent,
        Message,
        TextContent,
        Tool,
        get_logger,
    )
    from openhands.tools import (
        BashExecutor,
        FileEditorExecutor,
        execute_bash_tool,
        str_replace_editor_tool,
    )
except ImportError as e:
    print_formatted_text(HTML(f"<red>Error importing agent SDK: {e}</red>"))
    print_formatted_text(HTML("<yellow>Please ensure the openhands-sdk is properly installed.</yellow>"))
    sys.exit(1)


logger = get_logger(__name__)


class SimpleAgentChat:
    """Simple agent chat interface with confirmation mode."""
    
    def __init__(self):
        self.llm: Optional[LLM] = None
        self.agent: Optional[CodeActAgent] = None
        self.conversation: Optional[Conversation] = None
        self.session = PromptSession()
        self.confirmation_mode = True  # Enable confirmation mode by default
        self.always_confirm = False  # Track if user chose "always confirm"
        
    def setup_agent(self) -> bool:
        """Setup the agent with environment variables."""
        try:
            # Get API configuration from environment
            api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            model = os.getenv("LITELLM_MODEL", "gpt-4o-mini")
            base_url = os.getenv("LITELLM_BASE_URL")
            
            if not api_key:
                print_formatted_text(HTML(
                    "<red>Error: No API key found. Please set LITELLM_API_KEY or OPENAI_API_KEY environment variable.</red>"
                ))
                return False
            
            # Configure LLM
            llm_config = LLMConfig(
                model=model,
                api_key=SecretStr(api_key),
            )
            
            if base_url:
                llm_config.base_url = base_url
                
            self.llm = LLM(config=llm_config)
            
            # Setup tools
            cwd = os.getcwd()
            bash = BashExecutor(working_dir=cwd)
            file_editor = FileEditorExecutor()
            tools: list[Tool] = [
                execute_bash_tool.set_executor(executor=bash),
                str_replace_editor_tool.set_executor(executor=file_editor),
            ]
            
            # Create agent
            self.agent = CodeActAgent(llm=self.llm, tools=tools)
            
            # Setup conversation with callback
            def conversation_callback(event: EventType):
                logger.debug(f"Conversation event: {str(event)[:200]}...")
                
            self.conversation = Conversation(agent=self.agent, callbacks=[conversation_callback])
            
            print_formatted_text(HTML(
                f"<green>✓ Agent initialized with model: {model}</green>"
            ))
            return True
            
        except Exception as e:
            print_formatted_text(HTML(
                f"<red>Error setting up agent: {str(e)}</red>"
            ))
            return False
    
    def confirm_action(self, action_description: str) -> bool:
        """Ask user to confirm an action before execution."""
        if not self.confirmation_mode or self.always_confirm:
            return True
            
        print_formatted_text(HTML(f"<yellow>🤖 Agent wants to: {action_description}</yellow>"))
        print()
        
        try:
            choices = [
                "Yes, proceed",
                "No, skip this action", 
                "Always confirm (don't ask again)"
            ]
            
            print_formatted_text(HTML("<skyblue>Choose an option:</skyblue>"))
            for i, choice in enumerate(choices):
                print_formatted_text(HTML(f"  <white>{i + 1}. {choice}</white>"))
            
            while True:
                try:
                    user_choice = self.session.prompt(
                        HTML("<blue>Your choice (1-3): </blue>"),
                        multiline=False,
                    ).strip()
                    
                    if user_choice == '1':
                        return True
                    elif user_choice == '2':
                        print_formatted_text(HTML("<yellow>Action skipped.</yellow>"))
                        return False
                    elif user_choice == '3':
                        self.always_confirm = True
                        print_formatted_text(HTML("<green>✓ Will auto-confirm all future actions.</green>"))
                        return True
                    else:
                        print_formatted_text(HTML("<red>Please enter 1, 2, or 3.</red>"))
                        continue
                        
                except (KeyboardInterrupt, EOFError):
                    print_formatted_text(HTML("<yellow>Action cancelled.</yellow>"))
                    return False
                    
        except Exception as e:
            logger.error(f"Error in confirmation: {e}")
            return False
    
    def display_welcome(self):
        """Display welcome message."""
        clear()
        print_formatted_text(HTML("<gold>🤖 OpenHands Agent Chat</gold>"))
        print_formatted_text(HTML("<grey>Simple AI Agent Conversation Interface with Confirmation Mode</grey>"))
        print()
        print_formatted_text(HTML("<skyblue>Commands:</skyblue>"))
        print_formatted_text(HTML("  <white>/exit</white> - Exit the chat"))
        print_formatted_text(HTML("  <white>/clear</white> - Clear the screen"))
        print_formatted_text(HTML("  <white>/help</white> - Show this help"))
        print_formatted_text(HTML("  <white>/toggle-confirm</white> - Toggle confirmation mode"))
        print()
        confirmation_status = "ON" if self.confirmation_mode else "OFF"
        print_formatted_text(HTML(f"<yellow>⚠️  Confirmation Mode: {confirmation_status}</yellow>"))
        if self.confirmation_mode:
            print_formatted_text(HTML("<grey>   The agent will ask for approval before taking actions.</grey>"))
        print()
        print_formatted_text(HTML("<green>Type your message and press Enter to chat with the agent.</green>"))
        print()
    
    def run_with_confirmation(self):
        """Run the conversation with confirmation mode."""
        # For now, let's implement a simple approach that just runs the conversation
        # In a more sophisticated implementation, we would intercept individual actions
        if self.confirmation_mode and not self.always_confirm:
            # Ask for confirmation before running the agent
            if not self.confirm_action("process your request and potentially execute commands"):
                print_formatted_text(HTML("<yellow>Request cancelled by user.</yellow>"))
                return
        
        # Run the conversation
        self.conversation.run()
        print_formatted_text(HTML("<green>✓ Agent has processed your request.</green>"))
    
    def run_chat(self):
        """Run the interactive chat loop."""
        if not self.setup_agent():
            return
            
        self.display_welcome()
        
        while True:
            try:
                # Get user input
                user_input = self.session.prompt(
                    HTML("<blue>You: </blue>"),
                    multiline=False,
                )
                
                if not user_input.strip():
                    continue
                    
                # Handle commands
                if user_input.strip().lower() == '/exit':
                    print_formatted_text(HTML("<yellow>Goodbye! 👋</yellow>"))
                    break
                elif user_input.strip().lower() == '/clear':
                    clear()
                    self.display_welcome()
                    continue
                elif user_input.strip().lower() == '/help':
                    self.display_welcome()
                    continue
                elif user_input.strip().lower() == '/toggle-confirm':
                    self.confirmation_mode = not self.confirmation_mode
                    self.always_confirm = False  # Reset always confirm when toggling
                    status = "ON" if self.confirmation_mode else "OFF"
                    print_formatted_text(HTML(f"<green>✓ Confirmation mode is now {status}</green>"))
                    continue
                
                # Send message to agent
                print_formatted_text(HTML("<green>Agent: </green>"), end="")
                
                try:
                    # Create message and send to conversation
                    message = Message(
                        role="user",
                        content=[TextContent(text=user_input)],
                    )
                    
                    # Send message to conversation
                    self.conversation.send_message(message)
                    
                    # Run the conversation with confirmation mode
                    self.run_with_confirmation()
                    
                except Exception as e:
                    print_formatted_text(HTML(f"<red>Error: {str(e)}</red>"))
                
                print()  # Add spacing
                
            except KeyboardInterrupt:
                print_formatted_text(HTML("\n<yellow>Chat interrupted. Type /exit to quit.</yellow>"))
                continue
            except EOFError:
                print_formatted_text(HTML("\n<yellow>Goodbye! 👋</yellow>"))
                break


def main():
    """Main entry point for agent chat."""
    chat = SimpleAgentChat()
    chat.run_chat()


if __name__ == "__main__":
    main()