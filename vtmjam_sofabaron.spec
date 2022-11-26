# -*- mode: python ; coding: utf-8 -*-


import os
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'


from kivy_deps import sdl2, angle, gstreamer


block_cipher = None


dep_bins = (sdl2.dep_bins + angle.dep_bins + gstreamer.dep_bins)
deps = [Tree(p) for p in dep_bins]


base_path = os.path.normpath('vtmjam_sofabaron/')


def get_path(name):
    ret_path = os.path.normpath(os.path.join(base_path, name))
    print("\n\nGENERATING PATH: {}".format(ret_path))
    return ret_path


a = Analysis(
    [get_path('main.py')],
    pathex=[],
    binaries=[],
    datas=[(get_path('audio'), 'audio'), (get_path('images'), 'images'), (get_path('json'), 'json'), (get_path('text'), 'text')],
    hiddenimports=[],
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
    Tree(get_path('')),
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *deps,
    [],
    name='vtmjam_sofabaron',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
