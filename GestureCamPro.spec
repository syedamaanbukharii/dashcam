# PyInstaller build specification for GestureCam Pro.
#
# Build with:  pyinstaller GestureCamPro.spec --noconfirm
#
# Notes:
#  * MediaPipe ships data files that must be collected explicitly.
#  * Model .task files are downloaded at first run into the user's data dir,
#    so they are intentionally NOT bundled here (keeps the binary small and
#    lets models update independently).

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = []
hiddenimports = []

# MediaPipe and CustomTkinter need their bundled assets/submodules.
for package in ("mediapipe", "customtkinter"):
    try:
        datas += collect_data_files(package)
        hiddenimports += collect_submodules(package)
    except Exception:  # noqa: BLE001 - package may be absent at spec parse time
        pass


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GestureCamPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestureCamPro",
)
