"""
Media Handler for Bijou AI
===========================

Handles downloading, validating, and managing media files from WhatsApp Bridge.
Supports images, audio, video, and documents with size limits and cleanup.
"""

import hashlib
import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Deepgram prerecorded (batch) speech-to-text endpoint.
# WhatsApp voice notes arrive as OGG/Opus, which Deepgram ingests natively —
# no ffmpeg/transcoding required.
DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio_deepgram(
    audio_bytes: Optional[bytes] = None,
    mimetype: Optional[str] = None,
    *,
    audio_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "nova-2",
    timeout: float = 30.0,
) -> Optional[str]:
    """
    Transcribe a voice/audio note using Deepgram's prerecorded HTTP API.

    Accepts EITHER raw ``audio_bytes`` (preferred — WhatsApp voice notes are
    OGG/Opus, which Deepgram accepts directly) OR a remote ``audio_url``.

    Returns the transcript text on success, or ``None`` on any failure
    (missing ``DEEPGRAM_API_KEY``, network/HTTP error, empty transcript) so the
    caller can fall back gracefully. This function NEVER raises — the message
    pipeline must not crash on a bad voice note.

    Notes:
    - Auth: ``Authorization: Token <key>`` header (Deepgram convention).
    - Query params: model=nova-2, smart_format=true, detect_language=true.
    - No secret values are ever logged (only transcript length + latency).
    """
    key = api_key or os.getenv("DEEPGRAM_API_KEY")
    if not key:
        logger.warning(
            "⚠️ Deepgram transcription skipped: DEEPGRAM_API_KEY is not set"
        )
        return None

    if not audio_bytes and not audio_url:
        logger.warning(
            "⚠️ Deepgram transcription skipped: no audio bytes or URL provided"
        )
        return None

    params = {
        "model": model,
        "smart_format": "true",
        "detect_language": "true",
    }
    headers = {"Authorization": f"Token {key}"}

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if audio_bytes is not None:
                # Send raw audio bytes with the source content-type.
                headers["Content-Type"] = mimetype or "audio/ogg"
                response = await client.post(
                    DEEPGRAM_LISTEN_URL,
                    params=params,
                    headers=headers,
                    content=audio_bytes,
                )
            else:
                # Let Deepgram fetch the audio from a remote URL.
                response = await client.post(
                    DEEPGRAM_LISTEN_URL,
                    params=params,
                    headers=headers,
                    json={"url": audio_url},
                )

        response.raise_for_status()
        data = response.json()

        # results.channels[0].alternatives[0].transcript
        transcript = (
            (data.get("results") or {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        ).strip()

        elapsed_ms = (time.monotonic() - start) * 1000

        if not transcript:
            logger.warning(
                f"⚠️ Deepgram returned an empty transcript ({elapsed_ms:.0f}ms) — "
                "audio may be silent or unsupported"
            )
            return None

        logger.info(
            f"✅ Deepgram transcription OK: {len(transcript)} chars in {elapsed_ms:.0f}ms"
        )
        return transcript

    except httpx.HTTPStatusError as e:
        # Do NOT log response body / headers (may echo the key or PII).
        logger.error(
            f"❌ Deepgram HTTP {e.response.status_code}: transcription failed"
        )
        return None
    except httpx.TimeoutException:
        logger.error(f"❌ Deepgram transcription timed out after {timeout}s")
        return None
    except httpx.RequestError as e:
        logger.error(f"❌ Deepgram network error: {type(e).__name__}")
        return None
    except Exception as e:  # noqa: BLE001 — never let STT crash the pipeline
        logger.error(f"❌ Deepgram transcription error: {type(e).__name__}: {e}")
        return None


class MediaHandler:
    """
    Media file handler for Bijou AI.

    Downloads and manages media files from WhatsApp bridge with:
    - Size validation
    - Timeout handling
    - Automatic cleanup
    - Type validation
    - Error handling
    """

    def __init__(
        self,
        bridge_url: Optional[str] = None,
        temp_dir: Optional[str] = None,
        max_size_mb: int = 25,
        download_timeout: int = 30,
        auto_cleanup: bool = True,
    ):
        """
        Initialize MediaHandler.

        Args:
            bridge_url: WhatsApp bridge base URL
            temp_dir: Directory for temporary media files
            max_size_mb: Maximum file size in MB (default: 25MB for Whisper)
            download_timeout: Download timeout in seconds
            auto_cleanup: Automatically cleanup files after processing
        """
        self.bridge_url = bridge_url or os.getenv("BRIDGE_URL", "http://localhost:3000")
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.download_timeout = download_timeout
        self.auto_cleanup = auto_cleanup

        # Setup temp directory
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = (
                Path(os.getenv("MEDIA_TEMP_DIR", tempfile.gettempdir())) / "bijou_media"
            )

        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"📁 MediaHandler initialized: temp_dir={self.temp_dir}, max_size={max_size_mb}MB"
        )

    def download_media(
        self,
        message_id: str,
        media_type: str,
        media_url: Optional[str] = None,
        filename: Optional[str] = None,
        chat_jid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Download media file from WhatsApp bridge.

        Args:
            message_id: Unique message identifier
            media_type: Type of media (image, audio, video, document)
            media_url: URL to media file (optional)
            filename: Original filename (optional)
            chat_jid: Chat JID for bridge download (optional)

        Returns:
            Dictionary with download result:
            {
                "success": bool,
                "file_path": str,
                "file_size": int,
                "media_type": str,
                "error": str (if failed)
            }
        """
        try:
            # Determine download URL
            if media_url:
                # Direct URL provided - use it
                download_url = media_url
            else:
                # Construct bridge media endpoint: GET /api/media/{message_id}?chat_jid={chat_jid}
                if not chat_jid:
                    return {
                        "success": False,
                        "error": "chat_jid required for bridge download (no direct media_url provided)",
                    }
                download_url = (
                    f"{self.bridge_url}/api/media/{message_id}?chat_jid={chat_jid}"
                )

            logger.info(f"📥 Downloading {media_type} from: {download_url}")

            # Download with streaming to check size before full download
            with httpx.stream(
                "GET",
                download_url,
                timeout=self.download_timeout,
                follow_redirects=True,
            ) as response:
                response.raise_for_status()

                # Check content length if available
                content_length = response.headers.get("content-length")
                if content_length:
                    file_size = int(content_length)
                    if file_size > self.max_size_bytes:
                        return {
                            "success": False,
                            "error": f"File too large: {file_size / 1024 / 1024:.2f}MB (max {self.max_size_bytes / 1024 / 1024}MB)",
                        }

                # Generate safe filename
                safe_filename = self._generate_filename(
                    message_id, media_type, filename, response
                )
                file_path = self.temp_dir / safe_filename

                # Download file
                total_bytes = 0
                with open(file_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        total_bytes += len(chunk)

                        # Check size during download
                        if total_bytes > self.max_size_bytes:
                            f.close()
                            file_path.unlink(missing_ok=True)
                            return {
                                "success": False,
                                "error": f"File too large: exceeded {self.max_size_bytes / 1024 / 1024}MB during download",
                            }

                        f.write(chunk)

                logger.info(
                    f"✅ Downloaded {media_type}: {file_path} ({total_bytes / 1024:.2f}KB)"
                )

                return {
                    "success": True,
                    "file_path": str(file_path),
                    "file_size": total_bytes,
                    "media_type": media_type,
                    "filename": safe_filename,
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error downloading media: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: Failed to download media",
            }
        except httpx.TimeoutException:
            logger.error(f"❌ Timeout downloading media after {self.download_timeout}s")
            return {
                "success": False,
                "error": f"Download timeout after {self.download_timeout} seconds",
            }
        except httpx.RequestError as e:
            logger.error(f"❌ Network error downloading media: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading media: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }

    def _generate_filename(
        self,
        message_id: str,
        media_type: str,
        original_filename: Optional[str],
        response: httpx.Response,
    ) -> str:
        """
        Generate safe filename for downloaded media.

        Args:
            message_id: Message ID
            media_type: Media type
            original_filename: Original filename if available
            response: HTTP response (to check content-type)

        Returns:
            Safe filename with extension
        """
        # Get file extension
        extension = self._get_extension(media_type, original_filename, response)

        # Create safe filename from message_id
        safe_id = "".join(c for c in message_id if c.isalnum() or c in "._-")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{safe_id}_{timestamp}.{extension}"

    def _get_extension(
        self,
        media_type: str,
        filename: Optional[str],
        response: httpx.Response,
    ) -> str:
        """
        Determine file extension from media type, filename, or content-type.

        Args:
            media_type: Media type (image, audio, video, document)
            filename: Original filename
            response: HTTP response

        Returns:
            File extension (without dot)
        """
        # Try to get from original filename
        if filename:
            ext = Path(filename).suffix.lstrip(".")
            if ext:
                return ext.lower()

        # Try to get from content-type header
        content_type = response.headers.get("content-type", "").lower()

        # Map content-type to extension
        content_type_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "audio/ogg": "ogg",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/wav": "wav",
            "audio/webm": "webm",
            "video/mp4": "mp4",
            "video/webm": "webm",
            "video/3gpp": "3gp",
            "application/pdf": "pdf",
            "application/msword": "doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "text/plain": "txt",
        }

        for ct, ext in content_type_map.items():
            if ct in content_type:
                return ext

        # Default based on media_type
        default_extensions = {
            "image": "jpg",
            "audio": "ogg",
            "video": "mp4",
            "document": "pdf",
        }

        return default_extensions.get(media_type, "bin")

    def cleanup_media(self, file_path: str) -> bool:
        """
        Delete media file after processing.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"🗑️ Cleaned up media file: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ File not found for cleanup: {file_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Error cleaning up media file {file_path}: {e}")
            return False

    def get_media_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get information about a media file.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": "File not found"}

            stat = path.stat()

            return {
                "success": True,
                "file_path": str(path),
                "file_name": path.name,
                "file_size": stat.st_size,
                "file_size_mb": stat.st_size / 1024 / 1024,
                "extension": path.suffix.lstrip("."),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception as e:
            logger.error(f"❌ Error getting media info: {e}")
            return {"success": False, "error": str(e)}

    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files.

        Args:
            max_age_hours: Delete files older than this many hours

        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1

            if deleted_count > 0:
                logger.info(
                    f"🗑️ Cleaned up {deleted_count} old media files (>{max_age_hours}h)"
                )

            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error cleaning up old files: {e}")
            return 0

    def validate_media_type(self, media_type: str) -> bool:
        """
        Validate if media type is supported.

        Args:
            media_type: Media type to validate

        Returns:
            True if supported, False otherwise
        """
        supported_types = ["image", "audio", "video", "document"]
        return media_type.lower() in supported_types

    def get_temp_dir_size(self) -> Dict[str, Any]:
        """
        Get size of temporary directory.

        Returns:
            Dictionary with directory size information
        """
        try:
            total_size = 0
            file_count = 0

            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1

            return {
                "success": True,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / 1024 / 1024,
                "file_count": file_count,
                "temp_dir": str(self.temp_dir),
            }
        except Exception as e:
            logger.error(f"❌ Error getting temp dir size: {e}")
            return {"success": False, "error": str(e)}
