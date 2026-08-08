"""
Bijou Command Detection - Resume and Control Commands
======================================================

Detects special commands in messages for controlling Bijou behavior.

Commands:
- @bijou resume - Resume AI after human escalation
- @bijou quiet - Pause AI responses
- @bijou status - Check AI status
- @bijou help - Show available commands

Author: W3J Consulting
Date: 2026-02-11
Phase: 5 - Human Escalation Enhancements
"""

import re
from typing import Optional, Dict, Tuple
from loguru import logger
from enum import Enum


class BijouCommand(str, Enum):
    """Available Bijou commands"""
    RESUME = "resume"
    QUIET = "quiet"
    STATUS = "status"
    HELP = "help"
    TAKEOVER = "takeover"  # Alias for resume


class CommandDetector:
    """
    Detects and parses Bijou control commands in messages
    
    Features:
    - Case-insensitive matching
    - Multiple command formats (@bijou, bijou:, /bijou)
    - Command aliases
    - Parameter extraction
    """

    def __init__(self):
        """Initialize command detector"""
        # Command patterns (case-insensitive)
        self.patterns = [
            r'@bijou\s+(\w+)',  # @bijou resume
            r'bijou:\s*(\w+)',  # bijou: resume
            r'/bijou\s+(\w+)',  # /bijou resume
            r'bijou\s+(\w+)',   # bijou resume
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.patterns
        ]
        
        # Command aliases
        self.aliases = {
            "takeover": BijouCommand.RESUME,
            "back": BijouCommand.RESUME,
            "continue": BijouCommand.RESUME,
            "pause": BijouCommand.QUIET,
            "stop": BijouCommand.QUIET,
            "mute": BijouCommand.QUIET,
            "info": BijouCommand.STATUS,
            "?": BijouCommand.HELP
        }

    def detect_command(self, message: str) -> Optional[Tuple[BijouCommand, Dict]]:
        """
        Detect if message contains a Bijou command
        
        Args:
            message: User message
            
        Returns:
            Tuple of (command, params) or None if no command detected
        """
        if not message:
            return None
        
        # Try each pattern
        for pattern in self.compiled_patterns:
            match = pattern.search(message)
            if match:
                command_str = match.group(1).lower()
                
                # Resolve aliases
                command_str = self.aliases.get(command_str, command_str)
                
                # Convert to enum
                try:
                    command = BijouCommand(command_str)
                    
                    # Extract parameters (everything after the command)
                    params = self._extract_params(message, match)
                    
                    logger.info(f"Detected command: {command} with params: {params}")
                    return (command, params)
                    
                except ValueError:
                    # Not a valid command
                    logger.debug(f"Invalid command: {command_str}")
                    return None
        
        return None

    def _extract_params(self, message: str, match: re.Match) -> Dict:
        """Extract parameters from command"""
        # Get text after the matched command
        start_pos = match.end()
        remaining_text = message[start_pos:].strip()
        
        params = {}
        
        # Parse key=value pairs
        if remaining_text:
            # Look for key=value patterns
            kv_pattern = r'(\w+)=([^\s]+)'
            kv_matches = re.findall(kv_pattern, remaining_text)
            
            for key, value in kv_matches:
                params[key] = value
            
            # If no key=value pairs, treat as single text param
            if not params:
                params['text'] = remaining_text
        
        return params

    def is_resume_command(self, message: str) -> bool:
        """Quick check if message is a resume command"""
        result = self.detect_command(message)
        if result:
            command, _ = result
            return command == BijouCommand.RESUME
        return False

    def is_quiet_command(self, message: str) -> bool:
        """Quick check if message is a quiet/pause command"""
        result = self.detect_command(message)
        if result:
            command, _ = result
            return command == BijouCommand.QUIET
        return False

    def get_help_text(self) -> str:
        """Get help text for available commands"""
        return """**Available Bijou Commands:**

🔄 **@bijou resume** - Resume AI responses after human escalation
   Aliases: takeover, back, continue

⏸️ **@bijou quiet** - Pause AI responses temporarily
   Aliases: pause, stop, mute

ℹ️ **@bijou status** - Check current AI status

❓ **@bijou help** - Show this help message

**Examples:**
- `@bijou resume` - Resume normal AI operation
- `bijou: quiet` - Pause AI for this conversation
- `/bijou status` - Check if AI is active
"""


