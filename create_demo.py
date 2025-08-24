import argparse
import os
import sys
import json
import webbrowser
import logging
import re
import tempfile
import shutil
import subprocess


def _prepare_scripts(original_script_text: str) -> tuple[str, str]:
    """
    Prepares two versions of the script:
    1. A clean version for MFA alignment (no speaker names, no annotations).
    2. A display version for the final HTML (speaker names and annotations preserved).
    """
    # The display version is the original text with normalized apostrophes.
    display_text_normalized = original_script_text.replace("’", "'").replace("`", "'")

    # The MFA version is created by cleaning the display version.
    # 1. Remove annotations.
    mfa_text_intermediate = re.sub(r'[<\[][^>\]]*[>\]]', '', display_text_normalized)
    # 2. Remove speaker names.
    mfa_text_normalized = re.sub(r'^\s*[\w\s]+:\s*', '', mfa_text_intermediate, flags=re.MULTILINE)

    return mfa_text_normalized, display_text_normalized

def _parse_textgrid(textgrid_filepath: str) -> list:
    """Parses a TextGrid file from MFA to extract word timings."""
    logger = logging.getLogger("PodcastGenerator.Demo")
    try:
        import textgrid
    except ImportError:
        logger.error("The 'textgrid' library is required. Please run 'pip install textgrid'.")
        return []

    if not os.path.exists(textgrid_filepath):
        logger.warning(f"TextGrid file not found at {textgrid_filepath}")
        return []

    tg = textgrid.TextGrid.fromFile(textgrid_filepath)
    words_tier = tg.getFirst("words")
    if not words_tier:
        logger.warning("Could not find a 'words' tier in the TextGrid file.")
        return []

    transcript = []
    for interval in words_tier:
        # Skip silences which are often marked as empty strings
        if interval.mark and interval.mark.strip():
            transcript.append({
                "word": interval.mark.strip(),
                "start": interval.minTime,
                "end": interval.maxTime,
            })
    return transcript

