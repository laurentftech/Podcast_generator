"""Tests for Flask API endpoints."""
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
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
        "speaker_voices": {
            "John": "Puck - A voice"
        },
        "speaker_voices_elevenlabs": {}
    }
    settings_file.write_text(json.dumps(default_settings))
    return default_settings


class TestAboutEndpoint:
    """Tests for /api/about endpoint."""

    def test_about_returns_version(self, client):
        """Test that /api/about returns version information."""
        response = client.get('/api/about')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'version' in data
        # Version should be a string
        assert isinstance(data['version'], str)


class TestSettingsEndpoints:
    """Tests for /api/settings endpoints (GET and POST)."""

    def test_get_settings(self, client, mock_settings, monkeypatch):
        """Test GET /api/settings returns current settings."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key_2")

        response = client.get('/api/settings')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['tts_provider'] == 'gemini'
        assert 'speaker_voices' in data
        assert data['has_gemini_key'] is True
        assert data['has_elevenlabs_key'] is True

    def test_get_settings_shows_missing_keys(self, client, mock_settings, monkeypatch):
        """Test that missing API keys are indicated."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        response = client.get('/api/settings')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['has_gemini_key'] is False
        assert data['has_elevenlabs_key'] is False

    def test_post_settings_updates_provider(self, client, temp_settings_dir):
        """Test POST /api/settings updates TTS provider."""
        # Create initial settings
        settings_file = temp_settings_dir / "settings.json"
        initial_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        settings_file.write_text(json.dumps(initial_settings))

        # Update to ElevenLabs
        new_settings = {"tts_provider": "elevenlabs"}
        response = client.post('/api/settings',
                              data=json.dumps(new_settings),
                              content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'

        # Verify settings were saved
        saved_settings = json.loads(settings_file.read_text())
        assert saved_settings['tts_provider'] == 'elevenlabs'

    def test_post_settings_updates_speaker_voices(self, client, temp_settings_dir):
        """Test POST /api/settings updates speaker voices."""
        settings_file = temp_settings_dir / "settings.json"
        initial_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        settings_file.write_text(json.dumps(initial_settings))

        new_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "John": "Puck - Male voice",
                "Sarah": "Charon - Female voice"
            }
        }
        response = client.post('/api/settings',
                              data=json.dumps(new_settings),
                              content_type='application/json')

        assert response.status_code == 200

        # Verify settings were saved
        saved_settings = json.loads(settings_file.read_text())
        assert "John" in saved_settings['speaker_voices']
        assert "Sarah" in saved_settings['speaker_voices']

    def test_post_settings_invalid_format(self, client, mock_settings):
        """Test POST /api/settings with invalid format."""
        response = client.post('/api/settings',
                              data="invalid json",
                              content_type='application/json')

        # Flask will return 400 for invalid JSON, but the response body might be empty
        # or contain HTML error page depending on Flask version
        assert response.status_code in [400, 500]

    def test_post_settings_strips_has_key_flags(self, client, temp_settings_dir):
        """Test that has_*_key flags are not saved to settings file."""
        settings_file = temp_settings_dir / "settings.json"
        initial_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {},
            "speaker_voices_elevenlabs": {}
        }
        settings_file.write_text(json.dumps(initial_settings))

        new_settings = {
            "tts_provider": "gemini",
            "has_gemini_key": True,  # Should be stripped
            "has_elevenlabs_key": False  # Should be stripped
        }
        response = client.post('/api/settings',
                              data=json.dumps(new_settings),
                              content_type='application/json')

        assert response.status_code == 200

        # Verify has_*_key flags were not saved
        saved_settings = json.loads(settings_file.read_text())
        assert 'has_gemini_key' not in saved_settings
        assert 'has_elevenlabs_key' not in saved_settings


class TestVoicesEndpoint:
    """Tests for /api/voices endpoint."""

    def test_voices_returns_gemini_voices(self, client, monkeypatch):
        """Test that /api/voices returns Gemini voices."""
        # Don't need to mock much since AVAILABLE_VOICES is imported from config
        response = client.get('/api/voices')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'gemini' in data
        assert isinstance(data['gemini'], dict)
        # Should have some voices (from config.py)
        assert len(data['gemini']) > 0

    def test_voices_returns_elevenlabs_when_key_set(self, client, monkeypatch):
        """Test that ElevenLabs voices are returned when API key is set."""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")

        # Mock the requests.get call that app.py uses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'voices': [
                {
                    'voice_id': 'voice123',
                    'name': 'Josh',
                    'preview_url': 'http://example.com/preview.mp3',
                    'labels': {'gender': 'male', 'age': 'young', 'accent': 'american', 'use_case': 'narration'},
                    'description': 'A deep male voice'
                }
            ]
        }

        with patch('app.requests.get', return_value=mock_response):
            response = client.get('/api/voices')
            assert response.status_code == 200

            data = json.loads(response.data)
            assert 'elevenlabs' in data
            assert isinstance(data['elevenlabs'], list)
            assert len(data['elevenlabs']) > 0
            # Check structure of first voice
            voice = data['elevenlabs'][0]
            assert 'voice_id' in voice
            assert 'name' in voice
            assert 'preview_url' in voice

    def test_voices_empty_elevenlabs_when_no_key(self, client, monkeypatch):
        """Test that ElevenLabs voices list is empty when no API key."""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        response = client.get('/api/voices')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'elevenlabs' in data
        assert data['elevenlabs'] == []

    def test_voices_handles_elevenlabs_error(self, client, monkeypatch):
        """Test that errors fetching ElevenLabs voices are handled gracefully."""
        import requests as req_module
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")

        # Mock requests.get to raise a RequestException (which the code catches)
        with patch('app.requests.get', side_effect=req_module.RequestException("API Error")):
            response = client.get('/api/voices')
            assert response.status_code == 200

            data = json.loads(response.data)
            # Should return empty list on error
            assert data['elevenlabs'] == []
