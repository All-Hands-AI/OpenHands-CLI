# Repository Purpose
This is the OpenHands CLI - a command-line interface for OpenHands AI Agent with Terminal User Interface (TUI) support. It provides a standalone executable that allows users to interact with OpenHands through a terminal interface.

This project ports CLI code from `https://github.com/All-Hands-AI/OpenHands` (folder `openhands/cli`) and refactors it to use the new agent-sdk from `https://github.com/All-Hands-AI/agent-sdk`.

## References
- Example script for agent-sdk: `https://github.com/All-Hands-AI/agent-sdk/blob/main/examples/hello_world.py`
- Use `$GITHUB_TOKEN` to refer to OpenHands repo for copying UI and user interactions for the CLI
- Refer to agent-sdk repo for setting up agent behavior, tools, etc.

# Setup Instructions
To set up the development environment:
1. Install dependencies: `make install-dev`
2. Install pre-commit hooks: `make install-pre-commit-hooks`



# Development Guidelines

## Linting Requirements
**Always run lint before committing changes.** Use `make lint` to run all pre-commit hooks on all files. The project uses:

## Typing Requirements
When using types, prefer modern typing syntax (e.g., use `| None` instead of `Optional`).

## Documentation Guidelines
- **Do NOT send summary updates in the README.md** for the repository
- **Do NOT create .md files in the root** of the repository to track or send updates
- Only make documentation changes when explicitly requested to

## Updating Agent-SDK SHA

If the user says something along the lines of "update the sha" or "update the agent-sdk sha", you need to:

1. Use the `$GITHUB_TOKEN` to get the latest commit from the agent-sdk repository
2. Update the poetry toml file with the new SHA
3. Regenerate the uv lock file
4. Run `./build.sh` to confirm that the build still works
5. Open a pull request with the changes

If the build fails, still open the pull request and explain what error you're seeing, and the steps you plan to take to fix it; don't fix it yet though.