"""Tests for ACP file operations."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from acp.schema import ReadTextFileRequest, WriteTextFileRequest

from openhands_acp.file_operations import FileSystemHandler


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_connection():
    """Create a mock ACP connection."""
    return AsyncMock()


@pytest.fixture
def file_handler(mock_connection, temp_dir):
    """Create a file system handler."""
    return FileSystemHandler(mock_connection, temp_dir)


def test_resolve_path_relative(file_handler, temp_dir):
    """Test resolving relative paths."""
    resolved = file_handler._resolve_path("test.txt")
    expected = Path(temp_dir) / "test.txt"
    assert resolved == expected.resolve()


def test_resolve_path_absolute_within_workdir(file_handler, temp_dir):
    """Test resolving absolute paths within working directory."""
    test_path = os.path.join(temp_dir, "test.txt")
    resolved = file_handler._resolve_path(test_path)
    assert resolved == Path(test_path).resolve()


def test_resolve_path_outside_workdir(file_handler):
    """Test that paths outside working directory are rejected."""
    with pytest.raises(ValueError, match="outside the working directory"):
        file_handler._resolve_path("/etc/passwd")


def test_resolve_path_parent_traversal(file_handler):
    """Test that parent directory traversal is blocked."""
    with pytest.raises(ValueError, match="outside the working directory"):
        file_handler._resolve_path("../../../etc/passwd")


@pytest.mark.asyncio
async def test_read_file_content_success(file_handler, temp_dir):
    """Test reading file content successfully."""
    test_file = Path(temp_dir) / "test.txt"
    test_content = "Hello, world!"
    test_file.write_text(test_content)
    
    content = await file_handler.read_file_content("test.txt")
    assert content == test_content


@pytest.mark.asyncio
async def test_read_file_content_not_found(file_handler):
    """Test reading non-existent file."""
    with pytest.raises(FileNotFoundError):
        await file_handler.read_file_content("nonexistent.txt")


@pytest.mark.asyncio
async def test_write_file_content_success(file_handler, temp_dir):
    """Test writing file content successfully."""
    test_content = "Hello, world!"
    
    await file_handler.write_file_content("test.txt", test_content)
    
    test_file = Path(temp_dir) / "test.txt"
    assert test_file.read_text() == test_content


@pytest.mark.asyncio
async def test_write_file_content_create_directories(file_handler, temp_dir):
    """Test writing file with directory creation."""
    test_content = "Hello, world!"
    
    await file_handler.write_file_content("subdir/test.txt", test_content)
    
    test_file = Path(temp_dir) / "subdir" / "test.txt"
    assert test_file.exists()
    assert test_file.read_text() == test_content


@pytest.mark.asyncio
async def test_handle_read_text_file_success(file_handler, temp_dir):
    """Test handling read text file request successfully."""
    test_file = Path(temp_dir) / "test.txt"
    test_content = "Hello, world!"
    test_file.write_text(test_content)
    
    request = ReadTextFileRequest(path="test.txt")
    response = await file_handler.handle_read_text_file(request)
    
    assert response.content == test_content
    assert not hasattr(response, 'error') or response.error is None


@pytest.mark.asyncio
async def test_handle_read_text_file_not_found(file_handler):
    """Test handling read text file request for non-existent file."""
    request = ReadTextFileRequest(path="nonexistent.txt")
    response = await file_handler.handle_read_text_file(request)
    
    assert response.content == ""
    assert "File not found" in response.error


@pytest.mark.asyncio
async def test_handle_read_text_file_outside_workdir(file_handler):
    """Test handling read text file request outside working directory."""
    request = ReadTextFileRequest(path="/etc/passwd")
    response = await file_handler.handle_read_text_file(request)
    
    assert response.content == ""
    assert "outside the working directory" in response.error


@pytest.mark.asyncio
async def test_handle_write_text_file_success(file_handler, temp_dir):
    """Test handling write text file request successfully."""
    test_content = "Hello, world!"
    
    request = WriteTextFileRequest(path="test.txt", content=test_content)
    response = await file_handler.handle_write_text_file(request)
    
    assert not hasattr(response, 'error') or response.error is None
    
    # Verify file was written
    test_file = Path(temp_dir) / "test.txt"
    assert test_file.read_text() == test_content


@pytest.mark.asyncio
async def test_handle_write_text_file_outside_workdir(file_handler):
    """Test handling write text file request outside working directory."""
    request = WriteTextFileRequest(path="/tmp/test.txt", content="test")
    response = await file_handler.handle_write_text_file(request)
    
    assert "outside the working directory" in response.error


def test_is_path_safe(file_handler):
    """Test path safety checking."""
    assert file_handler.is_path_safe("test.txt")
    assert file_handler.is_path_safe("subdir/test.txt")
    assert not file_handler.is_path_safe("/etc/passwd")
    assert not file_handler.is_path_safe("../../../etc/passwd")


def test_get_relative_path(file_handler, temp_dir):
    """Test getting relative path."""
    abs_path = os.path.join(temp_dir, "test.txt")
    relative = file_handler.get_relative_path(abs_path)
    assert relative == "test.txt"
    
    # Test path outside working directory
    outside_path = "/etc/passwd"
    relative = file_handler.get_relative_path(outside_path)
    assert relative is None