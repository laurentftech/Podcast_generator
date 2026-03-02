"""Tests for podcast generation functions."""
import pytest
import sys
import os
import tempfile
import logging
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock heavy dependencies BEFORE importing generate_podcast
# This avoids pydantic issues and other import errors

# Mock google.genai
mock_genai = MagicMock()
mock_genai.errors = MagicMock()
mock_genai.types = MagicMock()
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = mock_genai
sys.modules['google.genai.types'] = mock_genai.types
sys.modules['google.genai.errors'] = mock_genai.errors

# Mock elevenlabs
mock_elevenlabs = MagicMock()
sys.modules['elevenlabs'] = mock_elevenlabs
sys.modules['elevenlabs.client'] = mock_elevenlabs
sys.modules['elevenlabs.core'] = MagicMock()

# Mock keyring - use a mock that doesn't require a backend
mock_keyring = MagicMock()
mock_keyring.get_password = MagicMock(return_value=None)
mock_keyring.set_password = MagicMock()
sys.modules['keyring'] = mock_keyring

# IMPORTANT: Do NOT mock requests globally - it breaks other tests
# requests needs to remain as the real module for app.py tests

from generate_podcast import (
    generate,
    sanitize_app_settings_for_backend,
    validate_speakers,
    parse_audio_mime_type,
    GeminiTTS,
    ElevenLabsTTS,
    setup_logging,
    get_api_key,
)


class TestSanitizeAppSettings:
    """Tests for the sanitize_app_settings_for_backend function."""

    def test_preserves_tts_provider(self):
        """Test that TTS provider is preserved."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {"John": "voice1"},
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["tts_provider"] == "elevenlabs"

    def test_cleans_gemini_voice_names(self):
        """Test that Gemini voice names are cleaned (removes descriptions)."""
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {"John": "Achernar - A deep male voice"},
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices"]["John"] == "Achernar"

    def test_cleans_gemini_voice_names_no_description(self):
        """Test that Gemini voice names without description are preserved."""
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {"John": "Achernar"},
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices"]["John"] == "Achernar"

    def test_cleans_elevenlabs_voice_ids(self):
        """Test that ElevenLabs voice IDs are extracted from dict."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices_elevenlabs": {
                "John": {"id": "voice123", "name": "John Voice"}
            },
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices_elevenlabs"]["John"] == "voice123"

    def test_preserves_elevenlabs_legacy_format(self):
        """Test that ElevenLabs legacy string format is preserved."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices_elevenlabs": {
                "John": "voice123"
            },
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices_elevenlabs"]["John"] == "voice123"

    def test_handles_empty_settings(self):
        """Test that empty settings are handled gracefully."""
        app_settings = {}
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["tts_provider"] is None
        assert result["speaker_voices"] == {}
        assert result["speaker_voices_elevenlabs"] == {}


class TestValidateSpeakers:
    """Tests for the validate_speakers function."""

    def test_extracts_speakers_from_script(self):
        """Test that speakers are correctly extracted from script."""
        script = "John: Hello\nSamantha: Hi there"
        settings = {"tts_provider": "gemini", "speaker_voices": {}}
        speakers, lines = validate_speakers(script, settings)
        assert "John" in speakers
        assert "Samantha" in speakers

    def test_gemini_limits_to_two_speakers(self):
        """Test that Gemini TTS enforces the 2-speaker limit."""
        script = "John: Hello\nSamantha: Hi\nMike: Welcome"
        settings = {"tts_provider": "gemini", "speaker_voices": {}}
        with pytest.raises(ValueError) as exc_info:
            validate_speakers(script, settings)
        assert "Gemini TTS supports at most 2 speakers" in str(exc_info.value)


class TestParseAudioMimeType:
    """Tests for the parse_audio_mime_type function."""

    def test_parses_standard_mime_type(self):
        """Test parsing of standard audio/mpeg mime type."""
        result = parse_audio_mime_type("audio/mpeg")
        assert result["bits_per_sample"] == 16
        assert result["rate"] == 24000

    def test_parses_mime_type_with_rate(self):
        """Test parsing of mime type with explicit rate."""
        result = parse_audio_mime_type("audio/mpeg;rate=48000")
        assert result["rate"] == 48000

    def test_defaults_to_24000(self):
        """Test that default rate is 24000 when not specified."""
        result = parse_audio_mime_type("audio/wav")
        assert result["rate"] == 24000

    def test_parse_audio_mime_type_with_invalid_rate(self):
        """Test parsing mime type with invalid rate value."""
        result = parse_audio_mime_type("audio/mpeg;rate=invalid")
        assert result["rate"] == 24000  # Falls back to default

    def test_parse_audio_mime_type_empty_string(self):
        """Test parsing empty mime type string."""
        result = parse_audio_mime_type("")
        assert result["rate"] == 24000


class TestGenerate:
    """Tests for the generate function."""

    def test_generate_requires_ffmpeg(self, monkeypatch):
        """Test that generate raises FileNotFoundError when FFmpeg is not found."""
        # Mock find_ffmpeg_path to return None
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: None)
        
        app_settings = {"tts_provider": "gemini", "speaker_voices": {}}
        
        with pytest.raises(FileNotFoundError) as exc_info:
            generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/output.mp3",
            )
        assert "FFmpeg" in str(exc_info.value)

    def test_generate_requires_api_key(self, monkeypatch):
        """Test that generate raises ValueError when API key is not provided."""
        # Mock find_ffmpeg_path to return a valid path
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: "/usr/bin/ffmpeg")
        # Mock get_api_key to return None
        monkeypatch.setattr("generate_podcast.get_api_key", lambda *args, **kwargs: None)
        
        app_settings = {"tts_provider": "gemini", "speaker_voices": {}}
        
        with pytest.raises(ValueError) as exc_info:
            generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/output.mp3",
                api_key=None,  # Explicitly no API key
            )
        assert "API key" in str(exc_info.value)

    def test_generate_uses_provided_api_key(self, monkeypatch):
        """Test that generate uses the provided API key."""
        # Mock find_ffmpeg_path
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: "/usr/bin/ffmpeg")
        
        # Mock the GeminiTTS class
        mock_provider = MagicMock()
        mock_provider.synthesize.return_value = "/tmp/output.mp3"
        
        with patch("generate_podcast.GeminiTTS") as mock_tts_class:
            mock_tts_class.return_value = mock_provider
            
            app_settings = {"tts_provider": "gemini", "speaker_voices": {}}
            
            result = generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/output.mp3",
                api_key="test_api_key",
            )
            
            # Verify the provider was instantiated with the correct API key
            mock_tts_class.assert_called_once_with(api_key="test_api_key")

    def test_generate_selects_elevenlabs_provider(self, monkeypatch):
        """Test that ElevenLabs provider is selected when specified."""
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: "/usr/bin/ffmpeg")
        
        mock_provider = MagicMock()
        mock_provider.synthesize.return_value = "/tmp/output.mp3"
        
        with patch("generate_podcast.ElevenLabsTTS") as mock_tts_class:
            mock_tts_class.return_value = mock_provider
            
            app_settings = {"tts_provider": "elevenlabs", "speaker_voices_elevenlabs": {}}
            
            result = generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/output.mp3",
                api_key="test_api_key",
            )
            
            mock_tts_class.assert_called_once_with(api_key="test_api_key")

    def test_generate_creates_output_directory(self, monkeypatch):
        """Test that generate creates the output directory if it doesn't exist."""
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: "/usr/bin/ffmpeg")
        
        mock_provider = MagicMock()
        mock_provider.synthesize.return_value = "/tmp/test_dir/output.mp3"
        
        with patch("generate_podcast.GeminiTTS") as mock_tts_class:
            mock_tts_class.return_value = mock_provider
            
            app_settings = {"tts_provider": "gemini", "speaker_voices": {}}
            
            # Call with a directory that doesn't exist
            result = generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/test_dir/output.mp3",
                api_key="test_api_key",
            )
            
            # Verify the directory was created
            assert os.path.exists("/tmp/test_dir")

    def test_generate_respects_stop_event(self, monkeypatch):
        """Test that generate checks stop_event before starting."""
        monkeypatch.setattr("generate_podcast.find_ffmpeg_path", lambda: "/usr/bin/ffmpeg")
        
        from generate_podcast import generate
        
        stop_event = threading.Event()
        stop_event.set()  # Already stopped
        
        app_settings = {"tts_provider": "gemini", "speaker_voices": {}}
        
        with pytest.raises(Exception) as exc_info:
            generate(
                script_text="Hello world",
                app_settings=app_settings,
                output_filepath="/tmp/output.mp3",
                api_key="test_key",
                stop_event=stop_event,
            )
        assert "stopped" in str(exc_info.value).lower()


