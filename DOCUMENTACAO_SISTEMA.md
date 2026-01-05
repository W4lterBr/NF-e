# Documentação do Sistema Busca XML

## 📋 Visão Geral

**Busca XML** é um sistema desktop desenvolvido em Python com PyQt5 para automação de download e gerenciamento de documentos fiscais eletrônicos brasileiros (NF-e, NFC-e, CT-e) através da SEFAZ.

### Funcionalidades Principais

1. **Download Automático de Documentos Fiscais**
   - NF-e (Nota Fiscal Eletrônica) - Modelo 55
   - NFC-e (Nota Fiscal ao Consumidor Eletrônica) - Modelo 65
   - CT-e (Conhecimento de Transporte Eletrônico) - Modelo 57

2. **Geração de PDFs** (DANFE/DACTE)
   - Conversão automática de XML para PDF
   - Múltiplos geradores: BRASNFe, NFePy, fallback simplificado
   - Geração em background para não travar interface

3. **Consultas SEFAZ**
   - Download por distribuição DFe (NSU)
   - Consulta por chave de acesso
   - Consulta de status/protocolo
   - Sistema de retry com tratamento de erro 656

4. **Busca e Filtros Avançados**
   - Busca por CNPJ emitente/destinatário
   - Filtro por valor, data, tipo de documento
   - Busca por chave de acesso
   - Filtro por status (autorizado, cancelado, etc)

5. **Gestão de Certificados Digitais A1**
   - Cadastro de múltiplos certificados
   - Criptografia de senhas
   - Validação de validade
   - Associação automática de UF e razão social

6. **Sistema de Atualização Automática**
   - Verificação de versões no GitHub
   - Download e instalação automática via GitHub Releases
   - Fallback para atualização de arquivos individuais

---

## 🏗️ Arquitetura do Sistema

### Estrutura de Diretórios

```
BOT - Busca NFE/
├── interface_pyqt5.py           # Interface principal (GUI)
├── nfe_search.py                # Motor de busca de NF-e/CT-e
├── nfse_search.py               # Motor de busca de NFS-e (futuro)
├── app.manifest                 # Manifesto Windows
├── build.bat                    # Script de compilação
├── installer.iss                # Configuração Inno Setup
├── version.txt                  # Versão atual
├── modules/
│   ├── database.py              # Gerenciamento SQLite
│   ├── updater.py               # Sistema de atualização
│   ├── certificate_manager.py  # Gestão de certificados
│   ├── certificate_dialog.py   # Diálogo de cadastro
│   ├── sefaz_integration.py    # Integração SEFAZ
│   ├── cte_service.py           # Serviços CT-e
│   ├── pdf_generator.py        # Geração de PDFs
│   ├── pdf_simple.py            # PDF fallback simplificado
│   ├── sandbox_worker.py        # Worker isolado
│   ├── sandbox_task.py          # Tarefas em sandbox
│   ├── crypto_portable.py       # Criptografia de senhas
│   └── ...
└── Arquivo_xsd/                 # Schemas XSD para validação
```

### Localização de Dados do Usuário

