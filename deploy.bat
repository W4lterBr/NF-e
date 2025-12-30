@echo off
chcp 65001 >nul
echo ============================================================
echo   Deploy Automático - Busca XML NF-e
echo ============================================================
echo.

REM Lê versão atual
set /p VERSION=<version.txt
echo Versão atual: %VERSION%
echo.

REM Confirma versão
set /p CONFIRM="Deseja criar release v%VERSION%? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo Deploy cancelado.
    pause
    exit /b
)

echo.
echo [1/5] Compilando aplicativo...
call build.bat

REM Verifica se compilação foi bem sucedida
if not exist "dist\Busca XML\Busca XML.exe" (
    echo ❌ ERRO: Compilação falhou!
    pause
    exit /b 1
)

echo.
echo [2/5] Verificando instalador...
if not exist "Output\Busca_XML_Setup.exe" (
    echo ❌ ERRO: Instalador não encontrado!
    pause
    exit /b 1
)

echo.
echo [3/5] Adicionando arquivos ao Git...
git add .
git status --short

echo.
set /p COMMIT_MSG="Mensagem do commit (deixe vazio para usar versão): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=Release v%VERSION%

git commit -m "%COMMIT_MSG%"

echo.
echo [4/5] Criando tag v%VERSION%...
git tag -a v%VERSION% -m "Release v%VERSION%"

echo.
echo [5/5] Enviando para GitHub...
git push origin main
git push origin v%VERSION%

echo.
echo ============================================================
echo ✅ Deploy concluído!
echo.
echo Próximos passos:
echo 1. Acesse: https://github.com/W4lterBr/NF-e/releases/new?tag=v%VERSION%
echo 2. Título: Release v%VERSION%
echo 3. Faça upload do instalador: Output\Busca_XML_Setup.exe
echo 4. Publique a release
echo.
echo Depois que publicar a release, os usuários poderão atualizar
echo automaticamente clicando em "🔄 Atualizações" no aplicativo!
echo ============================================================
echo.

REM Abre navegador na página de release
start https://github.com/W4lterBr/NF-e/releases/new?tag=v%VERSION%

pause
