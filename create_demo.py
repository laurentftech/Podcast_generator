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
import re
import unicodedata
from difflib import SequenceMatcher

def interpolate_missing_words(segments):
    """Interpole les timings des mots manqués entre des mots alignés."""
    interpolated_count = 0
    failed_count = 0

    for i, segment in enumerate(segments):
        if segment['type'] == 'word' and not segment.get('timing'):
            prev_word, next_word = find_adjacent_timed_words(segments, i)

            if prev_word and next_word:
                # Calculer la position relative du mot dans la séquence
                words_between = next_word['index'] - prev_word['index'] - 1
                word_position = i - prev_word['index']

                # Interpolation linéaire
                prev_end = prev_word['timing']['end']
                next_start = next_word['timing']['start']
                total_duration = next_start - prev_end

                # Répartir le temps entre les mots manqués
                word_duration = total_duration / (words_between + 1)
                word_start = prev_end + (word_position * word_duration)
                word_end = word_start + word_duration

                segment['timing'] = {
                    'start': round(word_start, 3),
                    'end': round(word_end, 3)
                }

                interpolated_count += 1
                # ✅ CORRECTION: Éviter les accolades qui interfèrent avec .format()
                prev_timing = f"{prev_word['timing']['start']:.3f}-{prev_word['timing']['end']:.3f}s"
                next_timing = f"{next_word['timing']['start']:.3f}-{next_word['timing']['end']:.3f}s"
                new_timing = f"{segment['timing']['start']:.3f}-{segment['timing']['end']:.3f}s"
                print(f"INTERPOLÉ: '{segment['text']}' -> {new_timing} (entre {prev_timing} et {next_timing})")
            else:
                failed_count += 1
                prev_text = f"{prev_word['timing']['start']:.3f}s" if prev_word else "NONE"
                next_text = f"{next_word['timing']['start']:.3f}s" if next_word else "NONE"
                print(f"ÉCHEC interpolation: '{segment['text']}' (prev: {prev_text}, next: {next_text})")

    print(f"Interpolation: {interpolated_count} réussies, {failed_count} échecs")
    return segments  # ✅ AJOUT DU RETURN


def find_adjacent_timed_words(segments, current_index):
    """Trouve le mot précédent et suivant avec timing."""
    prev_word = None
    next_word = None

    # Chercher le mot précédent avec timing
    for i in range(current_index - 1, -1, -1):
        if segments[i]['type'] == 'word' and segments[i].get('timing'):
            prev_word = {'index': i, 'timing': segments[i]['timing']}
            break

    # Chercher le mot suivant avec timing
    for i in range(current_index + 1, len(segments)):
        if segments[i]['type'] == 'word' and segments[i].get('timing'):
            next_word = {'index': i, 'timing': segments[i]['timing']}
            break

    return prev_word, next_word


