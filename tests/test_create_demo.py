"""Tests for the create_demo module."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from create_demo import (
    normalize_word,
    similar,
    find_adjacent_timed_words,
    interpolate_missing_words,
    fix_word_timings,
    reconstruct_html_with_timing,
    create_word_mapping_whisperx
)

class TestDemoUtils:
    """Tests for utility functions in create_demo.py."""

    def test_normalize_word(self):
        """Test word normalization."""
        assert normalize_word("Hello") == "hello"
        assert normalize_word("World!") == "world"
        assert normalize_word("Café") == "cafe"
        assert normalize_word("It's") == "its"
        assert normalize_word("  Space  ") == "space"

    def test_similar(self):
        """Test word similarity check."""
        assert similar("hello", "hello") is True
        assert similar("hello", "helo") is True  # Close enough
        assert similar("hello", "world") is False
        assert similar("colour", "color") is True

    def test_find_adjacent_timed_words(self):
        """Test finding adjacent words with timing."""
        segments = [
            {'type': 'word', 'text': 'one', 'timing': {'start': 0, 'end': 1}},
            {'type': 'word', 'text': 'two'},  # No timing
            {'type': 'word', 'text': 'three', 'timing': {'start': 2, 'end': 3}},
        ]
        
        # Test for the middle word (index 1)
        prev_word, next_word = find_adjacent_timed_words(segments, 1)
        
        assert prev_word is not None
        assert prev_word['index'] == 0
        assert prev_word['timing']['end'] == 1
        
        assert next_word is not None
        assert next_word['index'] == 2
        assert next_word['timing']['start'] == 2

    def test_interpolate_missing_words(self):
        """Test interpolation of missing timings."""
        segments = [
            {'type': 'word', 'text': 'one', 'timing': {'start': 1.0, 'end': 2.0}, 'index': 0},
            {'type': 'word', 'text': 'two', 'index': 1},  # Missing timing
            {'type': 'word', 'text': 'three', 'timing': {'start': 4.0, 'end': 5.0}, 'index': 2},
        ]
        
        # Run interpolation
        result = interpolate_missing_words(segments)
        
        # The middle word should now have timing
        middle_word = result[1]
        assert 'timing' in middle_word
        
        # Based on current implementation logic:
        # Duration = (4.0 - 2.0) / (1 + 1) = 1.0
        # Start = 2.0 + (1 * 1.0) = 3.0
        # End = 3.0 + 1.0 = 4.0
        assert middle_word['timing']['start'] == 3.0
        assert middle_word['timing']['end'] == 4.0

    def test_fix_word_timings_inverted(self):
        """Test fixing inverted timings."""
        segments = [
            {'type': 'word', 'text': 'test', 'timing': {'start': 2.0, 'end': 1.0}}
        ]
        result = fix_word_timings(segments)
        assert result[0]['timing']['start'] == 1.0
        assert result[0]['timing']['end'] == 2.0

    def test_fix_word_timings_overlap(self):
        """Test fixing overlapping timings."""
        segments = [
            {'type': 'word', 'text': 'one', 'timing': {'start': 1.0, 'end': 2.5}},
            {'type': 'word', 'text': 'two', 'timing': {'start': 2.0, 'end': 3.0}}
        ]
        # Overlap is 0.5s (2.0 to 2.5)
        # Midpoint is (2.5 + 2.0) / 2 = 2.25
        
        result = fix_word_timings(segments)
        
        # Check that overlap is resolved (with gap)
        assert result[0]['timing']['end'] < result[1]['timing']['start']
        assert result[0]['timing']['end'] == pytest.approx(2.24, 0.01)
        assert result[1]['timing']['start'] == pytest.approx(2.26, 0.01)

    def test_reconstruct_html_with_timing(self):
        """Test HTML reconstruction."""
        segments = [
            {'type': 'speaker', 'text': 'John:'},
            {'type': 'word', 'text': 'Hello', 'timing': {'start': 0, 'end': 1}},
            {'type': 'text', 'text': ' '},
            {'type': 'word', 'text': 'world', 'timing': {'start': 1, 'end': 2}},
            {'type': 'text', 'text': '.'}
        ]
        
        html = reconstruct_html_with_timing(segments)
        
        assert "<strong>John:</strong>" in html
        assert '<span class="word" data-start="0" data-end="1"' in html
        assert '>Hello</span>' in html
        assert '>world</span>' in html
        assert " ." in html or ".</span>" not in html # Punctuation shouldn't be a span

    def test_create_word_mapping_whisperx_simple(self):
        """Test mapping simple text to whisperx results."""
        source_text = "Hello world"
        whisperx_result = {
            'segments': [{
                'words': [
                    {'word': 'Hello', 'start': 0.0, 'end': 0.5},
                    {'word': 'world', 'start': 0.6, 'end': 1.0}
                ]
            }]
        }
        
        segments = create_word_mapping_whisperx(source_text, whisperx_result)
        
        # Should have 2 word segments and 1 space segment
        word_segments = [s for s in segments if s['type'] == 'word']
        assert len(word_segments) == 2
        assert word_segments[0]['text'] == 'Hello'
        assert word_segments[0]['timing']['start'] == 0.0
        assert word_segments[1]['text'] == 'world'
        assert word_segments[1]['timing']['start'] == 0.6

    def test_create_word_mapping_whisperx_with_speaker(self):
        """Test mapping text with speaker labels."""
        source_text = "John: Hello"
        whisperx_result = {
            'segments': [{
                'words': [
                    {'word': 'Hello', 'start': 0.0, 'end': 0.5}
                ]
            }]
        }
        
        segments = create_word_mapping_whisperx(source_text, whisperx_result)
        
        # The regex captures the speaker name AND the following spaces
        assert segments[0]['type'] == 'speaker'
        assert segments[0]['text'] == 'John: '
        
        word_segments = [s for s in segments if s['type'] == 'word']
        assert len(word_segments) == 1
        assert word_segments[0]['text'] == 'Hello'
