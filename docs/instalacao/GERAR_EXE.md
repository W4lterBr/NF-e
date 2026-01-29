# 🎯 Guia de Geração de Executável (.exe)

## 📋 Preparação ANTES de Gerar o .exe

### ✅ Passo 1: Migrar para Chave Portável

**OBRIGATÓRIO se você criptografou as senhas!**

```cmd
python migrate_to_portable.py
```

**O que isso faz:**
- Converte senhas da chave local → chave mestre
- Chave mestre fica embutida no código
- Banco funciona em QUALQUER PC

**Resultado esperado:**
```
✅ 5 senhas migradas para chave mestre
   Agora o banco pode ser usado em qualquer PC!
```

---

### ✅ Passo 2: Atualizar database.py

Você precisa modificar o `modules/database.py` para usar chave portável:

**ANTES:**
```python
from .crypto_utils import get_crypto  # Chave local
```

**DEPOIS:**
```python
from .crypto_portable import get_portable_crypto as get_crypto  # Chave mestre
```

Ou use este comando automático:
```cmd
python -c "import sys; sys.path.insert(0, '.'); from migrate_to_portable import update_database_imports; update_database_imports()"
```

---

## 🛠️ Gerar o Executável

### Opção 1: Usar PyInstaller Diretamente

```cmd
# Instalar PyInstaller
pip install pyinstaller

# Gerar executável
pyinstaller BOT_Busca_NFE.spec
```

**Resultado:**
- Executável em: `dist/BOT Busca NFE/BOT Busca NFE.exe`
- Tamanho: ~150-200 MB
- Modo: ONEDIR (pasta com exe + dependências)

---

### Opção 2: Executável Único (ONEFILE)

Criar novo spec file:

```python
# BOT_Busca_NFE_onefile.spec
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BOT Busca NFE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon='Logo.ico' if os.path.exists('Logo.ico') else None,
)
```

Gerar:
```cmd
pyinstaller BOT_Busca_NFE_onefile.spec
```

---

## 📦 O Que Incluir na Distribuição

### Arquivos Obrigatórios

```
📁 Distribuição/
├── 📁 BOT Busca NFE/           (pasta gerada pelo PyInstaller)
│   ├── BOT Busca NFE.exe       ← Executável principal
│   ├── python310.dll
│   ├── _internal/              (dependências)
│   └── ...
│
├── 📁 Arquivo_xsd/             ← OBRIGATÓRIO (validação XML)
│   ├── nfe_v4.00.xsd
│   ├── distDFeInt_v1.01.xsd
│   └── ...
│
├── 📁 Icone/                   ← OBRIGATÓRIO (ícones interface)
│   ├── xml.png
│   └── cancelado.png
│
├── 📁 modules/                 ← OBRIGATÓRIO (scripts Python)
│   ├── __init__.py
│   ├── database.py
│   ├── crypto_portable.py
│   ├── sandbox_worker.py
│   ├── pdf_generator.py
│   └── ...
│
├── nfe_search.py               ← OBRIGATÓRIO (busca NF-e)
├── nfse_search.py              ← Se usar NFS-e
├── nuvem_fiscal_api.py         ← Se usar Nuvem Fiscal
│
├── requirements.txt            ← Recomendado (documentação)
├── README.md                   ← Recomendado
├── INSTALACAO.md               ← Recomendado
│
└── notas.db                    ← OPCIONAL (apenas se quiser compartilhar dados)
```

---

## 🚀 Distribuir para Outro PC

### Método 1: Copiar Pasta Completa

```cmd
# Comprimir tudo
"C:\Program Files\7-Zip\7z.exe" a -tzip "BOT_Busca_NFE_Portatil.zip" "dist\BOT Busca NFE" "Arquivo_xsd" "Icone" "modules" "*.py" "*.md"

# No PC destino:
1. Extrair ZIP
2. Executar: BOT Busca NFE.exe
```

---

### Método 2: Instalador (Avançado)

Criar instalador com **Inno Setup**:

