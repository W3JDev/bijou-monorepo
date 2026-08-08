# AGENT.MD - Bijou AI Tools Documentation

## =============================================================================
## Last Updated: 2026-01-28
## Purpose: Complete guide for all AI tools in Bijou
## Location: packages/bijou-core/bijou_core/tools/
## =============================================================================

## 🎯 WHAT ARE THESE TOOLS?

The tools in this directory are **AI-powered capabilities** that Bijou can use to:
1. Analyze images (Gemini Vision)
2. Transcribe audio (OpenAI Whisper)
3. Manage emails (Gmail API)
4. Handle calendar events (Google Calendar API)
5. Create WhatsApp events (Bridge integration)

```
┌──────────────┐
│  User Input  │
│ (text/media) │
└──────┬───────┘
       │
       ↓
┌────────────────┐      ┌─────────────────┐
│ ToolOrchestrator│ ───→ │  ImageTool      │ → Gemini 2.5 Flash
│                │      │  AudioTool      │ → OpenAI Whisper
│  (Router)      │      │  CalendarTool   │ → Google Calendar
│                │      │  GmailTool      │ → Gmail API
│                │      │  EventTool      │ → WhatsApp Events
└────────────────┘      └─────────────────┘
```

---

## 📁 DIRECTORY STRUCTURE

```
tools/
├── AGENT.md                  # THIS FILE
├── __init__.py               # Package exports
├── image_tool.py             # Gemini Vision (400+ lines)
├── audio_tool.py             # Whisper + TTS (430+ lines)
├── gmail_tool.py             # Email management (360+ lines)
├── calendar_tool.py          # Calendar operations (380+ lines)
└── whatsapp_event_tool.py    # In-chat events (240+ lines)
```

---

## 🚨 CRITICAL LESSONS LEARNED (2026-01-28)

### ❌ WRONG APPROACH #1: Using Gemini 1.5 in ImageTool

**Problem:**
```python
# OLD (image_tool.py line 36):
self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
```

**Why This Was Wrong:**
- Main Bijou uses Gemini 2.5 Flash
- ImageTool used 1.5 Flash
- Inconsistent model versions
- 1.5 is older, less capable

**Fix Applied:**
```python
# NEW (image_tool.py line 36):
self.gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
```

**Lesson:** **ALWAYS use Gemini 2.5 Flash** across all components!

---

### ❌ WRONG APPROACH #2: Hardcoding API Keys

**Problem:**
Some tools had API keys hardcoded or required specific env var names.

**Correct Pattern:**
```python
def __init__(self, api_key: Optional[str] = None):
    # Try parameter first, then environment variable
    self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not self.api_key:
        logger.warning("⚠️ API key not set - tool disabled")
        self._initialized = False
```

**Lesson:** Always support multiple API key sources with fallbacks!

---

### ❌ WRONG APPROACH #3: Not Handling API Errors Gracefully

**Problem:**
Tools crashed or returned cryptic errors when API calls failed.

**Correct Pattern:**
```python
try:
    response = httpx.post(url, json=payload, timeout=60.0)
    response.raise_for_status()
    return {"success": True, "data": response.json()}
except httpx.HTTPStatusError as e:
    logger.error(f"API error {e.response.status_code}: {e.response.text}")
    return {
        "success": False,
        "error": f"API error {e.response.status_code}: {e.response.text}"
    }
except httpx.TimeoutException:
    return {"success": False, "error": "Request timed out"}
except Exception as e:
    return {"success": False, "error": str(e)}
```

**Lesson:** Always return structured error responses with success flags!

---

## 🛠️ TOOL REFERENCE

### 1. ImageTool (image_tool.py)

**Purpose:** Analyze images using Gemini Vision API

**Model:** Gemini 2.5 Flash ✅

**API Key:** `GOOGLE_AI_API_KEY` or `GEMINI_API_KEY`

**Key Methods:**

```python
analyze_image(image_path, prompt=None, detail_level="medium")
  → Returns detailed image description
  → Default prompt: "Describe this image in detail..."
  → detail_level: "low", "medium", "high"

extract_text(image_path)
  → OCR - Extract all text from image
  → Preserves formatting

identify_objects(image_path)
  → List all objects visible in image
  → Returns object names + locations

answer_question(image_path, question)
  → Answer specific questions about image
  → Example: "How many people are in this photo?"

analyze_document(image_path)
  → Analyze invoices, receipts, forms
  → Extracts key information
```

**Example Usage:**
```python
from bijou_core.tools import ImageTool

tool = ImageTool()
result = tool.analyze_image("photo.jpg", "What's in this image?")

if result["success"]:
    print(result["description"])
else:
    print(f"Error: {result['error']}")
```

