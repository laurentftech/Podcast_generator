import tkinter as tk
import webbrowser
from datetime import datetime
import customtkinter


class AboutWindow(customtkinter.CTkToplevel):
    def __init__(self, parent, version: str):
        super().__init__(parent)
        self.title("About Podcast Generator")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)

        customtkinter.CTkLabel(main_frame, text=f"Podcast Generator v{version}",
                               font=customtkinter.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        customtkinter.CTkLabel(main_frame, text=f"Copyright (c) {datetime.now().year} Laurent FRANCOISE").pack()
        customtkinter.CTkLabel(main_frame, text="Licence : MIT License").pack(pady=(0, 15))

        support_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        support_section.pack(fill=tk.X, padx=20, pady=(0, 10))
        customtkinter.CTkLabel(support_section, text="Support the project",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        support_frame = customtkinter.CTkFrame(support_section, border_width=1)
        support_frame.pack(fill=tk.X, pady=(5, 0), ipady=5)

        customtkinter.CTkLabel(support_frame,
                               text="If this application is useful to you, you can support its development:",
                               wraplength=400).pack(pady=10, padx=10)

        coffee_link = customtkinter.CTkLabel(support_frame, text="❤️ Buy Me a Coffee",
                                             text_color=("#3a7ebf", "#1f6aa5"), cursor="hand2",
                                             font=customtkinter.CTkFont(weight="bold"))
        coffee_link.pack(pady=(0, 10))
        coffee_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://buymeacoffee.com/laurentftech"))

        credits_section = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        credits_section.pack(fill=tk.X, padx=20, pady=(0, 10))
        customtkinter.CTkLabel(credits_section, text="Credits and Acknowledgements",
                               font=customtkinter.CTkFont(weight="bold")).pack(anchor="w")
        credits_frame = customtkinter.CTkFrame(credits_section, border_width=1)
        credits_frame.pack(fill=tk.X, pady=(5, 0), ipady=5)

        # Gemini API link
        gemini_frame = self._create_link_row(credits_frame, "- Google Gemini API:", "ai.google.dev/gemini-api",
                                             "https://ai.google.dev/gemini-api")
        gemini_frame.pack(fill=tk.X, padx=10, pady=2)

        # ElevenLabs API link
        elevenlabs_frame = self._create_link_row(credits_frame, "- ElevenLabs API:", "elevenlabs.io",
                                                 "https://elevenlabs.io")
        elevenlabs_frame.pack(fill=tk.X, padx=10, pady=2)

        # Montreal Forced Aligner link
        mfa_frame = self._create_link_row(credits_frame, "- Montreal Forced Aligner:",
                                          "montreal-forced-aligner.readthedocs.io",
                                          "https://montreal-forced-aligner.readthedocs.io/")
        mfa_frame.pack(fill=tk.X, padx=10, pady=2)

        customtkinter.CTkLabel(credits_frame, text="- Tkinter & customtkinter for the graphical interface",
                               anchor="w").pack(fill=tk.X, padx=10, pady=2)

        # Flaticon link
        flaticon_frame = self._create_link_row(credits_frame, "- Icon by Smashicons from", "flaticon.com",
                                               "https://www.flaticon.com")
        flaticon_frame.pack(fill=tk.X, padx=10, pady=2)

        ok_button = customtkinter.CTkButton(main_frame, text="OK", command=self.destroy, width=100)
        ok_button.pack(pady=(15, 15))

        self.bind('<Return>', lambda event: ok_button.invoke())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _create_link_row(self, parent, text, link_text, url):
        frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        customtkinter.CTkLabel(frame, text=text).pack(side=tk.LEFT)
        link_label = customtkinter.CTkLabel(frame, text=link_text, text_color=("#3a7ebf", "#1f6aa5"), cursor="hand2")
        link_label.pack(side=tk.LEFT, padx=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://ai.google.dev/gemini-api"))
        return frame
