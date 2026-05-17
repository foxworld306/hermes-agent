import yaml
from pathlib import Path
from typing import List, Optional, Dict
import os


class ToolService:
    """Manage global tool enable/disable status"""

    def __init__(self, config_path: str = "~/.hermes/config.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.admin_config_key = "admin"
        self.tools_key = "tools"
        self.enabled_key = "enabled"
        self._ensure_admin_config()

    def _ensure_admin_config(self):
        """Ensure admin config section exists"""
        config = self._load_config()
        if self.admin_config_key not in config:
            config[self.admin_config_key] = {}
        if self.tools_key not in config[self.admin_config_key]:
            config[self.admin_config_key][self.tools_key] = {}
        if self.enabled_key not in config[self.admin_config_key][self.tools_key]:
            config[self.admin_config_key][self.tools_key][self.enabled_key] = []
        self._save_config(config)

    def _load_config(self) -> dict:
        """Load config file"""
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _save_config(self, config: dict):
        """Save config file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def _get_disabled_tools(self) -> List[str]:
        """Get disabled tools list (using enabled whitelist)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])

        if not enabled:
            return []

        all_tools = self._get_all_available_tools()
        return [t for t in all_tools if t not in enabled]

    def _get_all_available_tools(self) -> List[str]:
        """Get all available tool names (hardcoded for Phase 1)"""
        return [
            "web_search", "terminal", "file", "code_execution",
            "browser", "memory", "todo", "vision"
        ]

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if tool is enabled"""
        disabled = self._get_disabled_tools()
        return tool_name not in disabled

    def enable_tool(self, tool_name: str):
        """Enable tool (add to enabled list)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])

        if tool_name not in enabled:
            enabled.append(tool_name)
            config[self.admin_config_key][self.tools_key][self.enabled_key] = enabled
            self._save_config(config)

    def disable_tool(self, tool_name: str):
        """Disable tool (remove from enabled list)"""
        config = self._load_config()
        enabled = config.get(self.admin_config_key, {}).get(self.tools_key, {}).get(self.enabled_key, [])

        if not enabled:
            # Empty list means all enabled; populate with all tools except the disabled one
            all_tools = self._get_all_available_tools()
            enabled = [t for t in all_tools if t != tool_name]
        elif tool_name in enabled:
            enabled.remove(tool_name)

        config[self.admin_config_key][self.tools_key][self.enabled_key] = enabled
        self._save_config(config)

    def get_tool_status(self) -> List[Dict]:
        """Get all tool status list"""
        all_tools = self._get_all_available_tools()
        disabled = self._get_disabled_tools()

        return [
            {
                "tool_name": tool,
                "enabled": tool not in disabled,
                "description": self._get_tool_description(tool)
            }
            for tool in all_tools
        ]

    def _get_tool_description(self, tool_name: str) -> str:
        """Get tool description"""
        descriptions = {
            "web_search": "Search the web for information",
            "terminal": "Execute commands in terminal",
            "file": "Read and write files",
            "code_execution": "Execute code snippets",
            "browser": "Navigate and interact with web pages",
            "memory": "Store and retrieve memories",
            "todo": "Manage todo lists",
            "vision": "Analyze images and vision content"
        }
        return descriptions.get(tool_name, "No description available")

    def filter_tools(self, tools: List[str]) -> List[str]:
        """Filter out disabled tools"""
        disabled = self._get_disabled_tools()
        if not disabled:
            return tools
        return [t for t in tools if t not in disabled]
