"""
Tool Call Handler for ACP Integration.

This module handles tool calls from OpenHands agents, including permission
requests and execution of various tools like shell commands, file operations, etc.
"""

import asyncio
import logging
import subprocess
from typing import Any, Dict, List, Optional

from acp_impl import AgentSideConnection
from acp.schema import (
    PermissionOption,
    PermissionOptionKind,
    RequestPermissionRequest,
    RequestPermissionResponse,
    ToolCallStatus,
)


logger = logging.getLogger(__name__)


class ToolCallHandler:
    """
    Handles tool calls and permission requests for ACP integration.
    
    This class manages the execution of various tools requested by OpenHands
    agents, with proper permission handling through the ACP client.
    """

    def __init__(self, connection: AgentSideConnection, working_directory: str) -> None:
        """Initialize the tool call handler.
        
        Args:
            connection: The ACP connection to the client
            working_directory: The working directory for tool execution
        """
        self._connection = connection
        self._working_directory = working_directory
        
        logger.info("Tool call handler initialized with cwd: %s", working_directory)

    async def handle_tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> Any:
        """Handle a tool call from OpenHands.
        
        Args:
            session_id: The ACP session ID
            tool_name: The name of the tool to call
            tool_args: The tool arguments
            
        Returns:
            The tool call result
        """
        logger.info("Handling tool call: %s with args: %s", tool_name, tool_args)
        
        try:
            # Request permission before executing the tool
            permission_granted = await self._request_tool_permission(
                session_id=session_id,
                tool_name=tool_name,
                tool_args=tool_args,
            )
            
            if not permission_granted:
                logger.warning("Permission denied for tool call: %s", tool_name)
                return {"error": "Permission denied"}
            
            # Execute the tool based on its name
            if tool_name == "bash":
                return await self._execute_bash_command(tool_args)
            elif tool_name == "str_replace_editor":
                return await self._execute_file_edit(tool_args)
            elif tool_name == "create_file":
                return await self._execute_create_file(tool_args)
            else:
                logger.warning("Unknown tool: %s", tool_name)
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            logger.error("Error executing tool %s: %s", tool_name, e)
            return {"error": str(e)}

    async def _request_tool_permission(
        self,
        session_id: str,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> bool:
        """Request permission to execute a tool.
        
        Args:
            session_id: The ACP session ID
            tool_name: The name of the tool
            tool_args: The tool arguments
            
        Returns:
            True if permission is granted, False otherwise
        """
        # Create permission options
        permission_options = self._create_permission_options(tool_name, tool_args)
        
        if not permission_options:
            # No permission needed for this tool
            return True
        
        try:
            # Request permission from the client
            request = RequestPermissionRequest(
                sessionId=session_id,
                permissionOptions=permission_options,
            )
            
            response = await self._connection.requestPermission(request)
            
            # Check if permission was granted
            return response.outcome == "granted"
            
        except Exception as e:
            logger.error("Error requesting permission: %s", e)
            return False

    def _create_permission_options(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
    ) -> List[PermissionOption]:
        """Create permission options for a tool call.
        
        Args:
            tool_name: The name of the tool
            tool_args: The tool arguments
            
        Returns:
            List of permission options
        """
        if tool_name == "bash":
            command = tool_args.get("command", "")
            return [
                PermissionOption(
                    kind=PermissionOptionKind.allow,
                    description=f"Execute shell command: {command}",
                ),
                PermissionOption(
                    kind=PermissionOptionKind.deny,
                    description="Deny shell command execution",
                ),
            ]
        
        elif tool_name in ["str_replace_editor", "create_file"]:
            file_path = tool_args.get("path", "unknown")
            action = "edit" if tool_name == "str_replace_editor" else "create"
            return [
                PermissionOption(
                    kind=PermissionOptionKind.allow,
                    description=f"Allow {action} file: {file_path}",
                ),
                PermissionOption(
                    kind=PermissionOptionKind.deny,
                    description=f"Deny {action} file: {file_path}",
                ),
            ]
        
        # No permission options for unknown tools
        return []

    async def _execute_bash_command(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a bash command.
        
        Args:
            tool_args: The tool arguments containing the command
            
        Returns:
            The command execution result
        """
        command = tool_args.get("command", "")
        if not command:
            return {"error": "No command provided"}
        
        logger.info("Executing bash command: %s", command)
        
        try:
            # Execute the command with a timeout
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self._working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=30.0
            )
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": process.returncode,
            }
            
        except asyncio.TimeoutError:
            logger.error("Command timed out: %s", command)
            return {"error": "Command timed out"}
        except Exception as e:
            logger.error("Error executing command %s: %s", command, e)
            return {"error": str(e)}

    async def _execute_file_edit(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file edit operation.
        
        Args:
            tool_args: The tool arguments containing edit details
            
        Returns:
            The edit operation result
        """
        # TODO: Implement file editing logic
        # This would involve string replacement operations
        logger.info("File edit requested: %s", tool_args)
        return {"status": "File edit not yet implemented"}

    async def _execute_create_file(self, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file creation operation.
        
        Args:
            tool_args: The tool arguments containing file details
            
        Returns:
            The file creation result
        """
        # TODO: Implement file creation logic
        logger.info("File creation requested: %s", tool_args)
        return {"status": "File creation not yet implemented"}