def fix_word_timings(segments):
    """Corrige les timings incohérents et trop courts."""
    word_segments = [s for s in segments if s['type'] == 'word' and s.get('timing')]
    corrections_made = 0

    # 1. PREMIÈRE PASSE: Corriger les timings inversés (start > end)
    for segment in word_segments:
        timing = segment['timing']
        if timing['start'] > timing['end']:
            # Inverser start et end
            timing['start'], timing['end'] = timing['end'], timing['start']
            corrections_made += 1
            print(f"TIMING INVERSÉ CORRIGÉ: '{segment['text']}' -> {timing['start']:.3f}-{timing['end']:.3f}s")

    # 2. DEUXIÈME PASSE: Durées minimales et chevauchements
    for i, segment in enumerate(word_segments):
        timing = segment['timing']
        original_end = timing['end']

        # 2a. Durée minimale de 0.15s
        duration = timing['end'] - timing['start']
        if duration < 0.15:
            timing['end'] = timing['start'] + 0.15
            corrections_made += 1
            print(f"DURÉE CORRIGÉE: '{segment['text']}' {duration:.3f}s -> 0.150s")

        # 2b. Éviter les chevauchements avec le mot suivant
        if i < len(word_segments) - 1:
            next_timing = word_segments[i + 1]['timing']
            if timing['end'] > next_timing['start']:
                # Calculer un compromis: partager l'espace disponible
                overlap_zone = timing['end'] - next_timing['start']
                gap_duration = 0.02  # 20ms de pause minimum

                # Répartir l'espace entre les deux mots
                available_space = timing['end'] - timing['start'] + next_timing['end'] - next_timing['start']
                mid_point = (timing['start'] + next_timing['end']) / 2

                # Ajuster intelligemment
                new_end = mid_point - gap_duration
                if new_end > timing['start'] + 0.1:  # Durée minimum de 100ms
                    timing['end'] = new_end
                    next_timing['start'] = mid_point + gap_duration
                    corrections_made += 2
                    print(f"CHEVAUCHEMENT INTELLIGENT: '{segment['text']}' {original_end:.3f}s -> {timing['end']:.3f}s")
                else:
                    # Fallback: juste éviter le chevauchement
                    timing['end'] = next_timing['start'] - 0.01
                    corrections_made += 1
                    print(f"CHEVAUCHEMENT SIMPLE: '{segment['text']}' {original_end:.3f}s -> {timing['end']:.3f}s")

    # 3. TROISIÈME PASSE: Vérifier qu'aucun mot n'a une durée trop courte après corrections
    for segment in word_segments:
        timing = segment['timing']
        duration = timing['end'] - timing['start']
        if duration < 0.05:  # Moins de 50ms = invisible
            timing['end'] = timing['start'] + 0.15
            corrections_made += 1
            print(f"DURÉE TROP COURTE APRÈS CORRECTION: '{segment['text']}' -> 0.150s")

    print(f"Corrections de timing: {corrections_made} ajustements effectués")
    return segments

def _prepare_scripts(original_script_text: str) -> tuple[str, str]:
    """
    Prepares two versions of the script:
    1. A clean version for MFA alignment (no speaker names, no annotations).
    2. A display version for the final HTML (speaker names and annotations preserved).
    """
    # The display version is the original text with normalized apostrophes.
    display_text_normalized = original_script_text.replace("â€™", "'").replace("`", "'")

    # The MFA version is created by cleaning the display version.
    # 1. Remove annotations.
    mfa_text_intermediate = re.sub(r'[<\[][^>\]]*[>\]]', '', display_text_normalized)
    # 2. Remove speaker names.
    mfa_text_normalized = re.sub(r'^\s*[\w\s]+:\s*', '', mfa_text_intermediate, flags=re.MULTILINE)

    mfa_text_normalized = normalize_text_for_mfa(mfa_text_normalized)

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


def _get_html_template() -> str:
    """Loads the HTML template from a file."""
    logger = logging.getLogger("PodcastGenerator.Demo")
    # Assumes the template is in a 'docs' folder relative to this script
    script_dir = os.path.dirname(__file__)
    template_path = os.path.join(script_dir, 'docs', 'demo_template.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"HTML template file not found at {template_path}. Cannot generate demo.")
        raise


def normalize_word(word):
    """Normalise un mot pour comparaison tolérante."""
    word = word.lower()
    word = word.replace("â€™", "'")  # uniformiser les apostrophes
    word = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9]", "", word)


def similar(a, b, threshold=0.7):
    """Retourne True si deux mots sont similaires (tolérance aux petites différences)."""
    return SequenceMatcher(None, normalize_word(a), normalize_word(b)).ratio() >= threshold


