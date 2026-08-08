"""
Bijou AI - Command Parser
==========================

Parses @bijou commands for explicit control of the AI agent.

Commands:
- @bijou quiet    → Enter Observer Mode (silent monitoring)
- @bijou active   → Resume normal responses
- @bijou summarize → Generate conversation summary
- @bijou analyze  → Provide sentiment/intent analysis
- @bijou help     → Show available commands

Author: W3J Bijou AI
Version: 2.2.0
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Command:
    """Represents a parsed command"""

    type: str
    args: Dict[str, Any]
    raw_message: str


class CommandParser:
    """
    Parses @bijou commands from messages.
    """

    # Command patterns
    COMMAND_PATTERN = r"@(?:bijou|bot)\s+(\w+)(?:\s+(.*))?"

    # Valid commands
    VALID_COMMANDS = {
        "quiet": "Enter Observer Mode (silent monitoring)",
        "active": "Resume normal responses",
        "summarize": "Generate conversation summary",
        "analyze": "Provide sentiment/intent analysis",
        "escalate": "Transfer conversation to human agent",
        "help": "Show available commands",
        "status": "Show current mode and settings",
    }

    def __init__(self):
        self.pattern = re.compile(self.COMMAND_PATTERN, re.IGNORECASE)

    def is_command(self, message: str) -> bool:
        """
        Check if message contains a @bijou command.

        Args:
            message: Message text to check

        Returns:
            True if message contains a command
        """
        return bool(self.pattern.search(message))

    def parse(self, message: str) -> Optional[Command]:
        """
        Parse a @bijou command from message.

        Args:
            message: Message text to parse

        Returns:
            Command object if valid command found, None otherwise
        """
        match = self.pattern.search(message)
        if not match:
            return None

        command_type = match.group(1).lower()
        command_args_str = match.group(2) or ""

        # Validate command
        if command_type not in self.VALID_COMMANDS:
            return Command(
                type="unknown", args={"requested": command_type}, raw_message=message
            )

        # Parse arguments based on command type
        args = self._parse_args(command_type, command_args_str)

        return Command(type=command_type, args=args, raw_message=message)

    def _parse_args(self, command_type: str, args_str: str) -> Dict[str, Any]:
        """
        Parse command arguments.

        Args:
            command_type: Type of command
            args_str: Arguments string

        Returns:
            Dictionary of parsed arguments
        """
        args = {}

        if command_type == "summarize":
            # Optional: number of messages to summarize
            if args_str.strip().isdigit():
                args["message_count"] = int(args_str.strip())
            else:
                args["message_count"] = 10  # Default

        elif command_type == "analyze":
            # Optional: specific aspect to analyze
            if args_str.strip():
                args["aspect"] = args_str.strip().lower()
            else:
                args["aspect"] = "all"

        return args

    def get_help_text(self) -> str:
        """
        Get help text for all commands.

        Returns:
            Formatted help text
        """
        help_lines = ["**Available Commands:**\n"]
        for cmd, description in self.VALID_COMMANDS.items():
            help_lines.append(f"• `@bijou {cmd}` - {description}")

        return "\n".join(help_lines)

    def format_unknown_command_response(self, requested_command: str) -> str:
        """
        Format response for unknown command.

        Args:
            requested_command: The unknown command that was requested

        Returns:
            Formatted error message with help
        """
        return (
            f"I don't recognize the command `{requested_command}`. "
            f"Here are the commands I understand:\n\n{self.get_help_text()}"
        )


# Example usage
if __name__ == "__main__":
    parser = CommandParser()

    test_messages = [
        "@bijou quiet",
        "Hey @bijou summarize the last 20 messages",
        "@bot analyze sentiment",
        "Can you @bijou help me?",
        "Just a normal message",
        "@bijou invalidcommand",
    ]

    for msg in test_messages:
        print(f"\nMessage: {msg}")
        if parser.is_command(msg):
            cmd = parser.parse(msg)
            print(f"  Command: {cmd.type}")
            print(f"  Args: {cmd.args}")
        else:
            print("  Not a command")
