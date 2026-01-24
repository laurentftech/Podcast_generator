"""Extra tests for utils.py."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import sanitize_text, sanitize_app_settings_for_backend

class TestUtilsExtra:
    """Tests for utility functions."""

    def test_sanitize_text_html_entities(self):
        """Test decoding of HTML entities."""
        assert sanitize_text("Hello &amp; World") == "Hello & World"
        assert sanitize_text("It&apos;s me") == "It's me"

    def test_sanitize_text_smart_quotes(self):
        """Test replacement of smart quotes."""
        assert sanitize_text("“Hello”") == '"Hello"'
        assert sanitize_text("‘World’") == "'World'"

    def test_sanitize_text_control_chars(self):
        """Test removal of control characters but keeping newlines."""
        text = "Line 1\nLine 2\x00"
        assert sanitize_text(text) == "Line 1\nLine 2"

    def test_sanitize_text_html_tags(self):
        """Test removal of HTML tags."""
        assert sanitize_text("<p>Hello</p>") == "Hello"
        assert sanitize_text("<b>Bold</b>") == "Bold"

    def test_sanitize_app_settings_gemini(self):
        """Test sanitization of Gemini voice names."""
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck - A voice",
                "Sarah": "Charon"
            }
        }
        clean = sanitize_app_settings_for_backend(settings)
        assert clean["speaker_voices"]["John"] == "Puck"
        assert clean["speaker_voices"]["Sarah"] == "Charon"

    def test_sanitize_app_settings_elevenlabs(self):
        """Test sanitization of ElevenLabs voice objects."""
        settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices_elevenlabs": {
                "John": {"id": "voice123", "name": "My Voice"},
                "Sarah": "voice456"  # Legacy string format
            }
        }
        clean = sanitize_app_settings_for_backend(settings)
        assert clean["speaker_voices_elevenlabs"]["John"] == "voice123"
        assert clean["speaker_voices_elevenlabs"]["Sarah"] == "voice456"
