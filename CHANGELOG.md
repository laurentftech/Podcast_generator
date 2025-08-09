# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

## [Unreleased]

### Added
- Ajout d'un fichier `CHANGELOG.md` pour suivre l'historique des versions.

## [1.4.4] - 2024-08-10

### Fixed
- Correction d'un bug qui affichait une version de développement (ex: `.dev0+g...`) même après la création d'un tag Git, en ajoutant un fichier `.gitignore` pour ignorer les fichiers de build.

## [1.4.3] - 2024-08-09

### Added
- Mise en place d'un système de versioning automatique basé sur les tags Git avec `setuptools-scm`.
- La version de l'application s'affiche désormais dans le titre de la fenêtre et dans la boîte de dialogue "À propos".