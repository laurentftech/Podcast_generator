import argparse
import os
import sys
import json
import webbrowser
import logging
import re
import tempfile
import shutil
import sys
import types

import torio._extension.utils as torio_utils

torio_utils._TORIO_EXTENSION_AVAILABLE = False

import torch
import torchaudio

# Configuration pour macOS Intel
torch.set_num_threads(1)  # Évite les problèmes de concurrence sur macOS Intel
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

from difflib import SequenceMatcher
import unicodedata


def interpolate_missing_words(segments):
    """Interpole les timings des mots manqués entre des mots alignés."""
    interpolated_count = 0
    failed_count = 0

    for i, segment in enumerate(segments):
        if segment['type'] == 'word' and not segment.get('timing'):
            prev_word, next_word = find_adjacent_timed_words(segments, i)

            if prev_word and next_word:
                words_between = next_word['index'] - prev_word['index'] - 1
                word_position = i - prev_word['index']

                prev_end = prev_word['timing']['end']
                next_start = next_word['timing']['start']
                total_duration = next_start - prev_end

                word_duration = total_duration / (words_between + 1)
                word_start = prev_end + (word_position * word_duration)
                word_end = word_start + word_duration

                segment['timing'] = {
                    'start': round(word_start, 3),
                    'end': round(word_end, 3)
                }

                interpolated_count += 1
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
    return segments


def find_adjacent_timed_words(segments, current_index):
    """Trouve le mot précédent et suivant avec timing."""
    prev_word = None
    next_word = None

    for i in range(current_index - 1, -1, -1):
        if segments[i]['type'] == 'word' and segments[i].get('timing'):
            prev_word = {'index': i, 'timing': segments[i]['timing']}
            break

    for i in range(current_index + 1, len(segments)):
        if segments[i]['type'] == 'word' and segments[i].get('timing'):
            next_word = {'index': i, 'timing': segments[i]['timing']}
            break

    return prev_word, next_word


def fix_word_timings(segments):
    """Corrige les timings incohérents avec une approche plus conservative."""
    word_segments = [s for s in segments if s['type'] == 'word' and s.get('timing')]
    corrections_made = 0

    print(f"Correction des timings pour {len(word_segments)} mots...")

    # Phase 1: Corriger les timings inversés
    for segment in word_segments:
        timing = segment['timing']
        if timing['start'] > timing['end']:
            timing['start'], timing['end'] = timing['end'], timing['start']
            corrections_made += 1
            print(f"TIMING INVERSÉ: '{segment['text']}' -> {timing['start']:.3f}-{timing['end']:.3f}s")

    # Phase 2: Traiter les chevauchements (plus conservative)
    for i in range(len(word_segments) - 1):
        current_timing = word_segments[i]['timing']
        next_timing = word_segments[i + 1]['timing']

        if current_timing['end'] > next_timing['start']:
            # Calculer le point de séparation optimal
            gap = 0.01  # Gap minimal entre les mots
            mid_point = (current_timing['end'] + next_timing['start']) / 2

            # Ajuster seulement si l'ajustement est raisonnable
            new_end = mid_point - gap
            new_start = mid_point + gap

            # Vérifier que les durées restent raisonnables
            current_duration = new_end - current_timing['start']
            next_duration = next_timing['end'] - new_start

            if current_duration > 0.05 and next_duration > 0.05:
                original_end = current_timing['end']
                current_timing['end'] = new_end
                next_timing['start'] = new_start
                corrections_made += 2
                print(f"CHEVAUCHEMENT: '{word_segments[i]['text']}' {original_end:.3f}s -> {new_end:.3f}s")

    # Phase 3: Corriger les durées trop courtes (plus conservatif)
    min_duration = 0.08  # Durée minimale plus réaliste
    for segment in word_segments:
        timing = segment['timing']
        duration = timing['end'] - timing['start']

        if duration < min_duration:
            # Étendre légèrement vers la fin seulement
            timing['end'] = timing['start'] + min_duration
            corrections_made += 1
            print(f"DURÉE COURTE: '{segment['text']}' {duration:.3f}s -> {min_duration:.3f}s")

    print(f"Corrections appliquées: {corrections_made} ajustements")
    return segments


def normalize_word(word):
    """Normalise un mot pour comparaison tolérante."""
    word = word.lower()
    word = word.replace("'", "'")
    word = unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9]", "", word)


def similar(a, b, threshold=0.7):
    """Retourne True si deux mots sont similaires."""
    return SequenceMatcher(None, normalize_word(a), normalize_word(b)).ratio() >= threshold


