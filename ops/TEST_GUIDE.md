# Bijou AI Multi-Channel Test Guide

## Quick Setup Checklist

- [x] Code deployed to `bijou-staging.fly.dev`
- [x] WhatsApp webhook working (`/webhook/message`)
- [ ] **YOU DO:** Set `TELEGRAM_BOT_TOKEN` secret (see below)
- [ ] Test WhatsApp
- [ ] Test Telegram

---

## Step 1: Set Telegram Token (Required)

```powershell
fly secrets set --app bijou-staging TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```

After setting, the app will auto-restart and register the Telegram webhook.

---

## Step 2: Test WhatsApp

### Option A: Send a real WhatsApp message
1. Open WhatsApp
2. Send message to your bot number
3. Wait for AI response (should reply within 5 seconds)

### Option B: Check logs
```powershell
fly logs --app bijou-staging
```
Look for: `[WEBHOOK] Received message` and `Sent to`

---

## Step 3: Test Telegram

### Option A: Message your bot
1. Open Telegram
2. Search for your bot (e.g., `@YourBijouBot`)
3. Send `/start` or any message
4. Wait for AI response

### Option B: Check logs
```powershell
fly logs --app bijou-staging
```
Look for: `[TELEGRAM] Received update` and `[TG] Sent to`

---

## Quick Validation Commands

```powershell
# Check app status
fly status --app bijou-staging

# Check health
curl https://bijou-staging.fly.dev/health

# View live logs
fly logs --app bijou-staging

# Check secrets are set
fly secrets list --app bijou-staging
```

---

## Expected Log Output (Success)

### WhatsApp Message:
```
[WEBHOOK] Received message ABC123 from 60123456789@s.whatsapp.net
Processing message ABC123
Response generated via Gemini 2.5 Flash
[WA] Sent to 60123456789@s.whatsapp.net: Hi there!...
```

### Telegram Message:
```
[TELEGRAM] Received update: 123456789
[TELEGRAM] Processing message 1 from 987654321
Response generated via Gemini 2.5 Flash
[TG] Sent to 987654321: Hi there!...
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Telegram not enabled" | Set `TELEGRAM_BOT_TOKEN` secret |
| App suspended | Run `fly machine start 080e091f05d6e8 --app bijou-staging` |
| No response | Check logs for errors |
| 429 rate limit | Add more `GEMINI_API_KEYS` |

---

## Test Messages to Try

| Language | Message |
|----------|---------|
| English | "Hi, what services do you offer?" |
| Malay | "Apa khabar? Boleh tolong saya?" |
| Manglish | "Eh boss, how much ah?" |
| Mandarin | "你好，我想了解你们的服务" |
| Bengali | "আমি সাহায্য চাই" |

---

## Production Deployment

After staging tests pass:

```powershell
# Deploy to production
fly deploy --app bijou-ai-enterprise-w3j --config fly.toml

# Set production Telegram token
fly secrets set --app bijou-ai-enterprise-w3j TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
```
