# -*- mode: python ; coding: utf-8 -*-
import os
from glob import glob
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.building.build_main import Analysis, PYZ, EXE

# Paths
project_root = os.getcwd()
debug_folder = os.path.join(project_root, 'src', 'Resources', 'Debug')

# Collect all hidden imports for cryptography
hiddenimports = collect_submodules('cryptography')
# Add _cffi_backend explicitly
hiddenimports += ['_cffi_backend']

# Collect datas (resources)
datas = [
    (os.path.join(project_root, 'src', 'Resources'), 'Resources'),
    # Include Debug folder
    (debug_folder, os.path.join('Resources', 'Debug')),
    # Include all files in Debug folder
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
    a.datas,
    [],
    name='Dark_Souls_3_Save_Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # False for GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
    windowed=True
)
