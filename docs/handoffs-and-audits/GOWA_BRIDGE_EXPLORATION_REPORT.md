# Gowa WhatsApp Bridge - Complete Exploration Report
**Bridge URL:** https://bijou-bridge-staging-v2.fly.dev  
**Version:** v8.1.2  
**Authentication:** Basic Auth (bijou:Ik7vOKhkH99a2deLtbW8eJGOudNDJVbn)  
**Date:** February 14, 2026  

---

## 🔐 Authentication Details

### Basic Auth Credentials
- **Username:** `bijou`
- **Password:** `Ik7vOKhkH99a2deLtbW8eJGOudNDJVbn`
- **Base64 Header:** `Basic Ymlqb3U6SWs3dk9LaGtIOTlhMmRlTHRiVzhlSkdPdWROREpWYm4=`

### Device Context
All device-scoped API calls require either:
- **HTTP Header:** `X-Device-Id: <device_id>`
- **Query Parameter:** `?device_id=<device_id>`
- If only one device is registered, it will be used as default

**Current Active Device:**
- **Device ID:** `0d1bc10a-1775-497f-a159-55ebb959d221`
- **Display Name:** Bijou
- **State:** `logged_in`
- **JID:** `60174106981@s.whatsapp.net`
- **Created:** 2026-02-11T10:52:29Z

---

## 📱 Bridge UI Pages & Features

### 1. **Homepage / Dashboard**
**URL:** `https://bijou-bridge-staging-v2.fly.dev/`

**Sections Available:**

#### **Device Management** (NEW in v8)
- Create/manage multiple WhatsApp devices
- View device status (logged_in, disconnected)
- Delete devices with logout
- Select active device for operations

#### **App Section** (Connection Management)
- **Login** - QR code-based authentication
- **Login with Code** - Pairing code authentication
- **Logout** - Disconnect and clear session
- **Reconnect** - Restore connection

#### **Send Section** (Message Types)
- Send Message (text with @mentions, ghost mentions, @everyone)
- Send Image (with compression, view-once)
- Send File (max 50MB)
- Send Video (max 100MB with compression)
- Send Sticker (auto WebP conversion from JPG/PNG/GIF)
- Send Contact (vCard)
- Send Location (coordinates)
- Send Audio
- Send Poll/Vote
- Send Presence (online/offline status)
- Send Chat Presence (typing indicator)
- Send Link (with caption)

#### **Message Section** (Message Actions)
- Delete Message
- Revoke Message (delete for everyone)
- React to Message (emoji reactions)
- Update/Edit Message
- Mark as Read

#### **Group Section**
- List My Groups (max 500 due to WhatsApp limitation)
- Create Group
- Join Group with Link
- Get Group Info from Link
- Add Participants
- Set Group Photo
- Set Group Name
- Set Group Locked (admin-only settings)
- Set Group Announce (announcement mode)
- Set Group Topic/Description
- Get Invite Link
- Group Info

#### **Newsletter Section**
- List My Newsletters
- Unfollow Newsletter

#### **Account Section**
- View Avatar
- Change Avatar
- Change Push Name
- User Info
- Business Profile
- Privacy Settings
- Contacts List
- User Check (verify number)

#### **Chat Management Section**
- Pin/Unpin Chats
- Disappearing Messages Settings
- Chat List (with pagination)
- Get Chat Messages

---

## 🔌 Complete API Endpoint Reference

### **Device Management API** (v8 Multi-Device)

| Method | Endpoint | Description | Requires Device ID? |
|--------|----------|-------------|---------------------|
| `GET` | `/devices` | List all devices | ❌ No |
| `POST` | `/devices` | Create new device | ❌ No |
| `GET` | `/devices/:device_id` | Get device info | ❌ No |
| `DELETE` | `/devices/:device_id` | Remove device | ❌ No |
| `GET` | `/devices/:device_id/login` | QR login (NOT IMPLEMENTED) | ❌ No |
| `POST` | `/devices/:device_id/login/code` | Pairing code login | ❌ No |
| `POST` | `/devices/:device_id/logout` | Logout device | ❌ No |
| `POST` | `/devices/:device_id/reconnect` | Reconnect device | ❌ No |
| `GET` | `/devices/:device_id/status` | Device connection status | ❌ No |

**Example Response - List Devices:**
```json
{
  "code": "SUCCESS",
  "message": "List devices",
  "results": [
    {
      "id": "0d1bc10a-1775-497f-a159-55ebb959d221",
      "display_name": "Bijou",
      "state": "logged_in",
      "jid": "60174106981@s.whatsapp.net",
      "created_at": "2026-02-11T10:52:29.767774838Z"
    }
  ]
}
```

