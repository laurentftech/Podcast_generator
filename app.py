from flask import Flask, render_template, request, jsonify, send_from_directory
from generate_podcast import generate, DEFAULT_INSTRUCTION, DEFAULT_SCRIPT, setup_logging, validate_speakers, update_elevenlabs_quota
from utils import sanitize_text, get_asset_path, get_app_data_dir
from config import AVAILABLE_VOICES, DEFAULT_APP_SETTINGS, DEMO_AVAILABLE
from create_demo import create_html_demo_whisperx
from transcript_analyzer import generate_analysis_docx, get_analysis_prompt_path
import os
import tempfile
import json
import requests
import zipfile
import shutil
from elevenlabs.core import ApiError
import re
import uuid
import threading
import json
from flask import jsonify

# --- App Initialization ---
app = Flask(__name__)
logger = setup_logging()

# --- In-Memory Task Manager ---
tasks = {}

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

def extract_filename_from_script(script_text, extension, max_length=50):
    """
    Extracts a safe filename from the beginning of the first sentence in the script.

    Args:
        script_text: The script content
        extension: File extension (e.g., 'mp3', 'docx')
        max_length: Maximum length for the filename (default 50)

    Returns:
        A sanitized filename with the given extension
    """
    # Remove speaker labels and get the first sentence
    lines = script_text.strip().split('\n')
    first_dialogue = ""

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        # Check if line has speaker format (Speaker: text)
        match = re.match(r'^\s*([^:]+?)\s*:\s*(.+)$', line)
        if match:
            first_dialogue = match.group(2).strip()
            break
        else:
            # If no speaker format, use the line as-is
            first_dialogue = line.strip()
            break

    if not first_dialogue:
        # Fallback to UUID if no content found
        return f"podcast_{os.urandom(4).hex()}.{extension}"

    # Remove any bracketed annotations like [playful], [laughing], etc.
    first_dialogue = re.sub(r'\[.*?\]', '', first_dialogue).strip()

    # Extract the beginning (up to first sentence or max_length)
    # Split by sentence-ending punctuation
    sentence_match = re.match(r'^([^.!?]+)', first_dialogue)
    if sentence_match:
        first_sentence = sentence_match.group(1).strip()
    else:
        first_sentence = first_dialogue

    # Limit length
    if len(first_sentence) > max_length:
        first_sentence = first_sentence[:max_length].strip()

    # Remove or replace characters that are unsafe for filenames
    # Keep alphanumeric, spaces, hyphens, and underscores
    safe_name = re.sub(r'[^\w\s\-]', '', first_sentence)
    # Replace multiple spaces/hyphens with single underscore
    safe_name = re.sub(r'[\s\-]+', '_', safe_name)
    # Remove leading/trailing underscores
    safe_name = safe_name.strip('_')

    # If we ended up with an empty name, use fallback
    if not safe_name:
        return f"podcast_{os.urandom(4).hex()}.{extension}"

    return f"{safe_name}.{extension}"

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html', 
                           default_instruction=DEFAULT_INSTRUCTION, 
                           default_script=DEFAULT_SCRIPT, 
                           demo_available=DEMO_AVAILABLE)

@app.route('/assets/<path:filename>')
def get_asset(filename):
    assets_dir = get_asset_path('.')
    if not assets_dir:
        return "Assets directory not found", 404
    return send_from_directory(assets_dir, filename)

@app.route('/api/about', methods=['GET'])
def get_about_info():
    return jsonify({'version': version(), 'license': LICENSE_TEXT})

def version():
    try:
        with open("version.json") as f:
            data = json.load(f)
            return data.get("version", "unknown")
    except Exception:
        return "unknown"

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
    settings['has_analysis_prompt'] = bool(get_analysis_prompt_path())
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

