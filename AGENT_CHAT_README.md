# OpenHands CLI - Simple Agent Chat

This OpenHands CLI now includes a simple agent chat functionality that allows you to have interactive conversations with an AI agent using the OpenHands Agent SDK.

## Features

- **Simple Agent Interaction**: Chat directly with an AI agent through a terminal interface
- **Environment-based Configuration**: Load API keys and model settings from environment variables
- **Clean TUI Interface**: Uses prompt-toolkit for a clean terminal user interface
- **Tool Integration**: The agent has access to bash execution and file editing tools

## Setup

### 1. Install Dependencies

The CLI is already set up with the necessary dependencies. If you need to install manually:

```bash
pip install -e .
```

### 2. Set Environment Variables

To use the agent chat, you need to set up your API credentials:

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-openai-api-key"
export LITELLM_MODEL="gpt-4o-mini"  # Optional, defaults to gpt-4o-mini
```

**For LiteLLM (supports multiple providers):**
```bash
export LITELLM_API_KEY="your-api-key"
export LITELLM_MODEL="gpt-4o-mini"  # Or any supported model
export LITELLM_BASE_URL="https://api.openai.com/v1"  # Optional
```

### 3. Test the Setup

Run the test script to verify everything is configured correctly:

```bash
python test_agent_chat.py
```

## Usage

### Start the CLI

```bash
python -m openhands_cli.simple_main
```

Or if installed:

```bash
openhands-cli
```

### Using Agent Chat

1. Select option `1` from the main menu: "Start Agent Chat"
2. The agent will initialize and show a welcome message
3. Type your messages and press Enter to chat with the agent
4. The agent can execute bash commands and edit files as needed

### Available Commands in Chat

- `/exit` - Exit the chat
- `/clear` - Clear the screen
- `/help` - Show help message

## Example Conversation

```
🤖 OpenHands Agent Chat
Simple AI Agent Conversation Interface

Commands:
  /exit - Exit the chat
  /clear - Clear the screen
  /help - Show this help

Type your message and press Enter to chat with the agent.

You: Hello! Can you create a simple Python script that prints "Hello, World!"?

Agent: ✓ Agent has processed your request.

You: /exit
Goodbye! 👋
```

## Architecture

The agent chat implementation:

1. **SimpleAgentChat Class**: Main chat interface class
2. **Agent SDK Integration**: Uses the OpenHands Agent SDK for conversation handling
3. **Tool Integration**: Includes bash executor and file editor tools
4. **Environment Configuration**: Loads settings from environment variables
5. **Clean Error Handling**: Provides helpful error messages for setup issues

## Files

- `openhands_cli/agent_chat.py` - Main agent chat implementation
- `openhands_cli/simple_main.py` - Updated main entry point with menu
- `test_agent_chat.py` - Test script to verify setup

## Troubleshooting

### Import Errors

If you see import errors related to the OpenHands SDK, make sure all dependencies are installed:

```bash
pip install libtmux bashlex binaryornot cachetools
```

### API Key Issues

- Make sure your API key is valid and has sufficient credits
- Check that the model name is correct for your provider
- Verify the base URL if using a custom endpoint

### Path Issues

The implementation automatically handles Python path conflicts between the main OpenHands repository and the agent SDK.

## Extending the Chat

The current implementation is intentionally simple. You can extend it by:

1. Adding more sophisticated conversation handling
2. Implementing conversation history persistence
3. Adding more tools and capabilities
4. Customizing the UI with more advanced prompt-toolkit features
5. Adding configuration file support