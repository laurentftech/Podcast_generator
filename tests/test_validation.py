"""Tests for script and speaker validation."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_podcast import validate_speakers


class TestValidateSpeakers:
    """Tests for the validate_speakers function."""

    def test_validate_all_speakers_configured(self):
        """Test validation when all speakers are properly configured."""
        script = "John: Hello\nSarah: Hi there"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert set(configured) == {"John", "Sarah"}

    def test_validate_missing_speakers(self):
        """Test validation when some speakers are missing from config."""
        script = "John: Hello\nSarah: Hi\nBob: Hey"
        settings = {
            "tts_provider": "elevenlabs",  # Use ElevenLabs to allow 3 speakers
            "speaker_voices_elevenlabs": {
                "John": "voice1"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert set(missing) == {"Bob", "Sarah"}
        assert configured == ["John"]

    def test_validate_empty_script(self):
        """Test validation with empty script."""
        script = ""
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {}
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert configured == []

    def test_validate_script_without_speakers(self):
        """Test validation with script that has no speaker format."""
        script = "This is just plain text\nNo speakers here"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {}
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert configured == []

    def test_validate_gemini_too_many_speakers(self):
        """Test that Gemini provider raises error with more than 2 speakers."""
        script = "John: Hi\nSarah: Hello\nBob: Hey"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon",
                "Bob": "Kore"
            }
        }
        with pytest.raises(ValueError) as exc_info:
            validate_speakers(script, settings)
        assert "Gemini TTS supports at most 2 speakers" in str(exc_info.value)
        assert "3 were found" in str(exc_info.value)

    def test_validate_gemini_two_speakers_allowed(self):
        """Test that Gemini provider allows exactly 2 speakers."""
        script = "John: Hello\nSarah: Hi there"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert len(configured) == 2

    def test_validate_gemini_one_speaker_allowed(self):
        """Test that Gemini provider allows 1 speaker."""
        script = "John: Hello there\nJohn: How are you?"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert configured == ["John"]

    def test_validate_elevenlabs_many_speakers(self):
        """Test that ElevenLabs provider allows multiple speakers."""
        script = "John: Hi\nSarah: Hello\nBob: Hey\nAlice: Greetings"
        settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices_elevenlabs": {
                "John": "voice1",
                "Sarah": "voice2",
                "Bob": "voice3",
                "Alice": "voice4"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert len(configured) == 4

    def test_validate_elevenlabs_uses_correct_settings_key(self):
        """Test that ElevenLabs validation uses speaker_voices_elevenlabs."""
        script = "John: Hello"
        settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {
                "John": "Puck"  # Wrong key for ElevenLabs
            },
            "speaker_voices_elevenlabs": {
                "Sarah": "voice1"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == ["John"]  # John not in speaker_voices_elevenlabs
        assert configured == []

    def test_validate_duplicate_speaker_names(self):
        """Test that duplicate speaker names in script are handled correctly."""
        script = "John: Hello\nJohn: How are you?\nJohn: Goodbye"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert configured == ["John"]  # Only listed once

    def test_validate_speaker_with_whitespace(self):
        """Test that speaker names with extra whitespace are trimmed."""
        script = " John : Hello\n  Sarah  : Hi"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert set(configured) == {"John", "Sarah"}

    def test_validate_multiline_dialogue(self):
        """Test that continuation lines don't create duplicate speakers."""
        script = """John: Hello there
this is a continuation
Sarah: Hi
and another continuation"""
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck",
                "Sarah": "Charon"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert missing == []
        assert set(configured) == {"John", "Sarah"}

    def test_validate_case_sensitive_speaker_names(self):
        """Test that speaker names are case-sensitive."""
        script = "john: Hello\nJohn: Hi"
        settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck"
            }
        }
        missing, configured = validate_speakers(script, settings)
        assert "john" in missing  # lowercase 'john' is not configured
        assert "John" in configured
