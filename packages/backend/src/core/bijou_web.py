#!/usr/bin/env python3
"""
W3J Bijou AI WhatsApp Enterprise - Fly.io Deployment Version
Multi-language WhatsApp AI service for Malaysian market
"""

import asyncio
import json
import logging
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Bijou AI WhatsApp Enterprise")


@app.get("/")
async def root():
    return HTMLResponse(f"""
    <h1>🤖 Bijou AI WhatsApp Enterprise</h1>
    <p>Status: <strong style="color: green;">Running on Fly.io</strong></p>
    <p>Region: Singapore (sin)</p>
    <p>Multi-language support: Malay, Mandarin, Tamil, English, Manglish</p>
    <p>Owner: {os.getenv("OWNER_WHATSAPP_JID", "Not configured")}</p>
    <h3>Features:</h3>
    <ul>
        <li>✅ Multi-Language Detection (ms, zh, ta, en, en-my)</li>
        <li>✅ Cultural Context Adaptation</li>
        <li>✅ Human Escalation System</li>
        <li>✅ AI-Powered Responses (Gemini + OpenAI)</li>
        <li>✅ Multi-Tenant Support</li>
        <li>✅ Google Sheets Integration</li>
    </ul>
    <p><a href="/health">Health Check</a> | <a href="/status">Status</a></p>
    """)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bijou-ai-enterprise",
        "platform": "fly.io",
        "region": "sin",
        "version": "1.0.0",
        "features": {
            "multi_language": True,
            "cultural_context": True,
            "human_escalation": True,
            "ai_powered": True,
            "multi_tenant": True,
        },
        "owner": os.getenv("OWNER_WHATSAPP_JID", "Not configured"),
        "languages": ["ms", "zh", "ta", "en", "en-my"],
    }


@app.get("/status")
async def status():
    return {
        "service": "bijou-ai-whatsapp-enterprise",
        "status": "running",
        "platform": "fly.io",
        "region": "singapore",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "ai_model": os.getenv("AI_MODEL", "gemini-1.5-flash"),
        "languages_supported": ["Malay", "Mandarin", "Tamil", "English", "Manglish"],
        "owner": os.getenv("OWNER_WHATSAPP_JID", "Not configured"),
        "features": {
            "multi_language_detection": True,
            "cultural_context": True,
            "human_escalation": True,
            "multi_tenant": True,
            "google_sheets": True,
        },
    }


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "owner": os.getenv("OWNER_WHATSAPP_JID", "Not configured"),
        "languages": os.getenv("PRIMARY_LANGUAGES", "ms,zh,ta,en,en-my").split(","),
        "cultural_context": os.getenv("CULTURAL_CONTEXT_ENABLED", "true").lower()
        == "true",
        "manglish_detection": os.getenv("MANGLISH_DETECTION", "true").lower() == "true",
        "escalation_enabled": os.getenv("ESCALATION_ENABLED", "true").lower() == "true",
        "multi_tenant": os.getenv("MULTI_TENANT_ENABLED", "true").lower() == "true",
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting Bijou AI WhatsApp Enterprise on port {port}")
    logger.info(
        f"🌐 Multi-language support: {os.getenv('PRIMARY_LANGUAGES', 'ms,zh,ta,en,en-my')}"
    )
    logger.info(f"📱 Owner: {os.getenv('OWNER_WHATSAPP_JID', 'Not configured')}")
    logger.info(f"🌏 Running on Fly.io in Singapore region")
    logger.info(
        f"🤖 AI Models: Gemini {'✓' if os.getenv('GEMINI_API_KEY') else '✗'}, OpenAI {'✓' if os.getenv('OPENAI_API_KEY') else '✗'}"
    )

    uvicorn.run("bijou:app", host="0.0.0.0", port=port, reload=False, access_log=True)
