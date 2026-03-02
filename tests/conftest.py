"""Pytest configuration and fixtures for Podcast Generator tests."""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


# Mock keyring BEFORE any test runs to avoid NoKeyringError in CI
# This must be done at module import time, before generate_podcast is imported
mock_keyring = MagicMock()
mock_keyring.get_password = MagicMock(return_value=None)
mock_keyring.set_password = MagicMock()
sys.modules['keyring'] = mock_keyring


@pytest.fixture(autouse=True)
def mock_keyring_fixture(monkeypatch):
    """Ensure keyring is mocked for all tests."""
    import keyring
    if not isinstance(keyring, MagicMock):
        monkeypatch.setattr(keyring, 'get_password', MagicMock(return_value=None))
        monkeypatch.setattr(keyring, 'set_password', MagicMock())


@pytest.fixture
def temp_settings_dir(monkeypatch, tmp_path):
    """Create a temporary directory for settings during tests."""
    settings_dir = tmp_path / "test_settings"
    settings_dir.mkdir()

    # Mock the get_app_data_dir function to use temp directory
    # We need to mock it in both utils and app modules
    import utils
    import app as flask_app

    def mock_get_app_data_dir():
        return str(settings_dir)

    monkeypatch.setattr(utils, 'get_app_data_dir', mock_get_app_data_dir)
    monkeypatch.setattr(flask_app, 'get_app_data_dir', mock_get_app_data_dir)

    return settings_dir


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables before each test."""
    # Remove API keys and model settings
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_TTS_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_ANALYSIS_MODEL", raising=False)
