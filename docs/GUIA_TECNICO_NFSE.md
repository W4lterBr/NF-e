# 🔧 Guia Técnico - Busca Automática de NFS-e

## Para Desenvolvedores e Mantenedores

---

## 📐 Arquitetura do Sistema

### Componentes Principais

```
┌──────────────────────────────────────────────────────┐
│               BUSCA NF-E.PY (UI PRINCIPAL)           │
│                                                       │
│  ┌─────────────────────────────────────────────┐   │
│  │  MainWindow                                  │   │
│  │                                              │   │
│  │  refresh_all()                               │   │
│  │      ↓                                       │   │
│  │  LoadNotesWorker (QThread)                   │   │
│  │      ↓                                       │   │
│  │  on_loaded()                                 │   │
│  │      ↓                                       │   │
│  │  QTimer.singleShot(2000, _buscar_nfse_...)  │   │
│  │      ↓                                       │   │
│  │  _buscar_nfse_automatico()                   │   │
│  │      ↓                                       │   │
│  │  NFSeBuscaWorker (QThread)                   │   │
│  │      ↓                                       │   │
│  │  subprocess.run(buscar_nfse_auto.py)         │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│          BUSCAR_NFSE_AUTO.PY (WORKER SCRIPT)         │
│                                                       │
│  buscar_todos_certificados()                         │
│      ↓                                               │
│  processar_certificado()                             │
│      ↓                                               │
│  consultar_nfse_incremental()                        │
│      ↓                                               │
│  NFSeService.buscar_documentos()                     │
│      ↓                                               │
│  API ADN REST                                        │
│      ↓                                               │
│  salvar_nfse_detalhada()                             │
│      ↓                                               │
│  SQLite (notas_detalhadas)                           │
└──────────────────────────────────────────────────────┘
```

---

## 🔌 Pontos de Integração

### 1. Trigger Automático (Busca NF-e.py)

**Arquivo**: `Busca NF-e.py`  
**Linha**: ~2554  
**Método**: `refresh_all() → on_loaded()`

```python
# Busca automática de NFS-e após carregar dados (em thread separada)
QTimer.singleShot(2000, self._buscar_nfse_automatico)
```

**Por que 2 segundos?**
- Aguarda conclusão de operações de UI (populate tables, PDF cache)
- Evita sobrecarga imediata do sistema
- Usuário vê feedback visual antes da busca NFS-e iniciar

### 2. Worker Thread (Busca NF-e.py)

**Arquivo**: `Busca NF-e.py`  
**Linha**: ~2591  
**Método**: `_buscar_nfse_automatico()`

```python
class NFSeBuscaWorker(QThread):
    def run(self):
        script_path = BASE_DIR / 'buscar_nfse_auto.py'
        subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos
        )
```

**Decisões de Design:**

| Decisão | Motivo |
|---------|--------|
| QThread ao invés de threading.Thread | Integração nativa com PyQt5 |
| subprocess ao invés de import direto | Isolamento de processo (evita conflitos de logging, signals) |
| timeout=300 | ADN pode demorar, mas 5 min é limite razoável |
| capture_output=True | Permite log de erros sem poluir stdout principal |

### 3. Motor de Busca (buscar_nfse_auto.py)

**Arquivo**: `buscar_nfse_auto.py`  
**Função principal**: `buscar_todos_certificados(busca_completa=False)`

**Fluxo de Execução:**

```python
def buscar_todos_certificados(busca_completa=False):
    """
    1. Conecta ao banco de dados (notas.db)
    2. Busca todos certificados ativos
    3. Para cada certificado:
       a. Verifica configuração NFS-e
       b. Chama processar_certificado()
       c. Trata erros individuais
    4. Retorna resumo
    """
```

**Vantagens desta arquitetura:**
- ✅ Cada certificado é independente (erro em um não afeta outros)
- ✅ Busca incremental por padrão (eficiente)
- ✅ Logs detalhados por certificado
- ✅ Fácil adicionar novos certificados sem modificar código

---

## 🗃️ Banco de Dados

### Tabelas Utilizadas

#### 1. `certificados`
```sql
CREATE TABLE certificados (
    cnpj_cpf TEXT PRIMARY KEY,
    caminho TEXT,
    senha TEXT,
    informante TEXT,
    cUF_autor INTEGER,
    razao_social TEXT,
    ativo INTEGER DEFAULT 1
);
```

**Uso**: Itera sobre certificados ativos para buscar NFS-e.

#### 2. `nsu_nfse`
```sql
CREATE TABLE nsu_nfse (
    informante TEXT PRIMARY KEY,
    ultimo_nsu INTEGER DEFAULT 0,
    data_ultima_atualizacao TEXT
);
```

**Uso**: Controla qual foi o último NSU processado (busca incremental).

