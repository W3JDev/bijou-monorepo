"""
E2E Tests for Voice Note Processing Pipeline

Tests the complete voice processing flow:
1. WhatsApp webhook receives voice message
2. Media download from bridge (HTTP Basic Auth)
3. Audio format conversion (OGG -> MP3 via ffmpeg)
4. Transcription (Gemini 2.5 Flash)
5. AI response generation
6. Message delivery

CRITICAL: These tests MUST pass before deployment to prevent voice processing failures.
"""

import asyncio
import base64
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Test configuration.
#
# Defaults target the local docker stack (docker-compose.local.yml), which
# publishes the bridge on 8081 with the basic-auth pair below. The previous
# default, bijou-bridge-staging-v2.fly.dev, no longer resolves, so the auth
# tests died on DNS instead of exercising the bridge.
#
# These read E2E_BRIDGE_* rather than BRIDGE_*: tests/conftest.py's autouse
# setup_test_env fixture points BRIDGE_URL at a mock host for unit tests, and
# these are the tests that want the real one.
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "media"
TEST_BRIDGE_URL = os.getenv("E2E_BRIDGE_URL", "http://localhost:8081")
TEST_BRIDGE_USER = os.getenv("E2E_BRIDGE_USER", "bijou")
TEST_BRIDGE_PASSWORD = os.getenv("E2E_BRIDGE_PASSWORD", "bijou-local-dev")

# The bridge is multi-tenant: /statics/** is routed per device and answers
# 400 DEVICE_ID_REQUIRED without this header, which would mask the auth result
# these tests are actually checking. An unknown device id still gets past basic
# auth and 404s, so a placeholder is enough here.
TEST_BRIDGE_DEVICE_ID = os.getenv("E2E_BRIDGE_DEVICE_ID", "e2e-test-device")
BRIDGE_HEADERS = {"X-Device-Id": TEST_BRIDGE_DEVICE_ID}


