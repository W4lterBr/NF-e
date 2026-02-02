# Upload Automatico para GitHub Release
$VERSION = (Get-Content "version.txt").Trim()
$TAG = "v$VERSION"
$DIST = "dist_release_v1.0.95_COMPLETO"

Write-Host ""
Write-Host "Fazendo upload da versao $VERSION..." -ForegroundColor Cyan
Write-Host ""

# Criar tag Git
Write-Host "Criando tag $TAG..." -ForegroundColor Yellow
git tag -a $TAG -m "Release $VERSION - Correcao Sistema de Versionamento" -f
git push origin $TAG -f

Write-Host ""
Write-Host "Tag criada e enviada!" -ForegroundColor Green
Write-Host ""
Write-Host "PROXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "1. Acesse: https://github.com/W4lterBr/NF-e/releases/new?tag=$TAG" -ForegroundColor White
Write-Host "2. Arraste os arquivos da pasta $DIST" -ForegroundColor White
Write-Host "3. Clique em Publish release" -ForegroundColor White
Write-Host ""

Start-Process "https://github.com/W4lterBr/NF-e/releases/new?tag=$TAG"
