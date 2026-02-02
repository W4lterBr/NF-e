# Setup GitHub CLI Automatico
Write-Host ""
Write-Host "Verificando GitHub CLI..." -ForegroundColor Yellow

$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue

if ($ghInstalled) {
    Write-Host "GitHub CLI ja instalado!" -ForegroundColor Green
    
    gh auth status 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Autenticado no GitHub!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Pronto para usar:" -ForegroundColor Cyan
        Write-Host "  .\upload_github_release.ps1" -ForegroundColor White
        Write-Host ""
        exit 0
    }
    else {
        Write-Host "Nao autenticado" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Autenticando agora..." -ForegroundColor Cyan
        Write-Host ""
        gh auth login
        exit 0
    }
}

Write-Host "GitHub CLI nao encontrado!" -ForegroundColor Red
Write-Host ""
Write-Host "Instalando via winget..." -ForegroundColor Yellow

$wingetInstalled = Get-Command winget -ErrorAction SilentlyContinue

if ($wingetInstalled) {
    winget install --id GitHub.cli --accept-package-agreements --accept-source-agreements
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Instalado com sucesso!" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANTE: Feche e reabra o PowerShell" -ForegroundColor Yellow
        Write-Host "Depois execute: .\setup_github_cli.ps1" -ForegroundColor Cyan
        Write-Host ""
    }
}
else {
    Write-Host "winget nao encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Instale manualmente:" -ForegroundColor Yellow
    Write-Host "  https://cli.github.com/" -ForegroundColor Cyan
    Write-Host ""
    
    Start-Process "https://cli.github.com/"
}