**Response Format:**
```python
{
    "success": True,
    "description": "The image shows...",
    "prompt": "What's in this image?",
    "detail_level": "medium"
}
```

**Common Issues:**

1. **"API key not valid"**
   - Check GEMINI_API_KEY is set correctly
   - Verify key has Gemini API access enabled

2. **"File too large"**
   - Gemini Vision has size limits (~20MB)
   - Resize image before sending

3. **"Invalid image format"**
   - Supported: JPEG, PNG, WebP, GIF
   - Convert to supported format first

---

### 2. AudioTool (audio_tool.py)

**Purpose:** Transcribe audio and generate speech

**APIs:**
- OpenAI Whisper (transcription)
- Google Text-to-Speech (optional)

**API Key:** `OPENAI_API_KEY`

**Key Methods:**

```python
transcribe(audio_path)
  → Transcribe audio to text
  → Supports: MP3, WAV, OGG, WebM, M4A
  → Returns full transcript

transcribe_with_timestamps(audio_path)
  → Transcribe with word-level timestamps
  → Useful for subtitles/captions

detect_language(audio_path)
  → Auto-detect spoken language
  → Returns language code + confidence

generate_speech(text, language="en")
  → Text-to-speech (Google TTS)
  → Returns audio file path
```

**Example Usage:**
```python
from bijou_core.tools import AudioTool

tool = AudioTool()
result = tool.transcribe("voice_note.ogg")

if result["success"]:
    print(f"Transcript: {result['text']}")
    print(f"Language: {result['language']}")
else:
    print(f"Error: {result['error']}")
```

**Response Format:**
```python
{
    "success": True,
    "text": "Hello, this is a test recording...",
    "language": "en",
    "duration": 15.3,
    "file_path": "/tmp/voice_note.ogg"
}
```

**Supported Audio Formats:**
- MP3 (most common)
- WAV (uncompressed)
- OGG (WhatsApp voice notes)
- WebM (web audio)
- M4A (Apple audio)

**Common Issues:**

1. **"Audio file too large"**
   - Whisper limit: 25MB
   - Split long audio or compress

2. **"Invalid audio format"**
   - Convert to supported format first
   - Use ffmpeg for conversion

3. **"Poor transcription quality"**
   - Check audio quality (background noise)
   - Ensure clear speech

---

### 3. CalendarTool (calendar_tool.py)

**Purpose:** Manage Google Calendar events

**API:** Google Calendar API v3

**Authentication:** OAuth2 (requires credentials.json)

**Key Methods:**

```python
create_event(title, start_time, end_time, description=None, attendees=None)
  → Create calendar event
  → Returns event ID

get_upcoming_events(max_results=10)
  → Get next N events
  → Returns list of events

update_event(event_id, title=None, start_time=None, ...)
  → Update existing event
  → Only updates provided fields

delete_event(event_id)
  → Delete calendar event
  → Returns success status

check_availability(start_time, end_time)
  → Check if time slot is free
  → Returns True/False + conflicting events
```

**Example Usage:**
```python
from bijou_core.tools import CalendarTool
from datetime import datetime, timedelta

tool = CalendarTool(credentials_path="credentials.json")

# Create event
start = datetime.now() + timedelta(hours=2)
end = start + timedelta(hours=1)

result = tool.create_event(
    title="Team Meeting",
    start_time=start,
    end_time=end,
    description="Weekly sync",
    attendees=["colleague@example.com"]
)

if result["success"]:
    print(f"Event created: {result['event_id']}")
```

**OAuth2 Setup:**

1. Create project in Google Cloud Console
2. Enable Calendar API
3. Create OAuth2 credentials (Desktop app)
4. Download credentials.json
5. First run will open browser for authorization
6. Token saved for future use

**Common Issues:**

1. **"OAuth2 not authorized"**
   - Delete token.json and reauthorize
   - Check credentials.json is valid

2. **"Invalid time format"**
   - Use datetime objects, not strings
   - Ensure timezone awareness

3. **"Event not found"**
   - Verify event_id is correct
   - Check calendar permissions

---

### 4. GmailTool (gmail_tool.py)

**Purpose:** Send and manage emails

**API:** Gmail API v1

**Authentication:** OAuth2 (same credentials as Calendar)

**Key Methods:**

```python
send_email(to, subject, body, cc=None, bcc=None, attachments=None)
  → Send email
  → Supports HTML body
  → Returns message ID

read_emails(max_results=10, query=None)
  → Read recent emails
  → Supports Gmail query syntax
  → Returns list of emails

search_emails(query)
  → Search emails with Gmail syntax
  → Example: "from:boss@company.com subject:urgent"

get_email(message_id)
  → Get full email by ID
  → Returns headers + body

delete_email(message_id)
  → Move email to trash
  → Returns success status
```