def create_word_mapping(source_text: str, mfa_transcript: list, debug: bool = False):
    """
    Crée un mapping entre texte original et MFA.
    Retourne les segments du texte avec leur type et timing éventuel.
    """
    segments = []
    mfa_index = 0
    i = 0

    # Statistiques pour debugging
    total_mfa_words = len(mfa_transcript)
    matched_words = 0
    unmatched_words = 0

    while i < len(source_text):
        # Détection des noms de locuteurs (format: "Nom: ")
        speaker_match = re.match(r'^([A-Z][a-zA-Z\s]+):\s*', source_text[i:], re.MULTILINE)
        if speaker_match:
            speaker_text = speaker_match.group(0)
            segments.append({
                'type': 'speaker',
                'text': speaker_text,
                'start_pos': i,
                'end_pos': i + len(speaker_text)
            })
            i += len(speaker_text)
            continue

        # Détection des annotations (format: <annotation> ou [annotation])
        annotation_match = re.match(r'(<[^>]+>|\[[^\]]+\])', source_text[i:])
        if annotation_match:
            annotation_text = annotation_match.group(1)  # groupe 1 = annotation complète
            segments.append({
                'type': 'annotation',
                'text': annotation_text,
                'start_pos': i,
                'end_pos': i + len(annotation_text)
            })
            i += len(annotation_text)
            continue

        # Détection des mots
        word_match = re.match(r"\b[\w'â€™-]+\b", source_text[i:])
        if word_match:
            word_text = word_match.group(0)

            # Essayer de mapper avec MFA
            timing_info = None

            # Recherche du meilleur match dans une fenêtre autour de mfa_index
            best_match_index = None
            best_similarity = 0
            search_window = 3  # Chercher dans un rayon de 3 mots

            # Définir les limites de recherche
            start_search = max(0, mfa_index - search_window)
            end_search = min(len(mfa_transcript), mfa_index + search_window + 1)

            for search_idx in range(start_search, end_search):
                if search_idx < len(mfa_transcript):
                    mfa_word = mfa_transcript[search_idx]["word"]
                    if mfa_word != "<unk>":
                        similarity = SequenceMatcher(None, normalize_word(word_text), normalize_word(mfa_word)).ratio()
                        if similarity > best_similarity and similarity >= 0.5:  # Seuil plus bas
                            best_similarity = similarity
                            best_match_index = search_idx

            # Si on a trouvé un bon match
            if best_match_index is not None:
                timing_info = {
                    "start": mfa_transcript[best_match_index]["start"],
                    "end": mfa_transcript[best_match_index]["end"]
                }
                mfa_index = best_match_index + 1
                matched_words += 1

                if debug and best_match_index != mfa_index - 1:
                    print(
                        f"Fenêtre de recherche utilisée: '{word_text}' -> '{mfa_transcript[best_match_index]['word']}' (similarity: {best_similarity:.2f}, offset: {best_match_index - (mfa_index - 1)})")

            # Si aucun match trouvé et qu'il reste des mots MFA, avancer d'un cran
            elif mfa_index < len(mfa_transcript):
                if debug:
                    current_mfa = mfa_transcript[mfa_index]["word"] if mfa_index < len(mfa_transcript) else "END"
                    print(
                        f"No match found: source='{word_text}' vs mfa='{current_mfa}' (position {i}, mfa_index {mfa_index})")
                unmatched_words += 1

                # Stratégie adaptative : si on a trop de mots non-matchés consécutifs,
                # on avance dans MFA pour essayer de resynchroniser
                if unmatched_words % 3 == 0 and mfa_index < len(mfa_transcript) - 1:
                    mfa_index += 1
                    if debug:
                        print(f"Advancing MFA index for resync: {mfa_index}")

            segments.append({
                'type': 'word',
                'text': word_text,
                'start_pos': i,
                'end_pos': i + len(word_text),
                'timing': timing_info
            })
            i += len(word_text)
            continue

        # Caractère simple (espaces, ponctuation, etc.)
        segments.append({
            'type': 'text',
            'text': source_text[i],
            'start_pos': i,
            'end_pos': i + 1
        })
        i += 1

    # Afficher les statistiques si debug activé
    if debug:
        print(f"\n=== Statistiques d'alignement ===")
        print(f"Mots MFA disponibles: {total_mfa_words}")
        print(f"Mots matchés: {matched_words}")
        print(f"Mots non-matchés: {unmatched_words}")
        print(f"Taux de réussite: {matched_words / (matched_words + unmatched_words) * 100:.1f}%")
        print(f"MFA index final: {mfa_index}")

    return segments


