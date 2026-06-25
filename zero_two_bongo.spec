# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files

DATAS = [
    ('zero_two.gif', '.'),
    ('zero_two_alt.gif', '.'),
]

for src, dest in collect_data_files('audio', include_py_files=False):
    DATAS.append((src, os.path.join('audio', os.path.dirname(os.path.relpath(src, 'audio')))))

a = Analysis(
    ['zero_two_bongo.py'],
    pathex=[],
    binaries=[],
    datas=DATAS,
    hiddenimports=['PIL', 'PIL.Image', 'PIL.ImageTk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZeroTwoBongo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
