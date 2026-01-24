"""Tests for filename extraction from scripts."""
import pytest
import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import extract_filename_from_script


class TestExtractFilename:
    """Tests for the extract_filename_from_script function."""

    def test_extract_from_simple_dialogue(self):
        """Test extracting filename from simple speaker dialogue."""
        script = "John: Hello world, how are you?"
        filename = extract_filename_from_script(script, "mp3")
        assert filename == "Hello_world_how_are_you.mp3"

    def test_extract_skips_instruction_lines(self):
        """Test that instruction lines (without speaker format) are skipped."""
        script = """This is an instruction line
Another instruction
John: This should be the filename"""
        filename = extract_filename_from_script(script, "mp3")
        assert "This_should_be_the_filename" in filename

    def test_extract_uses_first_dialogue_line(self):
        """Test that only the first dialogue line is used."""
        script = "John: First dialogue\nSarah: Second dialogue"
        filename = extract_filename_from_script(script, "mp3")
        assert "First_dialogue" in filename
        assert "Second" not in filename

    def test_extract_removes_bracketed_annotations(self):
        """Test that bracketed annotations like [playful] are removed."""
        script = "John: [playful] Hello there [laughing] friend"
        filename = extract_filename_from_script(script, "mp3")
        assert "[playful]" not in filename
        assert "[laughing]" not in filename
        assert "Hello_there_friend" in filename

    def test_extract_limits_to_first_sentence(self):
        """Test that only the first sentence is used."""
        script = "John: Hello world. This is the second sentence. And a third."
        filename = extract_filename_from_script(script, "mp3")
        assert "Hello_world" in filename
        assert "second" not in filename.lower()

    def test_extract_respects_max_length(self):
        """Test that filename respects max_length parameter."""
        script = "John: This is a very long dialogue that should be truncated"
        filename = extract_filename_from_script(script, "mp3", max_length=20)
        # Extract just the name part without extension
        name_part = filename.replace(".mp3", "")
        assert len(name_part) <= 20

    def test_extract_removes_unsafe_characters(self):
        """Test that unsafe filename characters are removed."""
        script = "John: Hello/world\\test:file*name?"
        filename = extract_filename_from_script(script, "mp3")
        # Should not contain any of these characters
        unsafe_chars = ['/', '\\', ':', '*', '?', '<', '>', '|', '"']
        for char in unsafe_chars:
            assert char not in filename

    def test_extract_replaces_spaces_with_underscores(self):
        """Test that spaces are replaced with underscores."""
        script = "John: Hello world test"
        filename = extract_filename_from_script(script, "mp3")
        assert " " not in filename
        assert "Hello_world_test" in filename

    def test_extract_replaces_multiple_spaces(self):
        """Test that multiple spaces/hyphens become single underscore."""
        script = "John: Hello    world   ---   test"
        filename = extract_filename_from_script(script, "mp3")
        assert "___" not in filename  # Multiple underscores should be collapsed
        assert filename == "Hello_world_test.mp3"

    def test_extract_strips_leading_trailing_underscores(self):
        """Test that leading and trailing underscores are removed."""
        script = "John: ---Hello world---"
        filename = extract_filename_from_script(script, "mp3")
        assert not filename.startswith("_")
        assert not filename.endswith("_.mp3")

    def test_extract_fallback_for_empty_script(self):
        """Test that a UUID-based filename is used for empty script."""
        script = ""
        filename = extract_filename_from_script(script, "mp3")
        assert filename.startswith("podcast_")
        assert filename.endswith(".mp3")
        # Should contain hex characters
        assert re.match(r"podcast_[0-9a-f]{8}\.mp3", filename)

    def test_extract_fallback_for_no_dialogue(self):
        """Test fallback when script has no dialogue lines."""
        script = "Just some plain text\nNo speakers here"
        filename = extract_filename_from_script(script, "mp3")
        assert filename.startswith("podcast_")
        assert filename.endswith(".mp3")

    def test_extract_fallback_for_only_special_characters(self):
        """Test fallback when dialogue contains only special characters."""
        script = "John: !!!???***"
        filename = extract_filename_from_script(script, "mp3")
        assert filename.startswith("podcast_")
        assert filename.endswith(".mp3")

    def test_extract_different_extensions(self):
        """Test that different file extensions work correctly."""
        script = "John: Hello world"

        filename_mp3 = extract_filename_from_script(script, "mp3")
        assert filename_mp3.endswith(".mp3")

        filename_docx = extract_filename_from_script(script, "docx")
        assert filename_docx.endswith(".docx")

        filename_wav = extract_filename_from_script(script, "wav")
        assert filename_wav.endswith(".wav")

    def test_extract_with_question_mark_punctuation(self):
        """Test extraction with question mark as sentence ending."""
        script = "John: How are you? I am fine."
        filename = extract_filename_from_script(script, "mp3")
        assert "How_are_you" in filename
        assert "fine" not in filename

    def test_extract_with_exclamation_punctuation(self):
        """Test extraction with exclamation mark as sentence ending."""
        script = "John: Hello there! Welcome to the show."
        filename = extract_filename_from_script(script, "mp3")
        assert "Hello_there" in filename
        assert "Welcome" not in filename

    def test_extract_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        script = "John: Test123 with numbers 456"
        filename = extract_filename_from_script(script, "mp3")
        assert "Test123_with_numbers_456" in filename

    def test_extract_handles_unicode_characters(self):
        """Test handling of unicode characters in dialogue."""
        script = "John: Café français"
        filename = extract_filename_from_script(script, "mp3")
        # Unicode characters should be preserved if safe, or removed
        assert ".mp3" in filename

    def test_extract_with_empty_speaker_dialogue(self):
        """Test with a speaker line that has empty dialogue after colon."""
        script = "John:    \nSarah: Hello world"
        filename = extract_filename_from_script(script, "mp3")
        # Should skip John's empty line and use Sarah's
        assert "Hello_world" in filename

    def test_extract_with_malformed_brackets(self):
        """Test that malformed brackets are handled gracefully."""
        script = "John: Hello [world there"
        filename = extract_filename_from_script(script, "mp3")
        # Should handle gracefully without crashing
        assert ".mp3" in filename
