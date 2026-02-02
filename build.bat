@echo off
echo ============================================================
echo  Busca XML - Compilador de Aplicativo v1.0.95
echo  Desenvolvido por: DWM System Developer
echo  GitHub: https://github.com/W4lterBr/NF-e
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

REM Verifica e instala Pillow se necessário (para conversão de ícone)
pip show pillow >nul 2>&1
if errorlevel 1 (
    echo Instalando Pillow para conversao de icone...
    pip install pillow
)

REM Converte Logo.png em Logo.ico se existir
if exist Logo.png (
    echo Convertendo Logo.png para Logo.ico...
    python -c "from PIL import Image; img = Image.open('Logo.png'); img.save('Logo.ico', format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])"
    if errorlevel 1 (
        echo AVISO: Falha ao converter icone, continuando...
    ) else (
        echo Icone Logo.ico criado com sucesso!
    )
) else (
    echo AVISO: Logo.png nao encontrado, compilando sem icone personalizado
)

REM Limpa builds anteriores
echo [3/4] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist "dist\Busca XML" rmdir /s /q "dist\Busca XML"
if exist "dist\Busca XML.exe" del /q "dist\Busca XML.exe"

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

REM ===================================================================
REM ARQUIVOS .PY REMOVIDOS DA DISTRIBUIÇÃO (Segurança)
REM ===================================================================
REM O executável já contém todo o código compilado.
REM Apenas dados do usuário (xmls/, notas.db) devem permanecer após desinstalação.
REM
REM Se precisar de atualizações remotas no futuro, implemente via:
REM - Novo instalador/executável
REM - Sistema de atualização automática que baixa novo .exe
REM ===================================================================

REM Copiar recursos necessários (Icone, Logo.ico e Arquivo_xsd)
echo.
echo [RECURSOS] Copiando icones e schemas XSD...
xcopy /E /I /Y "Icone" "dist\Busca XML\Icone" >nul 2>&1
xcopy /E /I /Y "Arquivo_xsd" "dist\Busca XML\Arquivo_xsd" >nul 2>&1
copy /Y "Logo.ico" "dist\Busca XML\Logo.ico" >nul 2>&1
copy /Y "Logo.png" "dist\Busca XML\Logo.png" >nul 2>&1
copy /Y "version.txt" "dist\Busca XML\version.txt" >nul 2>&1
echo   Recursos copiados com sucesso!

echo.
echo [SEGURANCA] Codigo-fonte NAO incluido na distribuicao
echo   Apenas executavel compilado sera distribuido

echo.
echo ============================================================
echo SUCESSO! Aplicativo compilado em: dist\Busca XML\
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
        echo Instalador criado em: Output\Busca_XML_Setup.exe
        echo ============================================================
    )
)

echo.
pause