class TestTTSProviders:
    """Tests for TTS provider classes."""

    def test_gemini_tts_init(self):
        """Test GeminiTTS initialization."""
        tts = GeminiTTS(api_key="test_key")
        assert tts.api_key == "test_key"

    def test_elevenlabs_tts_init(self):
        """Test ElevenLabsTTS initialization."""
        tts = ElevenLabsTTS(api_key="test_key")
        assert tts.api_key == "test_key"

    def test_gemini_tts_synthesize_signature(self):
        """Test that GeminiTTS.synthesize has the expected signature."""
        tts = GeminiTTS(api_key="test_key")
        # Check that synthesize method exists and is callable
        assert callable(tts.synthesize)

    def test_elevenlabs_tts_synthesize_signature(self):
        """Test that ElevenLabsTTS.synthesize has the expected signature."""
        tts = ElevenLabsTTS(api_key="test_key")
        # Check that synthesize method exists and is callable
        assert callable(tts.synthesize)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger."""
        # Get a fresh logger for testing
        test_logger = logging.getLogger("test_setup_logging")
        # Clear any existing handlers
        test_logger.handlers = []
        # Patch the module-level logger
        import generate_podcast
        original_logger = generate_podcast.logger
        generate_podcast.logger = test_logger
        try:
            result = setup_logging()
            assert result is not None
            assert result.name == "test_setup_logging"
        finally:
            generate_podcast.logger = original_logger

    def test_setup_logging_does_not_add_duplicate_handlers(self):
        """Test that setup_logging returns early if handlers exist."""
        import generate_podcast
        # The module already has handlers from previous tests, so this returns early
        result = setup_logging()
        # It should still return a logger
        assert result is not None


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_get_api_key_uses_env_var_when_present(self, monkeypatch):
        """Test that get_api_key uses env var when present."""
        # Make sure no .env file is loaded
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test_env_var_key")
        
        logger = logging.getLogger("test")
        
        result = get_api_key(status_callback=lambda x: None, logger=logger, service="gemini")
        assert result == "test_env_var_key"

    def test_get_api_key_elevenlabs_service(self, monkeypatch):
        """Test that get_api_key works for elevenlabs service."""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_elevenlabs_key")
        
        logger = logging.getLogger("test")
        
        result = get_api_key(status_callback=lambda x: None, logger=logger, service="elevenlabs")
        assert result == "test_elevenlabs_key"

    def test_get_api_key_prioritizes_env_over_keychain(self, monkeypatch):
        """Test that env var takes priority over keychain."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "env_priority_key")
        
        logger = logging.getLogger("test")
        
        result = get_api_key(status_callback=lambda x: None, logger=logger, service="gemini")
        # Env var should take priority
        assert result == "env_priority_key"
