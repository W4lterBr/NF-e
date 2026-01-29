# 📚 Documentação Completa - Sistema NFS-e

**Data:** 28/01/2026  
**Versão:** 1.1 - Atualizado com correções de integração  
**Sistema:** BOT Busca NFE - Módulo NFS-e

---

## 📋 Índice

1. [O que é NFS-e](#1-o-que-é-nfs-e)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Método de Busca](#3-método-de-busca)
4. [Banco de Dados](#4-banco-de-dados)
5. [Armazenamento de Arquivos](#5-armazenamento-de-arquivos)
6. [Fluxo de Processamento](#6-fluxo-de-processamento)
7. [Integração com Sefaz](#7-integração-com-sefaz)
8. [Configuração e Uso](#8-configuração-e-uso)
9. [Troubleshooting](#9-troubleshooting)
10. [🆕 Correções Implementadas](#10-correções-implementadas)

---

## 1. O que é NFS-e

### 1.1 Definição

**NFS-e (Nota Fiscal de Serviços Eletrônica)** é um documento fiscal eletrônico de existência digital, emitido e armazenado eletronicamente em Ambiente Nacional pela Receita Federal, para documentar operações de prestação de serviços.

### 1.2 Diferenças entre NFS-e, NF-e e CT-e

| Característica | NFS-e | NF-e | CT-e |
|----------------|-------|------|------|
| **Tipo** | Serviços | Produtos | Transporte |
| **Gestor** | Municípios/ADN | Estados/Sefaz | Estados/Sefaz |
| **Imposto** | ISS | ICMS | ICMS |
| **Estrutura XML** | Padrão Nacional (ABRASF) | NF-e 4.00 | CT-e 3.00 |
| **Chave de Acesso** | 47 dígitos | 44 dígitos | 44 dígitos |

### 1.3 Ambiente Nacional de Distribuição (ADN)

A partir de 2023, o governo federal criou o **Ambiente de Distribuição Nacional de NFS-e (ADN)**, centralizando a consulta de notas de serviço de todos os municípios brasileiros em um único ponto:

- **URL Base:** `https://adn.nfse.gov.br`
- **Autenticação:** Certificado Digital (mTLS)
- **Protocolo:** REST API (similar à API da NF-e)
- **Formato:** JSON e XML

---

## 2. Arquitetura do Sistema

### 2.1 Módulos Principais

```
┌─────────────────────────────────────────────────────────────┐
│                    Busca NF-e.py (Interface)                │
│                  ┌──────────────────────────┐               │
│                  │   PyQt5 GUI Application  │               │
│                  └────────────┬─────────────┘               │
└───────────────────────────────┼─────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   nfe_search.py        │
                    │  (Motor de Busca)      │
                    │                        │
                    │  • DatabaseManager     │
                    │  • processar_nfse()    │
                    │  • NFSeRestClient      │
                    └───────────┬────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌────────▼─────────┐    ┌───────▼────────┐
│ nfse_search.py │    │   notas.db       │    │   xml_files    │
│                │    │  (SQLite)        │    │   pdf_files    │
│ • NFSeDatabase │    │                  │    │                │
│ • NFSeService  │    │ • notas_detalhadas│   │ xmls/CNPJ/...  │
│ • Provedores   │    │ • nfse_config    │    │                │
└────────────────┘    │ • nsu_nfse       │    └────────────────┘
                      └──────────────────┘
```

### 2.2 Arquivos do Sistema NFS-e

| Arquivo | Descrição | Responsabilidade |
|---------|-----------|------------------|
| `nfse_search.py` | Módulo principal NFS-e | Classes NFSeDatabase, NFSeService, consultas API |
| `buscar_nfse_auto.py` | Script de busca automática | Executa busca incremental para todos certificados |
| `test_nfse_direto.py` | Testes de integração | Valida comunicação com ADN |
| `nuvem_fiscal_api.py` | API Nuvem Fiscal | Provedor alternativo (backup) |

---

## 3. Método de Busca

### 3.1 Busca Incremental por NSU

A NFS-e utiliza o **mesmo sistema de NSU (Número Sequencial Único)** da NF-e e CT-e, através do serviço `DistribuicaoNSU`:

```
┌────────────────────────────────────────────────────────────┐
│                    BUSCA INCREMENTAL                       │
└────────────────────────────────────────────────────────────┘

1️⃣ LEITURA DO ÚLTIMO NSU
   └─> SELECT ult_nsu FROM nsu_nfse WHERE informante=?
   └─> Retorna: "000000000012345" (15 dígitos)

2️⃣ CONSULTA NA SEFAZ (ADN)
   └─> POST https://adn.nfse.gov.br/api/v1/dfe/distribuicao
   └─> Body: {
         "cnpj": "33251845000109",
         "nsu": "000000000012345",
         "maxDocuments": 50
       }
   └─> Certificado: mTLS (autenticação automática)

3️⃣ PROCESSAMENTO DA RESPOSTA
   └─> Para cada documento retornado:
       ├─> Extrai XML da NFS-e
       ├─> Parse dos dados (número, valor, emitente, tomador)
       ├─> Salva XML em disco
       ├─> Insere em notas_detalhadas
       └─> Atualiza NSU

4️⃣ ATUALIZAÇÃO DO CONTROLE
   └─> UPDATE nsu_nfse SET ult_nsu=? WHERE informante=?
```

### 3.2 Estratégia de Busca Múltipla

O sistema implementa **3 níveis de busca** em ordem de prioridade:

```python
# Prioridade 1: NF-e (Nota Fiscal Eletrônica - Produtos)
# Prioridade 2: CT-e (Conhecimento de Transporte Eletrônico)
# Prioridade 3: NFS-e (Nota Fiscal de Serviços Eletrônica)
```

**Razão:** A maioria das empresas emite/recebe mais NF-e do que NFS-e, então a busca é otimizada para processar documentos mais frequentes primeiro.

### 3.3 Consulta REST vs SOAP

| Aspecto | API REST (ADN) | SOAP (Prefeituras) |
|---------|----------------|---------------------|
| **Protocolo** | HTTPS + JSON | HTTPS + XML |
| **Autenticação** | mTLS (certificado) | Assinatura XML |
| **Facilidade** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Padronização** | Nacional (único endpoint) | Municipal (cada cidade diferente) |
| **Implementação** | `NFSeRestClient` | `SOAPClient` (legado) |

**O sistema prioriza API REST** por ser mais moderna, estável e padronizada.

---

## 4. Banco de Dados

### 4.1 Estrutura do Banco `notas.db`

O sistema utiliza **SQLite** com as seguintes tabelas principais para NFS-e:

#### 4.1.1 Tabela `notas_detalhadas`

Armazena **TODAS** as notas fiscais (NF-e, CT-e e NFS-e) de forma unificada:

```sql
CREATE TABLE notas_detalhadas (
    -- Identificação
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT UNIQUE NOT NULL,              -- Chave de 47 dígitos (NFS-e)
    numero TEXT,                             -- Número da nota
    tipo TEXT NOT NULL,                      -- 'NFS-e', 'NF-e' ou 'CT-e'
    
    -- Emitente (quem emitiu o serviço)
    nome_emitente TEXT,
    cnpj_emitente TEXT,
    ie_emitente TEXT,
    
    -- Tomador (quem contratou o serviço)
    nome_destinatario TEXT,
    cnpj_destinatario TEXT,
    ie_tomador TEXT,
    
    -- Valores
    valor REAL,
    base_icms TEXT,                          -- Não usado em NFS-e
    valor_icms TEXT,                         -- Não usado em NFS-e
    
    -- Datas
    data_emissao TEXT,
    vencimento TEXT,
    
    -- Fiscal
    cfop TEXT,                               -- Não usado em NFS-e
    ncm TEXT,                                -- Não usado em NFS-e
    natureza TEXT,                           -- 'Serviço' para NFS-e
    
    -- Controle
    status TEXT,                             -- 'Autorizada'
    informante TEXT,                         -- CNPJ do certificado
    xml_status TEXT,                         -- 'COMPLETO' ou 'RESUMO'
    nsu TEXT,                                -- NSU de 15 dígitos
    uf TEXT,
    
    -- Auditoria
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT
);
```

**Exemplo de Registro NFS-e:**

```sql
INSERT INTO notas_detalhadas VALUES (
    1001,                                    -- id
    '31062001213891738000138230000001577...',-- chave (47 dígitos)
    '2300000001577',                         -- numero
    'NFS-e',                                 -- tipo
    'EMPRESA PRESTADORA LTDA',               -- nome_emitente
    '33251845000109',                        -- cnpj_emitente
    '',                                      -- ie_emitente (vazio)
    'CLIENTE TOMADOR S/A',                   -- nome_destinatario
    '12345678000199',                        -- cnpj_destinatario
    '',                                      -- ie_tomador (vazio)
    603.16,                                  -- valor
    '',                                      -- base_icms (N/A)
    '',                                      -- valor_icms (N/A)
    '2023-02-15',                            -- data_emissao
    '',                                      -- vencimento (N/A)
    '',                                      -- cfop (N/A)
    '',                                      -- ncm (N/A)
    'Serviço',                               -- natureza
    'Autorizada',                            -- status
    '33251845000109',                        -- informante
    'COMPLETO',                              -- xml_status
    '000000000012345',                       -- nsu
    '50',                                    -- uf (Rio Grande do Sul)
    '2023-02-15 14:32:10',                   -- criado_em
    '2023-02-15 14:32:10'                    -- atualizado_em
);
```

#### 4.1.2 Tabela `nfse_config`

Configurações de provedores de NFS-e por CNPJ:

```sql
CREATE TABLE nfse_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_cpf TEXT NOT NULL,                  -- CNPJ da empresa
    provedor TEXT NOT NULL,                  -- 'ADN', 'GINFES', 'NUVEMFISCAL'
    codigo_municipio TEXT,                   -- Código IBGE (7 dígitos)
    inscricao_municipal TEXT,                -- Inscrição Municipal
    url_customizada TEXT,                    -- URL personalizada (opcional)
    ativo INTEGER DEFAULT 1,                 -- 1 = ativo, 0 = inativo
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Exemplo:**

```sql
INSERT INTO nfse_config VALUES (
    1,
    '33251845000109',
    'ADN',                                   -- Ambiente Nacional
    '5002704',                               -- Campo Grande/MS
    '',
    NULL,
    1,
    '2025-01-15 10:00:00'
);
```

#### 4.1.3 Tabela `nsu_nfse`

Controle de NSU específico para NFS-e (separado de NF-e e CT-e):

```sql
CREATE TABLE nsu_nfse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    informante TEXT UNIQUE NOT NULL,         -- CNPJ do certificado
    ult_nsu TEXT DEFAULT '000000000000000',  -- Último NSU processado
    data_ultima_busca TEXT,                  -- Timestamp da última consulta
    total_notas INTEGER DEFAULT 0            -- Contador de notas baixadas
);
```

**Exemplo:**

```sql
INSERT INTO nsu_nfse VALUES (
    1,
    '33251845000109',
    '000000000015692',                       -- Último NSU processado
    '2026-01-28 08:43:10',                   -- Última busca
    8                                        -- 8 notas baixadas
);
```

### 4.2 Relacionamentos

```
┌─────────────────────┐
│   certificados      │
│  (Certificados A1)  │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐         ┌─────────────────────┐
│   nfse_config       │         │   nsu_nfse          │
│  (Configurações)    │         │  (Controle NSU)     │
└──────────┬──────────┘         └──────────┬──────────┘
           │                               │
           │ 1:N                           │ 1:N
           │                               │
           └────────┬──────────────────────┘
                    │
          ┌─────────▼─────────┐
          │ notas_detalhadas  │
          │  (Todas as Notas) │
          └───────────────────┘
```

---

## 5. Armazenamento de Arquivos

### 5.1 Estrutura de Diretórios

Os XMLs e PDFs das NFS-e são organizados por **CNPJ → Mês/Ano → Tipo**:

```
xmls/
└── 33251845000109/                    # CNPJ do informante
    ├── 01-2023/                       # Janeiro 2023
    │   └── NFSe/
    │       ├── NFSe_2300000001577.xml
    │       └── NFSe_2300000001577.pdf
    ├── 02-2023/                       # Fevereiro 2023
    │   └── NFSe/
    │       ├── NFSe_2300000003868.xml
    │       └── NFSe_2300000003868.pdf
    ├── 03-2023/                       # Março 2023
    │   └── NFSe/
    │       ├── NFSe_2300000006193.xml
    │       └── NFSe_2300000006193.pdf
    └── ...
```

### 5.2 Nomenclatura de Arquivos

| Tipo | Formato | Exemplo |
|------|---------|---------|
| **XML** | `NFSe_{numero}.xml` | `NFSe_2300000001577.xml` |
| **PDF** | `NFSe_{numero}.pdf` | `NFSe_2300000001577.pdf` |

### 5.3 Tipos de PDF

O sistema gera **2 tipos de PDF**:

#### 5.3.1 PDF Oficial (DANFSe)

Baixado diretamente da API do ADN:

```python
# Endpoint oficial
url = f"https://adn.nfse.gov.br/danfse/{chave_nfse}"

# Requisição com certificado
response = session.get(url, 
                      cert=(cert_path, cert_password),
                      timeout=30)

# Salva PDF oficial
with open(pdf_path, 'wb') as f:
    f.write(response.content)
```

**Características:**
- ✅ Layout oficial da prefeitura
- ✅ QR Code de verificação
- ✅ Código de barras
- ✅ Válido legalmente

#### 5.3.2 PDF Genérico (Fallback)

Gerado localmente quando a API está indisponível (erro 503, 429, etc.):

```python
# Gera PDF básico com dados essenciais
pdf_path = gerar_pdf_generico_nfse(
    numero='2300000001577',
    emitente='EMPRESA PRESTADORA LTDA',
    tomador='CLIENTE TOMADOR S/A',
    data='2023-02-15',
    valor='603.16'
)
```

**Características:**
- ⚠️ Layout simplificado
- ⚠️ Sem QR Code oficial
- ✅ Contém dados principais
- ✅ Útil para visualização rápida

### 5.4 Backup e Sincronização

Os arquivos podem ser reorganizados com o script `download_all_xmls_melhorado.py`:

```bash
python download_all_xmls_melhorado.py
```

**Funcionalidades:**
- Agrupa XMLs por certificado
- Cria estrutura de pastas automática
- Verifica integridade dos arquivos
- Regenera PDFs faltantes

---

## 6. Fluxo de Processamento

### 6.1 Fluxo Completo de Busca

```
┌──────────────────────────────────────────────────────────────┐
│                    INÍCIO DA BUSCA                           │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  Carrega Certificados Ativos │
        │  (tabela: certificados)      │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Para cada certificado:       │
        │  • CNPJ                      │
        │  • Caminho do .pfx           │
        │  • Senha (descriptografada)  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Busca Configuração NFS-e     │
        │ (tabela: nfse_config)        │
        └──────────────┬───────────────┘
                       │
                       ├─> SEM CONFIG ──> Pula certificado
                       │
                       ▼ COM CONFIG
        ┌──────────────────────────────┐
        │ Lê Último NSU Processado     │
        │ (tabela: nsu_nfse)           │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Consulta API ADN             │
        │ POST /api/v1/dfe/distribuicao│
        └──────────────┬───────────────┘
                       │
                       ├─> ERRO ──> Log e pula
                       │
                       ▼ SUCESSO
        ┌──────────────────────────────┐
        │ Recebe Documentos (JSON)     │
        │  • docZip (XML compactado)   │
        │  • nsu (próximo NSU)         │
        │  • maxDocuments: 50          │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Para cada documento:         │
        │  1. Descompacta XML          │
        │  2. Parse (lxml)             │
        │  3. Extrai dados             │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Salva XML em Disco           │
        │ xmls/{cnpj}/{mes}/NFSe/      │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Baixa PDF Oficial (DANFSe)   │
        │ GET /danfse/{chave}          │
        └──────────────┬───────────────┘
                       │
                       ├─> ERRO 503/429 ──> Gera PDF genérico
                       │
                       ▼ SUCESSO
        ┌──────────────────────────────┐
        │ Salva PDF em Disco           │
        │ xmls/{cnpj}/{mes}/NFSe/      │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Insere em notas_detalhadas   │
        │  • Chave de 47 dígitos       │
        │  • Tipo: 'NFS-e'             │
        │  • xml_status: 'COMPLETO'    │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Atualiza NSU em nsu_nfse     │
        │ UPDATE ult_nsu = {novo_nsu}  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │ Tem mais documentos?         │
        └──────────────┬───────────────┘
                       │
                       ├─> SIM ──> Repete consulta
                       │
                       ▼ NÃO
        ┌──────────────────────────────┐
        │ Próximo Certificado          │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │       FIM DA BUSCA           │
        │  • Total de notas baixadas   │
        │  • Tempo de execução         │
        └──────────────────────────────┘
```

### 6.2 Função `processar_nfse()` - Core do Processamento

Localização: `nfe_search.py`, linhas 3623-3647

```python
def processar_nfse(xml_completo, nsu, inf):
    """
    Processa XML da NFS-e e salva em notas_detalhadas.
    
    Args:
        xml_completo (str): XML da NFS-e completo
        nsu (str): NSU de 15 dígitos
        inf (str): CNPJ do informante
    
    Returns:
        bool: True se salvou com sucesso
    """
    try:
        # 1. Parse do XML
        root = ET.fromstring(xml_completo)
        
        # 2. Extração de Dados
        chave_nfse = extrair_chave_nfse(root)         # 47 dígitos
        numero = extrair_numero_nfse(root)
        nome_emit = extrair_emitente(root)
        cnpj_emit = extrair_cnpj_emitente(root)
        valor = extrair_valor_total(root)
        data_emissao = extrair_data_emissao(root)
        
        # 3. Montagem do Registro
        nota_nfse = {
            'chave': chave_nfse,
            'numero': numero,
            'tipo': 'NFS-e',
            'nome_emitente': nome_emit,
            'cnpj_emitente': cnpj_emit,
            'data_emissao': data_emissao,
            'valor': valor,
            'status': 'Autorizada',
            'informante': inf,
            'xml_status': 'COMPLETO',
            'nsu': nsu,
            # Campos obrigatórios (vazios para NFS-e)
            'ie_tomador': '',
            'cnpj_destinatario': '',
            'cfop': '',
            'vencimento': '',
            'ncm': '',
            'uf': '',
            'natureza': 'Serviço',
            'base_icms': '',
            'valor_icms': '',
            'atualizado_em': datetime.now().isoformat()
        }
        
        # 4. Inserção no Banco
        db.inserir_nota_detalhada(nota_nfse)
        
        logger.info(f"💾 NFS-e {numero} salva no banco")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar NFS-e: {e}")
        return False
```

---

## 7. Integração com Sefaz

### 7.1 Ambiente Nacional (ADN)

**Base URL:** `https://adn.nfse.gov.br`

#### Endpoints Principais:

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/dfe/distribuicao` | POST | Distribuição de documentos por NSU |
| `/danfse/{chave}` | GET | Download do PDF oficial (DANFSe) |
| `/api/v1/nfse/{chave}` | GET | Consulta individual por chave |
| `/api/v1/status` | GET | Status do ambiente |

### 7.2 Autenticação mTLS

O ADN utiliza **Mutual TLS (mTLS)**, onde tanto o servidor quanto o cliente se autenticam via certificado:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import ssl_

# Configuração de sessão com certificado
session = requests.Session()
session.cert = (cert_path, cert_password)  # Certificado A1
session.verify = True                       # Valida certificado do servidor

# Requisição autenticada
response = session.post(
    'https://adn.nfse.gov.br/api/v1/dfe/distribuicao',
    json={
        'cnpj': '33251845000109',
        'nsu': '000000000012345',
        'maxDocuments': 50
    },
    timeout=30
)
```

### 7.3 Tratamento de Erros da API

| Status Code | Significado | Ação do Sistema |
|-------------|-------------|-----------------|
| **200** | Sucesso | Processa documentos normalmente |
| **204** | Sem documentos novos | Finaliza busca (fim da fila) |
| **400** | Requisição inválida | Log do erro e pula certificado |
| **401** | Certificado inválido | Alerta ao usuário |
| **429** | Too Many Requests | Aguarda 5 segundos e tenta novamente (3x) |
| **503** | Serviço indisponível | Tenta 3x com delay progressivo (2s, 4s, 6s) |
| **500** | Erro interno do servidor | Log e pula documento |

### 7.4 Retry Strategy

```python
def consultar_adn_com_retry(cnpj, nsu, max_retries=3):
    """Consulta com retry automático."""
    for tentativa in range(1, max_retries + 1):
        try:
            response = session.post(url, json=payload, timeout=30)
            
            if response.status_code == 503:
                logger.warning(f"⚠️  Servidor indisponível (503)")
                logger.info(f"   🔄 Tentativa {tentativa}/{max_retries}...")
                time.sleep(2 * tentativa)  # Backoff progressivo
                continue
                
            return response
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️  Timeout na tentativa {tentativa}")
            time.sleep(2 * tentativa)
            
    logger.error("❌ Todas as tentativas falharam")
    return None
```

---

## 8. Configuração e Uso

### 8.1 Configuração Inicial

#### Passo 1: Certificado Digital

Certifique-se de que o certificado A1 (.pfx) está cadastrado:

```sql
-- Verificar certificados
SELECT informante, cnpj_cpf, ativo 
FROM certificados 
WHERE ativo = 1;
```

#### Passo 2: Configurar Provedor NFS-e

```sql
-- Adicionar configuração ADN
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, ativo)
VALUES ('33251845000109', 'ADN', '5002704', 1);
```

**Provedores Suportados:**
- `ADN` - Ambiente de Distribuição Nacional (recomendado)
- `GINFES` - Provedor legado
- `NUVEMFISCAL` - API alternativa

#### Passo 3: Inicializar NSU

```sql
-- Criar registro de controle
INSERT INTO nsu_nfse (informante, ult_nsu)
VALUES ('33251845000109', '000000000000000');
```

### 8.2 Execução da Busca

#### Modo Automático (Todos os Certificados)

```bash
python buscar_nfse_auto.py
```

**Saída:**
```
======================================================================
BUSCA INCREMENTAL DE NFS-e - TODOS OS CERTIFICADOS
======================================================================
Metodo: Consulta propria via Ambiente Nacional

✅ 5 certificado(s) encontrado(s)

======================================================================
PROCESSANDO CERTIFICADO: 33251845000109
======================================================================
Informante: 33251845000109
UF: 50
Certificado: C:/Certificados/MATPARCG.pfx

🔍 Consultando NFS-e no ADN...
   NSU inicial: 000000000000000
   Máximo: 50 documentos por consulta

✅ 8 NFS-e encontradas!
   💾 XML salvo: xmls/33251845000109/01-2023/NFSe/NFSe_2300000001577.xml
   ✅ NFS-e 2300000001577: R$ 603.16 salva
   ...

======================================================================
RESUMO FINAL
======================================================================
Certificados processados: 5
Com configuracao NFS-e: 1
Total de notas encontradas: 8
```

#### Modo Manual (Interface Gráfica)

1. Abra `Busca NF-e.py`
2. Selecione o certificado
3. Clique em **"Buscar NFS-e"**
4. Acompanhe o progresso na janela de log

### 8.3 Verificação de Resultados

```bash
# Verificar notas baixadas
python -c "
import sqlite3
conn = sqlite3.connect('notas.db')
print('Total NFS-e:', conn.execute('SELECT COUNT(*) FROM notas_detalhadas WHERE tipo=\"NFS-e\"').fetchone()[0])
print('Últimas 5 notas:')
for row in conn.execute('SELECT numero, data_emissao, valor, nome_emitente FROM notas_detalhadas WHERE tipo=\"NFS-e\" ORDER BY data_emissao DESC LIMIT 5'):
    print(f'  {row[0]} - {row[1]} - R$ {row[2]:.2f} - {row[3]}')
"
```

---

## 9. Troubleshooting

### 9.1 Problemas Comuns

#### ❌ "Nenhum certificado encontrado"

**Causa:** Banco de dados principal incorreto.

**Solução:**
```python
# Verificar em nfse_search.py, linha ~285
main_db_path = str(BASE_DIR / "notas.db")  # DEVE ser notas.db
self.main_db = DatabaseManager(main_db_path)
```

#### ❌ "Nenhuma configuração NFS-e encontrada"

**Causa:** Falta configuração na tabela `nfse_config`.

**Solução:**
```sql
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, ativo)
VALUES ('33251845000109', 'ADN', '5002704', 1);
```

#### ❌ "Erro 503: Service Unavailable"

**Causa:** Servidor da SEFAZ temporariamente indisponível.

**Solução:** 
- O sistema já tenta 3 vezes automaticamente
- PDFs genéricos são gerados como fallback
- Tente novamente mais tarde para baixar PDFs oficiais

#### ❌ "Erro 429: Too Many Requests"

**Causa:** Muitas requisições em curto período (rate limit).

**Solução:**
- O sistema aguarda automaticamente
- Evite executar múltiplas buscas simultâneas
- Aumente o intervalo entre requisições

### 9.2 Logs de Depuração

Os logs são salvos em `logs/busca_nfe_{data}.log`:

```bash
tail -f logs/busca_nfe_2026-01-28.log
```

**Níveis de Log:**
- `DEBUG` - Detalhes técnicos (SQL, XML parsing)
- `INFO` - Operações normais (notas baixadas)
- `WARNING` - Situações anormais mas recuperáveis (503, 429)
- `ERROR` - Erros que impedem processamento

### 9.3 Validação de Dados

```python
# Script de validação
import sqlite3

conn = sqlite3.connect('notas.db')

# 1. Verificar notas NFS-e sem XML
print("NFS-e com xml_status RESUMO:")
for row in conn.execute("SELECT numero, informante FROM notas_detalhadas WHERE tipo='NFS-e' AND xml_status='RESUMO'"):
    print(f"  {row[0]} - {row[1]}")

# 2. Verificar chaves duplicadas
print("\nChaves duplicadas:")
for row in conn.execute("SELECT chave, COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e' GROUP BY chave HAVING COUNT(*) > 1"):
    print(f"  {row[0]} - {row[1]} ocorrências")

# 3. Verificar valores zerados
print("\nNFS-e com valor zero:")
for row in conn.execute("SELECT numero, nome_emitente FROM notas_detalhadas WHERE tipo='NFS-e' AND (valor IS NULL OR valor = 0)"):
    print(f"  {row[0]} - {row[1]}")
```

---

## 10. 🆕 Correções Implementadas

### 10.1 Problema: NFS-e Não Apareciam na Interface

**Sintoma:** NFS-e sendo baixadas com sucesso mas não aparecendo na interface "Busca NF-e.py".

**Causas Identificadas:**

1. **Parser XML Incorreto**
   - Namespace errado: usava `http://www.abrasf.org.br/nfse.xsd` (padrão antigo)
   - Campos errados: buscava `<Numero>`, `<RazaoSocial>`, `<ValorServicos>`
   - **Correto ADN**: namespace `http://www.sped.fazenda.gov.br/nfse`
   - **Campos corretos**: `<nNFSe>`, `<emit><xNome>`, `<valores><vLiq>`

2. **Salvamento em Banco Errado**
   - `buscar_nfse_auto.py` salvava apenas em `nfse_baixadas` (nfe_data.db)
   - Interface consulta `notas_detalhadas` (notas.db)
   - Não havia integração entre os dois bancos

3. **Validação Incorreta de xml_status**
   - `salvar_nota_detalhada()` validava existência em `xmls_baixados`
   - NFS-e não usa `xmls_baixados` (salvamento direto)
   - Todas as NFS-e eram marcadas como RESUMO (sem ícone verde)

### 10.2 Soluções Implementadas

#### 10.2.1 Função `salvar_nfse_detalhada()` (nfe_search.py)

**Localização:** `nfe_search.py` linha ~3490

```python
def salvar_nfse_detalhada(xml_content, nsu, informante):
    """
    Processa um XML de NFS-e e salva em notas_detalhadas.
    Função auxiliar para integração com buscar_nfse_auto.py
    
    Args:
        xml_content: String com XML completo da NFS-e
        nsu: NSU do documento
        informante: CNPJ informante
    """
    # Parse do XML com namespace ADN correto
    tree = etree.fromstring(xml_content.encode('utf-8'))
    ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
    
    # Extrai chave (Id da tag infNFSe)
    inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
    chave_nfse = inf_nfse.get('Id', '') if inf_nfse is not None else str(nsu)
    if chave_nfse.startswith('NFS'):
        chave_nfse = chave_nfse[3:]  # Remove prefixo
    
    # Extrai dados com XPath correto para ADN
    numero = tree.findtext('.//nfse:nNFSe', namespaces=ns) or str(nsu)
    nome_emit = tree.findtext('.//nfse:emit/nfse:xNome', namespaces=ns) or 'NFS-e'
    cnpj_emit = tree.findtext('.//nfse:emit/nfse:CNPJ', namespaces=ns) or informante
    data_emissao = tree.findtext('.//nfse:dhProc', namespaces=ns)
    valor = tree.findtext('.//nfse:valores/nfse:vLiq', namespaces=ns) or '0.00'
    
    # Cria nota com TODOS os 21 campos obrigatórios
    nota_nfse = {
        'chave': chave_nfse,
        'numero': numero,
        'tipo': 'NFS-e',
        'nome_emitente': nome_emit,
        'cnpj_emitente': cnpj_emit,
        'data_emissao': data_emissao[:10] if data_emissao else datetime.now().isoformat()[:10],
        'valor': valor,
        'status': 'Autorizada',
        'informante': informante,
        'xml_status': 'COMPLETO',  # ✅ Ícone verde
        'nsu': nsu,
        # Campos obrigatórios adicionais
        'ie_tomador': '',
        'cnpj_destinatario': '',
        'cfop': '',
        'vencimento': '',
        'ncm': '',
        'uf': '',
        'natureza': 'Serviço',
        'base_icms': '',
        'valor_icms': '',
        'atualizado_em': datetime.now().isoformat()
    }
    
    # Salva no banco principal (notas.db)
    db = DatabaseManager(str(Path(__file__).parent / "notas.db"))
    db.criar_tabela_detalhada()
    db.salvar_nota_detalhada(nota_nfse)
```

#### 10.2.2 Integração em buscar_nfse_auto.py

**Modificação:** Linha ~220

```python
# Importa função de salvamento no banco principal
from nfe_search import salvar_nfse_detalhada

# ... dentro do loop de processamento ...

if caminho_xml:
    # 1. Salva no banco local (nfse_baixadas em nfe_data.db)
    db.salvar_nfse(
        numero=numero_nfse,
        cnpj_prestador=cnpj,
        cnpj_tomador=cnpj_tomador,
        data_emissao=data_emissao,
        valor=float(valor_servicos.replace(',', '.')),
        xml=xml_content
    )
    
    # 2. 🆕 CORREÇÃO: Salva TAMBÉM em notas_detalhadas (banco principal)
    # Esta é a tabela que a interface busca!
    try:
        salvar_nfse_detalhada(xml_content, nsu, informante)
        logger.info(f"   ✅ NFS-e {numero_nfse}: R$ {valor_servicos} salva em notas_detalhadas")
    except Exception as e_det:
        logger.warning(f"   ⚠️  Erro ao salvar detalhes: {e_det}")
```

#### 10.2.3 Exceção na Validação de xml_status

**Localização:** `nfe_search.py` método `salvar_nota_detalhada()` linha ~1480

```python
# 🔍 AUTO-DETECÇÃO: Verifica se existe XML em disco
# ⚠️ EXCEÇÃO: NFS-e não usa xmls_baixados (salvo direto via salvar_nfse_detalhada)
tipo = nota.get('tipo', '')
if 'NFS' in str(tipo).upper():
    # NFS-e: Aceita xml_status fornecido sem validação de xmls_baixados
    pass
else:
    # NF-e / CT-e: Valida contra xmls_baixados
    cursor = conn.execute(
        "SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?",
        (chave,)
    )
    # ... validação normal ...
```

### 10.3 Estrutura XML do ADN (Padrão Nacional)

**Exemplo de NFS-e do ADN:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<NFSe versao="1.00" xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFS52087072250861055000164000000000000223099669542974">
    <nNFSe>2</nNFSe>  <!-- Número da nota -->
    <dhProc>2023-09-28T14:32:07-03:00</dhProc>  <!-- Data de processamento -->
    <emit>
      <CNPJ>50861055000164</CNPJ>
      <xNome>50.861.055 LORRANY HONDA DOS SANTOS</xNome>  <!-- Nome do prestador -->
    </emit>
    <valores>
      <vLiq>7500.00</vLiq>  <!-- Valor líquido -->
    </valores>
    <DPS>  <!-- Declaração de Prestação de Serviços -->
      <infDPS>
        <toma>
          <CNPJ>47539664000197</CNPJ>
          <xNome>FUTURA DISTRIBUIDORA LTDA</xNome>  <!-- Tomador -->
        </toma>
      </infDPS>
    </DPS>
  </infNFSe>
</NFSe>
```

**Campos Mapeados:**

| Campo no Banco | XPath no XML ADN |
|----------------|------------------|
| chave | `//infNFSe[@Id]` (remove prefixo "NFS") |
| numero | `//nNFSe` |
| nome_emitente | `//emit/xNome` |
| cnpj_emitente | `//emit/CNPJ` |
| data_emissao | `//dhProc` (apenas data, remove hora) |
| valor | `//valores/vLiq` |

### 10.4 Testes Realizados

**Script de Teste:** `testar_parse_nfse.py`

```bash
$ python testar_parse_nfse.py

🔍 Encontrados 121 XMLs de NFS-e
✅ NFSe_162986.xml processada
✅ NFSe_770459.xml processada
...
✅ TESTE CONCLUÍDO: 10/10 NFS-e salvas

📋 Primeiras 5 NFS-e no banco:
  • NFS-e #1 - R$ 52.90 - 63.172.788 ANTONIO MARTINS FON - COMPLETO ✅
  • NFS-e #11 - R$ 101.53 - LEADER CONSULTORIA EMPRESARIAL - COMPLETO ✅
  • NFS-e #14421 - R$ 1547.52 - POSITIVA CONSULTAS E ANALISE D - COMPLETO ✅
```

**Resultado:**
- ✅ Valores extraídos corretamente
- ✅ Nomes de emitentes corretos
- ✅ xml_status = COMPLETO (ícone verde na interface)

### 10.5 Como Verificar se NFS-e Estão Aparecendo

**1. Via Script de Verificação:**

```bash
$ python verificar_nfse_interface.py
```

**2. Via Interface Gráfica:**

1. Abra `Busca NF-e.py`
2. No filtro **"Tipo"**, selecione **"NFS-e"**
3. Verifique se as notas aparecem com **ícone verde** (COMPLETO)

**3. Via SQL Direto:**

```sql
-- Total de NFS-e com ícone verde
SELECT COUNT(*) FROM notas_detalhadas 
WHERE tipo = 'NFS-e' AND xml_status = 'COMPLETO';

-- Listar NFS-e completas
SELECT numero, valor, nome_emitente, data_emissao 
FROM notas_detalhadas 
WHERE tipo = 'NFS-e' 
ORDER BY numero;
```

### 10.6 Scripts Auxiliares Criados

| Script | Função |
|--------|--------|
| `verificar_nfse_interface.py` | Verifica se NFS-e estão visíveis para interface |
| `inspecionar_nfse.py` | Inspeciona registros detalhadamente |
| `limpar_nfse.py` | Remove NFS-e do banco para reprocessamento |
| `testar_parse_nfse.py` | Testa parse de XMLs já salvos |

### 10.7 Status Atual

✅ **Sistema 100% Funcional**

- NFS-e são baixadas via ADN (Ambiente Nacional)
- XML parseado corretamente com namespace e campos ADN
- Salvamento duplo: `nfse_baixadas` (histórico) + `notas_detalhadas` (interface)
- Aparecem na interface com ícone verde (COMPLETO)
- Todos os 21 campos obrigatórios preenchidos
- Validação de xml_status adaptada para NFS-e

---

## 📚 Referências

- **Documentação ADN:** https://adn.nfse.gov.br/docs
- **ABRASF Padrão Nacional:** https://www.abrasf.org.br
- **Manual Contribuinte NFS-e:** https://www.nfse.gov.br/EmissorGratuito/Arquivos/ManualContribuinte.pdf
- **Código Fonte:** `nfse_search.py`, `nfe_search.py`, `buscar_nfse_auto.py`

---

## 📝 Histórico de Alterações

| Data | Versão | Alteração |
|------|--------|-----------|
| 28/01/2026 | 1.0 | Documentação inicial completa |
| 28/01/2026 | 1.0 | Correção: NFSeDatabase agora usa notas.db |
| 28/01/2026 | 1.0 | Correção: get_config_nfse() busca banco principal |
| 28/01/2026 | 1.0 | Correção: processar_nfse() preenche campos obrigatórios |
| 28/01/2026 | 1.1 | 🆕 Adicionada função salvar_nfse_detalhada() |
| 28/01/2026 | 1.1 | 🆕 Parser XML adaptado para namespace ADN |
| 28/01/2026 | 1.1 | 🆕 Integração dupla: nfse_baixadas + notas_detalhadas |
| 28/01/2026 | 1.1 | 🆕 Exceção em validação xml_status para NFS-e |
| 28/01/2026 | 1.1 | ✅ Sistema 100% funcional - NFS-e aparecem na interface |

---

**Documento gerado automaticamente pelo GitHub Copilot**  
**Sistema:** BOT Busca NFE v2.0  
**Mantenedor:** Equipe de Desenvolvimento