**Example Usage:**
```python
from bijou_core.tools import GmailTool

tool = GmailTool(credentials_path="credentials.json")

# Send email
result = tool.send_email(
    to="colleague@example.com",
    subject="Meeting Notes",
    body="<h1>Today's Discussion</h1><p>Here are the notes...</p>",
    cc=["manager@example.com"]
)

if result["success"]:
    print(f"Email sent: {result['message_id']}")

# Search emails
results = tool.search_emails("from:boss@company.com is:unread")
for email in results.get("emails", []):
    print(f"Subject: {email['subject']}")
```

**Gmail Query Syntax:**
```
from:user@example.com      - From specific sender
to:user@example.com        - To specific recipient
subject:meeting            - Subject contains "meeting"
is:unread                  - Unread emails
is:starred                 - Starred emails
has:attachment             - Has attachments
after:2024/01/01          - After date
before:2024/12/31         - Before date
```

**Common Issues:**

1. **"Insufficient permissions"**
   - Reauthorize with full Gmail scope
   - Check API is enabled in Google Cloud

2. **"Message not sent"**
   - Verify recipient email format
   - Check Gmail sending limits (500/day)

3. **"Attachment too large"**
   - Gmail limit: 25MB per email
   - Use cloud storage links instead

---

### 5. WhatsAppEventTool (whatsapp_event_tool.py)

**Purpose:** Create events directly in WhatsApp chats

**Integration:** WhatsApp Bridge + Optional Google Calendar

**No OAuth Required:** Uses bridge API

**Key Methods:**

```python
create_event(chat_jid, title, date, time, description=None)
  → Create in-chat event
  → Returns event message ID

send_event_invitation(chat_jid, event_details)
  → Send formatted event invitation
  → Includes calendar integration option

format_event_message(title, date, time, description)
  → Format event as WhatsApp message
  → Returns formatted string
```

**Example Usage:**
```python
from bijou_core.tools import WhatsAppEventTool

# Production bridge
tool = WhatsAppEventTool(bridge_url="https://bijou-bridge-production-v2.fly.dev")

# Staging bridge
# tool = WhatsAppEventTool(bridge_url="https://bijou-bridge-staging-v2.fly.dev")

result = tool.create_event(
    chat_jid="60123456789@s.whatsapp.net",
    title="Team Lunch",
    date="2026-01-30",
    time="12:00",
    description="Monthly team gathering"
)

if result["success"]:
    print(f"Event created in chat")
```

**Event Message Format:**
```
📅 Team Lunch

📆 Date: January 30, 2026
⏰ Time: 12:00 PM
📝 Monthly team gathering

React with ✅ to confirm attendance!
```

---

## 🔧 TOOL ORCHESTRATOR INTEGRATION

All tools are managed by `ToolOrchestrator` in `tool_orchestrator.py`.

### How Tools Are Enabled:

```python
# Environment variables control which tools load
ENABLE_IMAGE_TOOL=true        # Loads ImageTool
ENABLE_AUDIO_TOOL=true        # Loads AudioTool
ENABLE_CALENDAR_TOOL=true     # Loads CalendarTool
ENABLE_GMAIL_TOOL=true        # Loads GmailTool
ENABLE_WHATSAPP_EVENT_TOOL=true  # Loads WhatsAppEventTool
```

### Initialization Pattern:

```python
class ToolOrchestrator:
    def _initialize_tools(self):
        # Image Tool
        if self.image_enabled:
            api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                self.image_tool = ImageTool(api_key=api_key)
                logger.info("✅ Image tool initialized")

        # Audio Tool
        if self.audio_enabled:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.audio_tool = AudioTool(openai_api_key=api_key)
                logger.info("✅ Audio tool initialized")

        # ... similar for other tools
```

### Automatic Media Routing:

```python
def process_media(self, file_path: str, media_type: str):
    if media_type == "image" and self.image_tool:
        return self._process_image(file_path)
    elif media_type == "audio" and self.audio_tool:
        return self._process_audio(file_path)
    elif media_type == "video" and self.image_tool:
        return self._process_video(file_path)  # Extract frame → analyze
    else:
        return {"success": False, "error": "Unsupported media type"}
```

---

## 📊 STANDARD RESPONSE FORMAT

All tools follow this response format:

### Success Response:
```python
{
    "success": True,
    "data": <result_data>,
    "metadata": {
        "timestamp": "2026-01-28T10:00:00Z",
        "tool": "ImageTool",
        "operation": "analyze_image"
    }
}
```

### Error Response:
```python
{
    "success": False,
    "error": "Error description here",
    "error_code": "API_ERROR",  # Optional
    "metadata": {
        "timestamp": "2026-01-28T10:00:00Z",
        "tool": "ImageTool",
        "operation": "analyze_image"
    }
}
```

---

