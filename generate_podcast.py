import argparse
import sys
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError
import os
import subprocess
import logging
import getpass
from typing import Optional, Any, Dict, List, Tuple
import tempfile
import threading

import json
import keyring  # For secure credential storage

import re
import requests
from utils import get_app_data_dir, find_ffmpeg_path, sanitize_app_settings_for_backend, sanitize_text

# Global logger instance - initialized once when module is imported
logger = logging.getLogger(__name__)

# The podcast script is now split into instruction and main script
DEFAULT_INSTRUCTION = "Read aloud in a warm, welcoming tone"
DEFAULT_SCRIPT = """John: [playful] Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs, my dogs' names are corgis! Who am I??
Samantha: [laughing] You're queen Elizabeth II!!
"""
PODCAST_SCRIPT = f"{DEFAULT_INSTRUCTION}\n{DEFAULT_SCRIPT}"


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
    else:
        ACCOUNT_NAME = "gemini_api_key"
        ENV_VAR = "GEMINI_API_KEY"

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
        if parent_window:
            logger.info("API key not found in storage. Returning None to GUI caller.")
            return None

        logger.info("API key not found, prompting user in console.")
        prompt_text = "Please paste your Google Gemini API key:" if service == "gemini" else "Please paste your ElevenLabs API key:"
        print(f"\n{prompt_text}")
        try:
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


class TTSProvider:
    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print, stop_event: Optional[threading.Event] = None) -> str:
        raise NotImplementedError


class GeminiTTS(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def synthesize(self, script_text: str, speaker_mapping: dict, output_filepath: str, status_callback=print, stop_event: Optional[threading.Event] = None) -> str:
        logger = logging.getLogger("PodcastGenerator")
        client = genai.Client(api_key=self.api_key)

        gemini_script = script_text.replace('[', '(').replace(']', ')')
        logger.info("Converted script annotations from [] to () for Gemini.")

        models_to_try = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=gemini_script)])]

        num_speakers = len(speaker_mapping)
        if num_speakers == 1:
            speech_config = types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=list(speaker_mapping.values())[0])))
            logger.info("Using Gemini single-speaker configuration.")
        elif num_speakers == 2:
            speech_config = types.SpeechConfig(multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(speaker_voice_configs=[
                types.SpeakerVoiceConfig(speaker=speaker_name, voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)))
                for speaker_name, voice_name in speaker_mapping.items()
            ]))
            logger.info("Using Gemini multi-speaker configuration.")
        else:
            raise ValueError(f"Gemini TTS requires 1 or 2 speakers, but {num_speakers} were provided.")

        generate_content_config = types.GenerateContentConfig(temperature=1, response_modalities=["audio"], speech_config=speech_config)

        for i, model_name in enumerate(models_to_try):
            if stop_event and stop_event.is_set():
                raise Exception("Generation stopped by user.")
            status_callback(f"\nAttempting generation with model: {model_name}...")
            try:
                audio_chunks = []
                final_mime_type = ""
                for chunk in client.models.generate_content_stream(model=model_name, contents=contents, config=generate_content_config):
                    if stop_event and stop_event.is_set():
                        raise Exception("Generation stopped by user during streaming.")
                    if not (chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts):
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
                status_callback(f"Audio generated successfully via {model_name}.")
                return _ffmpeg_convert_inline_audio_chunks(audio_chunks, final_mime_type, output_filepath, status_callback)
            except errors.APIError as e:
                logger.warning(f"API error with model '{model_name}': {e}")
                if i < len(models_to_try) - 1:
                    status_callback("Trying next model...")
                else:
                    raise Exception(f"Gemini API Error: {e}")
        raise Exception("Audio generation failed after trying all available models.")


