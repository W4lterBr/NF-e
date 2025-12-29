@echo off
REM ===================================================================
REM BOT - Busca NFE - Instalador Automatico Windows
REM ===================================================================

echo.
echo ===================================================================
echo   BOT - BUSCA NFE - INSTALADOR AUTOMATICO
echo ===================================================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Por favor, instale Python 3.10 ou superior:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marque "Add Python to PATH" durante instalacao
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Verificar versao do Python
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python 3.10+ necessario
    python --version
    pause
    exit /b 1
)

echo [OK] Versao do Python compativel
echo.

REM Criar ambiente virtual se nao existir
if not exist ".venv" (
    echo [1/4] Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado
) else (
    echo [1/4] Ambiente virtual ja existe
)

echo.
echo [2/4] Ativando ambiente virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Falha ao ativar ambiente virtual
    pause
    exit /b 1
)
echo [OK] Ambiente virtual ativado

echo.
echo [3/4] Atualizando pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip atualizado

echo.
echo [4/4] Instalando dependencias...
echo (Isso pode levar 5-10 minutos...)
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias
    echo.
    echo Tente instalar manualmente:
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ===================================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ===================================================================
echo.
echo Proximos passos:
echo   1. Execute: verificar_instalacao.py
echo   2. Configure certificados digitais
echo   3. Inicie o sistema: python interface_pyqt5.py
echo.
echo ===================================================================
echo.

pause
