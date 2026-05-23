@echo off
REM Garante que o script roda sempre a partir da raiz do projeto
cd /d "%~dp0.."
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ============================================================
echo  🚀 Busca XML - Build Automatizado
echo  Desenvolvido por: DWM System Developer
echo  Site: https://dwmsystems.up.railway.app/
echo ============================================================
echo.

REM Lê versão do arquivo version.txt
if exist version.txt (
    set /p APP_VERSION=<version.txt
    echo 📌 Versão: !APP_VERSION!
) else (
    echo ⚠️  AVISO: version.txt não encontrado, usando versão padrão 1.0.0
    set APP_VERSION=1.0.0
)
echo.

REM Ativa ambiente virtual
echo [1/6] 🔧 Ativando ambiente virtual...
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    echo ✅ Ambiente virtual ativado
) else (
    echo ❌ ERRO: Ambiente virtual não encontrado em .venv\
    echo 💡 Execute: python -m venv .venv
    pause
    exit /b 1
)
echo.

REM Instala/atualiza dependências de build
echo [2/6] 📦 Verificando dependências de build...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo    Instalando PyInstaller...
    pip install pyinstaller
) else (
    echo    ✓ PyInstaller instalado
)

pip show pillow >nul 2>&1
if errorlevel 1 (
    echo    Instalando Pillow para conversão de ícone...
    pip install pillow
) else (
    echo    ✓ Pillow instalado
)
echo.

REM Converte Icone\Logo.png em Icone\Logo.ico se existir
echo [3/6] 🎨 Processando ícone da aplicação...
if exist Icone\Logo.png (
    echo    Convertendo Icone\Logo.png para Icone\Logo.ico...
    .venv\Scripts\python.exe -c "from PIL import Image; img = Image.open('Icone/Logo.png'); img.save('Icone/Logo.ico', format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])" 2>nul
    if !errorlevel! equ 0 (
        echo    ✅ Icone\Logo.ico criado com sucesso
    ) else (
        echo    ⚠️  Falha ao converter ícone, usando padrão
    )
) else (
    echo    ⚠️  Icone\Logo.png não encontrado
)
echo.

REM Gera metadados de versão do Windows para o EXE
echo [3.5/6] 📋 Gerando metadados de versão do Windows...
if exist scripts\gerar_version_info.py (
    .venv\Scripts\python.exe scripts\gerar_version_info.py 2>nul
    if !errorlevel! equ 0 (
        if exist file_version_info.txt (
            echo    ✅ file_version_info.txt gerado (Versão: !APP_VERSION!)
        ) else (
            echo    ⚠️  file_version_info.txt não foi criado
        )
    ) else (
        echo    ⚠️  Falha ao gerar metadados de versão
    )
) else (
    echo    ⚠️  gerar_version_info.py não encontrado
)
echo.

REM Valida arquivos críticos
echo [4/6] ✔️  Validando arquivos necessários...
set MISSING_FILES=0

if not exist "Busca NF-e.py" (
    echo    ❌ Busca NF-e.py não encontrado
    set MISSING_FILES=1
)
if not exist "build\BOT_Busca_NFE.spec" (
    echo    ❌ BOT_Busca_NFE.spec não encontrado
    set MISSING_FILES=1
)
if not exist "updater_launcher.py" (
    echo    ⚠️  updater_launcher.py não encontrado (auto-update desabilitado)
)
if not exist "Arquivo_xsd" (
    echo    ⚠️  Pasta Arquivo_xsd não encontrada
)

if !MISSING_FILES! EQU 1 (
    echo.
    echo ❌ Arquivos críticos ausentes. Build cancelado.
    pause
    exit /b 1
)
echo    ✅ Todos os arquivos críticos presentes
echo.

REM Limpa builds anteriores
echo [5/6] 🧹 Limpando builds anteriores...
if exist build (
    rmdir /s /q build
    echo    ✓ Pasta build removida
)
if exist "dist\Busca XML" (
    rmdir /s /q "dist\Busca XML"
    echo    ✓ Pasta dist\Busca XML removida
)
if exist "dist\Busca XML.exe" (
    del /q "dist\Busca XML.exe"
    echo    ✓ Executável antigo removido
)
echo.

REM Compila o aplicativo
echo [6/6] 🔨 Compilando aplicativo...
echo    PyInstaller: build\BOT_Busca_NFE.spec
echo.
pyinstaller --clean --noconfirm build\BOT_Busca_NFE.spec

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ❌ ERRO: Falha na compilação do PyInstaller
    echo ============================================================
    echo.
    echo 💡 Dicas de troubleshooting:
    echo    1. Verifique se todas as dependências estão instaladas
    echo    2. Execute: pip install -r requirements.txt
    echo    3. Tente limpar cache: rmdir /s /q build dist
    echo.
    pause
    exit /b 1
)

echo    ✅ Compilação concluída com sucesso!
echo.

REM Valida se o executável foi criado
if not exist "dist\Busca XML\Busca XML.exe" (
    echo ❌ ERRO: Executável não foi gerado em dist\Busca XML\
    pause
    exit /b 1
)

echo ============================================================
echo ✅ BUILD CONCLUÍDO COM SUCESSO!
echo ============================================================
echo.
echo 📦 Executável: dist\Busca XML\Busca XML.exe
echo 📏 Tamanho: 
for %%I in ("dist\Busca XML\Busca XML.exe") do echo    %%~zI bytes
echo.

REM Verifica se Inno Setup está instalado
set INNO_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe

if "%INNO_PATH%"=="" (
    echo ⚠️  Inno Setup 6 não encontrado
    echo 💡 Baixe em: https://jrsoftware.org/isdl.php
    echo.
    echo Build finalizado sem instalador.
    pause
    exit /b 0
)

echo 🔧 Inno Setup encontrado: %INNO_PATH%
echo.
echo ============================================================
echo Deseja criar o instalador agora? (S/N)
echo ============================================================
set /p CREATE_INSTALLER=

if /i "%CREATE_INSTALLER%"=="S" (
    echo.
    echo 📦 Criando instalador...
    echo.
    "%INNO_PATH%" build\installer.iss
    
    if errorlevel 1 (
        echo ❌ Erro ao criar instalador
        pause
        exit /b 1
    )
    
    echo.
    echo ============================================================
    echo ✅ INSTALADOR CRIADO COM SUCESSO!
    echo ============================================================
    echo.
    echo 📦 Localização: Output\Busca_XML_Setup.exe
    if exist "Output\Busca_XML_Setup.exe" (
        for %%I in ("Output\Busca_XML_Setup.exe") do echo 📏 Tamanho: %%~zI bytes
    )
    echo.
    pause
) else (
    echo.
    echo Build finalizado. Execute build\installer.iss manualmente para criar instalador.
    pause
)
    if errorlevel 1 (
        echo AVISO: Inno Setup nao encontrado em C:\Program Files (x86)\Inno Setup 6\
        echo Instale Inno Setup de: https://jrsoftware.org/isdl.php
    ) else (
        echo.
        echo ============================================================
        echo Instalador criado em: Output\Busca_XML_Setup.exe
        echo ============================================================
    )
)

echo.
pause
