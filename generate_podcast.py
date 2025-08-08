# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv

import base64
import mimetypes
import os
import re
import struct
from dotenv import load_dotenv
#from google.api_core import exceptions
from google import genai
from google.genai import types


def save_binary_file(file_name, data):
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    print(f"File saved to to: {file_name}")


def generate():
    load_dotenv()

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    # List of models to try, from most to least preferred.
    models_to_try = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""Read aloud in a warm, welcoming tone
John: Who am I? I am a little old lady. My hair is white. I have got a small crown and a black handbag. My dress is blue. My country's flag is red, white and blue. I am on many coins and stamps. I love dogs – my dogs' names are corgis! Who am I?
Samantha: [amused] Queen Elizabeth II!

John: Who am I? I am very big and strong. I have got a red beard and a large stomach. My clothes are rich and heavy. I have got a gold ring and a big sword. The king's throne is mine! I have got six wives! Who am I?
Samantha: [amused] King Henry VIII!

John: Who am I? I am tall and thin. I have got pale skin and red hair. My father's name is Henry. I have got a big white collar and a golden dress. In my hand, there is a scepter. My crown's jewels shine! Who am I?
Samantha: [amused] Queen Elizabeth I!

John: Who am I? I am short and serious. I have got black hair in a bun and a sad face. I wear black clothes – my husband's death made me very sad. I have got a small crown and an orb in my hands. My empire's size is very big. Who am I?
Samantha: [amused] Queen Victoria!

John: Who am I? I am a man with a short beard and brown hair. I have got a dark blue uniform. I am the new king – my mother's name was Elizabeth. I have got a golden scepter and a crown. My throne's color is red and gold. Who am I?
Samantha: [amused] King Charles III!"""),
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
        print(f"\nAttempting to generate audio with model: {model_name}...")
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
                    file_name = f"ENTER_FILE_NAME_{file_index}"
                    file_index += 1
                    inline_data = chunk.candidates[0].content.parts[0].inline_data
                    data_buffer = inline_data.data
                    file_extension = mimetypes.guess_extension(inline_data.mime_type)
                    if file_extension is None:
                        file_extension = ".wav"
                        data_buffer = convert_to_wav(
                            inline_data.data, inline_data.mime_type
                        )
                    save_binary_file(f"{file_name}{file_extension}", data_buffer)
                else:
                    print(chunk.text)

            print(f"Successfully generated audio with {model_name}.")
            generated_successfully = True
            break  # Exit the model-selection loop on success
        except:
            print("Attempting fallback to the next model...")

    if not generated_successfully:
        print("\nFailed to generate audio with all available models. Please check your API key and permissions.")

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
    bits_per_sample = 16
    rate = 24000

    # Extract rate from parameters
    parts = mime_type.split(";")
    for param in parts: # Skip the main type part
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                # Handle cases like "rate=" with no value or non-integer value
                pass # Keep rate as default
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass # Keep bits_per_sample as default if conversion fails

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    generate()
