# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [Unreleased]

### Added
- Ajout d'un écran de démarrage (splash screen) pour améliorer l'expérience au lancement.
- Ajout d'un fichier `CHANGELOG.md` pour suivre l'historique des versions.
- Ajout d'un lien de soutien "Buy Me a Coffee" dans la fenêtre "À propos".
- Amélioration README.md en Anglais et README-fr.md en Français

## [1.4.4] - 2024-08-10

### Fixed
- Correction d'un bug qui affichait une version de développement (ex: `.dev0+g...`) même après la création d'un tag Git, en ajoutant un fichier `.gitignore` pour ignorer les fichiers de build.

## [1.4.3] - 2024-08-09

### Added
- Mise en place d'un système de versioning automatique basé sur les tags Git avec `setuptools-scm`.
- La version de l'application s'affiche désormais dans le titre de la fenêtre et dans la boîte de dialogue "À propos".

## [1.4.0] - 2024-08-09

### Added
- Ajout de la lecture audio intégrée via `ffplay` directement depuis l'interface.
- Ajout d'un bouton "Ouvrir le dossier" pour révéler le fichier généré dans le gestionnaire de fichiers du système.
- Ajout d'une barre de progression visuelle pendant la génération audio.
- Ajout d'une fenêtre "À propos" et d'un lien vers la documentation dans le menu.
### Changed
- Amélioration de la robustesse de la génération audio avec une tentative de fallback sur un modèle secondaire en cas d'échec du modèle principal.

## [1.3.0] - 2024-08-09

### Added
- Mise en place d'un système de gestion de clé API sécurisé utilisant le trousseau natif du système (`keyring`).
- La clé API n'est demandée qu'une seule fois et est stockée de manière sécurisée.
### Changed
- Le fichier `.env` à la racine du projet est maintenant réservé uniquement au développement local.

## [1.2.0] - 2024-08-09

### Added
- Ajout d'une fenêtre de "Paramètres des voix" permettant aux utilisateurs de définir et de sauvegarder leurs propres paires locuteur/voix.
- Les paramètres sont sauvegardés dans un fichier `settings.json` dans le dossier de l'application.
- Ajout d'un bouton pour restaurer les paramètres par défaut.

## [1.0.0] - 2024-08-09

### Added
- Version initiale du Créateur de Podcast.
- Interface graphique simple construite avec Tkinter.
- Génération de podcast multi-locuteurs via l'API Google Gemini.
- Exportation des fichiers audio aux formats MP3 et WAV.
- Affichage des logs de génération dans l'interface.
- Possibilité de charger un script depuis un fichier texte.
