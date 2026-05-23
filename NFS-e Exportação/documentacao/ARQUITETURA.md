# 🏗️ Arquitetura do Sistema NFS-e

## Visão Geral

O sistema de busca de NFS-e é composto por **2 classes principais** e **diversas funções auxiliares** que trabalham em conjunto para consultar, processar e armazenar Notas Fiscais de Serviço Eletrônica de múltiplos municípios brasileiros.

---

## 📊 Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE DO USUÁRIO                      │
│  (CLI ou integração com aplicação principal PyQt5)          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE SERVIÇO                         │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  NFSeService     │◄────────┤  NFSeDatabase    │         │
│  │  (API Calls)     │         │  (Persistence)   │         │
│  └────────┬─────────┘         └──────────────────┘         │
│           │                                                  │
│           ├─► buscar_ginfes()      ─► SOAP Municipal        │
│           ├─► buscar_nuvemfiscal() ─► REST Nuvem Fiscal     │
│           └─► buscar_adn_rest()    ─► REST ADN Nacional     │
│                                                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                  CAMADA DE INTEGRAÇÃO                        │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  SOAP APIs     │  │  REST APIs     │  │  HTTP Clients│  │
│  │  (Municípios)  │  │  (ADN/Nuvem)   │  │  (requests)  │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│               PROVEDORES EXTERNOS (APIs)                     │
│                                                              │
│  • Ginfes (SOAP)                                            │
│  • ISS.NET (SOAP/REST)                                      │
│  • eISS (SOAP)                                              │
│  • Betha (SOAP)                                             │
│  • ADN Nacional (REST - apenas emissão)                     │
│  • Nuvem Fiscal (REST - agregador terceirizado)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  CAMADA DE PERSISTÊNCIA                      │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │         SQLite Database (notas.db)        │              │
│  │                                            │              │
│  │  • nfse_config (configurações)            │              │
│  │  • nfse_baixadas (NFS-e salvas)           │              │
│  │  • rps (recibos provisórios)              │              │
│  │  • nsu_nfse (controle NSU)                │              │
│  │  • certificados (do sistema principal)    │              │
│  └──────────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Componentes Principais

### 1. NFSeDatabase

**Arquivo**: `nfse_search.py` (linhas 278-428)

**Responsabilidade**: Gerenciar toda a persistência de dados relacionados a NFS-e.

#### Métodos Principais

```python
class NFSeDatabase:
    def __init__(self, db_path=DB_PATH):
        """Inicializa conexão com banco SQLite"""
        
    def _criar_tabelas(self):
        """Cria tabelas NFS-e se não existirem"""
        
    def get_certificados(self):
        """Busca certificados cadastrados"""
        
    def get_config_nfse(self, cnpj):
        """Busca configurações de um CNPJ"""
        
    def adicionar_config_nfse(self, cnpj, provedor, cod_municipio, ...):
        """Adiciona/atualiza configuração"""
        
    def salvar_nfse(self, numero, cnpj_prestador, ...):
        """Salva NFS-e baixada"""
        
    def get_last_nsu_nfse(self, informante):
        """Retorna último NSU processado"""
        
    def set_last_nsu_nfse(self, informante, nsu):
        """Atualiza último NSU processado"""
```

#### Diagrama de Relacionamentos

