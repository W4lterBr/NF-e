; Script Inno Setup para Busca XML
; Gera instalador profissional para Windows

#define MyAppName "Busca XML"
#define MyAppVersion "1.0.54"
#define MyAppPublisher "DWM System Developer"
#define MyAppURL "https://dwmsystems.up.railway.app/"
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
begin
    if CurStep = ssPostInstall then
    begin
        // Cria diretórios de dados se necessário
        CreateDir(ExpandConstant('{userappdata}\BOT Busca NFE'));
        CreateDir(ExpandConstant('{userappdata}\BOT Busca NFE\xmls'));
        CreateDir(ExpandConstant('{userappdata}\BOT Busca NFE\logs'));
    end;
end;

// Antes de desinstalar
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
    Response: Integer;
begin
    if CurUninstallStep = usUninstall then
    begin
        Response := MsgBox('Deseja manter os dados e configurações do aplicativo?' + #13#10 + 
                          '(XMLs, certificados e banco de dados)' + #13#10#13#10 + 
                          'Clique Sim para MANTER os dados' + #13#10 + 
                          'Clique Não para REMOVER TUDO', 
                          mbConfirmation, MB_YESNO);
        
        if Response = IDNO then
        begin
            // Remove dados do usuário
            DelTree(ExpandConstant('{userappdata}\BOT Busca NFE'), True, True, True);
        end;
    end;
end;
