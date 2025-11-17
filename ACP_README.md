# OpenHands Agent Client Protocol (ACP) Implementation

This document describes the Agent Client Protocol (ACP) implementation for OpenHands, enabling integration with ACP-compatible editors like Zed.

## Overview

The Agent Client Protocol (ACP) is a standardized protocol for communication between code editors/IDEs and AI coding agents. It uses JSON-RPC 2.0 over stdio (standard input/output) for bidirectional communication.

OpenHands now supports ACP, allowing it to work seamlessly with editors that implement the ACP client specification.

## Features

- **Full ACP Protocol Support**: Implements all core ACP methods (initialize, newSession, loadSession, prompt, cancel)
- **File System Operations**: Secure file read/write operations within the working directory
- **Session Management**: Persistent conversation sessions with history
- **Permission System**: Tool execution with user permission requests
- **Streaming Responses**: Real-time response streaming to the editor
- **Error Handling**: Comprehensive error handling and logging

## Usage

### As Standalone Binary

```bash
# Build the ACP binary
./build.sh --acp-only

# Run as ACP agent
./dist/openhands-acp serve
```

### As CLI Subcommand

```bash
# Run ACP mode through main CLI
openhands acp

# With custom log level
openhands acp --log-level DEBUG

# With custom sessions directory
openhands acp --sessions-dir /path/to/sessions
```

### Build Both Binaries

```bash
# Build both CLI and ACP binaries
./build.sh --all
```

## Editor Integration

### Zed Editor

To use OpenHands with Zed editor:

1. Build the OpenHands ACP binary:
   ```bash
   ./build.sh --acp-only
   ```

2. Configure Zed to use OpenHands as an ACP agent by adding to your Zed settings:
   ```json
   {
     "agents": {
       "openhands": {
         "command": "/path/to/openhands-acp",
         "args": ["serve"]
       }
     }
   }
   ```

3. Start using OpenHands in Zed through the agent panel.

### Other Editors

Any editor that supports the Agent Client Protocol can integrate with OpenHands. The agent communicates via stdin/stdout using JSON-RPC 2.0 messages.

## Protocol Implementation

### Supported Methods

#### Agent Methods (Client → Agent)

- `initialize`: Protocol version negotiation and capability exchange
- `authenticate`: Authentication handling (currently no-op)
- `newSession`: Create a new conversation session
- `loadSession`: Resume an existing session
- `prompt`: Process user prompts and generate responses
- `cancel`: Cancel ongoing operations

#### Client Methods (Agent → Client)

- `readTextFile`: Read file contents
- `writeTextFile`: Write file contents
- `requestPermission`: Request permission for tool execution
- `sessionUpdate`: Stream response updates

### Capabilities

The OpenHands ACP agent advertises the following capabilities:

- **Session Loading**: Can resume previous conversations
- **Embedded Context**: Supports context from file references
- **File System**: Read/write text files within working directory
- **Tool Execution**: Execute various tools with permission system

## Architecture

### Components

1. **`openhands_acp/agent.py`**: Core ACP agent implementation
2. **`openhands_acp/bridge.py`**: Bridge between ACP and OpenHands SDK
3. **`openhands_acp/file_operations.py`**: File system operations handler
4. **`openhands_acp/session.py`**: Session persistence and management
5. **`openhands_acp/tools.py`**: Tool call handling with permissions
6. **`openhands_acp/main.py`**: Entry point and CLI interface

### Data Flow

```
Editor (ACP Client) ←→ OpenHands ACP Agent ←→ OpenHands SDK ←→ AI Model
                           ↓
                    Session Storage
                    File Operations
                    Tool Execution
```

## Configuration

### Environment Variables

- `OPENHANDS_BASE_URL`: OpenHands server URL (default: http://localhost:3000)
- `OPENHANDS_API_KEY`: API key for OpenHands server
- `DEBUG`: Enable debug logging (set to "1" or "true")

### Session Storage

Sessions are stored in `~/.openhands/acp_sessions/` by default. Each session includes:

- Conversation history
- Session metadata
- Working directory
- MCP server configurations

## Development

### Running Tests

```bash
# Run ACP-specific tests
pytest tests/acp/

# Run all tests
pytest
```

### Building

```bash
# Build ACP binary only
python build.py --acp-only

# Build both binaries
python build.py --all

# Build with custom spec
python build.py --spec openhands-acp.spec
```

### Debugging

Enable debug logging:

```bash
# Environment variable
DEBUG=1 openhands acp

# Command line argument
openhands acp --log-level DEBUG
```

Logs are written to `/tmp/openhands-acp.log` and stderr.

## Security

### File System Security

- All file operations are restricted to the working directory
- Path traversal attacks are prevented
- Symbolic links are resolved safely

### Permission System

- Tool execution requires explicit user permission
- Permissions are requested through the ACP client
- Users can allow or deny each operation

### Network Security

- No network operations without explicit permission
- OpenHands server communication uses configured endpoints only

## Troubleshooting

### Common Issues

1. **Agent not starting**: Check that all dependencies are installed
2. **File permission errors**: Ensure working directory is accessible
3. **Connection issues**: Verify OpenHands server is running
4. **Protocol errors**: Check ACP client implementation compatibility

### Debug Information

Enable debug logging to see detailed protocol messages:

```bash
openhands acp --log-level DEBUG 2>&1 | tee debug.log
```

### Log Files

- ACP agent logs: `/tmp/openhands-acp.log`
- Session data: `~/.openhands/acp_sessions/`

## Contributing

When contributing to the ACP implementation:

1. Follow the existing code structure
2. Add tests for new functionality
3. Update this documentation
4. Ensure compatibility with ACP specification
5. Test with real editors when possible

## References

- [Agent Client Protocol Specification](https://agentclientprotocol.com/)
- [ACP Python SDK](https://github.com/agentclientprotocol/python-sdk)
- [Zed Editor ACP Documentation](https://zed.dev/docs/agents)
- [OpenHands SDK](https://github.com/All-Hands-AI/agent-sdk)