#### 3. `notas_detalhadas`
```sql
CREATE TABLE notas_detalhadas (
    chave TEXT PRIMARY KEY,
    tipo_documento TEXT,  -- "NFSe"
    numero TEXT,
    data_emissao TEXT,
    cnpj_emitente TEXT,
    cnpj_destinatario TEXT,
    valor_total REAL,
    xml_status TEXT,  -- "disponível" | "não disponível"
    -- ... outros campos
);
```

**Uso**: Armazena todas as NFS-e baixadas (mesma tabela de NF-e/CT-e).

---

## 🌐 API ADN

### Endpoint Principal

```
POST https://adn.nfse.gov.br/api/v1/consultar
```

### Autenticação

**Método**: mTLS (Mutual TLS)  
**Certificado**: PKCS12 (.pfx)  
**Senha**: Armazenada criptografada no banco

```python
session.cert = (cert_pem_path, key_pem_path)
session.verify = True  # Valida certificado do servidor
```

### Request Body

```json
{
  "informante": "47539664000197",
  "nsuInicial": "000000000000000",
  "tipoDocumento": "nfse"
}
```

### Response Body

```json
{
  "ultNSU": "000000000000042",
  "maxNSU": "000000000000042",
  "documentos": [
    {
      "nsu": "000000000000001",
      "xml": "<nfse>...</nfse>",
      "tipo": "nfse"
    }
  ]
}
```

### Rate Limiting

**Limite**: ~60 requests/min  
**Código de erro**: 429 Too Many Requests

**Estratégia de retry:**
```python
for tentativa in range(1, 4):  # 3 tentativas
    try:
        response = session.post(url, json=payload)
        if response.status_code == 502:  # Bad Gateway
            time.sleep(2 ** tentativa)  # Backoff exponencial
            continue
        return response
    except Exception as e:
        if tentativa == 3:
            raise
```

---

## 📝 Processamento de XML

### Parse de NFS-e

**Namespace**: `http://www.sped.fazenda.gov.br/nfse`

```python
from lxml import etree

tree = etree.fromstring(xml_content.encode('utf-8'))
ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}

# Extração de campos
numero = tree.findtext('.//nfse:nNFSe', namespaces=ns)
data_emissao = tree.findtext('.//nfse:dhEmi', namespaces=ns)
valor = tree.findtext('.//nfse:vServ', namespaces=ns)
```

### Estrutura do XML NFS-e (Padrão Nacional)

```xml
<nfse xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFSe123">
    <nNFSe>123</nNFSe>
    <dhEmi>2024-12-15T10:30:00</dhEmi>
    <cMunPrestacao>5208707</cMunPrestacao>
    <ChaveAcesso>52087072250861055000164000000000...</ChaveAcesso>
    <vServ>6000.00</vServ>
    <prestador>
      <CNPJ>25086105500016</CNPJ>
    </prestador>
    <tomador>
      <CNPJ>47539664000197</CNPJ>
    </tomador>
  </infNFSe>
</nfse>
```

### Chave de Acesso

**Formato**: 44 dígitos (igual NF-e)

```
UUMMAANN...CCCCCCC
│ │ │ │    └─ Código verificador
│ │ │ └────── Número da NFS-e
│ │ └──────── CNPJ prestador
│ └────────── Município
└──────────── UF
```

Exemplo:
```
52087072250861055000164000000000001123124542225139
││  │   │               │       │
│└──┴───┴─CNPJ──────────┴──NFS-e└─CV
└─UF+Município
```

---

## � Estrutura de Armazenamento

### Padrão Unificado (v2026-01-29)

A partir desta versão, **NFS-e segue o mesmo padrão de NF-e e CT-e**:

```
xmls/
└── {CNPJ}/
    └── {ANO-MES}/
        ├── NFe/
        │   ├── 12345-FORNECEDOR_A.xml
        │   └── 12345-FORNECEDOR_A.pdf
        ├── CTe/
        │   ├── 67890-TRANSPORTADORA_B.xml
        │   └── 67890-TRANSPORTADORA_B.pdf
        └── NFSe/                          ← ✨ NOVO
            ├── 123-PRESTADOR_C.xml        ← Padrão unificado
            └── 123-PRESTADOR_C.pdf        ← DANFSe oficial
```

### Configuração de Formato

**Chave do banco**: `storage_formato_mes`  
**Valores possíveis**:
- `AAAA-MM` (padrão): `2026-01/`
- `MM-AAAA`: `01-2026/`
- `AAAA/MM`: `2026/01/`
- `MM/AAAA`: `01/2026/`

**Implementação** (`buscar_nfse_auto.py`):

