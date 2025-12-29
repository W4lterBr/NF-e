# 📦 BOT Busca NFE - Sistema Automatizado de Busca e Gestão de Notas Fiscais

> Sistema completo para consulta, download e organização automática de NFe, CT-e e NFS-e diretamente da SEFAZ

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

## 🎯 Sobre o Projeto

O **BOT Busca NFE** é uma aplicação desktop desenvolvida para automatizar completamente o processo de busca, download e organização de documentos fiscais eletrônicos. Conecta-se diretamente aos webservices da SEFAZ utilizando certificados digitais A1, dispensando a necessidade de acessar portais manualmente.

### 🌟 Principais Funcionalidades

- 🔍 **Busca Automática na SEFAZ**
  - Consulta distribuição de DFe (NFe e CT-e)
  - Busca por NSU (Número Sequencial Único)
  - Busca por chave de acesso individual ou em lote
  - Atualização automática em intervalos configuráveis

- 📁 **Organização Inteligente**
  - Estrutura hierárquica por certificado/CNPJ
  - Separação por ano-mês de emissão
  - Categorização por tipo (NFe, CTe, Eventos, Resumos)
  - Nomes personalizados para certificados
  - Duplo armazenamento (backup + pasta configurada)

- 🔐 **Segurança e Certificados**
  - Suporte a múltiplos certificados A1
  - Senhas criptografadas no banco de dados
  - Substituição de certificados mantendo histórico
  - Auto-detecção de UF e razão social via API Brasil

- 📄 **Geração de PDFs**
  - Conversão automática de XML → PDF (DANFE/DACTE)
  - Geração em lote de PDFs
  - Abertura rápida com cache otimizado
  - Visualização de eventos e detalhes completos

- 💾 **Gestão de Dados**
  - Banco de dados SQLite integrado
  - Registro completo de status e protocolos
  - Tabelas emitidos por terceiros vs emitidos pela empresa
  - Filtros avançados e ordenação
  - Exportação e backup de dados

- 🔄 **Sistema de Atualização**
  - Atualização automática via GitHub
  - Versionamento semântico
  - Backup automático antes de atualizar
  - Sem necessidade de reinstalação

## 🚀 Instalação

### Pré-requisitos

- Windows 10/11 (64 bits)
- Python 3.10 ou superior
- Certificado digital A1 (.pfx)
- Conexão com internet

### Opção 1: Instalador Windows (Recomendado)

1. Baixe o instalador mais recente: `BOT_Busca_NFE_Setup.exe`
2. Execute o instalador e siga as instruções
3. Pronto! O aplicativo está instalado e pronto para uso

### Opção 2: Instalação Manual (Desenvolvimento)

```bash
# Clone o repositório
git clone https://github.com/W4lterBr/NF-e.git
cd NF-e

# Crie ambiente virtual
python -m venv .venv

# Ative o ambiente (Windows)
.venv\Scripts\activate

# Instale dependências
pip install -r requirements.txt

# Execute a aplicação
python interface_pyqt5.py
```

## 📖 Como Usar

### 1️⃣ Configuração Inicial

1. **Adicionar Certificado:**
   - Menu **Configurações** → **Certificados**
   - Clique em **"Adicionar Certificado"**
   - Selecione seu arquivo `.pfx` e informe a senha
   - (Opcional) Dê um nome personalizado para o certificado

2. **Configurar Armazenamento (Opcional):**
   - Menu **Configurações** → **📁 Armazenamento**
   - Escolha a pasta onde deseja salvar os XMLs e PDFs
   - Configure formato de organização de pastas

### 2️⃣ Buscando Notas Fiscais

**Busca Automática:**
- Clique em **"Buscar na SEFAZ"** na barra de ferramentas
- O sistema consultará automaticamente todos os certificados cadastrados
- Novos documentos serão baixados e organizados

**Busca Completa (Reset):**
- Menu **Configurações** → **Busca Completa**
- Reseta NSU para zero e busca todo o histórico disponível
- ⚠️ Pode demorar dependendo do volume de documentos

**Busca por Chave:**
- Menu **Configurações** → **Busca por chave**
- Digite a chave de 44 dígitos ou importe arquivo TXT
- Sistema busca o XML completo na SEFAZ

### 3️⃣ Visualizando e Gerenciando

- **Duplo clique** em qualquer linha abre o PDF automaticamente
- **Botão direito** para menu de contexto:
  - Ver detalhes completos
  - Buscar XML completo (se resumo)
  - Ver eventos relacionados
  - Copiar chave/CNPJ

### 4️⃣ Abas da Interface

- **📥 Emitidos por terceiros:** Notas recebidas (destinatário é sua empresa)
- **📤 Emitidos pela empresa:** Notas emitidas (emitente é sua empresa)
- **🗂️ Certificados (lateral):** Filtro por certificado específico

## ⚙️ Configurações Avançadas

### Intervalo de Busca

Configure o intervalo entre buscas automáticas (1-23 horas):
- Padrão: **1 hora**
- Ajustável na barra de ferramentas

