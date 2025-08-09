# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import logging
import mimetypes
import os
import sys
import struct
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# On importe les outils pour la boîte de dialogue
import tkinter as tk
from tkinter import simpledialog, messagebox

# Le script du podcast est maintenant une constante pour être utilisé par le mode console.
PODCAST_SCRIPT = """Read aloud in a warm, welcoming tone
John: Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs – my dogs' names are corgis! Who am I?
Samantha: [amused] Queen Elizabeth II!
"""

def save_binary_file(file_name: str, data: bytes, status_callback=print):
    """Sauvegarde les données binaires dans un fichier de manière sécurisée."""
    try:
        with open(file_name, "wb") as f:
            f.write(data)
        status_callback(f"Fichier sauvegardé : {file_name}")
    except IOError as e:
        status_callback(f"Erreur lors de la sauvegarde du fichier {file_name}: {e}")

def setup_logging() -> logging.Logger:
    """Configure le logging pour écrire dans un fichier dans le dossier de l'application."""
    logger = logging.getLogger("PodcastCreator")
    if logger.hasHandlers(): # Évite d'ajouter des handlers en double
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
    """Retourne le chemin du dossier de configuration standard pour l'application."""
    app_name = "PodcastCreator"
    if sys.platform == "darwin": # macOS
        return os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    elif sys.platform == "win32": # Windows
        return os.path.join(os.environ['APPDATA'], app_name)
    else: # Linux et autres
        return os.path.join(os.path.expanduser('~'), '.config', app_name)

def get_api_key(status_callback, logger: logging.Logger, parent_window=None) -> str | None:
    """
    Trouve la clé API. Si elle n'est pas trouvée, demande à l'utilisateur et la sauvegarde.
    """
    logger.info("="*20)
    logger.info("Début de la recherche de la clé API...")
    # 1. Définir les chemins de configuration et chercher une clé existante
    app_data_dir = get_app_data_dir()
    primary_dotenv_path = os.path.join(app_data_dir, '.env')
    api_key = None

    # Chemin portable (à côté de l'exécutable)
    if getattr(sys, 'frozen', False):
        portable_path_base = os.path.dirname(sys.executable)
        if sys.platform == "darwin": # Remonter depuis le .app
            portable_path_base = os.path.abspath(os.path.join(portable_path_base, "..", "..", ".."))
    else:
        portable_path_base = os.path.dirname(os.path.abspath(__file__))
    portable_dotenv_path = os.path.join(portable_path_base, '.env')
    logger.info(f"Chemin .env portable vérifié : {portable_dotenv_path}")
    logger.info(f"Chemin .env système vérifié : {primary_dotenv_path}")

    # 2. Chercher un .env existant et charger la clé (priorité au portable)
    dotenv_path_to_load = None
    if os.path.exists(portable_dotenv_path):
        logger.info(f"Fichier .env portable trouvé.")
        dotenv_path_to_load = portable_dotenv_path
    elif os.path.exists(primary_dotenv_path):
        logger.info(f"Fichier .env système trouvé.")
        dotenv_path_to_load = primary_dotenv_path
    else:
        logger.info("Aucun fichier .env trouvé.")

    if dotenv_path_to_load:
        logger.info(f"Chargement des variables depuis : {dotenv_path_to_load}")
        load_dotenv(dotenv_path=dotenv_path_to_load)
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            logger.info("Clé API trouvée dans les variables d'environnement.")
        else:
            logger.info("Fichier .env chargé, mais la variable GEMINI_API_KEY est absente ou vide.")

    # 3. Si la clé n'est toujours pas trouvée (fichier .env absent ou clé vide/blanche), demander à l'utilisateur
    if not api_key or not api_key.strip():
        logger.info("Clé API non trouvée, ouverture de la boîte de dialogue pour l'utilisateur.")
        status_callback("Clé API non trouvée ou invalide. Ouverture de la boîte de dialogue...")

        # Gère la fenêtre parente pour les boîtes de dialogue.
        # Si aucune n'est fournie (mode CLI), on en crée une temporaire.
        dialog_parent = parent_window
        we_created_root = False
        if dialog_parent is None:
            dialog_parent = tk.Tk()
            dialog_parent.withdraw()
            we_created_root = True

        messagebox.showinfo(
            "Bienvenue !",
            "Bienvenue dans le Créateur de Podcast !\n\n"
            "Pour fonctionner, l'application a besoin de votre clé API Google Gemini.\n\n"
            "Vous pouvez en obtenir une gratuitement à l'adresse suivante :\n"
            "https://ai.google.dev/gemini-api",
            parent=dialog_parent
        )
        
        api_key_input = simpledialog.askstring(
            "Clé API requise",
            "Veuillez coller votre clé API Google Gemini :",
            parent=dialog_parent
        )

        if we_created_root:
            dialog_parent.destroy()

        if api_key_input:
            logger.info("L'utilisateur a fourni une clé API.")
            api_key = api_key_input
            os.makedirs(app_data_dir, exist_ok=True)
            with open(primary_dotenv_path, 'w') as f:
                f.write(f'GEMINI_API_KEY="{api_key_input}"')
            logger.info(f"Nouvelle clé sauvegardée dans : {primary_dotenv_path}")
            status_callback("Clé API sauvegardée pour les futurs lancements.")
        else:
            logger.info("L'utilisateur a annulé la saisie de la clé API.")
            status_callback("Aucune clé API fournie. Annulation.")
            return None

    # 4. Retourner la clé
    logger.info("Recherche de la clé API terminée.")
    return api_key

