# 🎙️ Multi-Speaker Podcast Generator
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/laurentftech)

If you enjoy this project and want to support my work, feel free to [buy me a coffee](https://www.buymeacoffee.com/laurentftech) ☕. Thank you for your support!

---

## 📖 Overview
A lightweight Python app that lets you generate multi-speaker podcasts from any script using high-quality voices from the ElevenLabs and Google Gemini APIs — simple, fast, and effective.

### 🔑 Getting Started
Get your free API key from [ElevenLabs](https://try.elevenlabs.io/zobct2wsp98z) (or Google Gemini).
Add it securely to the app.
Start creating your own podcasts in minutes.

💡 **Note**: I am an **affiliate of ElevenLabs**. Using this link may earn me a commission at no extra cost to you. ElevenLabs also offers a **free tier** with monthly character limits for premium voices.

![Application Screenshot](podcast_creator_screenshot.png)

See also the [French README](docs/README-fr.md) for a version in French.

---

## ✨ Features

- **Audio Generation**: Create multi-speaker podcasts using high-quality voices from the Google Gemini or ElevenLabs API.
- **User-Friendly Interface**: An intuitive graphical interface built with Tkinter.
- **Flexible Formats**: Export your creations in **MP3** (default) or **WAV** formats.
- **Customization**: Configure and save voices for each speaker in your scripts, with options for language and accent.
- **Voice Guides**: Explore and listen to all available voices from Gemini and ElevenLabs directly within the settings. Add your favorite voices to your speaker list with a single click.
- **Integrated Playback**: Listen to and stop audio playback directly from the application (requires FFmpeg).
- **Secure API Key Storage**: Your Google Gemini API key is requested once and securely stored in your system's keychain (`keyring`).
- **Automatic Versioning**: The application version is automatically synchronized with the project's Git tags.
- **Accent and Language Support**: Create podcasts in multiple languages with distinct voices and accents for each language (from the speaker settings with the ElevenLabs API or from the prompt with Gemini).

---

## 🌍 Multilingual Support

Thanks to the ElevenLabs or Google Gemini API, **Podcast Generator** supports multiple languages and accents, allowing you to:

- Create multilingual podcasts with distinct voices and accents for each language.
- Emotional tone adaptation from the script.
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

⚠️ The speaker names in your script (e.g., John:, Samantha:) must **exactly** match the names defined in the "Voice Settings" window. If not, the script will not be processed.

### Here's an example of a script with emotional tone instructions:

```txt 
Read aloud the play with emphasing strongly the emotions of the characters.
Cyrano: [mocking] Ah ! non ! c’est un peu court, jeune homme !
On pouvait dire… oh ! Dieu ! … bien des choses en somme…
[sarcastic] Agressif : « moi, monsieur, si j’avais un tel nez,
Il faudrait sur-le-champ que je me l’amputasse ! »
[playful] Amical : « Mais il doit tremper dans votre tasse !
Pour boire, faites-vous fabriquer un hanap ! »
[dramatic] Descriptif : « C’est un roc ! … c’est un pic ! … c’est un cap !
Que dis-je, c’est un cap ? … C’est une péninsule ! »
[teasing] Curieux : « De quoi sert cette oblongue capsule ?
D’écritoire, monsieur, ou de boîte à ciseaux ? »
```

💡 Note on Annotations: The app uses square brackets [emotion] for ElevenLabs' emotional cues. If you use Gemini, the app will automatically convert them to parentheses (emotion) for you.

## 📦 Installation

### 1. Required Dependency: FFmpeg

For audio conversion and playback, this application requires FFmpeg to be installed on your system.

#### **macOS**
Install via [Homebrew](https://brew.sh/):
```bash
brew install ffmpeg
```

#### **Linux**
Most distributions provide FFmpeg in their package manager:
```bash
sudo apt install ffmpeg        # Debian/Ubuntu
sudo dnf install ffmpeg        # Fedora
sudo pacman -S ffmpeg          # Arch
```

#### **Windows (Detailed Guide)**

1. **Download FFmpeg**  
   Go to the official FFmpeg build page:  
   👉 [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)  
   Download the latest **"release full"** ZIP archive (e.g., `ffmpeg-release-full.7z` or `.zip`).

2. **Extract the archive**  
   - Right-click the downloaded ZIP file and choose **Extract All…**  
   - You will get a folder named similar to `ffmpeg-2025-xx-xx-full_build`.

3. **Move the folder**  
   - Move the extracted `ffmpeg` folder to a location where it will stay permanently, for example:  
     `C:\ffmpeg`

4. **Add FFmpeg to the PATH**  
   - Press **Windows + R**, type:
     ```
     sysdm.cpl
     ```
     and press **Enter**.
   - In the **System Properties** window, go to **Advanced** → **Environment Variables**.
   - Under **System variables**, find and select **Path**, then click **Edit**.
   - Click **New** and add the path to FFmpeg’s `bin` folder, e.g.:
     ```
     C:\ffmpeg\bin
     ```
   - Click **OK** to close all dialogs.

5. **Verify installation**  
   - Open **Command Prompt** and type:
     ```
     ffmpeg -version
     ```
     You should see the version info, confirming FFmpeg is installed and accessible from anywhere.

---

### 2. Installing the Application

1. Go to the **Releases** page.
2. Download the latest archive for your system:
    * **macOS/Linux**: Download the `.tar.gz` file (`..._MacOS_arm64.tar.gz` for Apple Silicon, `..._MacOS_x86_64.tar.gz` for Intel, or `..._Linux.tar.gz` for Linux).
    * **Windows**: Download the `.zip` or `.tar.gz` file.
3. **Extract the archive**:
    * On macOS and Linux, double-click the `.tar.gz` file to extract the application, or use:
      ```bash
      tar -xzf Podcast_Generator_MacOS_arm64.tar.gz
      ```
    * On Windows, unzip the archive.
4. **Move the application**:
    * On macOS, drag `Podcast Generator.app` to your `Applications` folder.
    * On Windows, place the extracted folder anywhere you like.
    * On Linux, place it in your home directory or any preferred location.

---

### 💡 Note for macOS Users

When you first run the application, macOS will show several security warnings because it's not from the App Store. This is normal.

1. **"App downloaded from the internet"**: Click **Open**.
2. **"Unidentified Developer"**: macOS may block the app. Click **OK**, then:
    * Go to **System Settings** → **Privacy & Security**.
    * Scroll to the **Security** section.
    * Click **Open Anyway** and confirm.

---

### 💡 Note for Windows Users (Windows 10 / 11)

When you first run the application, **Windows SmartScreen** might block it because it’s not signed by Microsoft Store.

1. When you double-click the executable, you might see a window saying:  
   *"Windows protected your PC"*.

2. Click on **More info**.

3. Then click on **Run anyway**.

After doing this once, Windows will remember your choice and won’t show the warning again.

---

### First Launch: API Key

On first launch, the application will request your **ElevenLabs API key** (and optionally your **Google Gemini API key**).  
It will be stored securely.

---

## 👨‍💻 For Developers
To contribute to the project, run the code, or create your own build, please refer to the full developer guide:
➡️ [DEVELOPERS.md](docs/DEVELOPERS.md)

### Generating a Synchronized HTML Demo (MFA required)

You can generate a shareable HTML demo with synchronized audio and text from the command line.

This completely optional feature require the installation of MFA [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/latest)

See an example of HTML page generated [here](https://laurentftech.github.io/Podcast_generator/who_am_i.html). 

```bash
python create_demo.py /path/to/audio.mp3 /path/to/script.txt --title "My Awesome Podcast" --subtitle "Episode 1" --output-dir docs
```

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE.md file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see the DEVELOPERS.md file for guidelines.

---

Thank you for exploring **Podcast Generator**! Feel free to support this project with a coffee ☕.
