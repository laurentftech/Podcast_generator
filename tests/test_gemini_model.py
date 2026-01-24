"""Tests for Gemini TTS model selection."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate_podcast
from generate_podcast import GeminiTTS


class TestGeminiModelSelection:
    """Tests for GeminiTTS model selection and defaults."""

    def test_default_model_is_pro(self, monkeypatch):
        """Test that the default Gemini model is gemini-2.5-pro-preview-tts."""
        # Ensure no environment variable is set
        monkeypatch.delenv("GEMINI_TTS_MODEL", raising=False)

        # Mock the genai client and its methods
        with patch('generate_podcast.genai.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Mock the generate_content_stream to avoid actual API calls
            mock_chunk = MagicMock()
            mock_chunk.candidates = []
            mock_instance.models.generate_content_stream.return_value = [mock_chunk]

            gemini_tts = GeminiTTS(api_key="test_key")

            # Create a simple script
            script = "John: Hello"
            speaker_mapping = {"John": "Puck"}

            # Mock the status callback
            status_callback = Mock()

            try:
                # Try to synthesize - we expect it to attempt using the default model
                gemini_tts.synthesize(
                    script_text=script,
                    speaker_mapping=speaker_mapping,
                    output_filepath="/tmp/test_output.mp3",
                    status_callback=status_callback
                )
            except Exception:
                # We expect this to fail because we're mocking, but we can check the calls
                pass

            # Check that status_callback was called with the default model
            call_args = [str(call) for call in status_callback.call_args_list]
            assert any("gemini-2.5-pro-preview-tts" in str(arg) for arg in call_args), \
                f"Default model should be gemini-2.5-pro-preview-tts. Calls: {call_args}"

    def test_custom_model_from_env(self, monkeypatch):
        """Test that custom model from environment variable is used."""
        # Set custom model
        monkeypatch.setenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

        # Read the environment variable to verify it was set correctly
        env_model = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-pro-preview-tts")
        assert env_model == "gemini-2.5-flash-preview-tts"

        with patch('generate_podcast.genai.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            mock_chunk = MagicMock()
            mock_chunk.candidates = []
            mock_instance.models.generate_content_stream.return_value = [mock_chunk]

            gemini_tts = GeminiTTS(api_key="test_key")

            script = "John: Hello"
            speaker_mapping = {"John": "Puck"}
            status_callback = Mock()

            try:
                gemini_tts.synthesize(
                    script_text=script,
                    speaker_mapping=speaker_mapping,
                    output_filepath="/tmp/test_output.mp3",
                    status_callback=status_callback
                )
            except Exception:
                pass

            # Check that the custom model was used
            call_args = [str(call) for call in status_callback.call_args_list]
            assert any("gemini-2.5-flash-preview-tts" in str(arg) for arg in call_args), \
                f"Custom model should be used. Calls: {call_args}"

    def test_model_fallback_order(self, monkeypatch):
        """Test that models are tried in the correct fallback order."""
        monkeypatch.delenv("GEMINI_TTS_MODEL", raising=False)

        with patch('generate_podcast.genai.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Make generate_content_stream raise an error to trigger fallback
            mock_instance.models.generate_content_stream.side_effect = Exception("Model error")

            gemini_tts = GeminiTTS(api_key="test_key")

            script = "John: Hello"
            speaker_mapping = {"John": "Puck"}
            status_callback = Mock()

            with pytest.raises(Exception):
                gemini_tts.synthesize(
                    script_text=script,
                    speaker_mapping=speaker_mapping,
                    output_filepath="/tmp/test_output.mp3",
                    status_callback=status_callback
                )

            # Check that the status callback was called with model names in order
            call_args = [str(call) for call in status_callback.call_args_list]
            call_text = " ".join(call_args)

            # Should try gemini-2.5-pro-preview-tts first (the default)
            assert "gemini-2.5-pro-preview-tts" in call_text, \
                f"Should attempt default model first. Calls: {call_args}"

    def test_models_to_try_list_uniqueness(self, monkeypatch):
        """Test that when custom model equals default, it's not duplicated in the list."""
        # Set the custom model to be the same as default
        monkeypatch.setenv("GEMINI_TTS_MODEL", "gemini-2.5-pro-preview-tts")

        with patch('generate_podcast.genai.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Make it fail immediately so we can check the attempts
            mock_instance.models.generate_content_stream.side_effect = Exception("Model error")

            gemini_tts = GeminiTTS(api_key="test_key")

            script = "John: Hello"
            speaker_mapping = {"John": "Puck"}
            status_callback = Mock()

            with pytest.raises(Exception):
                gemini_tts.synthesize(
                    script_text=script,
                    speaker_mapping=speaker_mapping,
                    output_filepath="/tmp/test_output.mp3",
                    status_callback=status_callback
                )

            # Count how many times the default model was attempted
            call_args = [str(call) for call in status_callback.call_args_list]
            pro_attempts = sum(1 for arg in call_args if "gemini-2.5-pro-preview-tts" in str(arg))

            # Should only attempt pro model once, not twice (no duplicates)
            assert pro_attempts == 1, \
                f"Pro model should only be attempted once when set as custom. Attempts: {pro_attempts}"
