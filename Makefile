.PHONY: help install install-dev test lint format clean run

# Default target
help:
	@echo "OpenHands CLI - Available commands:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  clean        - Clean build artifacts"
	@echo "  run          - Run the CLI"

# Install the package
install:
	uv sync

# Install with development dependencies
install-dev:
	uv sync --extra dev

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run flake8 openhands_cli/
	uv run mypy openhands_cli/

# Format code
format:
	uv run black openhands_cli/
	uv run isort openhands_cli/

# Clean build artifacts
clean:
	rm -rf .venv/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run the CLI
run:
	uv run openhands-cli

# Install UV if not present
install-uv:
	@if ! command -v uv &> /dev/null; then \
		echo "Installing UV..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	else \
		echo "UV is already installed"; \
	fi