**Em desenvolvimento**: Pasta do projeto
**Em produção (executável)**: `C:\Users\[Usuario]\AppData\Roaming\Busca XML\`

```
Busca XML/
├── logs/
│   └── busca_nfe_YYYY-MM-DD.log
├── xmls/
│   ├── [CNPJ_INFORMANTE]/
│   │   ├── NFE/
│   │   │   └── YYYY-MM/
│   │   │       ├── [chave].xml
│   │   │       └── [chave].pdf
│   │   └── CTE/
│   │       └── YYYY-MM/
│   │           ├── [chave].xml
│   │           └── [chave].pdf
│   └── Debug de notas/         # XMLs de resposta SEFAZ
├── notas.db                     # Banco SQLite
└── config.json                  # Configurações
```

---

## 🔧 Componentes Principais

### 1. Interface (interface_pyqt5.py)

**Classe Principal**: `MainWindow(QMainWindow)`

#### Elementos da Interface

- **Barra de Menu**:
  - Arquivo: Abrir pasta, Abrir logs, Exportar, Sair
  - Certificados: Gerenciar certificados
  - Tarefas: Buscar, Busca Completa, Download por Chave, Lote de PDFs
  - Configurações: SEFAZ, Atualizações

- **Toolbar**: Botões de ação rápida com ícones nativos Qt

- **Área Principal**:
  - Lista de certificados (sidebar esquerda)
  - Tabela de documentos (centro)
  - Filtros e busca (superior)
  - Barra de status e progresso (inferior)

- **System Tray**: Ícone na bandeja com menu

#### Funcionalidades Principais

```python
def do_search(self):
    """Busca automática de documentos na SEFAZ"""
    # 1. Marca busca em andamento
    # 2. Reseta estatísticas
    # 3. Mostra progress bar
    # 4. Executa run_search em thread separada
    # 5. Atualiza interface com progresso em tempo real
    # 6. Agenda próxima busca automática
```

```python
def do_busca_completa(self):
    """Busca completa: reseta NSU e baixa tudo"""
    # 1. Confirma operação com usuário
    # 2. Reseta NSU para 000000000000000
    # 3. Limpa bloqueios de erro 656
    # 4. Executa busca com progresso detalhado
    # 5. Mostra X/Y certificados processados
```

```python
def refresh_all(self):
    """Atualiza tabela de documentos"""
    # 1. Busca no banco de dados (filtros aplicados)
    # 2. Popula tabela com resultados
    # 3. Estiliza linhas (cores por status)
```

```python
def check_updates(self):
    """Verifica e aplica atualizações"""
    # 1. Consulta GitHub API
    # 2. Compara versões
    # 3. Download de instalador ou arquivos
    # 4. Execução automática
```

### 2. Motor de Busca (nfe_search.py)

**Função Principal**: `run_search(progress_cb=None)`

#### Fluxo de Busca

```python
def run_search(progress_cb=None):
    """
    1. FASE 1: Download de Documentos
       - Para cada certificado:
         a) Busca NF-e via distribuição DFe
         b) Busca CT-e via distribuição DFe
         c) Salva XMLs e registra no banco
         d) Atualiza NSU
    
    2. FASE 2: Consulta de Status
       - Para chaves sem protocolo:
         a) Consulta status na SEFAZ
         b) Atualiza informações no banco
    
    3. Retorna estatísticas
    """
```

#### Processamento de NF-e

```python
def processar_nfe(chave, xml_nfe, informante, caminho_xml):
    """
    - Extrai dados do XML (emitente, destinatário, valores)
    - Identifica tipo: NFE (modelo 55) ou NFCE (modelo 65)
    - Salva XML na pasta apropriada
    - Registra no banco de dados
    - Retorna resumo dos dados
    """
```

#### Processamento de CT-e

```python
def processar_cte(chave, xml_cte, informante, caminho_xml):
    """
    - Extrai dados do CT-e
    - Salva na pasta CTE/YYYY-MM
    - Registra no banco
    - Retorna resumo dos dados
    """
```

#### Tratamento de Erro 656

O erro 656 indica "consumo indevido" da SEFAZ, exigindo espera de 1 hora antes de nova consulta.

```python
def verificar_bloqueio_656(informante, tipo='nfe'):
    """
    Verifica se certificado está bloqueado por erro 656.
    Retorna True se bloqueado, False se pode buscar.
    """

def registrar_bloqueio_656(informante, tipo='nfe'):
    """
    Registra bloqueio de erro 656 com timestamp.
    Certificado ficará bloqueado por 1 hora.
    """
