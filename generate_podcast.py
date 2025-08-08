# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import mimetypes
import os
import struct
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


# Le script du podcast est maintenant une constante pour être utilisé par le mode console.
PODCAST_SCRIPT = """Read aloud in a warm, welcoming tone
John: Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs – my dogs' names are corgis! Who am I?
Samantha: [amused] Queen Elizabeth II!

John: Who am I? I am very big and strong. I have got a red beard and a large stomach. My clothes are rich and heavy. I have got a gold ring and a big sword. The king's throne is mine! I have got six wives! Who am I?
Samantha: [amused] King Henry VIII!

John: Who am I? I am tall and thin. I have got pale skin and red hair. My father's name is Henry. I have got a big white collar and a golden dress. In my hand, there is a scepter. My crown's jewels shine! Who am I?
Samantha: [amused] Queen Elizabeth I!

John: Who am I? I am short and serious. I have got black hair in a bun and a sad face. I wear black clothes – my husband's death made me very sad. I have got a small crown and an orb in my hands. My empire's size is very big. Who am I?
Samantha: [amused] Queen Victoria!

John: Who am I? I am a man with a short beard and brown hair. I have got a dark blue uniform. I am the new king – my mother's name was Elizabeth. I have got a golden scepter and a crown. My throne's color is red and gold. Who am I?
Samantha: [amused] King Charles III!"""

def save_binary_file(file_name: str, data: bytes, status_callback=print):
    """Sauvegarde les données binaires dans un fichier de manière sécurisée."""
    try:
        with open(file_name, "wb") as f:
            f.write(data)
        status_callback(f"Fichier sauvegardé : {file_name}")
    except IOError as e:
        status_callback(f"Erreur lors de la sauvegarde du fichier {file_name}: {e}")

def generate(script_text: str, output_basename: str = "podcast_segment", status_callback=print, output_dir: str = "."):
    """Génère l'audio à partir d'un script en utilisant Gemini, avec un fallback de modèle."""
    status_callback("DEBUG: Début de generate()")
    status_callback("Démarrage de la génération du podcast...")
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        status_callback("Erreur : Clé API 'GEMINI_API_KEY' non trouvée. Veuillez créer un fichier .env.")
        return False

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
    for model_name in models_to_try:
        status_callback(f"\nTentative de génération avec le modèle : {model_name}...")
        try:
            file_index = 0
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
                if (
                    chunk.candidates[0].content.parts[0].inline_data
                    and chunk.candidates[0].content.parts[0].inline_data.data
                ):
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    data_buffer = inline_data.data
                    file_extension = mimetypes.guess_extension(inline_data.mime_type)
                    if file_extension is None:
                        file_extension = ".wav"
                        data_buffer = convert_to_wav(
                            inline_data.data, inline_data.mime_type
                        )
                    
                    output_path = os.path.join(output_dir, f"{output_basename}_{file_index}{file_extension}")
                    save_binary_file(output_path, data_buffer, status_callback)
                    file_index += 1
                else:
                    status_callback(chunk.text)

            status_callback(f"Audio généré avec succès via {model_name}.")
            generated_successfully = True
            break  # Exit the model-selection loop on success
        except Exception:
            status_callback(f"Erreur avec le modèle '{model_name}'")
            status_callback("Tentative avec le modèle suivant...")

    if not generated_successfully:
        status_callback("\nÉchec de la génération audio avec tous les modèles disponibles.")
        return False
    status_callback("DEBUG: Fin de generate()")
    return True

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
