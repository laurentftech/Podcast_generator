
# Podcast Creator
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/laurentftech)

If you enjoy this project and want to support my work, feel free to [buy me a coffee](https://www.buymeacoffee.com/laurentftech) ☕. Thank you for your support!

---

## 📖 Overview

A simple yet powerful desktop application developed in Python with Tkinter, which allows you to create a multi-speaker audio podcast from a text script using the Google Gemini text-to-speech API.

![Application Screenshot](podcast_creator_screenshot.png)

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

## 🧪 Example of Multilingual Usage

Here's an example of a script for a multilingual podcast:

```txt
Speaker_1 (fr): Bonjour à tous, bienvenue dans ce nouvel épisode.
Speaker_2 (en): Hello everyone, welcome to this new episode.
Speaker_3 (es): Hola a todos, bienvenidos a este nuevo episodio.
```

Each speaker can be configured within the application with the corresponding language for a natural and fluent output.

---

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Required Python packages (see `requirements.txt`)

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/laurentftech/Podcast_creator.git
   cd Podcast_creator
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:

   Create a `.env` file in the project root and add your Google Gemini API key:

   ```env
   GEMINI_API_KEY=your_google_gemini_api_key_here
   ```

4. Run the application:

   ```bash
   python app.py
   ```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see the [DEVELOPERS](DEVELOPERS.md) file for guidelines.

---

Thank you for exploring **Podcast Creator**! Feel free to support this project with a coffee ☕.
