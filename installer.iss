; Script Inno Setup para Busca XML
; Gera instalador profissional para Windows
; Última atualização: 2026-05-04 (v1.2.7)
; Notas v1.2.7:
;   - CRÍTICO: _CopiaWorker movido para nível de módulo (fora de método) — fix trava no .exe PyInstaller.
;     QThread com pyqtSignal definido dentro de método não funciona no executável congelado.
; Notas v1.2.6:
;   - Perfil armazenamento: CNPJs sem certificado cadastrado são ignorados (não geram pasta).
;   - Perfil armazenamento: pasta de DATA (ex: 2026-03) não é mais criada como tipo de documento.
;     Estrutura CNPJ/TIPO/DATA/arquivo.xml agora reconhecida corretamente.
;   - Perfil armazenamento: corrigido FutureWarning lxml — 'or' chain substituído por 'is None' explícito.
; Notas v1.2.5:
;   - CRÍTICO: Corrigido crash Qt5Core.dll (0xc0000409) — QThread.finished sobrescrito por pyqtSignal().
;   - PDF NFS-e: ETAPA 1 (disco) → ETAPA 2 (API ADN) → ETAPA 2.5 (LinkNFSe ABRASF) → ETAPA 3 (local).
;   - pdf_tipo no banco: OFICIAL (API/LinkNFSe) ou GENERICO (local reportlab).
;   - Importação ABRASF multi-nota (ListaNotaFiscal): todas as notas importadas corretamente.
;   - Anti-duplicação: guard por numero+cnpj_emitente evita duplicatas ABRASF/ADN.
;   - salvar_nota_detalhada: nome_destinatario, v_ibs, v_cbs, cfop agora gravados para NFS-e ADN.
;   - DB: backfill automático de nome_destinatario via JOIN com nfse_docs na inicialização.

; Lê versão dinamicamente do arquivo version.txt
#pragma message "Reading version from version.txt..."
#define FileHandle FileOpen("version.txt")
#define MyAppVersion Trim(FileRead(FileHandle))
#expr FileClose(FileHandle)
#pragma message "Version loaded: " + MyAppVersion

#define MyAppName "Busca XML"
#define MyAppPublisher "DWM System Developer"
#define MyAppURL "https://dwmsystems.up.railway.app/"
#define MyAppExeName "Busca XML.exe"
#define MyAppDescription "Sistema de busca e gestão de documentos fiscais eletrônicos"

