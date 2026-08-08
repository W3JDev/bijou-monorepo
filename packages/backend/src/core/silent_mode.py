"""
Silent Observe Mode for Bijou AI
=================================

Enables professional, non-intrusive AI behavior:
- Observes conversations without unnecessary responses
- Only speaks when valuable or necessary
- Asks owner permission for proactive actions

Commands:
- /quiet - Enable silent observe mode
- /active - Return to normal mode
- /status - Check current mode

Author: W3J Bijou AI
Version: 1.0.0
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SilentObserveMode:
    """
    Manages Bijou's silent observe mode behavior.
    
    In silent mode:
    - No HEARTBEAT_OK spam
    - Only responds when directly addressed or high-value opportunity
    - Asks owner permission before proactive sends
    """
    
    def __init__(self, state_file: str = "silent_mode_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
        
    def _load_state(self) -> Dict:
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load silent mode state: {e}")
        
        return {
            "enabled": False,
            "last_updated": None,
            "owner_notifications_enabled": True
        }
    
    def _save_state(self):
        """Save state to disk"""
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save silent mode state: {e}")
    
    def enable(self) -> str:
        """Enable silent observe mode"""
        self.state["enabled"] = True
        self._save_state()
        logger.info("🤫 Silent observe mode ENABLED")
        return "🤫 Silent observe mode enabled. I'll only speak when necessary or asked."
    
    def disable(self) -> str:
        """Disable silent observe mode (return to normal)"""
        self.state["enabled"] = False
        self._save_state()
        logger.info("🗣️ Silent observe mode DISABLED (normal mode)")
        return "🗣️ Back to normal mode! I'll respond actively again."
    
    def is_enabled(self) -> bool:
        """Check if silent mode is currently enabled"""
        return self.state.get("enabled", False)
    
    def should_respond(
        self, 
        message: str, 
        sender: str,
        chat_type: str = "direct",  # direct, group, broadcast
        is_command: bool = False
    ) -> bool:
        """
        Determine if Bijou should respond to a message.
        
        Args:
            message: Message content
            sender: Sender identifier
            chat_type: Type of chat (direct/group/broadcast)
            is_command: Whether message is a command
        
        Returns:
            True if should respond, False if should stay silent
        """
        # Always respond to commands
        if is_command:
            return True
        
        # If not in silent mode, always respond
        if not self.is_enabled():
            return True
        
        # === SILENT MODE LOGIC ===
        
        # 1. Direct mentions (name or @bijou)
        mentions = ["bijou", "@bijou", "ai", "assistant", "hey bijou", "hello bijou"]
        message_lower = message.lower()
        if any(mention in message_lower for mention in mentions):
            logger.info(f"🎯 Responding: Direct mention detected")
            return True
        
        # 2. Questions (clear interrogatives)
        question_indicators = ["?", "how", "what", "when", "where", "why", "can you", "could you", "would you"]
        if any(indicator in message_lower for indicator in question_indicators):
            logger.info(f"🎯 Responding: Question detected")
            return True
        
        # 3. Direct chat (1-on-1 conversation)
        # NOTE: For now, we DON'T auto-respond to direct chats in silent mode
        # This prevents spam. User must mention Bijou or ask a question.
        # if chat_type == "direct":
        #     logger.info(f"🎯 Responding: Direct chat")
        #     return True
        
        # 4. Urgent keywords (problems, errors, help requests)
        urgent_keywords = ["help", "error", "problem", "urgent", "issue", "broken", "not working"]
        if any(keyword in message_lower for keyword in urgent_keywords):
            logger.info(f"🎯 Responding: Urgent keyword detected")
            return True
        
        # Otherwise, stay silent and observe
        logger.info(f"🤫 Staying silent: Observing in quiet mode")
        return False
    
    def get_status(self) -> str:
        """Get current mode status"""
        if self.is_enabled():
            return "🤫 Silent observe mode: **ENABLED**\n\nI'm quietly observing. I'll only speak when:\n- Directly mentioned\n- Asked a question\n- In direct chat\n- Urgent issue detected\n\nUse `/active` to return to normal mode."
        else:
            return "🗣️ Normal mode: **ACTIVE**\n\nI'm responding actively to all messages.\n\nUse `/quiet` to enable silent observe mode."


# Global instance
_silent_mode_instance: Optional[SilentObserveMode] = None


def get_silent_mode() -> SilentObserveMode:
    """Get or create global silent mode instance"""
    global _silent_mode_instance
    if _silent_mode_instance is None:
        _silent_mode_instance = SilentObserveMode()
    return _silent_mode_instance