```python
def salvar_xml_nfse(db, cnpj, xml_content, numero_nfse, data_emissao):
    # Lê formato do banco (mesmo usado por NF-e e CT-e)
    formato_mes = db.get_config('storage_formato_mes', 'AAAA-MM')
    
    # Aplica formato
    if formato_mes == 'MM-AAAA':
        ano_mes = f"{mes}-{ano}"
    elif formato_mes == 'AAAA/MM':
        ano_mes = f"{ano}/{mes}"
    # ... outros formatos
    
    # Extrai nome do prestador do XML
    xNome = extrair_razao_social(xml_content) or "NFSe"
    
    # Pasta: xmls/{CNPJ}/{ANO-MES}/NFSe/
    pasta = Path("xmls") / cnpj / ano_mes / "NFSe"
    
    # Arquivo: {NUMERO}-{PRESTADOR}.xml (mesmo padrão de NF-e)
    arquivo = pasta / f"{numero_nfse}-{xNome}.xml"
```

### Vantagens do Padrão Unificado

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **Nomenclatura** | `NFSe_123.xml` | `123-PRESTADOR.xml` |
| **Identificação** | Só número | Número + Nome |
| **Formato pasta** | Fixo `MM-AAAA` | Configurável |
| **Consistência** | Diferente de NF-e | Igual NF-e/CT-e |
| **Manutenção** | Código separado | Reutiliza funções |

### Migração de Arquivos Antigos

Arquivos no formato antigo continuam sendo lidos normalmente:
- Interface busca em **ambos** os padrões
- Novos arquivos usam padrão unificado
- Migração automática não é necessária

---

## �🔒 Segurança

### Tratamento de Certificados

```python
# 1. Certificado PKCS12 armazenado no banco (binário)
pkcs12_data = cert_from_db

# 2. Conversão para PEM (temporário)
from OpenSSL import crypto
p12 = crypto.load_pkcs12(pkcs12_data, senha)
cert_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())
key_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())

# 3. Uso em requests
import requests
session = requests.Session()
session.cert = (cert_pem_path, key_pem_path)
```

**⚠️ Segurança:**
- Arquivos PEM são criados em `temp/` com permissões restritas
- Deletados após uso
- Senha do certificado armazenada criptografada no banco

### Criptografia de Senhas

**Algoritmo**: Fernet (AES 128-bit)  
**Chave**: Derivada de master password + salt

```python
from cryptography.fernet import Fernet

# Criptografar
cipher = Fernet(key)
senha_cripto = cipher.encrypt(senha_plain.encode())

# Descriptografar
senha_plain = cipher.decrypt(senha_cripto).decode()
```

---

## 🧪 Testes

### Teste Manual

```bash
# Teste simples (consulta maxNSU)
python tests/test_nfse_simples.py

# Teste completo (baixa documentos)
python buscar_nfse_auto.py

# Teste com busca completa (reprocessa tudo)
python buscar_nfse_auto.py --completa
```

### Teste Unitário (Exemplo)

```python
import pytest
from modules.nfse_service import NFSeService

def test_nfse_service_init():
    """Testa inicialização do serviço NFS-e"""
    service = NFSeService(
        cert_path="cert.pfx",
        senha="senha123",
        informante="12345678000190",
        cuf=50,
        ambiente='producao'
    )
    assert service.informante == "12345678000190"
    assert service.base_url == "https://adn.nfse.gov.br"

def test_parse_xml_nfse():
    """Testa parse de XML NFS-e"""
    from nfse_search import extrair_dados_nfse
    
    xml = """
    <nfse xmlns="...">
      <infNFSe><nNFSe>123</nNFSe></infNFSe>
    </nfse>
    """
    
    dados = extrair_dados_nfse(xml)
    assert dados['numero'] == '123'
```

---

## 📊 Monitoramento e Debug

### Logs Estruturados

```python
import logging

logger = logging.getLogger('nfse_search')
logger.setLevel(logging.INFO)

# Formato
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

### Pontos de Log Importantes

```python
# 1. Início da busca
logger.info(f"BUSCANDO NFS-e VIA AMBIENTE NACIONAL")
logger.info(f"CNPJ: {cnpj}")

# 2. Resultado da consulta
logger.info(f"✅ {len(documentos)} documento(s) encontrado(s)")

# 3. Salvamento de dados
logger.info(f"💾 XML salvo: {caminho_xml}")
logger.info(f"✅ NFS-e {numero}: R$ {valor} salva em notas_detalhadas")

# 4. Erros
logger.error(f"❌ Erro ao processar certificado: {e}")
```

### Debug de Performance

```python
import time

inicio = time.time()
# ... código ...
fim = time.time()
logger.debug(f"Tempo de execução: {fim - inicio:.2f}s")
```

### Debug de Rede

```python
import requests

