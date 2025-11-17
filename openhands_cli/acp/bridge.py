"""
OpenHands Bridge for ACP Integration.

This module provides the bridge between the ACP protocol and OpenHands agent system,
handling the translation of ACP requests to OpenHands operations and streaming
responses back to the ACP client.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from acp import AgentSideConnection, text_block, update_agent_message
from acp.schema import StopReason, ToolCallStatus, TextContentBlock
from openhands.sdk import Conversation, LLM, Action, Event

from .file_operations import FileSystemHandler
from .tools import ToolCallHandler


logger = logging.getLogger(__name__)


class OpenHandsBridge:
    """
    Bridge between ACP protocol and OpenHands agent system.
    
    This class handles the translation of ACP requests to OpenHands operations
    and streams responses back to the ACP client.
    """

    def __init__(
        self, 
        connection: AgentSideConnection,
        working_directory: str,
    ) -> None:
        """Initialize the OpenHands bridge.
        
        Args:
            connection: The ACP connection to the client
            working_directory: The working directory for the session
        """
        self._connection = connection
        self._working_directory = working_directory
        self._conversation: Optional[Conversation] = None
        self._file_handler = FileSystemHandler(connection, working_directory)
        self._tool_handler = ToolCallHandler(connection, working_directory)
        self._active_sessions: Dict[str, str] = {}  # session_id -> conversation_id
        
        logger.info("OpenHands bridge initialized with cwd: %s", working_directory)

    async def _ensure_conversation(self) -> Conversation:
        """Ensure conversation is initialized.
        
        Returns:
            The conversation instance
        """
        if not self._conversation:
            # Initialize LLM and conversation
            llm = LLM(
                model=os.getenv("OPENHANDS_MODEL", "gpt-4o-mini"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
            )
            
            self._conversation = Conversation(
                llm=llm,
                workspace_dir=self._working_directory,
            )
            
            logger.info("OpenHands conversation initialized")
        
        return self._conversation

    async def process_prompt(
        self, 
        session_id: str, 
        content_blocks: List[TextContentBlock]
    ) -> StopReason:
        """Process a user prompt through OpenHands.
        
        Args:
            session_id: The ACP session ID
            content_blocks: The content blocks from the prompt
            
        Returns:
            The stop reason for the response
        """
        try:
            # Convert ACP content blocks to OpenHands message
            message = await self._convert_content_blocks_to_message(content_blocks)
            
            # Get conversation
            conversation = await self._ensure_conversation()
            
            # Send message and get response
            response = await conversation.send_message(message)
            
            # Stream response back to client
            await self._connection.sessionUpdate({
                "sessionId": session_id,
                "update": update_agent_message(
                    text_block(response)
                )
            })
            
            return StopReason.endTurn
            
        except Exception as e:
            logger.error("Error processing prompt: %s", e)
            # Send error message to client
            await self._connection.sessionUpdate({
                "sessionId": session_id,
                "update": update_agent_message(
                    text_block(f"Error processing request: {str(e)}")
                )
            })
            return StopReason.error

    async def cancel_operation(self, session_id: str) -> None:
        """Cancel an ongoing operation.
        
        Args:
            session_id: The ACP session ID
        """
        logger.info("Cancelling operation for session: %s", session_id)
        
        # TODO: Implement cancellation logic
        # This would involve stopping any ongoing OpenHands operations
        
        conversation_id = self._active_sessions.get(session_id)
        if conversation_id and self._openhands_client:
            # Cancel the conversation if possible
            try:
                # OpenHands SDK might have a cancel method
                pass
            except Exception as e:
                logger.error("Error cancelling operation: %s", e)

    async def _convert_content_blocks_to_message(
        self, content_blocks: List[TextContentBlock]
    ) -> str:
        """Convert ACP content blocks to OpenHands message format.
        
        Args:
            content_blocks: The ACP content blocks
            
        Returns:
            The converted message string
        """
        message_parts = []
        
        for block in content_blocks:
            if hasattr(block, 'type'):
                if block.type == "text":
                    message_parts.append(block.text)
                elif block.type == "resource":
                    # Handle resource references
                    if hasattr(block, 'resource') and hasattr(block.resource, 'uri'):
                        # Read file content if it's a file URI
                        if block.resource.uri.startswith("file://"):
                            file_path = block.resource.uri[7:]  # Remove "file://"
                            try:
                                content = await self._file_handler.read_file_content(file_path)
                                message_parts.append(f"File content from {file_path}:\n{content}")
                            except Exception as e:
                                message_parts.append(f"Error reading file {file_path}: {e}")
                        else:
                            message_parts.append(f"Resource: {block.resource.uri}")
                # TODO: Handle other content types (image, audio, etc.)
        
        return "\n".join(message_parts)





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
        return await self._tool_handler.handle_tool_call(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
        )