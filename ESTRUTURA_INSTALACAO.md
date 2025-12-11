# Estrutura de Instalação - BOT Busca NFE

## 📁 Estrutura após Compilação (PyInstaller)

Quando você executa `build.bat`, a estrutura criada é:

```
dist/BOT Busca NFE/
├── BOT Busca NFE.exe          ← Executável principal
├── nfe_search.py              ← Código Python (atualizável)
├── version.txt                ← Versão atual
├── CHANGELOG.md               ← Histórico de mudanças
├── modules/                   ← Módulos Python (atualizáveis)
│   ├── __init__.py
│   ├── database.py
│   ├── updater.py
│   ├── cte_service.py
│   └── ... (todos os .py)
└── _internal/                 ← Bibliotecas compiladas (PyInstaller)
    ├── python312.dll
    ├── PyQt5/
    ├── Icone/                 ← Ícones (dentro de _internal)
    ├── Arquivo_xsd/           ← XSDs de validação
    └── ... (todas as libs)
```

## 🔄 Como Funcionam as Atualizações

### Arquivos na Raiz (Atualizáveis remotamente via GitHub)
- `nfe_search.py` - Módulo principal de busca
- `modules/*.py` - Todos os módulos Python
- `version.txt` - Versão instalada
- `CHANGELOG.md` - Changelog

**Estes arquivos são substituídos quando o usuário clica em "🔄 Atualizações"**

### Arquivos em _internal (Só mudam com reinstalação)
- Bibliotecas compiladas (PyQt5, lxml, etc)
- Python runtime
- DLLs do sistema
- Ícones e XSDs

**Estes arquivos NÃO são atualizados remotamente - requerem nova compilação**

## 🎯 Por que esta Estrutura?

### Modo OnDir (não OnFile)
- Permite atualizar .py sem recompilar
- Arquivos .py ficam na raiz (fora de _internal)
- Executável pode importar dinamicamente

### Benefícios
✅ Usuário pode receber atualizações de código sem reinstalar
✅ Correções de bugs podem ser distribuídas rapidamente
✅ Novas funcionalidades podem ser adicionadas sem novo instalador

### Limitações
⚠️ Mudanças em bibliotecas (PyQt5, lxml) requerem reinstalação
⚠️ Novos arquivos binários (.dll, .so) requerem reinstalação
⚠️ Mudanças no Python runtime requerem reinstalação

## 📦 Instalação via Inno Setup

O `installer.iss` copia **TODA** a pasta `dist\BOT Busca NFE\` para o PC do usuário:

```
C:\Program Files\BOT Busca NFE\
├── BOT Busca NFE.exe
├── nfe_search.py              ← Será atualizado pelo sistema
├── version.txt                ← Será atualizado pelo sistema
├── modules/                   ← Será atualizado pelo sistema
└── _internal/                 ← Nunca muda após instalação
```

## 🛠️ Dados do Usuário (Separados)

Dados sensíveis ficam em `%APPDATA%\BOT Busca NFE\`:

```
C:\Users\[Usuario]\AppData\Roaming\BOT Busca NFE\
├── nfe_data.db               ← Banco de dados
├── xmls/                     ← XMLs baixados
├── logs/                     ← Arquivos de log
└── config/                   ← Configurações
```

**Estes dados NÃO são afetados por atualizações ou reinstalações**

## ⚙️ Processo de Build Completo

### 1. Compilação (build.bat)
```bash
# Compila com PyInstaller (onedir mode)
pyinstaller --clean BOT_Busca_NFE.spec

# Copia .py para a raiz de dist
copy nfe_search.py "dist\BOT Busca NFE\"
xcopy modules\*.py "dist\BOT Busca NFE\modules\"
```

### 2. Criação do Instalador (Inno Setup)
```
# installer.iss empacota tudo de dist\BOT Busca NFE\
Source: "dist\BOT Busca NFE\*"
DestDir: "{app}"
Flags: recursesubdirs createallsubdirs
```

### 3. Resultado Final
- `Output\BOT_Busca_NFE_Setup.exe` - Instalador Windows
- Contém executável + bibliotecas + código atualizável

## 🚀 Sistema de Atualização Automática

### Como funciona
1. Usuário clica em "🔄 Atualizações" no menu Tarefas
2. Sistema verifica `version.txt` no GitHub
3. Se houver nova versão, baixa:
   - `nfe_search.py`
   - `modules/*.py`
   - `version.txt`
   - `CHANGELOG.md`
4. Faz backup dos arquivos antigos em `backups/`
5. Substitui os arquivos
6. Usuário reinicia o aplicativo

### O que NÃO é atualizado automaticamente
- ❌ Executável (.exe)
- ❌ Bibliotecas Python (PyQt5, lxml, etc)
- ❌ DLLs do sistema
- ❌ Python runtime
- ❌ Ícones e XSDs

Para estas mudanças, é necessário:
1. Recompilar com `build.bat`
2. Gerar novo instalador
3. Distribuir e reinstalar

## 📝 Checklist de Verificação

Antes de distribuir, certifique-se:

- [ ] `build.bat` executado com sucesso
- [ ] Pasta `dist\BOT Busca NFE\` contém:
  - [ ] `BOT Busca NFE.exe`
  - [ ] `nfe_search.py`
  - [ ] `modules/` com todos os .py
  - [ ] `version.txt`
  - [ ] `CHANGELOG.md`
  - [ ] `_internal/` com todas as libs
- [ ] `installer.iss` compila sem erros
- [ ] `Output\BOT_Busca_NFE_Setup.exe` criado
- [ ] Código enviado para GitHub (para atualizações remotas)

## 🐛 Solução de Problemas Comuns

### Erro: "nfe_search.py não encontrado"
- **Causa**: build.bat não copiou os .py
- **Solução**: Execute build.bat novamente

### Erro: "Módulo não encontrado" após instalação
- **Causa**: PyInstaller não incluiu alguma lib em _internal
- **Solução**: Adicione em `hidden_imports` no .spec

### Atualização não funciona
- **Causa**: Arquivos .py não estão na raiz
- **Solução**: Verifique estrutura de dist\BOT Busca NFE\

### Erro de permissão ao atualizar
- **Causa**: Aplicativo instalado em Program Files (admin)
- **Solução**: Execute como administrador ou instale em pasta do usuário

## 📞 Suporte

- **Desenvolvedor**: DWM System Developer
- **Site**: https://dwmsystems.up.railway.app/
- **GitHub**: https://github.com/W4lterBr/NF-e

---

**Última atualização**: Dezembro 2025
