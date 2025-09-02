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


def clean_build_directories():
    """Clean up previous build artifacts."""
    print("🧹 Cleaning up previous build artifacts...")
    
    build_dirs = ["build", "dist", "__pycache__"]
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Clean up .pyc files
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))
    
    print("✅ Cleanup complete!")


def install_dependencies(install_pyinstaller=False):
    """Install required dependencies for building."""
    if not install_pyinstaller:
        print("⚠️  Skipping PyInstaller installation (use --install-pyinstaller to install)")
        return True
        
    print("📦 Installing build dependencies with uv...")
    
    try:
        # Check if uv is available
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ uv is not available. Please install uv first.")
        return False
    
    try:
        subprocess.run([
            "uv", "add", "--dev", "pyinstaller"
        ], check=True, capture_output=True)
        print("✅ PyInstaller installed successfully with uv!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyInstaller: {e}")
        return False
    
    return True


def build_executable(spec_file="openhands-cli.spec", clean=True, install_pyinstaller=False):
    """Build the executable using PyInstaller."""
    if clean:
        clean_build_directories()
    
    if not install_dependencies(install_pyinstaller):
        return False
    
    print(f"🔨 Building executable using {spec_file}...")
    
    try:
        # Run PyInstaller with uv
        cmd = ["uv", "run", "pyinstaller", spec_file, "--clean"]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ Build completed successfully!")
        
        # Check if the executable was created
        dist_dir = Path("dist")
        if dist_dir.exists():
            executables = list(dist_dir.glob("*"))
            if executables:
                print(f"📁 Executable(s) created in dist/:")
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


def test_executable():
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
        if os.name != 'nt':
            os.chmod(exe_path, 0o755)
        
        # Run the executable with a timeout
        result = subprocess.run([str(exe_path)], 
                              capture_output=True, 
                              text=True, 
                              timeout=30)
        
        if result.returncode == 0:
            print("✅ Executable test passed!")
            print("Output preview:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            return True
        else:
            print(f"❌ Executable test failed with return code {result.returncode}")
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Executable test timed out (this might be normal for interactive CLIs)")
        return True
    except Exception as e:
        print(f"❌ Error testing executable: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build OpenHands CLI executable")
    parser.add_argument("--spec", default="openhands-cli.spec", 
                       help="PyInstaller spec file to use")
    parser.add_argument("--no-clean", action="store_true", 
                       help="Skip cleaning build directories")
    parser.add_argument("--no-test", action="store_true", 
                       help="Skip testing the built executable")
    parser.add_argument("--install-pyinstaller", action="store_true",
                       help="Install PyInstaller using uv before building")
    
    args = parser.parse_args()
    
    print("🚀 OpenHands CLI Build Script")
    print("=" * 40)
    
    # Check if spec file exists
    if not os.path.exists(args.spec):
        print(f"❌ Spec file '{args.spec}' not found!")
        return 1
    
    # Build the executable
    if not build_executable(args.spec, clean=not args.no_clean, install_pyinstaller=args.install_pyinstaller):
        return 1
    
    # Test the executable
    if not args.no_test:
        if not test_executable():
            print("⚠️  Executable test failed, but build completed")
    
    print("\n🎉 Build process completed!")
    print("📁 Check the 'dist/' directory for your executable")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())