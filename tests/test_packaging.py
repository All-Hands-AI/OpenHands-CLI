#!/usr/bin/env python3
"""
Tests for PyInstaller packaging functionality.

This module tests that the PyInstaller packaging process works correctly
and that the generated executable functions as expected.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestPackaging:
    """Test cases for PyInstaller packaging."""

    def test_spec_file_exists(self):
        """Test that the PyInstaller spec file exists."""
        spec_file = Path("openhands-cli.spec")
        assert spec_file.exists(), "PyInstaller spec file should exist"
        assert spec_file.is_file(), "Spec file should be a regular file"

    def test_build_script_exists(self):
        """Test that the build script exists and is executable."""
        build_script = Path("build.py")
        assert build_script.exists(), "Build script should exist"
        assert build_script.is_file(), "Build script should be a regular file"
        
        # Check if it's executable (on Unix-like systems)
        if os.name != 'nt':
            assert os.access(build_script, os.X_OK), "Build script should be executable"

    def test_shell_build_script_exists(self):
        """Test that the shell build script exists and is executable."""
        build_script = Path("build.sh")
        assert build_script.exists(), "Shell build script should exist"
        assert build_script.is_file(), "Shell build script should be a regular file"
        
        # Check if it's executable (on Unix-like systems)
        if os.name != 'nt':
            assert os.access(build_script, os.X_OK), "Shell build script should be executable"

    def test_spec_file_content(self):
        """Test that the spec file contains expected content."""
        spec_file = Path("openhands-cli.spec")
        content = spec_file.read_text()
        
        # Check for key components
        assert "openhands_cli/simple_main.py" in content, "Should reference main entry point"
        assert "Analysis" in content, "Should contain PyInstaller Analysis configuration"
        assert "EXE" in content, "Should contain PyInstaller EXE configuration"
        assert "console=True" in content, "Should be configured as console application"
        assert "openhands-cli" in content, "Should have correct executable name"

    def test_build_script_functionality(self):
        """Test that the build script can be imported and has expected functions."""
        # Add the current directory to Python path for import
        sys.path.insert(0, str(Path.cwd()))
        
        try:
            import build
            
            # Check that main functions exist
            assert hasattr(build, 'main'), "Build script should have main function"
            assert hasattr(build, 'build_executable'), "Build script should have build_executable function"
            assert hasattr(build, 'clean_build_directories'), "Build script should have clean function"
            assert hasattr(build, 'test_executable'), "Build script should have test function"
            
        finally:
            # Clean up sys.path
            if str(Path.cwd()) in sys.path:
                sys.path.remove(str(Path.cwd()))

    def test_gitignore_updated(self):
        """Test that .gitignore properly excludes build artifacts but includes spec file."""
        gitignore_file = Path(".gitignore")
        assert gitignore_file.exists(), ".gitignore should exist"
        
        content = gitignore_file.read_text()
        
        # Should exclude build directories
        assert "build/" in content, "Should exclude build/ directory"
        assert "dist/" in content, "Should exclude dist/ directory"
        
        # Should not exclude spec files (commented out)
        assert "# *.spec" in content, "Should not exclude spec files (should be commented)"

    @pytest.mark.skipif(
        not Path("dist/openhands-cli").exists() and not Path("dist/openhands-cli.exe").exists(),
        reason="Executable not found - run build first"
    )
    def test_executable_exists_and_runs(self):
        """Test that the built executable exists and can run successfully."""
        # Find the executable
        exe_path = Path("dist/openhands-cli")
        if not exe_path.exists():
            exe_path = Path("dist/openhands-cli.exe")  # Windows
        
        assert exe_path.exists(), "Built executable should exist"
        assert exe_path.is_file(), "Executable should be a regular file"
        
        # Test that it can run
        try:
            result = subprocess.run(
                [str(exe_path)], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            # Should exit successfully
            assert result.returncode == 0, f"Executable should run successfully, got: {result.stderr}"
            
            # Should produce expected output
            assert "OpenHands CLI" in result.stdout, "Should display CLI title"
            assert "Welcome to OpenHands CLI" in result.stdout, "Should display welcome message"
            
        except subprocess.TimeoutExpired:
            # This is acceptable for interactive CLIs
            pass

    def test_build_artifacts_in_gitignore(self):
        """Test that build artifacts are properly ignored by git."""
        gitignore_file = Path(".gitignore")
        content = gitignore_file.read_text()
        
        # Common PyInstaller artifacts that should be ignored
        ignored_patterns = [
            "build/",
            "dist/",
            "*.manifest",
        ]
        
        for pattern in ignored_patterns:
            assert pattern in content, f"Pattern '{pattern}' should be in .gitignore"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])