# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for OpenHands CLI.

This spec file configures PyInstaller to create a standalone executable
for the OpenHands CLI application.
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

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
    ],
    hiddenimports=[
        # Explicitly include modules that might not be detected automatically
        'openhands_cli.tui',
        'openhands_cli.pt_style',
        *collect_submodules('prompt_toolkit'),
        *collect_submodules('openhands.core'),
        *collect_submodules('openhands.tools'),
        *collect_submodules('tiktoken'),
        *collect_submodules('tiktoken_ext'),
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
    ],
    noarchive=False,
    optimize=2,  # Enable Python optimization
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
