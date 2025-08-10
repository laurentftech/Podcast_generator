# Créateur de Podcast
[![Buy Me a Coffee](https://img.shields.io/badge/Buy_Me_a_Coffee-FFDD00?style=flat&logo=buy-me-a-coffee&logoColor=000000)](https://www.buymeacoffee.com/laurentftech)


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

## ✨ Cas d’usage concrets
- **Création de Podcasts** : Transformez vos scripts en épisodes audio captivants avec des voix distinctes pour chaque personnage.
- **Enseignement et formation** : Transformez vos supports de cours ou tutoriels écrits en podcasts audio dynamiques avec une ou plusieurs voix pour capter l’attention des apprenants.
- **Pratique des langues** : Créez des dialogues multilingues pour les apprenants, avec des voix distinctes pour chaque personnage.
- **Livres audio** : Convertissez des livres ou des articles en format audio, en utilisant différentes voix pour les narrateurs et les personnages.
- **Création de contenu** : Génération rapide de podcasts ou d’épisodes audio à partir de scripts, idéal pour les créateurs qui souhaitent automatiser une partie de leur production.
- **Accessibilité** : Rendez vos documents écrits accessibles aux personnes malvoyantes ou préférant le format audio.

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

## 👨‍💻 Pour les développeurs

Pour contribuer au projet, lancer le code ou créer votre propre version, veuillez consulter le guide complet pour les développeurs :

**➡️ `DEVELOPERS.md`**

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

## 🐞 Bugs connus / Limitations
- Connexion Internet obligatoire
- Pas encore de support pour la synthèse hors ligne

---

## 👤 Auteur

**Laurent FRANCOISE**  
📧 laurent.f.tech@icloud.com  