def create_word_mapping_whisperx(source_text: str, whisperx_result: dict, debug: bool = False):
    """
    Crée un mapping entre texte original et résultats WhisperX.
    Retourne les segments du texte avec leur type et timing éventuel.
    """
    segments = []

    # Extraire les mots avec timings de WhisperX - structure corrigée
    whisperx_words = []

    # Debug: Afficher la structure du résultat
    if debug:
        print("=== Structure du résultat WhisperX ===")
        print(f"Clés principales: {list(whisperx_result.keys())}")

    # Essayer différentes structures possibles
    if 'segments' in whisperx_result:
        for segment in whisperx_result['segments']:
            if debug:
                print(f"Segment: {segment.get('text', 'N/A')[:50]}...")
                print(f"  Clés du segment: {list(segment.keys())}")

            if 'words' in segment:
                for word_info in segment['words']:
                    if debug and len(whisperx_words) < 3:  # Debug pour les 3 premiers mots
                        print(f"  Mot: {word_info}")

                    # Vérifier la structure des mots
                    word_text = None
                    start_time = None
                    end_time = None

                    # Différentes façons dont le mot peut être stocké
                    if 'word' in word_info:
                        word_text = word_info['word'].strip()
                    elif 'text' in word_info:
                        word_text = word_info['text'].strip()

                    # Différentes façons dont les timings peuvent être stockés
                    if 'start' in word_info and 'end' in word_info:
                        start_time = word_info['start']
                        end_time = word_info['end']
                    elif 'timestamp' in word_info:
                        # Certaines versions utilisent 'timestamp'
                        ts = word_info['timestamp']
                        if isinstance(ts, (list, tuple)) and len(ts) >= 2:
                            start_time, end_time = ts[0], ts[1]

                    # Ajouter le mot si toutes les infos sont présentes
                    if word_text and start_time is not None and end_time is not None:
                        whisperx_words.append({
                            'word': word_text,
                            'start': start_time,
                            'end': end_time
                        })

    # Fallback: chercher dans 'word_segments' si disponible
    elif 'word_segments' in whisperx_result:
        for segment in whisperx_result['word_segments']:
            if 'words' in segment:
                for word_info in segment['words']:
                    if 'word' in word_info and 'start' in word_info and 'end' in word_info:
                        whisperx_words.append({
                            'word': word_info['word'].strip(),
                            'start': word_info['start'],
                            'end': word_info['end']
                        })

    print(f"WhisperX a trouvé {len(whisperx_words)} mots avec timing")

    # Afficher quelques exemples de mots trouvés
    if debug and whisperx_words:
        print("=== Premiers mots avec timing ===")
        for i, word in enumerate(whisperx_words[:5]):
            print(f"  {i}: '{word['word']}' [{word['start']:.3f}-{word['end']:.3f}s]")

    whisperx_index = 0
    i = 0
    matched_words = 0
    unmatched_words = 0
    used_whisperx_indices = set()  # Éviter la réutilisation des mêmes timings

    while i < len(source_text):
        # Détection des noms de locuteurs
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

        # Détection des annotations
        annotation_match = re.match(r'(<[^>]+>|\[[^\]]+\])', source_text[i:])
        if annotation_match:
            annotation_text = annotation_match.group(1)
            segments.append({
                'type': 'annotation',
                'text': annotation_text,
                'start_pos': i,
                'end_pos': i + len(annotation_text)
            })
            i += len(annotation_text)
            continue

        # Détection des séquences d'espaces blancs
        whitespace_match = re.match(r'\s+', source_text[i:])
        if whitespace_match:
            whitespace_text = whitespace_match.group(0)
            segments.append({
                'type': 'text',
                'text': whitespace_text,
                'start_pos': i,
                'end_pos': i + len(whitespace_text)
            })
            i += len(whitespace_text)
            continue

        # Détection des mots
        word_match = re.match(r"\b[\w'''-]+\b", source_text[i:])
        if word_match:
            word_text = word_match.group(0)
            timing_info = None

            # Ignorer certains mots très courts qui n'ont probablement pas de timing
            skip_timing = len(word_text) <= 1 and word_text.lower() in ['i', 'a']

            if not skip_timing:
                # Recherche du meilleur match dans WhisperX
                best_match_index = None
                best_similarity = 0
                search_window = 5  # Fenêtre plus large pour WhisperX

                start_search = max(0, whisperx_index - search_window)
                end_search = min(len(whisperx_words), whisperx_index + search_window + 1)

                for search_idx in range(start_search, end_search):
                    if search_idx < len(whisperx_words) and search_idx not in used_whisperx_indices:
                        whisperx_word = whisperx_words[search_idx]["word"]
                        similarity = SequenceMatcher(None, normalize_word(word_text),
                                                     normalize_word(whisperx_word)).ratio()
                        if similarity > best_similarity and similarity >= 0.6:  # Seuil ajusté
                            best_similarity = similarity
                            best_match_index = search_idx

                if best_match_index is not None:
                    timing_info = {
                        "start": whisperx_words[best_match_index]["start"],
                        "end": whisperx_words[best_match_index]["end"]
                    }
                    used_whisperx_indices.add(best_match_index)  # Marquer comme utilisé
                    whisperx_index = best_match_index + 1
                    matched_words += 1

                    if debug and best_similarity < 0.9:
                        print(
                            f"Match approximatif: '{word_text}' -> '{whisperx_words[best_match_index]['word']}' (sim: {best_similarity:.2f})")

                elif whisperx_index < len(whisperx_words):
                    unmatched_words += 1
                    if debug:
                        current_whisperx = whisperx_words[whisperx_index]["word"] if whisperx_index < len(
                            whisperx_words) else "END"
                        print(f"Mot non aligné: '{word_text}' vs whisperx='{current_whisperx}'")

                    # Avancer plus prudemment pour éviter de perdre des mots
                    if unmatched_words % 2 == 0 and whisperx_index < len(whisperx_words) - 1:
                        whisperx_index += 1

            segments.append({
                'type': 'word',
                'text': word_text,
                'start_pos': i,
                'end_pos': i + len(word_text),
                'timing': timing_info
            })
            i += len(word_text)
            continue

        # Caractère simple
        segments.append({
            'type': 'text',
            'text': source_text[i],
            'start_pos': i,
            'end_pos': i + 1
        })
        i += 1

    if debug:
        print(f"\n=== Statistiques WhisperX ===")
        print(f"Mots WhisperX disponibles: {len(whisperx_words)}")
        print(f"Mots matchés: {matched_words}")
        print(f"Mots non-matchés: {unmatched_words}")
        if matched_words + unmatched_words > 0:
            print(f"Taux de réussite: {matched_words / (matched_words + unmatched_words) * 100:.1f}%")

    return segments


