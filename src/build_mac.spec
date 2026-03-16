# -*- mode: python ; coding: utf-8 -*-
import os
from glob import glob
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE

# Paths
project_root = os.getcwd()
debug_folder = os.path.join(project_root, 'src', 'Resources', 'Debug')

# Collect hidden imports
hiddenimports = collect_submodules('cryptography')
hiddenimports += ['_cffi_backend']  # Explicitly include cffi backend

# Collect datas (resources)
datas = [
    (os.path.join(project_root, 'src', 'Resources'), 'Resources'),
    (debug_folder, os.path.join('Resources', 'Debug')),
    *[(os.path.join(debug_folder, f), os.path.join('Resources', 'Debug'))
      for f in os.listdir(debug_folder)
      if os.path.isfile(os.path.join(debug_folder, f))]
]

# Analysis
a = Analysis(
    ['Final.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['src/pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)

# Python archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Dark_Souls_3_Save_Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # GUI app
    windowed=True,
)

# macOS .app bundle
app = BUNDLE(
    exe,
    name='Dark_Souls_3_Save_Editor_App.app',
    icon=None,
    bundle_identifier=None,
)
