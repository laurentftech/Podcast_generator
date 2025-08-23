import argparse
import webbrowser
import sys
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from elevenlabs.client import ElevenLabs
import os
import shutil
import subprocess
import logging
from typing import Optional

import json
import keyring # For secure credential storage
# Import tools for dialog boxes
import tkinter as tk
from tkinter import simpledialog

import tempfile
import re
from typing import Any, Dict, List, Tuple
import requests
from datetime import datetime

# Global logger instance - initialized once when module is imported
logger = logging.getLogger(__name__)

# The podcast script is now a constant to be used by the console mode.
PODCAST_SCRIPT = """Read aloud in a warm, welcoming tone
John: [playful] Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs – my dogs' names are corgis! Who am I??
Samantha: [laughing] You're queen Elizabeth II!!
"""

class WelcomeDialog(tk.Toplevel):
    """A custom dialog window to welcome the user and provide a clickable link."""
    def __init__(self, parent, service: str = "gemini"):
        super().__init__(parent)
        self.title("Welcome!")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        main_frame = tk.Frame(self, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Welcome to Podcast Generator!", font=('Helvetica', 12, 'bold')).pack(pady=(0, 10))
        if service == "elevenlabs":
            tk.Label(main_frame, text="To get started, the application needs your ElevenLabs API key.").pack(pady=(0, 10))
            link_frame = tk.Frame(main_frame)
            link_frame.pack(pady=(0, 15))
            tk.Label(link_frame, text="You can get a key at:").pack(side=tk.LEFT)
            link_label = tk.Label(link_frame, text="elevenlabs.io", fg="blue", cursor="hand2")
            link_label.pack(side=tk.LEFT, padx=5)
            link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://elevenlabs.io"))
        else:
            tk.Label(main_frame, text="To get started, the application needs your Google Gemini API key.").pack(pady=(0, 10))
            link_frame = tk.Frame(main_frame)
            link_frame.pack(pady=(0, 15))
            tk.Label(link_frame, text="You can get a free key at:").pack(side=tk.LEFT)
            link_label = tk.Label(link_frame, text="ai.google.dev/gemini-api", fg="blue", cursor="hand2")
            link_label.pack(side=tk.LEFT, padx=5)
            link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://ai.google.dev/gemini-api"))

        ok_button = tk.Button(main_frame, text="OK", command=self.destroy, width=10)
        ok_button.pack(pady=(10, 0))

        self.bind('<Return>', lambda event: ok_button.invoke())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

def setup_logging() -> logging.Logger:
    """Configures logging to write to a file in the application's data directory."""
    if logger.hasHandlers(): # Avoids adding duplicate handlers
        return logger

    log_dir = get_app_data_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, 'w', 'utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

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

def get_api_key(status_callback, logger: logging.Logger, parent_window=None, service: str = "gemini") -> Optional[str]:
    """
    Finds the API key securely for a given service ("gemini" or "elevenlabs").
    1. (Developer) Looks for a local .env file (GEMINI_API_KEY / ELEVENLABS_API_KEY).
    2. (User) Looks for the key in the system keychain.
    3. (Migration) Looks for an old, insecure .env file and migrates it to the keychain.
    4. (First launch) Asks the user for the key and saves it to the keychain.
    """
    SERVICE_NAME = "PodcastGenerator"
    if service == "elevenlabs":
        ACCOUNT_NAME = "elevenlabs_api_key"
        ENV_VAR = "ELEVENLABS_API_KEY"
        welcome_service = "elevenlabs"
        prompt_title = "ElevenLabs API Key Required"
        prompt_text = "Please paste your ElevenLabs API key:"
    else:
        ACCOUNT_NAME = "gemini_api_key"
        ENV_VAR = "GEMINI_API_KEY"
        welcome_service = "gemini"
        prompt_title = "API Key Required"
        prompt_text = "Please paste your Google Gemini API key:"

    logger.info("="*20)
    logger.info(f"Starting API key search for service '{service}'...")

    # --- 1. For developers: priority to local .env file ---
    if not getattr(sys, 'frozen', False):
        dev_dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(dev_dotenv_path):
            logger.info(f"Development .env file found. Using this key if present.")
            load_dotenv(dotenv_path=dev_dotenv_path)
            dev_key = os.environ.get(ENV_VAR)
            if dev_key:
                return dev_key

    # --- 2. For users: search in the secure keychain ---
    api_key = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    if api_key:
        logger.info("API key found in the secure system keychain.")
        return api_key

    # --- 3. Migration from an old, insecure .env file ---
    app_data_dir = get_app_data_dir()
    old_dotenv_path = os.path.join(app_data_dir, '.env')
    if os.path.exists(old_dotenv_path):
        logger.info(f"Old .env file found at {old_dotenv_path}. Attempting migration.")
        load_dotenv(dotenv_path=old_dotenv_path)
        old_key = os.environ.get(ENV_VAR)
        if old_key:
            logger.info("Key found in old .env. Saving to keychain and deleting the old file.")
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, old_key)
            try:
                os.remove(old_dotenv_path)
                logger.info(f"Old insecure .env file deleted.")
            except OSError as e:
                logger.error(f"Could not delete old .env file: {e}")
            return old_key

    # --- 4. If the key is still not found, ask the user ---
    if not api_key:
        logger.info("API key not found, opening dialog for user.")
        status_callback("API key not found or invalid. Opening dialog...")

        # Manages the parent window for dialogs.
        # If none is provided (CLI mode), a temporary one is created.
        dialog_parent = parent_window
        we_created_root = False
        if dialog_parent is None:
            dialog_parent = tk.Tk()
            dialog_parent.withdraw()
            we_created_root = True

        # Temporarily de-iconify the parent if it exists and is withdrawn,
        # to ensure our dialogs are visible.
        parent_was_withdrawn = False
        if parent_window and parent_window.winfo_exists() and parent_window.state() == 'withdrawn':
            parent_window.deiconify()
            parent_was_withdrawn = True

        welcome_dialog = WelcomeDialog(dialog_parent, service=welcome_service)
        dialog_parent.wait_window(welcome_dialog)

        api_key_input = simpledialog.askstring(
            prompt_title,
            prompt_text,
            parent=dialog_parent
        )

        # Re-withdraw the parent if we temporarily showed it
        if parent_was_withdrawn:
            parent_window.withdraw()

        if we_created_root:
            dialog_parent.destroy()

        if api_key_input:
            logger.info("User provided an API key.")
            api_key = api_key_input
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key_input)
            logger.info(f"New key saved to the secure system keychain.")
            status_callback("API key saved securely for future launches.")
        else:
            logger.info("User cancelled API key entry.")
            status_callback("No API key provided. Cancelling.")
            return None

    logger.info("API key search finished.")
    return api_key