def reconstruct_html_with_timing(segments):
    """Reconstruit le HTML à partir des segments analysés avec validation des timings."""
    html_parts = []
    word_counter = 0
    words_with_timing = 0
    words_without_timing = 0

    for segment in segments:
        if segment['type'] == 'speaker':
            html_parts.append(f"<strong>{segment['text']}</strong>")
        elif segment['type'] == 'annotation':
            annotation_content = re.sub(r'[<>\[\]]', '', segment['text'])
            html_parts.append(f"<em>{annotation_content}</em>")
        elif segment['type'] == 'word':
            if segment.get('timing') and segment['timing']['start'] < segment['timing']['end']:
                # Mot avec timing valide
                timing = segment['timing']
                html_parts.append(
                    f'<span class="word" data-start="{timing["start"]}" data-end="{timing["end"]}" data-word-id="{word_counter}">{segment["text"]}</span>'
                )
                word_counter += 1
                words_with_timing += 1
            else:
                # Mot sans timing - affiché normalement
                html_parts.append(segment['text'])
                words_without_timing += 1
        else:
            # Texte normal, ponctuation, espaces
            text = segment['text']
            if '\n' in text:
                text = text.replace('\n', '<br>')
            html_parts.append(text)

    print(f"HTML généré: {words_with_timing} mots avec timing, {words_without_timing} mots sans timing")
    return ''.join(html_parts)


