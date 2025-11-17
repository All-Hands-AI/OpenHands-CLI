"""
File System Operations for ACP Integration.

This module handles file system operations requested by ACP clients,
including reading and writing text files with proper permission handling.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from acp import AgentSideConnection
from acp.schema import (
    ReadTextFileRequest,
    ReadTextFileResponse,
    WriteTextFileRequest,
    WriteTextFileResponse,
)


logger = logging.getLogger(__name__)


class FileSystemHandler:
    """
    Handles file system operations for ACP integration.
    
    This class manages file read/write operations with proper security
    and permission handling within the working directory context.
    """

    def __init__(self, connection: AgentSideConnection, working_directory: str) -> None:
        """Initialize the file system handler.
        
        Args:
            connection: The ACP connection to the client
            working_directory: The working directory for file operations
        """
        self._connection = connection
        self._working_directory = Path(working_directory).resolve()
        
        logger.info("File system handler initialized with cwd: %s", self._working_directory)

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a file path relative to the working directory.
        
        Args:
            file_path: The file path to resolve
            
        Returns:
            The resolved absolute path
            
        Raises:
            ValueError: If the path is outside the working directory
        """
        if os.path.isabs(file_path):
            resolved_path = Path(file_path).resolve()
        else:
            resolved_path = (self._working_directory / file_path).resolve()
        
        # Security check: ensure the path is within the working directory
        try:
            resolved_path.relative_to(self._working_directory)
        except ValueError:
            raise ValueError(
                f"Path {file_path} is outside the working directory {self._working_directory}"
            )
        
        return resolved_path

    async def read_file_content(self, file_path: str) -> str:
        """Read the content of a text file.
        
        Args:
            file_path: The path to the file to read
            
        Returns:
            The file content as a string
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file can't be read
            UnicodeDecodeError: If the file isn't valid text
        """
        resolved_path = self._resolve_path(file_path)
        
        logger.info("Reading file: %s", resolved_path)
        
        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug("Successfully read %d characters from %s", len(content), resolved_path)
            return content
            
        except FileNotFoundError:
            logger.error("File not found: %s", resolved_path)
            raise
        except PermissionError:
            logger.error("Permission denied reading file: %s", resolved_path)
            raise
        except UnicodeDecodeError as e:
            logger.error("Unicode decode error reading file %s: %s", resolved_path, e)
            raise

    async def write_file_content(self, file_path: str, content: str) -> None:
        """Write content to a text file.
        
        Args:
            file_path: The path to the file to write
            content: The content to write
            
        Raises:
            PermissionError: If the file can't be written
            OSError: If there's an OS-level error
        """
        resolved_path = self._resolve_path(file_path)
        
        logger.info("Writing file: %s", resolved_path)
        
        try:
            # Create parent directories if they don't exist
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug("Successfully wrote %d characters to %s", len(content), resolved_path)
            
        except PermissionError:
            logger.error("Permission denied writing file: %s", resolved_path)
            raise
        except OSError as e:
            logger.error("OS error writing file %s: %s", resolved_path, e)
            raise

    async def handle_read_text_file(self, request: ReadTextFileRequest) -> ReadTextFileResponse:
        """Handle a read text file request from ACP client.
        
        Args:
            request: The read text file request
            
        Returns:
            The read text file response
        """
        try:
            content = await self.read_file_content(request.path)
            return ReadTextFileResponse(content=content)
            
        except FileNotFoundError:
            return ReadTextFileResponse(
                content="",
                error=f"File not found: {request.path}"
            )
        except PermissionError:
            return ReadTextFileResponse(
                content="",
                error=f"Permission denied: {request.path}"
            )
        except UnicodeDecodeError:
            return ReadTextFileResponse(
                content="",
                error=f"File is not valid UTF-8 text: {request.path}"
            )
        except ValueError as e:
            return ReadTextFileResponse(
                content="",
                error=str(e)
            )
        except Exception as e:
            logger.error("Unexpected error reading file %s: %s", request.path, e)
            return ReadTextFileResponse(
                content="",
                error=f"Unexpected error: {str(e)}"
            )

    async def handle_write_text_file(self, request: WriteTextFileRequest) -> WriteTextFileResponse:
        """Handle a write text file request from ACP client.
        
        Args:
            request: The write text file request
            
        Returns:
            The write text file response
        """
        try:
            await self.write_file_content(request.path, request.content)
            return WriteTextFileResponse()
            
        except PermissionError:
            return WriteTextFileResponse(
                error=f"Permission denied: {request.path}"
            )
        except ValueError as e:
            return WriteTextFileResponse(
                error=str(e)
            )
        except OSError as e:
            return WriteTextFileResponse(
                error=f"OS error: {str(e)}"
            )
        except Exception as e:
            logger.error("Unexpected error writing file %s: %s", request.path, e)
            return WriteTextFileResponse(
                error=f"Unexpected error: {str(e)}"
            )

    def is_path_safe(self, file_path: str) -> bool:
        """Check if a file path is safe to access.
        
        Args:
            file_path: The file path to check
            
        Returns:
            True if the path is safe, False otherwise
        """
        try:
            self._resolve_path(file_path)
            return True
        except ValueError:
            return False

    def get_relative_path(self, file_path: str) -> Optional[str]:
        """Get the relative path from the working directory.
        
        Args:
            file_path: The file path to convert
            
        Returns:
            The relative path or None if not within working directory
        """
        try:
            resolved_path = self._resolve_path(file_path)
            return str(resolved_path.relative_to(self._working_directory))
        except ValueError:
            return None