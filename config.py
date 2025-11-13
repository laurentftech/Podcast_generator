import os

SERVICE_CONFIG = {
    "elevenlabs": {
        "title": "ElevenLabs API Key",
        "account": "elevenlabs_api_key",
        "url": "https://try.elevenlabs.io/zobct2wsp98z"
    },
    "gemini": {
        "title": "Gemini API Key",
        "account": "gemini_api_key",
        "url": "https://aistudio.google.com/app/apikey"
    }
}

# Gemini available voices
AVAILABLE_VOICES = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm"
}

# Default application settings
DEFAULT_APP_SETTINGS = {
    "tts_provider": "elevenlabs",
    "speaker_voices": {"John": "Schedar - Even", "Samantha": "Zephyr - Bright"},
    "speaker_voices_elevenlabs": {
        "John": {"id": "TX3LPaxmHKxFdv7VOQHJ", "display_name": "Liam - Male, Young, american"},
        "Samantha": {"id": "cgSgspJ2msm6clMCkdW9", "display_name": "Jessica - Female, Young, american"}
    },
    "elevenlabs_quota_cache": None
}

# Environment variable to control the demo button visibility
DEMO_AVAILABLE = os.getenv("DEMO_AVAILABLE") == "1"
