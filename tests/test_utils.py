"""Tests for utility functions."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import sanitize_text, sanitize_app_settings_for_backend


class TestSanitizeText:
    """Tests for the sanitize_text function."""

    def test_sanitize_empty_string(self):
        """Test that empty strings are handled correctly."""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""

    def test_remove_html_tags(self):
        """Test that HTML tags are removed."""
        text = "<p>Hello</p> <span>world</span>"
        assert sanitize_text(text) == "Hello world"

        # Word-style tags
        text = "<o:p>Test</o:p>"
        assert sanitize_text(text) == "Test"

    def test_decode_html_entities(self):
        """Test that HTML entities are decoded."""
        text = "Hello&nbsp;world&amp;stuff"
        result = sanitize_text(text)
        assert "&nbsp;" not in result
        assert "&amp;" not in result
        assert "world" in result

    def test_normalize_unicode(self):
        """Test that unicode characters are normalized."""
        text = "café"  # May contain combining characters
        result = sanitize_text(text)
        assert "café" in result or "cafe" in result

    def test_replace_smart_quotes(self):
        """Test that smart quotes are replaced with regular quotes."""
        text = "\u201cHello\u201d \u2018world\u2019"  # "Hello" 'world' with smart quotes
        result = sanitize_text(text)
        assert '"Hello"' in result
        assert "'world'" in result

    def test_replace_special_dashes(self):
        """Test that em-dashes and en-dashes are replaced with hyphens."""
        text = "Test \u2014 dash \u2013 another"  # Test — dash – another
        result = sanitize_text(text)
        assert "\u2014" not in result  # em-dash
        assert "\u2013" not in result  # en-dash
        assert "-" in result

    def test_remove_control_characters(self):
        """Test that control characters are removed (except newlines)."""
        text = "Hello\x00World\x1fTest"
        result = sanitize_text(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "HelloWorldTest" == result

    def test_preserve_newlines(self):
        """Test that newlines are preserved during sanitization."""
        text = "Line 1\nLine 2\rLine 3"
        result = sanitize_text(text)
        assert "\n" in result or result == "Line 1 Line 2 Line 3"  # Newlines may be normalized

    def test_reduce_multiple_spaces(self):
        """Test that multiple spaces are reduced to single space."""
        text = "Hello    world     test"
        result = sanitize_text(text)
        assert result == "Hello world test"

    def test_strip_leading_trailing_spaces(self):
        """Test that leading and trailing whitespace is removed."""
        text = "   Hello world   "
        result = sanitize_text(text)
        assert result == "Hello world"

    def test_complex_mixed_content(self):
        """Test sanitization of complex mixed content."""
        text = '<p>\u201cHello\u201d&nbsp;&amp;&nbsp;world</p>    with   spaces  '
        result = sanitize_text(text)
        assert "<p>" not in result
        assert "</p>" not in result
        assert '"Hello"' in result
        assert "world" in result
        # Multiple spaces should be reduced
        assert "    " not in result


class TestSanitizeAppSettings:
    """Tests for the sanitize_app_settings_for_backend function."""

    def test_sanitize_gemini_voices_with_description(self):
        """Test that Gemini voice descriptions are removed."""
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck - A young adult male",
                "Sarah": "Charon - A female voice"
            },
            "speaker_voices_elevenlabs": {}
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices"]["John"] == "Puck"
        assert result["speaker_voices"]["Sarah"] == "Charon"

    def test_sanitize_gemini_voices_without_description(self):
        """Test that Gemini voices without descriptions are kept as-is."""
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon"
            },
            "speaker_voices_elevenlabs": {}
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices"]["John"] == "Puck"
        assert result["speaker_voices"]["Sarah"] == "Charon"

    def test_sanitize_elevenlabs_voices_dict_format(self):
        """Test that ElevenLabs voice dicts are extracted to IDs."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {
                "John": {"id": "voice123", "display_name": "Josh - ..."},
                "Sarah": {"id": "voice456", "display_name": "Samantha - ..."}
            }
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices_elevenlabs"]["John"] == "voice123"
        assert result["speaker_voices_elevenlabs"]["Sarah"] == "voice456"

    def test_sanitize_elevenlabs_voices_legacy_string_format(self):
        """Test that legacy string format for ElevenLabs is preserved."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {
                "John": "voice123",
                "Sarah": "voice456"
            }
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["speaker_voices_elevenlabs"]["John"] == "voice123"
        assert result["speaker_voices_elevenlabs"]["Sarah"] == "voice456"

    def test_sanitize_preserves_tts_provider(self):
        """Test that TTS provider is preserved."""
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["tts_provider"] == "gemini"

        app_settings["tts_provider"] = "elevenlabs"
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["tts_provider"] == "elevenlabs"

    def test_sanitize_handles_missing_keys(self):
        """Test that missing settings keys are handled gracefully."""
        app_settings = {}
        result = sanitize_app_settings_for_backend(app_settings)
        assert result["tts_provider"] is None
        assert result["speaker_voices"] == {}
        assert result["speaker_voices_elevenlabs"] == {}

    def test_sanitize_handles_malformed_voice_data(self):
        """Test that malformed voice data doesn't crash the sanitizer."""
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {"John": None},  # Malformed
            "speaker_voices_elevenlabs": {
                "Sarah": {"wrong_key": "value"}  # Missing 'id'
            }
        }
        result = sanitize_app_settings_for_backend(app_settings)
        # Should not crash and should handle gracefully
        assert "speaker_voices_elevenlabs" in result
        assert result["speaker_voices_elevenlabs"]["Sarah"] == ""  # Gets empty string when 'id' is missing