```
┌─────────────────────┐
│   certificados      │
│   (sistema pai)     │
│                     │
│  • cnpj_cpf (PK)    │
│  • caminho          │
│  • senha            │
│  • informante       │
│  • cuf              │
└──────────┬──────────┘
           │ 1
           │
           │ N
┌──────────▼──────────┐
│   nfse_config       │
│                     │
│  • id (PK)          │
│  • cnpj_cpf (FK)◄───┼──────┐
│  • provedor         │      │
│  • codigo_municipio │      │ UNIQUE
│  • inscricao_mun    │      │ (cnpj, cod_mun)
│  • url_customizada  │      │
│  • ativo            │      │
└──────────┬──────────┘      │
           │                 │
           │ 1               │
           │                 │
           │ N               │
┌──────────▼──────────┐      │
│  nfse_baixadas      │      │
│                     │      │
│  • numero_nfse (PK) │      │
│  • cnpj_prestador◄──┼──────┘
│  • cnpj_tomador     │
│  • data_emissao     │
│  • valor_servico    │
│  • xml_content      │
│  • data_download    │
└─────────────────────┘

┌─────────────────────┐
│   rps               │
│                     │
│  • numero_rps       │◄── PK: (numero_rps, 
│  • serie_rps        │         serie_rps,
│  • cnpj_prestador   │         cnpj_prestador)
│  • data_emissao     │
│  • status           │
│  • numero_nfse      │
└─────────────────────┘

┌─────────────────────┐
│   nsu_nfse          │
│                     │
│  • informante (PK)  │
│  • ult_nsu          │
│  • atualizado_em    │
└─────────────────────┘
```

---

### 2. NFSeService

**Arquivo**: `nfse_search.py` (linhas 512-1120)

**Responsabilidade**: Comunicar com APIs municipais e processar respostas.

#### Métodos Principais

```python
class NFSeService:
    def __init__(self, certificado_path, senha, cnpj):
        """Inicializa serviço com certificado"""
        
    def buscar_ginfes(self, codigo_municipio, inscricao_municipal, ...):
        """Busca via SOAP Ginfes/ABRASF"""
        
    def buscar_nuvemfiscal(self, cpf_cnpj, data_inicial, ...):
        """Busca via REST Nuvem Fiscal (agregador)"""
        
    def buscar_adn_rest(self, codigo_municipio, ...):
        """Busca via REST ADN Nacional (limitado)"""
        
    def _processar_resposta_ginfes(self, xml_resposta):
        """Parse XML SOAP e extração de NFS-e"""
        
    def extrair_cstat_nsu(self, xml_resposta):
        """Extrai status e NSU da resposta"""
        
    def _formatar_data(self, data_str):
        """Converte DD/MM/YYYY para YYYY-MM-DD"""
```

#### Fluxo de Busca SOAP

```
┌──────────────────┐
│  buscar_ginfes() │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 1. Busca informações do município   │
│    (URLS_MUNICIPIOS)                │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 2. Verifica se usa Nuvem Fiscal     │
│    → SIM: buscar_nuvemfiscal()      │
│    → NÃO: continua SOAP             │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 3. Monta XML SOAP (ABRASF)          │
│    • ConsultarNfseEnvio             │
│    • Prestador (CNPJ + IM)          │
│    • PeriodoEmissao (datas)         │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 4. Tenta cada URL configurada       │
│    • POST com certificado A1        │
│    • Timeout: 15 segundos           │
│    • Retry em caso de erro          │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 5. Processa resposta XML            │
│    _processar_resposta_ginfes()     │
│    • Parse com lxml                 │
│    • Extração de erros              │
│    • Extração de NFS-e              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 6. Retorna resultado                │
│    {                                │
│      "status": "sucesso" | "erro",  │
│      "mensagem": str,               │
│      "notas": [...]                 │
│    }                                │
└─────────────────────────────────────┘
```

#### Fluxo de Busca REST (Nuvem Fiscal)

```
┌─────────────────────────┐
│ buscar_nuvemfiscal()    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 1. Inicializa NuvemFiscalAPI        │
│    (OAuth2 token management)        │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 2. Converte datas (DD/MM → YYYY-MM) │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 3. GET /nfse?parametros             │
│    Headers:                         │
│      Authorization: Bearer {token}  │
│    Query:                           │
│      cpf_cnpj, data_inicial,        │
│      data_final, codigo_municipio   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 4. Processa JSON response           │
│    • count: total de notas          │
│    • data: array de NFS-e           │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 5. Retorna lista de notas           │
│    [                                │
│      {                              │
│        "numero": str,               │
│        "data_emissao": str,         │
│        "valor_servicos": float,     │
│        ...                          │
│      }                              │
│    ]                                │
└─────────────────────────────────────┘
```

