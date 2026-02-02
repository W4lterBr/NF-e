; Script Inno Setup para Busca XML
; Gera instalador profissional para Windows

#define MyAppName "Busca XML"
#define MyAppVersion "1.0.95"
#define MyAppPublisher "DWM System Developer"
#define MyAppURL "https://github.com/W4lterBr/NF-e"
#define MyAppExeName "Busca XML.exe"

[Setup]
; Informações do aplicativo
AppId={{A7B8C9D0-E1F2-3A4B-5C6D-7E8F9A0B1C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=Output
OutputBaseFilename=Busca_XML_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Configurações de interface
DisableProgramGroupPage=yes
DisableWelcomePage=no
SetupIconFile=Logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Criar ícone na Barra de Tarefas"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Iniciar automaticamente com o Windows"; GroupDescription: "Opções de Inicialização:"; Flags: unchecked

[Files]
; Executável principal e toda a pasta dist (PyInstaller onedir mode)
; IMPORTANTE: Em onedir, o PyInstaller cria: BOT Busca NFE.exe + pasta _internal/ com tudo
Source: "dist\Busca XML\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: Arquivo_xsd, Icone e modules já estão dentro de dist\Busca XML\_internal\
; Os arquivos .py para atualização também já estão em dist\Busca XML\ e dist\Busca XML\_internal\

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[UninstallDelete]
; Remove TODOS os dados do usuário durante a desinstalação
Type: filesandordirs; Name: "{userappdata}\Busca XML"
Type: filesandordirs; Name: "{userappdata}\BOT Busca NFE"
Type: filesandordirs; Name: "{localappdata}\Busca XML"
Type: dirifempty; Name: "{userappdata}\Busca XML"
Type: dirifempty; Name: "{userappdata}\BOT Busca NFE"
; Remove pasta de instalação (Program Files)
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[Code]
// Verifica se o .NET Framework está instalado (se necessário)
function IsDotNetDetected(version: string; service: cardinal): boolean;
var
    key: string;
    install, release, serviceCount: cardinal;
    success: boolean;
begin
    // Código de verificação do .NET se necessário
    Result := true; // Por padrão retorna true
end;

// Mensagem antes da instalação
function InitializeSetup(): Boolean;
begin
    Result := True;
    if not IsDotNetDetected('v4.5', 0) then
    begin
        MsgBox('Este aplicativo requer .NET Framework 4.5 ou superior.' + #13#10 + 
               'Por favor, instale o .NET Framework antes de continuar.', 
               mbInformation, MB_OK);
    end;
end;

// Após a instalação
procedure CurStepChanged(CurStep: TSetupStep);
var
    StartupRegKey: string;
    ExePath: string;
begin
    if CurStep = ssPostInstall then
    begin
        // Cria diretórios de dados se necessário (novo padrão: Busca XML)
        CreateDir(ExpandConstant('{userappdata}\Busca XML'));
        CreateDir(ExpandConstant('{userappdata}\Busca XML\xmls'));
        CreateDir(ExpandConstant('{userappdata}\Busca XML\logs'));
        CreateDir(ExpandConstant('{userappdata}\Busca XML\backups'));
        
        // Adiciona ao registro de inicialização se selecionado
        if IsTaskSelected('startup') then
        begin
            StartupRegKey := 'Software\Microsoft\Windows\CurrentVersion\Run';
            ExePath := ExpandConstant('"{app}\{#MyAppExeName}" --startup');
            RegWriteStringValue(HKEY_CURRENT_USER, StartupRegKey, '{#MyAppName}', ExePath);
        end;
    end;
end;

// Antes de desinstalar - REMOÇÃO AUTOMÁTICA SILENCIOSA
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
    StartupRegKey: string;
    DataDir1, DataDir2, AppDir: string;
begin
    if CurUninstallStep = usUninstall then
    begin
        // Remove entrada de inicialização automática
        StartupRegKey := 'Software\Microsoft\Windows\CurrentVersion\Run';
        RegDeleteValue(HKEY_CURRENT_USER, StartupRegKey, '{#MyAppName}');
        
        // Define caminhos das pastas
        DataDir1 := ExpandConstant('{userappdata}\Busca XML');
        DataDir2 := ExpandConstant('{userappdata}\BOT Busca NFE');
        AppDir := ExpandConstant('{app}');
        
        // Remove TODOS os dados SILENCIOSAMENTE (sem mensagens)
        // Força remoção com parâmetros: (Path, DeleteSubdirs, DeleteReadOnly, DeleteSelf)
        if DirExists(DataDir1) then
            DelTree(DataDir1, True, True, True);
        if DirExists(DataDir2) then
            DelTree(DataDir2, True, True, True);
        
        // FORÇA remoção completa da pasta Program Files
        if DirExists(AppDir) then
            DelTree(AppDir, True, True, True);
    end;
end;
