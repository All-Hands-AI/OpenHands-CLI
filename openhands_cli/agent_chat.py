#!/usr/bin/env python3
"""
Simple agent chat functionality for OpenHands CLI.
Provides a basic conversation interface with an AI agent.
"""

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
from prompt_toolkit.shortcuts import clear

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
    """Simple agent chat interface."""
    
    def __init__(self):
        self.llm: Optional[LLM] = None
        self.agent: Optional[CodeActAgent] = None
        self.conversation: Optional[Conversation] = None
        self.session = PromptSession()
        
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
    
    def display_welcome(self):
        """Display welcome message."""
        clear()
        print_formatted_text(HTML("<gold>🤖 OpenHands Agent Chat</gold>"))
        print_formatted_text(HTML("<grey>Simple AI Agent Conversation Interface</grey>"))
        print()
        print_formatted_text(HTML("<skyblue>Commands:</skyblue>"))
        print_formatted_text(HTML("  <white>/exit</white> - Exit the chat"))
        print_formatted_text(HTML("  <white>/clear</white> - Clear the screen"))
        print_formatted_text(HTML("  <white>/help</white> - Show this help"))
        print()
        print_formatted_text(HTML("<green>Type your message and press Enter to chat with the agent.</green>"))
        print()
    
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
                
                # Send message to agent
                print_formatted_text(HTML("<green>Agent: </green>"), end="")
                
                try:
                    # Create message and send to conversation
                    message = Message(
                        role="user",
                        content=[TextContent(text=user_input)],
                    )
                    
                    self.conversation.send_message(message)
                    self.conversation.run()
                    
                    # Get the last response from the conversation
                    # For simplicity, we'll just indicate the agent processed the request
                    print_formatted_text(HTML("<green>✓ Agent has processed your request.</green>"))
                    
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