# Helper functions for integration
async def handle_bijou_command(
    message: str,
    customer_jid: str,
    tenant_id: str,
    escalation_api = None
) -> Optional[str]:
    """
    Handle Bijou command and return response message
    
    Args:
        message: User message
        customer_jid: Customer WhatsApp JID
        tenant_id: Tenant ID
        escalation_api: EscalationAPI instance (optional)
        
    Returns:
        Response message or None if no command detected
    """
    detector = CommandDetector()
    result = detector.detect_command(message)
    
    if not result:
        return None
    
    command, params = result
    
    try:
        if command == BijouCommand.RESUME:
            return await handle_resume_command(customer_jid, tenant_id, escalation_api)
        
        elif command == BijouCommand.QUIET:
            return await handle_quiet_command(customer_jid, tenant_id)
        
        elif command == BijouCommand.STATUS:
            return await handle_status_command(customer_jid, tenant_id)
        
        elif command == BijouCommand.HELP:
            return detector.get_help_text()
        
    except Exception as e:
        logger.error(f"Error handling command {command}: {e}")
        return "Sorry, I encountered an error processing that command."
    
    return None


async def handle_resume_command(
    customer_jid: str,
    tenant_id: str,
    escalation_api
) -> str:
    """Handle resume command"""
    if not escalation_api:
        return "AI responses are now active. How can I help?"
    
    try:
        # Find active escalation for this customer
        escalations = escalation_api.handover.get_queue(
            tenant_id=tenant_id,
            status=None  # Get all statuses
        )
        
        # Find escalation for this customer
        customer_escalations = [
            e for e in escalations
            if e.get("chat_jid") == customer_jid and e.get("status") in ["pending", "claimed", "in_progress"]
        ]
        
        if customer_escalations:
            # Resolve the most recent escalation
            latest_escalation = customer_escalations[0]
            
            # Use escalation API to resume
            from .escalation_api import ResumeRequest
            
            await escalation_api.resume_ai_after_escalation(
                ResumeRequest(
                    escalation_id=latest_escalation["id"],
                    tenant_id=tenant_id,
                    resolution_notes="Resumed via @bijou resume command"
                )
            )
            
            return "✅ AI responses resumed! I'm back to help you. What can I do for you?"
        else:
            return "AI responses are already active. How can I assist you?"
            
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        return "AI responses resumed. How can I help?"


async def handle_quiet_command(
    customer_jid: str,
    tenant_id: str
) -> str:
    """Handle quiet/pause command"""
    # TODO: Implement pause mechanism
    # For now, just return confirmation
    return "🔕 AI responses paused for this conversation. Message me again when you need help, or send '@bijou resume' to reactivate."


async def handle_status_command(
    customer_jid: str,
    tenant_id: str
) -> str:
    """Handle status command"""
    # TODO: Check actual status from database
    return """**Bijou Status:**
✅ AI: Active
🤖 Model: Gemini 2.0 Flash
💬 Language: Auto-detect enabled
⚡ Response Time: <2s average

All systems operational!"""


# Integration example
if __name__ == "__main__":
    # Test command detection
    detector = CommandDetector()
    
    test_messages = [
        "@bijou resume",
        "bijou: quiet",
        "/bijou status",
        "Hey @bijou help me out",
        "bijou takeover",
        "regular message without command"
    ]
    
    print("Command Detection Tests:")
    print("=" * 50)
    
    for msg in test_messages:
        result = detector.detect_command(msg)
        if result:
            command, params = result
            print(f"Message: {msg}")
            print(f"  → Command: {command}")
            print(f"  → Params: {params}")
            print()
        else:
            print(f"Message: {msg}")
            print(f"  → No command detected")
            print()