class ElevenLabsTTS(TTSProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)
        self.logger = logging.getLogger("PodcastGenerator")

    def synthesize(self, script_text: str, speaker_mapping: Dict[str, str], output_filepath: str, status_callback=print, stop_event: Optional[threading.Event] = None) -> str:
        segments = self._parse_script_segments(script_text)
        if not segments:
            raise ValueError("No valid dialogue segments found in the script. Ensure lines are in 'Speaker: Text' format.")

        dialogue_inputs = []
        for speaker, text in segments:
            voice_id = speaker_mapping.get(speaker)
            if not voice_id:
                self.logger.warning(f"No voice mapped for '{speaker}', skipping segment.")
                continue
            dialogue_inputs.append({"text": text, "voice_id": voice_id})

        if not dialogue_inputs:
            raise ValueError("No dialogue segments with mapped voices could be generated.")

        status_callback("[ElevenLabs] Generating full dialogue...")
        try:
            audio_generator = self.client.text_to_dialogue.convert(inputs=dialogue_inputs)
            output_ext = os.path.splitext(output_filepath)[1].lower()
            if output_ext not in [".mp3", ".wav"]:
                self.logger.warning(f"Unsupported file format: '{output_ext}'. Defaulting to '.mp3'.")
                output_filepath = os.path.splitext(output_filepath)[0] + ".mp3"
            
            with open(output_filepath, "wb") as f:
                for chunk in audio_generator:
                    if stop_event and stop_event.is_set():
                        raise Exception("Generation stopped by user during streaming.")
                    f.write(chunk)
            
            status_callback(f"File saved successfully: {output_filepath}")
            return output_filepath
        except ApiError as e:
            self.logger.error(f"ElevenLabs API error: {e}")
            try:
                # Extract the user-friendly message from the error body
                error_message = e.body['detail']['message']
                raise Exception(f"ElevenLabs API Error: {error_message}")
            except (KeyError, TypeError):
                # Fallback for unexpected error formats
                raise Exception(f"An unknown ElevenLabs API error occurred: {e}")
        except Exception as e:
            # Re-raise the stop exception to be caught by the task runner
            if "stopped by user" in str(e):
                raise e
            self.logger.error(f"ElevenLabs critical error: {e}", exc_info=True)
            raise Exception(f"An unexpected critical error occurred in ElevenLabs TTS: {e}")

    def _parse_script_segments(self, script_text: str) -> List[Tuple[str, str]]:
        segments = []
        for raw_line in script_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            m = re.match(r"^(\w+):\s*(.+)$", line)
            if not m:
                self.logger.info(f"Skipping non-dialogue line for ElevenLabs: '{line}'")
                continue
            speaker, text = m.group(1).strip(), m.group(2).strip()
            text = re.sub(r"<[^>]+>", "", text).strip()
            if text:
                segments.append((speaker, text))
        return segments


def update_elevenlabs_quota(api_key: str, status_callback=print) -> Optional[str]:
    """
    Fetches the character quota from the ElevenLabs v1 API.
    Returns a formatted quota string (e.g., "Remaining: X / Y characters") or None if unavailable.
    """
    try:
        headers = {"xi-api-key": api_key}
        resp = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        sub = data.get("subscription", {})
        used = sub.get("character_count", 0)
        limit = sub.get("character_limit", 0)
        if limit > 0:
            remaining = max(0, limit - used)
            return f"Remaining: {remaining} / {limit} characters" # Removed "TTS Provider: ElevenLabs v3 -"
        return "Quota info missing" # Removed "TTS Provider: ElevenLabs v3 -"
    except Exception as e:
        status_callback(f"Error fetching ElevenLabs quota: {e}")
        return "Network error" # Removed "TTS Provider: ElevenLabs v3 -"


def _ffmpeg_convert_inline_audio_chunks(audio_chunks: List[bytes], mime_type: str, output_filepath: str, status_callback=print) -> str:
    ffmpeg_path = find_ffmpeg_path()
    if not ffmpeg_path:
        raise FileNotFoundError("FFmpeg executable not found.")

    full_audio_data = b"".join(audio_chunks)
    parameters = parse_audio_mime_type(mime_type)
    command = [ffmpeg_path, "-y", "-f", "s16le", "-ar", str(parameters["rate"]), "-ac", "1", "-i", "pipe:0", output_filepath]
    status_callback(f"Converting with FFmpeg to {os.path.basename(output_filepath)}...")
    
    creation_flags = 0 if sys.platform != "win32" else subprocess.CREATE_NO_WINDOW
    process = subprocess.run(command, input=full_audio_data, capture_output=True, check=False, creationflags=creation_flags)
    
    if process.returncode != 0:
        ffmpeg_error = process.stderr.decode('utf-8', errors='ignore')
        raise Exception(f"FFmpeg error during audio conversion: {ffmpeg_error.strip().splitlines()[-1]}")
    return output_filepath


