# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 SCRIPT AUTOMÁTICO - UPLOAD GITHUB RELEASE
# ═══════════════════════════════════════════════════════════════════════════════
# Autor: DWM System Developer
# Data: 02/02/2026
# Descrição: Faz upload automático da release para GitHub
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [switch]$Draft,           # Criar como rascunho
    [switch]$PreRelease,      # Marcar como pré-release
    [switch]$SkipValidation   # Pular validação de arquivos
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

$REPO = "W4lterBr/NF-e"
$DIST_FOLDER = "dist_release_v1.0.95_COMPLETO"
$REQUIRED_FILES = @(
    "Busca XML.exe",
    "Busca_XML_Setup.exe",
    "version.txt"
)

# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES
# ═══════════════════════════════════════════════════════════════════════════════

function Write-Banner {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host ("═" * 80) -ForegroundColor $Color
    Write-Host " $Text" -ForegroundColor $Color
    Write-Host ("═" * 80) -ForegroundColor $Color
    Write-Host ""
}

function Write-Step {
    param([string]$Text)
    Write-Host "▶ $Text" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

function Test-GitHubCLI {
    Write-Step "Verificando GitHub CLI..."
    
    $ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
    
    if (-not $ghInstalled) {
        Write-Error "GitHub CLI (gh) não encontrado!"
        Write-Host ""
        Write-Host "📥 Para instalar:" -ForegroundColor Cyan
        Write-Host "   winget install --id GitHub.cli" -ForegroundColor White
        Write-Host ""
        Write-Host "Ou baixe em: https://cli.github.com/" -ForegroundColor White
        Write-Host ""
        return $false
    }
    
    Write-Success "GitHub CLI instalado"
    
    # Verificar autenticação
    Write-Step "Verificando autenticação..."
    
    $authStatus = gh auth status 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Não autenticado no GitHub!"
        Write-Host ""
        Write-Host "🔑 Para autenticar:" -ForegroundColor Cyan
        Write-Host "   gh auth login" -ForegroundColor White
        Write-Host ""
        return $false
    }
    
    Write-Success "Autenticado no GitHub"
    return $true
}

function Get-Version {
    Write-Step "Lendo versão..."
    
    $versionFile = "version.txt"
    
    if (-not (Test-Path $versionFile)) {
        Write-Error "Arquivo version.txt não encontrado!"
        return $null
    }
    
    $version = (Get-Content $versionFile -Raw).Trim()
    Write-Success "Versão: $version"
    
    return $version
}

function Test-RequiredFiles {
    param([string]$FolderPath)
    
    Write-Step "Validando arquivos obrigatórios..."
    
    if (-not (Test-Path $FolderPath)) {
        Write-Error "Pasta não encontrada: $FolderPath"
        return $false
    }
    
    $allFilesExist = $true
    
    foreach ($file in $REQUIRED_FILES) {
        $filePath = Join-Path $FolderPath $file
        
        if (Test-Path $filePath) {
            $fileSize = (Get-Item $filePath).Length
            $sizeMB = [Math]::Round($fileSize / 1MB, 2)
            Write-Success "$file ($sizeMB MB)"
        }
        else {
            Write-Error "Arquivo não encontrado: $file"
            $allFilesExist = $false
        }
    }
    
    return $allFilesExist
}

