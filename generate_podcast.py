# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import logging
import mimetypes
import argparse
import os
import subprocess
import webbrowser
import shutil
import sys
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

import keyring # For secure credential storage
# Import tools for dialog boxes
import tkinter as tk
from tkinter import simpledialog, messagebox

# The podcast script is now a constant to be used by the console mode.
PODCAST_SCRIPT = """Read aloud in a warm, welcoming tone
John: Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs – my dogs' names are corgis! Who am I?
Samantha: [amused] Queen Elizabeth II!
"""

class WelcomeDialog(tk.Toplevel):
    """A custom dialog window to welcome the user and provide a clickable link."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Welcome!")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        main_frame = tk.Frame(self, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Welcome to Podcast Generator!", font=('Helvetica', 12, 'bold')).pack(pady=(0, 10))
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
    logger = logging.getLogger("PodcastGenerator")
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

def _find_command_path(command: str) -> str | None:
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

def find_ffmpeg_path() -> str | None:
    """Finds the path to the FFmpeg executable."""
    return _find_command_path("ffmpeg")

def find_ffplay_path() -> str | None:
    """Finds the path to the ffplay executable."""
    return _find_command_path("ffplay")

def get_api_key(status_callback, logger: logging.Logger, parent_window=None) -> str | None:
    """
    Finds the API key securely.
    1. (Developer) Looks for a local .env file.
    2. (User) Looks for the key in the system keychain.
    3. (Migration) Looks for an old, insecure .env file and migrates it to the keychain.
    4. (First launch) Asks the user for the key and saves it to the keychain.
    """
    SERVICE_NAME = "PodcastGenerator"
    ACCOUNT_NAME = "gemini_api_key"
    logger.info("="*20)
    logger.info("Starting API key search...")

    # --- 1. For developers: priority to local .env file ---
    if not getattr(sys, 'frozen', False):
        dev_dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(dev_dotenv_path):
            logger.info(f"Development .env file found. Using this key.")
            load_dotenv(dotenv_path=dev_dotenv_path)
            dev_key = os.environ.get("GEMINI_API_KEY")
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
        old_key = os.environ.get("GEMINI_API_KEY")
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

        welcome_dialog = WelcomeDialog(dialog_parent)
        dialog_parent.wait_window(welcome_dialog)

        api_key_input = simpledialog.askstring(
            "API Key Required",
            "Please paste your Google Gemini API key:",
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

def generate(script_text: str, speaker_mapping: dict, api_key: str, output_filepath: str, status_callback=print) -> str | None:
    """Generates audio from a script using Gemini, with a model fallback."""
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
    if not api_key:
        return None # Should not happen if get_api_key is called first, but as a safeguard.

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_filepath)
    if output_dir: # Only create directories if a path is specified
        os.makedirs(output_dir, exist_ok=True)

    client = genai.Client(api_key=api_key)

    # List of models to try, from most to least preferred.
    models_to_try = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=script_text),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=[
            "audio",
        ],
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
                    if not final_mime_type:  # Store the mime_type only once
                        final_mime_type = part.inline_data.mime_type
                else:
                    status_callback(chunk.text)

            if not audio_chunks:
                raise errors.GoogleAPICallError("No audio data was generated by the model.")

            # --- Conversion with FFmpeg ---
            full_audio_data = b"".join(audio_chunks)
            output_format = os.path.splitext(output_filepath)[1].lower().strip('.')
            if output_format not in ["wav", "mp3"]:
                status_callback(f"Unsupported file format: {output_format}. Defaulting to 'mp3'.")
                output_format = "mp3"
                output_filepath = f"{os.path.splitext(output_filepath)[0]}.mp3"

            parameters = parse_audio_mime_type(final_mime_type)
            ffmpeg_format = "s16le" # PCM 16-bit signed little-endian, standard for L16

            command = [
                ffmpeg_path,
                "-y",  # Overwrite output file without asking
                "-f", ffmpeg_format,
                "-ar", str(parameters["rate"]),
                "-ac", "1",  # Mono
                "-i", "pipe:0",  # Read data from standard input (stdin)
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
                status_callback(f"FFmpeg error detail: {ffmpeg_error.strip().splitlines()[-1]}")
                generated_successfully = False
                break # Critical error, no need to try other models

            status_callback(f"File saved successfully: {output_filepath}")

            status_callback(f"Audio generated successfully via {model_name}.")
            generated_successfully = True
            break  # Exit the model-selection loop on success
        except errors.APIError as e:
            # Expected API error (e.g., model unavailable, quota exceeded). It's normal to continue.
            status_callback(f"API error with model '{model_name}'")
            status_callback("Trying next model...")
            logger.warning(f"API error with model '{model_name}': {e}")
        except Exception as e:
            # Unexpected and potentially critical error (network, logic, etc.).
            # We must stop the process and display as much information as possible.
            status_callback(f"An unexpected critical error occurred: {e}")
            status_callback(traceback.format_exc())
            logger.error(f"Unexpected critical error: {e}\n{traceback.format_exc()}")
            generated_successfully = False
            break # No need to continue with other models, the error is serious.

    if not generated_successfully:
        status_callback("\nFailed to generate audio with all available models.")
        return None
    return output_filepath

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
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
        description="Generate a podcast from a script file using the Gemini API.",
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

    # --- Get API Key and Generate ---
    api_key = get_api_key(print, logger)
    if not api_key:
        print("API key is required to proceed. Exiting.")
        sys.exit(1)

    # For command-line execution, we use a default mapping.
    default_speaker_mapping = {"John": "Schedar", "Samantha": "Zephyr"}
    print(f"\nGenerating audio from '{os.path.basename(args.script_filepath)}'...")
    generate(
        script_text=script_text,
        speaker_mapping=default_speaker_mapping,
        api_key=api_key,
        output_filepath=output_filepath
    )
