# -*- mode: python ; coding: utf-8 -*-
# BOT Busca NFE - PyInstaller Spec File
# Desenvolvido por: DWM System Developer
# Site: https://dwmsystems.up.railway.app/

import os

block_cipher = None

# Dados adicionais a incluir (APENAS recursos, NÃO código-fonte)
added_files = [
    ('Icone', 'Icone'),           # Ícones da interface
    ('Arquivo_xsd', 'Arquivo_xsd'), # Schemas XML para validação
    # CÓDIGO-FONTE (.py) NÃO É INCLUÍDO - apenas executável compilado
    # Dados do usuário (xmls/, notas.db) são criados em runtime no AppData
]

# Imports ocultos necessários
hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'zeep',
    'zeep.transports',
    'requests',
    'requests_pkcs12',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    'sqlite3',
    'cryptography',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.lib',
    'reportlab.platypus',
]

a = Analysis(
    ['interface_pyqt5.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'tkinter',
    ],
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
    name='BOT Busca NFE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Janela de console oculta
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Logo.ico' if os.path.exists('Logo.ico') else None,
    manifest='app.manifest',  # Manifest para executar como administrador
    uac_admin=True,  # Solicita privilégios de administrador
    uac_uiaccess=False,
)

# Modo ONEDIR: Executável + dependências (SEM código-fonte .py)
# Apenas dados do usuário (xmls/, notas.db) permanecem após desinstalação

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BOT Busca NFE',
)
