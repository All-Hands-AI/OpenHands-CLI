# OpenHands CLI

A command-line interface for OpenHands AI Agent with Terminal User Interface (TUI) support.

## Development

### Setup

1. Install dependencies:
   ```bash
   make install-dev
   ```

2. Install pre-commit hooks:
   ```bash
   make install-pre-commit-hooks
   ```

### Code Quality

This project uses pre-commit hooks to ensure code quality. The following tools are configured:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Pre-commit hooks**: Various code quality checks

#### Running Linters

```bash
# Run all pre-commit hooks
make lint-pre-commit

# Run individual linters
make lint        # Run ruff and mypy
make format      # Format code with ruff
```

#### Pre-commit Hooks

Pre-commit hooks will automatically run on every commit. To run them manually:

```bash
# Run on all files
uv run pre-commit run --all-files

# Run on staged files only
uv run pre-commit run
```

### Available Commands

Run `make help` to see all available commands:

```bash
make help
```