function Get-ReleaseNotes {
    param([string]$Version)
    
    Write-Step "Gerando notas de release..."
    
    $notes = @"
# 🎉 Versão $Version

## ✨ Correções Críticas

### 🔄 **Persistência de Versão**
- ✅ Corrigido bug onde versão voltava para 1.0.92 após atualização
- ✅ version.txt agora incluído no processo de build automaticamente
- ✅ Instalador atualizado para incluir version.txt
- ✅ Sistema de versionamento 100% funcional

### 🗄️ **Banco de Dados**
- ✅ Corrigido erro "sqlite3.OperationalError: no such column: nsu"
- ✅ Validação automática da estrutura da tabela antes de consultas
- ✅ Migração automática para adicionar coluna "nsu" em bancos antigos

### 🗑️ **Desinstalação Completa**
- ✅ Remove **100% dos arquivos** ao desinstalar
- ✅ Deleta pasta Program Files\Busca XML automaticamente
- ✅ Deleta %APPDATA%\Busca XML e dados do usuário

### 🔄 **Sistema de Auto-Update**
- ✅ Download automático de atualizações
- ✅ Substitui executável sem intervenção do usuário
- ✅ Reinicia aplicação automaticamente após atualização

---

## 📥 Como Atualizar

### **Opção 1: Auto-Update (Recomendado)**
1. Abra o Busca XML v1.0.93 ou anterior
2. Menu: **Configurações → 🔄 Atualizações**
3. Clique em **"Sim"**
4. Aguarde o download automático
5. Aplicação reiniciará automaticamente

### **Opção 2: Instalador Completo**
1. Baixe ``Busca_XML_Setup.exe`` abaixo
2. Execute o instalador
3. Pronto!

---

## ⚠️ Importante

**Ao desinstalar** (versão $Version+), o sistema remove **TODOS os dados**:
- ✅ Executável principal
- ✅ Banco de dados SQLite
- ✅ XMLs baixados
- ✅ Certificados
- ✅ Configurações

**Faça backup antes se necessário!**

---

## 📊 Changelog Completo

**v$Version** ($(Get-Date -Format "dd/MM/yyyy"))
- [FIX] Versão agora persiste corretamente após atualização
- [FIX] version.txt incluído automaticamente no build
- [FIX] Erro "no such column: nsu" resolvido definitivamente
- [FIX] Desinstalador agora remove pasta Program Files completamente
- [FEATURE] Sistema de auto-update TRUE funcional
- [IMPROVE] Build process automatizado

---

## 🔗 Links Úteis

- 📖 **Documentação**: [README.md](https://github.com/$REPO)
- 🐛 **Reportar Bug**: [Issues](https://github.com/$REPO/issues)
- 💬 **Discussões**: [Discussions](https://github.com/$REPO/discussions)

---

**Desenvolvido por**: DWM System Developer  
**Data**: $(Get-Date -Format "dd 'de' MMMM 'de' yyyy")  
**Versão**: $Version
"@
    
    return $notes
}

function New-GitHubRelease {
    param(
        [string]$Version,
        [string]$Notes,
        [string]$DistFolder,
        [bool]$IsDraft = $false,
        [bool]$IsPreRelease = $false
    )
    
    Write-Banner "CRIANDO RELEASE v$Version"
    
    $tag = "v$Version"
    $title = "v$Version - Correção Sistema de Versionamento"
    
    # Verificar se release já existe
    Write-Step "Verificando se release já existe..."
    
    $existingRelease = gh release view $tag --repo $REPO 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Warning "Release $tag já existe!"
        Write-Host ""
        
        $response = Read-Host "Deseja deletá-la e recriar? (S/N)"
        
        if ($response -eq "S" -or $response -eq "s") {
            Write-Step "Deletando release existente..."
            gh release delete $tag --repo $REPO --yes 2>&1 | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Release deletada"
            }
            else {
                Write-Error "Falha ao deletar release"
                return $false
            }
        }
        else {
            Write-Warning "Operação cancelada pelo usuário"
            return $false
        }
    }
    
    # Construir comando
    $ghCommand = @(
        "release", "create", $tag
        "--repo", $REPO
        "--title", $title
        "--notes", $Notes
    )
    
    if ($IsDraft) {
        $ghCommand += "--draft"
    }
    
    if ($IsPreRelease) {
        $ghCommand += "--prerelease"
    }
    else {
        $ghCommand += "--latest"
    }
    
    # Adicionar arquivos para upload
    foreach ($file in $REQUIRED_FILES) {
        $filePath = Join-Path $DistFolder $file
        $ghCommand += $filePath
    }
    
    # Criar release
    Write-Step "Criando release no GitHub..."
    Write-Host ""
    
    & gh @ghCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Success "Release criada com sucesso!"
        return $true
    }
    else {
        Write-Host ""
        Write-Error "Falha ao criar release"
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# SCRIPT PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

Write-Banner "🚀 UPLOAD AUTOMÁTICO - GITHUB RELEASE" "Green"

# Verificar GitHub CLI
if (-not (Test-GitHubCLI)) {
    exit 1
}

# Obter versão
$version = Get-Version

if (-not $version) {
    exit 1
}

# Validar arquivos
if (-not $SkipValidation) {
    if (-not (Test-RequiredFiles -FolderPath $DIST_FOLDER)) {
        Write-Host ""
        Write-Error "Validação de arquivos falhou!"
        Write-Warning "Use -SkipValidation para ignorar esta verificação"
        exit 1
    }
}

# Gerar notas de release
$releaseNotes = Get-ReleaseNotes -Version $version

# Mostrar resumo
Write-Host ""
Write-Host ("─" * 80) -ForegroundColor Cyan
Write-Host " RESUMO DO UPLOAD" -ForegroundColor Cyan
Write-Host ("─" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "  📦 Repositório: $REPO" -ForegroundColor White
Write-Host "  🏷️  Tag: v$version" -ForegroundColor White
Write-Host "  📁 Pasta: $DIST_FOLDER" -ForegroundColor White
Write-Host ""
Write-Host "  📄 Arquivos que serão enviados:" -ForegroundColor Yellow
foreach ($file in $REQUIRED_FILES) {
    Write-Host "     • $file" -ForegroundColor White
}
Write-Host ""
Write-Host "  ⚙️  Opções:" -ForegroundColor Yellow
Write-Host "     • Draft: $(if ($Draft) { "Sim" } else { "Não" })" -ForegroundColor White
Write-Host "     • Pre-release: $(if ($PreRelease) { "Sim" } else { "Não" })" -ForegroundColor White
Write-Host "     • Latest: $(if (-not $PreRelease) { "Sim" } else { "Não" })" -ForegroundColor White
Write-Host ""
Write-Host ("─" * 80) -ForegroundColor Cyan
Write-Host ""

# Confirmação
$confirmation = Read-Host "Deseja prosseguir com o upload? (S/N)"

if ($confirmation -ne "S" -and $confirmation -ne "s") {
    Write-Warning "Upload cancelado pelo usuário"
    exit 0
}

# Criar release
$success = New-GitHubRelease `
    -Version $version `
    -Notes $releaseNotes `
    -DistFolder $DIST_FOLDER `
    -IsDraft $Draft `
    -IsPreRelease $PreRelease

if ($success) {
    Write-Banner "✅ UPLOAD CONCLUÍDO COM SUCESSO!" "Green"
    
    Write-Host "🔗 Visualizar release:" -ForegroundColor Cyan
    Write-Host "   https://github.com/$REPO/releases/tag/v$version" -ForegroundColor White
    Write-Host ""
    
    Write-Host "📋 Próximos passos:" -ForegroundColor Yellow
    Write-Host "   1. Teste a auto-atualização em uma versão antiga" -ForegroundColor White
    Write-Host "   2. Verifique se todos os arquivos foram enviados" -ForegroundColor White
    Write-Host "   3. Confirme que a release está marcada como 'latest'" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Banner "❌ FALHA NO UPLOAD" "Red"
    exit 1
}
