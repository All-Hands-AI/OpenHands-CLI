"""Textual-based settings screens for OpenHands CLI."""

import os
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, TextArea

from openhands.sdk import Agent, BaseConversation, LLM, LLMSummarizingCondenser, LocalFileStore
from openhands_cli.locations import AGENT_SETTINGS_PATH, MCP_CONFIG_FILE, PERSISTENCE_DIR
from openhands_cli.tui.settings.store import AgentStore
from openhands_cli.utils import (
    get_default_cli_agent,
    get_llm_metadata,
    should_set_litellm_extra_body,
)


class SettingsScreen(ModalScreen):
    """Textual-based settings screen."""
    
    CSS = """
    SettingsScreen {
        align: center middle;
    }
    
    #settings_container {
        width: 80;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #settings_content {
        height: auto;
        margin: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    #buttons Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, conversation: BaseConversation | None = None):
        super().__init__()
        self.file_store = LocalFileStore(PERSISTENCE_DIR)
        self.agent_store = AgentStore()
        self.conversation = conversation
    
    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        with Container(id="settings_container"):
            yield Label("Settings", id="title")
            yield self._create_settings_display()
            with Horizontal(id="buttons"):
                yield Button("Basic Settings", id="basic", variant="primary")
                yield Button("Advanced Settings", id="advanced", variant="default")
                yield Button("Close", id="close", variant="default")
    
    def _create_settings_display(self) -> Static:
        """Create the settings display widget."""
        agent_spec = self.agent_store.load()
        if not agent_spec:
            return Static("No agent configuration found.", id="settings_content")
        
        llm = agent_spec.llm
        advanced_llm_settings = True if llm.base_url else False
        
        # Prepare labels and values based on settings
        labels_and_values = []
        if not advanced_llm_settings:
            # Attempt to determine provider, fallback if not directly available
            provider = llm.model.split("/")[0] if "/" in llm.model else "Unknown"
            
            labels_and_values.extend([
                ("   LLM Provider", str(provider)),
                ("   LLM Model", str(llm.model)),
            ])
        else:
            labels_and_values.extend([
                ("   Custom Model", llm.model),
                ("   Base URL", llm.base_url),
            ])
        
        labels_and_values.extend([
            ("   API Key", "********" if llm.api_key else "Not Set"),
        ])
        
        if self.conversation:
            labels_and_values.extend([
                (
                    "   Confirmation Mode",
                    "Enabled" if self.conversation.is_confirmation_mode_active else "Disabled",
                )
            ])
        
        labels_and_values.extend([
            (
                "   Memory Condensation",
                "Enabled" if agent_spec.condenser else "Disabled",
            ),
            (
                "   Configuration File",
                os.path.join(PERSISTENCE_DIR, AGENT_SETTINGS_PATH),
            ),
        ])
        
        # Calculate max widths for alignment
        str_labels_and_values = [
            (label, str(value)) for label, value in labels_and_values
        ]
        max_label_width = (
            max(len(label) for label, _ in str_labels_and_values)
            if str_labels_and_values
            else 0
        )
        
        # Construct the summary text with aligned columns
        settings_lines = [
            f"{label + ':':<{max_label_width + 1}} {value:<}"
            for label, value in str_labels_and_values
        ]
        settings_text = "\n".join(settings_lines)
        
        return Static(settings_text, id="settings_content")
    
    @on(Button.Pressed, "#basic")
    def handle_basic_settings(self) -> None:
        """Handle basic settings configuration."""
        self.app.push_screen("basic_settings")
    
    @on(Button.Pressed, "#advanced")
    def handle_advanced_settings(self) -> None:
        """Handle advanced settings configuration."""
        self.app.push_screen("advanced_settings")
    
    @on(Button.Pressed, "#close")
    def handle_close(self) -> None:
        """Close the settings screen."""
        self.dismiss()


class MCPScreen(ModalScreen):
    """Textual-based MCP configuration screen."""
    
    CSS = """
    MCPScreen {
        align: center middle;
    }
    
    #mcp_container {
        width: 90;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #mcp_content {
        height: auto;
        margin: 1;
    }
    
    #buttons {
        align: center middle;
        margin-top: 1;
    }
    
    #buttons Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent
    
    def compose(self) -> ComposeResult:
        """Compose the MCP screen."""
        with Container(id="mcp_container"):
            yield Label("MCP (Model Context Protocol) Configuration", id="title")
            yield self._create_mcp_display()
            with Horizontal(id="buttons"):
                yield Button("Close", id="close", variant="primary")
    
    def _create_mcp_display(self) -> Static:
        """Create the MCP configuration display."""
        from pathlib import Path
        from fastmcp.mcp_config import MCPConfig
        import json
        
        content_lines = []
        
        # Header information
        content_lines.extend([
            "To get started:",
            "  1. Create the configuration file: ~/.openhands/mcp.json",
            "  2. Add your MCP server configurations",
            "     https://gofastmcp.com/clients/client#configuration-format",
            "  3. Restart your OpenHands session to load the new configuration",
            "",
        ])
        
        # Check MCP config status
        config_path = Path(PERSISTENCE_DIR) / MCP_CONFIG_FILE
        
        if not config_path.exists():
            content_lines.extend([
                "Status: Configuration file not found",
                "",
                "Current Agent MCP Servers:",
            ])
        else:
            try:
                mcp_config = MCPConfig.from_file(config_path)
                servers = mcp_config.to_dict().get("mcpServers", {})
                content_lines.extend([
                    f"Status: Valid MCP configuration found with {len(servers)} server(s)",
                    "",
                    "Current Agent MCP Servers:",
                ])
            except Exception as e:
                content_lines.extend([
                    f"Status: Invalid MCP configuration file: {str(e)}",
                    "",
                    "Current Agent MCP Servers:",
                ])
        
        # Show current agent servers
        current_servers = self.agent.mcp_config.get("mcpServers", {})
        if current_servers:
            for name, cfg in current_servers.items():
                content_lines.append(f"  • {name}")
                if isinstance(cfg, dict):
                    if "command" in cfg:
                        cmd = cfg.get("command", "")
                        args = cfg.get("args", [])
                        args_str = " ".join(args) if args else ""
                        content_lines.append("    Type: Command-based")
                        if cmd or args_str:
                            content_lines.append(f"    Command: {cmd} {args_str}")
                    elif "url" in cfg:
                        url = cfg.get("url", "")
                        auth = cfg.get("auth", "none")
                        content_lines.append("    Type: URL-based")
                        if url:
                            content_lines.append(f"    URL: {url}")
                        content_lines.append(f"    Auth: {auth}")
        else:
            content_lines.append("  None configured on the current agent.")
        
        content_lines.append("")
        
        # Show incoming servers if config exists
        if config_path.exists():
            try:
                mcp_config = MCPConfig.from_file(config_path)
                incoming_servers = mcp_config.to_dict().get("mcpServers", {})
                
                if incoming_servers:
                    content_lines.append("Incoming Servers on Restart (from ~/.openhands/mcp.json):")
                    
                    current_names = set(current_servers.keys())
                    incoming_names = set(incoming_servers.keys())
                    new_servers = sorted(incoming_names - current_names)
                    
                    if new_servers:
                        content_lines.append("  New servers (will be added):")
                        for name in new_servers:
                            content_lines.append(f"    • {name}")
                    
                    # Check for changed servers
                    changed_servers = []
                    for name in sorted(incoming_names & current_names):
                        current_spec = json.dumps(current_servers[name], sort_keys=True)
                        incoming_spec = json.dumps(incoming_servers[name], sort_keys=True)
                        if current_spec != incoming_spec:
                            changed_servers.append(name)
                    
                    if changed_servers:
                        content_lines.append("  Updated servers (configuration will change):")
                        for name in changed_servers:
                            content_lines.append(f"    • {name}")
                    
                    if not new_servers and not changed_servers:
                        content_lines.append("  All configured servers match the current agent configuration.")
                else:
                    content_lines.append("No incoming servers detected for next restart.")
            except Exception:
                content_lines.append("No incoming servers detected for next restart.")
        else:
            content_lines.append("No incoming servers detected for next restart.")
        
        return Static("\n".join(content_lines), id="mcp_content")
    
    @on(Button.Pressed, "#close")
    def handle_close(self) -> None:
        """Close the MCP screen."""
        self.dismiss()