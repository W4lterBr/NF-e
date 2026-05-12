# -*- mode: python ; coding: utf-8 -*-
# Busca XML - PyInstaller Spec File
# Desenvolvido por: DWM System Developer
# Site: https://dwmsystems.up.railway.app/
# Última atualização: 2026-05-12

import os
from pathlib import Path

block_cipher = None

# Verifica existência de arquivos críticos
print("[SPEC] Validando arquivos necessários...")

required_files = {
    'Busca NF-e.py': 'Arquivo principal',
    'version.txt': 'Controle de versão',
    'updater_launcher.py': 'Sistema de auto-update'
}

for file, desc in required_files.items():
    if not Path(file).exists():
        print(f"[SPEC] ⚠️  {file} não encontrado ({desc})")
    else:
        print(f"[SPEC] ✓ {file}")

# Dados adicionais a incluir (recursos e arquivos de sistema)
added_files = [
    ('version.txt', '.'),                      # Versão atual (CRÍTICO)
    ('updater_launcher.py', '.'),              # Auto-update (CRÍTICO)
    ('nfe_search.py', '.'),                    # Motor de busca SEFAZ (CRÍTICO)
    ('nfse_search.py', '.'),                   # Motor de busca NFS-e (CRÍTICO v1.1.28)
    ('themes.py', '.'),                        # Temas visuais (CRÍTICO v1.1.30)
    ('gerar_danfse_profissional.py', '.'),     # Gerador DANFSe profissional NFS-e (CRÍTICO v1.1.16)
    ('buscar_nfse_auto.py', '.'),              # Busca automática NFS-e (CRÍTICO v1.1.30)
]

# Adiciona recursos se existirem
if Path('Icone').exists():
    added_files.append(('Icone', 'Icone'))
    print("[SPEC] ✓ Icone incluído")
else:
    print("[SPEC] ⚠️  Pasta Icone não encontrada")

if Path('Arquivo_xsd').exists():
    added_files.append(('Arquivo_xsd', 'Arquivo_xsd'))
    print("[SPEC] ✓ Arquivo_xsd incluído")
else:
    print("[SPEC] ⚠️  Pasta Arquivo_xsd não encontrada")

if Path('Logo.ico').exists():
    added_files.append(('Logo.ico', '.'))
    print("[SPEC] ✓ Logo.ico incluído")

if Path('Logo.png').exists():
    added_files.append(('Logo.png', '.'))
    print("[SPEC] ✓ Logo.png incluído")

# Inclui pasta modules/ completa (backend modules)
if Path('modules').exists():
    added_files.append(('modules', 'modules'))
    module_count = len(list(Path('modules').glob('*.py')))
    print(f"[SPEC] ✓ Pasta modules/ incluída ({module_count} arquivos)")
else:
    print("[SPEC] ⚠️  Pasta modules/ não encontrada")

print(f"[SPEC] Total de arquivos de dados: {len(added_files)}")

# Imports ocultos necessários
hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'zeep',
    'zeep.transports',
    'zeep.wsdl',
    'requests',
    'requests_pkcs12',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    'sqlite3',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    'pyOpenSSL',
    'wincertstore',
    'signxml',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.units',
    'reportlab.lib.colors',
    'reportlab.lib.utils',  # ImageReader para QR Code
    'reportlab.platypus',
    'borb',
    'borb.pdf',
    'PyPDF2',
    'argparse',
    'winreg',
    'psutil',
    # Excel Export
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.writer',
    'openpyxl.reader',
    # Modules personalizados
    'modules.certificate_manager',
    'modules.nfse_service',
    'modules.xml_processor',
    'modules.database',                # DatabaseManager (importado por nfe_search)
    'modules.manifestacao_service',    # Ciência / manifestações
    'modules.cte_service',             # CT-e distribuição
    'modules.brasilnfe_api',           # API alternativa manifestação
    'modules.sandbox_worker',          # PDF/SEFAZ isolado
    'modules.crypto_portable',         # Criptografia portável
    'modules.updater',                 # Auto-update GitHub
    'modules.task_scheduler',          # Agendador QTimer
    'modules.quota_manager',           # Limite 20 consultas/hora
    'modules.startup_manager',         # Windows registry autostart
    'modules.qt_components',           # Componentes PyQt5
    'modules.ui_components',           # Helpers UI
    'modules.xsd_validator',           # Validação XSD
    'modules.task_manager_dialog',     # Dialog gestão de tarefas
    'gerar_danfse_profissional',  # Gerador DANFSe profissional (v1.1.16)
    'qrcode',  # Dependência do gerar_danfse_profissional
    'qrcode.image',  # Módulo de imagem do qrcode
    'qrcode.image.pil',  # Backend PIL do qrcode
    # Jinja2 + WeasyPrint: geração local de DANFSe (fallback quando API /danfse/{chave} falha)
    'jinja2',
    'jinja2.environment',
    'jinja2.loaders',
    'jinja2.filters',
    'jinja2.utils',
    'markupsafe',
    'weasyprint',
    'weasyprint.css',
    'weasyprint.document',
    'weasyprint.html',
    'pydyf',
    'tinycss2',
    'cssselect2',
    'tinyhtml5',
    'fonttools',
    'pyphen',
    'PIL',  # Pillow para processamento de imagens
    'PIL.Image',  # Imagens PIL
    'buscar_nfse_auto',  # Busca automática NFS-e (necessário para modo .exe frozen)
    # PyNFe – usado por modules.manifestacao_service
    'pynfe',
    'pynfe.processamento',
    'pynfe.processamento.comunicacao',
    'pynfe.processamento.assinatura',
    'pynfe.processamento.serializacao',
    'pynfe.entidades',
    'pynfe.entidades.evento',
]

a = Analysis(
    ['Busca NF-e.py'],  # Arquivo principal atualizado
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
    name='Busca XML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Janela de console oculta (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Logo.ico' if os.path.exists('Logo.ico') else None,
    manifest='app.manifest' if os.path.exists('app.manifest') else None,
    version='file_version_info.txt' if os.path.exists('file_version_info.txt') else None,  # Fix: Versão correta no EXE
    uac_admin=False,  # NÃO requer admin (evita UAC desnecessário)
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
    name='Busca XML',
)
