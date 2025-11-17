# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for OpenHands ACP Agent.

This creates a standalone executable for the OpenHands Agent Client Protocol
implementation that can be used with ACP-compatible editors like Zed.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

block_cipher = None

# Define the main script
main_script = str(project_root / "openhands_acp" / "main.py")

# Collect all openhands_acp modules
openhands_acp_modules = []
openhands_acp_dir = project_root / "openhands_acp"
for py_file in openhands_acp_dir.glob("*.py"):
    if py_file.name != "__init__.py":
        module_name = f"openhands_acp.{py_file.stem}"
        openhands_acp_modules.append(module_name)

# Hidden imports for dependencies
hidden_imports = [
    # ACP dependencies
    "acp",
    "acp.schema",
    
    # OpenHands dependencies
    "openhands_sdk",
    "openhands_tools",
    
    # Standard library modules that might be missed
    "asyncio",
    "json",
    "logging",
    "pathlib",
    "uuid",
    
    # Pydantic
    "pydantic",
    "pydantic.fields",
    "pydantic.main",
    "pydantic.types",
    
    # Typer
    "typer",
    "typer.main",
    
    # OpenHands ACP modules
] + openhands_acp_modules

# Data files to include
datas = []

# Binaries to include
binaries = []

a = Analysis(
    [main_script],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude GUI-related modules to reduce size
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        
        # Exclude test modules
        "pytest",
        "unittest",
        "test",
        
        # Exclude development tools
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="openhands-acp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)