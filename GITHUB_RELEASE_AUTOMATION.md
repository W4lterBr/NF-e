# 🚀 Automação de GitHub Releases

Este documento explica como usar o sistema automatizado de upload de releases para o GitHub.

---

## 📋 Pré-requisitos

### 1️⃣ Instalar GitHub CLI

**Opção A - winget (Recomendado):**
```powershell
winget install --id GitHub.cli
```

**Opção B - Download Manual:**
- Acesse: https://cli.github.com/
- Baixe e instale o instalador para Windows

### 2️⃣ Autenticar no GitHub

Após instalar, execute:

```powershell
gh auth login
```

Siga as instruções:
1. Escolha: `GitHub.com`
2. Escolha: `HTTPS`
3. Escolha: `Login with a web browser`
4. Copie o código exibido
5. Pressione Enter (abrirá o navegador)
6. Cole o código e autorize

✅ **Pronto! Você está autenticado.**

---

## 🎯 Como Usar

### Uso Básico (Recomendado)

```powershell
.\upload_github_release.ps1
```

**O script irá:**
1. ✅ Verificar se GitHub CLI está instalado e autenticado
2. ✅ Ler a versão de `version.txt`
3. ✅ Validar se os 3 arquivos necessários existem
4. ✅ Gerar as notas de release automaticamente
5. ✅ Mostrar um resumo do que será enviado
6. ✅ Pedir confirmação
7. ✅ Criar a release no GitHub
8. ✅ Fazer upload dos arquivos
9. ✅ Marcar como "latest release"

### Opções Avançadas

**Criar como rascunho (draft):**
```powershell
.\upload_github_release.ps1 -Draft
```

**Marcar como pré-release:**
```powershell
.\upload_github_release.ps1 -PreRelease
```

**Pular validação de arquivos:**
```powershell
.\upload_github_release.ps1 -SkipValidation
```

**Combinar opções:**
```powershell
.\upload_github_release.ps1 -Draft -PreRelease
```

---

## 📁 Estrutura Necessária

O script espera esta estrutura:

```
BOT - Busca NFE/
├── version.txt                          ← Contém a versão (ex: 1.0.95)
├── upload_github_release.ps1            ← Script de upload
└── dist_release_v1.0.95_COMPLETO/       ← Pasta com os arquivos
    ├── Busca XML.exe                    ← Executável (obrigatório)
    ├── Busca_XML_Setup.exe              ← Instalador (obrigatório)
    └── version.txt                      ← Versão (obrigatório)
```

---

## 🔄 Fluxo Completo de Release

### 1. Atualizar Versão

Edite `version.txt`:
```
1.0.96
```

### 2. Compilar Executável

```powershell
.\build.bat
```

Isso irá:
- Compilar o executável
- Copiar `version.txt` automaticamente
- Gerar o instalador

### 3. Fazer Upload Automático

```powershell
.\upload_github_release.ps1
```

### 4. Testar Auto-Update

1. Instale uma versão antiga
2. Abra o aplicativo
3. Menu → Configurações → 🔄 Atualizações
4. Confirme se atualiza para a nova versão

---

## ❓ Perguntas Frequentes

### ❓ "GitHub CLI não encontrado"

**Solução:**
```powershell
winget install --id GitHub.cli
```

Feche e reabra o PowerShell após a instalação.

### ❓ "Não autenticado no GitHub"

**Solução:**
```powershell
gh auth login
```

### ❓ "Release já existe"

O script perguntará se você deseja deletar e recriar. Responda:
- `S` para deletar e recriar
- `N` para cancelar

### ❓ "Arquivo não encontrado"

Verifique se a pasta `dist_release_v1.0.95_COMPLETO` existe e contém:
- `Busca XML.exe`
- `Busca_XML_Setup.exe`
- `version.txt`

Se estiver faltando, execute `build.bat` primeiro.

### ❓ Como verificar se funcionou?

Acesse:
```
https://github.com/W4lterBr/NF-e/releases/latest
```

Deve mostrar a versão que você acabou de enviar com os 3 arquivos.

---

## 🛠️ Solução de Problemas

### Erro: "Permission denied"

**Causa:** Token do GitHub sem permissões suficientes

