"""CLI-specific visualization configuration.

This module customizes the SDK's default visualizer for CLI usage by:
- Skipping SystemPromptEvent (only relevant for SDK internals)
- Re-exporting DefaultConversationVisualizer for use in CLI
"""

from openhands.sdk.conversation.visualizer.default import (
    EVENT_VISUALIZATION_CONFIG,
    DefaultConversationVisualizer as CLIVisualizer,
    EventVisualizationConfig,
)
from openhands.sdk.event import SystemPromptEvent


# CLI-specific customization: skip SystemPromptEvent
# (not needed in CLI output, only relevant for SDK internals)
EVENT_VISUALIZATION_CONFIG[SystemPromptEvent] = EventVisualizationConfig(
    **{**EVENT_VISUALIZATION_CONFIG[SystemPromptEvent].model_dump(), "skip": True}
)

__all__ = ["CLIVisualizer"]
