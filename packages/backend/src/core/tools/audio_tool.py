"""
Audio Processing Tool
=====================

Handles audio transcription (Speech-to-Text) and text-to-speech synthesis.
Supports multiple audio formats and providers (OpenAI Whisper, Google Speech API).
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class AudioTool:
    """
    Audio processing tool for Bijou.

    Provides audio transcription and text-to-speech capabilities.
    Supports: OpenAI Whisper API, Google Speech-to-Text, Google Text-to-Speech.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        google_credentials_path: Optional[str] = None,
    ):
        """
        Initialize Audio tool.

        Args:
            openai_api_key: OpenAI API key for Whisper
            google_credentials_path: Path to Google Cloud credentials
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.google_credentials_path = google_credentials_path or os.getenv(
            "GOOGLE_CREDENTIALS_PATH"
        )

        self.whisper_endpoint = "https://api.openai.com/v1/audio/transcriptions"
        self.tts_endpoint = "https://api.openai.com/v1/audio/speech"

        self._whisper_available = bool(self.openai_api_key)
        self._google_available = bool(self.google_credentials_path)

        if not self._whisper_available and not self._google_available:
            logger.warning(
                "Audio tool initialized without API keys. Set OPENAI_API_KEY or GOOGLE_CREDENTIALS_PATH."
            )

    def transcribe_audio(
        self,
        audio_path: str,
        language: Optional[str] = None,
        provider: str = "whisper",
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)
            language: Language code (e.g., 'en', 'es', 'fr'). Auto-detect if None.
            provider: Transcription provider - 'whisper' or 'google'

        Returns:
            Dictionary with transcription results

        Example:
            >>> tool = AudioTool()
            >>> result = tool.transcribe_audio("voice_message.ogg")
            >>> print(result["text"])
        """
        try:
            if provider == "whisper":
                return self._transcribe_with_whisper(audio_path, language)
            elif provider == "google":
                return self._transcribe_with_google(audio_path, language)
            else:
                return {"success": False, "error": f"Unknown provider: {provider}"}

        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            return {"success": False, "error": str(e)}

    def text_to_speech(
        self,
        text: str,
        output_path: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Convert text to speech audio file.

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file (mp3)
            voice: Voice to use - 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
            model: TTS model - 'tts-1' (faster) or 'tts-1-hd' (higher quality)
            speed: Speech speed (0.25 to 4.0, default 1.0)

        Returns:
            Dictionary with success status and file path

        Example:
            >>> tool = AudioTool()
            >>> result = tool.text_to_speech("Hello, how are you?", "greeting.mp3")
            >>> print(result["audio_path"])
        """
        if not self._whisper_available:
            return {"success": False, "error": "OpenAI API key not configured"}

        try:
            # Build request
            url = self.tts_endpoint
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "input": text,
                "voice": voice,
                "speed": speed,
            }

            # Call API
            response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()

            # Save audio file
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Audio generated successfully: {output_path}")
            return {
                "success": True,
                "audio_path": output_path,
                "text": text,
                "voice": voice,
                "model": model,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI TTS API error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"API error {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return {"success": False, "error": str(e)}

    def _transcribe_with_whisper(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (optional)

        Returns:
            Dictionary with transcription results
        """
        if not self._whisper_available:
            return {"success": False, "error": "OpenAI API key not configured"}

        try:
            # Validate file
            if not os.path.exists(audio_path):
                return {
                    "success": False,
                    "error": f"Audio file not found: {audio_path}",
                }

            # Check file size (max 25MB for Whisper)
            file_size = os.path.getsize(audio_path)
            if file_size > 25 * 1024 * 1024:
                return {
                    "success": False,
                    "error": "File too large (max 25MB for Whisper API)",
                }

            # Prepare request
            url = self.whisper_endpoint
            headers = {"Authorization": f"Bearer {self.openai_api_key}"}

            # Read audio file
            with open(audio_path, "rb") as audio_file:
                files = {"file": (os.path.basename(audio_path), audio_file)}
                data = {"model": "whisper-1"}

                if language:
                    data["language"] = language

                # Call API
                response = httpx.post(
                    url, headers=headers, files=files, data=data, timeout=120.0
                )
                response.raise_for_status()

            result = response.json()

            logger.info(f"Audio transcribed successfully: {audio_path}")
            return {
                "success": True,
                "text": result.get("text", ""),
                "language": language or "auto",
                "audio_path": audio_path,
                "provider": "whisper",
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Whisper API error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"API error {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            logger.error(f"Failed to transcribe with Whisper: {e}")
            return {"success": False, "error": str(e)}

    def _transcribe_with_google(
        self, audio_path: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Google Speech-to-Text API.

        Args:
            audio_path: Path to audio file
            language: Language code (BCP-47, e.g., 'en-US')

        Returns:
            Dictionary with transcription results
        """
        if not self._google_available:
            return {
                "success": False,
                "error": "Google credentials not configured",
            }

        try:
            # Lazy import Google libraries
            from google.cloud import speech

            # Initialize client
            client = speech.SpeechClient()

            # Read audio file
            with open(audio_path, "rb") as audio_file:
                content = audio_file.read()

            # Configure audio
            audio = speech.RecognitionAudio(content=content)

            # Detect file format
            file_ext = Path(audio_path).suffix.lower()
            encoding_map = {
                ".wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                ".mp3": speech.RecognitionConfig.AudioEncoding.MP3,
                ".ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                ".flac": speech.RecognitionConfig.AudioEncoding.FLAC,
            }
            encoding = encoding_map.get(
                file_ext, speech.RecognitionConfig.AudioEncoding.LINEAR16
            )

            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=encoding,
                language_code=language or "en-US",
                enable_automatic_punctuation=True,
            )

            # Perform transcription
            response = client.recognize(config=config, audio=audio)

            # Extract transcription
            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript + " "

            transcript = transcript.strip()

            if not transcript:
                return {
                    "success": True,
                    "text": "",
                    "warning": "No speech detected in audio",
                }

            logger.info(f"Audio transcribed successfully with Google: {audio_path}")
            return {
                "success": True,
                "text": transcript,
                "language": language or "en-US",
                "audio_path": audio_path,
                "provider": "google",
            }

        except Exception as e:
            logger.error(f"Failed to transcribe with Google: {e}")
            return {"success": False, "error": str(e)}

    def convert_audio_format(
        self, input_path: str, output_path: str, output_format: str = "mp3"
    ) -> Dict[str, Any]:
        """
        Convert audio file to different format (requires ffmpeg).

        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file
            output_format: Output format (mp3, wav, ogg, etc.)

        Returns:
            Dictionary with conversion status
        """
        try:
            import subprocess

            # Check if ffmpeg is available
            try:
                subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                return {
                    "success": False,
                    "error": "ffmpeg not installed. Install ffmpeg to use audio conversion.",
                }

            # Convert using ffmpeg
            cmd = ["ffmpeg", "-i", input_path, "-y", output_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info(f"Audio converted: {input_path} -> {output_path}")
                return {
                    "success": True,
                    "input_path": input_path,
                    "output_path": output_path,
                    "format": output_format,
                }
            else:
                return {
                    "success": False,
                    "error": f"ffmpeg conversion failed: {result.stderr}",
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Audio conversion timed out"}
        except Exception as e:
            logger.error(f"Failed to convert audio: {e}")
            return {"success": False, "error": str(e)}

    def get_audio_duration(self, audio_path: str) -> Dict[str, Any]:
        """
        Get duration of audio file in seconds.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with duration information
        """
        try:
            import subprocess

            # Use ffprobe to get duration
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=10
            )

            duration = float(result.stdout.strip())

            return {
                "success": True,
                "duration_seconds": duration,
                "duration_formatted": self._format_duration(duration),
                "audio_path": audio_path,
            }

        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "success": False,
                "error": "ffprobe not installed or audio file invalid",
            }
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return {"success": False, "error": str(e)}

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string (e.g., "2:30" or "1:05:30")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
