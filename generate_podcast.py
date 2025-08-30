import argparse
import sys
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError
import os
import shutil
import subprocess
import logging
import getpass
from typing import Optional, Any, Dict, List, Tuple
import tempfile

import json
import keyring  # For secure credential storage
from create_demo import create_html_demo_whisperx

import re
import requests

# Global logger instance - initialized once when module is imported
logger = logging.getLogger(__name__)

# The podcast script is now a constant to be used by the console mode.
PODCAST_SCRIPT = """Read aloud in a warm, welcoming tone
John: [playful] Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs, my dogs' names are corgis! Who am I??
Samantha: [laughing] You're queen Elizabeth II!!
"""


def setup_logging() -> logging.Logger:
    """Configures logging to write to a file in the application's data directory."""
    if logger.hasHandlers():  # Avoids adding duplicate handlers
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

    logger.info("=" * 20)
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
        # If called from the GUI, we don't ask here. The GUI is responsible for its own dialogs.
        # This breaks the circular dependency that crashes the packaged app.
        if parent_window:
            logger.info("API key not found in storage. Returning None to GUI caller.")
            return None

        # If called from CLI (parent_window is None), we prompt in the console.
        logger.info("API key not found, prompting user in console.")

        # This is the CLI version of the WelcomeDialog
        print("\n--- Welcome to Podcast Generator ---")
        if service == "elevenlabs":
            print("To get started, the application needs your ElevenLabs API key.")
            print("You can get a key at: https://try.elevenlabs.io/zobct2wsp98z (affiliate link)")
        else:
            print("To get started, the application needs your Google Gemini API key.")
            print("You can get a free key at: https://ai.google.dev/gemini-api")

        print(f"\n{prompt_text}")
        try:
            # Use getpass to hide the key as it's typed
            api_key_input = getpass.getpass(prompt="> ")
        except EOFError:
            api_key_input = None

        if api_key_input and api_key_input.strip():
            api_key = api_key_input.strip()
            logger.info("User provided an API key.")
            keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)
            logger.info(f"New key saved to the secure system keychain.")
            status_callback("API key saved securely for future launches.")
        else:
            logger.info("User cancelled or provided empty API key entry.")
            status_callback("No API key provided. Cancelling.")
            return None

    logger.info("API key search finished.")
    return api_key


# --- Abstraction des fournisseurs TTS ---

class TTSProvider:
    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print) -> \
            Optional[str]:
        raise NotImplementedError


