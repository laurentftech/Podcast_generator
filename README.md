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

## Installation et Utilisation

### Pour les utilisateurs (Recommandé)

1.  Allez dans l'onglet **"Releases"** (ou "Tags") de ce dépôt.
2.  Téléchargez la dernière version pour votre système d'exploitation (par exemple, `Podcast-Creator-v1.0-macOS.zip`).
3.  Décompressez le fichier `.zip`.
4.  Déplacez l'application `Podcast Creator.app` dans votre dossier **Applications**.

#### Note importante pour les utilisateurs macOS

Au premier lancement, macOS affichera un message de sécurité car l'application n'est pas distribuée via l'App Store. **Ceci est un comportement normal.**

Pour autoriser l'application, choisissez l'une des deux méthodes suivantes (selon version de macOS) :

**Méthode 1 : Clic droit **
1.  Faites un **clic droit** (ou Ctrl-clic) sur l'icône de `Podcast Creator`.
2.  Sélectionnez **"Ouvrir"** dans le menu.
3.  Une nouvelle fenêtre de dialogue s'ouvrira avec un bouton **"Ouvrir"**. Cliquez dessus.

**Méthode 2 : Réglages Système**
1.  Essayez d'ouvrir l'application en double-cliquant. Un message d'erreur apparaîtra. Cliquez sur **OK**.
2.  Ouvrez les **Réglages Système** de votre Mac.
3.  Allez dans la section **Confidentialité et sécurité**.
4.  Faites défiler vers le bas jusqu'à la section "Sécurité". Vous y verrez un message indiquant que l'ouverture de "Podcast Creator" a été bloquée.
5.  Cliquez sur le bouton **"Ouvrir quand même"**.

Vous n'aurez à effectuer cette manipulation qu'une seule fois.

#### Premier Lancement : Clé API

Au premier démarrage, une fenêtre vous demandera de fournir votre clé API Google Gemini. Collez-la pour pouvoir utiliser l'application. Cette clé sera sauvegardée pour les lancements futurs.

### Pour les développeurs

Cette section vous guide pour lancer l'application depuis le code source.

##### 1. Prérequis

- Python 3.9+
- Git

##### 2. Installation et Lancement

```sh
# 1. Clonez le dépôt
git clone https://gitea.gandulf78.synology.me/laurent/Podcast_creator.git
cd Podcast_creator

# 2. Créez et activez un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Sur macOS/Linux
# .\.venv\Scripts\activate  # Sur Windows

# 3. Installez les dépendances
pip install -r requirements.txt

# 4. Lancez l'application
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