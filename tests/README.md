# Tests for Podcast Generator

This directory contains automated tests for the Podcast Generator application.

## Test Statistics

**Total Tests: 85** ✅ **All Passing**

- API Endpoints: 11 tests
- API Status: 5 tests
- Filename Extraction: 20 tests
- Gemini Model Selection: 4 tests
- Utility Functions: 25 tests (18 core + 7 extra)
- Validation: 13 tests
- Integration: 2 tests (requires API keys)
- Demo Creation: 7 tests

## Running Tests

### Install Test Dependencies

First, install the development dependencies including pytest:

```bash
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest
# or with verbose output
pytest -v
```

### Run Specific Test Files

```bash
# Test API endpoints
pytest tests/test_api_endpoints.py -v

# Test API status endpoint
pytest tests/test_api_status.py -v

# Test Gemini model selection
pytest tests/test_gemini_model.py -v

# Test utility functions
pytest tests/test_utils.py -v
pytest tests/test_utils_extra.py -v

# Test validation
pytest tests/test_validation.py -v

# Test filename extraction
pytest tests/test_filename_extraction.py -v

# Test demo creation logic
pytest tests/test_create_demo.py -v

# Test integration with real APIs (requires keys)
pytest tests/test_integration.py -v
```

### Run Specific Test Cases

```bash
pytest tests/test_api_status.py::TestAPIStatusEndpoint::test_status_returns_gemini_default_model -v
```

### Run Tests with Coverage

```bash
# Generate coverage report in terminal
pytest --cov=. --cov-report=term-missing tests/

# Generate HTML coverage report (opens in browser)
pytest --cov=. --cov-report=html tests/
# Then open htmlcov/index.html in your browser
```

**Coverage Statistics:**
- **Core Modules**: ~45% coverage (focused on testable backend logic)
- **Excluded**: GUI modules, voice classifier
- **Test Files**: 100% coverage on all test utilities

## Integration Tests & GitHub Secrets

The `tests/test_integration.py` file contains tests that hit the real Gemini and ElevenLabs APIs. These tests are skipped by default if API keys are not present.

To run these tests in GitHub Actions, you must configure the following **Repository Secrets**:

- `GEMINI_API_KEY`: Your Google Gemini API key
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key

To run them locally, ensure you have a `.env` file in the project root with these keys defined.

## Test Coverage

### test_integration.py (2 tests)

Tests actual API calls (skipped if keys missing):
- **test_gemini_integration**: Generates a short audio using Gemini
- **test_elevenlabs_integration**: Generates a short audio using ElevenLabs

### test_create_demo.py (7 tests)

Tests logic for HTML demo generation:
- **test_normalize_word**: Verifies word normalization
- **test_similar**: Verifies fuzzy string matching
- **test_find_adjacent_timed_words**: Verifies finding neighbors for interpolation
- **test_interpolate_missing_words**: Verifies timing interpolation logic
- **test_fix_word_timings_inverted**: Verifies fix for start > end
- **test_fix_word_timings_overlap**: Verifies fix for overlapping words
- **test_reconstruct_html_with_timing**: Verifies HTML output structure
- **test_create_word_mapping_whisperx_simple**: Verifies basic mapping
- **test_create_word_mapping_whisperx_with_speaker**: Verifies speaker label handling

### test_utils_extra.py (7 tests)

Additional tests for `utils.py`:
- **test_sanitize_text_***: Various tests for text sanitization (HTML entities, smart quotes, control chars)
- **test_sanitize_app_settings_***: Tests for settings sanitization before backend use

### test_api_endpoints.py (11 tests)

Tests for various Flask API endpoints:

**TestAboutEndpoint:**
- **test_about_returns_version**: Verifies `/api/about` returns version information

**TestSettingsEndpoints:**
- **test_get_settings**: Verifies `GET /api/settings` returns current settings
- **test_get_settings_shows_missing_keys**: Verifies missing API keys are indicated
- **test_post_settings_updates_provider**: Verifies `POST /api/settings` updates TTS provider
- **test_post_settings_updates_speaker_voices**: Verifies speaker voices can be updated
- **test_post_settings_invalid_format**: Verifies invalid JSON is rejected
- **test_post_settings_strips_has_key_flags**: Verifies internal flags aren't saved

**TestVoicesEndpoint:**
- **test_voices_returns_gemini_voices**: Verifies Gemini voices are returned
- **test_voices_returns_elevenlabs_when_key_set**: Verifies ElevenLabs voices with API key
- **test_voices_empty_elevenlabs_when_no_key**: Verifies empty list without API key
- **test_voices_handles_elevenlabs_error**: Verifies graceful error handling

### test_api_status.py (5 tests)

Tests for the `/api/status` Flask endpoint that displays TTS provider and model information:

- **test_status_returns_gemini_default_model**: Verifies that the default Gemini model (`gemini-2.5-pro-preview-tts`) is returned when no environment variable is set
- **test_status_returns_gemini_custom_model**: Verifies that a custom model from `GEMINI_TTS_MODEL` environment variable is returned
- **test_status_returns_elevenlabs_model**: Verifies that "Eleven v3" is returned for ElevenLabs provider
- **test_status_elevenlabs_without_api_key**: Tests proper handling when ElevenLabs API key is missing
- **test_status_with_different_gemini_models**: Tests that different Gemini model configurations are correctly reflected in the API response

### test_filename_extraction.py (20 tests)

Tests for the `extract_filename_from_script()` function:

