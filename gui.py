import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import threading
import os
import sys
import queue

class PodcastGeneratorApp:
    def __init__(self, root: tk.Tk, generate_func, default_script: str = ""):
        self.root = root
        self.root.title("Générateur de Podcast")
        self.root.geometry("800x600")
        self.generate_func = generate_func
        self.log_queue = queue.Queue()
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

        self.load_button = tk.Button(self.button_frame, text="Charger un script (.txt)", command=self.load_script_from_file)
        self.load_button.pack(side=tk.LEFT, padx=(0, 10))

        self.generate_button = tk.Button(self.button_frame, text="Lancer la génération", command=self.start_generation_thread)
        self.generate_button.pack(side=tk.LEFT)

        # Ajoutez ceci à la fin de __init__ dans PodcastGeneratorApp
        self.log_status("Test log depuis le thread principal")

    def log_status(self, message: str):
        self.log_queue.put(message)

    def poll_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self._update_log(message)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log_queue)  # Vérifie la queue toutes les 100 ms

    def _update_log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

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

        # Afficher et démarrer la barre de progression
        self.clear_log()

        self.progress_bar.pack(fill=tk.X, pady=(10, 0), before=self.button_frame)
        self.progress_bar.start()

        thread = threading.Thread(target=self.run_generation, args=(script_content, output_basename, output_dir))
        thread.daemon = True
        thread.start()

    def run_generation(self, script_content, output_basename, output_dir):
        """La fonction exécutée par le thread."""
        try:
            self.log_status(f"Lancement de la génération vers '{os.path.basename(output_dir)}'...")
            success = self.generate_func(
                script_text=script_content,
                output_basename=output_basename,
                output_dir=output_dir,
                status_callback=self.log_status
            )
            if success:
                self.log_status("\n--- Génération terminée avec succès ! ---")
            else:
                self.log_status("\n--- La génération a échoué. Veuillez vérifier les logs. ---")
        except Exception as e:
            self.log_status(f"Une erreur critique est survenue : {e}")
        finally:
            # Arrêter la progression et réactiver les boutons via le thread principal
            self.root.after(0, self.on_generation_complete)

    def on_generation_complete(self):
        self.log_status("Fin de la génération (callback on_generation_complete appelé).")
        print("DEBUG: on_generation_complete appelée")  # Console
        self.progress_bar.stop()
        print("DEBUG: progress_bar.stop() appelée")  # Console
        if self.progress_bar.winfo_ismapped():
            self.progress_bar.pack_forget()
        self.log_text.config(state='disabled')
        self.generate_button.config(state='normal')
        self.load_button.config(state='normal')

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