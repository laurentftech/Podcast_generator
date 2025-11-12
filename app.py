from flask import Flask, render_template, request, jsonify, send_from_directory
from generate_podcast import generate, PODCAST_SCRIPT, setup_logging, validate_speakers, update_elevenlabs_quota
from utils import sanitize_text, get_asset_path, get_app_data_dir
from config import AVAILABLE_VOICES, DEFAULT_APP_SETTINGS
from create_demo import create_html_demo_whisperx
import os
import tempfile
import json
import requests
import zipfile
import shutil
from elevenlabs.core import ApiError
import re

# --- App Initialization ---
app = Flask(__name__)
logger = setup_logging()

# --- Version & License ---
try:
    from _version import __version__
except ImportError:
    __version__ = "0.0.0-dev"

LICENSE_TEXT = "MIT License..."
try:
    with open('LICENSE', 'r') as f:
        LICENSE_TEXT = f.read()
except FileNotFoundError:
    logger.warning("LICENSE file not found.")


# --- Configuration ---
TEMP_DIR = tempfile.mkdtemp(prefix="podcast_generator_")
DEMOS_DIR = os.path.join(app.instance_path, 'demos')
os.makedirs(DEMOS_DIR, exist_ok=True)
app.config['TEMP_DIR'] = TEMP_DIR
app.config['DEMOS_DIR'] = DEMOS_DIR


def get_settings_path():
    return os.path.join(get_app_data_dir(), "settings.json")

