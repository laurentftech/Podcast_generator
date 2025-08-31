# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# --- Get Version ---
SPEC_DIR = SPECPATH
version_file_path = os.path.join(SPEC_DIR, '_version.py')
try:
    version_globals = {}
    with open(version_file_path, 'r') as f:
        exec(f.read(), version_globals)
    version_str = version_globals['__version__']
except (FileNotFoundError, KeyError) as e:
    print(f"Build Warning: Could not read version from _version.py ({e}). Using fallback.")
    version_str = "0.0.0-manual"

# --- Data and Hidden Imports Collection ---

# Collect all data files from customtkinter (themes, fonts, etc.)
# This is crucial for the UI to render correctly.
datas = collect_data_files('customtkinter')

# Add our own project assets
datas += [
    ('podcast.png', '.'),
    ('podcast.icns', '.'),
    ('docs/demo_template.html', 'docs')
]

# Explicitly list hidden imports that PyInstaller's static analysis might miss.
# This is the most common reason for applications crashing at startup.
hidden_imports = [
    'customtkinter',
    'whisperx',
    'torch',
    'torchaudio',
    'keyring.backends.macOS',  # Explicitly include keychain backend for macOS
    'pkg_resources.py2_warn'
]
# Also collect all submodules for whisperx to be safe
hidden_imports += collect_submodules('whisperx')

# --- Analysis ---
a = Analysis(
    ['gui.py'],
    pathex=[SPEC_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- Executable ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Podcast Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # This should be False for a GUI app
    windowed=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPEC_DIR, 'podcast.ico')  # Icon for Windows
)

# --- Platform-specific output ---
if sys.platform == 'darwin':
    # On macOS, we create a .app bundle.
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, upx_exclude=[], name='Podcast Generator')
    app = BUNDLE(
        coll,
        name='Podcast Generator.app',
        icon=os.path.join(SPEC_DIR, 'podcast.icns'),
        bundle_identifier='com.laurentftech.podcastgenerator',
        info_plist={
            'CFBundleShortVersionString': version_str.split('.dev')[0].split('+')[0],
            'CFBundleVersion': version_str,
            'NSHighResolutionCapable': 'True',
            'NSPrincipalClass': 'NSApplication',
            'NSAppleEventsUsageDescription': 'Required for application functionality.'
        }
    )
else:
    # On Windows and Linux, we collect the files into a simple directory.
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Podcast Generator'
    )