class GeminiTTS(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print) -> \
            Optional[str]:
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

        # Gemini has different configurations for 1 or 2 speakers.
        num_speakers = len(speaker_mapping)
        speech_config = None

        if num_speakers == 1:
            # Configuration for a single speaker
            the_only_voice_name = list(speaker_mapping.values())[0]
            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=the_only_voice_name)
                )
            )
            logger.info("Using Gemini single-speaker configuration.")
        elif num_speakers == 2:
            # Configuration for two speakers
            speech_config = types.SpeechConfig(
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
            )
            logger.info("Using Gemini multi-speaker configuration.")
        else:
            # This case is normally prevented by `validate_speakers`, but is handled for safety.
            status_callback(f"Error: Gemini TTS requires 1 or 2 speakers, but {num_speakers} were provided.")
            logger.error(f"Invalid number of speakers for Gemini TTS: {num_speakers}")
            return None

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=speech_config,
        )

        generated_successfully = False
        final_mime_type = ""
        audio_chunks = []

        nb_of_models = len(models_to_try)
        for i, model_name in enumerate(models_to_try):
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
                raw_error_message = str(e)
                # FIX 2: Use the correct error class names from google.genai.errors
                if "RESOURCE_EXHAUSTED" in raw_error_message:
                    status_callback(f"API Error with model '{model_name}': Quota limit reached.")
                    clean_details = None
                    if ". " in raw_error_message:
                        try:
                            import ast
                            details_str = raw_error_message.split('. ', 1)[1]
                            details_dict = ast.literal_eval(details_str)
                            if isinstance(details_dict, dict) and 'error' in details_dict and 'message' in details_dict[
                                'error']:
                                clean_details = details_dict['error']['message']
                        except (ValueError, SyntaxError, IndexError):
                            pass  # Parsing failed, clean_details remains None
                    final_message = clean_details or "Could not parse specific details from API response."
                    status_callback(f"Details: {final_message}")
                    logger.warning(f"API Quota Error with model '{model_name}': {final_message}")
                else:
                    status_callback(f"API error with model '{model_name}': {raw_error_message}")
                    logger.warning(f"API error with model '{model_name}': {e}")
                if i < nb_of_models - 1:
                    status_callback("Trying next model...")
            except Exception as e:
                status_callback(f"An unexpected critical error occurred: {e}")
                status_callback(traceback.format_exc())
                logger.error(f"Unexpected critical error: {e}\n{traceback.format_exc()}")
                generated_successfully = False
                break

        if not generated_successfully:
            status_callback(
                "\nAudio generation failed after trying all available models. Please check the logs for more details.")
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

    def synthesize(self, script_text: str, speaker_mapping: Dict[str, str], output_filepath: str,
                   status_callback=print) -> Optional[str]:
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

                process = subprocess.run(command, input=full_audio_data, capture_output=True, check=False,
                                         creationflags=creation_flags)
                if process.returncode != 0:
                    ffmpeg_error = process.stderr.decode('utf-8', errors='ignore')
                    self.logger.error(f"FFmpeg error during ElevenLabs conversion:\n{ffmpeg_error}")
                    status_callback("--- ERROR DURING AUDIO CONVERSION ---")
                    if ffmpeg_error.strip():
                        status_callback(f"FFmpeg error detail: {ffmpeg_error.strip().splitlines()[-1]}")
                    return None

                status_callback(f"File saved successfully: {output_filepath}")
                return output_filepath

        except ApiError as e:
            try:
                # Try to parse the specific quota error message from the API response body
                if hasattr(e, 'body') and e.body and e.body.get('detail', {}).get('status') == 'quota_exceeded':
                    message = e.body['detail'].get('message', 'Your ElevenLabs quota has been exceeded.')
                    status_callback("[ElevenLabs] API Error: Quota Exceeded.")
                    status_callback(f"Details: {message}")
                    self.logger.warning(f"ElevenLabs Quota Exceeded: {message}")
                else:
                    # For other API errors, show the raw error to the user and in logs
                    status_callback(f"[ElevenLabs] An API error occurred: {e}")
                    self.logger.error(f"ElevenLabs API error: {e}")
            except (KeyError, TypeError):
                # Fallback if the body structure is unexpected
                status_callback(f"[ElevenLabs] An API error occurred: {e}")
                self.logger.error(f"ElevenLabs API error with unexpected body: {e}")
            status_callback("\nAudio generation failed. Please check the logs for more details.")
            return None
        except Exception as e:
            status_callback(f"[ElevenLabs] An unexpected critical error occurred: {e}")
            self.logger.error(f"ElevenLabs critical error: {e}", exc_info=True)
            status_callback("\nAudio generation failed. Please check the logs for more details.")
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
            if text:  # Only add segment if there is text left to speak
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


def _ffmpeg_convert_inline_audio_chunks(audio_chunks: List[bytes], mime_type: str, output_filepath: str,
                                        status_callback=print) -> Optional[str]:
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

    process = subprocess.run(command, input=full_audio_data, capture_output=True, check=False,
                             creationflags=creation_flags)
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