# --- Abstraction des fournisseurs TTS ---

class TTSProvider:
    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print) -> Optional[str]:
        raise NotImplementedError

class GeminiTTS(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print) -> Optional[str]:
        logger = logging.getLogger("PodcastGenerator")
        client = genai.Client(api_key=self.api_key)

        # Gemini expects annotations in parentheses, so we convert them from the script's square bracket format.
        gemini_script = script_text.replace('[', '(').replace(']', ')')
        logger.info("Converted script annotations from [] to () for Gemini.")

        models_to_try = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=gemini_script)],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker=speaker_name,
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                            ),
                        )
                        for speaker_name, voice_name in speaker_mapping.items()
                    ]
                ),
            ),
        )

        generated_successfully = False
        final_mime_type = ""
        audio_chunks = []

        for model_name in models_to_try:
            status_callback(f"\nAttempting generation with model: {model_name}...")
            try:
                audio_chunks = []
                final_mime_type = ""
                for chunk in client.models.generate_content_stream(
                    model=model_name,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if (
                        chunk.candidates is None
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                    ):
                        continue

                    part = chunk.candidates[0].content.parts[0]
                    if part.inline_data and part.inline_data.data:
                        audio_chunks.append(part.inline_data.data)
                        if not final_mime_type:
                            final_mime_type = part.inline_data.mime_type
                    else:
                        status_callback(chunk.text)

                if not audio_chunks:
                    raise errors.GoogleAPICallError("No audio data was generated by the model.")

                generated_successfully = True
                status_callback(f"Audio generated successfully via {model_name}.")
                break
            except errors.APIError as e:
                status_callback(f"API error with model '{model_name}'")
                status_callback("Trying next model...")
                logger.warning(f"API error with model '{model_name}': {e}")
            except Exception as e:
                status_callback(f"An unexpected critical error occurred: {e}")
                status_callback(traceback.format_exc())
                logger.error(f"Unexpected critical error: {e}\n{traceback.format_exc()}")
                generated_successfully = False
                break

        if not generated_successfully:
            return None

        # Convertir avec FFmpeg
        return _ffmpeg_convert_inline_audio_chunks(audio_chunks, final_mime_type, output_filepath, status_callback)

# Updated ElevenLabsTTS class for v3 API integration
# Replace the existing ElevenLabsTTS class in generate_podcast.py

class ElevenLabsTTS:
    """
    ElevenLabs TTS provider using v3 API.
    Supports conversational mode and individual segments.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)
        self.logger = logging.getLogger("PodcastGenerator")

    def synthesize(self, script_text: str, speaker_mapping: Dict[str, str], output_filepath: str, status_callback=print) -> Optional[str]:
        """
        Main entry: generates audio from script_text and saves to output_filepath.
        Uses the v3 text_to_dialogue endpoint to generate the entire conversation at once.
        """
        segments = self._parse_script_segments(script_text)
        if not segments:
            status_callback("[ElevenLabs] No segments found in script.")
            return None

        dialogue_inputs = []
        for idx, (speaker, text) in enumerate(segments, start=1):
            voice_id = speaker_mapping.get(speaker, "")
            if not voice_id:
                status_callback(f"[ElevenLabs] No voice mapped for '{speaker}', skipping segment {idx}.")
                continue
            dialogue_inputs.append({"text": text, "voice_id": voice_id})

        if not dialogue_inputs:
            status_callback("[ElevenLabs] No valid dialogue segments to generate.")
            return None

        status_callback("[ElevenLabs] Generating full dialogue...")
        try:
            audio_generator = self.client.text_to_dialogue.convert(
                inputs=dialogue_inputs
            )

            # The API returns MP3 audio. We need to handle the output format.
            output_ext = os.path.splitext(output_filepath)[1].lower()
            if output_ext not in [".mp3", ".wav"]:
                status_callback(f"Unsupported file format: '{output_ext}'. Defaulting to '.mp3'.")
                self.logger.warning(f"Unsupported file format: '{output_ext}'. Defaulting to '.mp3'.")
                output_filepath = os.path.splitext(output_filepath)[0] + ".mp3"
                output_ext = ".mp3"

            # If the requested format is MP3, we can stream directly to the file.
            if output_ext == ".mp3":
                with open(output_filepath, "wb") as f:
                    for chunk in audio_generator:
                        f.write(chunk)
                status_callback(f"File saved successfully: {output_filepath}")
                return output_filepath

            # If another format (like WAV) is requested, we need FFmpeg for conversion.
            else:
                ffmpeg_path = find_ffmpeg_path()
                if not ffmpeg_path:
                    status_callback("FFmpeg not found. Cannot convert to WAV. Please install FFmpeg.")
                    return None

                command = [ffmpeg_path, "-y", "-i", "pipe:0", output_filepath]
                status_callback(f"Converting with FFmpeg to {os.path.basename(output_filepath)}...")
                full_audio_data = b"".join(audio_generator)

                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

                process = subprocess.run(command, input=full_audio_data, capture_output=True, check=False, creationflags=creation_flags)
                if process.returncode != 0:
                    ffmpeg_error = process.stderr.decode('utf-8', errors='ignore')
                    self.logger.error(f"FFmpeg error during ElevenLabs conversion:\n{ffmpeg_error}")
                    status_callback("--- ERROR DURING AUDIO CONVERSION ---")
                    if ffmpeg_error.strip():
                        status_callback(f"FFmpeg error detail: {ffmpeg_error.strip().splitlines()[-1]}")
                    return None

                status_callback(f"File saved successfully: {output_filepath}")
                return output_filepath

        except Exception as e:
            status_callback(f"[ElevenLabs] Critical error during dialogue generation: {e}")
            self.logger.error(f"ElevenLabs dialogue generation error: {e}", exc_info=True)
            return None

    def _parse_script_segments(self, script_text: str) -> List[Tuple[Optional[str], str]]:
        """
        Parse script into (speaker, text) segments.
        """
        segments = []
        for raw_line in script_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            m = re.match(r"^([^:]+):\s*(.+)$", line)
            if not m:
                # This line is not a dialog line (e.g., an instruction).
                # Gemini uses it, but for ElevenLabs we must skip it.
                self.logger.info(f"Skipping non-dialogue line for ElevenLabs: '{line}'")
                continue
            speaker = m.group(1).strip()
            text = m.group(2).strip()
            text = re.sub(r"<[^>]+>", "", text).strip()  # remove tags like <cheerfully>
            if text: # Only add segment if there is text left to speak
                segments.append((speaker, text))
        return segments


# Additional helper function to update the quota fetching for v3
def update_elevenlabs_quota(api_key: str, status_callback=print) -> Optional[str]:
    """
    Fetches the character quota from the ElevenLabs v1 API.
    Returns a formatted quota string or None if unavailable.
    """
    try:
        headers = {"xi-api-key": api_key}
        resp = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        sub = data.get("subscription", {})
        used = sub.get("character_count")
        limit = sub.get("character_limit")
        
        if isinstance(used, int) and isinstance(limit, int) and limit > 0:
            remaining = max(0, limit - used)
            return f"TTS Provider: ElevenLabs v3 - Remaining: {remaining} / {limit} characters"
        else:
            return "TTS Provider: ElevenLabs v3 - Quota info missing"
            
    except Exception as e:
        status_callback(f"Error fetching ElevenLabs quota: {e}")
        return "TTS Provider: ElevenLabs v3 - Network error"

def _ffmpeg_convert_inline_audio_chunks(audio_chunks: List[bytes], mime_type: str, output_filepath: str, status_callback=print) -> Optional[str]:
    """Convert inline PCM chunks to requested output via FFmpeg."""
    ffmpeg_path = find_ffmpeg_path()
    logger = logging.getLogger("PodcastGenerator")

    if not ffmpeg_path:
        status_callback("--- CRITICAL ERROR ---")
        status_callback("The FFmpeg executable was not found on this system.")
        status_callback("Please install it and try again.")
        logger.error("FFmpeg was not found in the PATH or Homebrew locations.")
        return None

    # Build input bytes
    full_audio_data = b"".join(audio_chunks)
    output_format = os.path.splitext(output_filepath)[1].lower().strip('.')
    if output_format not in ["wav", "mp3"]:
        status_callback(f"Unsupported file format: {output_format}. Defaulting to 'mp3'.")
        output_format = "mp3"
        output_filepath = f"{os.path.splitext(output_filepath)[0]}.mp3"

    parameters = parse_audio_mime_type(mime_type)
    ffmpeg_format = "s16le"  # PCM 16-bit signed little-endian, standard for L16

    command = [
        ffmpeg_path,
        "-y",
        "-f", ffmpeg_format,
        "-ar", str(parameters["rate"]),
        "-ac", "1",
        "-i", "pipe:0",
        output_filepath,
    ]
    status_callback(f"Converting with FFmpeg to {os.path.basename(output_filepath)}...")

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    process = subprocess.run(command, input=full_audio_data, capture_output=True, check=False, creationflags=creation_flags)
    if process.returncode != 0:
        ffmpeg_error = process.stderr.decode('utf-8', errors='ignore')
        logger.error(f"FFmpeg error:\n{ffmpeg_error}")
        status_callback("--- ERROR DURING AUDIO CONVERSION ---")
        status_callback("Please check that FFmpeg is correctly installed and accessible in the PATH.")
        if ffmpeg_error.strip():
            status_callback(f"FFmpeg error detail: {ffmpeg_error.strip().splitlines()[-1]}")
        return None

    return output_filepath

def validate_speakers(script_text: str, app_settings: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Valide la configuration des locuteurs du script pour le provider TTS actif.

    Args:
        script_text: Le texte du script du podcast.
        app_settings: Le dictionnaire des paramètres de l'application.

    Returns:
        Un tuple (missing_speakers, configured_speakers) où:
          - missing_speakers: liste triée des speakers présents dans le script mais non configurés.
          - configured_speakers: liste triée des speakers présents dans le script et configurés.

    Règles supplémentaires:
        - Pour le provider 'gemini', il ne peut pas y avoir plus de 2 speakers dans le script.
          Si plus de 2 sont détectés, une ValueError est levée avec un message explicite.
    """
    # Trouver tous les locuteurs uniques du script (lignes du style "Nom: texte")
    script_speakers = set(re.findall(r"^\s*(.+?)\s*:", script_text, re.MULTILINE))

    if not script_speakers:
        return ([], [])  # Aucun speaker détecté

    provider_name = (app_settings or {}).get("tts_provider", "gemini").lower()

    # Règle spécifique Gemini: au plus 2 speakers autorisés
    if provider_name == "gemini" and len(script_speakers) > 2:
        raise ValueError(
            f"Gemini TTS supports at most 2 speakers, but {len(script_speakers)} were found: "
            f"{', '.join(sorted(script_speakers))}.\n\n"
            f"Please reduce the number of speakers or switch to ElevenLabs."
        )

    if provider_name == "elevenlabs":
        defined_speakers = set((app_settings or {}).get("speaker_voices_elevenlabs", {}).keys())
    else:
        defined_speakers = set((app_settings or {}).get("speaker_voices", {}).keys())

    missing_speakers = sorted(list(script_speakers - defined_speakers))
    configured_speakers = sorted(list(script_speakers & defined_speakers))

    return (missing_speakers, configured_speakers)

def generate(script_text: str, app_settings: dict, output_filepath: str, status_callback=print, api_key: Optional[str] = None) -> Optional[str]:
    """
    Génère l'audio depuis un script en utilisant le fournisseur choisi (Gemini ou ElevenLabs).
    app_settings doit contenir:
      - tts_provider
      - speaker_voices (Gemini)
      - speaker_voices_elevenlabs (ElevenLabs)
    """
    logger = logging.getLogger("PodcastGenerator")
    logger.info("Starting generation function.")
    status_callback("Starting podcast generation...")

    ffmpeg_path = find_ffmpeg_path()
    if not ffmpeg_path:
        status_callback("--- CRITICAL ERROR ---")
        status_callback("The FFmpeg executable was not found on this system.")
        status_callback("Please install it (e.g., with 'brew install ffmpeg') and try again.")
        logger.error("FFmpeg was not found in the PATH or Homebrew locations.")
        return None

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_filepath)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    provider_name = (app_settings or {}).get("tts_provider", "elevenlabs").lower()
    if provider_name not in ("gemini", "elevenlabs"):
        provider_name = "elevenlabs"

    # Récupération de la clé si absente
    if not api_key:
        api_key = get_api_key(status_callback, logger, service=provider_name)
        if not api_key:
            return None

    if provider_name == "gemini":
        speaker_mapping = (app_settings or {}).get("speaker_voices", {})
        provider = GeminiTTS(api_key=api_key)
        return provider.synthesize(script_text=script_text, speaker_mapping=speaker_mapping, output_filepath=output_filepath, status_callback=status_callback)
    else:
        speaker_mapping = (app_settings or {}).get("speaker_voices_elevenlabs", {})
        provider = ElevenLabsTTS(api_key=api_key)
        return provider.synthesize(script_text=script_text, speaker_mapping=speaker_mapping, output_filepath=output_filepath, status_callback=status_callback)

