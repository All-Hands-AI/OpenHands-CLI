#!/usr/bin/env python3
"""
Security analyzer for OpenHands CLI.
Provides risk assessment for agent actions to enable confirmation mode.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class ActionSecurityRisk(Enum):
    """Security risk levels for agent actions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class SecurityAnalyzer:
    """Analyzes agent actions to determine security risk levels."""

    def __init__(self) -> None:
        # High-risk command patterns
        self.high_risk_patterns = [
            r"\brm\s+-rf\s+/",  # rm -rf /
            r"\bsudo\s+rm\s+-rf",  # sudo rm -rf
            r"\bchmod\s+777",  # chmod 777
            r"\bchown\s+.*\s+/",  # chown on root
            r"\bmkfs\.",  # filesystem formatting
            r"\bdd\s+if=.*of=/dev/",  # disk writing
            r"\b(wget|curl).*\|\s*sh",  # pipe to shell
            r"\b(wget|curl).*\|\s*bash",  # pipe to bash
            r"\biptables\s+-F",  # flush firewall rules
            r"\bufw\s+--force\s+reset",  # reset firewall
            r"\bsystemctl\s+stop\s+ssh",  # stop SSH service
            r"\bkillall\s+-9",  # force kill all processes
            r"\bpkill\s+-9",  # force kill processes
            r"\b/etc/passwd",  # password file access
            r"\b/etc/shadow",  # shadow file access
            r"\bpasswd\s+root",  # change root password
            r"\bsu\s+-",  # switch to root
            r"\bsudo\s+su",  # sudo to root
        ]

        # Medium-risk command patterns
        self.medium_risk_patterns = [
            r"\brm\s+-rf\s+\w+",  # rm -rf with specific paths
            r"\bsudo\s+",  # any sudo command
            r"\bchmod\s+[0-7]{3}",  # chmod with permissions
            r"\bchown\s+",  # any chown command
            r"\bmv\s+.*\s+/usr/",  # move to system directories
            r"\bcp\s+.*\s+/usr/",  # copy to system directories
            r"\bsystemctl\s+(start|stop|restart)",  # service management
            r"\bservice\s+\w+\s+(start|stop|restart)",  # service management
            r"\bapt\s+install",  # package installation
            r"\byum\s+install",  # package installation
            r"\bpip\s+install",  # Python package installation
            r"\bnpm\s+install\s+-g",  # global npm installation
            r"\bgit\s+clone\s+.*\s+/",  # clone to root directories
            r"\bwget\s+.*\s+-O\s+/",  # download to root directories
            r"\bcurl\s+.*\s+-o\s+/",  # download to root directories
        ]

        # Low-risk patterns (explicitly safe operations)
        self.low_risk_patterns = [
            r"\bls\s+",  # list files
            r"\bcat\s+",  # read files
            r"\bhead\s+",  # read file headers
            r"\btail\s+",  # read file tails
            r"\bgrep\s+",  # search in files
            r"\bfind\s+",  # find files
            r"\becho\s+",  # echo text
            r"\bpwd\b",  # print working directory
            r"\bwhoami\b",  # current user
            r"\bdate\b",  # current date
            r"\bhistory\b",  # command history
            r"\bps\s+",  # process list
            r"\btop\b",  # process monitor
            r"\bhtop\b",  # process monitor
            r"\bdf\s+",  # disk usage
            r"\bdu\s+",  # directory usage
            r"\bfree\b",  # memory usage
            r"\buptime\b",  # system uptime
        ]

    def analyze_command(self, command: str) -> ActionSecurityRisk:
        """Analyze a shell command and return its security risk level."""
        if not command or not command.strip():
            return ActionSecurityRisk.LOW

        command_lower = command.lower().strip()

        # Check for high-risk patterns
        for pattern in self.high_risk_patterns:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return ActionSecurityRisk.HIGH

        # Check for medium-risk patterns
        for pattern in self.medium_risk_patterns:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return ActionSecurityRisk.MEDIUM

        # Check for explicitly low-risk patterns
        for pattern in self.low_risk_patterns:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return ActionSecurityRisk.LOW

        # Default to medium risk for unknown commands
        return ActionSecurityRisk.MEDIUM

    def analyze_file_operation(
        self, operation: str, file_path: str
    ) -> ActionSecurityRisk:
        """Analyze file operations and return security risk level."""
        if not file_path:
            return ActionSecurityRisk.LOW

        # High-risk file paths
        high_risk_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/boot/",
            "/sys/",
            "/proc/",
            "/dev/",
            "~/.ssh/",
            "~/.bashrc",
            "~/.profile",
            "/usr/bin/",
            "/usr/sbin/",
            "/bin/",
            "/sbin/",
        ]

        # Medium-risk file paths
        medium_risk_paths = [
            "/etc/",
            "/var/",
            "/opt/",
            "/usr/",
            "~/.config/",
            "~/.local/",
        ]

        file_path_lower = file_path.lower()

        # Check for high-risk paths
        for path in high_risk_paths:
            if file_path_lower.startswith(path.lower()):
                return ActionSecurityRisk.HIGH

        # Check for medium-risk paths
        for path in medium_risk_paths:
            if file_path_lower.startswith(path.lower()):
                return ActionSecurityRisk.MEDIUM

        # Operations that are inherently risky
        if operation.lower() in ["delete", "remove", "chmod", "chown"]:
            return ActionSecurityRisk.MEDIUM

        return ActionSecurityRisk.LOW

    def analyze_action(
        self, action_type: str, action_data: dict[str, Any]
    ) -> ActionSecurityRisk:
        """Analyze any agent action and return security risk level."""
        if action_type == "execute_bash":
            command = action_data.get("command", "")
            return self.analyze_command(command)

        elif action_type == "str_replace_editor":
            command = action_data.get("command", "")
            file_path = action_data.get("path", "")

            if command in ["create", "str_replace", "insert"]:
                return self.analyze_file_operation(command, file_path)
            elif command == "view":
                return ActionSecurityRisk.LOW
            else:
                return ActionSecurityRisk.MEDIUM

        # Default to medium risk for unknown actions
        return ActionSecurityRisk.MEDIUM


# Global security analyzer instance
security_analyzer = SecurityAnalyzer()