### **Legacy App API** (Device-Scoped)

| Method | Endpoint | Description | Requires Device ID? |
|--------|----------|-------------|---------------------|
| `GET` | `/app/login` | Get QR code for login | ✅ Yes (Header/Query) |
| `GET` | `/app/login-with-code?phone=628xxx` | Get pairing code | ✅ Yes |
| `GET` | `/app/logout` | Logout current device | ✅ Yes |
| `GET` | `/app/reconnect` | Reconnect to WhatsApp | ✅ Yes |
| `GET` | `/app/devices` | List devices (legacy format) | ✅ Yes |
| `GET` | `/app/status` | Connection status | ✅ Yes |

**Example Response - App Status:**
```json
{
  "code": "SUCCESS",
  "message": "Connection status retrieved",
  "results": {
    "device_id": "0d1bc10a-1775-497f-a159-55ebb959d221",
    "is_connected": true,
    "is_logged_in": true
  }
}
```

**Example Response - App Login (QR Code):**
```json
{
  "code": "SUCCESS",
  "message": "QR Code generated",
  "results": {
    "qr_link": "data:image/png;base64,iVBORw0KG...",
    "qr_duration": 60
  }
}
```

### **User API** (Device-Scoped)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/user/info?phone=628xxx` | Get user profile info |
| `GET` | `/user/avatar?phone=628xxx&is_preview=false` | Get user avatar |
| `POST` | `/user/avatar` | Change own avatar |
| `POST` | `/user/pushname` | Change display name |
| `GET` | `/user/my/groups` | List user's groups (max 500) |
| `GET` | `/user/my/newsletters` | List subscribed newsletters |
| `GET` | `/user/my/privacy` | Get privacy settings |
| `GET` | `/user/my/contacts` | List all contacts |
| `GET` | `/user/check?phone=628xxx` | Verify if number on WhatsApp |
| `GET` | `/user/business-profile?phone=628xxx` | Get business profile |

### **Send Message API** (Device-Scoped)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/send/message` | Send text message |
| `POST` | `/send/image` | Send image with caption |
| `POST` | `/send/file` | Send document (max 50MB) |
| `POST` | `/send/video` | Send video (max 100MB) |
| `POST` | `/send/audio` | Send audio/voice note |
| `POST` | `/send/sticker` | Send sticker (auto WebP convert) |
| `POST` | `/send/contact` | Send contact vCard |
| `POST` | `/send/location` | Send location coordinates |
| `POST` | `/send/link` | Send link with preview |
| `POST` | `/send/poll` | Send poll/vote |
| `POST` | `/send/presence` | Set online/offline status |
| `POST` | `/send/chat-presence` | Send typing indicator |

**Example Payload - Send Message:**
```json
{
  "phone": "628123456789",
  "message": "Hello @628987654321, how are you?",
  "mentions": ["628987654321@s.whatsapp.net"]
}
```

**Ghost Mentions (Mention All):**
```json
{
  "phone": "120363xxx@g.us",
  "message": "Meeting at 3pm everyone!",
  "mentions": ["@everyone"]
}
```

### **Message Actions API** (Device-Scoped)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/message/:message_id/revoke` | Delete message for everyone |
| `POST` | `/message/:message_id/reaction` | React with emoji |
| `POST` | `/message/:message_id/delete` | Delete for self |
| `POST` | `/message/:message_id/update` | Edit message |
| `POST` | `/message/:message_id/read` | Mark as read |
| `POST` | `/message/:message_id/star` | Star message |
| `POST` | `/message/:message_id/unstar` | Unstar message |
| `GET` | `/message/:message_id/download` | Download media |

### **Group API** (Device-Scoped)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/group/join-with-link` | Join group via invite link |
| `GET` | `/group/info-from-link?link=xxx` | Get group info from link |
| `GET` | `/group/info?group_jid=xxx@g.us` | Get group details |
| `POST` | `/group/leave` | Leave group |
| `POST` | `/group` | Create new group |
| `GET` | `/group/participants?group_jid=xxx` | List members |
| `POST` | `/group/participants` | Add participants |
| `POST` | `/group/participants/remove` | Remove participant |
| `POST` | `/group/participants/promote` | Make admin |
| `POST` | `/group/participants/demote` | Remove admin |
| `GET` | `/group/participants/export` | Export members CSV |
| `GET` | `/group/participant-requests` | List pe
