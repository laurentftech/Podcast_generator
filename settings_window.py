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

        self.withdraw()
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

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

        if isinstance(preloaded_elevenlabs_voices, list) and preloaded_elevenlabs_voices:
            self.elevenlabs_voices = list(preloaded_elevenlabs_voices)
            self.elevenlabs_voices_loaded = True
            self._voices_need_update = True

        self.create_interface()
        self.populate_fields()

        if not self.elevenlabs_voices_loaded:
            self.after(500, self.load_elevenlabs_voices)

        self.check_voices_update()

        # Activer les boutons de lecture après un court délai pour éviter les race conditions
        self.after(500, self._enable_play_buttons)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.deiconify()

    def _enable_play_buttons(self):
        """Active tous les boutons de lecture dans les guides vocaux."""
        for button in self.guide_play_buttons:
            if button and button.winfo_exists():
                button.configure(state="normal")

    def check_voices_update(self):
        if self._voices_need_update and self.elevenlabs_voices_loaded:
            self._voices_need_update = False
            self.update_elevenlabs_comboboxes()
        self.after(200, self.check_voices_update)

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
                self._populate_guide_tab(gemini_tab, "gemini")

            if self.elevenlabs_api_configured:
                elevenlabs_tab = notebook.add("ElevenLabs Voices")
                self._populate_guide_tab(elevenlabs_tab, "elevenlabs")

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

    def _populate_guide_tab(self, tab, provider):
        scrollable_frame = customtkinter.CTkScrollableFrame(tab, label_text="")
        scrollable_frame.pack(fill="both", expand=True)

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
                    self._create_guide_row(scrollable_frame, provider, voice['id'], voice['display_name'],
                                           voice['preview_url'])
                    if i < len(voices) - 1:
                        separator = customtkinter.CTkFrame(scrollable_frame, height=1, fg_color=("gray80", "gray25"))
                        separator.pack(fill='x', pady=5, padx=5)
            else:
                customtkinter.CTkLabel(scrollable_frame, text="Loading ElevenLabs voices...").pack(pady=20)

    def _create_guide_row(self, parent, provider, voice_id, display_name, play_identifier):
        row_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill=tk.X, pady=2)
        row_frame.columnconfigure(0, weight=1)

        text_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        name, _, description = display_name.partition(" - ")
        customtkinter.CTkLabel(text_frame, text=name, font=customtkinter.CTkFont(weight="bold"),
                               anchor="w").pack(anchor="w", fill="x")
        if description:
            customtkinter.CTkLabel(text_frame, text=description, anchor="w", wraplength=400,
                                   font=customtkinter.CTkFont(size=11)).pack(anchor="w", fill="x")

        buttons_inner = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        buttons_inner.grid(row=0, column=1, sticky="e")

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
                voice_id = next((v['id'] for v in self.elevenlabs_voices if v['display_name'] == display), "")
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
        # Force the window to recalculate its size
        self.update_idletasks()

    def remove_row(self, row_frame):
        entry_to_remove = next((e for e in self.entries if e['frame'] == row_frame), None)
        if entry_to_remove:
            row_frame.destroy()
            self.entries.remove(entry_to_remove)
            self.update_idletasks()

    def restore_defaults(self):
        for row in self.entries: row['frame'].destroy()
        self.entries.clear()
        self.current_settings = dict(self.default_settings)
        self.populate_fields()