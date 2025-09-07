# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for OpenHands CLI.

This spec file configures PyInstaller to create a standalone executable
for the OpenHands CLI application.
"""

from pathlib import Path
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Ensure build-time import resolution prefers the packaged SDK over the monorepo path
# Needed when running build inside OpenHands conversation (due to nested runtimes)
_sys_paths_to_remove = [p for p in list(sys.path) if p.startswith('/openhands/code')]
for _p in _sys_paths_to_remove:
    try:
        sys.path.remove(_p)
    except ValueError:
        pass

# Get the project root directory (current working directory when running PyInstaller)
project_root = Path.cwd()

a = Analysis(
    ['openhands_cli/simple_main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include any data files that might be needed
        # Add more data files here if needed in the future
        *collect_data_files('tiktoken'),
        *collect_data_files('tiktoken_ext'),
        *collect_data_files('litellm'),
        *collect_data_files('fastmcp'),
        *collect_data_files('mcp'),
        # Include Jinja prompt templates required by the agent SDK
        *collect_data_files('openhands.sdk.agent.agent', includes=['prompts/*.j2']),
        # Include package metadata for importlib.metadata
        ('.venv/lib/python3.12/site-packages/fastmcp-2.12.2.dist-info', 'fastmcp-2.12.2.dist-info'),
        ('.venv/lib/python3.12/site-packages/mcp-1.13.1.dist-info', 'mcp-1.13.1.dist-info'),
        ('.venv/lib/python3.12/site-packages/openhands_sdk-1.0.0.dist-info', 'openhands_sdk-1.0.0.dist-info'),
        ('.venv/lib/python3.12/site-packages/openhands_tools-1.0.0.dist-info', 'openhands_tools-1.0.0.dist-info'),
    ],
    hiddenimports=[
        # Explicitly include modules that might not be detected automatically
        'openhands_cli.tui',
        'openhands_cli.pt_style',
        *collect_submodules('prompt_toolkit'),
        # Include OpenHands SDK submodules explicitly to avoid resolution issues
        *collect_submodules('openhands.sdk'),
        *collect_submodules('openhands.tools'),

        *collect_submodules('tiktoken'),
        *collect_submodules('tiktoken_ext'),
        *collect_submodules('litellm'),
        *collect_submodules('fastmcp'),
        # Include mcp but exclude CLI parts that require typer
        'mcp.types',
        'mcp.client',
        'mcp.server',
        'mcp.shared',
        # Additional dependencies that might be needed
        *collect_submodules('pydantic'),
        *collect_submodules('httpx'),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce binary size
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        # Exclude mcp CLI parts that cause issues
        'mcp.cli',
        'mcp.cli.cli',
    ],
    noarchive=False,
    # IMPORTANT: do not use optimize=2 (-OO) because it strips docstrings used by PLY/bashlex grammar
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='openhands-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols to reduce size
    upx=True,    # Use UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI application needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)