def generate(script_text: str, app_settings: dict, output_filepath: str, status_callback=print,
             api_key: Optional[str] = None, parent_window=None) -> Optional[str]:
    """
    Génère l'audio depuis un script en utilisant le fournisseur choisi (Gemini ou ElevenLabs).
    app_settings doit contenir:
      - tts_provider
      - speaker_voices (Gemini)
      - speaker_voices_elevenlabs (ElevenLabs)
    Le paramètre `parent_window` est crucial pour le contexte GUI.
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
        api_key = get_api_key(status_callback, logger, parent_window=parent_window, service=provider_name)
        if not api_key:
            return None

    if provider_name == "gemini":
        speaker_mapping = (app_settings or {}).get("speaker_voices", {})
        provider = GeminiTTS(api_key=api_key)
        return provider.synthesize(script_text=script_text, speaker_mapping=speaker_mapping,
                                   output_filepath=output_filepath, status_callback=status_callback)
    else:
        speaker_mapping = (app_settings or {}).get("speaker_voices_elevenlabs", {})
        provider = ElevenLabsTTS(api_key=api_key)
        return provider.synthesize(script_text=script_text, speaker_mapping=speaker_mapping,
                                   output_filepath=output_filepath, status_callback=status_callback)


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


if __name__ == "__main__":
    logger = setup_logging()

    # --- Argument Parsing for CLI mode ---
    parser = argparse.ArgumentParser(
        description="Generate a podcast from a script file or text using the Gemini or ElevenLabs API.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""\
Example usage:
  # From a file
  python generate_podcast.py path/to/your/script.txt
  python generate_podcast.py path/to/your/script.txt -o path/to/your/output.mp3
  python generate_podcast.py script.txt --provider elevenlabs --speaker "John:TX3LPaxmHKxFdv7VOQHJ" --speaker "Samantha:pT95jSTK1iJkOytAqCbf"

  # From a string
  python generate_podcast.py --script-text "John: Hello" --output out.mp3
"""
    )
    parser.add_argument(
        "script_filepath",
        nargs='?',
        default=None,
        help="Path to the text file containing the podcast script. Required if --script-text is not used."
    )
    parser.add_argument(
        "--script-text",
        help="The script text to generate, as a string. Use instead of a file."
    )
    parser.add_argument(
        "-o", "--output",
        dest="output_filepath",
        help="Path to save the output audio file. Can be a directory (if using a script file) or a full path. Required if using --script-text."
    )
    parser.add_argument(
        "--provider",
        choices=["elevenlabs", "gemini"],
        default="elevenlabs",
        help="TTS provider to use (default: ElevenLabs)"
    )
    parser.add_argument(
        "--speaker",
        action="append",
        help='Assign a voice to a speaker. Format: "SpeakerName:VoiceNameOrID".\n'
             'Can be used multiple times. This overrides settings from the config file.\n'
             'Example for ElevenLabs: --speaker "John:TX3LPaxmHKxFdv7VOQHJ"\n'
             'Example for Gemini: --speaker "Samantha:Zephyr"'
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate an HTML demo with a synchronized transcript after creating the audio."
    )
    args = parser.parse_args()

    # --- Validate input and read script ---
    if args.script_filepath and args.script_text:
        parser.error("argument script_filepath and --script-text are mutually exclusive.")
    if not args.script_filepath and not args.script_text:
        parser.error("one of the arguments script_filepath or --script-text is required.")

    temp_script_file_path = None
    if args.script_text:
        script_text = args.script_text
        script_source_description = "the provided text"
        if not args.output_filepath:
            parser.error("argument --output is required when using --script-text.")
        if os.path.isdir(args.output_filepath):
            parser.error("when using --script-text, --output must be a full file path, not a directory.")
        output_filepath = args.output_filepath
        # For demo generation, we need a file path.
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as f:
            f.write(script_text)
            script_filepath_for_demo = f.name
        temp_script_file_path = script_filepath_for_demo

    else:  # script_filepath is guaranteed to be not None here
        try:
            with open(args.script_filepath, 'r', encoding='utf-8') as f:
                script_text = f.read()
            script_filepath_for_demo = args.script_filepath
            script_source_description = f"'{os.path.basename(args.script_filepath)}'"
        except FileNotFoundError:
            print(f"Error: The script file was not found at '{args.script_filepath}'")
            sys.exit(1)
        except Exception as e:
            print(f"Error: Could not read the script file: {e}")
            sys.exit(1)

        # --- Determine Output Path (only when using a script file) ---
        output_filepath = args.output_filepath
        base_script_name = os.path.splitext(os.path.basename(args.script_filepath))[0]

        if output_filepath:
            if os.path.isdir(output_filepath):
                output_filepath = os.path.join(output_filepath, f"{base_script_name}.mp3")
                print(f"Output directory specified. Saving to: {output_filepath}")
        else:
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
    app_settings['tts_provider'] = args.provider  # Override provider from command line

    # --- Data Sanitization for backend ---
    # This logic mirrors the one in gui.py to ensure the backend receives clean data.
    app_settings_clean = sanitize_app_settings_for_backend(app_settings)

    # --- Override speakers from CLI arguments ---
    if args.speaker:
        print("INFO: Overriding speaker voices from command line arguments.")
        cli_speaker_mapping = {}
        for speaker_arg in args.speaker:
            if ":" not in speaker_arg:
                print(f"WARNING: Invalid speaker format '{speaker_arg}'. Skipping. Use 'Name:Voice'.")
                continue
            name, voice = speaker_arg.split(":", 1)
            cli_speaker_mapping[name.strip()] = voice.strip()

        if args.provider == "elevenlabs":
            app_settings_clean["speaker_voices_elevenlabs"] = cli_speaker_mapping
            print(f"INFO: ElevenLabs voices set to: {app_settings_clean['speaker_voices_elevenlabs']}")
        else:  # gemini
            app_settings_clean["speaker_voices"] = cli_speaker_mapping
            print(f"INFO: Gemini voices set to: {app_settings_clean['speaker_voices']}")

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

    print(
        f"\nGenerating audio from {script_source_description} with provider '{app_settings_clean['tts_provider']}'...")
    result = generate(
        script_text=script_text,
        app_settings=app_settings_clean,
        output_filepath=output_filepath,
        status_callback=print,
        api_key=api_key
    )
    if not result:
        # Clean up the temporary script file if it was created, even on failure
        if temp_script_file_path:
            os.remove(temp_script_file_path)
        sys.exit(1)

    if result and args.demo:
        # Create a default title from the output filename for the demo page
        demo_title = os.path.splitext(os.path.basename(output_filepath))[0].replace('_', ' ').replace('-', ' ').title()
        create_html_demo(
            script_filepath=script_filepath_for_demo,
            audio_filepath=result,
            title=demo_title,
            status_callback=print
        )

    if temp_script_file_path:
        os.remove(temp_script_file_path)