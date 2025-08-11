import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import threading
import os
import subprocess
import sys
import queue
import json
from importlib import metadata
import webbrowser
from datetime import datetime

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

def get_app_version() -> str:
    """Gets the application version from the package metadata."""
    try:
        # Works when the package is installed (even in editable mode)
        return metadata.version("Podcast_generator")
    except metadata.PackageNotFoundError:
        # Fallback if the script is run without being installed
        return "0.0.0-dev"

def get_asset_path(filename: str) -> str | None:
    """
    Gets the absolute path to an asset, handling running from source and from
    a PyInstaller bundle.
    """
    if getattr(sys, 'frozen', False):
        # The application is frozen (packaged with PyInstaller)
        bundle_dir = sys._MEIPASS
    else:
        # The application is running in a normal Python environment
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    
    path = os.path.join(bundle_dir, filename)
    return path if os.path.exists(path) else None

class PodcastGeneratorApp:
    DEFAULT_SPEAKER_SETTINGS = {"John": "Schedar", "Samantha": "Zephyr"}

    def __init__(self, root: tk.Tk, generate_func, logger, api_key: str, default_script: str = ""):
        self.root = root
        self.root.title(f"Podcast Generator v{get_app_version()}")
        self.root.geometry("960x700")

        # --- Application Icon ---
        icon_path = get_asset_path("podcast.png")
        if icon_path:
            try:
                img = tk.PhotoImage(file=icon_path)
                self.root.tk.call('wm', 'iconphoto', self.root._w, img)
            except tk.TclError:
                # In case of format error, continue without icon
                pass

        # --- Define configuration paths ---
        from generate_podcast import get_app_data_dir, find_ffplay_path # Local import
        self.app_data_dir = get_app_data_dir()
        self.settings_filepath = os.path.join(self.app_data_dir, "settings.json")

        self.generate_func = generate_func
        self.logger = logger
        self.api_key = api_key
        self.log_queue = queue.Queue()
        self.playback_obj = None # To keep a reference to the playback process
        self.last_generated_filepath = None
        self.ffplay_path = find_ffplay_path()
        
        self.speaker_settings = self.load_settings()

        # --- Menu Bar ---
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        options_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Voice settings...", command=self.open_settings_window)
        options_menu.add_separator()
        options_menu.add_command(label="Quit Podcast Generator", command=self.root.quit)

        # Help Menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation (Github)...", command=self.open_documentation)
        help_menu.add_command(label="About...", command=self.show_about_window)
        self.logger.info("Main interface initialized.")

        self.poll_log_queue()

        # --- Main Frame ---
        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Script Text Area ---
        script_frame = tk.LabelFrame(main_frame, text="Script to read", padx=5, pady=5)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.script_text = scrolledtext.ScrolledText(script_frame, wrap=tk.WORD, height=15, width=80)
        self.script_text.pack(fill=tk.BOTH, expand=True)
        self.script_text.insert(tk.END, default_script)

        # --- Log/Status Area ---
        log_frame = tk.LabelFrame(main_frame, text="Generation status", padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- Progress Bar (initially hidden) ---
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')

        # --- Button Frame ---
        self.button_frame = tk.Frame(main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))

        # Define a common width for visual consistency
        common_button_width = 22

        # --- Left-aligned buttons ---
        self.load_button = tk.Button(self.button_frame, text="Load a script (.txt)", command=self.load_script_from_file, width=common_button_width)
        self.load_button.pack(side=tk.LEFT, padx=(0, 5))

        self.generate_button = tk.Button(self.button_frame, text="Start generation", command=self.start_generation_thread, width=common_button_width)
        self.generate_button.pack(side=tk.LEFT)

        # --- Right-aligned buttons (packed in reverse order for correct display) ---
        self.show_button = tk.Button(self.button_frame, text="Open file location", command=self.open_file_location, state='disabled', width=common_button_width)
        self.show_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.play_button = tk.Button(self.button_frame, text="▶️ Play", command=self.play_last_generated_file, state='disabled', width=common_button_width)
        self.play_button.pack(side=tk.RIGHT)


    def load_settings(self):
        """Loads settings from the JSON file."""
        try:
            with open(self.settings_filepath, 'r') as f:
                settings = json.load(f)
                # Check
                return settings.get("speaker_voices", self.DEFAULT_SPEAKER_SETTINGS.copy())
        except (FileNotFoundError, json.JSONDecodeError):
            # Returns a copy of the default values if the file does not exist or is corrupt
            return self.DEFAULT_SPEAKER_SETTINGS.copy()

    def save_settings(self, settings_to_save):
        """Saves the settings to the JSON file."""
        self.speaker_settings = settings_to_save
        try:
            os.makedirs(self.app_data_dir, exist_ok=True) # Ensures the directory exists
            with open(self.settings_filepath, 'w') as f:
                json.dump({"speaker_voices": settings_to_save}, f, indent=4)
            self.log_status("Voice settings saved successfully.")
        except IOError as e:
            messagebox.showerror("Saving Error", f"Cannot save settings to file:\n{e}")
            self.logger.error(f"Saving error for settings: {e}")

    def open_settings_window(self):
        """Opens the settings management window."""
        # Disable the button while the window is open to avoid duplicates
        self.menubar.entryconfig("Options", state="disabled")
        SettingsWindow(self.root, self.speaker_settings, self.save_settings, self.on_settings_window_close, self.DEFAULT_SPEAKER_SETTINGS)

    def show_about_window(self):
        """Displays the 'About' window."""
        AboutWindow(self.root)
        
    def open_documentation(self):
        """Opens the link to the documentation or the repository."""
        webbrowser.open_new_tab("https://github.com/laurentftech/Podcast_generator")

    def log_status(self, message: str):
        self.log_queue.put(message)

    def poll_log_queue(self):
        # We only process one message at a time to avoid blocking the event loop.
        # This ensures the interface remains responsive and can handle other tasks
        # (like on_generation_complete) between log displays.
        try:
            message = self.log_queue.get_nowait()
            if isinstance(message, tuple):
                msg_type = message[0]
                if msg_type == 'GENERATION_COMPLETE':
                    self.on_generation_complete(success=message[1])
                elif msg_type == 'UPDATE_PLAY_BUTTON':
                    self.play_button.config(text=message[1], state=message[2])
            else:
                self._update_log(message)
        except queue.Empty:
            pass  # The queue is empty, do nothing
        self.root.after(100, self.poll_log_queue)  # Check the queue every 100 ms

    def _update_log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clear_log(self):
        """Clears the log text area."""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

    def load_script_from_file(self):
        """Opens a dialog to load a .txt file into the script area."""
        filepath = filedialog.askopenfilename(
            title="Open a script file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.script_text.delete('1.0', tk.END)
                self.script_text.insert('1.0', f.read())
            self.log_status(f"Script loaded from: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Reading error", f"Cannot read the file:\n{e}")
            self.logger.error(f"Error reading the script: {e}")

    def start_generation_thread(self):
        """Starts the generation in a separate thread to avoid freezing the UI."""
        script_content = self.script_text.get("1.0", tk.END).strip()
        if not script_content:
            messagebox.showwarning("Empty script", "Please enter or load a script before starting generation.")
            return

        # Ask the user where to save the output file
        output_filepath = filedialog.asksaveasfilename(
            title="Save podcast as...",
            defaultextension=".mp3",
            filetypes=(
                ("MP3", "*.mp3"),
                ("WAV", "*.wav"),
                ("All files", "*.*")
            ),
            initialdir= os.path.expanduser("~/Downloads"),
        )

        if not output_filepath:
            self.log_status("Generation cancelled by user.")
            return

        # Disable buttons during generation
        self.generate_button.config(state='disabled')
        self.load_button.config(state='disabled')
        self.play_button.config(state='disabled')
        self.show_button.config(state='disabled')
        self.menubar.entryconfig("Options", state="disabled")

        # Show and start the progress bar
        self.clear_log()

        self.progress_bar.pack(fill=tk.X, pady=(10, 0), before=self.button_frame)
        self.progress_bar.start()

        thread = threading.Thread(target=self.run_generation, args=(script_content, output_filepath, self.speaker_settings, self.api_key))
        thread.daemon = True
        thread.start()

    def run_generation(self, script_content, output_filepath, speaker_mapping, api_key):
        """The function executed by the thread."""
        generated_filepath = None
        try:
            self.logger.info("Starting generation thread.")
            self.log_status(f"Starting generation to '{os.path.basename(output_filepath)}'...")
            generated_filepath = self.generate_func(
                script_text=script_content,
                speaker_mapping=speaker_mapping,
                output_filepath=output_filepath,
                status_callback=self.log_status,
                api_key=api_key
            )
            if generated_filepath:
                self.last_generated_filepath = generated_filepath
                self.logger.info(f"Generation completed successfully. File: {generated_filepath}")
                self.log_status(f"\n--- Generation completed successfully! File: {os.path.basename(generated_filepath)} ---")
            else:
                self.logger.warning("Generation function completed without returning a file path.")
                self.log_status("\n--- Generation failed. Please check the logs. ---")
        except Exception as e:
            self.logger.error(f"Unhandled error in generation thread: {e}", exc_info=True)
            self.log_status(f"A critical error occurred in the thread: {e}")
            generated_filepath = None # Ensure the status is 'failure'
        finally:
            # We use the queue, our reliable communication channel,
            # to signal the end of the generation and its status (success/failure).
            success = bool(generated_filepath)
            self.log_queue.put(('GENERATION_COMPLETE', success))

    def on_generation_complete(self, success: bool):
        if success:
            self.root.bell()
            if self.ffplay_path:
                self.show_button.config(state='normal')
                self.play_button.config(state='normal')

        self.progress_bar.stop()
        self.generate_button.config(state='normal')
        self.load_button.config(state='normal')
        self.menubar.entryconfig("Options", state="normal")
        if self.progress_bar.winfo_ismapped():
            self.progress_bar.pack_forget()
        self.log_text.config(state='disabled') # Disable the log area at the very end

    def open_file_location(self):
        """Opens the folder containing the last generated file and selects it."""
        if not self.last_generated_filepath or not os.path.exists(self.last_generated_filepath):
            messagebox.showerror("File not found", "The generated audio file was not found or is no longer accessible.")
            return

        try:
            if sys.platform == "darwin":  # macOS
                # 'open -R' reveals the file in Finder
                subprocess.run(["open", "-R", self.last_generated_filepath], check=True)
            elif sys.platform == "win32":  # Windows
                # 'explorer /select,' selects the file. The path must be part of the same argument.
                subprocess.run(["explorer", f"/select,{os.path.normpath(self.last_generated_filepath)}"], check=True)
            else:  # Linux and others (opens the containing folder)
                subprocess.run(["xdg-open", os.path.dirname(self.last_generated_filepath)], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            messagebox.showerror("Error", f"Unable to open the file manager.\n"
                                           f"Check that system tools are accessible.\n\nError: {e}")

    def play_last_generated_file(self):
        """Plays or stops the playback of the last generated audio file."""
        if self.playback_obj and self.playback_obj.poll() is None:
            self.playback_obj.terminate() # Stops the ffplay process if running
            return

        if not self.ffplay_path:
            messagebox.showerror(
                "Audio player not found",
                "The 'ffplay' command (part of FFmpeg) was not found.\n\n"
                "Playback is disabled. Please ensure FFmpeg is properly installed."
            )
            self.play_button.config(state='disabled')
            return

        if not self.last_generated_filepath or not os.path.exists(self.last_generated_filepath):
            messagebox.showerror("File not found", "The generated audio file was not found or is no longer accessible.")
            return

        threading.Thread(target=self._play_in_thread, daemon=True).start()

    def _play_in_thread(self):
        """The playback function executed in a separate thread."""
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            self.log_queue.put(('UPDATE_PLAY_BUTTON', '⏹️ Stop', 'normal'))
            command = [self.ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", self.last_generated_filepath]
            self.playback_obj = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            self.playback_obj.wait()
        except Exception as e:
            self.logger.error(f"Audio playback error with ffplay: {e}", exc_info=True)
            self.log_status(f"Audio playback error: {e}")
        finally:
            self.playback_obj = None
            if self.root.winfo_exists():
                self.log_queue.put(('UPDATE_PLAY_BUTTON', '▶️ Play', 'normal'))

    def on_settings_window_close(self):
        """Callback to re-enable the menu when the settings window is closed."""
        self.menubar.entryconfig("Options", state="normal")

class AboutWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About Podcast Generator")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        main_frame = tk.Frame(self, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text=f"Podcast Generator v{get_app_version()}", font=('Helvetica', 12, 'bold')).pack(pady=(0, 5))
        tk.Label(main_frame, text=f"Copyright (c) {datetime.now().year} Laurent FRANCOISE").pack()
        tk.Label(main_frame, text="Licence : MIT License").pack(pady=(0, 15))

        support_frame = tk.LabelFrame(main_frame, text="Support the projet", padx=10, pady=10)
        support_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(support_frame, text="If this application is useful to you, you can support its development:").pack(pady=(0, 5))

        coffee_link = tk.Label(support_frame, text="❤️ Buy Me a Coffee", fg="blue", cursor="hand2", font=('Helvetica', 10, 'bold'))
        coffee_link.pack(pady=(0, 5))
        coffee_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://buymeacoffee.com/laurentftech"))

        credits_frame = tk.LabelFrame(main_frame, text="Credits and Acknowledgements", padx=10, pady=10)
        credits_frame.pack(fill=tk.X, pady=(0, 10))

        # Gemini API link
        gemini_frame = tk.Frame(credits_frame)
        gemini_frame.pack(fill=tk.X, pady=2)
        tk.Label(gemini_frame, text="- Google Gemini API:").pack(side=tk.LEFT)
        link_label = tk.Label(gemini_frame, text="ai.google.dev/gemini-api", fg="blue", cursor="hand2")
        link_label.pack(side=tk.LEFT, padx=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://ai.google.dev/gemini-api"))

        tk.Label(credits_frame, text="- Tkinter for the graphical interface", anchor="w").pack(fill=tk.X, pady=2)
        tk.Label(credits_frame, text="- Icon by Smashicons (www.flaticon.com)", anchor="w").pack(fill=tk.X, pady=2)

        ok_button = tk.Button(main_frame, text="OK", command=self.destroy, width=10)
        ok_button.pack(pady=(10, 0))
        ok_button.focus_set()
        
        self.bind('<Return>', lambda event: ok_button.invoke())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

class SettingsWindow(tk.Toplevel):
    VOICE_DISPLAY_LIST = [f"{name} - {desc}" for name, desc in AVAILABLE_VOICES.items()]

    def __init__(self, parent, current_settings, save_callback, close_callback, default_settings):
        super().__init__(parent)
        self.title("Voice settings")
        self.transient(parent)
        self.grab_set()

        self.default_settings = default_settings
        self.current_settings = dict(current_settings) # Crée une copie
        self.save_callback = save_callback
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.cancel_and_close) # Manages closing with the cross
        self.entries = []

        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        tk.Label(header_frame, text="Speaker name (in the script)", font=('Helvetica', 10, 'bold')).pack(side=tk.LEFT, expand=True)
        tk.Label(header_frame, text="Voice name (Gemini)", font=('Helvetica', 10, 'bold')).pack(side=tk.RIGHT, expand=True)

        self.speaker_frame = tk.Frame(main_frame)
        self.speaker_frame.pack(fill=tk.BOTH, expand=True)

        self.populate_fields()

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(button_frame, text="+", command=self.add_row).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Save", command=self.save_and_close).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Cancel", command=self.cancel_and_close).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Restore Defaults", command=self.restore_defaults).pack(side=tk.LEFT, padx=(10, 0))

    def populate_fields(self):
        for speaker, voice in self.current_settings.items():
            self.add_row(speaker, voice)

    def add_row(self, speaker_text="", voice_text=""):
        """Adds a complete row for a speaker with a dropdown list for the voice."""
        row_container = tk.Frame(self.speaker_frame)
        row_container.pack(fill=tk.X, pady=2)

        speaker_entry = tk.Entry(row_container)
        speaker_entry.insert(0, speaker_text)

        voice_combo = ttk.Combobox(row_container, values=self.VOICE_DISPLAY_LIST)
        # Finds the full string to display, or uses the raw value if it's a custom voice
        initial_display_value = voice_text
        if voice_text in AVAILABLE_VOICES:
            initial_display_value = f"{voice_text} - {AVAILABLE_VOICES[voice_text]}"
        voice_combo.insert(0, initial_display_value)
        
        entry_tuple = (speaker_entry, voice_combo)
        delete_button = tk.Button(row_container, text="-", width=2, command=lambda: self.delete_row(row_container, entry_tuple))

        # Layout with grid for better alignment
        row_container.columnconfigure(0, weight=1)
        row_container.columnconfigure(1, weight=1)
        row_container.columnconfigure(2, weight=0)

        speaker_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        voice_combo.grid(row=0, column=1, sticky="ew")
        delete_button.grid(row=0, column=2, sticky="w", padx=(5, 0))

        self.entries.append(entry_tuple)

    def delete_row(self, row_container, entry_tuple):
        """Deletes a speaker row from the interface and the list."""
        row_container.destroy()
        self.entries.remove(entry_tuple)

    def restore_defaults(self):
        """Clears the current fields and fills them with the default settings."""
        # Empties the interface and the internal list
        for widget in self.speaker_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        # Replaces the current settings with a copy of the defaults
        self.current_settings = self.default_settings.copy()
        # Fills the interface with the new values (which are now the defaults)
        self.populate_fields()

    def save_and_close(self):
        new_settings = {}
        for speaker_entry, voice_combo in self.entries:
            speaker = speaker_entry.get().strip()
            full_voice_string = voice_combo.get().strip()
            if speaker and full_voice_string:
                # Extracts only the voice name (before the " - ")
                voice_name = full_voice_string.split(' - ')[0]
                new_settings[speaker] = voice_name

        self.save_callback(new_settings)
        self.close_callback()
        self.destroy()

    def cancel_and_close(self):
        self.close_callback()
        self.destroy()

def main():
    # Initializes the application and starts the main Tkinter loop
    # Creates the root window but hides it for now.
    # This allows for reliable display of error dialogs
    # even if the full interface initialization fails.
    root = tk.Tk()
    root.withdraw()

    # --- Import path correction ---
    # Ensures the script can find 'generate_podcast.py'
    # regardless of where it is executed from.
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
    except NameError:
        # __file__ is not defined in some interactive environments
        pass

    # --- Importing dependencies ---
    try:
        from generate_podcast import generate, PODCAST_SCRIPT, setup_logging, get_api_key, find_ffplay_path
    except ImportError as e:
        messagebox.showerror(
            "Import Error",
            f"The file 'generate_podcast.py' was not found.\n\n"
            f"Please ensure it is in the same folder as gui.py.\n\n"
            f"Error details: {e}"
        , parent=root)
        root.destroy()
        return

    # Initializes logging before anything else
    logger = setup_logging()

    # --- API key check at startup ---
    api_key = get_api_key(lambda msg: logger.info(msg), logger, parent_window=root)
    if not api_key:
        logger.info("Application closed because no API key was provided at startup.")
        messagebox.showwarning("API Key Required", "The application cannot start without an API key.", parent=root)
        root.destroy()
        return
    
    # If everything is correct, we build the interface and display the window
    app = PodcastGeneratorApp(root, generate_func=generate, logger=logger, api_key=api_key, default_script=PODCAST_SCRIPT)
    root.deiconify()
    root.mainloop()

if __name__ == "__main__":
    main()
