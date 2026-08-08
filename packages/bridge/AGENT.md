# packages/bridge/AGENT.md — Bijou WhatsApp Bridge (Go, Fly.io)

> **Master playbook**: read `../../AGENTS.md` first. This file is the
> per-package detail for the **bridge** package (Go, 55KB `main.go`,
> runs on Fly.io per-tenant).
>
> The master covers: agent team, autonomous loop, CI/CD, local+remote sync,
> emergency procedures. This file covers: how to code + deploy the bridge.

---

# AGENT.md - WhatsApp Bridge Documentation

## =============================================================================
## Last Updated: 2026-01-28
## Purpose: Complete guide for the WhatsApp Bridge component
## Language: Go (using whatsmeow library)
## =============================================================================

## 🎯 WHAT IS THIS?

The WhatsApp Bridge is a **Go application** that:
1. Maintains a persistent connection to WhatsApp Web
2. Receives messages from WhatsApp users
3. Downloads and serves media files (images, audio, video)
4. Forwards messages to Bijou AI via webhook
5. Sends AI responses back to WhatsApp

```
┌──────────────┐      WebSocket       ┌──────────────┐
│   WhatsApp   │ ←─────────────────→ │    Bridge    │
│   Servers    │                      │   (Go App)   │
└──────────────┘                      └──────────────┘
                                             │
                                             │ HTTP Webhook
                                             ↓
                                      ┌──────────────┐
                                      │  Bijou AI    │
                                      │  (Python)    │
                                      └──────────────┘
```

---

## 📁 FILE STRUCTURE

```
whatsapp-bridge/
├── AGENT.md                    # THIS FILE
├── main.go                     # Main application (1,000+ lines)
├── go.mod                      # Go dependencies
├── go.sum                      # Dependency checksums
├── Dockerfile                  # Container build config
├── fly.toml                    # Production Fly.io config
├── fly.staging.toml            # Staging Fly.io config
└── store/                      # Local SQLite database + session
    ├── *.db                    # Message storage
    └── *.db3                   # WhatsApp session
```

---

## 🚨 CRITICAL LESSONS LEARNED

### ❌ WRONG APPROACH #1: Missing Media Endpoint

**Problem:**
- Bridge only had `/api/download` (POST) endpoint
- Bijou was calling `GET /api/media/{message_id}` → 404
- Media download always failed

**Fix Applied (2026-01-28):**
Added new endpoint in `main.go` around line 893:

```go
// Handler for getting media by message ID (GET endpoint for easier access)
http.HandleFunc("/api/media/", func(w http.ResponseWriter, r *http.Request) {
    // Only allow GET requests
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    // Extract message ID from URL path
    // URL format: /api/media/{messageId}?chat_jid={chatJID}
    path := r.URL.Path
    messageID := strings.TrimPrefix(path, "/api/media/")
    chatJID := r.URL.Query().Get("chat_jid")

    // Download media from WhatsApp
    success, mediaType, filename, path, err := downloadMedia(client, messageStore, messageID, chatJID)

    // Read and serve file
    fileData, _ := os.ReadFile(path)

    // Set proper content-type
    w.Header().Set("Content-Type", contentType)
    w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))
    w.Write(fileData)
})
```

**Result:**
✅ Bijou can now download media files directly
✅ Single GET request with message_id and chat_jid
✅ Returns actual file content, not just metadata

---

### ❌ WRONG APPROACH #2: History Sync Enabled

**Problem:**
- WhatsApp sends MASSIVE history sync on first connection
- Can download 10,000+ messages
- Fills up storage rapidly
- Costs money for storage/bandwidth
- Not needed for Bijou's use case

**Fix:**
Always set in environment:
```bash
ENABLE_HISTORY_SYNC=false
```

**Why:**
- Bijou only needs NEW incoming messages
- History is irrelevant for AI assistant
- Saves storage and costs
- Prevents database bloat

---

### ❌ WRONG APPROACH #3: Not Passing chat_jid to Media Endpoint

**Problem:**
- Multiple chats can have messages with similar IDs
- Need both message_id AND chat_jid to uniquely identify media
- Query: `SELECT ... WHERE id = ? AND chat_jid = ?`

**Fix:**
Always require `chat_jid` as query parameter:
```
GET /api/media/{message_id}?chat_jid={chat_jid}
```

---

## 📊 ENDPOINTS REFERENCE

### `GET /health`
**Purpose:** Health check for Fly.io monitoring

**Response:**
```json
{
  "status": "healthy",
  "connected": true,
  "uptime": "5h23m"
}
```

**Use:** Fly.io calls this every 15 seconds to verify bridge is alive

---

### `POST /api/send`
**Purpose:** Send message to WhatsApp user

**Request Body:**
```json
{
  "recipient": "60123456789@s.whatsapp.net",
  "message": "Hello from Bijou!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully"
}
```