# Habilitar logs de requests
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests.packages.urllib3").propagate = True
```

---

## 🚧 Limitações Conhecidas

### 1. Timeout de 5 Minutos

**Problema**: Se houver muitos documentos, pode exceder timeout.

**Solução Atual**: Processo é encerrado, mas parcialmente processado.

**Solução Futura**: Aumentar timeout ou implementar checkpoints.

### 2. API ADN Instável

**Problema**: Erros 502 (Bad Gateway) frequentes.

**Solução Atual**: Retry com backoff exponencial (3 tentativas).

**Solução Futura**: Fila de requisições com retry assíncrono.

### 3. Chave de Acesso Incompleta

**Problema**: Alguns XMLs não contêm `<ChaveAcesso>`.

**Solução Atual**: Usa `NSU_{nsu}` como identificador.

**Solução Futura**: Gerar chave sinteticamente baseado em dados do XML.

### 4. Múltiplas Instâncias

**Problema**: Se duas instâncias rodarem simultaneamente, podem processar mesmos NSUs.

**Solução Atual**: Lock a nível de processo (não protege contra múltiplos processos).

**Solução Futura**: Lock distribuído no banco de dados.

---

## 🔄 Fluxo de Dados Completo

```
┌────────────────┐
│ Usuário        │
│ clica          │
│ "Atualizar"    │
└────────┬───────┘
         ↓
┌────────────────────────────────┐
│ refresh_all()                  │
│ - Carrega notas do banco       │
│ - Popula tabelas               │
│ - Agenda busca NFS-e (2s)      │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ _buscar_nfse_automatico()      │
│ - Cria NFSeBuscaWorker         │
│ - Inicia thread                │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ subprocess.run()               │
│ - Executa buscar_nfse_auto.py  │
│ - Timeout: 5 minutos           │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ buscar_todos_certificados()    │
│ - SELECT * FROM certificados   │
│ - Loop por cada certificado    │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ processar_certificado()        │
│ - Busca último NSU             │
│ - Chama consultar_nfse_...()   │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ consultar_nfse_incremental()   │
│ - POST /api/v1/consultar       │
│ - Parse JSON response          │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ API ADN                        │
│ - Valida certificado           │
│ - Retorna documentos           │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ Parse XML                      │
│ - Extrai campos (lxml)         │
│ - Valida estrutura             │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ salvar_nfse_detalhada()        │
│ - INSERT notas_detalhadas      │
│ - UPDATE nsu_nfse              │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ Salvar arquivos                │
│ - XML em xmls/{CNPJ}/...       │
│ - PDF (DANFSe oficial)         │
└────────────────────────────────┘
```

---

## 📚 Referências de Código

### Arquivos Principais

| Arquivo | Linhas | Responsabilidade |
|---------|--------|------------------|
| `Busca NF-e.py` | ~15.000 | Interface principal, coordenação |
| `buscar_nfse_auto.py` | 451 | Motor de busca NFS-e |
| `nfse_search.py` | ~3.000 | Processamento XML, banco de dados |
| `modules/nfse_service.py` | ~500 | Cliente REST API ADN |

### Funções Críticas

```python
# 1. Coordenação
Busca NF-e.py::_buscar_nfse_automatico()

# 2. Busca
buscar_nfse_auto.py::buscar_todos_certificados()
buscar_nfse_auto.py::processar_certificado()

# 3. API
modules/nfse_service.py::consultar_nfse_incremental()
modules/nfse_service.py::NFSeService.buscar_documentos()

# 4. Persistência
nfse_search.py::salvar_nfse_detalhada()
nfse_search.py::extrair_dados_nfse()
```

---

## 🎓 Boas Práticas

### Para Modificar o Código

1. **Sempre teste manualmente primeiro**:
   ```bash
   python buscar_nfse_auto.py
   ```

2. **Verifique logs após mudanças**:
   ```bash
   tail -f logs/busca_nfe_*.log
   ```

3. **Use type hints**:
   ```python
   def processar_certificado(db: NFSeDatabase, cert: tuple) -> int:
       ...
   ```

4. **Documente funções complexas**:
   ```python
   def consultar_nfse_incremental(...):
       """
       Consulta NFS-e incrementalmente a partir do último NSU.
       
       Args:
           db: Instância do banco de dados
           cert_path: Caminho do certificado .pfx
           ...
           
       Returns:
           Lista de tuplas (nsu, xml_content, tipo_doc)
       """
   ```

### Para Adicionar Funcionalidades

1. **Novos endpoints**: Adicione em `modules/nfse_service.py`
2. **Novos campos XML**: Adicione em `nfse_search.py::extrair_dados_nfse()`
3. **Novos logs**: Use logger existente, não crie novo
4. **Novas tabelas**: Adicione migração em `nfe_search.py`

---

**Autor**: Sistema BOT Busca NFE  
**Versão**: 2.0  
**Última atualização**: 29/01/2026
