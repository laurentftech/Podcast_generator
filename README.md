
# Podcast Creator
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/laurentftech)

If you enjoy this project and want to support my work, feel free to [buy me a coffee](https://www.buymeacoffee.com/laurentftech) ☕. Thank you for your support!

---

## 📖 Overview

A simple yet powerful desktop application developed in Python with Tkinter, which allows you to create a multi-speaker audio podcast from a text script using the Google Gemini text-to-speech API.

![Application Screenshot](podcast_creator_screenshot.png)

See also the [French README](docs/README-fr.md) for a version in French.

---

## ✨ Features

- **Audio Generation**: Create multi-speaker podcasts using high-quality voices from the Google Gemini API.
- **User-Friendly Interface**: An intuitive graphical interface built with Tkinter.
- **Flexible Formats**: Export your creations in **MP3** (default) or **WAV** formats.
- **Customization**: Configure and save voices for each speaker in your scripts, with options for language and accent.
- **Integrated Playback**: Listen to and stop audio playback directly from the application (requires FFmpeg).
- **Secure API Key Storage**: Your Google Gemini API key is requested once and securely stored in your system's keychain (`keyring`).
- **Automatic Versioning**: The application version is automatically synchronized with the project's Git tags.

---

## 🌍 Multilingual Support

Thanks to the Google Gemini API, **Podcast Creator** supports multiple languages and accents, allowing you to:

- Create multilingual podcasts with distinct voices for each language.
- Produce content for an international audience.
- Facilitate language learning with realistic dialogues.
- Enhance accessibility by tailoring language to your target audience.

---

## 💡 Use Cases

- **Teaching and Training**  
  Transform your course materials or tutorials into multilingual audio podcasts to engage your learners.

- **Content Creation**  
  Automate the production of podcasts in various languages to reach a broader audience.

- **Accessibility**  
  Make your content accessible to a wider audience through multilingual support.

- **Language Practice**  
  Create multilingual dialogues with distinct voices for each character.

---

## 💡 Examples

### Creating multi-voice podcasts from written scripts

```txt
John: Hello everyone, welcome to this new episode.
Samantha: Today, we will explore the basics of artificial intelligence.
John: Stay with us to learn more!
Samantha: Don't forget to subscribe to our podcast.
```

### Here's an example of a script for a multilingual podcast:

```txt
John (fr): Bonjour à tous, bienvenue dans ce nouvel épisode.
Samantha (en): Hello everyone, welcome to this new episode.
John (es): Hola a todos, bienvenidos a este nuevo episodio.
```

---

## 📦 Installation

### 1. External Dependency: FFmpeg (Required)

For audio conversion and playback, this application requires FFmpeg to be installed on your system.

- **macOS**: The easiest way to install it is via Homebrew:  
  ```bash
  brew install ffmpeg
  ```
- **Windows / Linux**: Download it from the [official website](https://ffmpeg.org/download.html) and add it to your system's PATH.

---

### 2. Installing the Application

1. Go to the **"Releases"** or **"Tags"** tab.  
2. Download the version corresponding to your operating system.  
3. Unzip the `.zip` file.  
4. Place the application in the folder of your choice.  

---

### 💡 Note for macOS

When launching the application for the first time, macOS will block it because it comes from an unidentified developer (unsigned application).

**Recommended procedure (Recent macOS versions)**  
1. Double-click the application icon (an error message will appear saying it cannot be opened).  
2. Open **System Settings → Privacy & Security**.  
3. In the **Security** section, click **Open Anyway**.  
4. Confirm the opening.  

ℹ️ On some older versions of macOS, it was sometimes possible to bypass the warning by right-clicking → **Open**, but this method is no longer reliable on recent versions.

---

### First Launch: API Key

On first launch, the application will request your **Google Gemini API key**.  
It will be stored securely.


⸻

## 👨‍💻 For Developers
To contribute to the project, run the code, or create your own build, please refer to the full developer guide:
➡️ DEVELOPERS.md


---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see the [DEVELOPERS](docs/DEVELOPERS.md) file for guidelines.

---

Thank you for exploring **Podcast Creator**! Feel free to support this project with a coffee ☕.
