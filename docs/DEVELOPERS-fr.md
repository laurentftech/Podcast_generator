# Podcast Generator - Guide pour les développeurs

Ce document décrit les étapes nécessaires pour contribuer, tester et préparer une nouvelle version de Podcast Generator.

⚠️ **Important** : La génération des exécutables (macOS, Windows, Linux) et leur publication dans les releases **est entièrement automatisée** via le workflow GitHub Actions `release.yml`.  
Seul le propriétaire du dépôt (Laurent) peut déclencher cette génération et publier officiellement une version.

---

## 📋 Prérequis

- Python 3.9+ (3.11 ou 3.12 recommandé)
- Git
- FFmpeg installé et accessible dans le PATH
- Accès au dépôt Git (droits de push requis pour préparer une release)

---

## ⚙️ Installation de l'environnement de développement

```sh
# 1. Cloner le dépôt
git clone https://github.com/laurentftech/Podcast_generator.git
cd Podcast_generator

# 2. Créer et activer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# 3. Installer les dépendances
# Le drapeau '-e' installe le projet en mode "éditable".
pip install -e .[dev]

# 4. Lancer l'application
python gui.py
```

---

## 📦 Compiler l'application localement

Le projet utilise un fichier `Podcast Generator.spec` pour contrôler le processus de compilation. Cela garantit la cohérence sur toutes les plateformes et automatise l'injection de la version.

### Étapes de compilation

1.  **Nettoyage (Recommandé)** : Avant de compiler, il est bon de supprimer les anciens artefacts de build pour éviter les problèmes de cache.
    ```sh
    rm -rf build/ dist/ _version.py
    ```

2.  **Installer les dépendances**: Cette étape génère également le fichier `_version.py` nécessaire à la compilation.
    ```sh
     pip install -e .[dev]
    ```

3.  **Lancer PyInstaller**: Utilisez le fichier `.spec` pour compiler l'application.
    ```sh
    python -m PyInstaller "Podcast Generator.spec"
    ```

L'exécutable final se trouvera dans le dossier `dist`.

---

### Étape 1. Préparer la version

- **Mettre à jour le Changelog** : Éditer manuellement CHANGELOG.md pour ajouter la nouvelle version et la liste des changements.
- **Tests finaux** : Vérifier que toutes les fonctionnalités sont testées et fonctionnent correctement.
- **Dépôt propre** : S’assurer que le répertoire de travail est propre (git status ne doit afficher aucun changement non validé).

Seul Laurent peut **publier une release officielle**, mais toute personne ayant les droits d’écriture peut préparer le code.

### Étape 2. Commit, Tag et Push (Responsabilité de Laurent)

```sh
git add .
git commit -m "Préparation version vX.Y.Z"
git tag -a vX.Y.Z -m "Version X.Y.Z"
git push origin main
git push origin vX.Y.Z
```

Une fois le tag vX.Y.Z poussé, le workflow GitHub Actions release.yml :
- Génère automatiquement l’application pour toutes les plateformes
- Crée une nouvelle release GitHub
- Y attache toutes les archives .tar.gz correspondantes

Aucune compilation manuelle n’est nécessaire.

---

## 🤝 Contribution

- Fork du dépôt  
- Créer une branche :  
  ```sh
  git checkout -b feature/ma-fonctionnalite
  ```
- Développer et tester les changements  
- Commit :  
  ```sh
  git commit -m "Ajout de ma fonctionnalité"
  ```
- Push :  
  ```sh
  git push origin feature/ma-fonctionnalite
  ```
- Ouvrir une Pull Request

---

## 🛠 Conseils de développement

- Respecter la structure et le style du code existant
- Utiliser des noms de variables explicites
- Documenter les nouvelles fonctions avec des docstrings
- Faire des commits clairs et atomiques
- Tester sur macOS, Windows et Linux

---

## 📜 Licence

Les contributions sont acceptées sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
