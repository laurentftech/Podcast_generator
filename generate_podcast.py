# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import mimetypes
import os
import struct
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


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

def generate(script_text: str, output_basename: str = "podcast_segment", status_callback=print, output_dir: str = ".") -> str | None:
    """Génère l'audio à partir d'un script en utilisant Gemini, avec un fallback de modèle."""
    status_callback("Démarrage de la génération du podcast...")
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        status_callback("Erreur : Clé API 'GEMINI_API_KEY' non trouvée. Veuillez créer un fichier .env.")
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
                        speaker="John",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Schedar"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Samantha",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
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
        except Exception as e:
            # Erreur inattendue et potentiellement critique (réseau, logique, etc.).
            # On doit arrêter le processus et afficher un maximum d'informations.
            status_callback(f"Une erreur critique inattendue est survenue : {e}")
            status_callback(traceback.format_exc())
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
    generate(PODCAST_SCRIPT, "royal_family_quiz")