def _download_mfa_model_if_needed(model_type: str, model_name: str, mfa_base_command: list, status_callback=print):
    """Helper to check for an MFA model and download it if missing."""
    logger = logging.getLogger("PodcastGenerator.Demo")

    check_cmd = mfa_base_command + ["model", "inspect", model_type, model_name]
    logger.debug(f"Checking for MFA {model_type} model: {' '.join(check_cmd)}")
    if subprocess.run(check_cmd, capture_output=True).returncode != 0:
        status_callback(f"MFA {model_type} model '{model_name}' not found. Downloading...")
        download_cmd = mfa_base_command + ["model", "download", model_type, model_name]
        logger.debug(f"Running: {' '.join(download_cmd)}")
        result = subprocess.run(download_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download MFA {model_type} model '{model_name}'.\nError: {result.stderr}")
        status_callback(f"{model_type.capitalize()} model downloaded successfully.")
    else:
        logger.info(f"MFA {model_type} model '{model_name}' already installed.")

def _setup_mfa_models(dictionary: str, acoustic_model: str, mfa_base_command: list, status_callback=print):
    """Checks for MFA models and downloads them if not present."""
    _download_mfa_model_if_needed("dictionary", dictionary, mfa_base_command, status_callback)
    _download_mfa_model_if_needed("acoustic", acoustic_model, mfa_base_command, status_callback)

def create_html_demo(script_filepath: str, audio_filepath: str, title: str = "Podcast Demo", subtitle: str = None, output_dir: str = None, status_callback=print):
    """
    Génère une démo HTML synchronisée depuis un script et son audio.
    Utilise Montreal Forced Aligner (MFA) pour aligner mot à mot.
    """
    logger = logging.getLogger("PodcastGenerator.Demo")
    mfa_base_command = [sys.executable, "-m", "montreal_forced_aligner.command_line.mfa"]

    # --- 1. Dependency and Setup Checks ---
    if not shutil.which("ffmpeg"):
        error_msg = "Dependency 'ffmpeg' not found. MFA requires ffmpeg to process audio files. Please install it (e.g., 'brew install ffmpeg' on macOS or 'sudo apt-get install ffmpeg' on Debian/Ubuntu) and ensure it's in your system's PATH."
        status_callback(error_msg)
        logger.error(error_msg)
        return

    # Check MFA version compatibility
    try:
        # For MFA v3.x, 'version' is a command. check=True will raise on failure.
        version_result = subprocess.run(
            mfa_base_command + ["version"], capture_output=True, text=True, check=True
        )
        version_str = version_result.stdout.strip().split()[-1]
        logger.info(f"Found compatible MFA version: {version_str}")
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError) as e:
        error_msg = (
            "Could not run or verify Montreal Forced Aligner (MFA).\n"
            "Please ensure it is installed correctly using the recommended Conda method.\n"
            f"Details: {e}"
        )
        status_callback(error_msg)
        logger.error(error_msg)
        return

    try:
        import textgrid
    except ImportError:
        status_callback("The 'textgrid' library is required to parse MFA output. Install with: pip install textgrid")
        logger.error("'textgrid' library not found")
        return

    # For now, we hardcode English models. This could be parameterized in the future.
    dictionary_model = "english_us_arpa"
    acoustic_model = "english_us_arpa"
    try:
        _setup_mfa_models(dictionary_model, acoustic_model, mfa_base_command, status_callback)
    except Exception as e:
        status_callback(f"MFA model setup failed: {e}")
        logger.error(f"MFA model setup failed: {e}", exc_info=True)
        return

    # Use temporary directories that are automatically cleaned up
    with tempfile.TemporaryDirectory() as corpus_dir, tempfile.TemporaryDirectory() as mfa_output_dir:
        try:
            # --- 2. Prepare Corpus for MFA ---
            status_callback("Preparing corpus for MFA...")
            base_name = os.path.splitext(os.path.basename(audio_filepath))[0]

            # MFA works best with WAV files, so we convert the input audio.
            temp_audio_filepath = os.path.join(corpus_dir, f"{base_name}.wav")
            ffmpeg_command = ["ffmpeg", "-y", "-i", audio_filepath, "-ac", "1", "-ar", "16000", temp_audio_filepath]
            logger.debug(f"Executing ffmpeg: {' '.join(ffmpeg_command)}")
            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)

            # Clean the script and save it with the same basename as the audio.
            with open(script_filepath, "r", encoding="utf-8") as f:
                original_script_text = f.read()
            mfa_script_text, display_script_text = _prepare_scripts(original_script_text)
            temp_script_filepath = os.path.join(corpus_dir, f"{base_name}.txt")
            with open(temp_script_filepath, "w", encoding="utf-8") as f:
                f.write(mfa_script_text)

            status_callback("Corpus prepared. Starting alignment with MFA (this may take a moment)...")

            # --- 3. Run MFA Aligner ---
            mfa_command = mfa_base_command + [
                "align", corpus_dir, dictionary_model, acoustic_model, mfa_output_dir,
                "--clean", "--use_punctuation", "--case_sensitive",
                # Use a wider beam to make alignment more robust on difficult segments
                # (e.g., non-speech sounds like laughter) at the cost of speed.
                "--beam", "200", "--retry_beam", "400"
            ]
            logger.debug(f"Executing MFA: {' '.join(mfa_command)}")
            # Run MFA and stream its output to the console to show progress.
            # check=True will raise an exception on failure.
            subprocess.run(mfa_command, check=True)

            status_callback("MFA alignment successful.")

            # --- 4. Parse TextGrid Output and Reconstruct HTML ---
            textgrid_filepath = os.path.join(mfa_output_dir, f"{base_name}.TextGrid")
            transcript_from_mfa = _parse_textgrid(textgrid_filepath)
            if not transcript_from_mfa:
                raise RuntimeError("Failed to parse TextGrid output or no words were aligned.")

            # Reconstruct the final HTML body by mapping timed words back to the cleaned script text.
            # This preserves all original formatting (casing, line breaks, extra spaces).
            html_body_parts = []
            text_pointer = 0
            source_text = display_script_text # Use the script with speaker names for reconstruction

            for timed_item in transcript_from_mfa:
                word_to_find = timed_item['word']
                # MFA can output <unk> for words it doesn't recognize (like emojis). Skip them.
                if word_to_find == '<unk>':
                    continue
                try:
                    # Find the next occurrence of the word from MFA in our source text, case-insensitively.
                    # This is crucial for matching MFA's lowercase output to the original script's casing.
                    found_at = source_text.lower().index(word_to_find.lower(), text_pointer)

                    # Append the text (whitespace, etc.) between the last word and this one
                    leading_text = source_text[text_pointer:found_at]
                    # Format for HTML: escape special chars, convert newlines, and bold speaker names
                    processed_leading_text = leading_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    processed_leading_text = processed_leading_text.replace("\n", "<br>\n")
                    processed_leading_text = re.sub(r'(^|<br>\n)(\s*)([\w\s]+:)', r'\1\2<strong>\3</strong>', processed_leading_text)
                    html_body_parts.append(
                        processed_leading_text
                    )

                    # Append the timed word as a span
                    start, end = timed_item['start'], timed_item['end']
                    original_word = source_text[found_at:found_at + len(word_to_find)] # Get the word with original casing
                    word_html = f'<span class="word" data-start="{start}" data-end="{end}" onclick="audio.currentTime = {start};">{original_word}</span>'
                    html_body_parts.append(word_html)

                    # Move the pointer to the end of the found word
                    text_pointer = found_at + len(word_to_find)
                except ValueError:
                    logger.warning(f"Could not find word '{word_to_find}' in the original script after position {text_pointer}. Appending as plain text.")
                    # Append the word as plain, non-interactive text so it's not lost.
                    html_body_parts.append(word_to_find)

            # Append any remaining text after the last aligned word
            trailing_text = source_text[text_pointer:]
            processed_trailing_text = trailing_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            processed_trailing_text = processed_trailing_text.replace("\n", "<br>\n")
            processed_trailing_text = re.sub(r'(^|<br>\n)(\s*)([\w\s]+:)', r'\1\2<strong>\3</strong>', processed_trailing_text)
            html_body_parts.append(
                processed_trailing_text
            )
            final_html_body = "".join(html_body_parts)

            # --- 5. Generate HTML ---
            # Sanitize the title to create a safe filename
            safe_filename = re.sub(r'[^\w\s-]', '', title).strip().lower()
            safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
            if not safe_filename:
                # Fallback if the title contains only special characters
                safe_filename = "podcast_demo"
            
            # Determine the output directory for the demo files
            if output_dir:
                final_output_dir = output_dir
                os.makedirs(final_output_dir, exist_ok=True)
                # Copy the audio file to the output directory so the relative path works
                shutil.copy(audio_filepath, final_output_dir)
            else:
                final_output_dir = os.path.dirname(audio_filepath)

            html_filepath = os.path.join(final_output_dir, f"{safe_filename}.html")

            subtitle_html = f'<h2>{subtitle.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</h2>' if subtitle else ""

            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width:800px; margin:2rem auto; line-height:1.6; }}
    h1 {{ margin-bottom: 0.5rem; }}
    h2 {{ margin-top: 0; color: #666; font-weight: normal; font-size: 1.2rem; }}
    audio {{ width:100%; margin:1rem 0; }}
    .word {{ padding:0 2px; transition:background 0.2s; cursor: pointer; }}
    .highlight {{ background:#ffe08a; border-radius:3px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {subtitle_html}
  <audio id="player" controls src="{os.path.basename(audio_filepath)}"></audio>
  <p id="transcript">{final_html_body}</p>
  <script>
    const audio = document.getElementById("player");
    const words = document.querySelectorAll(".word");
    audio.addEventListener("timeupdate", () => {{
      const t = audio.currentTime;
      words.forEach(w => {{
        const start = parseFloat(w.dataset.start);
        const end = parseFloat(w.dataset.end);
        w.classList.toggle("highlight", t >= start && t < end);
      }});
    }});
  </script>
</body>
</html>"""

            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_template)

            webbrowser.open("file://" + os.path.abspath(html_filepath))
            status_callback(f"Demo generated and opened: {os.path.basename(html_filepath)}")

        except Exception as e:
            status_callback(f"Demo generation failed: {e}")
            logger.error(f"HTML demo generation failed: {e}", exc_info=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a synchronized HTML demo from an audio file and a text script.",
        epilog="Example: python create_demo.py my_podcast.mp3 my_script.txt"
    )
    parser.add_argument("audio_file", help="Path to the audio file (e.g., .mp3, .wav).")
    parser.add_argument("script_file", help="Path to the text script file (.txt).")
    parser.add_argument(
        "--title",
        default="Podcast Demo",
        help="The title for the generated HTML page. (default: %(default)s)"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory to save the generated HTML and audio file. (default: same as audio file)"
    )
    parser.add_argument(
        "--subtitle",
        help="An optional subtitle for the generated HTML page."
    )
    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found at '{args.audio_file}'")
        sys.exit(1)
    if not os.path.exists(args.script_file):
        print(f"Error: Script file not found at '{args.script_file}'")
        sys.exit(1)

    # Set logging to DEBUG for detailed output, especially for Aeneas.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    create_html_demo(args.script_file, args.audio_file, title=args.title, subtitle=args.subtitle, output_dir=args.output_dir)