**Called By:** Bijou AI when sending responses

---

### `POST /api/download` (Legacy)
**Purpose:** Download media and return metadata

**Request Body:**
```json
{
  "message_id": "3EB0...",
  "chat_jid": "60123456789@s.whatsapp.net"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully downloaded image media",
  "filename": "image_20260128_165021.jpg",
  "path": "store/60123456789_s.whatsapp.net/image_20260128_165021.jpg"
}
```

**Note:** Returns path to local file, doesn't serve file content

---

### `GET /api/media/{message_id}?chat_jid={chat_jid}` ✨ NEW
**Purpose:** Download and serve media file directly

**URL:**
```
GET /api/media/3EB06F69959B6DEFDB2729?chat_jid=84950644740196@lid
```

**Response:**
- Binary file content (JPEG, OGG, MP4, etc.)
- Content-Type header set correctly
- Content-Disposition with filename

**Called By:** Bijou's MediaHandler

**Flow:**
1. Parse message_id from URL path
2. Get chat_jid from query parameter
3. Query database for media metadata
4. Download from WhatsApp if not cached
5. Read file from local storage
6. Serve file with proper headers

---

### `GET /api/messages`
**Purpose:** List recent messages (polling fallback)

**Query Parameters:**
- `since` - ISO timestamp (optional)
- `limit` - Number of messages (default: 50)
- `chat_jid` - Filter by chat (optional)

**Response:**
```json
{
  "success": true,
  "messages": [
    {
      "id": "3EB0...",
      "chat_jid": "60123456789@s.whatsapp.net",
      "sender": "60123456789@s.whatsapp.net",
      "content": "Hello",
      "timestamp": "2026-01-28T16:50:00Z",
      "is_from_me": false,
      "media_type": "",
      "filename": ""
    }
  ]
}
```

**Note:** Webhook is preferred over polling

---

## 💾 DATABASE SCHEMA

### Messages Table (SQLite)

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    chat_jid TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT,
    timestamp DATETIME NOT NULL,
    is_from_me BOOLEAN,
    media_type TEXT,
    filename TEXT,
    url TEXT,                -- WhatsApp media URL
    media_key BLOB,          -- Encryption key
    file_sha256 BLOB,        -- File hash
    file_enc_sha256 BLOB,    -- Encrypted file hash
    file_length INTEGER      -- File size in bytes
);
```

**Key Functions:**

1. `StoreMessage()` - Save incoming message
2. `GetMediaInfo()` - Retrieve media metadata
3. `StoreMediaInfo()` - Update media info after download

---

## 🔄 MESSAGE FLOW

### Incoming Message (Text)

```
1. WhatsApp sends message event
   ↓
2. handleMessage() processes event
   - Extract: id, chat_jid, sender, content, timestamp
   ↓
3. Store in database
   ↓
4. Send webhook to Bijou
   POST https://bijou-staging.fly.dev/webhook/message
   ↓
5. Wait for Bijou response
   ↓
6. Receive response via /api/send
   ↓
7. Send to WhatsApp
```

### Incoming Message (Media)

```
1. WhatsApp sends media message event
   ↓
2. handleMessage() processes event
   - Extract: id, chat_jid, media_type, filename
   - Extract: url, media_key, file_sha256 (from protobuf)
   ↓
