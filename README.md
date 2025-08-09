# Créateur de Podcast

Une application de bureau simple mais puissante, développée en Python avec Tkinter, qui permet de créer un podcast audio multi-locuteurs à partir d'un script texte en utilisant l'API de synthèse vocale de [Google Gemini](https://ai.google.dev/).

![Capture d'écran de l'application](podcast_creator_screenshot.png)

---

## ✨ Fonctionnalités

- Interface graphique simple avec Tkinter.
- Génération audio multi-locuteurs via l'API Google Gemini.
- Exportation audio au format **MP3** (par défaut) ou **WAV**.
- Paramètres de voix personnalisables et sauvegardés.
- Lecture et arrêt de l'audio généré directement depuis l'application (via FFmpeg/ffplay).
- Accès direct au fichier généré via le gestionnaire de fichiers du système.
- Gestion de la clé API : demandée une seule fois et **sauvegardée de manière sécurisée** dans le trousseau natif du système (Keychain sur macOS, etc.).

---

## 📦 Installation (pour les utilisateurs)

### 1. Dépendance Externe : FFmpeg (Requis)

Pour la conversion et la lecture audio, cette application nécessite que **FFmpeg** soit installé sur votre système.

Sur macOS, le moyen le plus simple de l'installer est via [Homebrew](https://brew.sh/index_fr) :

```sh
brew install ffmpeg
```
Sur Windows ou Linux, téléchargez-le depuis le [site officiel de FFmpeg](https://ffmpeg.org/download.html) et assurez-vous qu'il est accessible dans le PATH.

---

### 2. Pour les utilisateurs (Application prête à l'emploi)

1.  Allez dans l'onglet **"Releases"** (ou "Tags") de ce dépôt.
2.  Téléchargez la dernière version pour votre système d'exploitation.
3.  Décompressez le fichier `.zip`.
4.  Déplacez l'application `Podcast Creator.app` (ou équivalent Windows/Linux) dans le dossier de votre choix.

#### Note importante pour macOS

L'application n'étant pas signée via l'App Store, macOS affichera un avertissement. Suivez l'une de ces méthodes selon votre version de macOS :

**Méthode 1 : Clic droit**
1.  Faites un **clic droit** (ou Ctrl-clic) sur l'icône de `Podcast Creator`.
2.  Sélectionnez **"Ouvrir"**.
3.  Cliquez sur **"Ouvrir"** dans la boîte de dialogue.

**Méthode 2 : Réglages Système**
1.  Essayez d'ouvrir l'application normalement (double-clic).
2.  Dans **Réglages Système → Confidentialité et sécurité**, autorisez l'ouverture.

Cette opération est à faire une seule fois.

#### Premier Lancement : Clé API

Lors du premier démarrage, saisissez votre **clé API Google Gemini** ([obtenir une clé](https://ai.google.dev/tutorials/setup)). Elle sera sauvegardée de manière sécurisée.

---

### 3. Pour les développeurs (Depuis le code source)

#### Prérequis
- Python 3.9+
- Git
- FFmpeg

#### Installation et lancement
```sh
# 1. Clonez le dépôt
git clone https://gitea.gandulf78.synology.me/laurent/Podcast_creator.git
cd Podcast_creator

# 2. Créez un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# 3. Installez les dépendances
pip install -r requirements.txt

# 4. Lancez l'application
python gui.py
```

#### Configuration
Créez un fichier `.env` à la racine :
```
GEMINI_API_KEY="VOTRE_CLE_API_ICI"
```

#### Création d’un exécutable
```sh
sips -s format icns podcast.png --out podcast.icns
pip install pyinstaller
pyinstaller --name="Podcast Generator" --windowed --icon=podcast.icns gui.py
```

---

## 💡 Exemple d’utilisation

Script texte :
```
Locuteur_1: Bonjour et bienvenue dans notre podcast !
Locuteur_2: Aujourd'hui, nous allons parler d'intelligence artificielle.
```
Locuteur_1 et Locuteur_2 seront reconnus comme deux voix distinctes, à configurer dans Options / Paramètres de voix...
Résultat : un fichier MP3 ou WAV avec deux voix distinctes.

---

## 🛠 Compatibilité

- macOS (testé)
- Windows (prévoir FFplay dans le PATH pour lecture intégrée)
- Linux (supporté, dépendances identiques à macOS)

---

## 📜 Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus d’informations.

---

## 🤝 Contribuer

1. Forkez le dépôt
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Committez vos changements : `git commit -m "Ajout de ma fonctionnalité"`
4. Poussez la branche : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

---

## 🐞 Bugs connus / Limitations
- Nécessite une connexion Internet pour générer l'audio.
- Pas encore de support pour la synthèse hors ligne.

---

**Auteur** : Laurent FRANCOISE
**Contact** : laurent.francoise@gmail.com
