#!/bin/bash
"""
Shell script wrapper for building OpenHands CLI executable.

This script provides a simple interface to build the OpenHands CLI
using PyInstaller with uv package management.
"""

set -e  # Exit on any error

echo "🚀 OpenHands CLI Build Script"
echo "=============================="

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv is required but not found! Please install uv first."
    exit 1
fi

# Run the Python build script using uv
uv run python build.py "$@"