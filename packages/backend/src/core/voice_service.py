"""
Voice Response Service for Bijou AI
====================================

Provides TTS (Text-to-Speech) capabilities by routing requests to external services.
Currently relies on OpenAI for high-quality voice generation,
avoiding heavy local dependencies like Torch/Chatterbox.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional
import time

# Use OpenAI for TTS generation since Gemini 2.5 Flash only supports audio INPUT (not output)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

class VoiceResponseService:
    """
    Lightweight voice response generator for Bijou AI.
    
    Features:
    - No heavy ML dependencies (Torch, Chatterbox removed)
    - PTT (Push-to-Talk) format for WhatsApp (OGG/Opus)
    - External API integration (OpenAI TTS)
    """
    
    def __init__(
        self,
        enabled: bool = True,
        temp_dir: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        **kwargs
    ):
        self.enabled = enabled
        self.gemini_api_key = gemini_api_key
        # Use provided key or env var
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        self.openai_client = None
        if self.enabled:
            if not self.openai_api_key:
                logger.warning("⚠️ Voice Service enabled but OPENAI_API_KEY is missing. Voice generation will fail.")
            elif OpenAI:
                try:
                    self.openai_client = OpenAI(api_key=self.openai_api_key)
                    logger.info("✅ OpenAI Client initialized for Voice Service")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            else:
                logger.warning("⚠️ 'openai' package not installed. Cannot generate voice.")

        # Setup temp directory
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(os.getenv("VOICE_TEMP_DIR", tempfile.gettempdir())) / "bijou_voice"
        
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        if self.enabled:
            logger.info(f"✅ Voice Service initialized (Lightweight Mode) - Temp Dir: {self.temp_dir}")

    def generate_voice(
        self,
        text: str,
        language: Optional[str] = None,
        emotion: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Generate voice audio from text using OpenAI TTS.
        Returns a dict with 'path' to the generated OGG file, or None on failure.
        """
        if not self.enabled or not self.openai_client:
            if self.enabled and not self.openai_client:
                logger.error("❌ Voice generation requested but OpenAI client is not available")
            return None
        
        try:
            # Cleanup old files first to prevent disk fill-up
            self.cleanup_old_files()

            logger.info(f"🎤 Generating voice for: {text[:50]}...")
            
            # OpenAI TTS settings
            # model: tts-1 (faster) or tts-1-hd (better quality)
            # voice: alloy, echo, fable, onyx, nova, shimmer
            # Nova is a good, energetic female voice. Alloy is neutral.
            voice = "nova" 
            if emotion == "calm":
                voice = "shimmer"
            elif emotion == "serious":
                voice = "onyx"

            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                response_format="opus" # WhatsApp prefers OGG/Opus. OpenAI 'opus' format is in an .ogg container.
            )

            # Generate unique filename
            timestamp = int(time.time())
            filename = f"voice_{timestamp}_{hash(text) % 10000}.ogg"
            file_path = self.temp_dir / filename

            # Stream to file
            response.stream_to_file(file_path)

            if file_path.exists() and file_path.stat().st_size > 0:
                logger.info(f"✅ Voice generated successfully: {file_path}")
                return {
                    "path": str(file_path),
                    "format": "ogg",
                    "duration": None # OpenAI doesn't return duration in metadata easily
                }
            else:
                logger.error("❌ Voice file creation failed (empty or missing)")
                return None

        except Exception as e:
            logger.error(f"❌ Voice generation failed: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: int = 1):
        """Clean up old voice files (default 1 hour to save space)."""
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        
        deleted = 0
        try:
            for file in self.temp_dir.glob("voice_*.ogg"):
                if file.stat().st_mtime < cutoff:
                    try:
                        file.unlink()
                        deleted += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error during voice cleanup: {e}")
            
        if deleted > 0:
            logger.debug(f"🧹 Cleaned up {deleted} old voice files")

    def should_use_voice_response(
        self,
        message_has_voice: bool,
        tenant_config: Optional[Dict] = None,
        user_preference: Optional[bool] = None,
    ) -> bool:
        """Determine if we should respond with voice."""
        if not self.enabled:
            return False
        
        if user_preference is not None:
            return user_preference
        
        if tenant_config:
            # Check if voice is globally disabled for this tenant
            if not tenant_config.get("voice_responses_enabled", True):
                return False
            
            # Check mirror mode (only reply voice if user sent voice)
            # Default to True (mirroring) if not specified
            if tenant_config.get("voice_mirror_mode", True):
                return message_has_voice
        
        # Default behavior: mirror user's modality
        return message_has_voice


# Singleton instance
_voice_service = None

def get_voice_service(
    enabled: bool = True,
    gemini_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    **kwargs
) -> VoiceResponseService:
    """Get or create voice service singleton."""
    global _voice_service
    
    if _voice_service is None:
        _voice_service = VoiceResponseService(
            enabled=enabled,
            gemini_api_key=gemini_api_key,
            openai_api_key=openai_api_key,
            **kwargs
        )
    
    return _voice_service
