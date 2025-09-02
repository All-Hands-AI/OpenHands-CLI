# Repository Purpose
This is the OpenHands CLI - a command-line interface for OpenHands AI Agent with Terminal User Interface (TUI) support. It provides a standalone executable that allows users to interact with OpenHands through a terminal interface.

# Setup Instructions
To set up the development environment:
1. Install dependencies: `make install-dev`
2. Install pre-commit hooks: `make install-pre-commit-hooks`

# Repository Structure
- `/openhands_cli/`: Core CLI application code
  - `simple_main.py`: Main entry point for the CLI
  - `tui.py`: Terminal User Interface implementation
  - `pt_style.py`: Prompt toolkit styling
- `/.github/workflows/`: CI/CD workflows
- `/build.py` and `/build.sh`: Binary packaging scripts
- `/openhands-cli.spec`: PyInstaller specification for binary builds
- `/pyproject.toml`: Project configuration and dependencies
- `/Makefile`: Development commands and automation

# CI/CD Workflows
- `lint.yml`: Runs pre-commit hooks including Ruff linter, MyPy type checking, and various code quality checks on all Python files

# Development Guidelines

## Linting Requirements
**Always run lint before committing changes.** Use `make lint` to run all pre-commit hooks on all files. The project uses:
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking  
- **Pre-commit hooks**: Various code quality checks including trailing whitespace, YAML validation, and debug statement detection

## Documentation Guidelines
- **Do NOT send summary updates in the README.md** for the repository
- **Do NOT create .md files in the root** of the repository to track or send updates
- Keep documentation changes minimal and focused on essential information only
- Any documentation should be integrated into existing files rather than creating new tracking files

## Available Commands
Run `make help` to see all available development commands including install, test, lint, format, clean, and run.