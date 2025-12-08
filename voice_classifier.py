#!/usr/bin/env python3
"""
Voice Classification using Google Gemini API
Classifies audio files (Gemini voices) and ElevenLabs voices by age, accent, etc.
"""

from google import genai
from google.genai import types
import os
import json
import sys
import argparse
from pathlib import Path
import requests
import keyring

# Configure API key (for Gemini classification)
# Try environment variable first, then keyring (same as generate_podcast.py)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = keyring.get_password("PodcastGenerator", "gemini_api_key")

if not GEMINI_API_KEY:
    print("ERROR: Gemini API key not found")
    print("Please set it via:")
    print("  1. Environment variable: export GEMINI_API_KEY='your-api-key'")
    print("  2. Or configure it in the Podcast Generator app (stored in keyring)")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT = """Analyze this voice recording and classify it based on the speaker's voice characteristics."""

# JSON schema for Gemini voice classification (includes gender)
GEMINI_CLASSIFICATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "gender": types.Schema(
            type=types.Type.STRING,
            enum=["male", "female", "ambiguous"],
            description="Perceived gender of the speaker"
        ),
        "age_group": types.Schema(
            type=types.Type.STRING,
            enum=["child", "teen", "young adult", "middle aged", "senior"],
            description="Age group: child (0-12), teen (13-19), young adult (20-35), middle aged (36-55), senior (56+)"
        ),
        "accent": types.Schema(
            type=types.Type.STRING,
            description="English accent/dialect (e.g., American, British RP, British Regional, Australian, Irish, Scottish)"
        ),
        "voice_quality": types.Schema(
            type=types.Type.STRING,
            enum=["deep", "medium", "high-pitched"],
            description="Voice pitch quality"
        ),
        "speaking_style": types.Schema(
            type=types.Type.STRING,
            enum=["formal", "casual", "narrative", "conversational"],
            description="Speaking style"
        ),
        "confidence": types.Schema(
            type=types.Type.INTEGER,
            description="Confidence score 1-10"
        ),
        "notes": types.Schema(
            type=types.Type.STRING,
            description="Additional observations about the voice"
        ),
    },
    required=["gender", "age_group", "accent", "voice_quality", "speaking_style", "confidence"],
)

# JSON schema for ElevenLabs voice classification (excludes gender - already provided by API)
ELEVENLABS_CLASSIFICATION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "age_group": types.Schema(
            type=types.Type.STRING,
            enum=["child", "teen", "young adult", "middle aged", "senior"],
            description="Age group: child (0-12), teen (13-19), young adult (20-35), middle aged (36-55), senior (56+)"
        ),
        "accent": types.Schema(
            type=types.Type.STRING,
            description="English accent/dialect (e.g., American, British RP, British Regional, Australian, Irish, Scottish)"
        ),
        "voice_quality": types.Schema(
            type=types.Type.STRING,
            enum=["deep", "medium", "high-pitched"],
            description="Voice pitch quality"
        ),
        "speaking_style": types.Schema(
            type=types.Type.STRING,
            enum=["formal", "casual", "narrative", "conversational"],
            description="Speaking style"
        ),
        "confidence": types.Schema(
            type=types.Type.INTEGER,
            description="Confidence score 1-10"
        ),
        "notes": types.Schema(
            type=types.Type.STRING,
            description="Additional observations about the voice"
        ),
    },
    required=["age_group", "accent", "voice_quality", "speaking_style", "confidence"],
)


def classify_voice_from_file(audio_path: str, use_elevenlabs_schema: bool = False) -> dict:
    """Classify a single voice recording from a local file using Gemini."""
    try:
        # Read audio file
        audio_bytes = Path(audio_path).read_bytes()

        schema = ELEVENLABS_CLASSIFICATION_SCHEMA if use_elevenlabs_schema else GEMINI_CLASSIFICATION_SCHEMA

        # Generate classification with structured output
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="audio/mpeg",
                                data=audio_bytes
                            )
                        ),
                        types.Part(text=PROMPT)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        result = json.loads(response.text)
        result["filename"] = Path(audio_path).stem
        return result

    except json.JSONDecodeError as e:
        return {
            "filename": Path(audio_path).stem,
            "error": f"JSON parse error: {e}",
            "raw_response": response.text if 'response' in dir() else "No response"
        }
    except Exception as e:
        return {
            "filename": Path(audio_path).stem,
            "error": str(e)
        }


