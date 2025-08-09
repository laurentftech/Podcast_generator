# Créateur de Podcast

Ce projet est une application de bureau simple mais puissante, développée en Python avec Tkinter, qui permet de créer un podcast audio multi-locuteurs à partir d'un script texte, en utilisant l'API de synthèse vocale de Google Gemini.

![Capture d'écran de l'application](podcast_creator_screenshot.png)

## Fonctionnalités

- Interface graphique simple avec Tkinter.
- Génération audio multi-locuteurs.
- Paramètres de voix personnalisables et sauvegardés.
- Lecture et arrêt de l'audio généré directement depuis l'application.
- Accès direct au fichier généré via le gestionnaire de fichiers du système.
- Gestion intelligente de la clé API (demandée une seule fois et sauvegardée de manière sécurisée).

## Installation

### Pour les utilisateurs (Recommandé)

1.  Allez dans l'onglet **"Releases"** (ou "Tags") de ce dépôt.
2.  Téléchargez la dernière version pour votre système d'exploitation (par exemple, `Podcast-Generator-v1.0-macOS.zip`).
3.  Décompressez le fichier `.zip`.
4.  Double-cliquez sur l'application `Podcast Creator`.
5.  Au premier lancement, une fenêtre vous demandera de fournir votre clé API Google Gemini. Collez-la et c'est tout !

### Pour les développeurs

#### 1. Prérequis

- Python 3.9+
- Git

#### 2. Installation et Lancement

```sh
# Clonez le dépôt (remplacez l'URL par celle de votre dépôt)
git clone https://gitea.gandulf78.synology.me/laurent/Podcast_creator.git
cd Podcast_creator

# Créez et activez un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Sur macOS/Linux
# .\.venv\Scripts\activate  # Sur Windows

# Installez les dépendances
pip install -r requirements.txt

# Lancez l'application
python gui.py
```

### 3. Configuration

Créez un fichier nommé `.env` à la racine du projet et ajoutez votre clé API Gemini :

```
GEMINI_API_KEY="VOTRE_CLE_API_ICI"
```

### 4. Lancement de l'application

```sh
python gui.py
```

### 4. Création de l'exécutable

```sh

sips -s format icns podcast.png --out podcast.icns # Convertir l'image en format .icns
# Installez PyInstaller si ce n'est pas déjà fait
pip install pyinstaller
pyinstaller --name="Podcast Generator" --windowed --icon=podcast.icns gui.py
```