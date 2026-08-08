#!/usr/bin/env python3
"""
API-based Bijou AI Connector
============================

Uses WhatsApp Bridge REST API instead of direct database access.
This fixes the database connection issues while maintaining full functionality.

Author: W3J Bijou AI
Version: 2.1.0 API Edition
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add w3j-bijou-enterprise/src to path for imports (run from repo root or ops/)
_ops_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_ops_dir) if os.path.basename(_ops_dir) == "ops" else _ops_dir
_w3j_src = os.path.join(_root, "w3j-bijou-enterprise", "src")
sys.path.insert(0, _w3j_src)

# Import TRACE agents
try:
    from agents.asi import AffectiveStateIdentifier
    from agents.cae import CausalAnalysisEngine
    from agents.ers import EmpatheticResponseSynthesizer
    from agents.srp import StrategicResponsePlanner
    from core.memory import ConversationMemory
except ImportError as e:
    print(f"[ERROR] Failed to import TRACE components: {e}")
    print("Make sure you're running from the correct directory with src/ folder")
    sys.exit(1)


class APIBijouAI:
    """API-based Bijou AI that connects via REST API instead of direct DB access"""

    def __init__(self):
        """Initialize API-based Bijou AI"""
        print("🚀 Initializing API-based Bijou AI...")

        # Configuration
        self.bridge_url = os.getenv("BRIDGE_URL", "http://localhost:8080")
        self.whatsapp_owner = os.getenv("WHATSAPP_OWNER", "+60174106981")
        self.polling_interval = int(os.getenv("POLLING_INTERVAL", "2"))
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        # Track processed messages to avoid duplicates
        self.processed_messages = set()
        self.startup_time = datetime.now(timezone.utc)

        print(f"Bridge URL: {self.bridge_url}")
        print(f"WhatsApp Owner: {self.whatsapp_owner}")
        print(f"Polling Interval: {self.polling_interval}s")

        # Initialize TRACE framework
        self.init_trace_framework()

        # Initialize conversation memory
        self.memory = ConversationMemory()

        print("✅ API-based Bijou AI initialized successfully!")

    def init_trace_framework(self):
        """Initialize TRACE AI agents"""
        try:
            print("Initializing TRACE framework...")

            # Initialize agents
            self.asi = AffectiveStateIdentifier(api_key=self.gemini_api_key)
            self.cae = CausalAnalysisEngine(api_key=self.gemini_api_key)
            self.srp = StrategicResponsePlanner(api_key=self.gemini_api_key)
            self.ers = EmpatheticResponseSynthesizer(api_key=self.gemini_api_key)

            print("  [OK] ASI (Affective State Identifier)")
            print("  [OK] CAE (Causal Analysis Engine)")
            print("  [OK] SRP (Strategic Response Planner)")
            print("  [OK] ERS (Empathetic Response Synthesizer)")
            print("✅ TRACE framework initialized successfully!")

        except Exception as e:
            print(f"[ERROR] Failed to initialize TRACE framework: {e}")
            print("[WARN] Falling back to basic responses")
            self.asi = None
            self.cae = None
            self.srp = None
            self.ers = None

    def test_bridge_connection(self) -> bool:
        """Test connection to WhatsApp bridge API"""
        try:
            response = requests.get(
                f"{self.bridge_url}/api/messages", params={"limit": 1}, timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    print("✅ Bridge connection: OK")
                    return True
                else:
                    print(f"❌ Bridge API error: {data}")
                    return False
            else:
                print(f"❌ Bridge connection failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Bridge connection error: {e}")
            return False

    def get_new_messages(self) -> List[Dict[str, Any]]:
        """Fetch new messages from bridge API"""
        try:
            # Get recent messages from the API
            response = requests.get(
                f"{self.bridge_url}/api/messages", params={"limit": 20}, timeout=10
            )

            if response.status_code != 200:
                print(f"[WARN] API request failed: HTTP {response.status_code}")
                return []

            data = response.json()
            if not data.get("success", False):
                print(f"[WARN] API returned error: {data}")
                return []

            messages = data.get("messages", [])
            new_messages = []

            for msg in messages:
                msg_id = msg.get("id")
                timestamp_str = msg.get("timestamp")
                sender = msg.get("sender")
                content = msg.get("content", "").strip()
                is_from_me = msg.get("is_from_me", False)

                # Skip if already processed
                if msg_id in self.processed_messages:
                    continue

                # Skip messages from me (bot responses)
                if is_from_me:
                    self.processed_messages.add(msg_id)
                    continue

                # Skip empty messages
                if not content:
                    self.processed_messages.add(msg_id)
                    continue

                # Parse timestamp
                try:
                    msg_time = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                except:
                    print(f"[WARN] Invalid timestamp format: {timestamp_str}")
                    self.processed_messages.add(msg_id)
                    continue

                # Skip messages older than startup time
                if msg_time < self.startup_time:
                    self.processed_messages.add(msg_id)
                    continue

                # This is a new message to process
                new_messages.append(
                    {
                        "id": msg_id,
                        "sender": sender,
                        "content": content,
                        "timestamp": msg_time,
                        "chat_jid": msg.get("chat_jid"),
                    }
                )

                self.processed_messages.add(msg_id)

            return new_messages

        except Exception as e:
            print(f"[ERROR] Failed to fetch messages: {e}")
            return []

    def process_message(self, message_content: str, sender: str) -> str:
        """Process message using TRACE framework"""
        try:
            print(f"\n🧠 Processing message from {sender}")
            print(f"Message: {message_content[:100]}...")

            # If TRACE is not available, use fallback
            if not self.asi:
                return self.fallback_response(message_content, sender)

            # TRACE Pipeline
            # 1. ASI - Detect emotional state
            emotion_data = self.asi.identify_emotion(message_content, sender)
            emotion = emotion_data.get("emotion", "neutral")
            confidence = emotion_data.get("confidence", 0.5)

            print(f"  Emotion: {emotion} ({confidence:.1%})")

            # 2. CAE - Analyze root causes
            analysis = self.cae.analyze_causes(message_content, sender, emotion)

            # 3. SRP - Plan response strategy
            strategy = self.srp.plan_response(
                message_content, sender, emotion, analysis
            )

            # 4. ERS - Generate empathetic response
            response = self.ers.synthesize_response(
                message_content, sender, emotion, analysis, strategy
            )

            # Store in memory
            self.memory.add_interaction(sender, message_content, response)

            return response

        except Exception as e:
            print(f"[ERROR] Failed to process message: {e}")
            return self.fallback_response(message_content, sender)

    def fallback_response(self, message_content: str, sender: str) -> str:
        """Fallback response when TRACE framework is not available"""

        # Language detection
        message_lower = message_content.lower()

        if any(
            word in message_lower for word in ["malay", "bahasa", "malaysia", "melayu"]
        ):
            return "Hai! Terima kasih atas mesej anda. Saya Bijou, pembantu AI untuk W3J Consulting. Bagaimana saya boleh membantu anda hari ini? 😊"

        elif any(
            word in message_lower
            for word in ["apa khabar", "selamat", "assalamualaikum"]
        ):
            return "Apa khabar! 👋 Saya Bijou, pembantu AI dari W3J Consulting. Ada apa yang boleh saya bantu hari ini?"

        elif "escalate" in message_lower or "human" in message_lower:
            return "I understand you'd like to speak with a human. Let me connect you with our team right away. Someone will be with you shortly! 🙋‍♂️"

        else:
            return "Hi there! I'm Bijou, your AI assistant from W3J Consulting 😊 How can I help you today? (Boleh juga dalam Bahasa Malaysia!)"

    def send_response(self, chat_jid: str, response: str) -> bool:
        """Send response via bridge API"""
        try:
            payload = {"recipient": chat_jid, "message": response}

            response_req = requests.post(
                f"{self.bridge_url}/api/send", json=payload, timeout=10
            )

            if response_req.status_code == 200:
                result = response_req.json()
                if result.get("success", False):
                    print(f"✅ Response sent to {chat_jid}")
                    return True
                else:
                    print(f"❌ Send failed: {result}")
                    return False
            else:
                print(f"❌ Send request failed: HTTP {response_req.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error sending response: {e}")
            return False

    def run_polling_loop(self):
        """Main polling loop"""
        print(f"\n🔄 Starting message polling loop...")
        print(f"Polling interval: {self.polling_interval}s")
        print(f"Startup time filter: {self.startup_time}")
        print("Press Ctrl+C to stop\n")

        # Test connection first
        if not self.test_bridge_connection():
            print(
                "❌ Cannot connect to bridge API. Please check the bridge is running."
            )
            return

        poll_count = 0

        try:
            while True:
                poll_count += 1

                # Get new messages
                new_messages = self.get_new_messages()

                if new_messages:
                    print(
                        f"[POLL #{poll_count}] Found {len(new_messages)} new message(s)"
                    )

                    for msg in new_messages:
                        sender = msg["sender"]
                        content = msg["content"]
                        chat_jid = msg["chat_jid"]

                        print(f"\n📨 NEW MESSAGE from {sender}")
                        print(f"Content: {content}")
                        print("=" * 60)

                        # Process message
                        response = self.process_message(content, sender)

                        print(f"\n🤖 RESPONSE:")
                        print(f"{response}")
                        print("=" * 60)

                        # Send response
                        success = self.send_response(chat_jid, response)

                        if success:
                            print(f"✅ Successfully responded to {sender}")
                        else:
                            print(f"❌ Failed to send response to {sender}")

                        print()

                else:
                    print(f"[POLL #{poll_count}] No new messages")

                # Wait before next poll
                time.sleep(self.polling_interval)

        except KeyboardInterrupt:
            print(f"\n🛑 Polling stopped by user")
        except Exception as e:
            print(f"\n❌ Polling error: {e}")
            print("Restarting in 5 seconds...")
            time.sleep(5)
            self.run_polling_loop()  # Restart on error


def main():
    """Main entry point"""
    print("🌟 W3J Bijou AI - API Edition")
    print("=" * 50)

    # Initialize API-based Bijou AI
    bijou = APIBijouAI()

    # Run polling loop
    bijou.run_polling_loop()


if __name__ == "__main__":
    main()