[Setup]
; ============================================================
; INFORMAÇÕES DO APLICATIVO
; ============================================================
AppId={{A7B8C9D0-E1F2-3A4B-5C6D-7E8F9A0B1C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments={#MyAppDescription}
AppCopyright=Copyright (C) 2025-2026 {#MyAppPublisher}

; ============================================================
; CONFIGURAÇÕES DE INSTALAÇÃO
; ============================================================
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=Busca_XML_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=1048576
LZMANumFastBytes=273

; ============================================================
; REQUISITOS E COMPATIBILIDADE
; ============================================================
MinVersion=10.0.17763
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; ============================================================
; INTERFACE E VISUAL
; ============================================================
WizardStyle=modern
WizardSizePercent=120,100
DisableProgramGroupPage=yes
DisableWelcomePage=no
SetupIconFile=Logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; ============================================================
; INFORMAÇÕES DE VERSÃO (metadados do executável)
; ============================================================
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoTextVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2025-2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Criar ícone na Barra de Tarefas"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Iniciar automaticamente com o Windows"; GroupDescription: "Opções de Inicialização:"; Flags: unchecked

[Files]
; ============================================================
; ARQUIVOS DA APLICAÇÃO
; ============================================================
; Executável principal e dependências (modo onedir do PyInstaller)
; Estrutura: Busca XML.exe + _internal/ (DLLs, bibliotecas, recursos)
Source: "dist\Busca XML\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; NOTA: PyInstaller onedir já inclui automaticamente:
;  - Busca XML.exe (executável principal)
;  - _internal/ (todas as DLLs e dependências)
;  - Arquivo_xsd/ (schemas de validação)
;  - Icone/ (ícones da interface)
;  - updater_launcher.py (sistema de auto-update)
;  - version.txt (controle de versão)

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec

[Code]
// ============================================================
// VALIDAÇÕES PRÉ-INSTALAÇÃO
// ============================================================

// Verifica se é Windows 10 ou superior
function IsWindows10OrNewer(): Boolean;
var
    Version: TWindowsVersion;
begin
    GetWindowsVersionEx(Version);
    Result := (Version.Major >= 10);
end;

// Verifica se há espaço em disco suficiente (mínimo 500 MB)
function HasEnoughDiskSpace(): Boolean;
begin
    // Nota: DiskFree foi removido em Inno Setup 6.3+
    // A validação de espaço é feita automaticamente pelo instalador
    // baseado no DiskSpaceRequired em [Setup]
    Result := True;
end;

// Inicialização - validações antes de começar
function InitializeSetup(): Boolean;
var
    ErrorMsg: String;
begin
    Result := True;
    ErrorMsg := '';
    
    // Valida Windows 10+
    if not IsWindows10OrNewer() then
    begin
        ErrorMsg := ErrorMsg + '• Windows 10 ou superior é necessário' + #13#10;
        Result := False;
    end;
    
    // Nota: Espaço em disco é validado automaticamente pelo Inno Setup
    // usando a diretiva DiskSpaceRequired em [Setup]
    
    // Exibe erros se houver
    if not Result then
    begin
        MsgBox('A instalação não pode continuar:' + #13#10#13#10 + ErrorMsg + #13#10 + 
               'Por favor, corrija os problemas e tente novamente.', 
               mbCriticalError, MB_OK);
    end;
end;

// ============================================================
// AÇÕES DURANTE A INSTALAÇÃO
// ============================================================
procedure CurStepChanged(CurStep: TSetupStep);
var
    StartupRegKey: string;
    ExePath: string;
    DataDir: string;
begin
    if CurStep = ssPostInstall then
    begin
        // Cria estrutura de diretórios de dados
        DataDir := ExpandConstant('{userappdata}\Busca XML');
        
        if not DirExists(DataDir) then
        begin
            Log('Criando diretório de dados: ' + DataDir);
            CreateDir(DataDir);
        end;
        
        if not DirExists(DataDir + '\xmls') then
            CreateDir(DataDir + '\xmls');
        if not DirExists(DataDir + '\logs') then
            CreateDir(DataDir + '\logs');
        if not DirExists(DataDir + '\config') then
            CreateDir(DataDir + '\config');
        
        Log('Estrutura de diretórios criada com sucesso');
        
        // Adiciona ao registro de inicialização se selecionado
        if IsTaskSelected('startup') then
        begin
            StartupRegKey := 'Software\Microsoft\Windows\CurrentVersion\Run';
            ExePath := ExpandConstant('"{app}\{#MyAppExeName}"');
            RegWriteStringValue(HKEY_CURRENT_USER, StartupRegKey, '{#MyAppName}', ExePath);
            Log('Adicionado ao startup do Windows');
        end;
    end;
end;

// ============================================================
// DESINSTALAÇÃO
// ============================================================
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
    Response: Integer;
    StartupRegKey: string;
    DataDir: string;
    DataSize: Int64;
begin
    if CurUninstallStep = usUninstall then
    begin
        // Remove entrada de inicialização automática
        StartupRegKey := 'Software\Microsoft\Windows\CurrentVersion\Run';
        RegDeleteValue(HKEY_CURRENT_USER, StartupRegKey, '{#MyAppName}');
        Log('Removido do startup do Windows');
        
        DataDir := ExpandConstant('{userappdata}\Busca XML');
        
        // Verifica se há dados do usuário
        if DirExists(DataDir) then
        begin
            Response := MsgBox(
                'Deseja MANTER seus dados e configurações?' + #13#10#13#10 +
                '📁 Seus arquivos em:' + #13#10 +
                DataDir + #13#10#13#10 +
                '• XMLs de notas fiscais' + #13#10 +
                '• Certificados digitais' + #13#10 +
                '• Banco de dados' + #13#10 +
                '• Configurações' + #13#10#13#10 +
                'Clique SIM para MANTER os dados' + #13#10 +
                'Clique NÃO para REMOVER TUDO',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON1);
            
            if Response = IDNO then
            begin
                Log('Usuário optou por remover dados');
                if DelTree(DataDir, True, True, True) then
                    Log('Dados removidos com sucesso')
                else
                    Log('Erro ao remover dados - alguns arquivos podem estar em uso');
            end
            else
            begin
                Log('Dados do usuário preservados em: ' + DataDir);
                MsgBox('Seus dados foram preservados em:' + #13#10#13#10 +
                       DataDir + #13#10#13#10 +
                       'Você pode usar estes dados ao reinstalar o aplicativo.',
                       mbInformation, MB_OK);
            end;
        end;
    end;
end;
