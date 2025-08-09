# Créateur de Podcast - Guide pour les développeurs

Ce document décrit les étapes nécessaires pour contribuer, tester, builder et publier une nouvelle version de Créateur de Podcast.

## 📋 Prérequis

- Python 3.9+ (3.11 ou 3.12 recommandé)
- Git
- FFmpeg installé et accessible dans le PATH
- PyInstaller pour la génération d'exécutables
- Accès au dépôt Git (droits de push pour la publication)

## ⚙️ Installation de l'environnement de développement

```sh
# 1. Cloner le dépôt
git clone https://gitea.gandulf78.synology.me/laurent/Podcast_creator.git
cd Podcast_creator

# 2. Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -r requirements.txt
pip install -e .  # mode développement

# 4. Lancer l'application
python gui.py
```

## 🧪 Tests
Pour le moment, il n'y a pas de suite de tests automatisés.
Les tests se font manuellement en lançant l'application et en vérifiant le comportement des fonctionnalités.

## 🚀 Workflow complet pour créer une nouvelle version

### 1. Préparer la version
    Mettre à jour le changelog (CHANGELOG.md)
    Mettre à jour le numéro de version dans le code source (__version__ si défini)
    
### 2. Taguer la version

```sh
git add .
git commit -m "Préparation version vX.Y.Z"
git tag -a vX.Y.Z -m "Version X.Y.Z"
git push origin main
git push origin vX.Y.Z
```

### 3. Générer l'exécutable
#### Créer l'icône .icns depuis un PNG (macOS uniquement)
```sh
sips -s format icns podcast.png --out podcast.icns
```

#### Installer PyInstaller si besoin
```sh
pip install pyinstaller
```

#### Générer l'exécutable
```sh
pyinstaller --name="Podcast Generator" --windowed --icon=podcast.icns gui.py
```

### 4. Tester l'exécutable

macOS : open dist/Podcast\ Generator.app
Windows : double-cliquer sur dist/Podcast Generator.exe
Linux : ./dist/Podcast\ Generator

### 5. Nettoyer les fichiers temporaires
```sh
rm -rf build dist __pycache__ *.spec podcast.icns
```

### 6. Créer un zip de distribution
```sh
zip -r Podcast_Generator_vX.Y.Z.zip dist/Podcast\ Generator.app
# ou version Windows
zip -r Podcast_Generator_vX.Y.Z.zip dist/Podcast\ Generator.exe
```

### 7. Publier sur Gitea
Aller dans Releases
Sélectionner le tag vX.Y.Z
Ajouter le fichier ZIP généré
Renseigner la description de la release


# 🤝 Contribution
Fork du dépôt
Créer une branche : git checkout -b feature/ma-fonctionnalite
Développer et tester les changements
Commit : git commit -m "Ajout de ma fonctionnalité"
Push : git push origin feature/ma-fonctionnalite
Ouvrir une Pull Request

# 🛠 Conseils de développement
Respecter la structure du code existant
Utiliser des noms de variables explicites
Documenter les nouvelles fonctions avec des docstrings
Faire des commits atomiques et clairs
Tester la compatibilité sur macOS, Windows et Linux

# 📜 Licence
Les contributions sont acceptées sous licence MIT.
