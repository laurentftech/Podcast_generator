import tkinter as tk
import webbrowser
from tkinter import messagebox
import customtkinter
from customtkinter.windows.ctk_input_dialog import CTkInputDialog

from config import SERVICE_CONFIG


class APIKeysWindow(customtkinter.CTkToplevel):
    def __init__(self, parent, close_callback):
        super().__init__(parent)
        self.title("Welcome to Podcast Generator!")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.close_callback = close_callback
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)

        customtkinter.CTkLabel(main_frame, text="Manage API Keys",
                               font=customtkinter.CTkFont(size=14, weight="bold")).pack(pady=(15, 15))
        # Message de bienvenue (en anglais) pour guider l'utilisateur
        welcome_text = (
            "Welcome!\n"
            "Podcast Generator is a tool that generates podcasts using AI.\n"
            "To use it, you need to configure at least one API key for TTS (Text-to-Speech).\n"
            "You can set your ElevenLabs (and/or Google Gemini) API keys below. They will be stored securely in your system.\n"
        )
        customtkinter.CTkLabel(
            main_frame,
            text=welcome_text,
            justify="left",
            wraplength=520
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # ElevenLabs API Key section
        elevenlabs_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        elevenlabs_section.pack(fill=tk.X, padx=20, pady=(0, 10))
        customtkinter.CTkLabel(elevenlabs_section, text="ElevenLabs API",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        elevenlabs_frame = customtkinter.CTkFrame(elevenlabs_section, border_width=1)
        elevenlabs_frame.pack(fill=tk.X, pady=(5, 0), ipady=5)

        # Note sur les permissions minimales requises
        customtkinter.CTkLabel(
            elevenlabs_frame,
            text="Minimum required permissions in ElevenLabs API settings:\n"
                 "• Text to Speech: Has access\n"
                 "• User: Read only\n"
                 "• Voices: Read only",
            justify="left",
            wraplength=500
        ).pack(anchor="w", padx=10, pady=(10, 6))
        # Lien cliquable vers la page pour obtenir la clé ElevenLabs
        elevenlabs_link = customtkinter.CTkLabel(elevenlabs_frame, text="Get an ElevenLabs API key (affiliate)",
                                                 text_color=("#3a7ebf", "#1f6aa5"), cursor="hand2")
        elevenlabs_link.pack(anchor="w", padx=10, pady=(0, 6))
        elevenlabs_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://try.elevenlabs.io/zobct2wsp98z"))

        self.elevenlabs_status_label = customtkinter.CTkLabel(elevenlabs_frame, text="")
        self.elevenlabs_status_label.pack(anchor="w", padx=10, pady=(0, 5))

        elevenlabs_button_frame = customtkinter.CTkFrame(elevenlabs_frame, fg_color="transparent")
        elevenlabs_button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        elevenlabs_button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        customtkinter.CTkButton(elevenlabs_button_frame, text="Set/Update Key", command=lambda: self.set_api_key("elevenlabs")).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        customtkinter.CTkButton(elevenlabs_button_frame, text="Remove Key", command=lambda: self.remove_api_key("elevenlabs")).grid(
            row=0, column=1, sticky="ew", padx=(0, 5))
        customtkinter.CTkButton(elevenlabs_button_frame, text="Test Key", command=lambda: self.test_api_key("elevenlabs")).grid(
            row=0, column=2, sticky="ew")

        # Gemini API Key section
        gemini_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        gemini_section.pack(fill=tk.X, padx=20, pady=(0, 10))
        customtkinter.CTkLabel(gemini_section, text="Google Gemini API",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        gemini_frame = customtkinter.CTkFrame(gemini_section, border_width=1)
        gemini_frame.pack(fill=tk.X, pady=(5, 0), ipady=5)

        gemini_link = customtkinter.CTkLabel(gemini_frame, text="Get a Gemini API key",
                                             text_color=("#3a7ebf", "#1f6aa5"), cursor="hand2")
        gemini_link.pack(anchor="w", padx=10, pady=(10, 6))
        gemini_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://aistudio.google.com/app/apikey"))
        self.gemini_status_label = customtkinter.CTkLabel(gemini_frame, text="")
        self.gemini_status_label.pack(anchor="w", padx=10, pady=(0, 5))

        gemini_button_frame = customtkinter.CTkFrame(gemini_frame, fg_color="transparent")
        gemini_button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        gemini_button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        customtkinter.CTkButton(gemini_button_frame, text="Set/Update Key", command=lambda: self.set_api_key("gemini")).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        customtkinter.CTkButton(gemini_button_frame, text="Remove Key", command=lambda: self.remove_api_key("gemini")).grid(
            row=0, column=1, sticky="ew", padx=(0, 5))
        customtkinter.CTkButton(gemini_button_frame, text="Test Key", command=lambda: self.test_api_key("gemini")).grid(
            row=0, column=2, sticky="ew")

        # Close button
        customtkinter.CTkButton(main_frame, text="Close", command=self.on_close).pack(pady=(15, 15))

        # Update status on window creation
        self.update_status()

    def on_close(self):
        """Handle window close event."""
        if self.close_callback:
            self.close_callback()
        self.destroy()

    def update_status(self):
        """Update the status labels for both APIs."""
        import keyring

        # Check Gemini key
        gemini_key = keyring.get_password("PodcastGenerator", "gemini_api_key")
        if gemini_key:
            self.gemini_status_label.configure(text="✓ API key is configured", text_color="green")
        else:
            self.gemini_status_label.configure(text="✗ No API key configured", text_color="red")

        # Check ElevenLabs key
        elevenlabs_key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
        if elevenlabs_key:
            self.elevenlabs_status_label.configure(text="✓ API key is configured", text_color="green")
        else:
            self.elevenlabs_status_label.configure(text="✗ No API key configured", text_color="red")

    def set_api_key(self, service: str):
        """Set or update an API key for the specified service."""
        import keyring

        config = SERVICE_CONFIG.get(service)
        if not config: return

        dialog = CTkInputDialog(title=config["title"], text=f"Enter your {config['title']}:")
        new_key = dialog.get_input()

        if new_key and new_key.strip():
            keyring.set_password("PodcastGenerator", config["account"], new_key.strip())
            messagebox.showinfo("Success", f"{config['title']} has been saved securely.", parent=self)
            self.update_status()
        elif new_key is not None:  # User clicked OK but entered empty key
            messagebox.showwarning("Invalid Key", "API key cannot be empty.", parent=self)

    def remove_api_key(self, service: str):
        """Remove an API key for the specified service."""
        import keyring
        config = SERVICE_CONFIG.get(service)
        if not config: return

        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove the {config['title']}?",
                               parent=self):
            try:
                keyring.delete_password("PodcastGenerator", config["account"])
                messagebox.showinfo("Success", f"{config['title']} has been removed.", parent=self)
            except keyring.errors.PasswordDeleteError:
                messagebox.showinfo("Info", f"No {config['title']} was stored.", parent=self)
            self.update_status()

    def test_api_key(self, service: str):
        """Test an API key for the specified service."""
        import keyring
        import requests
        from tkinter import messagebox

        if service == "elevenlabs":
            key = keyring.get_password("PodcastGenerator", "elevenlabs_api_key")
            if not key:
                messagebox.showwarning("No Key", "No ElevenLabs API key is configured.", parent=self)
                return

            # Test ElevenLabs API
            try:
                headers = {"xi-api-key": key}
                response = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, timeout=10)

                if response.status_code == 200:
                    user_data = response.json()
                    subscription = user_data.get('subscription', {}).get('tier', 'Unknown')
                    char_count = user_data.get('subscription', {}).get('character_count', 'Unknown')
                    char_limit = user_data.get('subscription', {}).get('character_limit', 'Unknown')

                    messagebox.showinfo("Success",  # Restoring more detailed message
                                        f"ElevenLabs API key is valid! (API v1)\n\n"
                                        f"Subscription: {subscription}\n"
                                        f"Usage: {char_count} / {char_limit} characters\n\n"
                                        f"⚠ Using v1 compatibility mode",
                                        parent=self)

                elif response.status_code == 401:
                    try:
                        error_detail = response.json().get('detail', {})
                        if isinstance(error_detail, dict):
                            error_msg = error_detail.get('message', 'Invalid API key')
                        else:
                            error_msg = str(error_detail)
                    except:
                        error_msg = "Invalid or expired API key"

                    messagebox.showerror("Authentication Error",
                                         f"ElevenLabs API key test failed (401 Unauthorized):\n\n"
                                         f"{error_msg}\n\n"
                                         f"Please check:\n"
                                         f"• Key is correct and complete\n"
                                         f"• Key hasn't expired\n"
                                         f"• Account is active on elevenlabs.io", parent=self)
                else:
                    try:
                        error_detail = response.json()
                        error_msg = str(error_detail)
                    except:
                        error_msg = response.text[:200] if response.text else "Unknown error"

                    messagebox.showerror("Error",
                                         f"ElevenLabs API key test failed: {response.status_code}\n\n"
                                         f"Details: {error_msg}", parent=self)

            except requests.exceptions.RequestException as e:
                messagebox.showerror("Network Error", f"Failed to connect to ElevenLabs API:\n{str(e)}", parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to test ElevenLabs API key: {str(e)}", parent=self)

        else:
            # Gemini testing code
            key = keyring.get_password("PodcastGenerator", "gemini_api_key")
            if not key:
                messagebox.showwarning("No Key", "No Gemini API key is configured.", parent=self)
                return

            # Test Gemini API
            try:
                from google import genai
                client = genai.Client(api_key=key)
                # Simple test request
                models = list(client.models.list())
                if models:
                    messagebox.showinfo("Success", f"Gemini API key is valid!", parent=self)
                else:
                    messagebox.showwarning("Warning", "Gemini API key appears valid but no models accessible.",
                                           parent=self)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to test Gemini API key: {str(e)}", parent=self)

    def on_close(self):
        """Handle window closing."""
        self.close_callback()
        self.destroy()