```

### 3. Banco de Dados (modules/database.py)

**Classe**: `DatabaseManager`

#### Tabelas Principais

```sql
-- Certificados digitais
CREATE TABLE certificados (
    id INTEGER PRIMARY KEY,
    cnpj_cpf TEXT UNIQUE,
    informante TEXT,
    razao_social TEXT,
    caminho TEXT,
    senha TEXT,  -- criptografada
    cUF_autor TEXT,
    criado_em TIMESTAMP
)

-- Documentos (NF-e, NFC-e, CT-e)
CREATE TABLE notas (
    id INTEGER PRIMARY KEY,
    chave TEXT UNIQUE,
    informante TEXT,
    tipo TEXT,  -- NFE, NFCE, CTE
    numero TEXT,
    data_emissao TEXT,
    cnpj_emitente TEXT,
    nome_emitente TEXT,
    cnpj_destinatario TEXT,
    nome_destinatario TEXT,
    valor REAL,
    status TEXT,
    protocolo TEXT,
    xml_status TEXT,
    criado_em TIMESTAMP
)

-- Controle de NSU (NF-e)
CREATE TABLE nsu (
    informante TEXT PRIMARY KEY,
    ult_nsu TEXT
)

-- Controle de NSU (CT-e)
CREATE TABLE nsu_cte (
    informante TEXT PRIMARY KEY,
    ult_nsu TEXT
)

-- Bloqueios de erro 656
CREATE TABLE erro_656 (
    informante TEXT,
    tipo TEXT,  -- nfe ou cte
    bloqueado_em TIMESTAMP,
    PRIMARY KEY (informante, tipo)
)

-- Registro de downloads
CREATE TABLE downloads_xml (
    chave TEXT PRIMARY KEY,
    caminho_arquivo TEXT,
    informante TEXT,
    baixado_em TIMESTAMP
)
```

### 4. Geração de PDFs (modules/pdf_generator.py)

**Ordem de Tentativa de Geradores**:

1. **BRASNFe** (prioritário)
2. **NFePy** (fallback)
3. **PDF Simplificado** (último recurso)

```python
def generate_pdf(xml_path, tipo='NFe'):
    """
    1. Identifica tipo (NFe, NFCe, CTe)
    2. Tenta BRASNFe
    3. Se falhar, tenta NFePy
    4. Se falhar, gera PDF simplificado
    5. Salva no mesmo diretório do XML
    """
```

#### PDF Simplificado (modules/pdf_simple.py)

Usado quando bibliotecas especializadas falham:

```python
def gerar_danfe_simplificado(xml_path, pdf_path):
    """
    Extrai dados principais do XML e gera PDF básico com ReportLab:
    - Cabeçalho com dados da nota
    - Emitente e destinatário
    - Produtos/serviços
    - Totais
    - Chave de acesso com código de barras
    """
```

### 5. Sistema de Atualização (modules/updater.py)

**Classe**: `GitHubUpdater`

#### Fluxo de Atualização

```python
def check_for_updates():
    """
    1. Lê version.txt local
    2. Consulta GitHub API (tags)
    3. Compara versões
    4. Retorna (has_update, current, remote)
    """

def apply_update(progress_callback):
    """
    MÉTODO 1 (Executável):
        1. Busca última release no GitHub
        2. Download do instalador .exe
        3. Executa instalador com /VERYSILENT
        4. Retorna sucesso
    
    MÉTODO 2 (Fallback/Dev):
        1. Lista arquivos Python a atualizar
        2. Download arquivo por arquivo
        3. Cria backups
        4. Substitui arquivos
        5. Retorna lista de atualizados
    """
```

### 6. Sandbox Worker (modules/sandbox_worker.py)

Sistema de execução isolada para tarefas pesadas (PDFs, SEFAZ).

```python
class SandboxWorker(QThread):
    """
    Executa tarefas em processo Python separado via subprocess.
    Evita travamento da interface e isolamento de erros.
    
    Tarefas suportadas:
    - generate_pdf: Geração de PDF
    - fetch_by_chave: Consulta SEFAZ por chave
    - check_protocolo: Verificação de protocolo
    """