---

## 🗂️ Estrutura de Dados

### Configuração de Provedor

```python
URLS_MUNICIPIOS = {
    "5002704": {  # Código IBGE (Campo Grande/MS)
        "nome": "Campo Grande",
        "uf": "MS",
        "urls": [
            "https://nfse.pmcg.ms.gov.br/ws/nfse.asmx",
            "https://nfse.pmcg.ms.gov.br/IssWeb-ejb/IssWebWS/IssWebWS"
        ],
        "versao": "2.02",  # Versão ABRASF
        "provedor": "NUVEMFISCAL",  # Ou GINFES, ISSNET, etc.
        "tipo_api": "REST"  # SOAP ou REST
    }
}
```

### Provedores Disponíveis

```python
PROVEDORES_NFSE = {
    "GINFES": {
        "nome": "Ginfes",
        "descricao": "Sistema Nacional NFS-e",
        "url_base": "https://nfse.ginfes.com.br/ServiceGinfesImpl",
        "municipios": ["Várias cidades"],
        "versao": "2.02"
    },
    "NUVEMFISCAL": {
        "nome": "Nuvem Fiscal",
        "descricao": "Agregador terceirizado REST",
        "url_base": "https://api.nuvemfiscal.com.br",
        "tipo_api": "REST",
        "requer_certificado": False  # Usa OAuth2
    }
}
```

---

## 🔄 Fluxo de Execução Completo

### CLI (Menu Interativo)

```
┌─────────────────────────────────────────────────────────────┐
│                  menu_principal()                            │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Inicializa NFSeDatabase()                               │
│  2. Lista certificados cadastrados                          │
│  3. Exibe menu:                                             │
│     [1] Listar provedores                                   │
│     [2] Configurar NFS-e                                    │
│     [3] Buscar NFS-e                                        │
│     [0] Sair                                                │
└────────┬────────────────────────────────────────────────────┘
         │
         ├─► Opção 1: listar_provedores()
         │            └─► Exibe PROVEDORES_NFSE
         │
         ├─► Opção 2: configurar_nfse(db, certificados)
         │            ├─► Escolhe certificado
         │            ├─► consultar_cnpj() (BrasilAPI)
         │            ├─► buscar_codigo_ibge() (IBGE API)
         │            ├─► Escolhe provedor
         │            └─► db.adicionar_config_nfse()
         │
         └─► Opção 3: buscar_nfse_agora(db, certificados)
                      ├─► Escolhe certificado
                      ├─► Solicita período (data inicial/final)
                      ├─► Para cada município configurado:
                      │   ├─► NFSeService.buscar_ginfes()
                      │   │   ou buscar_nuvemfiscal()
                      │   ├─► Processa notas encontradas
                      │   └─► db.salvar_nfse()
                      └─► Exibe relatório final
```

### Integração com Sistema Principal

O sistema pode ser integrado via:

#### 1. Thread Worker (PyQt5)

```python
from PyQt5.QtCore import QThread, pyqtSignal

class NFSeBuscaWorker(QThread):
    progresso = pyqtSignal(int, int, str)
    concluido = pyqtSignal(dict)
    
    def __init__(self, certificado_path, senha, cnpj, ...):
        self.service = NFSeService(certificado_path, senha, cnpj)
    
    def run(self):
        # Busca em background
        resultado = self.service.buscar_ginfes(...)
        
        # Emite sinais de progresso
        self.progresso.emit(current, total, "Processando...")
        
        # Emite resultado final
        self.concluido.emit(resultado)
```

#### 2. Chamada Direta