def parse_audio_mime_type(mime_type: str) -> Dict[str, int]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    # Default values
    bits_per_sample = 16
    rate = 24000

    # Separates the main type (e.g., "audio/L16") from parameters (e.g., "rate=24000")
    parts = [p.strip() for p in mime_type.split(';')]
    main_type = parts[0]
    params = parts[1:]

    # Extracts bits per sample from the main type
    if main_type.lower().startswith("audio/l"):
        try:
            bits_per_sample = int(main_type.split('L', 1)[1])
        except (ValueError, IndexError):
            pass  # Keep the default value if parsing fails

    # Extracts the rate from the parameters
    for param in params:
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split('=', 1)[1])
            except (ValueError, IndexError):
                pass  # Keep the default value if parsing fails
            break  # Rate found, no need to continue

    return {"bits_per_sample": bits_per_sample, "rate": rate}

if __name__ == "__main__":
    logger = setup_logging()

    # --- Argument Parsing for CLI mode ---
    parser = argparse.ArgumentParser(
        description="Generate a podcast from a script file using the Gemini or ElevenLabs API.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Example usage:
  python generate_podcast.py path/to/your/script.txt
  python generate_podcast.py path/to/your/script.txt -o path/to/your/output.mp3
"""
    )
    parser.add_argument(
        "script_filepath",
        help="Path to the text file containing the podcast script."
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_filepath",
        help="Path to save the output audio file. Can be a directory or a full path. Defaults to the same directory as the input script."
    )
    parser.add_argument(
        "--provider",
        choices=["elevenlabs", "gemini"],
        default="elevenlabs",
        help="TTS provider to use (default: ElevenLabs)"
    )
    args = parser.parse_args()

    # --- Read Script File ---
    try:
        with open(args.script_filepath, 'r', encoding='utf-8') as f:
            script_text = f.read()
    except FileNotFoundError:
        print(f"Error: The script file was not found at '{args.script_filepath}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not read the script file: {e}")
        sys.exit(1)

    # --- Determine Output Path ---
    output_filepath = args.output_filepath
    base_script_name = os.path.splitext(os.path.basename(args.script_filepath))[0]

    if output_filepath:
        # If the provided path is a directory, create the filename inside it
        if os.path.isdir(output_filepath):
            output_filepath = os.path.join(output_filepath, f"{base_script_name}.mp3")
            print(f"Output directory specified. Saving to: {output_filepath}")
    else:
        # Default to the same directory as the input script
        script_dir = os.path.dirname(os.path.abspath(args.script_filepath))
        output_filepath = os.path.join(script_dir, f"{base_script_name}.mp3")
        print(f"No output path specified. Defaulting to: {output_filepath}")

    def _load_cli_settings():
        """Loads settings from the JSON file for CLI usage."""
        app_data_dir = get_app_data_dir()
        settings_filepath = os.path.join(app_data_dir, "settings.json")
        try:
            with open(settings_filepath, 'r') as f:
                print(f"INFO: Loaded voice settings from {settings_filepath}")
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print("WARNING: settings.json not found or invalid. Using hardcoded default speakers.")
            return {
                "tts_provider": "elevenlabs",
                "speaker_voices": {"John": "Schedar", "Samantha": "Zephyr"},
                "speaker_voices_elevenlabs": {"John": "EkK5I93UQWFDigLMpZcX", "Samantha": "Z3R5wn05IrDiVCyEkUrK"}
            }

    # --- Get API Key and Generate ---
    app_settings = _load_cli_settings()
    app_settings['tts_provider'] = args.provider # Override provider from command line

    # --- Data Sanitization for backend ---
    # This logic mirrors the one in gui.py to ensure the backend receives clean data.
    app_settings_clean = {
        "tts_provider": app_settings.get("tts_provider"),
        "speaker_voices": app_settings.get("speaker_voices", {})
    }
    gemini_clean = {}
    for speaker, voice in app_settings_clean.get("speaker_voices", {}).items():
        if isinstance(voice, str) and " - " in voice:
            gemini_clean[speaker] = voice.split(" - ", 1)[0].strip()
        else:
            gemini_clean[speaker] = voice
    app_settings_clean["speaker_voices"] = gemini_clean

    elevenlabs_mapping_clean = {}
    elevenlabs_mapping_raw = app_settings.get("speaker_voices_elevenlabs", {})
    for speaker, data in elevenlabs_mapping_raw.items():
        if isinstance(data, dict):
            elevenlabs_mapping_clean[speaker] = data.get('id', '')
        else:
            # Legacy format: use the string as-is
            elevenlabs_mapping_clean[speaker] = data
    app_settings_clean["speaker_voices_elevenlabs"] = elevenlabs_mapping_clean

    # --- Validate Speaker Voices ---
    # Use the clean settings for validation, as this is what the backend expects
    missing_speakers, _ = validate_speakers(script_text, app_settings_clean)
    if missing_speakers:
        missing_speakers_str = ", ".join(missing_speakers)
        print(f"\n--- CONFIGURATION ERROR ---")
        print(f"The following speakers from the script do not have an assigned voice: {missing_speakers_str}")
        print(f"Please update your voice settings before running the generation.")
        logger.error(f"Generation stopped. Missing speakers in configuration: {missing_speakers_str}")
        sys.exit(1)

    api_key = get_api_key(print, logger, service=app_settings_clean["tts_provider"])
    if not api_key:
        print("API key is required to proceed. Exiting.")
        sys.exit(1)

    print(f"\nGenerating audio from '{os.path.basename(args.script_filepath)}' with provider '{app_settings_clean['tts_provider']}'...")
    result = generate(
        script_text=script_text,
        app_settings=app_settings_clean,
        output_filepath=output_filepath,
        status_callback=print,
        api_key=api_key
    )
    if not result:
        sys.exit(1)