def classify_voice_from_url(preview_url: str, voice_name: str, existing_gender: str = None) -> dict:
    """Classify a voice from a URL (for ElevenLabs preview URLs) using Gemini."""
    try:
        # Download audio from URL
        response = requests.get(preview_url, timeout=30)
        response.raise_for_status()
        audio_bytes = response.content

        # Use ElevenLabs schema (no gender field)
        schema = ELEVENLABS_CLASSIFICATION_SCHEMA

        # Generate classification with structured output
        gemini_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="audio/mpeg",
                                data=audio_bytes
                            )
                        ),
                        types.Part(text=PROMPT)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        result = json.loads(gemini_response.text)
        result["voice_name"] = voice_name

        # Add the existing gender from ElevenLabs API if provided
        if existing_gender:
            result["gender"] = existing_gender.lower()

        return result

    except requests.RequestException as e:
        return {
            "voice_name": voice_name,
            "error": f"Download error: {e}"
        }
    except json.JSONDecodeError as e:
        return {
            "voice_name": voice_name,
            "error": f"JSON parse error: {e}",
            "raw_response": gemini_response.text if 'gemini_response' in dir() else "No response"
        }
    except Exception as e:
        return {
            "voice_name": voice_name,
            "error": str(e)
        }


def fetch_elevenlabs_voices():
    """Fetch all ElevenLabs voices using the API (similar to settings_window.py)."""
    api_key = os.getenv("ELEVENLABS_API_KEY") or keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
    if not api_key:
        print("ERROR: ElevenLabs API key not found")
        print("Set it with: export ELEVENLABS_API_KEY='your-api-key'")
        return []

    try:
        headers = {"xi-api-key": api_key}
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=15)
        response.raise_for_status()

        voices_data = response.json().get('voices', [])
        voices = []

        for voice in voices_data:
            labels = voice.get('labels', {}) or {}
            voices.append({
                'id': voice.get('voice_id', ''),
                'name': voice.get('name', 'Unknown'),
                'gender': labels.get('gender', 'unknown'),
                'preview_url': voice.get('preview_url', ''),
                'category': voice.get('category', ''),
                'labels': labels
            })

        return voices

    except Exception as e:
        print(f"Error fetching ElevenLabs voices: {e}")
        return []


def classify_gemini_voices():
    """Classify Gemini voices from local audio files."""
    audio_dir = "./samples/gemini_voices"
    audio_files = sorted(Path(audio_dir).glob("*.mp3"))
    output_path = Path("./samples/gemini_voices/voice_classifications.json")

    # Load existing results (cache)
    existing_results = {}
    if output_path.exists():
        try:
            with open(output_path) as f:
                cached = json.load(f)
                # Index by filename for quick lookup
                existing_results = {r["filename"]: r for r in cached if "error" not in r}
            print(f"📁 Loaded {len(existing_results)} cached classifications\n")
        except (json.JSONDecodeError, KeyError):
            print("⚠️  Could not load cache, starting fresh\n")

    print(f"Found {len(audio_files)} audio files total\n")

    results = []
    skipped = 0
    processed = 0

    for i, audio_path in enumerate(audio_files, 1):
        filename = audio_path.stem

        # Check if already classified (and no error)
        if filename in existing_results:
            print(f"[{i}/{len(audio_files)}] {audio_path.name} → ⏭️  SKIPPED (cached)")
            results.append(existing_results[filename])
            skipped += 1
            continue

        print(f"[{i}/{len(audio_files)}] Classifying {audio_path.name}...", end=" ", flush=True)
        result = classify_voice_from_file(str(audio_path), use_elevenlabs_schema=False)
        results.append(result)
        processed += 1

        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
        else:
            print(f"✅ {result['gender']}, {result['age_group']}, {result['accent']}")

        # Save after each successful classification (incremental save)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"\n✅ Done! Processed: {processed}, Skipped: {skipped}, Total: {len(results)}")
    print(f"📁 Results saved to {output_path}")

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'Voice':<15} {'Gender':<10} {'Age Group':<15} {'Accent':<20} {'Quality':<12} {'Conf':<5}")
    print("=" * 100)

    for r in results:
        if "error" not in r:
            print(
                f"{r['filename']:<15} {r['gender']:<10} {r['age_group']:<15} {r['accent']:<20} {r['voice_quality']:<12} {r['confidence']:<5}")
        else:
            print(f"{r['filename']:<15} ERROR: {r['error'][:60]}")

    print("=" * 100)