### Consulta de Status

Habilite/desabilite consulta automática de status via protocolo:
- ✅ Habilitado: Busca status de notas pendentes
- ❌ Desabilitado: Acelera busca de novos documentos

### Armazenamento Duplo

O sistema mantém **dois locais de armazenamento**:

1. **`xmls/`** - Backup local permanente (sempre salvo)
2. **Pasta configurada** - Armazenamento principal (configurável)

```
Estrutura de pastas:
xmls/
├── [Nome_Certificado ou CNPJ]/
│   └── [ANO-MES]/
│       ├── NFe/
│       │   ├── 12345-EMPRESA_LTDA.xml
│       │   └── 12345-EMPRESA_LTDA.pdf
│       ├── CTe/
│       ├── Eventos/
│       └── Resumos/
```

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Descrição |
|------------|-----------|
| **Python 3.10+** | Linguagem principal |
| **PyQt5** | Interface gráfica |
| **lxml** | Parsing de XML |
| **Zeep** | Cliente SOAP para SEFAZ |
| **requests-pkcs12** | Autenticação com certificado |
| **cryptography** | Criptografia de senhas |
| **ReportLab** | Geração de PDFs |
| **SQLite** | Banco de dados local |

## 📂 Estrutura do Projeto

```
BOT-Busca-NFE/
├── interface_pyqt5.py          # Interface principal (PyQt5)
├── nfe_search.py               # Lógica de busca SEFAZ
├── requirements.txt            # Dependências Python
├── version.txt                 # Versão atual (1.0.21)
├── BOT_Busca_NFE.spec         # Config PyInstaller
├── installer.iss               # Config Inno Setup
├── build.bat                   # Script de compilação
│
├── modules/                    # Módulos do sistema
│   ├── database.py            # Gerenciamento de banco
│   ├── cte_service.py         # Serviço de CT-e
│   ├── updater.py             # Sistema de atualização
│   ├── pdf_simple.py          # Geração de PDF
│   └── ...
│
├── Arquivo_xsd/               # Schemas XSD SEFAZ
├── Icone/                     # Ícones da interface
├── xmls/                      # Armazenamento local (backup)
└── logs/                      # Logs de execução
```

## 🔄 Atualizações Automáticas

O sistema verifica e aplica atualizações automaticamente:

1. Menu **Configurações** → **🔄 Atualizações** (ou `Ctrl+U`)
2. Sistema verifica versão no GitHub
3. Se houver atualização, faz backup e atualiza arquivos Python
4. Reinicia automaticamente com nova versão

**Arquivos atualizáveis remotamente:**
- ✅ Todos os arquivos `.py`
- ✅ `version.txt` e `CHANGELOG.md`

**Requerem reinstalação:**
- ❌ Executável `.exe`
- ❌ Bibliotecas Python (PyQt5, lxml, etc)

## 🐛 Resolução de Problemas

### Erro 656 - Excesso de Consultas

**Sintoma:** Sistema informa bloqueio temporário  
**Causa:** SEFAZ limita consultas (máx. 100/hora por certificado)  
**Solução:** Sistema aguarda automaticamente o tempo necessário (65 minutos)

### XMLs não aparecem na interface

**Verificar:**
1. Certificado está ativo? (Menu Certificados)
2. Filtros aplicados? (Campo de busca, status, tipo)
3. Limite de linhas configurado? (Dropdown "Exibir")
4. Clique em **Atualizar** (F5)

### PDF não abre ou não gera

**Solução:**
1. Verifique se o XML é completo (não apenas resumo)
2. Use menu de contexto → "Buscar XML completo"
3. Em último caso: Menu → PDFs em lote

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📋 Notas Técnicas

### Conformidade SEFAZ

O sistema segue rigorosamente a **NT 2014.002 v1.60** da SEFAZ:

- ✅ Serviço: `NFeDistribuicaoDFe`
- ✅ Estrutura: `distNSU` com `ultNSU`
- ✅ Validação: Schemas XSD v1.01
- ✅ Sincronização: Loop até `ultNSU == maxNSU`
- ✅ Tratamento de erros: 137 (1h), 656 (65min)
- ✅ Limite: 50 documentos por chamada

### Segurança

- 🔐 Senhas de certificados criptografadas (Fernet)
- 🔐 Chave de criptografia única por instalação
- 🔐 Dados sensíveis nunca em logs
- 🔐 Certificados apenas em memória durante uso

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**DWM System Developer**

- 🌐 Website: [https://dwmsystems.up.railway.app/](https://dwmsystems.up.railway.app/)
- 💼 GitHub: [@W4lterBr](https://github.com/W4lterBr)

## 🙏 Agradecimentos

- Receita Federal e SEFAZ pela documentação dos webservices
- Comunidade Python Brasil
- Colaboradores e usuários que reportam bugs e sugestões

---

⭐ Se este projeto foi útil para você, considere dar uma estrela no GitHub!

**Versão atual:** 1.0.21  
**Última atualização:** Dezembro 2025
