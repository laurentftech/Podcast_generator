# 🎙️ Podcast Generator
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/laurentftech)
[![Docker Hub](https://img.shields.io/docker/v/gandulf78/podcast_generator?label=docker&logo=docker)](https://hub.docker.com/r/gandulf78/podcast_generator)
[![Docker Pulls](https://img.shields.io/docker/pulls/gandulf78/podcast_generator)](https://hub.docker.com/r/gandulf78/podcast_generator)

If you enjoy this project and want to support my work, feel free to [buy me a coffee](https://www.buymeacoffee.com/laurentftech) ☕. Thank you for your support!

---

## 📖 Overview
A lightweight Python app with a modern UI that lets you generate multi-speaker podcasts from any script. It uses high-quality voices from the **ElevenLabs** and **Google Gemini** APIs, and can even create synchronized HTML demos of your podcasts.


### 🔑 Getting Started
Get your free API key from [ElevenLabs](https://try.elevenlabs.io/zobct2wsp98z) (or Google Gemini).
Add it securely to the app.
Start creating your own podcasts in minutes.

💡 **Note**: I am an **affiliate of ElevenLabs**. Using this link may earn me a commission at no extra cost to you. ElevenLabs also offers a **free tier** with monthly character limits for premium voices.

![Application Screenshot](docs/assets/podcast_creator_screenshot.png)

See also the [French README](docs/README-fr.md) for a version in French.

---

## ✨ Features

 - **Modern UI**: A clean, modern, and responsive interface built with `customtkinter` that adapts to your system's light or dark mode.
 - **Dual TTS Provider**: Choose between the high-quality voices of **Google Gemini** or **ElevenLabs**.
 - **AI-Powered Script Analysis**: Generate DOCX documents with AI-powered analysis of your podcast scripts, including summaries, comprehension questions for different language levels (A1, A2, B1), and key educational insights. Perfect for language teachers and content creators.
 - **Synchronized HTML Demo**: Automatically generate a shareable HTML page with your podcast audio and a synchronized, highlighted transcript.
 - **Flexible Formats**: Export your creations in **MP3** (default) or **WAV** formats.
 - **Customization**: Configure and save voices for each speaker in your scripts, with options for language and accent.
 - **Voice Guides**: Explore and listen to all available voices from Gemini and ElevenLabs directly within the settings. Add your favorite voices to your speaker list with a single click.
- **Integrated Playback**: Listen to and stop audio playback directly from the application (requires FFmpeg).
- **Secure API Key Storage**: Your Google Gemini API key is requested once and securely stored in your system's keychain (`keyring`).
- **Accent and Language Support**: Create podcasts in multiple languages with distinct voices and accents for each language (from the speaker settings with the ElevenLabs API or from the prompt with Gemini).
- **Docker Support**: Run the application as a web service using Docker. This simplifies deployment, requires no additional installation, and can run on a small headless server or locally.

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

---

## 📝 AI-Powered Script Analysis (Web Interface)

The web interface includes an optional AI-powered analysis feature that generates professional DOCX documents analyzing your podcast scripts. This feature is particularly useful for **language teachers**, **content creators**, and **educational material developers**.

### What's Included in the Analysis

The generated DOCX document contains:
- **Summary**: A concise overview of the podcast content
- **Main Characters**: Key speakers and personalities mentioned
- **Key Locations**: Important places referenced in the script
- **Central Theme**: The main message or topic
- **Comprehension Questions**: Tailored questions for different language proficiency levels:
  - A1 (Beginner)
  - A1+/A2 (Elementary)
  - A2+/B1 (Intermediate)

### Setup Instructions

To enable this feature in the web interface:

1. **Configure Gemini API Key**
   Add your Gemini API key to the `.env` file:
   ```bash
   GEMINI_API_KEY=your_actual_key_here
   ```

2. **Create Analysis Prompt File**
   Copy the example prompt configuration:
   ```bash
   cp config/analysis_prompt.txt.example config/analysis_prompt.txt
   ```

3. **Customize the Prompt (Optional)**
   Edit `config/analysis_prompt.txt` to modify how the AI analyzes your scripts. You can adjust:
   - The types of questions generated
   - Language levels targeted
   - Analysis depth and focus areas
   - Output formatting preferences

4. **Access the Feature**
   Once configured, a purple "Generate DOCX Analysis" button will appear next to the "Generate Podcast" button in the web interface.

### File Locations

- **Docker**: `./config/analysis_prompt.txt`
- **macOS**: `~/Library/Application Support/PodcastGenerator/analysis_prompt.txt`
- **Windows**: `%APPDATA%/PodcastGenerator/analysis_prompt.txt`
- **Linux**: `~/.config/PodcastGenerator/analysis_prompt.txt`

For more details, see the `config/README.md` file.

---

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

## 🚀 Advanced Feature: HTML Demo Generation (optional)
 
 The app can generate a shareable HTML page with your podcast audio and a synchronized, word-by-word highlighted transcript. This is perfect for sharing demos or for accessibility.
 
 See an example of a generated HTML page [here](https://laurentftech.github.io/Podcast_generator/assets/who_am_i.html).
 
 ### Installing Optional Dependencies for Demo Generation
 
 This feature relies on `whisperx` for audio alignment, which requires PyTorch. These are heavy dependencies, so they are optional. To enable this feature, you need to install them manually.
 
 **1. Install PyTorch**  
 It is highly recommended to install the CPU-only version of PyTorch, as it is much lighter and sufficient for this application. Visit the official PyTorch website and select the appropriate options for your system.
 
 For example, using `conda`:

```bash
conda install pytorch torchaudio cpuonly -c pytorch
```

 **2. Install WhisperX**  
Once PyTorch is installed, you can install whisperx and its other dependencies using the [demo] extra:
pip install .[demo]

```bash
pip install .[demo]
```

---

## 🐳 Docker Deployment

You can run Podcast Generator as a web service using Docker. This provides a REST API and web interface.

### Setting up API Keys

First, create a `.env` file with your API keys:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
# ELEVENLABS_API_KEY=your_actual_key_here
# GEMINI_API_KEY=your_actual_key_here
```

### Using Docker Hub (Recommended)

**Option 1: Using docker-compose (easiest)**

```bash
# Pull and start the container (reads .env automatically)
docker-compose -f docker-compose.prod.yml up -d
```

**Option 2: Using docker run**

```bash
# Pull the latest image
docker pull gandulf78/podcast_generator:latest

# Run the container (load .env file)
docker run -d -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  gandulf78/podcast_generator:latest
```

The web interface will be available at `http://localhost:8000`

### Building from Source

```bash
docker-compose up --build
```

---

## 👨‍💻 For Developers
To contribute to the project, run the code, or create your own build, please refer to the full developer guide:
➡️ [DEVELOPERS.md](docs/DEVELOPERS.md)


---

## 📜 License

This project is licensed under the MIT License - see the LICENSE.md file for details.

---

## 🤝 Contributing

Contributions are welcome! Please see the DEVELOPERS.md file for guidelines.

---

Thank you for exploring **Podcast Generator**! Feel free to support this project with a coffee ☕.