```python
from nfse_search import NFSeService, NFSeDatabase

# Buscar e salvar
service = NFSeService("cert.pfx", "senha", "12345678000199")
db = NFSeDatabase()

resultado = service.buscar_ginfes("5002704", "12345", "01/01/2025", "31/01/2025")

for nota in resultado['notas']:
    db.salvar_nfse(
        nota['numero'],
        "12345678000199",
        nota['tomador_cnpj'],
        nota['data_emissao'],
        nota['valor'],
        nota['xml']
    )
```

---

## 🔐 Autenticação e Certificados

### Certificado A1 (.pfx)

```
┌─────────────────────────────────────────┐
│  Certificado A1 (PKCS#12)               │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Private Key (chave privada)      │ │
│  │  • Usado para assinar requisições │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Certificate (certificado)        │ │
│  │  • Contém chave pública           │ │
│  │  • Identifica a empresa (CN=CNPJ) │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  CA Chain (cadeia de certificação)│ │
│  │  • Autoridade Certificadora       │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Fluxo de Autenticação SOAP

```
Cliente ──┐
          │
          │ 1. Carrega certificado .pfx com senha
          ▼
┌────────────────────┐
│  requests_pkcs12   │
│  (biblioteca)      │
└────────┬───────────┘
         │
         │ 2. Extrai chave privada e certificado
         ▼
┌────────────────────┐
│  TLS Handshake     │
│  (SSL/TLS)         │
└────────┬───────────┘
         │
         │ 3. Apresenta certificado ao servidor
         ▼
┌────────────────────┐
│  Servidor Municipal│
│  (SOAP)            │
└────────┬───────────┘
         │
         │ 4. Valida certificado
         │    • Cadeia de certificação OK?
         │    • Data de validade OK?
         │    • CNPJ corresponde?
         ▼
┌────────────────────┐
│  Autorizado        │
│  Processa requisição│
└────────────────────┘
```

### OAuth2 (Nuvem Fiscal)

```
Cliente ──┐
          │
          │ 1. Credenciais (client_id, client_secret)
          ▼
┌────────────────────┐
│  POST /oauth/token │
└────────┬───────────┘
         │
         │ 2. Retorna access_token (JWT)
         ▼
┌────────────────────┐
│  Token válido por  │
│  X horas           │
└────────┬───────────┘
         │
         │ 3. Usa token em todas as requisições
         │    Authorization: Bearer {token}
         ▼
┌────────────────────┐
│  GET /api/nfse     │
│  (com token)       │
└────────┬───────────┘
         │
         │ 4. Valida token no backend
         ▼
┌────────────────────┐
│  Autorizado        │
│  Retorna dados     │
└────────────────────┘
```

---

## 📡 Comunicação com APIs

### SOAP Request (ABRASF)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <ConsultarNfseEnvioRequest xmlns="http://www.ginfes.com.br">
            <nfseCabecMsg><![CDATA[
                <?xml version="1.0" encoding="UTF-8"?>
                <cabecalho versao="3" xmlns="http://www.abrasf.org.br/nfse.xsd">
                    <versaoDados>3</versaoDados>
                </cabecalho>
            ]]></nfseCabecMsg>
            <nfseDadosMsg><![CDATA[
                <ConsultarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
                    <Prestador>
                        <Cnpj>12345678000199</Cnpj>
                        <InscricaoMunicipal>12345</InscricaoMunicipal>
                    </Prestador>
                    <PeriodoEmissao>
                        <DataInicial>2025-01-01</DataInicial>
                        <DataFinal>2025-01-31</DataFinal>
                    </PeriodoEmissao>
                </ConsultarNfseEnvio>
            ]]></nfseDadosMsg>
        </ConsultarNfseEnvioRequest>
    </soap:Body>
</soap:Envelope>
```