@app.route('/api/voice_classifications', methods=['GET'])
def get_voice_classifications():
    """Returns voice classifications for Gemini voices."""
    classifications_path = get_asset_path(os.path.join("samples", "gemini_voices", "voice_classifications.json"))
    if not classifications_path:
        return jsonify({'error': 'Classifications file not found'}), 404
    try:
        with open(classifications_path, 'r', encoding='utf-8') as f:
            classifications = json.load(f)
        # Filter out entries with errors and create a lookup dictionary
        classifications_dict = {}
        for entry in classifications:
            if 'error' not in entry and 'filename' in entry:
                classifications_dict[entry['filename']] = {
                    'gender': entry.get('gender', 'unknown'),
                    'age_group': entry.get('age_group', 'unknown'),
                    'accent': entry.get('accent', 'unknown'),
                    'speaking_style': entry.get('speaking_style', 'unknown')
                }
        return jsonify(classifications_dict)
    except Exception as e:
        logger.error(f"Error loading voice classifications: {e}")
        return jsonify({'error': 'Could not load classifications'}), 500

@app.route('/api/elevenlabs_voice_classifications', methods=['GET'])
def get_elevenlabs_voice_classifications():
    """Returns voice classifications for ElevenLabs voices."""
    classifications_path = get_asset_path(os.path.join("samples", "elevenlabs_voices", "voice_classifications.json"))
    if not classifications_path:
        return jsonify({'error': 'Classifications file not found'}), 404
    try:
        with open(classifications_path, 'r', encoding='utf-8') as f:
            classifications = json.load(f)
        # Filter out entries with errors and create a lookup dictionary by voice_name
        classifications_dict = {}
        for entry in classifications:
            if 'error' not in entry and 'voice_name' in entry:
                # Exclude gender since it's already provided by ElevenLabs API
                classifications_dict[entry['voice_name']] = {
                    'age_group': entry.get('age_group', 'unknown'),
                    'accent': entry.get('accent', 'unknown'),
                    'speaking_style': entry.get('speaking_style', 'unknown')
                }
        return jsonify(classifications_dict)
    except Exception as e:
        logger.error(f"Error loading ElevenLabs voice classifications: {e}")
        return jsonify({'error': 'Could not load classifications'}), 500

def run_generation_task(task_id, script_text, app_settings, output_filepath, api_key):
    """The target function for the generation thread."""
    stop_event = tasks[task_id]['stop_event']
    try:
        generated_file = generate(
            script_text=script_text,
            app_settings=app_settings,
            output_filepath=output_filepath,
            api_key=api_key,
            status_callback=logger.info,
            stop_event=stop_event
        )
        if generated_file:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['result'] = {'download_url': f'/temp/{os.path.basename(generated_file)}', 'filename': os.path.basename(generated_file)}
    except Exception as e:
        # If the exception is due to the stop event, set a specific status
        if "stopped by user" in str(e):
            tasks[task_id]['status'] = 'cancelled'
            tasks[task_id]['error'] = 'Generation cancelled by user.'
            # Clean up the partially created file
            if os.path.exists(output_filepath):
                try:
                    os.remove(output_filepath)
                    logger.info(f"Removed partial file for stopped task: {output_filepath}")
                except OSError as err:
                    logger.error(f"Error removing partial file for stopped task: {err}")
        else:
            logger.error(f"Error during generation for task {task_id}: {e}", exc_info=True)
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = str(e)

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

    provider = app_settings.get("tts_provider", "elevenlabs")
    api_key_env_var = "ELEVENLABS_API_KEY" if provider == "elevenlabs" else "GEMINI_API_KEY"
    api_key = os.environ.get(api_key_env_var)
    if not api_key:
        return jsonify({'error': f'API key ({api_key_env_var}) not found in environment variables.'}), 500

    from utils import sanitize_app_settings_for_backend
    app_settings_clean = sanitize_app_settings_for_backend(app_settings)

    task_id = str(uuid.uuid4())
    output_filename = extract_filename_from_script(sanitized_script, 'mp3')
    output_filepath = os.path.join(app.config['TEMP_DIR'], output_filename)
    
    stop_event = threading.Event()
    thread = threading.Thread(target=run_generation_task, args=(task_id, sanitized_script, app_settings_clean, output_filepath, api_key))
    
    tasks[task_id] = {'thread': thread, 'stop_event': stop_event, 'status': 'running'}
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/generation_status/<task_id>', methods=['GET'])
def get_generation_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    response = {'status': task['status']}
    if task['status'] == 'completed':
        response['result'] = task['result']
    elif task['status'] in ['failed', 'cancelled']:
        response['error'] = task.get('error', 'An unknown error occurred.')
        
    return jsonify(response)

