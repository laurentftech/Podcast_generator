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

# --- Overwrite Handling ---
OVERWRITE_MODE="ask" # Default behavior

# Check if any files already exist to decide if we need to prompt the user.
needs_prompt=false
for voice in "${VOICES[@]}"; do
    if [ -f "$OUTPUT_DIR/${voice}.mp3" ]; then
        needs_prompt=true
        break
    fi
done

if [ "$needs_prompt" = true ]; then
    read -p "Some sample files already exist. What should I do? ([O]verwrite all / [S]kip existing / [A]sk for each) [S]: " -n 1 -r
    echo # Move to a new line
    case $REPLY in
        [Oo]) OVERWRITE_MODE="all" ;;
        [Ss]|"") OVERWRITE_MODE="none" ;; # Default to 'skip' on Enter
        [Aa]) OVERWRITE_MODE="ask" ;;
        *)
            echo "Invalid choice. Skipping already existing files."
            OVERWRITE_MODE="none"
            ;;
    esac
fi

echo "---"

for voice in "${VOICES[@]}"; do
    output_file="$OUTPUT_DIR/${voice}.mp3"

    # Determine if we need to generate this file based on user's choice
    if [ -f "$output_file" ]; then
        case $OVERWRITE_MODE in
            "all")
                echo "-> Overwriting sample for '$voice'..."
                ;;
            "none")
                echo "-> Skipping existing sample for '$voice'."
                echo "---"
                continue # Skip to next voice
                ;;
            "ask")
                read -p "-> Sample for '$voice' already exists. Overwrite? [y/N] " -n 1 -r
                echo # Move to a new line
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo "   Skipping '$voice'."
                    echo "---"
                    continue # Skip to next voice
                fi
                echo "-> Overwriting sample for '$voice'..."
                ;;
        esac
    else
        echo "-> Generating new sample for '$voice'..."
    fi

    # Crée un texte d'échantillon personnalisé pour chaque voix
    current_sample_text=$(printf "$SAMPLE_TEXT_TEMPLATE" "$voice")

    # Le locuteur dans le script est "Sample", la voix est le nom de la voix actuelle.
    python generate_podcast.py --script-text "Sample: $current_sample_text" --output "$output_file" --speaker "Sample:$voice" --provider "gemini"

    # Vérifie si la commande a réussi. Si non, arrête le script.
    if [ $? -ne 0 ]; then
        echo
        echo "❌ ERROR: Generation failed for '$voice'."
        echo "   This might be due to a quota limit or a network issue."
        echo "   Aborting script to prevent further errors."
        exit 1
    fi

    echo "---"
done

echo "✅ Generation complete. All samples are in '$OUTPUT_DIR'."