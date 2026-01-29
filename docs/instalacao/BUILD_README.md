# Guia de Compilação - BOT Busca NFE

## Pré-requisitos

### 1. Python e Ambiente Virtual
- Python 3.8 ou superior instalado
- Ambiente virtual (.venv) configurado com todas as dependências

### 2. PyInstaller
Será instalado automaticamente pelo script build.bat

### 3. Inno Setup (Para criar o instalador)
- Download: https://jrsoftware.org/isdl.php
- Instale em: `C:\Program Files (x86)\Inno Setup 6\`
- Versão recomendada: 6.x ou superior

## Como Compilar

### Método 1: Build Completo (Recomendado)
1. Execute `build.bat`
2. Aguarde a compilação (pode demorar alguns minutos)
3. Quando perguntado, digite `S` para criar o instalador
4. O instalador será criado em: `Output\BOT_Busca_NFE_Setup.exe`

### Método 2: Build Manual
```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Compilar aplicativo
pyinstaller --clean --noconfirm BOT_Busca_NFE.spec

# Criar instalador (após compilação)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Estrutura de Arquivos

```
BOT - Busca NFE/
├── build.bat                  # Script de compilação automática
├── BOT_Busca_NFE.spec        # Configuração PyInstaller
├── installer.iss             # Script Inno Setup
├── interface_pyqt5.py        # Arquivo principal
├── nfe_search.py             # Módulo de busca
├── modules/                  # Módulos adicionais
│   ├── cte_service.py
│   └── ...
├── Icone/                    # Ícones do aplicativo
│   └── app_icon.ico
├── Arquivo_xsd/              # Schemas XSD
└── .venv/                    # Ambiente virtual
```

## Arquivos Gerados

### Durante a Compilação:
- `build/` - Arquivos temporários (pode ser deletado)
- `dist/BOT Busca NFE/` - Aplicativo compilado (pasta portável)

### Instalador Final:
- `Output/BOT_Busca_NFE_Setup.exe` - Instalador para distribuição

## Testando o Aplicativo

### Teste Portável:
1. Navegue até `dist\BOT Busca NFE\`
2. Execute `BOT Busca NFE.exe`
3. Verifique se todas as funcionalidades estão operando

### Teste do Instalador:
1. Execute `Output\BOT_Busca_NFE_Setup.exe`
2. Siga o assistente de instalação
3. Execute o aplicativo instalado
4. Teste desinstalação via Painel de Controle

## Solução de Problemas

### Erro: "Módulo não encontrado"
- Adicione o módulo em `hidden_imports` no arquivo .spec
- Reinstale as dependências: `pip install -r requirements.txt`

### Erro: "Arquivo não encontrado"
- Verifique se as pastas `Icone/` e `Arquivo_xsd/` existem
- Adicione arquivos necessários em `added_files` no .spec

### Aplicativo não inicia:
- Execute via terminal para ver erros: `"dist\BOT Busca NFE\BOT Busca NFE.exe"`
- Verifique logs em `%APPDATA%\BOT Busca NFE\logs\`

### Inno Setup não encontrado:
- Instale de: https://jrsoftware.org/isdl.php
- Ajuste caminho em build.bat se instalou em local diferente

## Distribuição

### Instalador Completo:
- Distribua `Output\BOT_Busca_NFE_Setup.exe`
- Tamanho aproximado: 80-150 MB
- Requer privilégios de administrador para instalação

### Versão Portável:
- Compacte a pasta `dist\BOT Busca NFE\` em ZIP
- Não requer instalação
- Pode ser executado de qualquer pasta

## Personalização

### Alterar Ícone:
1. Coloque seu ícone (.ico) em `Icone\app_icon.ico`
2. Recompile o aplicativo

### Alterar Nome/Versão:
1. Edite `installer.iss`:
   - `#define MyAppName`
   - `#define MyAppVersion`
   - `#define MyAppPublisher`
2. Recompile

### Adicionar Arquivos:
1. Edite `BOT_Busca_NFE.spec`
2. Adicione em `added_files` ou `datas`
3. Recompile

## Certificado Digital (Opcional)

Para assinar o executável:
```bash
signtool sign /f "certificado.pfx" /p "senha" /t http://timestamp.digicert.com "dist\BOT Busca NFE\BOT Busca NFE.exe"
```

## Notas Importantes

- **Primeira compilação**: Pode demorar 5-10 minutos
- **Antivírus**: Pode alertar falso positivo - adicione exceção
- **Atualizações**: Incremente versão em `installer.iss` antes de recompilar
- **Tamanho**: Instalador final ~80-150 MB (inclui Python runtime)

## Checklist Pré-Release

- [ ] Testar todos os módulos
- [ ] Verificar certificados funcionando
- [ ] Testar busca NFe e CTe
- [ ] Confirmar geração de PDFs
- [ ] Testar instalação limpa
- [ ] Testar atualização (se aplicável)
- [ ] Verificar desinstalação
- [ ] Documentar versão (CHANGELOG)

## Suporte

Para problemas de compilação, verifique:
1. Logs em `build/` e `dist/`
2. Dependências instaladas: `pip list`
3. Versão Python: `python --version`
4. Console de erros ao executar .exe

---
**Versão do Guia**: 1.0
**Última Atualização**: Dezembro 2025
