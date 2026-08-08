# WhatsApp Bridge (`whatsapp-bridge/`)

**Status:** Production
**Language:** Go (Golang 1.21)

---

## 🌉 What is this folder?
This is a **Microservice** separate from the main Python backend.
It connects to the WhatsApp Network using the `whatsmeow` library (reverse engineered WebSocket).

## 🚀 Architecture
*   **Standalone**: Run as its own container/process.
*   **Protocol**: HTTP API for Control + Webhooks for Events.
*   **State**: Stores session keys in a SQLite database (or Postgres in Prod).

## 🔌 API Endpoints
This service exposes a local API on port `3000` (default).

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | Check if alive. |
| `GET` | `/qr` | Get the Login QR code image. |
| `POST` | `/send` | Send a text message. |
| `GET` | `/status` | Check if logged in. |

## 🔗 Hooking into Bijou
1.  **Inbound**: When WhatsApp receives a message, this bridge POSTs JSON to `w3j-bijou-enterprise/api/webhook`.
2.  **Outbound**: Bijou POSTs JSON to `/send` on this bridge to reply.

## ⚠️ Critical Notes
*   **Session File**: The `device.db` or `token.pickle` contains the sensitive login keys.
*   **Multi-Device**: Supports generic multi-device login, but currently optimized for **Single Tenant** per container instance in the MVP.
