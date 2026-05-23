# 🚀 INSTALADOR AUTOMÁTICO INTELIGENTE

## 📋 Visão Geral

O **`instalar_auto.bat`** é um script de instalação automático e inteligente que detecta Python automaticamente e configura todo o ambiente sem intervenção manual.

---

## ⚡ Uso Rápido

```bash
# Basta executar:
instalar_auto.bat
```

**Pronto!** O script faz tudo sozinho:
- Detecta Python
- Cria ambiente virtual
- Instala todas as dependências
- Verifica a instalação

---

## 🎯 Funcionalidades

### 🔍 **Detecção Automática de Python**

O script tenta encontrar Python em múltiplas localizações:

1. ✅ **`py` launcher** (Windows Python Launcher) - Método recomendado
2. ✅ **`python`** - No PATH do sistema
3. ✅ **`python3`** - Alternativo no PATH
4. ✅ **Locais comuns de instalação**:
   - `C:\Python312\`
   - `C:\Python311\`
   - `C:\Python310\`
   - `%LOCALAPPDATA%\Programs\Python\Python312\`
   - `%LOCALAPPDATA%\Programs\Python\Python311\`
   - `%LOCALAPPDATA%\Programs\Python\Python310\`

### ✔️ **Verificação de Versão**

- Detecta a versão exata do Python instalado
- Valida se é Python 3.10, 3.11 ou 3.12
- Exibe mensagem clara se versão incompatível

### 🔧 **Configuração do Ambiente**

- Cria ambiente virtual (`.venv`)
- Verifica integridade do ambiente
- Recria automaticamente se corrompido
- Ativa o ambiente virtual

### 📦 **Instalação de Dependências**

- Atualiza pip para versão mais recente
- Instala todas as dependências de `requirements.txt`
- **Sistema de retry**: 3 tentativas automáticas em caso de falha
- Mensagens de progresso detalhadas

### ✅ **Verificação Final**

Testa importação dos pacotes críticos:
- ✓ PyQt5
- ✓ lxml
- ✓ requests
- ✓ zeep
- ✓ cryptography

---

## 📊 Processo de Instalação

```
┌─────────────────────────────────────────────┐
│ [ETAPA 1/6] Detectando Python instalado    │
│   ► Tentando py launcher...                │
│   ✓ Encontrado: Python 3.12.0              │
├─────────────────────────────────────────────┤
│ [ETAPA 2/6] Verificando versão             │
│   ✓ Versão compatível: Python 3.12.0       │
├─────────────────────────────────────────────┤
│ [ETAPA 3/6] Configurando ambiente virtual  │
│   ✓ Ambiente virtual criado                │
├─────────────────────────────────────────────┤
│ [ETAPA 4/6] Ativando ambiente virtual      │
│   ✓ Ambiente virtual ativado               │
├─────────────────────────────────────────────┤
│ [ETAPA 5/6] Atualizando pip                │
│   ✓ pip atualizado                         │
├─────────────────────────────────────────────┤
│ [ETAPA 6/6] Instalando dependências        │
│   ✓ Todas as dependências instaladas!     │
├─────────────────────────────────────────────┤
│ VERIFICANDO PACOTES CRÍTICOS...            │
│   ✓ PyQt5                                  │
│   ✓ lxml                                   │
│   ✓ requests                               │
│   ✓ zeep                                   │
│   ✓ cryptography                           │
└─────────────────────────────────────────────┘

╔═══════════════════════════════════════════╗
║  ✓ INSTALAÇÃO CONCLUÍDA COM SUCESSO!     ║
╚═══════════════════════════════════════════╝
```

---

## 🆘 Tratamento de Erros

### ❌ **Python não encontrado**

```
[✗] ERRO: Python não encontrado!

┌────────────────────────────────────────────┐
│  SOLUÇÃO:                                  │
│                                            │
│  1. Baixe Python 3.10, 3.11 ou 3.12:      │
│     https://www.python.org/downloads/     │
│                                            │
│  2. Durante a instalação, MARQUE:         │
│     [✓] Add Python to PATH                │
│     [✓] Install for all users (opcional)  │
│                                            │
│  3. Após instalar, execute novamente      │
└────────────────────────────────────────────┘
```

### ❌ **Versão incompatível**

```
[✗] ERRO: Python 3.10+ necessário!

    Versão atual: Python 3.9.0
    Versão mínima: Python 3.10.0

Instale Python 3.10, 3.11 ou 3.12 e tente novamente.
```

### ❌ **Falha na instalação**

```
[✗] ERRO: Falha ao instalar dependências após 3 tentativas!