def generate(script_text: str, speaker_mapping: dict, api_key: str, output_basename: str = "podcast_segment", status_callback=print, output_dir: str = ".") -> str | None:
    """Génère l'audio à partir d'un script en utilisant Gemini, avec un fallback de modèle."""
    logger = logging.getLogger("PodcastCreator")
    logger.info("Démarrage de la fonction de génération.")
    status_callback("Démarrage de la génération du podcast...")
    if not api_key:
        return None

    # S'assurer que le dossier de sortie existe
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
    output_path = None
    for model_name in models_to_try:
        status_callback(f"\nTentative de génération avec le modèle : {model_name}...")
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
                    if not final_mime_type:  # On ne stocke le mime_type qu'une seule fois
                        final_mime_type = part.inline_data.mime_type
                else:
                    status_callback(chunk.text)

            if not audio_chunks:
                raise errors.GoogleAPICallError("Aucune donnée audio n'a été générée par le modèle.")

            # Concaténer tous les morceaux audio et sauvegarder en un seul fichier
            full_audio_data = b"".join(audio_chunks)
            file_extension = mimetypes.guess_extension(final_mime_type) or ".wav"
            if file_extension == ".wav" and not final_mime_type.startswith("audio/wav"):
                full_audio_data = convert_to_wav(full_audio_data, final_mime_type)

            output_path = os.path.join(output_dir, f"{output_basename}{file_extension}")
            save_binary_file(output_path, full_audio_data, status_callback)

            status_callback(f"Audio généré avec succès via {model_name}.")
            generated_successfully = True
            break  # Exit the model-selection loop on success
        except errors.APIError as e:
            # Erreur attendue de l'API (ex: modèle non dispo, quota dépassé). C'est normal de continuer.
            status_callback(f"Erreur API avec le modèle '{model_name}'")
            status_callback("Tentative avec le modèle suivant...")
            logger.warning(f"Erreur API avec le modèle '{model_name}': {e}")
        except Exception as e:
            # Erreur inattendue et potentiellement critique (réseau, logique, etc.).
            # On doit arrêter le processus et afficher un maximum d'informations.
            status_callback(f"Une erreur critique inattendue est survenue : {e}")
            status_callback(traceback.format_exc())
            logger.error(f"Erreur critique inattendue: {e}\n{traceback.format_exc()}")
            generated_successfully = False
            break # Inutile de continuer avec d'autres modèles, l'erreur est grave.

    if not generated_successfully:
        status_callback("\nÉchec de la génération audio avec tous les modèles disponibles.")
        return None
    return output_path

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters.

    Args:
        audio_data: The raw audio data as a bytes object.
        mime_type: Mime type of the audio data.

    Returns:
        A bytes object representing the WAV file header.
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size  # 36 bytes for header fields before data chunk size

    # http://soundfile.sapp.org/doc/WaveFormat/

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize (total file size - 8 bytes)
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size (16 for PCM)
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size (size of audio data)
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string.

    Assumes bits per sample is encoded like "L16" and rate as "rate=xxxxx".

    Args:
        mime_type: The audio MIME type string (e.g., "audio/L16;rate=24000").

    Returns:
        A dictionary with "bits_per_sample" and "rate" keys. Values will be
        integers if found, otherwise None.
    """
    # Valeurs par défaut
    bits_per_sample = 16
    rate = 24000

    # Sépare le type principal (ex: "audio/L16") des paramètres (ex: "rate=24000")
    parts = [p.strip() for p in mime_type.split(';')]
    main_type = parts[0]
    params = parts[1:]

    # Extrait les bits par sample depuis le type principal
    if main_type.lower().startswith("audio/l"):
        try:
            bits_per_sample = int(main_type.split('L', 1)[1])
        except (ValueError, IndexError):
            pass  # Garde la valeur par défaut si l'analyse échoue

    # Extrait la fréquence (rate) depuis les paramètres
    for param in params:
        if param.lower().startswith("rate="):
            try:
                rate = int(param.split('=', 1)[1])
            except (ValueError, IndexError):
                pass # Garde la valeur par défaut si l'analyse échoue
            break # Fréquence trouvée, pas besoin de continuer

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    # Pour l'exécution en ligne de commande, on utilise un mapping par défaut.
    logger = setup_logging()
    api_key = get_api_key(print, logger)
    if api_key:
        default_speaker_mapping = {"John": "Schedar", "Samantha": "Zephyr"}
        generate(script_text=PODCAST_SCRIPT, 
                 speaker_mapping=default_speaker_mapping, 
                 api_key=api_key,
                 output_basename="royal_family_quiz")
