@echo off
echo ============================================================
echo  BOT Busca NFE - Compilador de Aplicativo
echo  Desenvolvido por: DWM System Developer
echo  Site: https://dwmsystems.up.railway.app/
echo ============================================================
echo.

REM Ativa ambiente virtual
echo [1/4] Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERRO: Nao foi possivel ativar o ambiente virtual
    pause
    exit /b 1
)

REM Instala PyInstaller se necessário
echo [2/4] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

REM Limpa builds anteriores
echo [3/4] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist "dist\BOT Busca NFE" rmdir /s /q "dist\BOT Busca NFE"
if exist "dist\BOT Busca NFE.exe" del /q "dist\BOT Busca NFE.exe"

REM Compila o aplicativo
echo [4/4] Compilando aplicativo...
pyinstaller --clean --noconfirm BOT_Busca_NFE.spec

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERRO: Falha na compilacao
    echo ============================================================
    pause
    exit /b 1
)

REM Copia arquivos .py para a pasta dist (necessário para atualizações)
echo.
echo Copiando arquivos Python para dist...
copy /Y nfe_search.py "dist\BOT Busca NFE\"
copy /Y version.txt "dist\BOT Busca NFE\"
copy /Y CHANGELOG.md "dist\BOT Busca NFE\"
if not exist "dist\BOT Busca NFE\modules" mkdir "dist\BOT Busca NFE\modules"
xcopy /Y /E modules "dist\BOT Busca NFE\modules\"

echo.
echo ============================================================
echo SUCESSO! Aplicativo compilado em: dist\BOT Busca NFE\
echo ============================================================
echo.
echo Deseja criar o instalador agora? (S/N)
set /p CREATE_INSTALLER=

if /i "%CREATE_INSTALLER%"=="S" (
    echo.
    echo Criando instalador...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    if errorlevel 1 (
        echo AVISO: Inno Setup nao encontrado em C:\Program Files (x86)\Inno Setup 6\
        echo Instale Inno Setup de: https://jrsoftware.org/isdl.php
    ) else (
        echo.
        echo ============================================================
        echo Instalador criado em: Output\BOT_Busca_NFE_Setup.exe
        echo ============================================================
    )
)

echo.
pause