3. Store metadata in database (DON'T download yet)
   ↓
4. Send webhook to Bijou
   - Include media_type, filename
   - Don't include media_url (Bijou will request it)
   ↓
5. Bijou requests media via GET /api/media/{id}?chat_jid={jid}
   ↓
6. downloadMedia() called
   - Check local cache
   - If not cached, download from WhatsApp using url + media_key
   - Decrypt using media_key and sha256
   - Save to store/{chat_jid}/{filename}
   ↓
7. Serve file content to Bijou
   ↓
8. Bijou processes and responds
```

---

## 🛠️ CONFIGURATION

### Environment Variables

```bash
# Required
ENVIRONMENT=staging              # or "production"
BIJOU_WEBHOOK_URL=https://bijou-staging.fly.dev/webhook/message

# Critical Settings
ENABLE_HISTORY_SYNC=false        # ⚠️ MUST be false!

# Optional
PORT=8080                        # Default: 8080
LOG_LEVEL=info                   # info, debug, warn, error
```

### Fly.io Configuration

**fly.staging.toml:**
```toml
app = "whatsapp-bridge-staging-w3j"
primary_region = "sjc"

[build]
  dockerfile = "Dockerfile"

[env]
  ENVIRONMENT = "staging"
  BIJOU_WEBHOOK_URL = "https://bijou-staging.fly.dev/webhook/message"
  ENABLE_HISTORY_SYNC = "false"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  memory = '512mb'
  cpu_kind = 'shared'
  cpus = 1

[[mounts]]
  source = "whatsapp_staging_data"
  destination = "/app/store"
  initial_size = "1gb"
```

---

## 🚀 DEPLOYMENT

### Deploy to Staging

```bash
cd whatsapp-bridge

# Deploy
fly deploy -a whatsapp-bridge-staging-w3j

# Check status
fly status -a whatsapp-bridge-staging-w3j

# View logs
fly logs -a whatsapp-bridge-staging-w3j
```

### Deploy to Production

```bash
cd whatsapp-bridge

# Deploy
fly deploy -a whatsapp-bridge-w3j

# Monitor
fly logs -a whatsapp-bridge-w3j
```

### First-Time Setup

```bash
# Create app
fly apps create whatsapp-bridge-staging-w3j

# Create volume for persistent storage
fly volumes create whatsapp_staging_data --region sjc --size 1 -a whatsapp-bridge-staging-w3j

# Deploy
fly deploy -a whatsapp-bridge-staging-w3j
```

**Important:** After first deploy, you must scan QR code to link WhatsApp:

```bash
# View logs to get QR code
fly logs -a whatsapp-bridge-staging-w3j

# Look for QR code in terminal output
# Scan with WhatsApp mobile app
```

---

## 🔍 DEBUGGING

### Check Connection Status

```bash
# View logs
fly logs -a whatsapp-bridge-staging-w3j

# Look for:
# ✓ Connected to WhatsApp!
# ✅ Successfully authenticated
```

### Test Endpoints

```bash
# Health check
curl https://whatsapp-bridge-staging-w3j.fly.dev/health

# List messages
curl "https://whatsapp-bridge-staging-w3j.fly.dev/api/messages?limit=5"

# Test media download (replace with real IDs)
curl "https://whatsapp-bridge-staging-w3j.fly.dev/api/media/MESSAGE_ID?chat_jid=CHAT_JID" -o test.jpg
```

### Common Issues

**Issue:** "Failed to connect to WhatsApp"
- Check if device is still linked (session might have expired)
- Scan QR code again

**Issue:** "Database locked"
- Only one instance should run (set min_machines_running = 1)
- Volume should be mounted correctly

**Issue:** "Media download returns 404"
- Verify message_id is correct
- Verify chat_jid is passed as query parameter
- Check if media exists in database: `SELECT * FROM messages WHERE id = ?`

---

## 📝 CODE ORGANIZATION

### main.go Structure (1000+ lines)

```
Lines 1-100:    Imports and type definitions
Lines 100-200:  MessageStore struct and database methods
Lines 200-400:  Media download and handling
Lines 400-600:  Message event handlers
Lines 600-800:  API endpoints (send, download, messages)
Lines 800-900:  NEW: GET /api/media endpoint
Lines 900-1000: Health check and server setup
Lines 1000+:    Main function and initialization
```

### Key Functions

**handleMessage(evt *events.Message)**
- Processes incoming WhatsApp messages
- Extracts text, media, metadata
- Stores in database
- Sends webhook to Bijou

**downloadMedia(client, messageStore, messageID, chatJID)**
- Downloads media from WhatsApp
- Decrypts using media_key
- Saves to local storage
- Returns file path

**extractMediaInfo(msg *waProto.Message)**
- Extracts media metadata from protobuf
- Returns: mediaType, filename, url, keys, hashes

**sendWebhook(message)**
- POSTs message to Bijou AI
- Retries on failure
- Logs success/failure

---

## 🔐 SECURITY

### Session Storage
- WhatsApp session stored in SQLite database
- Contains encryption keys and authentication tokens
- **NEVER** commit `store/*.db3` files to git
- Backup session DB to prevent re-authentication

### Media Files
- Encrypted by WhatsApp during transmission
- Decrypted using media_key from message
- Stored locally after decryption
- Served only via authenticated endpoints

### API Security
- Bridge accepts requests from Bijou AI only
- No public API exposure
- Fly.io provides HTTPS termination
- Internal communication on private network

---

## 📊 MONITORING

### Key Metrics to Watch

1. **Connection Status**
   - Should always show "Connected to WhatsApp"
   - If disconnected > 5 min, restart

2. **Webhook Success Rate**
   - Monitor "✅ Webhook sent successfully" logs
   - Alert if failures > 5% in 1 hour

3. **Media Download Success**
   - Monitor "Downloaded media" logs
   - Alert on repeated 404s or timeouts

4. **Storage Usage**
   ```bash
   fly volumes list -a whatsapp-bridge-staging-w3j
   ```
   - Alert if > 80% full
   - Clean old media files if needed

---

## 🧹 MAINTENANCE

### Clean Old Media Files

```go
// Add to main.go (TODO)
func cleanOldMedia() {
    // Delete files older than 7 days
    // Keep database records
}
```

### Database Maintenance

```bash
# SSH into container
fly ssh console -a whatsapp-bridge-staging-w3j

# Run SQLite commands
sqlite3 /app/store/*.db
sqlite> VACUUM;
sqlite> .quit
```

### Session Refresh

If WhatsApp disconnects:
1. Delete session: `rm /app/store/*.db3`
2. Restart bridge
3. Scan QR code again

---

## 🎯 PERFORMANCE OPTIMIZATION

### Current Settings
- Memory: 512MB (adequate for 1000 msg/day)
- CPU: Shared (sufficient for I/O bound work)
- Storage: 1GB (can handle ~2000 media files)

### Scaling Recommendations
- Single instance is sufficient (WebSocket connection)
- If media storage grows, increase volume size
- If CPU becomes bottleneck, upgrade to dedicated CPU

---

## 🚨 EMERGENCY PROCEDURES

### Bridge Not Responding
```bash
# 1. Check status
fly status -a whatsapp-bridge-staging-w3j

# 2. Restart machine
fly machine restart <machine-id> -a whatsapp-bridge-staging-w3j

# 3. Check logs
fly logs -a whatsapp-bridge-staging-w3j
```

### WhatsApp Disconnected
```bash
# 1. Check logs for disconnect reason
fly logs -a whatsapp-bridge-staging-w3j | grep -i disconnect

# 2. Restart to reconnect
fly machine restart <machine-id> -a whatsapp-bridge-staging-w3j

# 3. If session expired, rescan QR
```

### Database Corrupted
```bash
# 1. SSH into machine
fly ssh console -a whatsapp-bridge-staging-w3j

# 2. Check database integrity
cd /app/store
sqlite3 *.db "PRAGMA integrity_check;"

# 3. If corrupted, restore from backup or recreate
```

---

## ✅ TESTING CHECKLIST

Before deploying changes:

- [ ] Build succeeds locally: `go build`
- [ ] No lint errors: `go vet ./...`
- [ ] Test endpoints with curl
- [ ] Deploy to staging first
- [ ] Verify WhatsApp connection after deploy
- [ ] Test sending message via /api/send
- [ ] Test media download via /api/media
- [ ] Monitor logs for 10 minutes
- [ ] If all good, deploy to production

---

## 📚 DEPENDENCIES

### Go Modules

```
go.mau.fi/whatsmeow         - Official WhatsApp library
modernc.org/sqlite          - Pure Go SQLite
github.com/mdp/qrterminal   - QR code display
```

### Important Notes

- **whatsmeow** is maintained by Tulir (trusted developer)
- Library handles all WhatsApp protocol complexity
- Auto-updates protobuf definitions
- Supports latest WhatsApp features

---

## 🔄 CHANGELOG

### 2026-01-28
- ✅ Added GET /api/media/{id}?chat_jid={jid} endpoint
- ✅ Serves media files directly instead of just metadata
- ✅ Fixed content-type detection for images/audio/video
- ✅ Resolved 404 errors for media downloads
- ✅ Updated documentation

### Previous
- See git history for older changes

---

## 📞 INTEGRATION WITH BIJOU

### Bijou → Bridge

**Webhook Registration:**
Bridge sends all new messages to:
```
POST https://bijou-staging.fly.dev/webhook/message
```

**Message Send:**
Bijou sends responses via:
```
POST https://whatsapp-bridge-staging-w3j.fly.dev/api/send
```

**Media Download:**
Bijou downloads media via:
```
GET https://whatsapp-bridge-staging-w3j.fly.dev/api/media/{id}?chat_jid={jid}
```

### Bridge → WhatsApp

- Uses official whatsmeow library
- WebSocket connection (persistent)
- E2E encrypted messages
- Media uploaded/downloaded with encryption

---

## 🎓 BEST PRACTICES

1. **Always disable history sync** (`ENABLE_HISTORY_SYNC=false`)
2. **Single instance only** - WhatsApp allows one connection
3. **Monitor storage** - Media files accumulate
4. **Backup session DB** - Prevent re-authentication
5. **Use staging first** - Test changes before production
6. **Check logs daily** - Catch issues early
7. **Keep dependencies updated** - Security patches

---

## 🔗 USEFUL LINKS

- **whatsmeow GitHub:** https://github.com/tulir/whatsmeow
- **WhatsApp Business API Docs:** (for reference, we use personal API)
- **Fly.io Docs:** https://fly.io/docs/
- **Staging Bridge:** https://whatsapp-bridge-staging-w3j.fly.dev
- **Production Bridge:** https://whatsapp-bridge-w3j.fly.dev

---

**Last Updated:** 2026-01-28
**Next Review:** When adding new endpoints or fixing major bugs
**Maintained By:** AI Agent + Solo Founder

=============================================================================