## 🧪 TESTING TOOLS

### Unit Tests:

```bash
cd packages/bijou-core
pytest tests/test_image_tool.py
pytest tests/test_audio_tool.py
pytest tests/test_tool_orchestrator.py
```

### Manual Testing:

```python
# Test ImageTool
from bijou_core.tools import ImageTool
tool = ImageTool()
result = tool.analyze_image("test_image.jpg")
print(result)

# Test AudioTool
from bijou_core.tools import AudioTool
tool = AudioTool()
result = tool.transcribe("test_audio.ogg")
print(result)
```

---

## 🔐 SECURITY BEST PRACTICES

1. **Never commit API keys** - Use environment variables
2. **Validate inputs** - Check file types, sizes before processing
3. **Sanitize outputs** - Clean extracted text, remove PII if needed
4. **Rate limiting** - Respect API quotas (Gemini: 60 req/min)
5. **Timeout all API calls** - Default 60s, adjust as needed
6. **Clean temp files** - Delete after processing (security + storage)

---

## 🚀 PERFORMANCE OPTIMIZATION

### Image Processing:
- Resize large images before sending to Gemini
- Use appropriate detail_level (low/medium/high)
- Cache results for identical images

### Audio Processing:
- Compress audio files when possible
- Use appropriate sample rate (16kHz sufficient for speech)
- Consider batch processing for multiple files

### API Calls:
- Implement exponential backoff for retries
- Use connection pooling (httpx Client)
- Monitor rate limits and quota usage

---

## 🐛 DEBUGGING TOOLS

### Enable Debug Logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all tool operations will log details
```

### Check Tool Initialization:

```bash
# Look for these in logs:
✅ Image tool initialized
✅ Audio tool initialized
✅ Calendar tool initialized
✅ Gmail tool initialized
✅ WhatsApp event tool initialized
```

### Test Individual Tools:

```python
# Test if tool is properly initialized
tool = ImageTool()
print(f"Initialized: {tool._initialized}")
print(f"API Key set: {bool(tool.api_key)}")
print(f"Endpoint: {tool.gemini_endpoint}")
```

---

## 📚 API REFERENCE LINKS

- **Gemini API:** https://ai.google.dev/docs
- **OpenAI Whisper:** https://platform.openai.com/docs/guides/speech-to-text
- **Google Calendar API:** https://developers.google.com/calendar/api
- **Gmail API:** https://developers.google.com/gmail/api
- **httpx Documentation:** https://www.python-httpx.org/

---

## ✅ DEPLOYMENT CHECKLIST

Before deploying tool changes:

- [ ] Updated tool uses Gemini 2.5 Flash (not 1.5)
- [ ] API key fallback logic implemented
- [ ] Error handling returns structured responses
- [ ] Logging statements added for debugging
- [ ] Unit tests pass
- [ ] Environment variables documented
- [ ] No hardcoded credentials
- [ ] Timeout values are reasonable
- [ ] Temp files are cleaned up
- [ ] AGENT.md updated if behavior changed

---

## 🔄 CHANGELOG

### 2026-01-28 - Gemini 2.5 Upgrade
- ✅ Updated ImageTool to use Gemini 2.5 Flash
- ✅ Added API key fallback (GOOGLE_AI_API_KEY → GEMINI_API_KEY)
- ✅ Standardized error response format
- ✅ Improved logging and debugging
- ✅ Created comprehensive documentation

### Previous
- See git history for older changes

---

## 💡 ADDING NEW TOOLS

When adding a new tool to this directory:

1. **Create tool file:** `new_tool.py`
2. **Follow standard pattern:**
   ```python
   class NewTool:
       def __init__(self, api_key: Optional[str] = None):
           self.api_key = api_key or os.getenv("NEW_TOOL_API_KEY")
           self._initialized = bool(self.api_key)

       def execute_action(self, params):
           if not self._initialized:
               return {"success": False, "error": "API key not configured"}

           try:
               # Tool logic here
               return {"success": True, "data": result}
           except Exception as e:
               return {"success": False, "error": str(e)}
   ```

3. **Add to `__init__.py`:**
   ```python
   from .new_tool import NewTool
   __all__ = [..., "NewTool"]
   ```

4. **Add to ToolOrchestrator:**
   - Add enable flag check
   - Add initialization logic
   - Add routing logic if needed

5. **Update documentation:**
   - This AGENT.md file
   - Main package AGENT.md
   - README files

6. **Add tests:**
   - Create `tests/test_new_tool.py`
   - Test initialization, success, and error cases

7. **Update environment variables:**
   - Document required env vars
   - Update fly.toml configs

---

**Last Updated:** 2026-01-28
**Next Review:** When adding new tools or major refactors
**Maintained By:** AI Agent + Solo Founder

=============================================================================