def load_settings():
    try:
        with open(get_settings_path(), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_APP_SETTINGS

def save_settings(settings):
    with open(get_settings_path(), 'w') as f:
        json.dump(settings, f, indent=4)

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html', default_script=PODCAST_SCRIPT)

@app.route('/assets/<path:filename>')
def get_asset(filename):
    assets_dir = get_asset_path('.')
    if not assets_dir:
        return "Assets directory not found", 404
    return send_from_directory(assets_dir, filename)

@app.route('/api/about', methods=['GET'])
def get_about_info():
    return jsonify({'version': __version__, 'license': LICENSE_TEXT})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current TTS provider and quota info."""
    settings = load_settings()
    provider = settings.get("tts_provider", "elevenlabs")
    quota_text = None

    if provider == "elevenlabs":
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if api_key:
            quota_text = update_elevenlabs_quota(api_key)
        else:
            quota_text = "ElevenLabs API Key not set."
    
    provider_display = "ElevenLabs" if provider == "elevenlabs" else "Gemini"

    return jsonify({
        'provider_name': provider_display,
        'quota_text': quota_text
    })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    settings = load_settings()
    settings['has_elevenlabs_key'] = bool(os.environ.get("ELEVENLABS_API_KEY"))
    settings['has_gemini_key'] = bool(os.environ.get("GEMINI_API_KEY"))
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    new_settings = request.json
    if not new_settings:
        return jsonify({'error': 'Invalid settings format.'}), 400
    new_settings.pop('has_elevenlabs_key', None)
    new_settings.pop('has_gemini_key', None)
    current_settings = load_settings()
    current_settings.update(new_settings)
    save_settings(current_settings)
    return jsonify({'status': 'success'})

@app.route('/api/voices', methods=['GET'])
def get_voices():
    gemini_voices = AVAILABLE_VOICES
    elevenlabs_voices = []
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        try:
            headers = {"xi-api-key": api_key}
            response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
            if response.ok:
                elevenlabs_voices = response.json().get('voices', [])
        except requests.RequestException as e:
            logger.error(f"Could not fetch ElevenLabs voices: {e}")
    return jsonify({'gemini': gemini_voices, 'elevenlabs': elevenlabs_voices})

@app.route('/api/gemini_sample/<voice_name>')
def get_gemini_sample(voice_name):
    sample_path = get_asset_path(os.path.join("samples", "gemini_voices"))
    if not sample_path:
        return "Sample directory not found", 404
    return send_from_directory(sample_path, f"{voice_name}.mp3")

@app.route('/generate', methods=['POST'])
def handle_generate():
    script_text = request.form.get('script', '')
    if not script_text:
        return jsonify({'error': 'Script text is required.'}), 400

    sanitized_script = sanitize_text(script_text)
    app_settings = load_settings()

    try:
        missing_speakers, _ = validate_speakers(sanitized_script, app_settings)
        if missing_speakers:
            return jsonify({'error': f"Missing voice configuration for speakers: {', '.join(missing_speakers)}"}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    first_words = re.sub(r'<[^>]+>', '', sanitized_script).strip().split()[:2]
    base_name = "_".join(first_words).lower()
    safe_base_name = re.sub(r'[^a-z0-9_]+', '', base_name)
    if not safe_base_name:
        safe_base_name = "podcast"
    random_suffix = os.urandom(4).hex()
    output_filename = f"{safe_base_name}_{random_suffix}.mp3"
    
    output_filepath = os.path.join(app.config['TEMP_DIR'], output_filename)

    provider = app_settings.get("tts_provider", "elevenlabs")
    api_key_env_var = "ELEVENLABS_API_KEY" if provider == "elevenlabs" else "GEMINI_API_KEY"
    api_key = os.environ.get(api_key_env_var)

    if not api_key:
        return jsonify({'error': f'API key ({api_key_env_var}) not found in environment variables.'}), 500

    from utils import sanitize_app_settings_for_backend
    app_settings_clean = sanitize_app_settings_for_backend(app_settings)

    try:
        generated_file = generate(
            script_text=sanitized_script,
            app_settings=app_settings_clean,
            output_filepath=output_filepath,
            api_key=api_key,
            status_callback=logger.info
        )
        if generated_file:
            return jsonify({'download_url': f'/temp/{output_filename}', 'filename': output_filename})
        else:
            return jsonify({'error': 'Generation failed for an unknown reason. Check server logs.'}), 500
    except ApiError as e:
        error_detail = e.body.get('detail', {})
        message = error_detail.get('message', 'An unknown ElevenLabs API error occurred.')
        logger.error(f"ElevenLabs API Error: {message}")
        return jsonify({'error': f"ElevenLabs Error: {message}"}), 500
    except Exception as e:
        logger.error(f"Error during generation: {e}", exc_info=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/api/generate_demo', methods=['POST'])
def handle_generate_demo():
    data = request.json
    script_text, audio_filename = data.get('script'), data.get('audio_filename')
    title, subtitle = data.get('title', 'Podcast Demo'), data.get('subtitle', '')
    show_credits = data.get('show_credits', True)

    if not script_text or not audio_filename:
        return jsonify({'error': 'Script and audio filename are required.'}), 400

    audio_filepath = os.path.join(app.config['TEMP_DIR'], audio_filename)
    if not os.path.exists(audio_filepath):
        return jsonify({'error': 'Audio file not found on server.'}), 404

    demo_id = os.urandom(8).hex()
    demo_output_dir = os.path.join(app.config['DEMOS_DIR'], demo_id)
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as f:
            f.write(script_text)
            temp_script_file = f.name

        create_html_demo_whisperx(
            script_filepath=temp_script_file,
            audio_filepath=audio_filepath,
            title=title,
            subtitle=subtitle,
            output_dir=demo_output_dir,
            status_callback=logger.info,
            show_credits=show_credits
        )
        
        return jsonify({
            'view_url': f'/demos/{demo_id}/index.html',
            'download_url': f'/api/download_demo/{demo_id}'
        })
    except Exception as e:
        logger.error(f"Error during demo generation: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred during demo generation.'}), 500
    finally:
        if 'temp_script_file' in locals() and os.path.exists(temp_script_file):
            os.remove(temp_script_file)

@app.route('/demos/<demo_id>/<path:filename>')
def serve_demo_file(demo_id, filename):
    demo_dir = os.path.join(app.config['DEMOS_DIR'], demo_id)
    return send_from_directory(demo_dir, filename)

@app.route('/api/download_demo/<demo_id>')
def download_demo_zip(demo_id):
    demo_dir = os.path.join(app.config['DEMOS_DIR'], demo_id)
    if not os.path.isdir(demo_dir):
        return "Demo not found", 404
    
    zip_filename = f"demo_{demo_id}.zip"
    zip_filepath = os.path.join(app.config['TEMP_DIR'], zip_filename)
    
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(demo_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, demo_dir)
                zipf.write(full_path, arcname)
    
    return send_from_directory(app.config['TEMP_DIR'], zip_filename, as_attachment=True)

@app.route('/temp/<filename>')
def get_temp_file(filename):
    return send_from_directory(app.config['TEMP_DIR'], filename)

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    app.run(debug=False, port=5001)