```

---

## 🔄 Fluxos Principais

### Fluxo de Busca Automática

```
1. Timer dispara (intervalo configurado)
   ↓
2. do_search() é chamado
   ↓
3. Marca _search_in_progress = True
   ↓
4. Cria SearchWorker (QThread)
   ↓
5. run_search() executa em background
   ↓
6. Para cada certificado:
   ├─ Verifica bloqueio 656
   ├─ Busca NF-e (distribuição DFe)
   ├─ Busca CT-e (distribuição DFe)
   ├─ Processa XMLs recebidos
   ├─ Salva em xmls/[informante]/[tipo]/[ano-mes]/
   ├─ Registra no banco
   └─ Atualiza NSU
   ↓
7. Consulta status de chaves pendentes
   ↓
8. Atualiza interface com resultados
   ↓
9. Gera PDFs dos novos XMLs em background
   ↓
10. Agenda próxima busca (intervalo configurado)
```

### Fluxo de Busca Completa

```
1. Usuário clica "Busca Completa"
   ↓
2. Confirmação de operação
   ↓
3. Reseta NSU para 000000000000000 (todos certificados)
   ↓
4. Limpa bloqueios erro 656
   ↓
5. Executa busca normal
   ↓
6. Progresso detalhado:
   - X/Y certificados processados
   - Contador NFEs encontradas
   - Contador CTes encontrados
   - Tempo decorrido
   ↓
7. Resumo final com estatísticas
```

### Fluxo de Download por Chave

```
1. Usuário informa chave de 44 dígitos
   ↓
2. Sistema extrai UF e CNPJ da chave
   ↓
3. Seleciona certificado apropriado
   ↓
4. Envia solicitação SEFAZ (NFeDistribuicaoDFe)
   ↓
5. Processa resposta:
   ├─ XML completo (nfeProc/procCTe)
   ├─ Ou busca complementar por protocolo
   └─ Salva XML e gera PDF
   ↓
6. Registra no banco de dados
   ↓
7. Atualiza interface
```

### Fluxo de Geração de PDF

```
1. Identifica XML sem PDF
   ↓
2. Cria PDFWorker (QThread)
   ↓
3. SandboxWorker executa em processo isolado
   ↓
4. Ordem de tentativa:
   ├─ BRASNFe
   ├─ NFePy  
   └─ PDF Simplificado (fallback)
   ↓
5. PDF salvo no mesmo diretório do XML
   ↓
6. Status atualizado na interface
```

### Fluxo de Atualização

```
1. Usuário clica "Atualizações" (ou Ctrl+U)
   ↓
2. GitHubUpdater consulta API
   ↓
3. Compara versões (local vs remote)
   ↓
4. Se nova versão disponível:
   ├─ Mostra diálogo de confirmação
   ├─ Usuário aceita
   ├─ Download do instalador (releases)
   ├─ Progresso: "📥 Baixando: 45%"
   ├─ Executa instalador /VERYSILENT
   └─ Reinicia aplicativo
   ↓
5. Se não há updates:
   └─ "Você já está na versão mais recente"
```

---

## ⚙️ Configurações Importantes

### Intervalos de Busca

```python
# interface_pyqt5.py
self.spin_intervalo = QSpinBox()
self.spin_intervalo.setRange(1, 24)  # 1 a 24 horas
self.spin_intervalo.setValue(2)       # Padrão: 2 horas
```

### Timeout de Conexões

```python
# nfe_search.py
TIMEOUT_CONEXAO = 30  # segundos
```

### Bloqueio Erro 656

```python
TEMPO_BLOQUEIO_656 = 60  # minutos (1 hora)
```

### Schemas XSD

Validação de XMLs contra schemas oficiais em `Arquivo_xsd/`.

---

## 🚀 Compilação e Deploy

### Compilar Aplicativo

```batch
build.bat
```

Processo:
1. Remove dist/ e build/
2. Compila com PyInstaller:
   - --onedir (pasta com dependências)
   - --windowed (sem console)
   - --icon Icone/icone.ico
   - Inclui version.txt
3. Cria dist/Busca XML/

### Criar Instalador

```batch
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Gera: `Output/Busca_XML_Setup.exe`