**Solução:**
```powershell
gh auth refresh -h github.com -s repo
```

### Erro: "Rate limit exceeded"

**Causa:** Muitas requisições ao GitHub

**Solução:** Aguarde 15-30 minutos e tente novamente.

### Erro: "Network error"

**Causa:** Problema de conexão

**Solução:**
1. Verifique sua internet
2. Tente novamente
3. Se persistir, use VPN

---

## 📊 O Que o Script Faz Automaticamente

✅ **Verificações:**
- GitHub CLI instalado
- Autenticação válida
- Arquivos necessários existem
- Versão válida

✅ **Criação da Release:**
- Tag: `v{versão}`
- Título: `v{versão} - Correção Sistema de Versionamento`
- Notas de release completas e formatadas
- Marca como "latest release" automaticamente

✅ **Upload de Arquivos:**
- `Busca XML.exe` (executável para auto-update)
- `Busca_XML_Setup.exe` (instalador completo)
- `version.txt` (arquivo de versão)

✅ **Segurança:**
- Pede confirmação antes de enviar
- Avisa se release já existe
- Valida todos os arquivos antes

---

## 🎨 Customização

### Alterar Repositório

Edite no script (linha 18):
```powershell
$REPO = "SeuUsuario/SeuRepo"
```

### Alterar Pasta de Distribuição

Edite no script (linha 19):
```powershell
$DIST_FOLDER = "sua_pasta_dist"
```

### Alterar Arquivos Obrigatórios

Edite no script (linhas 20-24):
```powershell
$REQUIRED_FILES = @(
    "SeuArquivo1.exe",
    "SeuArquivo2.msi",
    "version.txt"
)
```

---

## 📝 Exemplo de Uso

```powershell
PS C:\...\BOT - Busca NFE> .\upload_github_release.ps1

═══════════════════════════════════════════════════════════════════════════════
 🚀 UPLOAD AUTOMÁTICO - GITHUB RELEASE
═══════════════════════════════════════════════════════════════════════════════

▶ Verificando GitHub CLI...
✅ GitHub CLI instalado
▶ Verificando autenticação...
✅ Autenticado no GitHub
▶ Lendo versão...
✅ Versão: 1.0.95
▶ Validando arquivos obrigatórios...
✅ Busca XML.exe (17.68 MB)
✅ Busca_XML_Setup.exe (51.68 MB)
✅ version.txt (0.01 MB)

────────────────────────────────────────────────────────────────────────────────
 RESUMO DO UPLOAD
────────────────────────────────────────────────────────────────────────────────

  📦 Repositório: W4lterBr/NF-e
  🏷️  Tag: v1.0.95
  📁 Pasta: dist_release_v1.0.95_COMPLETO

  📄 Arquivos que serão enviados:
     • Busca XML.exe
     • Busca_XML_Setup.exe
     • version.txt

  ⚙️  Opções:
     • Draft: Não
     • Pre-release: Não
     • Latest: Sim

────────────────────────────────────────────────────────────────────────────────

Deseja prosseguir com o upload? (S/N): S

═══════════════════════════════════════════════════════════════════════════════
 CRIANDO RELEASE v1.0.95
═══════════════════════════════════════════════════════════════════════════════

▶ Verificando se release já existe...
▶ Criando release no GitHub...

https://github.com/W4lterBr/NF-e/releases/tag/v1.0.95

✅ Release criada com sucesso!

═══════════════════════════════════════════════════════════════════════════════
 ✅ UPLOAD CONCLUÍDO COM SUCESSO!
═══════════════════════════════════════════════════════════════════════════════

🔗 Visualizar release:
   https://github.com/W4lterBr/NF-e/releases/tag/v1.0.95

📋 Próximos passos:
   1. Teste a auto-atualização em uma versão antiga
   2. Verifique se todos os arquivos foram enviados
   3. Confirme que a release está marcada como 'latest'
```

---

## 🔗 Links Úteis

- 📖 **GitHub CLI Docs:** https://cli.github.com/manual/
- 🔐 **Autenticação:** https://cli.github.com/manual/gh_auth_login
- 📦 **Releases:** https://cli.github.com/manual/gh_release

---

**Criado por:** DWM System Developer  
**Data:** 02/02/2026  
**Versão:** 1.0
