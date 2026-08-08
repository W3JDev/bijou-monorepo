
import sqlite3
import os
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from core.bijou import BijouAI
from agents.ers import EmpatheticResponseSynthesizer
from unittest.mock import patch

DB_PATH = "test_bridge.db"

def setup_test_db():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            chat_jid TEXT,
            sender TEXT,
            content TEXT,
            timestamp TEXT,
            is_from_me INTEGER
        )
    """)
    conn.commit()
    conn.close()
    print(f"[SETUP] Created test DB: {DB_PATH}")

def insert_owner_message(chat_jid, seconds_ago=10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create timestamp - User Activity Detection uses datetime.now(timezone.utc) comparison
    # Messages in DB are expected to be roughly ISO encoded.
    # Bijou logic: datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    ts = datetime.utcnow().isoformat() + "Z"
    
    cursor.execute("""
        INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (f"msg_{time.time()}", chat_jid, "me", "I am active", ts, 1))
    
    conn.commit()
    conn.close()
    print(f"[SETUP] Inserted OWNER message for {chat_jid} (active)")

@patch('core.bijou.get_knowledge_loader')
@patch('core.bijou.SHEETS_AVAILABLE', False)
@patch('core.bijou.PRODUCTION_FEATURES', False)
def test_activity_detection(mock_loader):
    print("\n=== TEST 1: User Activity Detection ===")
    setup_test_db()
    
    # Mock knowledge loader to return None or dummy
    mock_loader.return_value = MagicMock()
    mock_loader.return_value.load_system_prompt.return_value = "System Prompt"
    
    # Initialize Bijou (mocking API keys to avoid errors)
    # We also need to mock TRACE agents or they might try to hit API
    with patch('core.bijou.AffectiveStateIdentifier'), \
         patch('core.bijou.CausalAnalysisEngine'), \
         patch('core.bijou.StrategicResponsePlanner'), \
         patch('core.bijou.EmpatheticResponseSynthesizer'):
         
        bijou = BijouAI(
            gemini_api_key="fake_key",
            bridge_db_path=DB_PATH,
            enable_health_check=False
        )
        
        # 1. Test Inactive (No owner messages)
        print("Testing INACTIVE user...")
        # Clean DB first just in case
        setup_test_db() 
        
        is_active = bijou.check_if_user_active("12345@s.whatsapp.net")
        if not is_active:
            print("PASS: Correctly identified inactive user.")
        else:
            print("FAIL: False positive on inactive user.")

        # 2. Test Active (Owner message just sent)
        insert_owner_message("12345@s.whatsapp.net")
        print("Testing ACTIVE user...")
        is_active = bijou.check_if_user_active("12345@s.whatsapp.net")
        if is_active:
            print("PASS: Correctly identified active user.")
        else:
            print("FAIL: Failed to detect active user.")

def test_time_context():
    print("\n=== TEST 2: Time Context Injection ===")
    
    # We want to verify that ers.py injects the CURRENT TIME into the prompt.
    # Since we can't see the internal prompt variable, we will mock the model.generate_content
    # and inspect the argument passed to it.
    
    os.environ["GEMINI_API_KEY"] = "fake_key"
    ers = EmpatheticResponseSynthesizer(api_key="fake_key")
    
    # Mock the generative model
    ers.model = MagicMock()
    ers.model.generate_content.return_value.text = "Mock response"
    
    # Call synthesize
    ers.synthesize_response(
        message="Hello",
        emotion="joy",
        emotion_confidence=0.9,
        emotional_cues=[],
        global_cause="greeting",
        unmet_need="none",
        urgency_level="low",
        strategy="mirroring",
        behavioral_taxonomy=["mirroring"],
        response_guidance=[],
        knowledge_retrieved={},
        conversation_history=[]
    )
    
    # Inspect the call
    args, _ = ers.model.generate_content.call_args
    prompt_sent = args[0]
    
    print("Checking prompt for time context...")
    if "CURRENT TIME:" in prompt_sent:
        print("PASS: Found 'CURRENT TIME:' in prompt.")
        # Extract the time to verify format
        import re
        match = re.search(r"CURRENT TIME: (.*)", prompt_sent)
        if match:
            print(f"PASS: Injected Time: {match.group(1)}")
    else:
        print("FAIL: 'CURRENT TIME:' missing from prompt.")
        print("First 500 chars of prompt:")
        print(prompt_sent[:500])

if __name__ == "__main__":
    try:
        test_activity_detection()
        test_time_context()
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
