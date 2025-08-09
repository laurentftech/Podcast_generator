import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import threading
import os
import sys
import queue
import json

try:
    from playsound import playsound
except ImportError:
    playsound = None # Gère l'absence de la bibliothèque

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


class PodcastGeneratorApp:
    SETTINGS_FILE = "settings.json"
    DEFAULT_SPEAKER_SETTINGS = {"John": "Schedar", "Samantha": "Zephyr"}

    def __init__(self, root: tk.Tk, generate_func, default_script: str = ""):
        self.root = root
        self.root.title("Générateur de Podcast")
        self.root.geometry("800x600")
        self.generate_func = generate_func
        self.log_queue = queue.Queue()
        self.GENERATION_COMPLETE = object()  # Sentinel pour marquer la fin
        self.last_generated_filepath = None
        
        self.speaker_settings = self.load_settings()

        # --- Barre de menu ---
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        options_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Paramètres des voix...", command=self.open_settings_window)
        options_menu.add_separator()
        options_menu.add_command(label="Quitter", command=self.root.quit)

        # Menu Aide
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos...", command=self.show_about_window)

        self.poll_log_queue()

        # --- Cadre principal ---
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Zone de texte pour le script ---
        script_frame = tk.LabelFrame(main_frame, text="Script à lire", padx=5, pady=5)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.script_text = scrolledtext.ScrolledText(script_frame, wrap=tk.WORD, height=15, width=80)
        self.script_text.pack(fill=tk.BOTH, expand=True)
        self.script_text.insert(tk.END, default_script)

        # --- Zone pour les logs/status ---
        log_frame = tk.LabelFrame(main_frame, text="Status de la génération", padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- Barre de progression (initialement cachée) ---
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')

        # --- Cadre pour les boutons ---
        self.button_frame = tk.Frame(main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))

        # Définir une largeur commune pour l'uniformité visuelle
        common_button_width = 26

        self.load_button = tk.Button(self.button_frame, text="Charger un script (.txt)", command=self.load_script_from_file, width=common_button_width)
        self.load_button.pack(side=tk.LEFT, padx=(0, 10))

        self.generate_button = tk.Button(self.button_frame, text="Lancer la génération", command=self.start_generation_thread, width=common_button_width)
        self.generate_button.pack(side=tk.LEFT)

        self.play_button = tk.Button(self.button_frame, text="▶️ Lire", command=self.play_last_generated_file, state='disabled', width=common_button_width)
        self.play_button.pack(side=tk.LEFT, padx=(10, 0))

    def load_settings(self):
        """Charge les paramètres depuis le fichier JSON."""
        try:
            with open(self.SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # On vérifie que la clé existe, sinon on retourne les défauts
                return settings.get("speaker_voices", self.DEFAULT_SPEAKER_SETTINGS.copy())
        except (FileNotFoundError, json.JSONDecodeError):
            # Retourne une copie des valeurs par défaut si le fichier n'existe pas ou est corrompu
            return self.DEFAULT_SPEAKER_SETTINGS.copy()

    def save_settings(self, settings_to_save):
        """Sauvegarde les paramètres dans le fichier JSON."""
        self.speaker_settings = settings_to_save
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump({"speaker_voices": settings_to_save}, f, indent=4)
            self.log_status("Paramètres des voix sauvegardés.")
        except IOError as e:
            messagebox.showerror("Erreur de sauvegarde", f"Impossible de sauvegarder les paramètres:\n{e}")

    def open_settings_window(self):
        """Ouvre la fenêtre de gestion des paramètres."""
        # On désactive le bouton pendant que la fenêtre est ouverte pour éviter les doublons
        self.menubar.entryconfig("Options", state="disabled")
        SettingsWindow(self.root, self.speaker_settings, self.save_settings, self.on_settings_window_close, self.DEFAULT_SPEAKER_SETTINGS)

    def show_about_window(self):
        """Affiche la fenêtre 'À propos'."""
        about_title = "À propos de Générateur de Podcast"
        about_message = (
            "Générateur de Podcast v1.0\n\n"
            "Copyright (c) 2025 Laurent FRANCOISE\n\n"
            "Licence : MIT License\n\n"
            "Crédits :\n"
            " - Google Gemini API pour la génération audio\n"
            " - Tkinter pour l'interface graphique\n"
            " - playsound pour la lecture audio"
        )
        messagebox.showinfo(about_title, about_message, parent=self.root)

    def log_status(self, message: str):
        self.log_queue.put(message)

    def poll_log_queue(self):
        # On ne traite qu'un seul message à la fois pour ne pas bloquer la boucle d'événements.
        # Cela garantit que l'interface reste réactive et peut traiter d'autres tâches
        # (comme on_generation_complete) entre deux affichages de log.
        try:
            message = self.log_queue.get_nowait()
            if isinstance(message, tuple) and message[0] is self.GENERATION_COMPLETE:
                was_successful = message[1]
                self.on_generation_complete(success=was_successful)
            else:
                self._update_log(message)
        except queue.Empty:
            pass  # La file est vide, on ne fait rien
        self.root.after(100, self.poll_log_queue)  # Vérifie la queue toutes les 100 ms

    def _update_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        """Vide la zone de texte des logs."""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

    def load_script_from_file(self):
        """Ouvre une boîte de dialogue pour charger un fichier .txt dans la zone de script."""
        filepath = filedialog.askopenfilename(
            title="Ouvrir un fichier script",
            filetypes=(("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*"))
        )
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.script_text.delete('1.0', tk.END)
                self.script_text.insert('1.0', f.read())
            self.log_status(f"Script chargé depuis : {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible de lire le fichier :\n{e}")

    def start_generation_thread(self):
        """Lance la génération dans un thread séparé pour ne pas geler l'interface."""
        script_content = self.script_text.get("1.0", tk.END).strip()
        if not script_content:
            messagebox.showwarning("Script vide", "Veuillez entrer ou charger un script avant de lancer la génération.")
            return

        # Demander à l'utilisateur où enregistrer le fichier de sortie
        output_filepath = filedialog.asksaveasfilename(
            title="Enregistrer le podcast sous...",
            defaultextension=".wav",
            filetypes=(("Fichiers Audio WAV", "*.wav"), ("Tous les fichiers", "*.*"))
        )

        if not output_filepath:
            self.log_status("Génération annulée par l'utilisateur.")
            return

        # Extraire le répertoire et le nom de base du fichier
        output_dir = os.path.dirname(output_filepath)
        output_basename = os.path.splitext(os.path.basename(output_filepath))[0]

        # Désactiver les boutons pendant la génération
        self.generate_button.config(state='disabled')
        self.load_button.config(state='disabled')
        self.play_button.config(state='disabled')
        self.menubar.entryconfig("Options", state="disabled")

        # Afficher et démarrer la barre de progression
        self.clear_log()
        # On active la zone de log pour pouvoir y écrire pendant la génération
        self.log_text.config(state='normal')

        self.progress_bar.pack(fill=tk.X, pady=(10, 0), before=self.button_frame)
        self.progress_bar.start()

        thread = threading.Thread(target=self.run_generation, args=(script_content, output_basename, output_dir, self.speaker_settings))
        thread.daemon = True
        thread.start()

    def run_generation(self, script_content, output_basename, output_dir, speaker_mapping):
        """La fonction exécutée par le thread."""
        generated_filepath = None
        try:
            self.log_status(f"Lancement de la génération vers '{os.path.basename(output_dir)}'...")
            generated_filepath = self.generate_func(
                script_text=script_content,
                speaker_mapping=speaker_mapping,
                output_basename=output_basename,
                output_dir=output_dir,
                status_callback=self.log_status
            )
            if generated_filepath:
                self.last_generated_filepath = generated_filepath
                self.log_status(f"\n--- Génération terminée avec succès ! Fichier : {os.path.basename(generated_filepath)} ---")
            else:
                self.log_status("\n--- La génération a échoué. Veuillez vérifier les logs. ---")
        except Exception as e:
            self.log_status(f"Une erreur critique est survenue : {e}")
            generated_filepath = None # S'assurer que le statut est bien 'échec'
        finally:
            # On utilise la queue, notre canal de communication fiable,
            # pour signaler la fin de la génération et son statut (succès/échec).
            success = bool(generated_filepath)
            self.log_queue.put((self.GENERATION_COMPLETE, success))

    def on_generation_complete(self, success: bool):
        if success:
            self.root.bell()
            if playsound:
                self.play_button.config(state='normal')

        self.progress_bar.stop()
        self.generate_button.config(state='normal')
        self.load_button.config(state='normal')
        self.menubar.entryconfig("Options", state="normal")
        if self.progress_bar.winfo_ismapped():
            self.progress_bar.pack_forget()
        self.log_text.config(state='disabled') # On désactive la zone de log à la toute fin

    def play_last_generated_file(self):
        """Joue le dernier fichier audio généré dans un thread séparé."""
        if not playsound:
            messagebox.showerror(
                "Dépendance manquante",
                "La bibliothèque 'playsound' est requise pour lire l'audio.\n\n"
                "Veuillez l'installer avec : pip install playsound"
            )
            return

        if not self.last_generated_filepath or not os.path.exists(self.last_generated_filepath):
            messagebox.showerror("Fichier introuvable", "Le fichier audio généré n'a pas été trouvé ou n'est plus accessible.")
            return

        def _play_in_thread():
            try:
                self.play_button.config(state='disabled')
                playsound(self.last_generated_filepath)
            except Exception as e:
                self.log_status(f"Erreur de lecture audio : {e}")
                messagebox.showerror("Erreur de lecture", f"Impossible de lire le fichier audio.\n{e}")
            finally:
                if self.root.winfo_exists():
                    self.play_button.config(state='normal')

        threading.Thread(target=_play_in_thread, daemon=True).start()

    def on_settings_window_close(self):
        """Callback pour réactiver le menu lorsque la fenêtre des paramètres est fermée."""
        self.menubar.entryconfig("Options", state="normal")

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings):
        super().__init__(parent)
        self.title("Paramètres des voix")
        self.transient(parent)
        self.grab_set()

        self.default_settings = default_settings
        self.current_settings = dict(current_settings) # Crée une copie
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.cancel_and_close) # Gère la fermeture avec la croix
        self.voice_display_list = [f"{name} - {desc}" for name, desc in AVAILABLE_VOICES.items()]
        self.entries = []

        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(header_frame, text="Nom du Speaker (dans le script)", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT, expand=True)
        tk.Label(header_frame, text="Nom de la Voix (Gemini)", font=('Helvetica', 10, 'bold')).pack(side=tk.RIGHT, expand=True)

        self.speaker_frame = tk.Frame(main_frame)
        self.speaker_frame.pack(fill=tk.BOTH, expand=True)

        self.populate_fields()

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(button_frame, text="+", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Sauvegarder", command=self.save_and_close).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Annuler", command=self.cancel_and_close).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Restaurer les défauts", command=self.restore_defaults).pack(side=tk.LEFT, padx=(10, 0))

    def populate_fields(self):
        for speaker, voice in self.current_settings.items():
            self.add_row(speaker, voice)

    def add_row(self, speaker_text="", voice_text=""):
        """Ajoute une ligne complète pour un speaker avec une liste déroulante pour la voix."""
        row_container = tk.Frame(self.speaker_frame)
        row_container.pack(fill=tk.X, pady=2)

        speaker_entry = tk.Entry(row_container)
        speaker_entry.insert(0, speaker_text)

        voice_combo = ttk.Combobox(row_container, values=self.voice_display_list)
        # Retrouve la chaîne complète à afficher, ou utilise la valeur brute si c'est une voix personnalisée
        initial_display_value = voice_text
        if voice_text in AVAILABLE_VOICES:
            initial_display_value = f"{voice_text} - {AVAILABLE_VOICES[voice_text]}"
        voice_combo.insert(0, initial_display_value)
        
        entry_tuple = (speaker_entry, voice_combo)
        delete_button = tk.Button(row_container, text="-", width=2, command=lambda: self.delete_row(row_container, entry_tuple))

        # Layout avec grid pour un meilleur alignement
        row_container.columnconfigure(0, weight=1)
        row_container.columnconfigure(1, weight=1)
        row_container.columnconfigure(2, weight=0)

        speaker_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        voice_combo.grid(row=0, column=1, sticky="ew")
        delete_button.grid(row=0, column=2, sticky="w", padx=(5, 0))

        self.entries.append(entry_tuple)

    def delete_row(self, row_container, entry_tuple):
        """Supprime une ligne de speaker de l'interface et de la liste."""
        row_container.destroy()
        self.entries.remove(entry_tuple)

    def restore_defaults(self):
        """Efface les champs actuels et les remplit avec les paramètres par défaut."""
        # Vide l'interface et la liste interne
        for widget in self.speaker_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        # Remplit avec les valeurs par défaut
        self.populate_fields()

    def save_and_close(self):
        new_settings = {}
        for speaker_entry, voice_combo in self.entries:
            speaker = speaker_entry.get().strip()
            full_voice_string = voice_combo.get().strip()
            if speaker and full_voice_string:
                # Extrait seulement le nom de la voix (avant le " - ")
                voice_name = full_voice_string.split(' - ')[0]
                new_settings[speaker] = voice_name

        self.save_callback(new_settings)
        self.close_callback()
        self.destroy()

    def cancel_and_close(self):
        self.close_callback()
        self.destroy()

