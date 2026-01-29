# 📦 Guia de Distribuição - BOT Busca NFE

## ✅ O que INCLUIR na distribuição

### Arquivos Obrigatórios

```
📦 BOT_Busca_NFE_Instalacao/
│
├── 📁 BOT Busca NFE/              ← PASTA GERADA PELO PYINSTALLER
│   ├── BOT Busca NFE.exe          ← Executável principal
│   ├── _internal/                 ← Dependências compiladas
│   │   ├── PyQt5/
│   │   ├── lxml/
│   │   ├── cryptography/
│   │   └── ... (outras libs)
│   ├── 📁 Icone/                  ← Ícones da interface
│   │   ├── xml.png
│   │   └── cancelado.png
│   └── 📁 Arquivo_xsd/            ← Schemas para validação XML
│       ├── nfe_v4.00.xsd
│       ├── distDFeInt_v1.01.xsd
│       └── ... (~56 arquivos)
│
├── 📄 README.md                   ← Instruções de uso (opcional)
└── 📄 INSTALACAO.md               ← Guia de instalação (opcional)
```

### Tamanho Esperado
- **Pasta completa:** ~200 MB
- **Compactado (ZIP):** ~60-80 MB

---

## ❌ O que NÃO INCLUIR

### Código-Fonte (NÃO distribuir!)

```
❌ interface_pyqt5.py
❌ nfe_search.py
❌ nfse_search.py
❌ nuvem_fiscal_api.py
❌ modules/*.py
❌ __pycache__/
❌ *.pyc
```

### Dados de Desenvolvimento

```
❌ .venv/
❌ .git/
❌ build/
❌ *.spec
❌ build.bat
❌ requirements.txt
❌ .vscode/
```

### Dados Sensíveis (NUNCA distribuir!)

```
❌ notas.db (contém dados do usuário)
❌ xmls/ (XMLs do usuário)
❌ *.pfx, *.p12 (certificados digitais)
❌ api_credentials.csv (credenciais)
❌ .env (configurações)
❌ logs/ (logs do sistema)
```

---

## 🗂️ Estrutura Final da Distribuição

### Opção 1: ZIP Simples

```cmd
# Comprimir apenas a pasta compilada
"C:\Program Files\7-Zip\7z.exe" a -tzip BOT_Busca_NFE_v2.0.zip "dist\BOT Busca NFE"
```

**Resultado:** `BOT_Busca_NFE_v2.0.zip` (~60-80 MB)

---

### Opção 2: Instalador (Recomendado)

Use Inno Setup para criar instalador profissional.

**installer.iss atualizado:**

```iss
[Setup]
AppName=BOT Busca NFE
AppVersion=2.0
DefaultDirName={autopf}\BOT Busca NFE
DefaultGroupName=BOT Busca NFE
OutputBaseFilename=BOT_Busca_NFE_Setup_v2.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\BOT Busca NFE.exe

[Files]
; Apenas executável compilado e recursos
Source: "dist\BOT Busca NFE\*"; DestDir: "{app}"; Flags: recursesubdirs

; NÃO incluir código-fonte (.py)
; NÃO incluir dados do usuário (xmls/, notas.db)

[Icons]
Name: "{group}\BOT Busca NFE"; Filename: "{app}\BOT Busca NFE.exe"
Name: "{autodesktop}\BOT Busca NFE"; Filename: "{app}\BOT Busca NFE.exe"

[UninstallDelete]
; MANTER dados do usuário após desinstalar
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\Icone"
Type: filesandordirs; Name: "{app}\Arquivo_xsd"
Type: files; Name: "{app}\BOT Busca NFE.exe"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('Deseja manter os dados (XMLs e banco de dados)?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Mantém xmls/ e notas.db
      MsgBox('Dados mantidos em: ' + ExpandConstant('{userappdata}\BOT Busca NFE'), mbInformation, MB_OK);
    end
    else
    begin
      // Remove tudo
      DelTree(ExpandConstant('{userappdata}\BOT Busca NFE'), True, True, True);
      MsgBox('Todos os dados foram removidos.', mbInformation, MB_OK);
    end;
  end;
end;
```

---

## 🧪 Teste Antes de Distribuir

### Checklist de Validação

