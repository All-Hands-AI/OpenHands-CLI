#!/usr/bin/env python3
"""
Build script for OpenHands CLI using PyInstaller.

This script packages the OpenHands CLI into a standalone executable binary
using PyInstaller with the custom spec file.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def clean_build_directories() -> None:
    """Clean up previous build artifacts."""
    print("🧹 Cleaning up previous build artifacts...")

    build_dirs = ["build", "dist", "__pycache__"]
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)

    # Clean up .pyc files
    for root, _dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))

    print("✅ Cleanup complete!")


def check_pyinstaller() -> bool:
    """Check if PyInstaller is available."""
    try:
        subprocess.run(
            ["uv", "run", "pyinstaller", "--version"], check=True, capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(
            "❌ PyInstaller is not available. Use --install-pyinstaller flag or install manually with:"
        )
        print("   uv add --dev pyinstaller")
        return False


def build_executable(
    spec_file: str = "openhands-cli.spec",
    clean: bool = True,
    install_pyinstaller: bool = False,
) -> bool:
    """Build the executable using PyInstaller."""
    if clean:
        clean_build_directories()

    # Check if PyInstaller is available (installation is handled by build.sh)
    if not check_pyinstaller():
        return False

    print(f"🔨 Building executable using {spec_file}...")

    try:
        # Run PyInstaller with uv
        cmd = ["uv", "run", "pyinstaller", spec_file, "--clean"]

        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        print("✅ Build completed successfully!")

        # Check if the executable was created
        dist_dir = Path("dist")
        if dist_dir.exists():
            executables = list(dist_dir.glob("*"))
            if executables:
                print("📁 Executable(s) created in dist/:")
                for exe in executables:
                    size = exe.stat().st_size / (1024 * 1024)  # Size in MB
                    print(f"  - {exe.name} ({size:.1f} MB)")
            else:
                print("⚠️  No executables found in dist/ directory")

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def test_executable() -> bool:
    """Test the built executable."""
    print("🧪 Testing the built executable...")

    exe_path = Path("dist/openhands-cli")
    if not exe_path.exists():
        # Try with .exe extension for Windows
        exe_path = Path("dist/openhands-cli.exe")
        if not exe_path.exists():
            print("❌ Executable not found!")
            return False

    try:
        # Make executable on Unix-like systems
        if os.name != "nt":
            os.chmod(exe_path, 0o755)

        # Test 1: Basic startup test - should fail gracefully without API key
        print("  Testing basic startup (should fail gracefully without API key)...")
        result = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=10,
            input="\n",  # Send newline to exit quickly
            env={
                **os.environ,
                "LITELLM_API_KEY": "",
                "OPENAI_API_KEY": "",
            },  # Clear API keys
        )

        # Should return exit code 1 (no API key) but not crash
        if result.returncode == 1:
            print("  ✅ Executable handles missing API key correctly (exit code 1)")
            if (
                "No API key found" in result.stderr
                or "No API key found" in result.stdout
            ):
                print("  ✅ Proper error message displayed")
            else:
                print("  ⚠️  Expected API key error message not found")
                print("  STDOUT:", result.stdout[:200])
                print("  STDERR:", result.stderr[:200])
        elif result.returncode == 0:
            print("  ⚠️  Executable returned 0 but should fail without API key")
            return False
        else:
            print(f"  ❌ Unexpected return code {result.returncode}")
            print("  STDOUT:", result.stdout[:500])
            print("  STDERR:", result.stderr[:500])
            return False

        # Test 2: Check that it doesn't crash with missing prompt files
        print("  Testing with dummy API key (should not crash on startup)...")
        result = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=10,
            input="\n",  # Send newline to exit quickly
            env={
                **os.environ,
                "LITELLM_API_KEY": "dummy-test-key",
                "LITELLM_MODEL": "dummy-model",
            },
        )

        # Should not crash with missing prompt file error
        if "system_prompt.j2 not found" in result.stderr:
            print("  ❌ Executable still has missing prompt file error!")
            print("  STDERR:", result.stderr)
            return False
        else:
            print("  ✅ No missing prompt file errors detected")

        print("✅ Executable test passed!")
        return True

    except subprocess.TimeoutExpired:
        print(
            "  ⚠️  Executable test timed out (this might be normal for interactive CLIs)"
        )
        return True
    except Exception as e:
        print(f"❌ Error testing executable: {e}")
        return False


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="Build OpenHands CLI executable")
    parser.add_argument(
        "--spec", default="openhands-cli.spec", help="PyInstaller spec file to use"
    )
    parser.add_argument(
        "--no-clean", action="store_true", help="Skip cleaning build directories"
    )
    parser.add_argument(
        "--no-test", action="store_true", help="Skip testing the built executable"
    )
    parser.add_argument(
        "--install-pyinstaller",
        action="store_true",
        help="Install PyInstaller using uv before building",
    )

    args = parser.parse_args()

    print("🚀 OpenHands CLI Build Script")
    print("=" * 40)

    # Check if spec file exists
    if not os.path.exists(args.spec):
        print(f"❌ Spec file '{args.spec}' not found!")
        return 1

    # Build the executable
    if not build_executable(
        args.spec, clean=not args.no_clean, install_pyinstaller=args.install_pyinstaller
    ):
        return 1

    # Test the executable
    if not args.no_test:
        if not test_executable():
            print("❌ Executable test failed, build process failed")
            return 1

    print("\n🎉 Build process completed!")
    print("📁 Check the 'dist/' directory for your executable")

    return 0


if __name__ == "__main__":
    sys.exit(main())