### SOAP Response (ABRASF)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
            <ListaNfse>
                <CompNfse>
                    <Nfse>
                        <InfNfse>
                            <Numero>123456</Numero>
                            <DataEmissao>2025-01-15</DataEmissao>
                            <ValoresNfse>
                                <ValorServicos>1500.00</ValorServicos>
                            </ValoresNfse>
                            <PrestadorServico>
                                <IdentificacaoPrestador>
                                    <Cnpj>12345678000199</Cnpj>
                                    <InscricaoMunicipal>12345</InscricaoMunicipal>
                                </IdentificacaoPrestador>
                            </PrestadorServico>
                            <TomadorServico>
                                <IdentificacaoTomador>
                                    <CpfCnpj>
                                        <Cnpj>98765432000100</Cnpj>
                                    </CpfCnpj>
                                </IdentificacaoTomador>
                            </TomadorServico>
                        </InfNfse>
                    </Nfse>
                </CompNfse>
            </ListaNfse>
        </ConsultarNfseResposta>
    </soap:Body>
</soap:Envelope>
```

### REST Request (Nuvem Fiscal)

```http
GET /api/v1/nfse?cpf_cnpj=12345678000199&data_inicial=2025-01-01&data_final=2025-01-31&codigo_municipio=5002704 HTTP/1.1
Host: api.nuvemfiscal.com.br
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Accept: application/json
```

### REST Response (Nuvem Fiscal)

```json
{
  "count": 10,
  "data": [
    {
      "numero": "123456",
      "codigo_verificacao": "ABC123DEF",
      "data_emissao": "2025-01-15T10:30:00",
      "status": "AUTORIZADA",
      "declaracao_prestacao_servico": {
        "tomador": {
          "cpf_cnpj": "98765432000100",
          "razao_social": "Empresa Tomadora LTDA"
        },
        "servicos": [
          {
            "valor_servicos": 1500.00,
            "valor_iss": 75.00,
            "aliquota": 5.0
          }
        ]
      }
    }
  ]
}
```

---

## 🔍 Parse e Processamento

### Extração de Dados (lxml)

```python
from lxml import etree

def processar_nfse(xml_string):
    # Parse XML
    root = etree.fromstring(xml_string.encode('utf-8'))
    
    # Namespace ABRASF
    ns = {'nfse': 'http://www.abrasf.org.br/nfse.xsd'}
    
    # XPath para extrair dados
    numero = root.xpath('.//nfse:Numero/text()', namespaces=ns)[0]
    data = root.xpath('.//nfse:DataEmissao/text()', namespaces=ns)[0]
    valor = root.xpath('.//nfse:ValorServicos/text()', namespaces=ns)[0]
    
    return {
        'numero': numero,
        'data_emissao': data,
        'valor': float(valor)
    }
```

---

## 📝 Logging

### Estrutura de Logs

```
logs/
├── busca_nfse_2025-01-13.log
├── busca_nfse_2025-01-14.log
└── busca_nfse_2025-01-15.log
```

### Níveis de Log

```python
logger.debug("📤 SOAP Envelope montado (1500 bytes)")  # Desenvolvimento
logger.info("✅ CNPJ consultado com sucesso!")         # Informação
logger.warning("⚠️  URL não respondeu")                  # Aviso
logger.error("❌ Erro ao processar XML")                 # Erro
logger.critical("🔥 Erro fatal no sistema")            # Crítico
```

### Exemplo de Log

```
2025-01-13 10:30:15 INFO 🔍 Consultando CNPJ 12345678000199 via BrasilAPI...
2025-01-13 10:30:16 INFO ✅ CNPJ consultado com sucesso!
2025-01-13 10:30:16 INFO    Razão Social: EMPRESA EXEMPLO LTDA
2025-01-13 10:30:16 INFO    Município: Campo Grande/MS
2025-01-13 10:30:16 INFO    Código IBGE: 5002704
2025-01-13 10:30:16 INFO 🔍 Buscando NFS-e para município 5002704
2025-01-13 10:30:16 INFO 📅 Período: 2025-01-01 a 2025-01-31
2025-01-13 10:30:16 DEBUG 📤 SOAP Envelope montado (1456 bytes)
2025-01-13 10:30:16 INFO 🌐 [1/3] Tentando: https://nfse.pmcg.ms.gov.br/ws/nfse.asmx
2025-01-13 10:30:18 INFO 📥 Resposta recebida: HTTP 200
2025-01-13 10:30:18 INFO ✅ Servidor respondeu com sucesso!
2025-01-13 10:30:18 INFO 🔄 Processando resposta XML...
2025-01-13 10:30:18 INFO ✅ 5 NFS-e encontrada(s)!
2025-01-13 10:30:18 INFO    📄 NFS-e 123456 - R$ 1500.00 - 2025-01-15
2025-01-13 10:30:18 INFO 💾 NFS-e 123456 salva no banco
```

---

## 🚀 Performance e Otimizações

### Timeouts

```python
# Requisições SOAP: 15 segundos
response = requests_pkcs12.post(url, data=xml, timeout=15)

