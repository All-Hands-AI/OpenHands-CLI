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

## Binary Packaging

The OpenHands CLI can be packaged into a standalone executable binary using PyInstaller. This allows distribution of the CLI without requiring users to install Python or dependencies.

### Building the Executable

#### Quick Build

Use the provided build script to create a standalone executable:

```bash
# Using Python script (install PyInstaller first)
python3 build.py --install-pyinstaller

# Using shell script (Unix/Linux/macOS)
./build.sh --install-pyinstaller
```

#### Manual Build

You can also build manually using PyInstaller with uv:

```bash
# Install PyInstaller as dev dependency
uv add --dev pyinstaller

# Build using the spec file
uv run pyinstaller openhands-cli.spec --clean
```

### Build Options

The build script supports several options:

```bash
# Install PyInstaller and build
python3 build.py --install-pyinstaller

# Build without testing the executable
python3 build.py --install-pyinstaller --no-test

# Build without cleaning previous artifacts
python3 build.py --install-pyinstaller --no-clean

# Use a custom spec file
python3 build.py --install-pyinstaller --spec custom.spec

# Show help
python3 build.py --help
```

**Note:** Use `--install-pyinstaller` flag to automatically install PyInstaller as a dev dependency using uv. If PyInstaller is already installed, you can omit this flag.

### Output

The build process creates:
- `dist/openhands-cli` - The standalone executable
- `build/` - Temporary build files (automatically cleaned)

The executable is typically 10-15 MB and includes all necessary dependencies.

### Testing the Executable

The build script automatically tests the executable, but you can also test manually:

```bash
# Run the executable
./dist/openhands-cli

# Check that it displays the CLI interface
```

### Packaging Configuration

The packaging is configured through:
- `openhands-cli.spec` - PyInstaller specification file
- `build.py` - Build automation script
- `build.sh` - Shell wrapper script

The spec file is optimized for:
- Single-file executable
- Minimal size through exclusions
- All required dependencies included
- Console application mode