```iss
; BOT_Busca_NFE_Setup.iss
[Setup]
AppName=BOT Busca NFE
AppVersion=2.0
DefaultDirName={autopf}\BOT Busca NFE
DefaultGroupName=BOT Busca NFE
OutputBaseFilename=BOT_Busca_NFE_Installer
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\BOT Busca NFE\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "Arquivo_xsd\*"; DestDir: "{app}\Arquivo_xsd"; Flags: recursesubdirs
Source: "Icone\*"; DestDir: "{app}\Icone"
Source: "modules\*"; DestDir: "{app}\modules"; Flags: recursesubdirs
Source: "*.py"; DestDir: "{app}"
Source: "*.md"; DestDir: "{app}"

[Icons]
Name: "{group}\BOT Busca NFE"; Filename: "{app}\BOT Busca NFE.exe"
Name: "{autodesktop}\BOT Busca NFE"; Filename: "{app}\BOT Busca NFE.exe"
```

Compilar:
```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" BOT_Busca_NFE_Setup.iss
```

---

## ⚠️ Problemas Comuns e Soluções

### ❌ Erro: "Failed to execute script"

**Causa:** Faltam dependências ou arquivos

**Solução:**
```cmd
# Adicione ao spec file:
hiddenimports=[
    'PyQt5.sip',
    'lxml.etree',
    'requests_pkcs12',
    'cryptography.hazmat.backends.openssl',
]
```

---

### ❌ Erro: "ModuleNotFoundError: No module named 'modules'"

**Causa:** Pasta modules não está no PATH

**Solução:** Certifique-se que pasta `modules/` está junto com o .exe

---

### ❌ Senhas não descriptografam no outro PC

**Causa:** Não executou `migrate_to_portable.py`

**Solução:**
```cmd
python migrate_to_portable.py
# Gere o .exe novamente
```

---

### ❌ Antivírus bloqueia executável

**Causa:** .exe não assinado digitalmente

**Soluções:**
1. **Code Signing** (recomendado): Assine com certificado digital
2. **Adicione exceção** no antivírus
3. **VirusTotal**: Suba para análise e whitelist

---

### ❌ "API-MS-WIN-CRT-RUNTIME" erro

**Causa:** Falta Visual C++ Redistributable

**Solução:**
```
Incluir na distribuição:
- VC_redist.x64.exe
- Instruir usuário a instalar
```

---

## 🔒 Segurança na Distribuição

### ⚠️ IMPORTANTE: Ofuscar Código

A chave mestre está no código! Para proteger:

```cmd
# Instalar PyArmor
pip install pyarmor

# Ofuscar código
pyarmor gen --recursive --output dist_obfuscated/ modules/*.py *.py

# Gerar .exe com código ofuscado
pyinstaller BOT_Busca_NFE.spec
```

---

### 🔐 Níveis de Proteção

| Ação | Proteção | Dificuldade |
|------|----------|-------------|
| Apenas .exe | 20% | Muito fácil extrair |
| .exe + UPX | 40% | Fácil descomprimir |
| PyArmor | 80% | Difícil reverter |
| PyArmor + Code Signing | 95% | Muito difícil |

---

## ✅ Checklist Final

Antes de distribuir:

- [ ] ✅ Executou `migrate_to_portable.py`
- [ ] ✅ Atualizou database.py para usar crypto_portable
- [ ] ✅ Testou .exe no PC atual
- [ ] ✅ Incluiu pasta Arquivo_xsd/
- [ ] ✅ Incluiu pasta Icone/
- [ ] ✅ Incluiu pasta modules/
- [ ] ✅ Incluiu scripts .py principais
- [ ] ✅ (Opcional) Ofuscou código com PyArmor
- [ ] ✅ (Opcional) Assinou com Code Signing
- [ ] ✅ Testou em VM ou outro PC
- [ ] ✅ Criou README com instruções

---

## 🧪 Teste em Outro PC

### VM para Teste (Recomendado)

```cmd
# 1. Criar VM Windows limpa
# 2. Copiar apenas a pasta dist/
# 3. Executar .exe
# 4. Verificar se:
   - Interface abre
   - Banco carrega
   - Certificados descriptografam
   - Busca funciona
```

---

## 📊 Tamanhos Esperados

| Tipo | Tamanho |
|------|---------|
| ONEDIR (pasta) | 180-220 MB |
| ONEFILE (único) | 90-120 MB |
| Compactado ZIP | 40-60 MB |
| Instalador | 50-70 MB |

---

## 🎉 Resultado Final

Após seguir este guia:

✅ Executável portátil funcionando
✅ Banco de dados portável (senhas criptografadas com chave mestre)
✅ Pronto para distribuição
✅ Funciona em Windows 10/11 sem Python instalado

---

**Próximo passo:** Execute `migrate_to_portable.py` e depois gere o .exe!
