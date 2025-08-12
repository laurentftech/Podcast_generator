# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Added a splash screen to improve user experience on startup.
- Added a `CHANGELOG.md` file to track version history.
- Added a "Buy Me a Coffee" support link in the "About" window.
- Improved `README.md` in English and `README-fr.md` in French.

## [1.4.4] - 2024-08-10

### Fixed
- Fixed a bug that displayed a development version (e.g., `.dev0+g...`) even after creating a Git tag, by adding a `.gitignore` file to ignore build artifacts.

## [1.4.3] - 2024-08-09

### Added
- Implemented an automatic versioning system based on Git tags using `setuptools-scm`.
- The application version is now displayed in the window title and the "About" dialog.

## [1.4.0] - 2024-08-09

### Added
- Added integrated audio playback via `ffplay` directly from the interface.
- Added an "Open file location" button to reveal the generated file in the system's file manager.
- Added a visual progress bar during audio generation.
- Added an "About" window and a link to the documentation in the menu.
### Changed
- Improved audio generation robustness with a fallback to a secondary model in case the primary one fails.

## [1.3.0] - 2024-08-09

### Added
- Implemented a secure API key management system using the native system keychain (`keyring`).
- The API key is requested only once and stored securely.
### Changed
- The `.env` file at the project root is now reserved for local development only.

## [1.2.0] - 2024-08-09

### Added
- Added a "Voice Settings" window allowing users to define and save their own speaker/voice pairs.
- Settings are saved to a `settings.json` file in the application's data directory.
- Added a button to restore default settings.

## [1.0.0] - 2024-08-09

### Added
- Initial version of Podcast Generator.
- Simple graphical interface built with Tkinter.
- Multi-speaker podcast generation via the Google Gemini API.
- Audio file export in MP3 and WAV formats.
- Display of generation logs in the interface.
- Ability to load a script from a text file.
