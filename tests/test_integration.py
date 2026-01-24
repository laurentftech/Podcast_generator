"""Integration tests that hit the real APIs."""
import os
import pytest
import tempfile
from pathlib import Path
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if present
load_dotenv(Path(__file__).parent.parent / ".env")

from generate_podcast import generate, GeminiTTS, ElevenLabsTTS

# Short script for testing to minimize cost and time
TEST_SCRIPT = """
Host: This is a test.
Guest: Indeed it is.
"""

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_gemini_integration():
    """Test actual generation with Gemini API."""
    api_key = os.environ["GEMINI_API_KEY"]
    
    # Use a temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        output_path = tmp.name
    
    try:
        # Minimal settings for Gemini
        app_settings = {
            "tts_provider": "gemini",
            "speaker_voices": {
                "Host": "Puck",
                "Guest": "Charon"
            }
        }
        
        # Run generation
        try:
            result_path = generate(
                script_text=TEST_SCRIPT,
                app_settings=app_settings,
                output_filepath=output_path,
                api_key=api_key,
                status_callback=lambda msg: None # Silence output
            )
        except Exception as e:
            # Check for quota errors (429 / Resource Exhausted)
            error_msg = str(e)
            if "Quota Exceeded" in error_msg or "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                pytest.skip(f"Skipping test due to API Quota limit: {error_msg}")
            raise e
        
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

@pytest.mark.skipif(not os.environ.get("ELEVENLABS_API_KEY"), reason="ELEVENLABS_API_KEY not set")
def test_elevenlabs_integration():
    """Test actual generation with ElevenLabs API."""
    api_key = os.environ["ELEVENLABS_API_KEY"]
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        output_path = tmp.name
        
    try:
        # Minimal settings for ElevenLabs
        app_settings = {
            "tts_provider": "elevenlabs",
            "speaker_voices_elevenlabs": {
                "Host": "21m00Tcm4TlvDq8ikWAM", # Rachel
                "Guest": "AZnzlk1XvdvUeBnXmlld"  # Domi
            }
        }
        
        try:
            result_path = generate(
                script_text=TEST_SCRIPT,
                app_settings=app_settings,
                output_filepath=output_path,
                api_key=api_key,
                status_callback=lambda msg: None
            )
        except Exception as e:
            # Check for quota errors (429)
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                pytest.skip(f"Skipping test due to API Quota limit: {error_msg}")
            raise e
        
        assert os.path.exists(result_path)
        assert os.path.getsize(result_path) > 0
        
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
