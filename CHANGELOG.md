# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.0b26]

### Changed
- **Voice Display Format**: Improved ElevenLabs voice display to match Gemini's tag-based format
  - Changed from `Name - Long Description` to `Name (gender, age, Accent, use_case)` format
  - Only accent is capitalized, other tags are lowercase for consistency with Gemini voices
  - Full descriptions remain available as tooltips in the web interface
- **Voice Classifications**: Enhanced Gemini voice catalog with enriched metadata
  - Voice guide now displays complete classification data (gender, age_group, accent, speaking_style)
  - Loads data from `voice_classifications.json` for detailed voice information
  - Improved voice selection experience with more informative descriptions

### Fixed
- **Desktop App - Voice Selection**: Fixed frozen ElevenLabs voice dropdown menus in settings window
  - Added "Loading..." placeholder to indicate when voices are being fetched
  - Improved `update_elevenlabs_comboboxes()` to properly refresh dropdown values
  - Dropdowns now respond immediately without requiring "Restore Defaults" workaround
  - Added comprehensive logging to track voice loading process
- **Web Interface**: Eliminated transient validation error message on initial page load
  - Deferred script preview validation until after settings are fully loaded
- **UI Alignment**: Left-aligned voice descriptions in voice guide for both providers

## [2.0.0b1-b25]

### Added
- **Web Interface**: Complete Flask-based web interface for podcast generation
  - Access the app from any browser (desktop and web share the same settings)
  - Stop generation in progress from the UI
  - Real-time generation status tracking
- **Docker Support**: Run as a containerized web service
  - Pre-built images available on Docker Hub (gandulf78/podcast_generator)
  - Simple deployment with Docker Compose
  - No installation required - runs on any platform with Docker
- **WhisperX Demo Generation**: Create interactive HTML demos with word-level highlighting
  - Karaoke-style synchronized transcript highlighting
  - Dark mode support
  - Mobile-responsive design
  - Optional feature: `pip install .[demo]`
- **Stop Generation**: Ability to cancel podcast generation in progress
  - Works in both desktop and web interface
  - Clean cancellation with file cleanup
- **Audio Feedback**: Sound notifications for generation results
  - Success "ding" when generation completes
  - Failure "gong" on errors
- **Voice Preview System**: Listen to voices before selecting them
  - Voice guide with play/pause controls for all voices
  - 30 Gemini voice samples included
  - Voice classifications showing gender, age, accent, and style
- **Voice Metadata**: Detailed voice information for better selection
  - Age group, accent, speaking style for all voices
  - Searchable and filterable voice catalog

### Changed
- **Modern UI**: Upgraded to CustomTkinter with dark mode support
- **Improved Demo Generation**: Switched from Montreal Forced Aligner to WhisperX for better accuracy
- **Better Voice Display**: More informative voice descriptions with metadata tags

### Fixed
- **Security**: Prevented sensitive API key information from appearing in logs
- **Windows**: Dark mode detection and better subprocess handling
- **macOS**: Improved menu bar integration
- **Voice Loading**: Fixed race conditions and improved error handling

## [1.4.8] - 2024-08-14

### Changed
- **Build System**: Finalized the build configuration by adding the auto-generated `_version.py` file to `.gitignore`. This prevents the version file, which changes with each commit, from being tracked in version control.
- **Documentation**: Added a warning in the README files (English and French) to emphasize that speaker names in the script must exactly match those in the voice settings.
- **macOS**: Fixing about dialog on macOS to ensure it displays correctly.

### Fixed
- **macOS**: Fixed a startup crash on systems with an older version of the Tcl/Tk library (common with pyenv) by providing a fallback for native menu roles.

## [1.4.7] - 2024-08-13

### Added
- **Command-Line Interface (CLI) Overhaul**:
  - The application can now be fully controlled from the command line.
  - Added the ability to pass a script file as a required argument.
  - Added an optional `-o` / `--output` flag to specify the output file or directory.
  - By default, the output is now saved in the same directory as the input script.
  - The CLI now intelligently handles directory paths, creating the output file with the correct name inside.
- **GUI Enhancements**:
  - Added a splash screen to improve user experience on startup.
  - Added a "Buy Me a Coffee" support link in the "About" window.
  - Added a clickable link to the Gemini API page in the welcome dialog to simplify key retrieval.
  - Added a clickable link to Flaticon in the "About" window for proper attribution.

### Changed
- **Dependency Management**:
  - Centralized all project dependencies in `pyproject.toml` and removed the redundant `requirements.txt` file.
- **Developer Workflow**:
  - Simplified the development setup to a single command: `pip install -e .[dev]`.
  - Completely rewrote `DEVELOPERS.md` and `DEVELOPERS-fr.md` to reflect the new, simpler process for contribution and release.
  - Improved the `release.yml` GitHub Actions workflow for better clarity and reliability.
- **Documentation**:
  - Improved `README.md` in English and `README-fr.md` in French.

### Fixed
- **GUI and UX**:
  - Removed the visual focus outline on buttons in dialog windows for a cleaner look.
- **CLI**:
  - Fixed a crash that occurred in CLI mode when the output file was in the root directory.
- **Cross-Platform**:
  - Improved the reliability of the "Open file location" feature on Windows, especially for paths with spaces.

## [1.4.4] - 2024-08-10

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