def reconstruct_html_with_timing(segments):
    """Reconstruit le HTML à partir des segments analysés."""
    html_parts = []
    word_counter = 0  # Compteur unique pour éviter les conflits de timing

    for segment in segments:
        if segment['type'] == 'speaker':
            # Nom de locuteur en gras
            html_parts.append(f"<strong>{segment['text']}</strong>")
        elif segment['type'] == 'annotation':
            # Extraire le contenu sans les délimiteurs < > ou [ ]
            annotation_content = re.sub(r'[<>\[\]]', '', segment['text'])
            html_parts.append(f"<em>{annotation_content}</em>")  # FIX: utiliser annotation_content
        elif segment['type'] == 'word' and segment.get('timing'):
            # Mot avec timing pour l'effet karaoke - ID unique pour éviter les conflits
            timing = segment['timing']
            html_parts.append(
                f'<span class="word" data-start="{timing["start"]}" data-end="{timing["end"]}" data-word-id="{word_counter}">{segment["text"]}</span>'
            )
            word_counter += 1
        else:
            # Texte simple (mots sans timing, espaces, ponctuation)
            text = segment['text']
            # Convertir les retours à la ligne en <br>
            if '\n' in text:
                text = text.replace('\n', '<br>')
            html_parts.append(text)

    return ''.join(html_parts)


def normalize_text_for_mfa(text):
    # Normaliser les apostrophes
    text = text.replace("'", "'")
    text = text.replace("'", "'")
    # Normaliser les guillemets si nécessaire
    text = text.replace(""", '"')
    text = text.replace(""", '"')
    return text

def create_html_demo(script_filepath: str, audio_filepath: str, title: str = "Podcast Demo", subtitle: str = None,
                     output_dir: str = None, status_callback=print):
    """
    Génère une démo HTML synchronisée depuis un script et son audio.
    Utilise Montreal Forced Aligner (MFA) pour aligner mot à mot.
    """
    logger = logging.getLogger("PodcastGenerator.Demo")
    # Using 'mfa' directly relies on it being in the system's PATH.
    # This is the correct approach for an external dependency and avoids
    # the infinite loop issue with frozen apps, where sys.executable
    # would point to the app bundle itself.
    mfa_base_command = ["mfa"]

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

            # Analyser le texte en segments avec debug activé
            segments = create_word_mapping(display_script_text, transcript_from_mfa, debug=True)

            # Appliquer les corrections en chaîne
            segments = interpolate_missing_words(segments)  # ✅ RÉCUPÉRER LE RÉSULTAT
            segments = fix_word_timings(segments)  # ✅ RÉCUPÉRER LE RÉSULTAT

            # Reconstruire le HTML final
            final_html_body = reconstruct_html_with_timing(segments)

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

            html_template = _get_html_template()
            html_content = html_template.format(
                title=title,
                subtitle_html=subtitle_html,
                audio_filename=os.path.basename(audio_filepath),
                final_html_body=final_html_body
            )

            with open(html_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            webbrowser.open("file://" + os.path.abspath(html_filepath))
            status_callback(f"Demo generated and opened: {os.path.basename(html_filepath)}")

        except Exception as e:
            status_callback(f"Demo generation failed: {e}")
            logger.error(f"HTML demo generation failed: {e}", exc_info=True)


if __name__ == "__main__":
    # This is crucial for preventing infinite loops if this script were
    # ever to be frozen with PyInstaller on macOS and Windows.
    import multiprocessing

    multiprocessing.freeze_support()

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
    create_html_demo(args.script_file, args.audio_file, title=args.title, subtitle=args.subtitle,
                     output_dir=args.output_dir)