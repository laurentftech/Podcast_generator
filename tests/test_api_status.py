"""Tests for the /api/status endpoint."""
import os
import json
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import app as flask_app


@pytest.fixture
def app(temp_settings_dir):
    """Create Flask app for testing."""
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['WTF_CSRF_ENABLED'] = False
    return flask_app.app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_settings(temp_settings_dir):
    """Create mock settings file."""
    settings_file = temp_settings_dir / "settings.json"
    default_settings = {
        "tts_provider": "gemini",
        "speaker_voices": {},
        "speaker_voices_elevenlabs": {}
    }
    settings_file.write_text(json.dumps(default_settings))
    return default_settings


class TestAPIStatusEndpoint:
    """Tests for /api/status endpoint model display."""

    def test_status_returns_gemini_default_model(self, client, mock_settings, monkeypatch):
        """Test that /api/status returns the default Gemini model when no env var is set."""
        # Ensure GEMINI_TTS_MODEL is not set
        monkeypatch.delenv("GEMINI_TTS_MODEL", raising=False)

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['provider_name'] == 'Gemini'
        assert data['model_name'] == 'gemini-2.5-pro-preview-tts'
        assert data['quota_text'] is None

    def test_status_returns_gemini_custom_model(self, client, mock_settings, monkeypatch):
        """Test that /api/status returns custom Gemini model from environment variable."""
        # Set custom model
        monkeypatch.setenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['provider_name'] == 'Gemini'
        assert data['model_name'] == 'gemini-2.5-flash-preview-tts'

    def test_status_returns_elevenlabs_model(self, client, temp_settings_dir, monkeypatch):
        """Test that /api/status returns Eleven v3 for ElevenLabs provider."""
        # Create settings with ElevenLabs as provider
        settings_file = temp_settings_dir / "settings.json"
        settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        settings_file.write_text(json.dumps(settings))

        # Set API key to avoid error message
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")

        # Mock the quota update function
        with patch('app.update_elevenlabs_quota', return_value="Remaining: 10000 / 10000 characters"):
            response = client.get('/api/status')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['provider_name'] == 'ElevenLabs'
            assert data['model_name'] == 'Eleven v3'
            assert 'Remaining' in data['quota_text']

    def test_status_elevenlabs_without_api_key(self, client, temp_settings_dir, monkeypatch):
        """Test that /api/status handles missing ElevenLabs API key."""
        # Create settings with ElevenLabs as provider
        settings_file = temp_settings_dir / "settings.json"
        settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        settings_file.write_text(json.dumps(settings))

        # Ensure API key is not set
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        response = client.get('/api/status')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['provider_name'] == 'ElevenLabs'
        assert data['model_name'] == 'Eleven v3'
        assert data['quota_text'] == 'ElevenLabs API Key not set.'

    def test_status_with_different_gemini_models(self, client, mock_settings, monkeypatch):
        """Test that /api/status correctly reflects different Gemini model configurations."""
        test_models = [
            "gemini-2.5-pro-preview-tts",
            "gemini-2.5-flash-preview-tts",
            "gemini-experimental-tts"
        ]

        for model in test_models:
            monkeypatch.setenv("GEMINI_TTS_MODEL", model)

            response = client.get('/api/status')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data['model_name'] == model, f"Expected {model}, got {data['model_name']}"