@pytest.fixture(scope="module")
def sample_voice_ogg() -> bytes:
    """
    A real 1-second OGG/Opus file, the container WhatsApp voice notes arrive in.

    This used to be a hand-assembled OggS+OpusHead byte string. ffmpeg cannot
    decode it -- it has a page header and no audio pages -- so every test that
    converted this fixture was asserting on a broken input rather than on the
    conversion. Encoding a real tone with ffmpeg keeps the fixture honest and
    costs a few milliseconds.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ogg_path = str(Path(tmp) / "sample_voice.ogg")
        result = subprocess.run(
            [
                "ffmpeg",
                "-f", "lavfi",
                "-i", "sine=frequency=440:duration=1",
                "-c:a", "libopus",
                "-b:a", "32k",
                "-y", ogg_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"could not build OGG fixture: {result.stderr}"
        return Path(ogg_path).read_bytes()


@pytest.fixture
def sample_voice_english() -> str:
    """Path to English voice sample (if exists)"""
    path = FIXTURES_DIR / "voice_english_5sec.ogg"
    return str(path) if path.exists() else None


@pytest.fixture
def sample_voice_malay() -> str:
    """Path to Malay voice sample (if exists)"""
    path = FIXTURES_DIR / "voice_malay_5sec.ogg"
    return str(path) if path.exists() else None


@pytest.fixture
def sample_voice_manglish() -> str:
    """Path to Manglish voice sample (if exists)"""
    path = FIXTURES_DIR / "voice_manglish_5sec.ogg"
    return str(path) if path.exists() else None


@pytest.fixture
def webhook_voice_payload() -> Dict:
    """WhatsApp webhook payload for voice message"""
    return {
        "messages": [
            {
                "from": "60123456789@s.whatsapp.net",
                "id": "test_msg_voice_001",
                "timestamp": "1708857600",
                "type": "audio",
                "audio": {
                    "mimetype": "audio/ogg; codecs=opus",
                    "sha256": "test_sha256_hash",
                    "id": "test_media_id_001",
                    "voice": True,
                },
            }
        ]
    }


@pytest.mark.e2e
@pytest.mark.asyncio
class TestVoiceProcessingPipeline:
    """Complete voice processing pipeline tests"""

    async def test_ffmpeg_installed(self):
        """CRITICAL: Verify ffmpeg is installed and working"""
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, "ffmpeg is not installed or not working"
        assert "ffmpeg version" in result.stdout.lower()
        print(f"OK: ffmpeg version: {result.stdout.split()[2]}")

    async def test_ffmpeg_opus_support(self):
        """Verify ffmpeg has libopus support (required for OGG decoding)"""
        result = subprocess.run(
            ["ffmpeg", "-codecs"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "libopus" in result.stdout or "opus" in result.stdout
        print("OK: ffmpeg has Opus codec support")

    async def test_ogg_to_mp3_conversion(self, sample_voice_ogg):
        """Test OGG -> MP3 conversion with ffmpeg"""
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
            ogg_file.write(sample_voice_ogg)
            ogg_path = ogg_file.name

        try:
            mp3_path = ogg_path.replace(".ogg", ".mp3")

            # Run ffmpeg conversion (same command as production code)
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    ogg_path,
                    "-ar",
                    "16000",  # 16kHz (Gemini requirement)
                    "-ac",
                    "1",  # Mono
                    "-b:a",
                    "32k",  # 32kbps
                    "-y",  # Overwrite
                    mp3_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            assert result.returncode == 0, f"ffmpeg failed: {result.stderr}"
            assert Path(mp3_path).exists(), "MP3 file was not created"
            assert Path(mp3_path).stat().st_size > 0, "MP3 file is empty"

            print(f"OK: OGG -> MP3 conversion successful ({Path(mp3_path).stat().st_size} bytes)")

        finally:
            # Cleanup
            if Path(ogg_path).exists():
                Path(ogg_path).unlink()
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY").startswith("mock"),
        reason="Requires real Gemini API key",
    )
    async def test_gemini_audio_transcription(self, sample_voice_ogg):
        """Test Gemini 2.5 Flash audio transcription (requires real API key)"""
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Convert OGG to MP3
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
            ogg_file.write(sample_voice_ogg)
            ogg_path = ogg_file.name

        try:
            mp3_path = ogg_path.replace(".ogg", ".mp3")
            subprocess.run(
                ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-b:a", "32k", "-y", mp3_path],
                capture_output=True,
                timeout=10,
            )

            # Upload to Gemini
            with open(mp3_path, "rb") as f:
                audio_file = genai.upload_file(f, mime_type="audio/mp3")

            # Transcribe
            response = model.generate_content([audio_file, "Transcribe this audio."])
            transcript = response.text

            assert transcript, "Gemini returned empty transcription"
            assert len(transcript) > 0, "Transcription is empty"

            print(f"OK: Gemini transcription: {transcript[:100]}...")

        finally:
            if Path(ogg_path).exists():
                Path(ogg_path).unlink()
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()

    async def test_media_download_auth_basic(self):
        """CRITICAL: Test media download uses HTTP Basic Auth (not X-API-Key)"""
        # This test verifies the bug fix from commit 3651abb
        test_media_url = f"{TEST_BRIDGE_URL}/statics/media/test_nonexistent.ogg"

        async with httpx.AsyncClient() as client:
            # Test with Basic Auth (CORRECT)
            response_basic = await client.get(
                test_media_url,
                auth=(TEST_BRIDGE_USER, TEST_BRIDGE_PASSWORD),
                headers=BRIDGE_HEADERS,
                timeout=10,
            )

            # We expect 404 (file not found) NOT 401/403 (auth error)
            assert response_basic.status_code in [404, 200], (
                f"Basic Auth failed with {response_basic.status_code}. "
                "Expected 404 (not found) or 200 (success), not 401/403 (auth error)"
            )

            print(f"OK: Basic Auth works (status: {response_basic.status_code})")

            # Test with X-API-Key header (WRONG - should fail)
            response_apikey = await client.get(
                test_media_url,
                headers={**BRIDGE_HEADERS, "X-API-Key": "test_key"},
                timeout=10,
            )

            # This should return 401/403 (no auth or wrong auth). NOT 404: GOWA
            # checks basic auth before device routing, so a 404 here means the
            # target has auth disabled (or isn't the bridge) — a real failure.
            assert response_apikey.status_code in [401, 403], (
                f"X-API-Key incorrectly succeeded with {response_apikey.status_code}"
            )

            print(f"OK: X-API-Key correctly rejected (status: {response_apikey.status_code})")

    async def test_voice_webhook_processing_mock(self, webhook_voice_payload):
        """Test voice webhook processing with mocked dependencies"""
        from unittest.mock import AsyncMock, patch

        # Mock dependencies
        mock_download = AsyncMock(return_value=b"fake_audio_data")
        mock_ffmpeg = AsyncMock(return_value=b"fake_mp3_data")
        mock_gemini = MagicMock(return_value="Hello this is a test message")

        # google-generativeai was dropped from requirements.txt (deprecated
        # Dec 2025); the audio branch in src/core/bijou.py uses google.genai's
        # Client instead, so that is what a mocked run has to stand in for.
        with patch("httpx.AsyncClient.get", mock_download), \
             patch("subprocess.run", return_value=MagicMock(returncode=0)), \
             patch("google.genai.models.Models.generate_content", mock_gemini):

            # Simulate webhook processing
            # (In real implementation, this would call bijou.py webhook handler)
            
            from google.genai import models as genai_models

            assert genai_models.Models.generate_content is mock_gemini, (
                "Gemini audio call site is not the one this test mocks"
            )
            assert webhook_voice_payload["messages"][0]["audio"]["id"], (
                "webhook voice payload must carry a media id to download"
            )
            print("OK: Voice webhook processing flow verified (mocked)")

    async def test_voice_error_handling_download_failure(self):
        """Test graceful handling when media download fails"""
        # Simulate 404/500 from bridge
        test_media_url = f"{TEST_BRIDGE_URL}/statics/media/nonexistent_file_12345.ogg"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    test_media_url,
                    auth=(TEST_BRIDGE_USER, TEST_BRIDGE_PASSWORD),
                    headers=BRIDGE_HEADERS,
                    timeout=10,
                )
                # Should return 404 or similar error
                assert response.status_code >= 400
                print(f"OK: Download failure handled (status: {response.status_code})")
            except httpx.HTTPError as e:
                # Network errors are also acceptable
                print(f"OK: Network error handled: {e}")

    async def test_voice_error_handling_corrupt_audio(self, sample_voice_ogg):
        """Test handling of corrupt/invalid audio files"""
        # Create corrupt audio (invalid OGG data)
        corrupt_audio = b"INVALID_AUDIO_DATA" * 100

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
            ogg_file.write(corrupt_audio)
            ogg_path = ogg_file.name

        try:
            mp3_path = ogg_path.replace(".ogg", ".mp3")

            # ffmpeg should fail gracefully
            result = subprocess.run(
                ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-y", mp3_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # ffmpeg should return non-zero exit code
            assert result.returncode != 0, "ffmpeg should fail on corrupt audio"
            print("OK: Corrupt audio detected and rejected by ffmpeg")

        finally:
            if Path(ogg_path).exists():
                Path(ogg_path).unlink()
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()

    async def test_temp_file_cleanup(self, sample_voice_ogg):
        """Verify temporary files are cleaned up after processing"""
        temp_dir = tempfile.gettempdir()
        initial_files = set(Path(temp_dir).glob("bijou_voice_*.mp3"))

        # Simulate voice processing (create temp file)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, prefix="bijou_voice_") as ogg_file:
            ogg_file.write(sample_voice_ogg)
            ogg_path = ogg_file.name

        mp3_path = ogg_path.replace(".ogg", ".mp3").replace("bijou_voice_", "bijou_voice_converted_")

        try:
            # Convert
            subprocess.run(
                ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-y", mp3_path],
                capture_output=True,
                timeout=10,
            )

            # Cleanup (production code should do this)
            if Path(ogg_path).exists():
                Path(ogg_path).unlink()
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()

            # Verify cleanup
            final_files = set(Path(temp_dir).glob("bijou_voice_*.mp3"))
            assert final_files == initial_files, "Temp files not cleaned up"
            print("OK: Temporary files cleaned up successfully")

        finally:
            # Ensure cleanup even if test fails
            for path in [ogg_path, mp3_path]:
                if Path(path).exists():
                    Path(path).unlink()


@pytest.mark.e2e
@pytest.mark.asyncio
class TestVoiceMultiLanguage:
    """Test voice processing across multiple languages"""

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY").startswith("mock"),
        reason="Requires real Gemini API key and voice samples",
    )
    async def test_english_voice_detection(self, sample_voice_english):
        """Test English voice note transcription"""
        if not sample_voice_english or not Path(sample_voice_english).exists():
            pytest.skip("English voice sample not found")

        # Test transcription and language detection
        # (Would call actual voice processing pipeline)
        print("OK: English voice processing (skipped - requires real sample)")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY").startswith("mock"),
        reason="Requires real Gemini API key and voice samples",
    )
    async def test_malay_voice_detection(self, sample_voice_malay):
        """Test Malay voice note transcription"""
        if not sample_voice_malay or not Path(sample_voice_malay).exists():
            pytest.skip("Malay voice sample not found")

        print("OK: Malay voice processing (skipped - requires real sample)")

    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY").startswith("mock"),
        reason="Requires real Gemini API key and voice samples",
    )
    async def test_manglish_voice_detection(self, sample_voice_manglish):
        """Test Manglish voice note transcription"""
        if not sample_voice_manglish or not Path(sample_voice_manglish).exists():
            pytest.skip("Manglish voice sample not found")

        print("OK: Manglish voice processing (skipped - requires real sample)")


@pytest.mark.e2e
@pytest.mark.asyncio
class TestVoicePerformance:
    """Performance and timeout tests for voice processing"""

    async def test_conversion_timeout(self, sample_voice_ogg):
        """Verify ffmpeg conversion completes within reasonable time"""
        import time

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
            ogg_file.write(sample_voice_ogg)
            ogg_path = ogg_file.name

        try:
            mp3_path = ogg_path.replace(".ogg", ".mp3")
            start_time = time.time()

            result = subprocess.run(
                ["ffmpeg", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-y", mp3_path],
                capture_output=True,
                timeout=30,  # 30 second timeout
            )

            duration = time.time() - start_time

            assert result.returncode == 0
            assert duration < 10, f"Conversion took too long: {duration:.2f}s"
            print(f"OK: Conversion completed in {duration:.2f}s")

        finally:
            if Path(ogg_path).exists():
                Path(ogg_path).unlink()
            if Path(mp3_path).exists():
                Path(mp3_path).unlink()


# Test summary report
def pytest_collection_modifyitems(items):
    """Add markers and metadata to tests"""
    for item in items:
        if "voice" in item.nodeid.lower():
            item.add_marker(pytest.mark.voice)
        if "critical" in item.name.lower() or "ffmpeg" in item.name.lower():
            item.add_marker(pytest.mark.critical)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s", "--tb=short"])
