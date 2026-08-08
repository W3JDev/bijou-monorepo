"""
Bijou AI - Conversation Analytics
==================================

Tracks conversation metrics for Observer Mode and reporting.

Features:
- Sentiment tracking
- Intent detection
- Conversation summaries
- Daily/weekly reports

Author: W3J Bijou AI
Version: 2.2.0
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json


class ConversationAnalytics:
    """
    Tracks and analyzes conversations for insights and reporting.
    """
    
    def __init__(self):
        # Per-chat analytics
        self.sentiment_history: Dict[str, List[Dict]] = defaultdict(list)
        self.intent_history: Dict[str, List[Dict]] = defaultdict(list)
        self.message_count: Dict[str, int] = defaultdict(int)
        
    def track_sentiment(self, chat_jid: str, emotion: str, confidence: float, timestamp: Optional[datetime] = None):
        """
        Track sentiment for a message.
        
        Args:
            chat_jid: Chat identifier
            emotion: Detected emotion
            confidence: Confidence score (0-1)
            timestamp: Message timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.sentiment_history[chat_jid].append({
            'emotion': emotion,
            'confidence': confidence,
            'timestamp': timestamp.isoformat()
        })
        
        # Keep only last 100 entries per chat
        if len(self.sentiment_history[chat_jid]) > 100:
            self.sentiment_history[chat_jid] = self.sentiment_history[chat_jid][-100:]
    
    def track_intent(self, chat_jid: str, intent: str, timestamp: Optional[datetime] = None):
        """
        Track detected intent.
        
        Args:
            chat_jid: Chat identifier
            intent: Detected intent
            timestamp: Message timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.intent_history[chat_jid].append({
            'intent': intent,
            'timestamp': timestamp.isoformat()
        })
        
        self.message_count[chat_jid] += 1
    
    def get_sentiment_summary(self, chat_jid: str, hours: int = 24) -> Dict:
        """
        Get sentiment summary for recent messages.
        
        Args:
            chat_jid: Chat identifier
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with sentiment statistics
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            s for s in self.sentiment_history.get(chat_jid, [])
            if datetime.fromisoformat(s['timestamp']) > cutoff
        ]
        
        if not recent:
            return {'message': 'No recent data'}
        
        # Calculate statistics
        emotions = [s['emotion'] for s in recent]
        emotion_counts = defaultdict(int)
        for emotion in emotions:
            emotion_counts[emotion] += 1
        
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        avg_confidence = sum(s['confidence'] for s in recent) / len(recent)
        
        return {
            'total_messages': len(recent),
            'dominant_emotion': dominant_emotion,
            'emotion_distribution': dict(emotion_counts),
            'average_confidence': round(avg_confidence, 2),
            'time_period': f'Last {hours} hours'
        }
    
    def generate_summary(self, chat_jid: str, message_count: int = 10) -> str:
        """
        Generate conversation summary.
        
        Args:
            chat_jid: Chat identifier
            message_count: Number of recent messages to summarize
            
        Returns:
            Formatted summary text
        """
        sentiment_data = self.get_sentiment_summary(chat_jid, hours=24)
        
        if sentiment_data.get('message') == 'No recent data':
            return "No recent conversation data available for this chat."
        
        summary_lines = [
            f"**Conversation Summary** (Last {message_count} messages)",
            f"",
            f"📊 **Sentiment Analysis:**",
            f"• Dominant emotion: {sentiment_data['dominant_emotion'].title()}",
            f"• Confidence: {sentiment_data['average_confidence'] * 100:.0f}%",
            f"• Total messages analyzed: {sentiment_data['total_messages']}",
            f"",
            f"**Emotion Breakdown:**"
        ]
        
        for emotion, count in sentiment_data['emotion_distribution'].items():
            percentage = (count / sentiment_data['total_messages']) * 100
            summary_lines.append(f"• {emotion.title()}: {percentage:.0f}% ({count} messages)")
        
        return "\n".join(summary_lines)
    
    def get_daily_report(self) -> str:
        """
        Generate daily analytics report across all chats.
        
        Returns:
            Formatted daily report
        """
        total_chats = len(self.message_count)
        total_messages = sum(self.message_count.values())
        
        # Aggregate sentiment across all chats
        all_sentiments = []
        for chat_sentiments in self.sentiment_history.values():
            cutoff = datetime.now() - timedelta(hours=24)
            recent = [
                s for s in chat_sentiments
                if datetime.fromisoformat(s['timestamp']) > cutoff
            ]
            all_sentiments.extend(recent)
        
        if not all_sentiments:
            return "No activity in the last 24 hours."
        
        # Calculate overall sentiment
        emotions = [s['emotion'] for s in all_sentiments]
        emotion_counts = defaultdict(int)
        for emotion in emotions:
            emotion_counts[emotion] += 1
        
        positive_emotions = ['happy', 'excited', 'grateful', 'satisfied']
        positive_count = sum(emotion_counts.get(e, 0) for e in positive_emotions)
        positive_percentage = (positive_count / len(emotions)) * 100 if emotions else 0
        
        report_lines = [
            "📈 **Daily Analytics Report**",
            f"",
            f"**Activity:**",
            f"• Total chats: {total_chats}",
            f"• Total messages: {total_messages}",
            f"",
            f"**Sentiment Overview:**",
            f"• Positive sentiment: {positive_percentage:.0f}%",
            f"• Most common emotion: {max(emotion_counts.items(), key=lambda x: x[1])[0].title()}",
        ]
        
        return "\n".join(report_lines)
