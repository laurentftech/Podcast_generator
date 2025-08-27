import tkinter as tk
import webbrowser
from datetime import datetime


class AboutWindow(tk.Toplevel):
    def __init__(self, parent, version: str):
        super().__init__(parent)
        self.title("About Podcast Generator")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        main_frame = tk.Frame(self, padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text=f"Podcast Generator v{version}", font=('Helvetica', 12, 'bold')).pack(
            pady=(0, 5))
        tk.Label(main_frame, text=f"Copyright (c) {datetime.now().year} Laurent FRANCOISE").pack()
        tk.Label(main_frame, text="Licence : MIT License").pack(pady=(0, 15))

        support_frame = tk.LabelFrame(main_frame, text="Support the projet", padx=10, pady=10)
        support_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(support_frame, text="If this application is useful to you, you can support its development:").pack(
            pady=(0, 5))

        coffee_link = tk.Label(support_frame, text="❤️ Buy Me a Coffee", fg="blue", cursor="hand2",
                               font=('Helvetica', 10, 'bold'))
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

        # ElevenLabs API link
        elevenlabs_frame = tk.Frame(credits_frame)
        elevenlabs_frame.pack(fill=tk.X, pady=2)
        tk.Label(elevenlabs_frame, text="- ElevenLabs API:").pack(side=tk.LEFT)
        link_label2 = tk.Label(elevenlabs_frame, text="elevenlabs.io", fg="blue", cursor="hand2")
        link_label2.pack(side=tk.LEFT, padx=5)
        link_label2.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://elevenlabs.io"))

        # Montreal Forced Aligner link
        mfa_frame = tk.Frame(credits_frame)
        mfa_frame.pack(fill=tk.X, pady=2)
        tk.Label(mfa_frame, text="- Montreal Forced Aligner:").pack(side=tk.LEFT)
        mfa_link_label = tk.Label(mfa_frame, text="montreal-forced-aligner.readthedocs.io", fg="blue", cursor="hand2")
        mfa_link_label.pack(side=tk.LEFT, padx=5)
        mfa_link_label.bind("<Button-1>",
                            lambda e: webbrowser.open_new_tab("https://montreal-forced-aligner.readthedocs.io/"))

        tk.Label(credits_frame, text="- Tkinter for the graphical interface", anchor="w").pack(fill=tk.X, pady=2)

        # Flaticon link
        flaticon_frame = tk.Frame(credits_frame)
        flaticon_frame.pack(fill=tk.X, pady=2)
        tk.Label(flaticon_frame, text="- Icon by Smashicons from").pack(side=tk.LEFT)
        flaticon_link = tk.Label(flaticon_frame, text="flaticon.com", fg="blue", cursor="hand2")
        flaticon_link.pack(side=tk.LEFT, padx=5)
        flaticon_link.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://www.flaticon.com"))

        ok_button = tk.Button(main_frame, text="OK", command=self.destroy, width=10)
        ok_button.pack(pady=(10, 0))

        self.bind('<Return>', lambda event: ok_button.invoke())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
