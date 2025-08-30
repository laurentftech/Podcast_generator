import os
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter


class DemoSettingsWindow(customtkinter.CTkToplevel):
    def __init__(self, parent, callback, default_title="", default_output_dir=""):
        super().__init__(parent)
        self.title("HTML Demo Settings")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.callback = callback

        main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Fields ---
        fields_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        fields_frame.pack(fill=tk.X, padx=20, pady=15)

        # Title
        customtkinter.CTkLabel(fields_frame, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        self.title_var = tk.StringVar(value=default_title)
        self.title_entry = customtkinter.CTkEntry(fields_frame, textvariable=self.title_var, width=350)
        self.title_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=5)

        # Subtitle
        customtkinter.CTkLabel(fields_frame, text="Subtitle:").grid(row=1, column=0, sticky="w", pady=2)
        self.subtitle_var = tk.StringVar()
        self.subtitle_entry = customtkinter.CTkEntry(fields_frame, textvariable=self.subtitle_var, width=350)
        self.subtitle_entry.grid(row=1, column=1, sticky="ew", pady=2, padx=5)

        # Output Directory
        customtkinter.CTkLabel(fields_frame, text="Output Directory:").grid(row=2, column=0, sticky="w", pady=2)
        self.output_dir_var = tk.StringVar(value=default_output_dir or os.path.expanduser("~/Downloads"))
        dir_frame = customtkinter.CTkFrame(fields_frame, fg_color="transparent")
        dir_frame.grid(row=2, column=1, sticky="ew", pady=2, padx=5)
        self.output_dir_entry = customtkinter.CTkEntry(dir_frame, textvariable=self.output_dir_var)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_button = customtkinter.CTkButton(dir_frame, text="Browse...", command=self.browse_directory, width=80)
        browse_button.pack(side=tk.LEFT, padx=(5, 0))

        fields_frame.grid_columnconfigure(1, weight=1)

        # --- Buttons ---
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=(15, 15))

        ok_button = customtkinter.CTkButton(button_frame, text="Generate Demo", command=self.on_ok)

        ok_button.pack(side=tk.LEFT, padx=5)
        cancel_button = customtkinter.CTkButton(button_frame, text="Cancel", command=self.destroy,
                                                fg_color="transparent", text_color = ("gray10", "gray90"), border_width=1)

        cancel_button.pack(side=tk.LEFT, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind('<Return>', lambda event: ok_button.invoke())
        self.bind('<Escape>', lambda event: cancel_button.invoke())

        self.after(100, self.title_entry.focus_set)

    def browse_directory(self):
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get(),
            parent=self
        )
        if directory:
            self.output_dir_var.set(directory)

    def on_ok(self):
        title = self.title_var.get().strip()
        subtitle = self.subtitle_var.get().strip()
        output_dir = self.output_dir_var.get().strip()

        if not title:
            messagebox.showerror("Validation Error", "Title cannot be empty.", parent=self)
            return
        if not output_dir:
            messagebox.showerror("Validation Error", "Output directory cannot be empty.", parent=self)
            return

        self.callback(title, subtitle, output_dir)
        self.destroy()
