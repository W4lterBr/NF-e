# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Busca NF-e.py'],
    pathex=[],
    binaries=[],
    datas=[('Arquivo_xsd', 'Arquivo_xsd'), ('Logo.ico', '.'), ('Icone', 'Icone'), ('themes.py', '.'), ('nfe_search.py', '.'), ('nfse_search.py', '.'), ('gerar_danfce.py', '.'), ('gerar_danfse_profissional.py', '.'), ('modules/sandbox_task_runner.py', 'modules')],
    hiddenimports=['themes', 'nfe_search', 'gerar_danfce', 'gerar_danfse_profissional'],
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
    [],
    exclude_binaries=True,
    name='Busca XML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Busca XML',
)
