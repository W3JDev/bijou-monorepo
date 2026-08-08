"""
Co-pilot Mode Methods for Bijou AI
===================================

Methods to add to bijou.py for Phase 4 Co-pilot Mode.
Insert these methods BEFORE the process_message method.
"""

import os

def notify_owner(self, message: str, priority: str = "normal"):
    """
    Send notification to owner's personal WhatsApp.
    
    Args:
        message: Notification message
        priority: Priority level ("normal" or "urgent")
    """
    # NEVER hardcode owner JID - always use env var
    OWNER_JID = os.getenv("OWNER_WHATSAPP_JID", "")
    if not OWNER_JID:
        print("[ERROR] OWNER_WHATSAPP_JID not set - cannot notify owner")
        return
    
    if priority == "urgent":
        message = f"🚨 URGENT: {message}"
    elif priority == "info":
        message = f"ℹ️ {message}"
    
    try:
        self.send_message(OWNER_JID, message)
        print(f"[OWNER NOTIFICATION] Sent {priority} notification to owner")
    except Exception as e:
        print(f"[ERROR] Failed to notify owner: {e}")


def handle_command(self, command: Command, chat_jid: str) -> Optional[str]:
    """
    Handle @bijou commands.
    
    Args:
        command: Parsed command object
        chat_jid: Chat identifier
        
    Returns:
        Response message or None
    """
    if command.type == "unknown":
        response = self.command_parser.format_unknown_command_response(
            command.args.get('requested', 'unknown')
        )
        self.send_message(chat_jid, response)
        return None
    
    if command.type == "quiet":
        self.observer_mode[chat_jid] = True
        response = "👁️ Observer Mode activated. I'll monitor the conversation but won't respond unless you call me with `@bijou active`."
        self.send_message(chat_jid, response)
        self.notify_owner(f"Observer Mode activated in chat {chat_jid}", priority="info")
        return None
    
    elif command.type == "active":
        self.observer_mode[chat_jid] = False
        response = "✅ I'm back! Observer Mode deactivated. I'll respond normally now."
        self.send_message(chat_jid, response)
        return None
    
    elif command.type == "summarize":
        message_count = command.args.get('message_count', 10)
        summary = self.analytics.generate_summary(chat_jid, message_count)
        self.send_message(chat_jid, summary)
        return None
    
    elif command.type == "analyze":
        aspect = command.args.get('aspect', 'all')
        sentiment_data = self.analytics.get_sentiment_summary(chat_jid, hours=24)
        
        if sentiment_data.get('message') == 'No recent data':
            response = "No recent conversation data to analyze."
        else:
            response = f"**Sentiment Analysis:**\n"
            response += f"• Dominant emotion: {sentiment_data['dominant_emotion'].title()}\n"
            response += f"• Confidence: {sentiment_data['average_confidence'] * 100:.0f}%\n"
            response += f"• Messages analyzed: {sentiment_data['total_messages']}"
        
        self.send_message(chat_jid, response)
        return None
    
    elif command.type == "help":
        help_text = self.command_parser.get_help_text()
        self.send_message(chat_jid, help_text)
        return None
    
    elif command.type == "status":
        is_observer = self.observer_mode.get(chat_jid, False)
        mode_text = "Observer Mode (Silent)" if is_observer else "Active Mode (Responding)"
        response = f"**Current Status:**\n• Mode: {mode_text}\n• Analytics: Tracking\n• Security: Active"
        self.send_message(chat_jid, response)
        return None
    
    return None