┌────────────────────────────────────────────┐
│  SOLUÇÕES:                                 │
│                                            │
│  1. Verifique sua conexão com a internet  │
│  2. Desative temporariamente o antivírus  │
│  3. Tente instalar manualmente:           │
│     .venv\Scripts\activate                │
│     pip install -r requirements.txt       │
│                                            │
│  4. Use o requirements-frozen.txt:        │
│     pip install -r requirements-frozen.txt│
└────────────────────────────────────────────┘
```

---

## 🔧 Recursos Avançados

### 🔄 **Sistema de Retry**

Se a instalação falhar (problema de rede, timeout, etc.), o script:
- Aguarda 3 segundos
- Tenta novamente automaticamente
- Até 3 tentativas no total

### 🛡️ **Validação de Integridade**

Verifica se o ambiente virtual está íntegro:
- Arquivo `activate.bat` existe?
- Executável `python.exe` existe?
- Se corrompido, recria automaticamente

### 📝 **Encoding UTF-8**

```batch
chcp 65001 >nul
```
Garante exibição correta de caracteres especiais (✓, ✗, ►, etc.)

### 🎨 **Interface Visual**

- Caixas e bordas decorativas
- Ícones visuais (✓, ✗, ►, !)
- Cores e formatação clara
- Barra de título personalizada

---

## 📊 Comparação com `instalar.bat`

| Funcionalidade | `instalar.bat` | `instalar_auto.bat` |
|----------------|----------------|---------------------|
| Detecta Python no PATH | ✅ | ✅ |
| Detecta py launcher | ❌ | ✅ |
| Busca em locais comuns | ❌ | ✅ |
| Verifica versão | ✅ | ✅ |
| Sistema de retry | ❌ | ✅ (3x) |
| Valida integridade venv | ❌ | ✅ |
| Verifica pacotes críticos | ❌ | ✅ |
| Interface visual | Simples | Avançada |
| Mensagens de erro detalhadas | Básicas | Completas |

---

## 🎯 Quando Usar

### ✅ Use `instalar_auto.bat` quando:

- 🔹 Primeira instalação em um PC novo
- 🔹 Não sabe onde o Python está instalado
- 🔹 Quer detecção automática total
- 🔹 Conexão de internet instável (retry automático)
- 🔹 Precisa de verificação completa

### ✅ Use `instalar.bat` quando:

- 🔹 Python já está no PATH
- 🔹 Quer script mais simples
- 🔹 Ambiente já está configurado parcialmente

---

## 🧪 Testado em:

- ✅ Windows 10 (64-bit)
- ✅ Windows 11 (64-bit)
- ✅ Python 3.10.x
- ✅ Python 3.11.x
- ✅ Python 3.12.x
- ✅ PowerShell 5.1
- ✅ CMD (Prompt de Comando)

---

## 🔍 Logs e Diagnóstico

O script fornece logs detalhados em tempo real:

```
[►] = Em progresso
[✓] = Sucesso
[✗] = Erro crítico
[!] = Aviso
```

**Exemplo de log completo:**

```
[►] Tentando: py launcher (py.exe)...
[✓] Encontrado: Python 3.12.0 (py launcher)
[►] Versão detectada: Python 3.12.0
[✓] Versão compatível: Python 3.12.0
[►] Criando ambiente virtual...
[✓] Ambiente virtual criado com sucesso
[►] Python do venv: C:\Busca NFE\.venv
[✓] pip atualizado
[►] pip 24.3.1 from C:\Busca NFE\.venv\lib\site-packages\pip (python 3.12)
[►] Instalando pacotes... (isso pode levar 5-10 minutos)
[✓] Todas as dependências foram instaladas com sucesso!
```

---

## 💡 Dicas

### 🔧 **Se o Python não for detectado:**

1. Reinstale Python marcando "Add Python to PATH"
2. Adicione manualmente ao PATH:
   - Painel de Controle → Sistema → Variáveis de Ambiente
   - Adicione: `C:\Python312` e `C:\Python312\Scripts`
3. Use `py --list` para ver versões instaladas

### 🔧 **Se a instalação falhar:**

1. Desative antivírus temporariamente
2. Use `requirements-frozen.txt`:
   ```batch
   .venv\Scripts\activate
   pip install -r requirements-frozen.txt
   ```
3. Instale manualmente pacote por pacote

### 🔧 **Para atualizar dependências:**

```batch
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

---

## 📞 Suporte

- 📚 **Documentação completa:** [INSTALACAO.md](INSTALACAO.md)
- 🔍 **Verificação:** Execute `python verificar_instalacao.py` após instalação
- 🚀 **Execução:** Use `executar.bat` para iniciar o sistema

---

**Desenvolvido por:** DWM System Developer  
**Versão:** 1.0.96  
**Data:** 06/02/2026  
**Compatibilidade:** Windows 10/11 + Python 3.10+
