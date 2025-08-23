#!/bin/bash
#
# ==============================================================================
# Script to generate voice samples for all available Gemini voices.
# ==============================================================================
#
# This script uses the `generate_podcast.py` CLI to create a short
# audio file for each voice, using a standard sample sentence. The generated
# files are placed in `samples/gemini_voices/`.
#
# Requirements:
# - A working Python environment with all project dependencies installed.
# - A configured Gemini API key (set via the GUI or `keyring`).
# - The script must be run from the project's root directory.
#
# Usage:
# 1. Make the script executable:
#    chmod +x generate_gemini_samples.sh
#
# 2. Run the script:
#    ./generate_gemini_samples.sh
#
# ==============================================================================

# --- Configuration ---
OUTPUT_DIR="samples/gemini_voices"
SAMPLE_TEXT_TEMPLATE="Hello, my name is %s. You can use my voice for your podcast."
VOICES=(
    "Zephyr" "Puck" "Charon" "Kore" "Fenrir" "Leda" "Orus" "Aoede"
    "Callirrhoe" "Autonoe" "Enceladus" "Iapetus" "Umbriel" "Algieba"
    "Despina" "Erinome" "Algenib" "Rasalgethi" "Laomedeia" "Achernar"
    "Alnilam" "Schedar" "Gacrux" "Pulcherrima" "Achird" "Zubenelgenubi"
    "Vindemiatrix" "Sadachbia" "Sadaltager" "Sulafat"
)

# --- Script Logic ---

mkdir -p "$OUTPUT_DIR"
echo "Starting Gemini voice sample generation into '$OUTPUT_DIR'..."
echo "---"

for voice in "${VOICES[@]}"; do
    output_file="$OUTPUT_DIR/${voice}.mp3"
    echo "-> Generating sample for '$voice'..."

    # Crée un texte d'échantillon personnalisé pour chaque voix
    current_sample_text=$(printf "$SAMPLE_TEXT_TEMPLATE" "$voice")

    # Le locuteur dans le script est "Sample", la voix est le nom de la voix actuelle.
    python generate_podcast.py --script-text "Sample: $current_sample_text" --output "$output_file" --speaker "Sample:$voice" --provider "gemini"
    echo "---"
done

echo "✅ Generation complete. All samples are in '$OUTPUT_DIR'."