def main():
    """Initialise l'application et lance la boucle principale de Tkinter."""
    # Crée la fenêtre racine mais la cache pour l'instant.
    # Cela permet d'afficher des boîtes de dialogue d'erreur de manière fiable
    # même si l'initialisation complète de l'interface échoue.
    root = tk.Tk()
    root.withdraw()

    # --- Correction du chemin d'importation ---
    # S'assure que le script peut trouver 'generate_podcast.py'
    # peu importe d'où il est exécuté.
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
    except NameError:
        # __file__ n'est pas défini dans certains environnements interactifs
        pass

    # --- Importation des dépendances ---
    try:
        from generate_podcast import generate, PODCAST_SCRIPT
    except ImportError as e:
        messagebox.showerror(
            "Erreur d'importation",
            f"Le fichier 'generate_podcast.py' est introuvable.\n\n"
            f"Veuillez vous assurer qu'il se trouve dans le même dossier que gui.py.\n\n"
            f"Détail de l'erreur : {e}"
        )
        root.destroy()
        return
    
    # Si tout est correct, on construit l'interface et on affiche la fenêtre
    app = PodcastGeneratorApp(root, generate_func=generate, default_script=PODCAST_SCRIPT)
    root.deiconify()
    root.mainloop()

if __name__ == "__main__":
    main()