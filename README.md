# Créateur de Podcast

Une application de bureau simple mais puissante, développée en Python avec Tkinter, qui permet de créer un podcast audio multi-locuteurs à partir d'un script texte en utilisant l'API de synthèse vocale de [Google Gemini](https://ai.google.dev/).

![Capture d'écran de l'application](podcast_creator_screenshot.png)

---

## ✨ Fonctionnalités

- **Génération Audio** : Créez des podcasts multi-locuteurs en utilisant les voix de haute qualité de l'API Google Gemini.
- **Interface Simple** : Une interface graphique intuitive construite avec Tkinter.
- **Formats Flexibles** : Exportez vos créations au format **MP3** (par défaut) ou **WAV**.
- **Personnalisation** : Configurez et sauvegardez les voix pour chaque locuteur de vos scripts.
- **Lecture Intégrée** : Écoutez et arrêtez la lecture de l'audio directement depuis l'application (nécessite FFmpeg).
- **Gestion Sécurisée** : Votre clé API est demandée une seule fois et stockée de manière sécurisée dans le trousseau natif de votre système (`keyring`).
- **Versioning Automatique** : La version de l'application est automatiquement synchronisée avec les tags Git du projet.

---

## 📦 Installation

### 1. Dépendance Externe : FFmpeg (Requis)

Pour la conversion et la lecture audio, cette application nécessite que **FFmpeg** soit installé sur votre système.

Sur macOS, le moyen le plus simple de l'installer est via Homebrew :
```sh
brew install ffmpeg
```
Windows / Linux : [Télécharger depuis le site officiel](https://ffmpeg.org/download.html) et ajouter au PATH.

---

### 2. Pour les utilisateurs (Application prête à l'emploi)

1.  Allez dans l'onglet **"Releases"** ou **"Tags"**.
2.  Téléchargez la version correspondant à votre OS.
3.  Décompressez le `.zip`.
4.  Placez l'application dans le dossier de votre choix.

#### Note macOS

macOS affichera un avertissement au premier lancement (application non signée).  

**Méthode rapide** :
1. Clic droit sur l'icône → **Ouvrir** → **Ouvrir**.

**Méthode via réglages** :
1. Double-clic (message d’erreur).
2. **Réglages Système → Confidentialité et sécurité** → **Ouvrir quand même**.

#### Premier Lancement : Clé API
L’application demandera votre clé API Google Gemini lors du premier lancement. Elle sera sauvegardée de manière sécurisée.

---

### 3. Pour les développeurs (Depuis le code source)

#### Installation rapide
```sh
# Clone du dépôt
git clone https://gitea.gandulf78.synology.me/laurent/Podcast_creator.git
cd Podcast_creator

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# Dépendances
pip install -r requirements.txt

# Lancement
python gui.py
```

#### Configuration
Créer un fichier `.env` à la racine :
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

## 🚀 Workflow de publication

Voir le fichier [`DEVELOPERS.md`](DEVELOPERS.md) pour la procédure complète de publication, y compris la création d'exécutables et la gestion des versions.

---

## 💡 Exemple d’utilisation

Script texte :
```
Locuteur_1: Bonjour et bienvenue dans notre podcast !
Locuteur_2: Aujourd'hui, nous allons parler d'intelligence artificielle.
```
Résultat : un fichier MP3 ou WAV avec deux voix distinctes, configurées dans **Options → Paramètres de voix**.

---

## 🛠 Compatibilité

- macOS (testé)
- Windows (prévoir FFplay dans le PATH pour lecture intégrée)
- Linux (mêmes dépendances que macOS)

---

## 📜 Licence

Projet distribué sous licence MIT — voir le fichier `LICENSE`.

---

## 🤝 Contribuer

1. Forkez le dépôt
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Commit : `git commit -m "Ajout de ma fonctionnalité"`
4. Push : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

---

## 🐞 Bugs connus / Limitations
- Connexion Internet obligatoire
- Pas encore de support pour la synthèse hors ligne

---

## 👤 Auteur

**Laurent FRANCOISE**  
📧 laurent.francoise@gmail.com