### Deploy Completo

```batch
deploy.bat
```

Automatiza:
1. Lê versão de version.txt
2. Compila aplicativo
3. Git add/commit/tag
4. Push para GitHub
5. Abre navegador para criar Release

### Criar Release no GitHub

1. Acesse: https://github.com/W4lterBr/NF-e/releases/new
2. Selecione tag (ex: v1.0.36)
3. Título: "Release v1.0.36 - [Descrição]"
4. Upload: `Output/Busca_XML_Setup.exe`
5. Publish release

---

## 🔒 Segurança

### Criptografia de Senhas

```python
# modules/crypto_portable.py
from cryptography.fernet import Fernet

# Chave derivada do certificado + salt
def encrypt_password(password, cert_path):
    """Criptografa senha usando Fernet"""
    
def decrypt_password(encrypted, cert_path):
    """Descriptografa senha"""
```

### Validação de Certificados

```python
# modules/certificate_manager.py
def validate_certificate(cert_path, password):
    """
    1. Tenta carregar certificado .pfx
    2. Valida senha
    3. Verifica data de validade
    4. Extrai CNPJ e razão social
    5. Retorna dados validados
    """
```

---

## 📊 Indicadores e Status

### Cores de Status na Tabela

```python
# interface_pyqt5.py
STATUS_COLORS = {
    'Autorizado': '#E8F5E9',      # Verde claro
    'Cancelado': '#FFEBEE',       # Vermelho claro
    'Denegado': '#FFF3E0',        # Laranja claro
    'Inutilizado': '#F5F5F5',     # Cinza
    'Rejeitado': '#FFCDD2',       # Vermelho
}
```

### Barra de Progresso

```python
# Busca em andamento
self.search_progress.setVisible(True)
self.search_progress.setRange(0, total_certificados)  # Determinada
# ou
self.search_progress.setRange(0, 0)  # Indeterminada

# Labels de status
self.search_summary_label.setText(
    f"🔄 NFes: {nfes} | CTes: {ctes} | Tempo: {elapsed}s"
)
```

---

## 🐛 Tratamento de Erros

### Erro 656 - Consumo Indevido

```python
if cStat == '656':
    registrar_bloqueio_656(informante, tipo='nfe')
    logger.warning(f"⚠️ Erro 656 - Bloqueado por 1 hora")
    continue  # Pula para próximo certificado
```

### Timeout de Conexão

```python
try:
    response = client.service.nfeDistDFeInteresse(nfeDist)
except requests.exceptions.Timeout:
    logger.error("Timeout na conexão com SEFAZ")
    continue
```

### Erros de Certificado

```python
try:
    pkcs12.load_key_and_certificates(
        cert_data, password.encode()
    )
except Exception as e:
    QMessageBox.critical(
        self, 
        "Erro", 
        f"Certificado inválido ou senha incorreta:\n{e}"
    )
```

---

## 📝 Logs

### Formato de Log

```
YYYY-MM-DD HH:MM:SS,mmm [LEVEL] Mensagem
```

### Níveis

- **INFO**: Operações normais
- **WARNING**: Avisos (erro 656, arquivos não encontrados)
- **ERROR**: Erros recuperáveis
- **CRITICAL**: Erros críticos

### Exemplos

```
2025-12-30 08:46:02,267 [INFO] === Início da busca ===
2025-12-30 08:46:05,123 [INFO] 📥 [12345678000190] Processando NSU: 000000000034592
2025-12-30 08:46:06,456 [WARNING] ⚠️ Erro 656 - Bloqueado por 1 hora
2025-12-30 08:46:10,789 [INFO] ✅ Fase 1 concluída: 15 documentos baixados
```

