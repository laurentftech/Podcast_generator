import logging
import tkinter as tk
import threading
import json
import keyring
import sys
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

        self.withdraw()
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

        # Fix pour le bandeau de titre sombre sur Windows
        if sys.platform == "win32":
            try:
                # Cette méthode force Windows à utiliser un bandeau de titre sombre
                # compatible avec le mode sombre de l'application
                self.after(10, lambda: self.wm_attributes("-alpha", 0.99))
                self.after(20, lambda: self.wm_attributes("-alpha", 1.0))
                # Alternative plus robuste pour Windows 10/11
                try:
                    import ctypes
                    from ctypes import wintypes

                    # Constantes Windows pour le mode sombre
                    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20

                    # Obtenir le handle de la fenêtre
                    hwnd = int(self.wm_frame(), 16)

                    # Essayer d'abord avec la nouvelle constante (Windows 10 20H1+)
                    try:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            DWMWA_USE_IMMERSIVE_DARK_MODE,
                            ctypes.byref(ctypes.c_int(1)),
                            ctypes.sizeof(ctypes.c_int)
                        )
                    except:
                        # Fallback pour les versions plus anciennes
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                            ctypes.byref(ctypes.c_int(1)),
                            ctypes.sizeof(ctypes.c_int)
                        )
                except Exception as e:
                    logging.debug(f"Could not set dark title bar: {e}")
            except Exception as e:
                logging.debug(f"Title bar styling failed: {e}")

        self.gemini_api_configured = bool(keyring.get_password("PodcastGenerator", "gemini_api_key"))
        self.elevenlabs_api_configured = bool(keyring.get_password("PodcastGenerator", "elevenlabs_api_key"))

        self.default_settings = default_settings
        self.current_settings = dict(current_settings)
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.cancel_and_close)
        self.play_gemini_sample = play_gemini_sample_callback
        self.play_elevenlabs_sample = play_elevenlabs_sample_callback

        self.entries = []
        self.guide_play_buttons = []  # Pour gérer l'activation des boutons play

        self.elevenlabs_voices = []
        self.elevenlabs_voices_loaded = False
        self._loading_voices = False
        self._voices_need_update = False
        self._voices_update_in_progress = False  # Protection contre les appels multiples

        # Pour le chargement progressif des voix ElevenLabs
        self.elevenlabs_voice_offset = 0
        self.load_more_btn = None
        self.elevenlabs_scroll_frame = None  # Pour stocker la référence au frame
        self._elevenlabs_voices_displayed = False  # Flag pour éviter les doublons
        self._loading_more_voices = False  # Protection contre les appels simultanés

        # Pour éviter les doublons Gemini
        self._gemini_voices_displayed = False
        self.gemini_scroll_frame = None

        if isinstance(preloaded_elevenlabs_voices, list) and preloaded_elevenlabs_voices:
            self.elevenlabs_voices = list(preloaded_elevenlabs_voices)
            self.elevenlabs_voices_loaded = True
            self._voices_need_update = True

        self.create_interface()
        self.populate_fields()

        if not self.elevenlabs_voices_loaded:
            self.after(500, self.load_elevenlabs_voices)

        self.check_voices_update()

        self.update_idletasks()
        # Forcer une largeur minimale sous Windows pour éviter une fenêtre trop étroite à l'ouverture
        if sys.platform == "win32":
            self.geometry("800x600")  # Définit une taille de départ raisonnable

        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.deiconify()

        # Activate play buttons after the window is shown to avoid race conditions
        # A longer delay is more robust on slower systems or different architectures like Mac ARM.
        self.after(1000, self._enable_play_buttons)

    def _enable_play_buttons(self):
        """Active tous les boutons de lecture dans les guides vocaux."""
        for button in self.guide_play_buttons:
            if button and button.winfo_exists():
                button.configure(state="normal")

    def check_voices_update(self):
        """Vérifie périodiquement si les voix doivent être mises à jour."""
        if self._voices_need_update and self.elevenlabs_voices_loaded and not self._voices_update_in_progress:
            self._voices_need_update = False
            self._voices_update_in_progress = True
            try:
                self.update_elevenlabs_comboboxes()
                # Déclencher le chargement des voix dans le guide si pas encore fait
                if not self._elevenlabs_voices_displayed and self.elevenlabs_scroll_frame:
                    self._load_more_elevenlabs_voices()
            finally:
                self._voices_update_in_progress = False

        # Continue à vérifier mais avec intervalle plus long sur macOS
        try:
            if self.winfo_exists():
                interval = 500 if sys.platform == "darwin" else 200
                self.after(interval, self.check_voices_update)
        except tk.TclError:
            pass  # Window destroyed

    def create_interface(self):
        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)

        speaker_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        speaker_section.pack(fill=tk.X, padx=10, pady=10)
        customtkinter.CTkLabel(speaker_section, text="My Speaker Voices",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        speaker_config_frame = customtkinter.CTkFrame(speaker_section, border_width=1, fg_color="transparent")
        speaker_config_frame.pack(fill=tk.X, pady=(5, 0))

        self._create_speaker_headers(speaker_config_frame)

        self.speaker_frame = customtkinter.CTkFrame(speaker_config_frame, fg_color="transparent")
        self.speaker_frame.pack(fill=tk.X, expand=True, padx=10, pady=(0, 5))

        if self.gemini_api_configured or self.elevenlabs_api_configured:
            guides_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
            guides_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
            customtkinter.CTkLabel(guides_section, text="Voice Guides",
                                   font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")

            notebook = customtkinter.CTkTabview(guides_section, border_width=1)
            notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

            if self.gemini_api_configured:
                gemini_tab = notebook.add("Gemini Voices")
                # Créer le scrollable frame et le stocker pour éviter de recréer les voix
                self.gemini_scroll_frame = customtkinter.CTkScrollableFrame(gemini_tab, label_text="")
                self.gemini_scroll_frame.pack(fill="both", expand=True)
                self._populate_guide_tab(self.gemini_scroll_frame, "gemini")

            if self.elevenlabs_api_configured:
                elevenlabs_tab = notebook.add("ElevenLabs Voices")
                # Créer le conteneur une seule fois
                self.elevenlabs_scroll_frame = customtkinter.CTkScrollableFrame(elevenlabs_tab, label_text="")
                self.elevenlabs_scroll_frame.pack(fill="both", expand=True)
                # Le chargement sera déclenché par check_voices_update() quand les voix seront prêtes
                if self.elevenlabs_voices_loaded:
                    self._load_more_elevenlabs_voices()

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
        header_frame = customtkinter.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.pack(fill=tk.X, padx=10, pady=(5, 5))

        customtkinter.CTkLabel(header_frame, text="Speaker Name (in script)",
                               font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT, padx=(0, 10))

        if self.gemini_api_configured:
            customtkinter.CTkLabel(header_frame, text="Gemini Voice",
                                   font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT,
                                                                                              padx=(0, 10))

        if self.elevenlabs_api_configured:
            customtkinter.CTkLabel(header_frame, text="ElevenLabs Voice",
                                   font=customtkinter.CTkFont(weight="bold"), width=220).pack(side=tk.LEFT,
                                                                                              padx=(0, 10))

    def _populate_guide_tab(self, scrollable_frame, provider):
        """Peuple l'onglet des voix Gemini. Ne doit être appelé qu'une seule fois."""
        # Protection contre les appels multiples (doublons)
        if provider == "gemini" and self._gemini_voices_displayed:
            return

        voices = list(AVAILABLE_VOICES.items())
        for i, (name, desc) in enumerate(voices):
            self._create_guide_row(scrollable_frame, provider, name, f"{name} - {desc}", name)
            if i < len(voices) - 1:
                separator = customtkinter.CTkFrame(scrollable_frame, height=1, fg_color=("gray80", "gray25"))
                separator.pack(fill='x', pady=5, padx=5)

        # Marquer comme affiché
        if provider == "gemini":
            self._gemini_voices_displayed = True

    def _create_guide_row(self, parent, provider, voice_id, display_name, play_identifier):
        # Set a fixed height for each row and prevent it from resizing.
        # This makes layout calculations much faster and scrolling smoother.
        row_frame = customtkinter.CTkFrame(parent, fg_color="transparent", height=55)
        row_frame.pack(fill=tk.X, pady=2)
        row_frame.pack_propagate(False)  # This is the key to enforcing the height

        row_frame.columnconfigure(0, weight=1)
        # Configure the row to center the content vertically
        row_frame.rowconfigure(0, weight=1)

        text_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        # Use sticky="w" to align left, the rowconfigure will handle vertical centering
        text_frame.grid(row=0, column=0, sticky="w", padx=(5, 10))

        name, _, description = display_name.partition(" - ")
        customtkinter.CTkLabel(text_frame, text=name, font=customtkinter.CTkFont(weight="bold"),
                               anchor="w").pack(anchor="w", fill="x")
        if description:
            # We still wrap, but the container's fixed height prevents layout jumps.
            customtkinter.CTkLabel(text_frame, text=description, anchor="w", wraplength=400,
                                   font=customtkinter.CTkFont(size=11)).pack(anchor="w", fill="x")

        buttons_inner = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        # Use sticky="e" to align right
        buttons_inner.grid(row=0, column=1, sticky="e", padx=(0, 5))

        play_btn = None
        if provider == "gemini" and self.play_gemini_sample:
            play_btn = customtkinter.CTkButton(buttons_inner, text="▶", width=30, height=30, state="disabled")
            play_btn.configure(command=lambda b=play_btn, v=play_identifier: self.play_gemini_sample(b, v))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))
        elif provider == "elevenlabs" and self.play_elevenlabs_sample:
            play_btn = customtkinter.CTkButton(buttons_inner, text="▶", width=30, height=30, state="disabled")
            play_btn.configure(
                command=lambda b=play_btn, i=voice_id, u=play_identifier: self.play_elevenlabs_sample(b, i, u))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))

        if play_btn:
            self.guide_play_buttons.append(play_btn)

        add_btn = customtkinter.CTkButton(buttons_inner, text="Add", width=60, height=30,
                                          command=lambda p=provider, d=display_name,
                                                         i=voice_id: self.add_voice_to_speakers(p, d, i))
        add_btn.pack(side=tk.LEFT)

    def _load_more_elevenlabs_voices(self):
        """Charge le prochain lot de voix ElevenLabs dans le frame existant."""
        if not self.elevenlabs_scroll_frame:
            return

        # Protection contre les appels multiples
        if hasattr(self, '_loading_more_voices') and self._loading_more_voices:
            return
        self._loading_more_voices = True

        try:
            # Supprimer l'ancien bouton "Charger plus" s'il existe
            if self.load_more_btn:
                try:
                    if self.load_more_btn.winfo_exists():
                        self.load_more_btn.destroy()
                except tk.TclError:
                    pass
                self.load_more_btn = None

            if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
                # Si c'est le premier chargement et que des voix sont déjà affichées, ne rien faire
                if self.elevenlabs_voice_offset == 0 and self._elevenlabs_voices_displayed:
                    return

                voices_to_display = self.elevenlabs_voices[self.elevenlabs_voice_offset : self.elevenlabs_voice_offset + 20]

                if voices_to_display:  # Seulement si on a des voix à afficher
                    for voice in voices_to_display:
                        self._create_guide_row(self.elevenlabs_scroll_frame, "elevenlabs", voice['id'],
                                             voice['display_name'], voice['preview_url'])
                        separator = customtkinter.CTkFrame(self.elevenlabs_scroll_frame, height=1,
                                                          fg_color=("gray80", "gray25"))
                        separator.pack(fill='x', pady=5, padx=5)

                    self.elevenlabs_voice_offset += len(voices_to_display)
                    self._elevenlabs_voices_displayed = True

                    # S'il reste des voix à charger, recréer le bouton
                    if self.elevenlabs_voice_offset < len(self.elevenlabs_voices):
                        self.load_more_btn = customtkinter.CTkButton(
                            self.elevenlabs_scroll_frame,
                            text=f"Load more... ({self.elevenlabs_voice_offset}/{len(self.elevenlabs_voices)})",
                            command=self._load_more_elevenlabs_voices
                        )
                        self.load_more_btn.pack(pady=10)
                    
                    # Enable the newly added buttons
                    self.after(100, self._enable_play_buttons)

            elif not self.elevenlabs_voices_loaded:
                # Afficher un message de chargement seulement si rien n'est affiché
                if not self._elevenlabs_voices_displayed:
                    customtkinter.CTkLabel(self.elevenlabs_scroll_frame,
                                         text="Loading ElevenLabs voices...").pack(pady=20)
        finally:
            self._loading_more_voices = False

    def safe_update_button(self, state, text):
        try:
            if hasattr(self,
                       'refresh_voices_btn') and self.refresh_voices_btn and self.refresh_voices_btn.winfo_exists():
                self.refresh_voices_btn.configure(state=state, text=text)
        except (tk.TclError, AttributeError, TypeError) as e:
            logging.warning(f"Error updating button state (ignored): {e}")

    def load_elevenlabs_voices(self):
        if self._loading_voices:
            return
        self._loading_voices = True

        def fetch_voices():
            try:
                if not self.winfo_exists(): return
                self.after(0, lambda: self.safe_update_button('disabled', '⏳'))
                if not requests:
                    self.elevenlabs_voices, self.elevenlabs_voices_loaded = [], False
                    return
                api_key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
                if not api_key:
                    self.elevenlabs_voices, self.elevenlabs_voices_loaded = [], False
                    return
                headers = {"xi-api-key": api_key}
                response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=15)
                if response.status_code == 200:
                    voices_data = response.json().get('voices', [])
                    voices = []
                    for voice in voices_data:
                        labels = voice.get('labels', {}) or {}
                        desc_parts = [p.title() for p in [labels.get('gender'), labels.get('age'), labels.get('accent')]
                                      if p]
                        description = ', '.join(desc_parts) or str(voice.get('category', '')).title()
                        display_name = f"{voice.get('name', 'Unknown')} - {description}" if description else voice.get(
                            'name', 'Unknown')
                        voices.append({'id': voice.get('voice_id', ''), 'name': voice.get('name', 'Unknown'),
                                       'display_name': display_name, 'category': voice.get('category', ''),
                                       'labels': labels, 'preview_url': voice.get('preview_url', '')})
                    voices.sort(key=lambda x: x.get('name', ''))
                    self.elevenlabs_voices = voices
                    self.elevenlabs_voices_loaded = True
                    self._voices_need_update = True
                else:
                    self.elevenlabs_voices, self.elevenlabs_voices_loaded = [], False
            except Exception as e:
                logging.error(f"Error loading ElevenLabs voices: {e}")
                self.elevenlabs_voices, self.elevenlabs_voices_loaded = [], False
            finally:
                if not self.winfo_exists(): return
                self.after(100, self.populate_fields_delayed)

        threading.Thread(target=fetch_voices, daemon=True).start()

    def populate_fields_delayed(self):
        self.populate_fields()

    def add_voice_to_speakers(self, provider, voice_display_name, voice_id):
        target_row = next((row for row in self.entries if not row['speaker'].get().strip()), None)
        if not target_row:
            self.add_row()
            target_row = self.entries[-1]
        existing_names = {r['speaker'].get().strip() for r in self.entries if r['speaker'].get().strip()}
        i = 1
        while f"Speaker {i}" in existing_names: i += 1
        target_row['speaker'].delete(0, tk.END)
        target_row['speaker'].insert(0, f"Speaker {i}")
        if provider == 'gemini' and target_row.get('gemini_voice'):
            target_row['gemini_voice'].set(voice_display_name)
        elif provider == 'elevenlabs' and target_row.get('elevenlabs_voice'):
            target_row['elevenlabs_voice'].set(voice_display_name)

    def update_elevenlabs_comboboxes(self):
        try:
            if not self.elevenlabs_voices_loaded or not self.elevenlabs_voices or not self.winfo_exists():
                return
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
        except Exception as e:
            logging.warning(f"Error updating comboboxes: {e}")

    def cancel_and_close(self):
        if self.close_callback: self.close_callback()
        self.destroy()

    def save_and_close(self):
        new_settings = json.loads(json.dumps(self.current_settings))
        ui_speakers = {row['speaker'].get().strip() for row in self.entries if row['speaker'].get().strip()}
        for voice_dict_key in ['speaker_voices', 'speaker_voices_elevenlabs']:
            if voice_dict_key in new_settings:
                for speaker in list(new_settings[voice_dict_key]):
                    if speaker not in ui_speakers: del new_settings[voice_dict_key][speaker]
        for row in self.entries:
            speaker_name = row['speaker'].get().strip()
            if not speaker_name: continue
            if row.get('gemini_voice'):
                new_settings.setdefault('speaker_voices', {})[speaker_name] = row['gemini_voice'].get()
            if row.get('elevenlabs_voice'):
                display = row['elevenlabs_voice'].get()
                # Try to find the voice_id from the loaded voices
                voice_id = next((v['id'] for v in self.elevenlabs_voices if v['display_name'] == display), None)

                # If voice_id is not found (voices not loaded yet), preserve the existing ID from current_settings
                if voice_id is None:
                    existing_data = self.current_settings.get('speaker_voices_elevenlabs', {}).get(speaker_name, {})
                    if isinstance(existing_data, dict) and existing_data.get('display_name') == display:
                        # Keep the existing voice_id if the display_name hasn't changed
                        voice_id = existing_data.get('id', '')
                    else:
                        voice_id = ''

                new_settings.setdefault('speaker_voices_elevenlabs', {})[speaker_name] = {'id': voice_id,
                                                                                          'display_name': display}
        if self.save_callback: self.save_callback(new_settings)
        if self.close_callback: self.close_callback()
        self.destroy()

    def populate_fields(self):
        if self.entries: return
        speaker_voices = self.current_settings.get('speaker_voices', {})
        speaker_voices_elevenlabs = self.current_settings.get('speaker_voices_elevenlabs', {})
        all_speakers = set(speaker_voices.keys()) | set(speaker_voices_elevenlabs.keys())
        if all_speakers:
            for speaker_name in sorted(list(all_speakers)):
                gemini_voice = speaker_voices.get(speaker_name, '')
                gemini_display = gemini_voice
                if isinstance(gemini_voice, str) and ' - ' not in gemini_voice and gemini_voice in AVAILABLE_VOICES:
                    gemini_display = f"{gemini_voice} - {AVAILABLE_VOICES.get(gemini_voice, '')}"
                elevenlabs_data = speaker_voices_elevenlabs.get(speaker_name, {})
                elevenlabs_display = elevenlabs_data.get('display_name', '') if isinstance(elevenlabs_data,
                                                                                           dict) else ''
                self.add_row(speaker_name=speaker_name, gemini_voice=gemini_display,
                             elevenlabs_voice=elevenlabs_display)
        else:
            self.add_row()

    def add_row(self, speaker_name='', gemini_voice='', elevenlabs_voice=''):
        row_frame = customtkinter.CTkFrame(self.speaker_frame, fg_color="transparent")
        row_frame.pack(fill=tk.X, pady=2)
        textbox_fg_color = customtkinter.ThemeManager.theme["CTkTextbox"]["fg_color"]
        speaker_entry = customtkinter.CTkEntry(row_frame, width=220, border_width=1, fg_color=textbox_fg_color)
        speaker_entry.pack(side=tk.LEFT, padx=(0, 10), fill='x')
        speaker_entry.insert(0, speaker_name)
        row_data = {'frame': row_frame, 'speaker': speaker_entry, 'gemini_voice': None, 'elevenlabs_voice': None}
        if self.gemini_api_configured:
            gemini_combo = customtkinter.CTkComboBox(row_frame, values=self.VOICE_DISPLAY_LIST, width=220,
                                                     state="readonly")
            gemini_combo.pack(side=tk.LEFT, padx=(0, 10), fill='x')
            if gemini_voice: gemini_combo.set(gemini_voice)
            row_data['gemini_voice'] = gemini_combo
        if self.elevenlabs_api_configured:
            elevenlabs_values = [v['display_name'] for v in
                                 self.elevenlabs_voices] if self.elevenlabs_voices_loaded else []
            elevenlabs_combo = customtkinter.CTkComboBox(row_frame, values=elevenlabs_values, width=220,
                                                         state="readonly")
            elevenlabs_combo.pack(side=tk.LEFT, padx=(0, 10), fill='x')
            if elevenlabs_voice: elevenlabs_combo.set(elevenlabs_voice)
            row_data['elevenlabs_voice'] = elevenlabs_combo
        remove_btn = customtkinter.CTkButton(row_frame, text="-", width=30,
                                             command=lambda r=row_frame: self.remove_row(r))
        remove_btn.pack(side=tk.RIGHT)
        row_data['remove_btn'] = remove_btn
        self.entries.append(row_data)

        # Force an explicit resize of the window to fit the new content.
        # This is more reliable than just calling update_idletasks().
        self.update_idletasks()  # Ensure new widgets are processed
        new_height = self.winfo_reqheight()
        self.geometry(f"{self.winfo_width()}x{new_height}")

    def remove_row(self, row_frame):
        entry_to_remove = next((e for e in self.entries if e['frame'] == row_frame), None)
        if entry_to_remove:
            row_frame.destroy()
            self.entries.remove(entry_to_remove)
            # Also update the size when a row is removed.
            self.update_idletasks() # Ensure widgets are removed
            new_height = self.winfo_reqheight()
            self.geometry(f"{self.winfo_width()}x{new_height}")

    def restore_defaults(self):
        for row in self.entries: row['frame'].destroy()
        self.entries.clear()
        self.current_settings = dict(self.default_settings)
        self.populate_fields()