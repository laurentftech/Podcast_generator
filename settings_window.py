import tkinter as tk
from tkinter import ttk
import threading
import json

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


class SettingsWindow(tk.Toplevel):
    VOICE_DISPLAY_LIST = [f"{name} - {desc}" for name, desc in AVAILABLE_VOICES.items()]

    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings, preloaded_elevenlabs_voices=None):
        super().__init__(parent)
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

        import keyring
        self.gemini_api_configured = bool(keyring.get_password("PodcastGenerator", "gemini_api_key"))
        self.elevenlabs_api_configured = bool(keyring.get_password("PodcastGenerator", "elevenlabs_api_key"))

        print(f"=== DEBUG __init__ SettingsWindow ===")
        print(f"current_settings reçu: {current_settings}")

        self.default_settings = default_settings
        self.current_settings = dict(current_settings)  # Crée une copie
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.cancel_and_close)
        self.entries = []

        # Cache pour les voix ElevenLabs - initialisation simple
        self.elevenlabs_voices = []
        self.elevenlabs_voices_loaded = False
        self._loading_voices = False
        self._voices_need_update = False  # NOUVEAU FLAG

        # Si un cache est fourni par le parent, l'utiliser immédiatement
        if isinstance(preloaded_elevenlabs_voices, list) and preloaded_elevenlabs_voices:
            print(f"Préchargement de {len(preloaded_elevenlabs_voices)} voix ElevenLabs depuis le cache")
            self.elevenlabs_voices = list(preloaded_elevenlabs_voices)
            self.elevenlabs_voices_loaded = True
            self._voices_need_update = True

        # Créer l'interface d'abord
        self.create_interface()

        # FORCER le chargement immédiat des paramètres existants
        print("Chargement immédiat des paramètres existants...")
        self.populate_fields()

        # Puis charger les voix ElevenLabs en arrière-plan après un délai
        # Ne lancer le chargement que si aucune voix préchargée n'a été fournie
        if not self.elevenlabs_voices_loaded:
            self.after(500, self.load_elevenlabs_voices)

        # Démarrer la vérification périodique
        self.check_voices_update()

    def check_voices_update(self):
        """Vérifie périodiquement si les voix ont besoin d'être mises à jour."""
        if self._voices_need_update and self.elevenlabs_voices_loaded:
            print("=== Détection que les voix ont besoin d'être mises à jour ===")
            self._voices_need_update = False
            self.update_elevenlabs_comboboxes()

        # Reprogram la vérification dans 200ms
        self.after(200, self.check_voices_update)

    def create_interface(self):
        """Crée l'interface utilisateur de base."""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Provider selection (supprimé car doublon avec le menu principal)
        # provider_frame = tk.Frame(main_frame)
        # provider_frame.pack(fill=tk.X, pady=(0, 10))
        # tk.Label(provider_frame, text="TTS Provider:", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        # self.provider_var = tk.StringVar(value=self.current_settings.get("tts_provider", "gemini"))
        # provider_combo = ttk.Combobox(provider_frame, textvariable=self.provider_var,
        #                               values=["gemini", "elevenlabs"], width=15, state="readonly")
        # provider_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Headers
        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(header_frame, text="Speaker name (in the script)",
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w")

        next_column = 1

        # Conditionally create Gemini header
        if self.gemini_api_configured:
            tk.Label(header_frame, text="Voice (Gemini)",
                     font=('Helvetica', 10, 'bold')).grid(row=0, column=next_column, sticky="w", padx=(10, 0))
            header_frame.columnconfigure(next_column, weight=1)
            next_column += 1

        # Conditionally create ElevenLabs header
        if self.elevenlabs_api_configured:
            el_header_frame = tk.Frame(header_frame)
            el_header_frame.grid(row=0, column=next_column, sticky="w", padx=(10, 0))
            tk.Label(el_header_frame, text="Voice (ElevenLabs)",
                     font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
            # (Bouton de rafraîchissement supprimé)
            header_frame.columnconfigure(next_column, weight=1)

        # Configure grid weights for headers
        header_frame.columnconfigure(0, weight=1)

        self.speaker_frame = tk.Frame(main_frame)
        self.speaker_frame.pack(fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(button_frame, text="+", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Save", command=self.save_and_close).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Cancel", command=self.cancel_and_close).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Restore Defaults", command=self.restore_defaults).pack(side=tk.LEFT, padx=(10, 0))

    def safe_update_button(self, state, text):
        """Met à jour le bouton de manière sécurisée."""
        try:
            if (hasattr(self, 'refresh_voices_btn') and
                    self.refresh_voices_btn is not None):
                try:
                    self.refresh_voices_btn.winfo_class()
                    self.refresh_voices_btn.config(state=state, text=text)
                except tk.TclError:
                    pass
        except (tk.TclError, AttributeError, TypeError) as e:
            print(f"Erreur lors de la mise à jour du bouton (ignorée): {e}")
            pass

    def load_elevenlabs_voices(self):
        """Charge la liste des voix ElevenLabs depuis l'API."""
        print("=== DEBUG load_elevenlabs_voices appelé ===")

        if self._loading_voices:
            print("Déjà en cours de chargement, abandon")
            return

        self._loading_voices = True

        import keyring
        import requests

        def fetch_voices():
            try:
                try:
                    self.winfo_class()
                except tk.TclError:
                    print("Fenêtre détruite, abandon")
                    return

                self.after(0, lambda: self.safe_update_button('disabled', '⏳'))

                api_key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
                if not api_key:
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    print("Aucune clé API ElevenLabs configurée")
                    print("Programmation de populate_fields_delayed sans clé API...")
                    self.after(100, self.populate_fields_delayed)
                    return

                print("Tentative de chargement des voix ElevenLabs...")
                headers = {"xi-api-key": api_key}
                response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=15)

                if response.status_code == 200:
                    voices_data = response.json()
                    voices = []

                    for voice in voices_data.get('voices', []):
                        voice_id = voice.get('voice_id', '')
                        name = voice.get('name', 'Unknown')
                        category = voice.get('category', '')
                        labels = voice.get('labels', {}) if voice.get('labels') else {}

                        accent = labels.get('accent', '') if isinstance(labels, dict) else ''
                        age = labels.get('age', '') if isinstance(labels, dict) else ''
                        gender = labels.get('gender', '') if isinstance(labels, dict) else ''

                        description_parts = []
                        if gender:
                            description_parts.append(str(gender).title())
                        if age:
                            description_parts.append(str(age).title())
                        if accent:
                            description_parts.append(str(accent))

                        description = ', '.join(description_parts) if description_parts else str(category).title()
                        display_name = f"{name} - {description}" if description else name

                        voices.append({
                            'id': voice_id,
                            'name': name,
                            'display_name': display_name,
                            'category': category,
                            'labels': labels
                        })

                    voices.sort(key=lambda x: x.get('name', ''))
                    self.elevenlabs_voices = voices
                    self.elevenlabs_voices_loaded = True

                    print(f"Chargé {len(voices)} voix ElevenLabs avec succès")
                    print("Activation du flag de mise à jour des voix...")
                    self._voices_need_update = True

                else:
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    print(f"Erreur API ElevenLabs: {response.status_code} - {response.text[:200]}")

            except requests.exceptions.Timeout:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                print("Timeout lors du chargement des voix ElevenLabs")
                print("Programmation de populate_fields_delayed après timeout...")
                self.after(100, self.populate_fields_delayed)
            except requests.exceptions.RequestException as e:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                print(f"Erreur réseau lors du chargement des voix ElevenLabs: {e}")
                print("Programmation de populate_fields_delayed après erreur réseau...")
                self.after(100, self.populate_fields_delayed)
            except Exception as e:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                print(f"Erreur lors du chargement des voix ElevenLabs: {e}")
                print("Programmation de populate_fields_delayed après exception...")
                self.after(100, self.populate_fields_delayed)

        print("Lancement du thread de chargement...")
        thread = threading.Thread(target=fetch_voices, daemon=True)
        thread.start()

    def populate_fields_delayed(self):
        """Populate les champs après que les voix ElevenLabs aient été chargées (ou échoué)."""
        print(f"=== DEBUG populate_fields_delayed ===")
        print(f"self.entries avant: {len(self.entries)} entrées")
        print(f"Contenu de self.entries: {[row.get('speaker', 'NO_SPEAKER') for row in self.entries]}")
        self.populate_fields()

    def update_elevenlabs_comboboxes(self):
        """Met à jour toutes les comboboxes ElevenLabs avec les nouvelles voix chargées."""
        try:
            if not self.elevenlabs_voices_loaded or not self.elevenlabs_voices:
                return
            self.winfo_class()
            print(f"Mise à jour des comboboxes avec {len(self.elevenlabs_voices)} voix")
            elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]
            for row in self.entries:
                if 'elevenlabs_voice' in row and row['elevenlabs_voice']:
                    try:
                        current_value = row['elevenlabs_voice'].get()
                        row['elevenlabs_voice']['values'] = elevenlabs_values
                        if current_value in elevenlabs_values:
                            row['elevenlabs_voice'].set(current_value)
                    except tk.TclError:
                        continue
            print("Mise à jour des comboboxes terminée avec succès")
        except (tk.TclError, AttributeError):
            pass
        except Exception as e:
            print(f"Erreur lors de la mise à jour des comboboxes: {e}")

    def cancel_and_close(self):
        """Ferme la fenêtre sans sauvegarder les modifications."""
        if self.close_callback:
            self.close_callback()
        self.destroy()

    def save_and_close(self):
        """Sauvegarde les paramètres et ferme la fenêtre."""
        print("=== DEBUG save_and_close ===")

        new_settings = json.loads(json.dumps(self.current_settings))

        ui_speakers = {row['speaker'].get().strip() for row in self.entries if row['speaker'].get().strip()}

        for voice_dict_key in ['speaker_voices', 'speaker_voices_elevenlabs']:
            if voice_dict_key in new_settings:
                for speaker in list(new_settings[voice_dict_key]):
                    if speaker not in ui_speakers:
                        del new_settings[voice_dict_key][speaker]

        for row in self.entries:
            speaker_name = row['speaker'].get().strip()
            if not speaker_name:
                continue

            if row.get('gemini_voice'):
                gemini_voice = row['gemini_voice'].get()
                new_settings.setdefault('speaker_voices', {})[speaker_name] = gemini_voice

            if row.get('elevenlabs_voice'):
                elevenlabs_voice_display = row['elevenlabs_voice'].get()
                elevenlabs_voice_id = ""
                if elevenlabs_voice_display and self.elevenlabs_voices:
                    for voice in self.elevenlabs_voices:
                        if voice['display_name'] == elevenlabs_voice_display:
                            elevenlabs_voice_id = voice['id']
                            break
                new_settings.setdefault('speaker_voices_elevenlabs', {})[speaker_name] = {
                    'id': elevenlabs_voice_id,
                    'display_name': elevenlabs_voice_display
                }

        # Ne plus enregistrer tts_provider ici (géré par le menu principal)

        print(f"new_settings à sauvegarder: {new_settings}")

        if self.save_callback:
            self.save_callback(new_settings)

        if self.close_callback:
            self.close_callback()
        self.destroy()

    def populate_fields(self):
        """Remplit les champs avec les paramètres actuels."""
        print("=== DEBUG populate_fields ===")
        print(f"current_settings reçu: {self.current_settings}")

        speaker_voices = self.current_settings.get('speaker_voices', {})
        speaker_voices_elevenlabs = self.current_settings.get('speaker_voices_elevenlabs', {})

        print(f"speaker_voices: {speaker_voices}")
        print(f"speaker_voices_elevenlabs: {speaker_voices_elevenlabs}")

        voice_settings = self.current_settings.get('voice_settings', {})
        print(f"voice_settings: {voice_settings}")

        if voice_settings:
            print("Utilisation du nouveau format voice_settings")
            for speaker_name, voices in voice_settings.items():
                print(f"Ajout ligne: {speaker_name} -> {voices}")
                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=voices.get('gemini_voice', ''),
                    elevenlabs_voice=voices.get('elevenlabs_voice', '')
                )
        elif speaker_voices:
            print("Utilisation de l'ancien format speaker_voices")
            all_speakers = set(speaker_voices.keys()) | set(speaker_voices_elevenlabs.keys())
            print(f"All speakers: {all_speakers}")

            for speaker_name in all_speakers:
                gemini_voice = speaker_voices.get(speaker_name, '')
                elevenlabs_data = speaker_voices_elevenlabs.get(speaker_name, '')

                elevenlabs_voice_display = ""

                if isinstance(elevenlabs_data, dict):
                    elevenlabs_voice_display = elevenlabs_data.get('display_name', '')
                elif isinstance(elevenlabs_data, str):
                    if ' - ' in elevenlabs_data:
                        elevenlabs_voice_display = elevenlabs_data
                    else:
                        if self.elevenlabs_voices:
                            for voice in self.elevenlabs_voices:
                                if voice['id'] == elevenlabs_data:
                                    elevenlabs_voice_display = voice['display_name']
                                    break

                print(
                    f"Ajout ligne: {speaker_name} -> gemini='{gemini_voice}', elevenlabs_display='{elevenlabs_voice_display}'")
                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=gemini_voice,
                    elevenlabs_voice=elevenlabs_voice_display
                )
        else:
            print("Aucun paramètre trouvé, ajout d'une ligne vide")
            self.add_row()

    def add_row(self, speaker_name='', gemini_voice='', elevenlabs_voice=''):
        """Ajoute une nouvelle ligne de paramètres."""
        row_frame = tk.Frame(self.speaker_frame)
        row_frame.pack(fill=tk.X, pady=2)

        speaker_entry = tk.Entry(row_frame, width=25)
        speaker_entry.pack(side=tk.LEFT, padx=(0, 10))
        speaker_entry.insert(0, speaker_name)

        row_data = {
            'frame': row_frame,
            'speaker': speaker_entry,
            'gemini_voice': None,
            'elevenlabs_voice': None
        }

        if self.gemini_api_configured:
            gemini_combo = ttk.Combobox(row_frame, values=self.VOICE_DISPLAY_LIST,
                                        width=25, state="readonly")
            gemini_combo.pack(side=tk.LEFT, padx=(0, 10))
            if gemini_voice:
                gemini_combo.set(gemini_voice)
            row_data['gemini_voice'] = gemini_combo

        if self.elevenlabs_api_configured:
            elevenlabs_values = []
            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]

            elevenlabs_combo = ttk.Combobox(row_frame, values=elevenlabs_values,
                                            width=25, state="readonly")
            elevenlabs_combo.pack(side=tk.LEFT, padx=(0, 10))
            if elevenlabs_voice:
                elevenlabs_combo.set(elevenlabs_voice)
            row_data['elevenlabs_voice'] = elevenlabs_combo

        remove_btn = tk.Button(row_frame, text="-", width=3,
                               command=lambda r=row_frame: self.remove_row(r))
        remove_btn.pack(side=tk.LEFT)

        row_data['remove_btn'] = remove_btn
        self.entries.append(row_data)

    def remove_row(self, row_frame):
        """Supprime une ligne de paramètres."""
        for i, row in enumerate(self.entries):
            if row['frame'] == row_frame:
                row_frame.destroy()
                del self.entries[i]
                break

    def restore_defaults(self):
        """Restaure les paramètres par défaut."""
        for row in self.entries:
            row['frame'].destroy()
        self.entries.clear()

        self.current_settings = dict(self.default_settings)
        # Ne plus toucher au provider ici (géré par le menu principal)
        self.populate_fields()