- [ ] Executável abre normalmente
- [ ] Sem arquivos .py na pasta `dist/BOT Busca NFE/`
- [ ] Pasta `Icone/` presente
- [ ] Pasta `Arquivo_xsd/` presente (~56 arquivos)
- [ ] Tamanho total: ~200 MB
- [ ] Testado em VM ou PC limpo
- [ ] Certificado digital funciona
- [ ] Busca de notas funciona
- [ ] PDFs são gerados

---

## 📋 O Que Permanece Após Desinstalar

### No PC do Usuário

```
📁 %USERPROFILE%\AppData\Roaming\BOT Busca NFE\
├── notas.db              ← Banco de dados (histórico)
├── xmls/                 ← XMLs baixados
│   ├── 33251845000109/
│   │   ├── 2025-05/
│   │   └── 2025-06/
│   └── 47539664000197/
└── logs/                 ← Logs do sistema (opcional)
```

**Total:** ~10-500 MB (depende de quantos XMLs foram baixados)

---

## 🚀 Processo Completo de Distribuição

### 1. Limpar Build Anterior

```cmd
rmdir /s /q build
rmdir /s /q "dist\BOT Busca NFE"
```

### 2. Gerar Executável

```cmd
# Opção A: Usar build.bat (recomendado)
build.bat

# Opção B: PyInstaller direto
pyinstaller --clean --noconfirm BOT_Busca_NFE.spec
```

### 3. Verificar Conteúdo

```cmd
dir "dist\BOT Busca NFE"
```

**Deve mostrar:**
```
BOT Busca NFE.exe
_internal\
Icone\
Arquivo_xsd\
```

**NÃO deve ter:**
```
❌ interface_pyqt5.py
❌ modules\
❌ *.py
```

### 4. Testar em VM

Copie para máquina virtual limpa e teste:
- Executar BOT Busca NFE.exe
- Adicionar certificado
- Fazer busca
- Gerar PDF
- Fechar e reabrir

### 5. Criar Pacote

```cmd
# ZIP
"C:\Program Files\7-Zip\7z.exe" a -tzip BOT_Busca_NFE_v2.0.zip "dist\BOT Busca NFE"

# OU Instalador
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## 📊 Comparação: Antes vs Depois

### ❌ ANTES (Inseguro)

```
dist/BOT Busca NFE/
├── BOT Busca NFE.exe
├── interface_pyqt5.py       ← Código exposto!
├── nfe_search.py             ← Código exposto!
├── modules/
│   ├── database.py           ← Código exposto!
│   └── crypto_portable.py    ← Chave mestre exposta!
└── ...
```

**Problema:** Código-fonte fica no PC do usuário!

---

### ✅ DEPOIS (Seguro)

```
dist/BOT Busca NFE/
├── BOT Busca NFE.exe         ← Código compilado (bytecode)
├── _internal/                ← Dependências compiladas
├── Icone/                    ← Apenas recursos
└── Arquivo_xsd/              ← Apenas recursos
```

**Apenas dados do usuário:**
```
%APPDATA%/BOT Busca NFE/
├── notas.db                  ← Banco de dados
└── xmls/                     ← XMLs baixados
```

---

## 🎯 Resumo

### Para Distribuir:

```
✅ dist/BOT Busca NFE/  (pasta completa)
❌ Código-fonte (.py)
❌ Dados do usuário (notas.db, xmls/)
❌ Certificados (.pfx)
```

### Após Desinstalar Ficam:

```
✅ notas.db
✅ xmls/
❌ Executável
❌ Dependências
❌ Código-fonte
```

---

## 📞 Perguntas Frequentes

### P: E se eu quiser atualizar o sistema?

**R:** Gere novo executável e distribua novo instalador. Não é necessário incluir .py.

### P: Como fazer atualizações sem reinstalar?

**R:** Implemente sistema de auto-atualização que:
1. Verifica versão no servidor
2. Baixa novo .exe
3. Substitui executável antigo
4. Reinicia aplicação

### P: Os dados do usuário são preservados?

**R:** SIM! Apenas o executável e dependências são removidos. `notas.db` e `xmls/` ficam em `%APPDATA%`.

### P: Como limpar tudo (inclusive dados)?

**R:** Desinstalar normalmente + deletar manualmente:
```
%USERPROFILE%\AppData\Roaming\BOT Busca NFE\
```

---

**Atualizado em:** 18/12/2025  
**Versão:** 2.0 - Distribuição sem código-fonte
