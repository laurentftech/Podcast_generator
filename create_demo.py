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


def _clean_script(script_text: str) -> str:
    """
    Cleans the script text to keep only the spoken words for the aligner.
    Removes speaker names, annotations, and instructions.
    """
    # Remove speaker names like "John: "
    cleaned_text = re.sub(r'^\s*[\w\s]+:\s*', '', script_text, flags=re.MULTILINE)
    # Remove annotations in brackets or angle brackets like "[playful]" or "<playful>"
    cleaned_text = re.sub(r'[<\[][^>\]]*[>\]]', '', cleaned_text)
    # Remove lines that seem to be instructions and clean up
    lines = []
    for line in cleaned_text.splitlines():
        if "aloud" not in line.lower() and "tone" not in line.lower() and line.strip():
            lines.append(line.strip())
    return " ".join(lines)

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

def _setup_mfa_models(dictionary: str, acoustic_model: str, mfa_base_command: list, status_callback=print):
    """Checks for MFA models and downloads them if not present."""
    logger = logging.getLogger("PodcastGenerator.Demo")

    # Check dictionary model
    check_dict_cmd = mfa_base_command + ["model", "inspect", "dictionary", dictionary]
    logger.debug(f"Checking for MFA dictionary: {' '.join(check_dict_cmd)}")
    if subprocess.run(check_dict_cmd, capture_output=True).returncode != 0:
        status_callback(f"MFA dictionary '{dictionary}' not found. Downloading...")
        download_dict_cmd = mfa_base_command + ["model", "download", "dictionary", dictionary]
        logger.debug(f"Running: {' '.join(download_dict_cmd)}")
        result = subprocess.run(download_dict_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download MFA dictionary '{dictionary}'.\nError: {result.stderr}")
        status_callback("Dictionary downloaded successfully.")

    # Check acoustic model
    check_acoustic_cmd = mfa_base_command + ["model", "inspect", "acoustic", acoustic_model]
    logger.debug(f"Checking for MFA acoustic model: {' '.join(check_acoustic_cmd)}")
    if subprocess.run(check_acoustic_cmd, capture_output=True).returncode != 0:
        status_callback(f"MFA acoustic model '{acoustic_model}' not found. Downloading...")
        download_acoustic_cmd = mfa_base_command + ["model", "download", "acoustic", acoustic_model]
        logger.debug(f"Running: {' '.join(download_acoustic_cmd)}")
        result = subprocess.run(download_acoustic_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to download MFA acoustic model '{acoustic_model}'.\nError: {result.stderr}")
        status_callback("Acoustic model downloaded successfully.")

def create_html_demo(script_filepath: str, audio_filepath: str, status_callback=print):
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
        version_result = subprocess.run(
            mfa_base_command + ["version"], capture_output=True, text=True, check=True
        )
        version_str = version_result.stdout.strip().split()[-1] # e.g. 'mfa, version 2.2.17' -> '2.2.17'
        major_version = int(version_str.split('.')[0])
        if major_version < 2:
            raise RuntimeError(f"Your installed MFA version ({version_str}) is too old. Version 2.0 or higher is required for automatic model downloads.")
        logger.info(f"Found compatible MFA version: {version_str}")
    except Exception as e:
        error_msg = (
            "Could not run Montreal Forced Aligner (MFA).\n"
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
    with tempfile.TemporaryDirectory() as corpus_dir, tempfile.TemporaryDirectory() as output_dir:
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
            cleaned_script_text = _clean_script(original_script_text)
            temp_script_filepath = os.path.join(corpus_dir, f"{base_name}.txt")
            with open(temp_script_filepath, "w", encoding="utf-8") as f:
                f.write(cleaned_script_text)

            status_callback("Corpus prepared. Starting alignment with MFA (this may take a moment)...")

            # --- 3. Run MFA Aligner ---
            mfa_command = mfa_base_command + [
                "align", corpus_dir, dictionary_model, acoustic_model, output_dir,
                "--clean", "--quiet", "--use_punctuation"
            ]
            logger.debug(f"Executing MFA: {' '.join(mfa_command)}")
            result = subprocess.run(mfa_command, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error("MFA alignment failed.")
                logger.error(f"  - STDOUT: {result.stdout}")
                logger.error(f"  - STDERR: {result.stderr}")
                raise RuntimeError(f"MFA alignment failed. See logs for details. Error: {result.stderr or result.stdout}")

            status_callback("MFA alignment successful.")

            # --- 4. Parse TextGrid Output ---
            textgrid_filepath = os.path.join(output_dir, f"{base_name}.TextGrid")
            transcript_from_mfa = _parse_textgrid(textgrid_filepath)
            if not transcript_from_mfa:
                raise RuntimeError("Failed to parse TextGrid output or no words were aligned.")

            # Reconstruct transcript with correct spacing for display
            transcript = []
            for i, item in enumerate(transcript_from_mfa):
                current_word = item['word']
                # Add a space after the word, unless it's the last word or the next word is punctuation.
                add_space = (i + 1) < len(transcript_from_mfa) and transcript_from_mfa[i+1]['word'].isalnum()

                transcript.append({
                    "word": current_word + (" " if add_space else ""),
                    "start": item['start'],
                    "end": item['end']
                })

            # --- 5. Generate HTML ---
            html_filepath = os.path.splitext(audio_filepath)[0] + ".html"
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Podcast Demo</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width:800px; margin:2rem auto; line-height:1.6; }}
    audio {{ width:100%; margin:1rem 0; }}
    .word {{ padding:0 2px; transition:background 0.2s; cursor: pointer; }}
    .highlight {{ background:#ffe08a; border-radius:3px; }}
  </style>
</head>
<body>
  <h1>Podcast Demo</h1>
  <audio id="player" controls src="{os.path.basename(audio_filepath)}"></audio>
  <p id="transcript"></p>
  <script>
    const transcript = {json.dumps(transcript, ensure_ascii=False)};
    const container = document.getElementById("transcript");
    transcript.forEach(item => {{
      const span = document.createElement("span");
      span.textContent = item.word;
      span.classList.add("word");
      span.dataset.start = item.start;
      span.dataset.end = item.end;
      span.onclick = () => {{ audio.currentTime = item.start; }};
      container.appendChild(span);
    }});
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
    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found at '{args.audio_file}'")
        sys.exit(1)
    if not os.path.exists(args.script_file):
        print(f"Error: Script file not found at '{args.script_file}'")
        sys.exit(1)

    # Set logging to DEBUG for detailed output, especially for Aeneas.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    create_html_demo(args.script_file, args.audio_file)