- **test_extract_from_simple_dialogue**: Verifies basic filename extraction
- **test_extract_skips_instruction_lines**: Verifies instruction lines are skipped
- **test_extract_uses_first_dialogue_line**: Verifies only first dialogue is used
- **test_extract_removes_bracketed_annotations**: Verifies [emotion] tags are removed
- **test_extract_limits_to_first_sentence**: Verifies sentence boundary detection
- **test_extract_respects_max_length**: Verifies length limiting
- **test_extract_removes_unsafe_characters**: Verifies filesystem-unsafe characters removed
- **test_extract_replaces_spaces_with_underscores**: Verifies space replacement
- **test_extract_replaces_multiple_spaces**: Verifies space collapsing
- **test_extract_strips_leading_trailing_underscores**: Verifies trimming
- **test_extract_fallback_for_empty_script**: Verifies UUID fallback
- **test_extract_fallback_for_no_dialogue**: Verifies fallback for non-dialogue scripts
- **test_extract_fallback_for_only_special_characters**: Verifies fallback for special chars
- **test_extract_different_extensions**: Verifies extension handling (mp3, docx, wav)
- **test_extract_with_question_mark_punctuation**: Verifies ? as sentence boundary
- **test_extract_with_exclamation_punctuation**: Verifies ! as sentence boundary
- **test_extract_preserves_alphanumeric**: Verifies numbers and letters preserved
- **test_extract_handles_unicode_characters**: Verifies unicode handling
- **test_extract_with_empty_speaker_dialogue**: Verifies empty dialogue handling
- **test_extract_with_malformed_brackets**: Verifies graceful handling of malformed input

### test_gemini_model.py (4 tests)

Tests for the GeminiTTS class model selection logic:

- **test_default_model_is_pro**: Verifies that `gemini-2.5-pro-preview-tts` is used as the default model
- **test_custom_model_from_env**: Verifies that a custom model from environment variable is used correctly
- **test_model_fallback_order**: Verifies that models are tried in the correct fallback order
- **test_models_to_try_list_uniqueness**: Ensures that when the custom model equals the default, it's not duplicated in the fallback list

### test_utils.py (18 tests)

Tests for utility functions in `utils.py`:

**TestSanitizeText:**
- **test_sanitize_empty_string**: Verifies empty/None handling
- **test_remove_html_tags**: Verifies HTML tag removal
- **test_decode_html_entities**: Verifies HTML entity decoding (&nbsp;, &amp;)
- **test_normalize_unicode**: Verifies unicode normalization
- **test_replace_smart_quotes**: Verifies smart quote replacement
- **test_replace_special_dashes**: Verifies em-dash and en-dash replacement
- **test_remove_control_characters**: Verifies control character removal
- **test_preserve_newlines**: Verifies newlines are preserved
- **test_reduce_multiple_spaces**: Verifies space collapsing
- **test_strip_leading_trailing_spaces**: Verifies whitespace trimming
- **test_complex_mixed_content**: Verifies combined sanitization operations

**TestSanitizeAppSettings:**
- **test_sanitize_gemini_voices_with_description**: Verifies description removal from Gemini voices
- **test_sanitize_gemini_voices_without_description**: Verifies voices without descriptions
- **test_sanitize_elevenlabs_voices_dict_format**: Verifies ElevenLabs dict extraction
- **test_sanitize_elevenlabs_voices_legacy_string_format**: Verifies legacy format
- **test_sanitize_preserves_tts_provider**: Verifies provider preservation
- **test_sanitize_handles_missing_keys**: Verifies graceful handling of missing keys
- **test_sanitize_handles_malformed_voice_data**: Verifies malformed data handling

### test_validation.py (13 tests)

Tests for the `validate_speakers()` function:

- **test_validate_all_speakers_configured**: Verifies validation when all speakers configured
- **test_validate_missing_speakers**: Verifies detection of missing speakers
- **test_validate_empty_script**: Verifies empty script handling
- **test_validate_script_without_speakers**: Verifies plain text handling
- **test_validate_gemini_too_many_speakers**: Verifies Gemini 2-speaker limit error
- **test_validate_gemini_two_speakers_allowed**: Verifies Gemini allows 2 speakers
- **test_validate_gemini_one_speaker_allowed**: Verifies Gemini allows 1 speaker
- **test_validate_elevenlabs_many_speakers**: Verifies ElevenLabs multi-speaker support
- **test_validate_elevenlabs_uses_correct_settings_key**: Verifies correct settings key usage
- **test_validate_duplicate_speaker_names**: Verifies duplicate speaker handling
- **test_validate_speaker_with_whitespace**: Verifies whitespace trimming
- **test_validate_multiline_dialogue**: Verifies continuation line handling
- **test_validate_case_sensitive_speaker_names**: Verifies case sensitivity

## Test Fixtures

### temp_settings_dir

Creates a temporary directory for settings files during tests, ensuring tests don't modify the actual application settings.

### clean_env

Cleans up environment variables before each test to ensure isolation.

### app

Creates a Flask app instance configured for testing.

### client

Creates a Flask test client for making HTTP requests.

### mock_settings

Creates default settings in the temporary settings directory.

## Writing New Tests

When adding new tests:

1. Use the existing fixtures (`temp_settings_dir`, `clean_env`, `app`, `client`) to ensure test isolation
2. Mock external API calls to avoid making real requests during tests
3. Follow the existing naming conventions (`test_<functionality>`)
4. Add docstrings to explain what each test verifies
5. Group related tests in classes (e.g., `TestAPIStatusEndpoint`)
6. Ensure tests are deterministic and don't depend on external state

## Continuous Integration

These tests should be run as part of the CI/CD pipeline before merging changes or creating releases.

## Test Configuration

Tests are configured via `pytest.ini` in the project root:
- Verbose output by default
- Short traceback format for cleaner output
- Warnings disabled for cleaner test output
- Test discovery patterns configured
