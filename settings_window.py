import logging
import tkinter as tk
import threading
import json
import keyring
import customtkinter

from gui import AVAILABLE_VOICES

try:
    import requests
except ImportError:
    requests = None

class VoiceSettingsWindow(customtkinter.CTkToplevel):
    VOICE_DISPLAY_LIST = [f"{name} - {desc}" for name, desc in AVAILABLE_VOICES.items()]

    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings,
                 preloaded_elevenlabs_voices=None,
                 play_gemini_sample_callback=None,
                 play_elevenlabs_sample_callback=None):
        super().__init__(parent)

        # --- Hide window during setup to prevent flickering ---
        self.withdraw()

        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

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

        # --- Center and show the fully-built window ---
        self.update_idletasks()  # Ensure all widgets are drawn and have a size
        # Center the window on the parent
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.deiconify()  # Show the window

    def check_voices_update(self):
        """Vérifie périodiquement si les voix ont besoin d'être mises à jour."""
        if self._voices_need_update and self.elevenlabs_voices_loaded:
            self._voices_need_update = False
            self.update_elevenlabs_comboboxes()

        # Reprogram la vérification dans 200ms
        self.after(200, self.check_voices_update)

    def create_interface(self):
        """Crée l'interface utilisateur de base."""
        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: Speaker Configuration ---
        speaker_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        speaker_section.pack(fill=tk.X, padx=10, pady=10)
        customtkinter.CTkLabel(speaker_section, text="My Speaker Voices",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        speaker_config_frame = customtkinter.CTkFrame(speaker_section, border_width=1, fg_color="transparent")
        speaker_config_frame.pack(fill=tk.X, pady=(5, 0))

        self._create_speaker_headers(speaker_config_frame)

        self.speaker_frame = customtkinter.CTkFrame(speaker_config_frame, fg_color="transparent")
        self.speaker_frame.pack(fill=tk.X, expand=True, padx=10, pady=(0, 5))

        # --- Section 2: Voice Guides (Tabs) ---
        # N'afficher cette section que si au moins une clé API est configurée.
        if self.gemini_api_configured or self.elevenlabs_api_configured:
            guides_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
            guides_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
            customtkinter.CTkLabel(guides_section, text="Voice Guides",
                                   font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")

            notebook = customtkinter.CTkTabview(guides_section, border_width=1)
            notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

            if self.gemini_api_configured:
                gemini_tab = notebook.add("Gemini Voices")
                self._populate_guide_tab(gemini_tab, "gemini")

            if self.elevenlabs_api_configured:
                elevenlabs_tab = notebook.add("ElevenLabs Voices")
                self._populate_guide_tab(elevenlabs_tab, "elevenlabs")

        # --- Section 3: Main Buttons ---
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=tk.X, padx=10, pady=(15, 10))
        button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        customtkinter.CTkButton(button_frame, text="+ Add Speaker", command=self.add_row).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        customtkinter.CTkButton(button_frame, text="Restore Defaults", command=self.restore_defaults).grid(
            row=0, column=1, sticky="ew", padx=5)
        customtkinter.CTkButton(button_frame, text="Cancel", command=self.cancel_and_close,
                                fg_color="transparent", text_color=("gray10", "gray90"), border_width=1).grid(
            row=0, column=2, sticky="ew", padx=5)
        customtkinter.CTkButton(button_frame, text="Save", command=self.save_and_close).grid(
            row=0, column=3, sticky="ew", padx=(5, 0))

    def _create_speaker_headers(self, parent_frame):
        """Creates the headers for the speaker configuration section."""
        header_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

        customtkinter.CTkLabel(header_frame, text="Speaker Name (in script)",
                               font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT, padx=(0, 10))

        if self.gemini_api_configured:
            customtkinter.CTkLabel(header_frame, text="Gemini Voice",
                                   font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT, padx=(0, 10))

        if self.elevenlabs_api_configured:
            customtkinter.CTkLabel(header_frame, text="ElevenLabs Voice",
                                   font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT, padx=(0, 10))

    def _populate_guide_tab(self, tab, provider):
        """Populates a tab with voice samples using CTkScrollableFrame."""
        scrollable_frame = customtkinter.CTkScrollableFrame(tab, label_text="")
        scrollable_frame.pack(fill="both", expand=True)

        # Remplir le contenu selon le provider
        if provider == "gemini":
            voices = list(AVAILABLE_VOICES.items())
            for i, (name, desc) in enumerate(voices):
                self._create_guide_row(scrollable_frame, provider, name, f"{name} - {desc}", name)
                if i < len(voices) - 1:
                    separator = customtkinter.CTkFrame(scrollable_frame, height=1, fg_color=("gray80", "gray25"))
                    separator.pack(fill='x', pady=5, padx=5)
        elif provider == "elevenlabs":
            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                voices = self.elevenlabs_voices
                for i, voice in enumerate(voices):
                    self._create_guide_row(scrollable_frame, provider, voice['id'], voice['display_name'], voice['preview_url'])
                    if i < len(voices) - 1:
                        separator = customtkinter.CTkFrame(scrollable_frame, height=1, fg_color=("gray80", "gray25"))
                        separator.pack(fill='x', pady=5, padx=5)
            else:
                customtkinter.CTkLabel(scrollable_frame, text="Loading ElevenLabs voices...").pack(pady=20)

    def _create_guide_row(self, parent, provider, voice_id, display_name, play_identifier):
        """Creates a single row in the voice guide with perfect button alignment."""
        row_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill=tk.X, pady=2)
        row_frame.columnconfigure(0, weight=1)

        # --- Colonne 0: Contenu texte ---
        text_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        if " - " in display_name:
            name, description = display_name.split(" - ", 1)
        else:
            name = display_name
            description = ""

        customtkinter.CTkLabel(text_frame, text=name, font=customtkinter.CTkFont(weight="bold"),
                               anchor="w").pack(anchor="w", fill="x")

        if description:
            customtkinter.CTkLabel(text_frame, text=description, anchor="w", wraplength=400,
                                   font=customtkinter.CTkFont(size=11)).pack(anchor="w", fill="x")

        # --- Colonne 1: Boutons (alignés à droite et centrés verticalement) ---
        buttons_inner = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        buttons_inner.grid(row=0, column=1, sticky="e")

        # Bouton Play
        if provider == "gemini" and self.play_gemini_sample:
            play_btn = customtkinter.CTkButton(buttons_inner, text="▶", width=30, height=30)
            play_btn.configure(command=lambda b=play_btn, v=play_identifier: self.play_gemini_sample(b, v))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))
        elif provider == "elevenlabs" and self.play_elevenlabs_sample:
            play_btn = customtkinter.CTkButton(buttons_inner, text="▶", width=30, height=30)
            play_btn.configure(
                command=lambda b=play_btn, i=voice_id, u=play_identifier: self.play_elevenlabs_sample(b, i, u))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Bouton Add
        add_btn = customtkinter.CTkButton(buttons_inner, text="Add", width=60, height=30,
                                          command=lambda p=provider, d=display_name,
                                                         i=voice_id: self.add_voice_to_speakers(p, d, i))
        add_btn.pack(side=tk.LEFT)

    def safe_update_button(self, state, text):
        """Met à jour le bouton de manière sécurisée."""
        try:
            if (hasattr(self, 'refresh_voices_btn') and
                    self.refresh_voices_btn is not None):
                if self.refresh_voices_btn.winfo_exists():
                    self.refresh_voices_btn.configure(state=state, text=text)
        except (tk.TclError, AttributeError, TypeError) as e:
            logging.warning(f"Error updating button state (ignored): {e}")
            pass

    def load_elevenlabs_voices(self):
        """Charge la liste des voix ElevenLabs depuis l'API."""

        if self._loading_voices:
            return

        self._loading_voices = True

        def fetch_voices():
            try:
                try:
                    self.winfo_class()
                except tk.TclError:
                    return

                self.after(0, lambda: self.safe_update_button('disabled', '⏳'))

                if not requests:
                    logging.warning("'requests' library not found. Cannot fetch ElevenLabs voices.")
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    self.after(100, self.populate_fields_delayed)
                    return

                api_key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
                if not api_key:
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    logging.warning("No ElevenLabs API key configured. Cannot fetch voices.")
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
            logging.warning(f"Error updating comboboxes: {e}")

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

        # Si des lignes existent déjà dans l'UI, ne pas les écraser
        if self.entries:
            return

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
            # Seulement ajouter une ligne par défaut si aucune configuration n'existe
            # ET si aucune ligne n'est déjà présente dans l'UI
            self.add_row()

    def add_row(self, speaker_name='', gemini_voice='', elevenlabs_voice=''):
        """Ajoute une nouvelle ligne de paramètres."""
        row_frame = customtkinter.CTkFrame(self.speaker_frame, fg_color="transparent")
        row_frame.pack(fill=tk.X, pady=2)

        # Harmonisation du style avec la zone de texte principale
        # On récupère la couleur de fond par défaut d'un CTkTextbox pour l'appliquer
        textbox_fg_color = customtkinter.ThemeManager.theme["CTkTextbox"]["fg_color"]

        # Entry pour le nom du speaker - largeur augmentée pour correspondre aux headers
        speaker_entry = customtkinter.CTkEntry(row_frame, width=220, border_width=1, fg_color=textbox_fg_color)
        speaker_entry.pack(side=tk.LEFT, padx=(0, 10), fill='x')
        speaker_entry.insert(0, speaker_name)

        row_data = {
            'frame': row_frame,
            'speaker': speaker_entry,
            'gemini_voice': None,
            'elevenlabs_voice': None
        }

        # Combobox Gemini (si API configurée)
        if self.gemini_api_configured:
            gemini_combo = customtkinter.CTkComboBox(row_frame, values=self.VOICE_DISPLAY_LIST, width=220,
                                                     state="readonly")
            gemini_combo.pack(side=tk.LEFT, padx=(0, 10), fill='x')
            if gemini_voice:
                gemini_combo.set(gemini_voice)
            row_data['gemini_voice'] = gemini_combo

        # Combobox ElevenLabs (si API configurée)
        if self.elevenlabs_api_configured:
            elevenlabs_values = []
            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]

            elevenlabs_combo = customtkinter.CTkComboBox(row_frame, values=elevenlabs_values, width=220,
                                                         state="readonly")
            elevenlabs_combo.pack(side=tk.LEFT, padx=(0, 10), fill='x')
            if elevenlabs_voice:
                elevenlabs_combo.set(elevenlabs_voice)
            row_data['elevenlabs_voice'] = elevenlabs_combo

        # Bouton de suppression
        remove_btn = customtkinter.CTkButton(row_frame, text="-", width=30, command=lambda r=row_frame: self.remove_row(r))
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