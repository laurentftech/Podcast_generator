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

    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings):
        super().__init__(parent)
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

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

        # Créer l'interface d'abord
        self.create_interface()

        # FORCER le chargement immédiat des paramètres existants
        print("Chargement immédiat des paramètres existants...")
        self.populate_fields()

        # Puis charger les voix ElevenLabs en arrière-plan après un délai
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

        # Provider selection
        provider_frame = tk.Frame(main_frame)
        provider_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(provider_frame, text="TTS Provider:", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        self.provider_var = tk.StringVar(value=self.current_settings.get("tts_provider", "gemini"))
        provider_combo = ttk.Combobox(provider_frame, textvariable=self.provider_var,
                                      values=["gemini", "elevenlabs"], width=15, state="readonly")
        provider_combo.pack(side=tk.LEFT, padx=(10, 0))

        # Headers
        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(header_frame, text="Speaker name (in the script)",
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="w")
        tk.Label(header_frame, text="Voice (Gemini)",
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky="w", padx=(10, 0))

        # ElevenLabs header avec bouton de rechargement
        el_header_frame = tk.Frame(header_frame)
        el_header_frame.grid(row=0, column=2, sticky="w", padx=(10, 0))
        tk.Label(el_header_frame, text="Voice (ElevenLabs)",
                 font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT)
        self.refresh_voices_btn = tk.Button(el_header_frame, text="🔄", width=3, font=('Arial', 8),
                                            command=self.load_elevenlabs_voices,
                                            relief=tk.FLAT, bg="lightgray")
        self.refresh_voices_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Configure grid weights for headers
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(2, weight=1)

        self.speaker_frame = tk.Frame(main_frame)
        self.speaker_frame.pack(fill=tk.BOTH, expand=True)

        # NE PAS populate_fields() maintenant - attendre que les voix se chargent
        # self.populate_fields()

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(button_frame, text="+", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Save", command=self.save_and_close).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Cancel", command=self.cancel_and_close).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Restore Defaults", command=self.restore_defaults).pack(side=tk.LEFT, padx=(10, 0))

    def safe_update_button(self, state, text):
        """Met à jour le bouton de manière sécurisée."""
        try:
            # Vérifications plus robustes
            if (hasattr(self, 'refresh_voices_btn') and 
                self.refresh_voices_btn is not None):
                
                # Vérifier que les widgets existent vraiment
                try:
                    # Test simple pour voir si le widget est encore valide
                    self.refresh_voices_btn.winfo_class()
                    self.refresh_voices_btn.config(state=state, text=text)
                except tk.TclError:
                    # Le widget a été détruit
                    pass
        except (tk.TclError, AttributeError, TypeError) as e:
            # Ignorer toutes les erreurs liées à Tkinter
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
                # Vérifier que la fenêtre existe encore de manière plus simple
                try:
                    self.winfo_class()  # Test simple d'existence
                except tk.TclError:
                    print("Fenêtre détruite, abandon")
                    return

                # Désactiver temporairement le bouton
                self.after(0, lambda: self.safe_update_button('disabled', '⏳'))

                api_key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
                if not api_key:
                    self.elevenlabs_voices = []
                    self.elevenlabs_voices_loaded = False
                    print("Aucune clé API ElevenLabs configurée")
                    # Charger les champs même sans voix ElevenLabs
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

                        # Extraction sécurisée des labels
                        accent = labels.get('accent', '') if isinstance(labels, dict) else ''
                        age = labels.get('age', '') if isinstance(labels, dict) else ''
                        gender = labels.get('gender', '') if isinstance(labels, dict) else ''

                        # Construire une description
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

                    # Trier par nom
                    voices.sort(key=lambda x: x.get('name', ''))
                    self.elevenlabs_voices = voices
                    self.elevenlabs_voices_loaded = True
                    
                    print(f"Chargé {len(voices)} voix ElevenLabs avec succès")

                    # Activer le flag pour que check_voices_update() détecte la mise à jour
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

        # Lancer dans un thread pour ne pas bloquer l'interface
        print("Lancement du thread de chargement...")
        thread = threading.Thread(target=fetch_voices, daemon=True)
        thread.start()

    def populate_fields_delayed(self):
        """Populate les champs après que les voix ElevenLabs aient été chargées (ou échoué)."""
        print(f"=== DEBUG populate_fields_delayed ===")
        print(f"self.entries avant: {len(self.entries)} entrées")
        print(f"Contenu de self.entries: {[row.get('speaker', 'NO_SPEAKER') for row in self.entries]}")
        
        # TOUJOURS populate, pas seulement si vide
        self.populate_fields()

    def update_elevenlabs_comboboxes(self):
        """Met à jour toutes les comboboxes ElevenLabs avec les nouvelles voix chargées."""
        try:
            if not self.elevenlabs_voices_loaded or not self.elevenlabs_voices:
                return
            
            # Vérifier que la fenêtre existe encore
            self.winfo_class()
            
            print(f"Mise à jour des comboboxes avec {len(self.elevenlabs_voices)} voix")
            
            # Créer la liste des noms d'affichage pour les comboboxes
            elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]
            
            # Mettre à jour toutes les comboboxes ElevenLabs existantes
            for row in self.entries:
                if 'elevenlabs_voice' in row and row['elevenlabs_voice']:
                    try:
                        # Sauvegarder la valeur actuelle
                        current_value = row['elevenlabs_voice'].get()
                        
                        # Mettre à jour les valeurs disponibles
                        row['elevenlabs_voice']['values'] = elevenlabs_values
                        
                        # Restaurer la valeur si elle existe toujours, sinon la laisser vide
                        if current_value in elevenlabs_values:
                            row['elevenlabs_voice'].set(current_value)
                        
                    except tk.TclError:
                        # La combobox a été détruite, ignorer
                        continue
            
            print("Mise à jour des comboboxes terminée avec succès")
            
        except (tk.TclError, AttributeError):
            # La fenêtre a été fermée
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
        
        # Récupérer les valeurs des champs
        speaker_voices = {}
        speaker_voices_elevenlabs = {}
        
        for row in self.entries:
            speaker_name = row['speaker'].get().strip()
            gemini_voice = row['gemini_voice'].get()
            elevenlabs_voice_display = row['elevenlabs_voice'].get()
            
            # Convertir le nom d'affichage ElevenLabs en ID
            elevenlabs_voice_id = ""
            if elevenlabs_voice_display and self.elevenlabs_voices:
                for voice in self.elevenlabs_voices:
                    if voice['display_name'] == elevenlabs_voice_display:
                        elevenlabs_voice_id = voice['id']
                        break
            
            print(f"Row: speaker='{speaker_name}', gemini='{gemini_voice}', elevenlabs_display='{elevenlabs_voice_display}', elevenlabs_id='{elevenlabs_voice_id}'")
            
            if speaker_name:
                speaker_voices[speaker_name] = gemini_voice
                # Sauvegarder LES DEUX : ID et nom d'affichage
                speaker_voices_elevenlabs[speaker_name] = {
                    'id': elevenlabs_voice_id,
                    'display_name': elevenlabs_voice_display
                }
        
        print(f"speaker_voices: {speaker_voices}")
        print(f"speaker_voices_elevenlabs: {speaker_voices_elevenlabs}")
        
        # Construire les nouveaux paramètres dans le format attendu par gui.py
        new_settings = {
            'tts_provider': self.provider_var.get(),
            'speaker_voices': speaker_voices,
            'speaker_voices_elevenlabs': speaker_voices_elevenlabs
        }
        
        print(f"new_settings à sauvegarder: {new_settings}")
        
        # Sauvegarder via le callback
        if self.save_callback:
            self.save_callback(new_settings)
        
        # Fermer la fenêtre
        if self.close_callback:
            self.close_callback()
        self.destroy()

    def populate_fields(self):
        """Remplit les champs avec les paramètres actuels."""
        print("=== DEBUG populate_fields ===")
        print(f"current_settings reçu: {self.current_settings}")
        
        # Supporter les deux formats pour la rétrocompatibilité
        speaker_voices = self.current_settings.get('speaker_voices', {})
        speaker_voices_elevenlabs = self.current_settings.get('speaker_voices_elevenlabs', {})
        
        print(f"speaker_voices: {speaker_voices}")
        print(f"speaker_voices_elevenlabs: {speaker_voices_elevenlabs}")
        
        # Format nouveau (si present)
        voice_settings = self.current_settings.get('voice_settings', {})
        print(f"voice_settings: {voice_settings}")
        
        # Si on a le nouveau format, l'utiliser
        if voice_settings:
            print("Utilisation du nouveau format voice_settings")
            for speaker_name, voices in voice_settings.items():
                print(f"Ajout ligne: {speaker_name} -> {voices}")
                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=voices.get('gemini_voice', ''),
                    elevenlabs_voice=voices.get('elevenlabs_voice', '')
                )
        # Sinon utiliser l'ancien format
        elif speaker_voices:
            print("Utilisation de l'ancien format speaker_voices")
            # Obtenir tous les speakers uniques des deux dictionnaires
            all_speakers = set(speaker_voices.keys()) | set(speaker_voices_elevenlabs.keys())
            print(f"All speakers: {all_speakers}")
            
            for speaker_name in all_speakers:
                gemini_voice = speaker_voices.get(speaker_name, '')
                elevenlabs_data = speaker_voices_elevenlabs.get(speaker_name, '')
                
                # Gérer les deux formats : ancien (string) et nouveau (dict)
                elevenlabs_voice_display = ""
                
                if isinstance(elevenlabs_data, dict):
                    # Nouveau format avec ID et display_name
                    elevenlabs_voice_display = elevenlabs_data.get('display_name', '')
                elif isinstance(elevenlabs_data, str):
                    # Ancien format : soit ID seul, soit display_name seul
                    if ' - ' in elevenlabs_data:
                        # Ressemble à un display_name
                        elevenlabs_voice_display = elevenlabs_data
                    else:
                        # Ressemble à un ID - essayer de trouver le display_name
                        if self.elevenlabs_voices:
                            for voice in self.elevenlabs_voices:
                                if voice['id'] == elevenlabs_data:
                                    elevenlabs_voice_display = voice['display_name']
                                    break
                
                print(f"Ajout ligne: {speaker_name} -> gemini='{gemini_voice}', elevenlabs_display='{elevenlabs_voice_display}'")
                self.add_row(
                    speaker_name=speaker_name,
                    gemini_voice=gemini_voice,
                    elevenlabs_voice=elevenlabs_voice_display
                )
        else:
            print("Aucun paramètre trouvé, ajout d'une ligne vide")
            # Si aucun paramètre, ajouter une ligne vide
            self.add_row()
    def add_row(self, speaker_name='', gemini_voice='', elevenlabs_voice=''):
        """Ajoute une nouvelle ligne de paramètres."""
        row_frame = tk.Frame(self.speaker_frame)
        row_frame.pack(fill=tk.X, pady=2)
        
        # Champ nom du speaker
        speaker_entry = tk.Entry(row_frame, width=25)
        speaker_entry.pack(side=tk.LEFT, padx=(0, 10))
        speaker_entry.insert(0, speaker_name)
        
        # Combobox voix Gemini
        gemini_combo = ttk.Combobox(row_frame, values=self.VOICE_DISPLAY_LIST,
                                   width=25, state="readonly")
        gemini_combo.pack(side=tk.LEFT, padx=(0, 10))
        if gemini_voice:
            gemini_combo.set(gemini_voice)
        
        # Combobox voix ElevenLabs
        elevenlabs_values = []
        if self.elevenlabs_voices_loaded and self.elevenlabs_voices:
            elevenlabs_values = [voice['display_name'] for voice in self.elevenlabs_voices]
        
        elevenlabs_combo = ttk.Combobox(row_frame, values=elevenlabs_values,
                                       width=25, state="readonly")
        elevenlabs_combo.pack(side=tk.LEFT, padx=(0, 10))
        if elevenlabs_voice:
            elevenlabs_combo.set(elevenlabs_voice)
        
        # Bouton supprimer
        remove_btn = tk.Button(row_frame, text="-", width=3,
                              command=lambda r=row_frame: self.remove_row(r))
        remove_btn.pack(side=tk.LEFT)
        
        # Stocker les références
        row_data = {
            'frame': row_frame,
            'speaker': speaker_entry,
            'gemini_voice': gemini_combo,
            'elevenlabs_voice': elevenlabs_combo,
            'remove_btn': remove_btn
        }
        self.entries.append(row_data)

    def remove_row(self, row_frame):
        """Supprime une ligne de paramètres."""
        # Trouver et supprimer l'entrée correspondante
        for i, row in enumerate(self.entries):
            if row['frame'] == row_frame:
                row_frame.destroy()
                del self.entries[i]
                break

    def restore_defaults(self):
        """Restaure les paramètres par défaut."""
        # Vider tous les champs existants
        for row in self.entries:
            row['frame'].destroy()
        self.entries.clear()
        
        # Restaurer les paramètres par défaut
        self.current_settings = dict(self.default_settings)
        self.provider_var.set(self.current_settings.get("tts_provider", "gemini"))
        self.populate_fields()