@app.route('/api/stop_generation/<task_id>', methods=['POST'])
def stop_generation(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task['status'] == 'running':
        task['stop_event'].set()
        task['status'] = 'stopping'
        return jsonify({'status': 'Stop signal sent.'})
    
    return jsonify({'status': 'Task was not running.'})

@app.route('/api/generate_demo', methods=['POST'])
def handle_generate_demo():
    # If DEMO_AVAILABLE is not set to "1", return an error
    if not DEMO_AVAILABLE:
        return jsonify({'error': 'Demo generation is not available.'}), 403

    data = request.json
    script_text, audio_filename = data.get('script'), data.get('audio_filename')
    title, subtitle = data.get('title', 'Podcast Demo'), data.get('subtitle', '')
    show_credits = data.get('show_credits', True)

    if not script_text or not audio_filename:
        return jsonify({'error': 'Script and audio filename are required.'}), 400

    audio_filepath = os.path.join(app.config['TEMP_DIR'], audio_filename)
    # Validate: ensure audio_filepath is inside TEMP_DIR
    normalized_audio_filepath = os.path.normpath(audio_filepath)
    if not normalized_audio_filepath.startswith(os.path.abspath(app.config['TEMP_DIR'])):
        return jsonify({'error': 'Invalid audio filename.'}), 400
    if not os.path.exists(normalized_audio_filepath):
        return jsonify({'error': 'Audio file not found on server.'}), 404

    demo_id = os.urandom(8).hex()
    demo_output_dir = os.path.join(app.config['DEMOS_DIR'], demo_id)
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as f:
            f.write(script_text)
            temp_script_file = f.name

        create_html_demo_whisperx(
            script_filepath=temp_script_file,
            audio_filepath=normalized_audio_filepath,
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
    # Validate demo_dir is inside DEMOS_DIR
    normalized_demo_dir = os.path.normpath(os.path.abspath(demo_dir))
    demos_base = os.path.abspath(app.config['DEMOS_DIR'])
    if not normalized_demo_dir.startswith(demos_base + os.sep):
        return "Invalid demo ID", 400
    return send_from_directory(normalized_demo_dir, filename)

@app.route('/api/download_demo/<demo_id>')
def download_demo_zip(demo_id):
    demo_dir = os.path.join(app.config['DEMOS_DIR'], demo_id)
    # Normalize and validate that demo_dir is within DEMOS_DIR
    normalized_demo_dir = os.path.normpath(os.path.abspath(demo_dir))
    demos_base = os.path.abspath(app.config['DEMOS_DIR'])
    if not normalized_demo_dir.startswith(demos_base + os.sep):
        return "Invalid demo ID", 400
    if not os.path.isdir(normalized_demo_dir):
        return "Demo not found", 404
    
    zip_filename = f"demo_{demo_id}.zip"
    zip_filepath = os.path.join(app.config['TEMP_DIR'], zip_filename)
    
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(normalized_demo_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, normalized_demo_dir)
                zipf.write(full_path, arcname)
    
    return send_from_directory(app.config['TEMP_DIR'], zip_filename, as_attachment=True)

@app.route('/temp/<filename>')
def get_temp_file(filename):
    return send_from_directory(app.config['TEMP_DIR'], filename)

@app.route('/api/generate_analysis', methods=['POST'])
def handle_generate_analysis():
    """Generates a DOCX analysis document from a transcript using Gemini API."""
    data = request.json
    transcript = data.get('transcript', '')

    if not transcript:
        return jsonify({'error': 'Transcript is required.'}), 400

    # Check if Gemini API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({'error': 'Gemini API key not configured.'}), 403

    try:
        # Generate the analysis DOCX
        docx_filename = extract_filename_from_script(transcript, 'docx')
        docx_path = os.path.join(app.config['TEMP_DIR'], docx_filename)

        generate_analysis_docx(
            transcript=transcript,
            output_path=docx_path,
            api_key=api_key
        )

        return jsonify({
            'download_url': f'/temp/{docx_filename}',
            'filename': docx_filename
        })

    except ValueError as e:
        logger.error(f"Validation error during analysis generation: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error during analysis generation: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred during analysis generation.'}), 500

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    app.run(debug=False, port=5001)
