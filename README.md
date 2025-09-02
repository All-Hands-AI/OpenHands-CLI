# OpenHands CLI

A command-line interface for OpenHands AI Agent with Terminal User Interface (TUI) support.

## Features

- Interactive Terminal User Interface (TUI)
- Command-line interface for OpenHands operations
- Built with prompt-toolkit for rich terminal interactions

## Installation

### Using UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the CLI
uv pip install -e .
```

### Using Poetry

```bash
# Install dependencies
poetry install

# Run the CLI
poetry run openhands-cli
```

## Usage

```bash
# Run the CLI
openhands-cli

# Or with poetry
poetry run openhands-cli
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/All-Hands-AI/OpenHands-CLI.git
cd OpenHands-CLI

# Install dependencies with UV
uv pip install -e ".[dev]"

# Or with Poetry
poetry install
```

### Development

The project is set up for easy development and testing.

## License

MIT License - see LICENSE file for details.