import os
import sys
import shutil
from typing import Optional, Dict, Any
import re
import unicodedata
from html import unescape

def get_asset_path(filename: str) -> Optional[str]:
    """
    Gets the absolute path to an asset, handling running from source and from
    a PyInstaller bundle.
    """
    if getattr(sys, 'frozen', False):
        # The application is frozen (packaged with PyInstaller)
        bundle_dir = sys._MEIPASS
    else:
        # The application is running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(bundle_dir, filename)
    return path if os.path.exists(path) else None


def get_app_data_dir() -> str:
    """Returns the standard application data directory path for the current OS."""
    app_name = "PodcastGenerator"
    if sys.platform == "darwin":  # macOS
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    elif sys.platform == "win32":  # Windows
        return os.path.join(os.environ['APPDATA'], app_name)
    else:  # Linux and others
        return os.path.join(os.path.expanduser('~'), '.config', app_name)


def _find_command_path(command: str) -> Optional[str]:
    """
    Finds the path to an executable.
    Searches the system PATH first, then common Homebrew locations.
    """
    # 1. Search in the system PATH (which will work if the PATH is correctly configured)
    path = shutil.which(command)
    if path:
        return path
    # 2. If not found, search in known Homebrew locations
    for brew_path in [f"/opt/homebrew/bin/{command}", f"/usr/local/bin/{command}"]:
        if os.path.exists(brew_path):
            return brew_path
    return None


def find_ffmpeg_path() -> Optional[str]:
    """Finds the path to the FFmpeg executable."""
    return _find_command_path("ffmpeg")


def find_ffplay_path() -> Optional[str]:
    """Finds the path to the ffplay executable."""
    return _find_command_path("ffplay")


def sanitize_text(text: str) -> str:
    if not text:
        return ""

    # 1️⃣ Enlève le HTML ou XML résiduel (ex : <p>, <o:p> de Word)
    text = re.sub(r"<[^>]+>", " ", text)

    # 2️⃣ Décode les entités HTML (ex: &nbsp;, &amp;)
    text = unescape(text)

    # 3️⃣ Normalise les caractères unicode (accents, quotes, symboles)
    text = unicodedata.normalize("NFKC", text)

    # 4️⃣ Remplace les espaces insécables et similaires par des espaces normaux,
    # mais préserve les retours à la ligne.
    text = re.sub(r"[\u00A0\u2000-\u200B\u202F\u205F\u3000]", " ", text)

    # 5️⃣ Supprime les caractères de contrôle invisibles, mais préserve les retours à la ligne.
    # [\x00-\x1f\x7f-\x9f] sont les caractères de contrôle.
    # Nous voulons exclure \n (LF, U+000A) et \r (CR, U+000D) de cette suppression.
    text = re.sub(r"[\x00-\x09\x0B-\x0C\x0E-\x1f\x7f-\x9f]", "", text)


    # 6️⃣ Remplace les guillemets Word “smart quotes” par des guillemets simples
    text = text.translate(str.maketrans({
        "“": '"', "”": '"',
        "‘": "'", "’": "'",
        "–": "-", "—": "-", "•": "-"
    }))

    # 7️⃣ Réduit les espaces multiples (mais pas les retours à la ligne)
    # et supprime les espaces en début/fin de chaîne.
    text = re.sub(r"[ \t]+", " ", text) # Replace multiple spaces/tabs with single space

    return text.strip() # Apply strip at the very end to clean leading/trailing spaces/newlines


def sanitize_app_settings_for_backend(app_settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a "clean" version of app_settings suitable for the backend.
    - Flattens ElevenLabs voice data to only include the voice ID.
    - Cleans Gemini voice names by removing descriptions.
    """
    app_settings_clean = {
        "tts_provider": app_settings.get("tts_provider"),
        "speaker_voices": app_settings.get("speaker_voices", {})
    }

    # Clean Gemini voices: convert "Name - Desc" -> "Name"
    gemini_clean = {}
    try:
        for speaker, voice in app_settings_clean.get("speaker_voices", {}).items():
            if isinstance(voice, str) and " - " in voice:
                gemini_clean[speaker] = voice.split(" - ", 1)[0].strip()
            else:
                gemini_clean[speaker] = voice
    except Exception:
        gemini_clean = app_settings_clean.get("speaker_voices", {})
    app_settings_clean["speaker_voices"] = gemini_clean

    # Clean ElevenLabs voices: extract just the ID
    elevenlabs_mapping_clean = {}
    elevenlabs_mapping_raw = app_settings.get("speaker_voices_elevenlabs", {})
    for speaker, data in elevenlabs_mapping_raw.items():
        if isinstance(data, dict):
            elevenlabs_mapping_clean[speaker] = data.get('id', '')
        else:
            # Legacy format: use the string as-is
            elevenlabs_mapping_clean[speaker] = data

    app_settings_clean["speaker_voices_elevenlabs"] = elevenlabs_mapping_clean
    return app_settings_clean