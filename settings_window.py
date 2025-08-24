import logging
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


class VoiceSettingsWindow(tk.Toplevel):
    VOICE_DISPLAY_LIST = [f"{name} - {desc}" for name, desc in AVAILABLE_VOICES.items()]

    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings,
                 preloaded_elevenlabs_voices=None,
                 play_gemini_sample_callback=None,
                 play_elevenlabs_sample_callback=None):
        super().__init__(parent)
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

        import keyring
        self.gemini_api_configured = bool(keyring.get_password("PodcastGenerator", "gemini_api_key"))
        self.elevenlabs_api_configured = bool(keyring.get_password("PodcastGenerator", "elevenlabs_api_key"))

        self.default_settings = default_settings
        self.current_settings = dict(current_settings)  # Crée une copie
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.cancel_and_close)
        # Callbacks for playing voice samples
        self.play_gemini_sample = play_gemini_sample_callback
        self.play_elevenlabs_sample = play_elevenlabs_sample_callback

        self.entries = []

        # Cache pour les voix ElevenLabs - initialisation simple
        self.elevenlabs_voices = []
        self.elevenlabs_voices_loaded = False
        self._loading_voices = False
        self._voices_need_update = False  # NOUVEAU FLAG

        # Si un cache est fourni par le parent, l'utiliser immédiatement
        if isinstance(preloaded_elevenlabs_voices, list) and preloaded_elevenlabs_voices:
            self.elevenlabs_voices = list(preloaded_elevenlabs_voices)
            self.elevenlabs_voices_loaded = True
            self._voices_need_update = True

        # Créer l'interface d'abord
        self.create_interface()

        # FORCER le chargement immédiat des paramètres existants
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
            self._voices_need_update = False
            self.update_elevenlabs_comboboxes()

        # Reprogram la vérification dans 200ms
        self.after(200, self.check_voices_update)

    def create_interface(self):
        """Crée l'interface utilisateur de base."""
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: Speaker Configuration ---
        speaker_config_frame = tk.LabelFrame(main_frame, text="My Speaker Voices", padx=10, pady=10)
        speaker_config_frame.pack(fill=tk.X, pady=(0, 10))

        self._create_speaker_headers(speaker_config_frame)

        self.speaker_frame = tk.Frame(speaker_config_frame)
        self.speaker_frame.pack(fill=tk.X, expand=True)

        # --- Section 2: Voice Guides (Tabs) ---
        # N'afficher cette section que si au moins une clé API est configurée.
        if self.gemini_api_configured or self.elevenlabs_api_configured:
            guides_frame = tk.LabelFrame(main_frame, text="Voice Guides", padx=10, pady=10)
            guides_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

            notebook = ttk.Notebook(guides_frame)
            notebook.pack(fill=tk.BOTH, expand=True)

            if self.gemini_api_configured:
                gemini_tab = ttk.Frame(notebook)
                notebook.add(gemini_tab, text="Gemini Voices")
                self._populate_guide_tab(gemini_tab, "gemini")

            if self.elevenlabs_api_configured:
                elevenlabs_tab = ttk.Frame(notebook)
                notebook.add(elevenlabs_tab, text="ElevenLabs Voices")
                self._populate_guide_tab(elevenlabs_tab, "elevenlabs")

        # --- Section 3: Main Buttons ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        tk.Button(button_frame, text="+ Add Speaker", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Save", command=self.save_and_close, font=('Helvetica', 10, 'bold')).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Cancel", command=self.cancel_and_close).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Restore Defaults", command=self.restore_defaults).pack(side=tk.LEFT, padx=(10, 0))

    def _create_speaker_headers(self, parent_frame):
        """Creates the headers for the speaker configuration section."""
        header_frame = tk.Frame(parent_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        # Speaker Name header - ajuster la largeur pour correspondre aux Entry
        speaker_label = tk.Label(header_frame, text="Speaker Name (in script)",
                                 font=('Helvetica', 10, 'bold'), anchor="w", width=30)
        speaker_label.pack(side=tk.LEFT, padx=(0, 10))

        # Gemini Voice header (si API configurée)
        if self.gemini_api_configured:
            gemini_label = tk.Label(header_frame, text="Gemini Voice",
                                    font=('Helvetica', 10, 'bold'), anchor="w", width=30)
            gemini_label.pack(side=tk.LEFT, padx=(0, 10))

        # ElevenLabs Voice header (si API configurée)
        if self.elevenlabs_api_configured:
            elevenlabs_label = tk.Label(header_frame, text="ElevenLabs Voice",
                                        font=('Helvetica', 10, 'bold'), anchor="w", width=30)
            elevenlabs_label.pack(side=tk.LEFT, padx=(0, 10))

    def _populate_guide_tab(self, tab, provider):
        """Populates a tab with voice samples with improved scrolling."""
        # Frame principal pour contenir le canvas et la scrollbar
        main_frame = tk.Frame(tab)
        main_frame.pack(fill="both", expand=True)

        # Canvas avec scrollbar
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)

        # Frame scrollable
        scrollable_frame = tk.Frame(canvas)

        # Fonction pour mettre à jour la région de scroll
        def configure_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        # Fonction pour synchroniser la largeur du frame scrollable avec le canvas
        def configure_canvas_width(event=None):
            canvas_width = canvas.winfo_width()
            canvas.itemconfig(canvas_window, width=canvas_width)

        # Lier les événements
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)

        # Créer la fenêtre dans le canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configurer le scrolling avec la molette de la souris
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<MouseWheel>", on_mousewheel)  # Windows
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux

        # Configurer le canvas pour le scrolling
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack le canvas et la scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Remplir le contenu selon le provider
        if provider == "gemini":
            for name, desc in AVAILABLE_VOICES.items():
                self._create_guide_row(scrollable_frame, provider, name, f"{name} - {desc}", name)
        elif provider == "elevenlabs":
            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                for voice in self.elevenlabs_voices:
                    self._create_guide_row(scrollable_frame, provider, voice['id'],
                                           voice['display_name'], voice['preview_url'])
            else:
                # Message de chargement avec style cohérent
                loading_frame = tk.Frame(scrollable_frame, height=60)
                loading_frame.pack(fill="x", pady=20, padx=5)
                loading_frame.pack_propagate(False)

                tk.Label(loading_frame, text="Loading ElevenLabs voices...",
                         font=('Helvetica', 10), fg="grey").pack(expand=True)

        # Mettre le focus sur le canvas pour permettre le scrolling au clavier
        canvas.focus_set()

        # Lier les touches fléchées pour le scrolling
        canvas.bind("<Up>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Down>", lambda e: canvas.yview_scroll(1, "units"))
        canvas.bind("<Prior>", lambda e: canvas.yview_scroll(-10, "units"))  # Page Up
        canvas.bind("<Next>", lambda e: canvas.yview_scroll(10, "units"))

    def _create_guide_row(self, parent, provider, voice_id, display_name, play_identifier):
        """Creates a single row in the voice guide with perfect button alignment."""
        # Créer un frame principal pour la ligne avec une hauteur minimale fixe
        row_frame = tk.Frame(parent, height=60)  # Hauteur minimale fixe
        row_frame.pack(fill=tk.X, pady=4, padx=5)
        row_frame.pack_propagate(False)  # Empêche le frame de se redimensionner selon son contenu

        # Configuration du grid: colonne 0 pour le texte (expandable), colonne 1 pour les boutons (fixe)
        row_frame.columnconfigure(0, weight=1)
        row_frame.columnconfigure(1, weight=0, minsize=120)  # Largeur minimale fixe pour les boutons

        # --- Colonne 0: Contenu texte ---
        text_frame = tk.Frame(row_frame)
        text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Séparer le nom d'affichage en nom et description pour un meilleur formatage
        if " - " in display_name:
            name, description = display_name.split(" - ", 1)
        else:
            name = display_name
            description = ""

        # Nom de la voix (en gras)
        name_label = tk.Label(text_frame, text=name, font=('Helvetica', 10, 'bold'),
                              anchor="w", justify=tk.LEFT)
        name_label.pack(anchor="w", fill="x")

        # Description (si présente)
        if description:
            desc_label = tk.Label(text_frame, text=description, anchor="w", justify=tk.LEFT,
                                  wraplength=400, fg="grey", font=('Helvetica', 9))
            desc_label.pack(anchor="w", fill="x")

        # --- Colonne 1: Boutons (alignés à droite et centrés verticalement) ---
        button_frame = tk.Frame(row_frame)
        button_frame.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        # Créer un conteneur pour centrer verticalement les boutons
        buttons_container = tk.Frame(button_frame)
        buttons_container.pack(expand=True, fill="both")

        # Frame pour les boutons avec centrage vertical
        buttons_inner = tk.Frame(buttons_container)
        buttons_inner.pack(expand=True, anchor="center")  # Centre verticalement

        # Bouton Play
        if provider == "gemini" and self.play_gemini_sample:
            play_btn = tk.Button(buttons_inner, text="▶", width=3, height=1,
                                 command=lambda v=play_identifier: self.play_gemini_sample(v))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))
        elif provider == "elevenlabs" and self.play_elevenlabs_sample:
            play_btn = tk.Button(buttons_inner, text="▶", width=3, height=1,
                                 command=lambda i=voice_id, u=play_identifier: self.play_elevenlabs_sample(i, u))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Bouton Add
        add_btn = tk.Button(buttons_inner, text="Add", width=6, height=1,
                            command=lambda p=provider, d=display_name, i=voice_id: self.add_voice_to_speakers(p, d, i))
        add_btn.pack(side=tk.LEFT)

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

        if self._loading_voices:
            return

        self._loading_voices = True

        import keyring
        import requests

        def fetch_voices():
            try:
                try:
                    self.winfo_class()
                except tk.TclError:
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

                logging.info("Attempting to fetch ElevenLabs voices from v1 endpoint...")
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
                        preview_url = voice.get('preview_url', '')

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
                            'labels': labels,
                            'preview_url': preview_url
                        })

                    voices.sort(key=lambda x: x.get('name', ''))
                    self.elevenlabs_voices = voices
                    self.elevenlabs_voices_loaded = True

                    logging.info(f"Loaded {len(voices)} voices and flagged UI for update.")
                    self._voices_need_update = True

                else:
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    logging.error(f"ElevenLabs API Error: {response.status_code} - {response.text[:200]}")

            except requests.exceptions.Timeout:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                self.after(100, self.populate_fields_delayed)
            except requests.exceptions.RequestException as e:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                logging.error(f"Network error loading ElevenLabs voices: {e}")
                self.after(100, self.populate_fields_delayed)
            except Exception as e:
                self.elevenlabs_voices = []
                self.elevenlabs_voices_loaded = False
                logging.error(f"Error loading ElevenLabs voices: {e}")
                self.after(100, self.populate_fields_delayed)

        thread = threading.Thread(target=fetch_voices, daemon=True)
        thread.start()

    def populate_fields_delayed(self):
        """Populate les champs après que les voix ElevenLabs aient été chargées (ou échoué)."""
        self.populate_fields()

    def add_voice_to_speakers(self, provider, voice_display_name, voice_id):
        """Adds a selected voice from the guide to the speaker list."""
        # Find the first empty speaker row, or create a new one
        target_row = None
        for row in self.entries:
            if not row['speaker'].get().strip():
                target_row = row
                break

        if not target_row:
            self.add_row()
            target_row = self.entries[-1]

        # Generate a unique default speaker name
        existing_names = {r['speaker'].get().strip() for r in self.entries if r['speaker'].get().strip()}
        i = 1
        while f"Speaker {i}" in existing_names:
            i += 1
        target_row['speaker'].delete(0, tk.END)
        target_row['speaker'].insert(0, f"Speaker {i}")

        # Set the voice in the correct combobox
        if provider == 'gemini' and target_row.get('gemini_voice'):
            # For Gemini, the display name is what we store.
            target_row['gemini_voice'].set(voice_display_name)
        elif provider == 'elevenlabs' and target_row.get('elevenlabs_voice'):
            # For ElevenLabs, we also use the display name for the combobox.
            target_row['elevenlabs_voice'].set(voice_display_name)

    def update_elevenlabs_comboboxes(self):
        """Met à jour toutes les comboboxes ElevenLabs avec les nouvelles voix chargées."""
        try:
            if not self.elevenlabs_voices_loaded or not self.elevenlabs_voices:
                return
            self.winfo_class()
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


        if self.save_callback:
            self.save_callback(new_settings)

        if self.close_callback:
            self.close_callback()
        self.destroy()

    def populate_fields(self):
        """Remplit les champs avec les paramètres actuels."""

        speaker_voices = self.current_settings.get('speaker_voices', {})
        speaker_voices_elevenlabs = self.current_settings.get('speaker_voices_elevenlabs', {})

        voice_settings = self.current_settings.get('voice_settings', {})

        if voice_settings:
            for speaker_name, voices in voice_settings.items():
                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=voices.get('gemini_voice', ''),
                    elevenlabs_voice=voices.get('elevenlabs_voice', '')
                )
        elif speaker_voices:
            all_speakers = set(speaker_voices.keys()) | set(speaker_voices_elevenlabs.keys())

            for speaker_name in all_speakers:
                gemini_voice = speaker_voices.get(speaker_name, '')
                elevenlabs_data = speaker_voices_elevenlabs.get(speaker_name, '')

                # Normaliser le libellé Gemini pour l'affichage: "Name" -> "Name - Desc" si possible
                gemini_display = gemini_voice
                if isinstance(gemini_voice, str) and ' - ' not in gemini_voice and gemini_voice in AVAILABLE_VOICES:
                    desc = AVAILABLE_VOICES.get(gemini_voice, '').strip()
                    gemini_display = f"{gemini_voice} - {desc}" if desc else gemini_voice

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

                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=gemini_display,
                    elevenlabs_voice=elevenlabs_voice_display
                )
        else:
            self.add_row()

    def add_row(self, speaker_name='', gemini_voice='', elevenlabs_voice=''):
        """Ajoute une nouvelle ligne de paramètres."""
        row_frame = tk.Frame(self.speaker_frame)
        row_frame.pack(fill=tk.X, pady=2)

        # Entry pour le nom du speaker - largeur augmentée pour correspondre aux headers
        speaker_entry = tk.Entry(row_frame, width=30)
        speaker_entry.pack(side=tk.LEFT, padx=(0, 10))
        speaker_entry.insert(0, speaker_name)

        row_data = {
            'frame': row_frame,
            'speaker': speaker_entry,
            'gemini_voice': None,
            'elevenlabs_voice': None
        }

        # Combobox Gemini (si API configurée)
        if self.gemini_api_configured:
            gemini_combo = ttk.Combobox(row_frame, values=self.VOICE_DISPLAY_LIST,
                                        width=30, state="readonly")
            gemini_combo.pack(side=tk.LEFT, padx=(0, 10))
            if gemini_voice:
                gemini_combo.set(gemini_voice)
            row_data['gemini_voice'] = gemini_combo

        # Combobox ElevenLabs (si API configurée)
        if self.elevenlabs_api_configured:
            elevenlabs_values = []
            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]

            elevenlabs_combo = ttk.Combobox(row_frame, values=elevenlabs_values,
                                            width=30, state="readonly")
            elevenlabs_combo.pack(side=tk.LEFT, padx=(0, 10))
            if elevenlabs_voice:
                elevenlabs_combo.set(elevenlabs_voice)
            row_data['elevenlabs_voice'] = elevenlabs_combo

        # Bouton de suppression
        remove_btn = tk.Button(row_frame, text="-", width=3,
                               command=lambda r=row_frame: self.remove_row(r))
        remove_btn.pack(side=tk.RIGHT)

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