def classify_elevenlabs_voices():
    """Classify ElevenLabs voices from API preview URLs."""
    output_path = Path("./samples/elevenlabs_voices/voice_classifications.json")
    output_path.parent.mkdir(exist_ok=True)

    # Load existing results (cache)
    existing_results = {}
    if output_path.exists():
        try:
            with open(output_path) as f:
                cached = json.load(f)
                # Index by voice_name for quick lookup
                existing_results = {r["voice_name"]: r for r in cached if "error" not in r}
            print(f"📁 Loaded {len(existing_results)} cached classifications\n")
        except (json.JSONDecodeError, KeyError):
            print("⚠️  Could not load cache, starting fresh\n")

    # Fetch voices from ElevenLabs API
    print("🔍 Fetching ElevenLabs voices from API...")
    voices = fetch_elevenlabs_voices()

    if not voices:
        print("❌ No voices found. Exiting.")
        return

    print(f"Found {len(voices)} voices total\n")

    results = []
    skipped = 0
    processed = 0

    for i, voice in enumerate(voices, 1):
        voice_name = voice['name']

        # Check if already classified (and no error)
        if voice_name in existing_results:
            print(f"[{i}/{len(voices)}] {voice_name} → ⏭️  SKIPPED (cached)")
            results.append(existing_results[voice_name])
            skipped += 1
            continue

        if not voice['preview_url']:
            print(f"[{i}/{len(voices)}] {voice_name} → ⚠️  No preview URL")
            results.append({"voice_name": voice_name, "error": "No preview URL available"})
            continue

        print(f"[{i}/{len(voices)}] Classifying {voice_name}...", end=" ", flush=True)
        result = classify_voice_from_url(voice['preview_url'], voice_name, voice['gender'])
        results.append(result)
        processed += 1

        if "error" in result:
            print(f"❌ ERROR: {result['error']}")
        else:
            print(f"✅ {result.get('gender', 'N/A')}, {result['age_group']}, {result['accent']}")

        # Save after each successful classification (incremental save)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"\n✅ Done! Processed: {processed}, Skipped: {skipped}, Total: {len(results)}")
    print(f"📁 Results saved to {output_path}")

    # Print summary table
    print("\n" + "=" * 120)
    print(f"{'Voice':<25} {'Gender':<10} {'Age Group':<15} {'Accent':<20} {'Quality':<12} {'Style':<15} {'Conf':<5}")
    print("=" * 120)

    for r in results:
        if "error" not in r:
            print(
                f"{r['voice_name']:<25} {r.get('gender', 'N/A'):<10} {r['age_group']:<15} {r['accent']:<20} {r['voice_quality']:<12} {r['speaking_style']:<15} {r['confidence']:<5}")
        else:
            print(f"{r['voice_name']:<25} ERROR: {r['error'][:80]}")

    print("=" * 120)


def main():
    parser = argparse.ArgumentParser(
        description="Classify voices using Gemini AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Classify Gemini voices from local audio files
  python voice_classifier.py --provider gemini

  # Classify ElevenLabs voices from API
  python voice_classifier.py --provider elevenlabs
        """
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "elevenlabs"],
        default="gemini",
        help="Voice provider to classify (default: gemini)"
    )

    args = parser.parse_args()

    if args.provider == "gemini":
        print("🎙️  Classifying Gemini voices...\n")
        classify_gemini_voices()
    elif args.provider == "elevenlabs":
        print("🎙️  Classifying ElevenLabs voices...\n")
        classify_elevenlabs_voices()


if __name__ == "__main__":
    main()