---

## 🔗 Referências de Código

### Principais Arquivos

- **interface_pyqt5.py** (6321 linhas): Interface gráfica completa
- **nfe_search.py** (2152 linhas): Motor de busca SEFAZ
- **modules/database.py**: Gerenciamento banco de dados
- **modules/updater.py**: Sistema de atualização
- **modules/pdf_generator.py**: Geração de PDFs

### Variáveis Globais Importantes

```python
# interface_pyqt5.py
BASE_DIR: Path        # Diretório base (desenvolvimento ou executável)
DATA_DIR: Path        # Dados do usuário (AppData/Busca XML)
DB_PATH: Path         # Caminho do banco SQLite

# Estados
_search_in_progress: bool        # Busca em andamento?
_next_search_time: datetime      # Próxima busca agendada
_search_worker: SearchWorker     # Thread de busca
_selected_cert_cnpj: str         # Certificado selecionado
```

### Signals/Slots PyQt5

```python
# Comunicação entre threads
class SearchWorker(QThread):
    finished_search = pyqtSignal(dict)
    progress_line = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

# Conexões
worker.finished_search.connect(on_finished)
worker.progress_line.connect(on_progress)
```

---

## 🎯 Roadmap e Melhorias Futuras

### Implementado

- ✅ Busca automática NF-e/CT-e
- ✅ Múltiplos certificados
- ✅ Geração de PDFs
- ✅ Sistema de atualização
- ✅ Busca completa com progresso
- ✅ Filtros avançados
- ✅ Tratamento erro 656
- ✅ Criptografia de senhas

### Planejado

- 🔲 Busca de NFS-e (Nota Fiscal de Serviço)
- 🔲 Integração com sistema financeiro
- 🔲 Relatórios e dashboards
- 🔲 Exportação Excel/CSV avançada
- 🔲 Validação automática de XMLs (XSD)
- 🔲 Configuração de múltiplas UFs por certificado

---

## 📞 Informações Técnicas

### Tecnologias

- **Python 3.11+**
- **PyQt5**: Interface gráfica
- **SQLite**: Banco de dados
- **Zeep**: Cliente SOAP SEFAZ
- **lxml**: Processamento XML
- **cryptography**: Criptografia
- **requests**: HTTP/API
- **ReportLab**: PDFs simplificados
- **PyInstaller**: Empacotamento

### Repositório

- **GitHub**: https://github.com/W4lterBr/NF-e
- **Branch**: main
- **Versionamento**: Semantic Versioning (X.Y.Z)

### Compatibilidade

- **Windows**: 10, 11
- **Arquitetura**: x64
- **.NET Framework**: Não requerido
- **Visual C++**: Redistribuível incluído no instalador

---

## 🆘 Troubleshooting

### Pasta de logs vazia

**Causa**: Nome de pasta incorreto em get_data_dir()
**Solução**: Verificar que todos usam `"Busca XML"` (não "BOT Busca NFE")

### XMLs não aparecem na interface

**Causa**: BASE_DIR usado no lugar de DATA_DIR
**Solução**: Operações de leitura devem usar DATA_DIR

### Erro 656 persistente

**Causa**: Bloqueio de 1 hora da SEFAZ
**Solução**: Sistema registra bloqueio e aguarda automaticamente

### PDFs não são gerados

**Causa**: Dependências de geração faltando
**Solução**: Usa fallback PDF simplificado automaticamente

### Atualização não funciona

**Causa**: Release no GitHub sem instalador anexado
**Solução**: Criar release e anexar Busca_XML_Setup.exe

---

## 📄 Licença e Créditos

Sistema desenvolvido para automação de processos fiscais brasileiros.

**Desenvolvedor**: W4lterBr
**Última atualização**: Janeiro 2026
**Versão atual**: 1.0.36