def validate_speakers(script_text: str, app_settings: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    script_speakers = set(re.findall(r"^\s*(\w+)\s*:", script_text, re.MULTILINE))
    if not script_speakers:
        return [], []
    provider_name = app_settings.get("tts_provider", "gemini").lower()
    if provider_name == "gemini" and len(script_speakers) > 2:
        raise ValueError(f"Gemini TTS supports at most 2 speakers, but {len(script_speakers)} were found: {', '.join(sorted(script_speakers))}.")
    
    defined_speakers_key = "speaker_voices_elevenlabs" if provider_name == "elevenlabs" else "speaker_voices"
    defined_speakers = set(app_settings.get(defined_speakers_key, {}).keys())
    
    missing_speakers = sorted(list(script_speakers - defined_speakers))
    configured_speakers = sorted(list(script_speakers & defined_speakers))
    return missing_speakers, configured_speakers


def generate(script_text: str, app_settings: dict, output_filepath: str, status_callback=print, api_key: Optional[str] = None, parent_window=None, stop_event: Optional[threading.Event] = None) -> str:
    logger = logging.getLogger("PodcastGenerator")
    logger.info("Starting generation function.")
    status_callback("Starting podcast generation...")

    if stop_event and stop_event.is_set():
        raise Exception("Generation stopped by user before starting.")

    sanitized_script_text = sanitize_text(script_text)
    if not find_ffmpeg_path():
        raise FileNotFoundError("FFmpeg executable not found.")

    output_dir = os.path.dirname(output_filepath)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    provider_name = app_settings.get("tts_provider", "elevenlabs").lower()
    if not api_key:
        api_key = get_api_key(status_callback, logger, parent_window=parent_window, service=provider_name)
        if not api_key:
            raise ValueError("API key is required but was not provided.")

    speaker_mapping_key = "speaker_voices_elevenlabs" if provider_name == "elevenlabs" else "speaker_voices"
    speaker_mapping = app_settings.get(speaker_mapping_key, {})
    
    ProviderClass = ElevenLabsTTS if provider_name == "elevenlabs" else GeminiTTS
    provider = ProviderClass(api_key=api_key)
    
    return provider.synthesize(script_text=sanitized_script_text, speaker_mapping=speaker_mapping, output_filepath=output_filepath, status_callback=status_callback, stop_event=stop_event)


def parse_audio_mime_type(mime_type: str) -> Dict[str, int]:
    rate = 24000
    for param in mime_type.split(';'):
        if param.lower().strip().startswith("rate="):
            try:
                rate = int(param.split('=', 1)[1])
            except (ValueError, IndexError):
                pass
            break
    return {"bits_per_sample": 16, "rate": rate}


def sanitize_app_settings_for_backend(app_settings: Dict[str, Any]) -> Dict[str, Any]:
    clean_settings = {"tts_provider": app_settings.get("tts_provider")}
    
    gemini_voices = app_settings.get("speaker_voices", {})
    clean_gemini = {}
    for speaker, voice in gemini_voices.items():
        clean_gemini[speaker] = voice.split(" - ", 1)[0].strip() if isinstance(voice, str) and " - " in voice else voice
    clean_settings["speaker_voices"] = clean_gemini

    elevenlabs_voices = app_settings.get("speaker_voices_elevenlabs", {})
    clean_elevenlabs = {}
    for speaker, data in elevenlabs_voices.items():
        clean_elevenlabs[speaker] = data.get('id', '') if isinstance(data, dict) else data
    clean_settings["speaker_voices_elevenlabs"] = clean_elevenlabs
    
    return clean_settings


if __name__ == "__main__":
    logger = setup_logging()
    parser = argparse.ArgumentParser(description="Generate a podcast from a script file or text.")
    parser.add_argument("script_filepath", nargs='?', default=None, help="Path to the podcast script file.")
    parser.add_argument("--script-text", help="The script text to generate.")
    parser.add_argument("-o", "--output", dest="output_filepath", help="Path to save the output audio file.")
    parser.add_argument("--provider", choices=["elevenlabs", "gemini"], default="elevenlabs", help="TTS provider to use.")
    parser.add_argument("--speaker", action="append", help='Assign a voice to a speaker. Format: "SpeakerName:VoiceNameOrID".')
    args = parser.parse_args()

    if not args.script_filepath and not args.script_text:
        parser.error("Either script_filepath or --script-text is required.")

    if args.script_text:
        script_text = sanitize_text(args.script_text)
        output_filepath = args.output_filepath or "output.mp3"
    else:
        try:
            with open(args.script_filepath, 'r', encoding='utf-8') as f:
                script_text = sanitize_text(f.read())
            output_filepath = args.output_filepath or f"{os.path.splitext(args.script_filepath)[0]}.mp3"
        except FileNotFoundError:
            sys.exit(f"Error: The script file was not found at '{args.script_filepath}'")

    try:
        app_settings = {"tts_provider": args.provider}
        if args.speaker:
            speaker_mapping = {}
            for speaker_arg in args.speaker:
                name, voice = speaker_arg.split(":", 1)
                speaker_mapping[name.strip()] = voice.strip()
            if args.provider == "elevenlabs":
                app_settings["speaker_voices_elevenlabs"] = speaker_mapping
            else:
                app_settings["speaker_voices"] = speaker_mapping
        
        missing_speakers, _ = validate_speakers(script_text, app_settings)
        if missing_speakers:
            sys.exit(f"Error: Missing voice configuration for speakers: {', '.join(missing_speakers)}")

        api_key = get_api_key(print, logger, service=args.provider)
        if not api_key:
            sys.exit("API key is required. Exiting.")

        generate(script_text=script_text, app_settings=app_settings, output_filepath=output_filepath, status_callback=print, api_key=api_key)
    except Exception as e:
        sys.exit(f"\n--- A CRITICAL ERROR OCCURRED ---\n{e}")
