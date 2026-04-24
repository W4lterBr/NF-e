# 📦 Guia Completo de Build e Instalador

## 🎯 Visão Geral

Sistema automatizado de build para criar instalador profissional do **Busca XML** usando:
- **PyInstaller** (compilação do executável)
- **Inno Setup 6** (criação do instalador)
- **Build.bat** (automação completa)

---

## 📋 Pré-requisitos

### 1. Python e Ambiente Virtual

```bash
# Versão mínima: Python 3.10+
python --version

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Inno Setup 6

**Download:** https://jrsoftware.org/isdl.php

**Instalação padrão:**
- `C:\Program Files (x86)\Inno Setup 6\`
- Adicione ao PATH (opcional)

### 3. Pillow (conversão de ícone)

```bash
pip install pillow
```

---

## 🚀 Como Criar o Instalador

### Opção 1: Build Automatizado (Recomendado)

```bash
# Executa build.bat (compilação + instalador)
build.bat
```

**O script irá:**
1. ✅ Validar ambiente virtual
2. ✅ Instalar/verificar PyInstaller e Pillow
3. ✅ Converter Logo.png → Logo.ico
4. ✅ Validar arquivos críticos
5. ✅ Limpar builds anteriores
6. ✅ Compilar com PyInstaller
7. ✅ Perguntar se deseja criar instalador
8. ✅ Criar instalador com Inno Setup

**Resultado:**
- `dist\Busca XML\Busca XML.exe` - Executável standalone
- `Output\Busca_XML_Setup_v1.0.96.exe` - Instalador completo

### Opção 2: Build Manual

```bash
# 1. Compilar executável
pyinstaller --clean --noconfirm BOT_Busca_NFE.spec

# 2. Criar instalador (se Inno Setup instalado)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📂 Estrutura de Arquivos

### Arquivos de Build

| Arquivo | Descrição |
|---------|-----------|
| `build.bat` | Script automatizado de build |
| `BOT_Busca_NFE.spec` | Configuração do PyInstaller |
| `installer.iss` | Configuração do Inno Setup |
| `version.txt` | Versão atual (sincronizada automaticamente) |

### Arquivos Necessários

```
Busca NFE/
├── Busca NF-e.py              # ✅ Arquivo principal
├── updater_launcher.py        # ✅ Sistema de auto-update
├── version.txt                # ✅ Controle de versão
├── Logo.ico                   # ⚠️ Ícone (gerado de Logo.png)
├── Logo.png                   # ⚠️ Imagem original
├── Arquivo_xsd/               # ⚠️ Schemas XSD
├── Icone/                     # ⚠️ Ícones da interface
└── modules/                   # ✅ Módulos Python
```

**Legenda:**
- ✅ Crítico - Build falha se ausente
- ⚠️ Opcional - Build continua com aviso

---

## 🔧 Configurações Avançadas

### Alterar Versão

**1. Atualize `version.txt`:**
```
1.0.97
```

**2. O installer.iss lê automaticamente:**
```inno
#define MyAppVersion ReadIni(SourcePath + "version.txt", "", "", "1.0.96")
```

### Personalizar Ícone

**Método 1: Substituir Logo.png**
```bash
# Coloque uma imagem PNG 512x512
# O build.bat converterá automaticamente
```

**Método 2: Fornecer Logo.ico diretamente**
```bash
# Coloque o arquivo .ico na raiz
# Tamanhos recomendados: 16, 32, 48, 64, 128, 256
```

### Ajustar Compressão do Instalador

Em `installer.iss`:

```inno
; Máxima compressão (mais lento, menor tamanho)
Compression=lzma2/max

; Compressão rápida (mais rápido, maior tamanho)
Compression=lzma2/fast
```

### Desabilitar UAC (Admin)

Em `installer.iss`:

```inno
; Instalação sem privilégios de admin
PrivilegesRequired=lowest
```

---

## 🐛 Troubleshooting

### ❌ Erro: "Ambiente virtual não encontrado"

**Solução:**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### ❌ Erro: "PyInstaller não encontrado"

**Solução:**
```bash
pip install pyinstaller
```

### ❌ Erro: "Inno Setup não encontrado"

**Soluções:**
1. Instale Inno Setup 6: https://jrsoftware.org/isdl.php
2. Ou compile apenas o executável:
   ```bash
   pyinstaller --clean --noconfirm BOT_Busca_NFE.spec
   ```

### ❌ Erro: "Logo.ico não encontrado"

**Causa:** `Logo.png` ausente ou conversão falhou

**Solução:**
```bash
# Instale Pillow
pip install pillow

# Ou forneça Logo.ico diretamente
```

### ❌ Erro: "Arquivo crítico ausente"

**Arquivos obrigatórios:**
- `Busca NF-e.py`
- `BOT_Busca_NFE.spec`

**Solução:** Baixe os arquivos do repositório

### ⚠️ Aviso: "Pasta Arquivo_xsd não encontrada"

**Impacto:** Validação de XMLs desabilitada

**Solução:** Baixe schemas XSD da SEFAZ:
```bash
# Crie pasta e baixe schemas
mkdir Arquivo_xsd
# Adicione arquivos .xsd
```

---

## 📊 Tamanhos Esperados

| Componente | Tamanho Aproximado |
|------------|-------------------|
| Executável compilado | ~100-150 MB |
| Instalador compactado | ~50-70 MB |
| Instalação completa | ~150-200 MB |

---

## 🔐 Segurança e Distribuição

### Código-Fonte Protegido

✅ **Arquivos .py NÃO são incluídos na distribuição**
- Apenas executável compilado (binário)
- Chaves criptográficas ofuscadas
- Código Python compilado em bytecode

### Assinatura Digital (Opcional)

Para assinatura code signing:

```bash
# Após criar o instalador
signtool sign /f "certificado.pfx" /p "senha" /tr "http://timestamp.digicert.com" "Output\Busca_XML_Setup.exe"
```

### Antivírus

**Downloads executáveis podem disparar alertas falsos**

**Soluções:**
1. Assinar código com certificado válido
2. Submeter para análise (Windows Defender, VirusTotal)
3. Distribuir via Microsoft Store (após validação)

---

## 🚢 Checklist de Release

Antes de distribuir:

- [ ] Atualizar `version.txt`
- [ ] Atualizar `CHANGELOG.md`
- [ ] Testar executável em máquina limpa (VM)
- [ ] Validar instalação e desinstalação
- [ ] Testar funcionalidades principais
- [ ] Verificar auto-update (se aplicável)
- [ ] Criar release no GitHub
- [ ] Documentar mudanças no README

---

## 📝 Variáveis de Ambiente (Opcional)

Para builds em CI/CD:

```env
INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
PYTHON_PATH=C:\Python310\python.exe
BUILD_VERSION=1.0.96
```

---

## 🆘 Suporte

**Erros de build?**

1. Execute `build.bat` e copie log completo
2. Verifique requisitos (Python, PyInstaller, Inno Setup)
3. Teste compilação manual: `pyinstaller BOT_Busca_NFE.spec`
4. Abra issue no GitHub com:
   - Mensagem de erro completa
   - Versão do Python
   - Sistema operacional
   - Arquivo `build.log` (se existir)

---

**Desenvolvido por:** DWM System Developer  
**Última atualização:** 2026-02-06  
**Versão do documento:** 1.0