# APIs públicas (CNPJ, IBGE): 5-10 segundos
response = requests.get(url, timeout=10)
```

### Retry Logic

```python
# Tenta múltiplas URLs até sucesso
for idx, url in enumerate(urls_tentar, 1):
    try:
        response = requests_pkcs12.post(url, ...)
        if response.status_code == 200:
            resultado = processar_resposta(response.text)
            if resultado['status'] != 'erro':
                return resultado  # Sucesso - retorna
    except Exception as e:
        logger.warning(f"URL {idx} falhou - tentando próxima")
        continue  # Tenta próxima URL

# Se todas falharam
return {"status": "erro", "mensagem": "Nenhuma URL funcionou"}
```

### Batch Processing

```python
# Processar múltiplos municípios em sequência
configs = db.get_config_nfse(cnpj)

for provedor, cod_mun, insc_mun, url in configs:
    resultado = service.buscar_ginfes(...)
    
    for nota in resultado['notas']:
        db.salvar_nfse(...)  # Commit por nota
```

---

## 🔗 Integração com Sistema Principal

### DatabaseManager do Sistema Principal

```python
# Importa gerenciador do banco principal
from nfe_search import DatabaseManager

# Usa banco principal (notas.db)
main_db = DatabaseManager(str(BASE_DIR / "notas.db"))

# Busca certificados do sistema principal
certificados = main_db.get_certificados()
```

### Comunicação via Signals (PyQt5)

```python
class NFSeBuscaWorker(QThread):
    progresso = pyqtSignal(int, int, str)    # (atual, total, mensagem)
    nota_encontrada = pyqtSignal(dict)       # Emite cada nota
    concluido = pyqtSignal(dict)             # Resultado final
    erro = pyqtSignal(str)                    # Erros

# Na interface principal:
worker = NFSeBuscaWorker (...)
worker.progresso.connect(self.atualizar_progresso)
worker.nota_encontrada.connect(self.adicionar_nota_tabela)
worker.concluido.connect(self.finalizar_busca)
worker.erro.connect(self.exibir_erro)
worker.start()
```

---

## 📚 Referências

- **ABRASF**: [Padrão Nacional NFS-e](https://abrasf.org.br)
- **ADN**: [Documentação Oficial](https://adn.producaorestrita.nfse.gov.br/docs/)
- **lxml**: [Documentação](https://lxml.de/)
- **requests**: [Documentação](https://requests.readthedocs.io/)
- **SQLite**: [Documentação](https://www.sqlite.org/docs.html)

---

**Próximos Passos**

Para mais detalhes sobre aspectos específicos, consulte:
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Estrutura completa do banco
- [API_GUIDE.md](API_GUIDE.md) - Guia de APIs e endpoints
- [PROVIDERS.md](PROVIDERS.md) - Provedores de NFS-e
- [WEB_MIGRATION.md](WEB_MIGRATION.md) - Migração para web