def _get_html_template() -> str:
    """Loads the HTML template from a file."""
    logger = logging.getLogger("PodcastGenerator.Demo")
    script_dir = os.path.dirname(__file__)
    template_path = os.path.join(script_dir, 'docs', 'demo_template.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"HTML template file not found at {template_path}. Cannot generate demo.")
        raise


def create_html_demo_whisperx(script_filepath: str, audio_filepath: str, title: str = "Podcast Demo",
                              subtitle: str = None, output_dir: str = None, status_callback=print,
                              language: str = "auto"):
    """
    Génère une démo HTML synchronisée avec WhisperX pour l'alignement.

    Args:
        language: Code de langue (ex: "en", "fr", "es") ou "auto" pour détection automatique
    """
    logger = logging.getLogger("PodcastGenerator.Demo")

    try:
        import whisperx
    except ImportError:
        error_msg = "WhisperX n'est pas installé. Installez-le avec: pip install whisperx"
        status_callback(error_msg)
        logger.error(error_msg)
        return

    try:
        # --- 1. Charger le modèle WhisperX ---
        status_callback("Chargement du modèle WhisperX...")

        # Configuration spécifique pour macOS Intel
        device = "cpu"  # Force CPU sur macOS Intel pour éviter les problèmes CUDA/MPS
        compute_type = "int8"  # Plus stable sur CPU

        # Charger avec des paramètres optimisés pour macOS Intel
        model = whisperx.load_model("small", device, compute_type=compute_type)  # Modèle plus petit
        status_callback(f"Modèle WhisperX chargé (device: {device})")

        # --- 2. Transcription et alignement ---
        status_callback("Chargement de l'audio...")
        audio = whisperx.load_audio(audio_filepath)

        status_callback("Transcription avec WhisperX (ceci peut prendre du temps sur CPU)...")

        # Déterminer la langue à utiliser
        transcribe_params = {
            "batch_size": 4,  # Batch size réduit pour CPU
            "verbose": True,
            "task": "transcribe"
        }

        if language != "auto":
            transcribe_params["language"] = language
            status_callback(f"Transcription forcée en {language}")
        else:
            status_callback("Transcription avec détection automatique de langue")

        result = model.transcribe(audio, **transcribe_params)

        detected_language = result.get('language', 'inconnu')
        status_callback(f"Transcription terminée. Langue détectée: {detected_language}")

        # Vérifier si des segments ont été trouvés
        if not result.get('segments'):
            status_callback("Aucun segment trouvé dans la transcription. Vérifiez votre fichier audio.")
            return

        status_callback("Chargement du modèle d'alignement...")

        # Utiliser la langue spécifiée ou détectée
        alignment_language = language if language != "auto" else detected_language

        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=alignment_language,
                device=device
            )
            status_callback(f"Modèle d'alignement chargé pour: {alignment_language}")
        except Exception as e:
            status_callback(f"Erreur avec {alignment_language}: {e}")
            status_callback("Tentative avec anglais par défaut...")
            try:
                model_a, metadata = whisperx.load_align_model(
                    language_code="en",
                    device=device
                )
            except Exception as e2:
                status_callback(f"Erreur avec anglais: {e2}")
                return

        status_callback("Alignement des mots...")
        aligned_result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False
        )

        # Mettre à jour result avec les données alignées
        result.update(aligned_result)

        print(f"WhisperX - Language détectée: {result.get('language', 'inconnu')}")
        print(f"WhisperX - Segments trouvés: {len(result.get('segments', []))}")

        # Affichage détaillé des informations de debug
        total_words_with_timing = 0
        for i, segment in enumerate(result.get('segments', [])[:3]):  # Premiers 3 segments
            print(f"Segment {i}: {segment.get('text', 'N/A')[:50]}...")
            print(f"  - Clés disponibles: {list(segment.keys())}")
            if 'words' in segment:
                words_count = len(segment['words'])
                total_words_with_timing += words_count
                print(f"  - Mots avec timing: {words_count}")
                # Afficher les premiers mots pour debug
                for j, word in enumerate(segment['words'][:3]):
                    print(f"    Mot {j}: {word}")

        print(f"Total de mots avec timing dans les 3 premiers segments: {total_words_with_timing}")

        # --- 3. Lire le script original ---
        with open(script_filepath, "r", encoding="utf-8") as f:
            original_script_text = f.read()

        # --- 4. Créer le mapping ---
        status_callback("Création du mapping texte-audio...")
        segments = create_word_mapping_whisperx(original_script_text, result, debug=False)  # Désactiver debug verbose

        # --- 5. Appliquer les corrections ---
        segments = interpolate_missing_words(segments)
        segments = fix_word_timings(segments)

        # --- 6. Générer le HTML ---
        final_html_body = reconstruct_html_with_timing(segments)

        # --- 7. Sauvegarder ---
        safe_filename = re.sub(r'[^\w\s-]', '', title).strip().lower()
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        if not safe_filename:
            safe_filename = "podcast_demo"

        if output_dir:
            final_output_dir = output_dir
            os.makedirs(final_output_dir, exist_ok=True)
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
        status_callback(f"Démo WhisperX générée et ouverte: {os.path.basename(html_filepath)}")

    except Exception as e:
        status_callback(f"Erreur WhisperX: {e}")
        logger.error(f"WhisperX demo generation failed: {e}", exc_info=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        description="Generate a synchronized HTML demo using WhisperX for word-level alignment.",
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
    parser.add_argument(
        "--language",
        default="auto",
        help="Language code for transcription (en, fr, es, etc.) or 'auto' for automatic detection. (default: %(default)s)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found at '{args.audio_file}'")
        sys.exit(1)
    if not os.path.exists(args.script_file):
        print(f"Error: Script file not found at '{args.script_file}'")
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    create_html_demo_whisperx(args.script_file, args.audio_file, title=args.title,
                              subtitle=args.subtitle, output_dir=args.output_dir,
                              language=args.language)