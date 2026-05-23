# 🗺️ Mapa de Funções - Sistema Busca NF-e/CT-e

> 📋 **Referência Rápida**: Localização exata de todas as funções principais do sistema
> 
> 🔍 **Como usar**: Busque pelo nome da função para encontrar sua localização e descrição

---

## 📑 Índice

1. [Funções de Extração de Dados](#funcoes-extracao)
2. [Funções de Comunicação SEFAZ](#funcoes-comunicacao)
3. [Funções de Processamento](#funcoes-processamento)
4. [Funções de Armazenamento](#funcoes-armazenamento)
5. [Funções de Banco de Dados](#funcoes-banco)
6. [Funções da Interface GUI](#funcoes-interface)

---

<a name="funcoes-extracao"></a>
## 1️⃣ Funções de Extração de Dados

### `extrair_nota_detalhada()`
**Arquivo**: `nfe_search.py`  
**Linha**: 630-663  
**Descrição**: Função principal que detecta automaticamente o tipo de documento (NF-e ou CT-e) e chama a função específica de extração.

**Assinatura**:
```python
def extrair_nota_detalhada(
    xml_txt: str, 
    parser: XMLProcessor, 
    db: DatabaseManager, 
    chave: str, 
    informante: Optional[str] = None, 
    nsu_documento: Optional[str] = None
) -> dict
```

**Parâmetros**:
- `xml_txt`: String contendo XML completo do documento
- `parser`: Instância de `XMLProcessor` para parsing
- `db`: Instância de `DatabaseManager` para consultas
- `chave`: Chave de acesso (44 dígitos)
- `informante`: CNPJ/CPF do certificado (opcional)
- `nsu_documento`: NSU do documento - **OBRIGATÓRIO para rastreamento** (15 dígitos)

**Retorno**: Dicionário com 40+ campos do documento:
```python
{
    'chave': str,           # Chave de acesso (44 dígitos)
    'numero': str,          # Número da nota
    'cnpj_emitente': str,   # CNPJ do emitente
    'nome_emitente': str,   # Razão social
    'cnpj_destinatario': str,
    'nome_destinatario': str,
    'valor': float,         # Valor total
    'data_emissao': str,    # Data ISO format
    'tipo': str,            # 'NFe' ou 'CTe'
    'nsu': str,             # NSU (15 dígitos)
    'status': str,          # Status da nota
    # ... mais 30+ campos
}
```

**Validação Crítica**:
```python
if not nsu_documento:
    logger.error(f"🚨 CRÍTICO: extrair_nota_detalhada chamado SEM NSU para chave {chave}")
    logger.error(f"   Documento será salvo mas NSU ficará vazio, impedindo rastreamento!")
```

**Fluxo**:
1. Detecta tipo via `detectar_tipo_documento(xml_txt)`
2. Se CT-e → chama `extrair_cte_detalhado()`
3. Se NF-e → chama `extrair_nfe_detalhado()`
4. Retorna dicionário padronizado

---

### `extrair_nfe_detalhado()`
**Arquivo**: `nfe_search.py`  
**Linha**: 667-747  
**Descrição**: Extrai informações detalhadas de uma NF-e (Nota Fiscal Eletrônica modelo 55).

**Assinatura**:
```python
def extrair_nfe_detalhado(
    xml_txt: str, 
    parser: XMLProcessor, 
    db: DatabaseManager, 
    chave: str, 
    informante: Optional[str] = None, 
    nsu_documento: Optional[str] = None
) -> dict
```

**Campos Extraídos**:

#### Identificação
- `chave`: ID única da NF-e (44 dígitos)
- `numero`: Número da nota fiscal
- `serie`: Série da nota
- `modelo`: Sempre "55" para NF-e

#### Emitente
- `cnpj_emitente`: CNPJ de quem emitiu
- `nome_emitente`: Razão social do emitente

#### Destinatário
- `cnpj_destinatario`: CNPJ de quem recebeu
- `nome_destinatario`: Razão social do destinatário

#### Valores
- `valor`: Valor total da nota (float)
- `base_icms`: Base de cálculo ICMS
- `valor_icms`: Valor do ICMS

#### Tributação
- `cfop`: Código Fiscal de Operação
- `ncm`: Nomenclatura Comum do Mercosul
- `uf`: UF do emitente

#### Operacional
- `data_emissao`: Data/hora de emissão (ISO format)
- `natureza`: Natureza da operação
- `vencimento`: Data de vencimento (se aplicável)
- `nsu`: NSU do documento (15 dígitos)
- `informante`: CNPJ/CPF do certificado

#### Controle
- `tipo`: Sempre "NFe"
- `status`: Status atual da nota
- `atualizado_em`: Timestamp da última atualização

**Namespaces XML**:
```python
NS = {
    'nfe': 'http://www.portalfiscal.inf.br/nfe'
}
```

**XPath Principais**:
```python
tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
tree.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
tree.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
tree.find('.//{http://www.portalfiscal.inf.br/nfe}dest')
tree.find('.//{http://www.portalfiscal.inf.br/nfe}total')
```

---

### `extrair_cte_detalhado()`
**Arquivo**: `nfe_search.py`  
**Linha**: 468-628  
**Descrição**: Extrai informações detalhadas de um CT-e (Conhecimento de Transporte modelo 57).

**Assinatura**:
```python
def extrair_cte_detalhado(
    xml_txt: str, 
    parser: XMLProcessor, 
    db: DatabaseManager, 
    chave: str, 
    informante: Optional[str] = None, 
    nsu_documento: Optional[str] = None
) -> dict
```

**Campos Específicos de CT-e**:

#### Identificação  
- `modelo`: Sempre "57" para CT-e
- `tipo_servico`: Tipo do serviço de transporte

#### Remetente
- `cnpj_remetente`: CNPJ de quem enviou a carga
- `nome_remetente`: Razão social do remetente

#### Destinatário
- `cnpj_destinatario`: CNPJ de quem receberá
- `nome_destinatario`: Razão social

#### Carga
- `peso_bruto`: Peso bruto em KG
- `peso_liquido`: Peso líquido em KG (se disponível)
- `quantidade_volumes`: Número de volumes transportados
- `natureza_carga`: Descrição da natureza da carga

#### Valores
- `valor`: Valor total da prestação do serviço
- `valor_carga`: Valor da mercadoria transportada

#### Trajeto
- `uf_inicio`: UF de origem
- `uf_fim`: UF de destino
- `cidade_inicio`: Município de origem
- `cidade_fim`: Município de destino

**Namespaces XML**:
```python
NS = {
    'cte': 'http://www.portalfiscal.inf.br/cte'
}
```

**XPath Principais**:
```python
tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
tree.find('.//{http://www.portalfiscal.inf.br/cte}ide')
tree.find('.//{http://www.portalfiscal.inf.br/cte}rem')
tree.find('.//{http://www.portalfiscal.inf.br/cte}infCarga')
```

---

### `extrair_chave_nfe()`
**Arquivo**: `nfe_search.py`  
**Linha**: 450-465  
**Descrição**: Extrai a chave de acesso de 44 dígitos do XML (funciona para NF-e e CT-e).

**Assinatura**:
```python
def extrair_chave_nfe(xml_txt: str) -> Optional[str]
```

**Retorno**: String de 44 dígitos ou None

**Estratégia**:
1. Tenta extrair de `<infNFe Id="NFe44dígitos">`
2. Se falhar, tenta `<infCte Id="CTe44dígitos">`
3. Remove prefixo "NFe" ou "CTe" e pega últimos 44 caracteres

**Exemplo**:
```python
xml = '<infNFe Id="NFe35210133251845000109550010001234561009581385">'
chave = extrair_chave_nfe(xml)
# Retorna: "35210133251845000109550010001234561009581385"
```

---

### `detectar_tipo_documento()`
**Arquivo**: `nfe_search.py`  
**Linha**: 419-448  
**Descrição**: Detecta automaticamente se XML é NF-e, CT-e, NFS-e ou Evento.

**Assinatura**:
```python
def detectar_tipo_documento(xml_txt: str) -> str
```

**Retorno**: Uma das strings:
- `"NFe"` - Nota Fiscal Eletrônica
- `"CTe"` - Conhecimento de Transporte
- `"NFSe"` - Nota Fiscal de Serviço
- `"Evento"` - Carta de correção, cancelamento, etc.
- `"Desconhecido"` - Tipo não identificado

**Lógica de Detecção**:
```python
xml_lower = xml_txt.lower()

if 'nfeproc' in xml_lower or '<nfe' in xml_lower:
    return 'NFe'
elif 'cteproc' in xml_lower or '<cte' in xml_lower:
    return 'CTe'
elif 'rps' in xml_lower or 'nfse' in xml_lower:
    return 'NFSe'
elif 'procev' in xml_lower or 'evento' in xml_lower:
    return 'Evento'
else:
    return 'Desconhecido'
```

**Uso**:
```python
xml = """<?xml version="1.0"?>
<nfeProc versao="4.00">...</nfeProc>"""

tipo = detectar_tipo_documento(xml)
# Retorna: "NFe"
```

---

### `processar_evento_status()`
**Arquivo**: `nfe_search.py`  
**Linha**: 344-415  
**Descrição**: Processa eventos (cancelamento, carta de correção) e atualiza o status da nota original no banco.

**Assinatura**:
```python
def processar_evento_status(
    xml_txt: str, 
    chave_evento: str, 
    db: DatabaseManager
) -> None
```

**Tipos de Evento Reconhecidos**:
```python
EVENTOS = {
    '110110': 'Carta de Correção',
    '110111': 'Cancelamento',
    '110112': 'Cancelamento por Substituição',
    '110140': 'EPEC',
    '210200': 'Confirmação da Operação',
    '210210': 'Ciência da Operação',
    '210220': 'Desconhecimento da Operação',
    '210240': 'Operação não Realizada'
}
```

**Fluxo**:
1. Extrai `tpEvento` e `chNFe` do XML do evento
2. Mapeia código para descrição legível
3. Atualiza campo `status` da nota no banco
4. Se evento de cancelamento (110111):
   ```python
   db.update_nota_status(chave_nfe, "CANCELADA - " + data_evento)
   ```

**Exemplo de XML Evento**:
```xml
<procEventoNFe>
  <evento>
    <infEvento>
      <tpEvento>110111</tpEvento>
      <chNFe>35210133251845000109550010001234561009581385</chNFe>
      <dhEvento>2021-02-15T10:30:00-03:00</dhEvento>
      <xJust>Duplicidade na emissão</xJust>
    </infEvento>
  </evento>
</procEventoNFe>
```

---

<a name="funcoes-comunicacao"></a>
## 2️⃣ Funções de Comunicação SEFAZ

### `NFeService.__init__()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3138-3196  
**Descrição**: Inicializa cliente SOAP para comunicação com SEFAZ (Distribuição DFe).

**Assinatura**:
```python
class NFeService:
    def __init__(self, cert_path: str, senha: str, informante: str, cuf: int):
```

**Parâmetros**:
- `cert_path`: Caminho completo para arquivo .pfx do certificado A1
- `senha`: Senha do certificado
- `informante`: CNPJ ou CPF do titular
- `cuf`: Código UF de autorização (ex: 50 = Mato Grosso do Sul)

**Configuração**:
```python
# URL do serviço de distribuição (PRODUÇÃO)
URL_DISTRIBUICAO = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl"

# Configura cliente Zeep com autenticação mTLS
self.dist_client = Client(
    URL_DISTRIBUICAO,
    transport=Transport(session=session)
)
```

**Sessão HTTPS com Certificado**:
```python
session = Session()
session.cert = (cert_path, senha)  # Autenticação mútua TLS
session.verify = True               # Valida certificado do servidor
```

---

### `NFeService.fetch_by_cnpj()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3280-3360  
**Descrição**: Busca documentos via Distribuição DFe usando NSU sequencial.

**Assinatura**:
```python
def fetch_by_cnpj(self, tipo: str, ult_nsu: str) -> Optional[str]
```

**Parâmetros**:
- `tipo`: "CNPJ" ou "CPF" (define qual tag usar no XML)
- `ult_nsu`: Último NSU processado (15 dígitos, ex: "000000000000000")

**XML de Requisição**:
```xml
<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
    <tpAmb>1</tpAmb>
    <cUFAutor>50</cUFAutor>
    <CNPJ>33251845000109</CNPJ>
    <distNSU>
        <ultNSU>000000000123456</ultNSU>
    </distNSU>
</distDFeInt>
```

**Retorno**: String XML da resposta completa ou None

**Validação XSD**:
```python
validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
```

**Resposta Típica**:
```xml
<retDistDFeInt>
    <tpAmb>1</tpAmb>
    <cStat>138</cStat>
    <xMotivo>Documento localizado</xMotivo>
    <dhResp>2024-01-15T14:30:00-03:00</dhResp>
    <ultNSU>000000000123460</ultNSU>
    <maxNSU>000000005678900</maxNSU>
    <loteDistDFeInt>
        <docZip NSU="000000000123457" schema="procNFe_v4.00.xsd">
            H4sIAAAAAAAA...  <!-- Base64 + gzip -->
        </docZip>
        <docZip NSU="000000000123458" schema="procCTe_v4.00.xsd">
            H4sIAAAAAAAA...
        </docZip>
    </loteDistDFeInt>
</retDistDFeInt>
```

**cStat Possíveis**:
- `138`: Documento localizado (sucesso)
- `137`: Nenhum documento localizado
- `656`: Consumo indevido (bloqueio temporário)
- `656`: Rejeição por NSU fora de ordem

---

### `NFeService.fetch_by_chave_dist()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3202-3278  
**Descrição**: Busca documento específico via Distribuição DFe usando chave de acesso (disponibilidade: ~1000 dias).

**Assinatura**:
```python
def fetch_by_chave_dist(self, chave: str) -> Optional[str]
```

**Vantagens**:
- ✅ Disponibilidade maior que `ConsultaProtocolo` (1000+ dias vs 180 dias)
- ✅ Retorna XML completo quando disponível
- ✅ Funciona para NF-e recebidas e emitidas (se manifestadas)

**XML de Requisição**:
```xml
<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
    <tpAmb>1</tpAmb>
    <cUFAutor>50</cUFAutor>
    <CNPJ>33251845000109</CNPJ>
    <consChNFe>
        <chNFe>35210133251845000109550010001234561009581385</chNFe>
    </consChNFe>
</distDFeInt>
```

**Diferença para fetch_by_cnpj**:
- `fetch_by_cnpj`: Usa `<distNSU>` → busca sequencial
- `fetch_by_chave_dist`: Usa `<consChNFe>` → busca direta

**Retorno**: XML completo da resposta ou None

---

### `NFeService.fetch_prot_nfe()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3362-3440  
**Descrição**: Consulta protocolo de autorização de NF-e pela chave (serviço ConsultaProtocolo).

**Assinatura**:
```python
def fetch_prot_nfe(self, chave: str) -> Optional[str]
```

**⚠️ LIMITAÇÃO CRÍTICA**:
- Para NF-e **EMITIDAS** pela empresa: Retorna apenas PROTOCOLO (não o XML completo)
- Para NF-e **RECEBIDAS**: Pode retornar XML completo via Distribuição
- Disponibilidade: ~180 dias

**XML de Requisição**:
```xml
<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
    <tpAmb>1</tpAmb>
    <xServ>CONSULTAR</xServ>
    <chNFe>35210133251845000109550010001234561009581385</chNFe>
</consSitNFe>
```

**URLs por UF** (exemplos):
```python
URL_CONSULTA_UF = {
    '50': "https://nfe.fazenda.ms.gov.br/ws/NFeConsultaProtocolo4",
    '35': "https://nfe.fazenda.sp.gov.br/ws/nfeconsulta4.asmx",
    '43': "https://nfe.sefaz.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx"
}
```

**Resposta Protocolo-Only** (NF-e emitida):
```xml
<retConsSitNFe>
    <tpAmb>1</tpAmb>
    <cStat>100</cStat>
    <xMotivo>Autorizado o uso da NF-e</xMotivo>
    <chNFe>35210133251845000109550010001234561009581385</chNFe>
    <protNFe>
        <infProt>
            <tpAmb>1</tpAmb>
            <dhRecbto>2021-02-15T10:30:00-03:00</dhRecbto>
            <nProt>350210000123456</nProt>
            <chNFe>35210133251845000109550010001234561009581385</chNFe>
            <cStat>100</cStat>
            <xMotivo>Autorizado</xMotivo>
        </infProt>
    </protNFe>
</retConsSitNFe>
```

**🔍 Detecção de Protocolo-Only** em `salvar_xml_por_certificado()` (linha 955-966):
```python
is_only_protocol = (
    '<retconssit' in xml_lower and 
    '<protnfe' in xml_lower and
    '<nfeproc' not in xml_lower and
    '<nfe' not in xml_lower
)

if is_only_protocol:
    logger.warning("XML contém apenas protocolo, não será salvo")
    return None  # Bloqueia salvamento
```

---

### `NFeService.fetch_prot_cte()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3442-3520  
**Descrição**: Consulta protocolo de autorização de CT-e pela chave.

**Assinatura**:
```python
def fetch_prot_cte(self, chave: str) -> Optional[str]
```

**URL**:
```python
URL_CONSULTA_CTE = "https://cte.svrs.rs.gov.br/ws/cteconsulta/CteConsulta4.asmx?wsdl"
```

**XML de Requisição**:
```xml
<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00">
    <tpAmb>1</tpAmb>
    <xServ>CONSULTAR</xServ>
    <chCTe>50251203232675000154570010056290311009581385</chCTe>
</consSitCTe>
```

**Namespaces CT-e**:
```python
NS_CTE = 'http://www.portalfiscal.inf.br/cte'
```

**Validação**:
```python
# Valida com XSD específico de CT-e
validar_xml_auto(xml_envio, 'consSitCTe_v4.00.xsd')
```

---

### `consultar_nfe_por_chave()`
**Arquivo**: `nfe_search.py`  
**Linha**: 4396-4438  
**Descrição**: Função helper standalone para consultar XML completo de NF-e pela chave.

**Assinatura**:
```python
def consultar_nfe_por_chave(
    chave: str, 
    certificado_path: str, 
    senha: str, 
    cnpj: str, 
    cuf: int
) -> Optional[str]
```

**Uso Prático**:
```python
xml = consultar_nfe_por_chave(
    chave="35210133251845000109550010001234561009581385",
    certificado_path="C:\\certificados\\empresa.pfx",
    senha="senha123",
    cnpj="33251845000109",
    cuf=50
)

if xml:
    print("XML completo obtido!")
    # Processar com extrair_nota_detalhada()
else:
    print("NF-e não encontrada ou apenas protocolo disponível")
```

**Verificações**:
```python
# 1. Verifica se certificado existe
from pathlib import Path
cert_file = Path(certificado_path)
if not cert_file.exists():
    return None

# 2. Chama NFeService
svc = NFeService(certificado_path, senha, cnpj, cuf)
prot_xml = svc.fetch_prot_nfe(chave)

# 3. Valida resposta
if '<protNFe' in prot_xml or '<retConsSitNFe' in prot_xml:
    return prot_xml
```

---

<a name="funcoes-processamento"></a>
## 3️⃣ Funções de Processamento

### `processar_cte()`
**Arquivo**: `nfe_search.py`  
**Linha**: 3688-3896  
**Descrição**: Processa CT-e para um certificado específico usando o serviço CTeDistribuicaoDFe.

**Assinatura**:
```python
def processar_cte(db: DatabaseManager, cert_data: tuple) -> None
```

**Parâmetros**:
- `db`: Instância do DatabaseManager
- `cert_data`: Tupla `(cnpj, path, senha, informante, cuf)`

**Fluxo Completo**:
```
1. Inicializa CTeService com certificado
2. Obtém último NSU CT-e processado (get_last_nsu_cte)
3. Se NSU=0, consulta para descobrir maxNSU disponível
4. Loop incremental:
   ├─ Busca documentos (fetch_by_cnpj)
   ├─ Extrai cStat da resposta
   ├─ Se cStat=656 (bloqueio): Para sem atualizar NSU
   ├─ Se cStat=137 (sem documentos): Registra e termina
   ├─ Se cStat=138 (sucesso):
   │  ├─ Extrai documentos compactados (gzip + base64)
   │  ├─ Para cada CT-e:
   │  │  ├─ Detecta tipo (procCTe, resCTe, evento)
   │  │  ├─ Extrai chave de acesso
   │  │  ├─ Verifica se já existe no banco
   │  │  ├─ Extrai dados detalhados (extrair_cte_detalhado)
   │  │  ├─ Salva no banco (salvar_nota_detalhada)
   │  │  ├─ Salva XML em arquivo (salvar_xml_por_certificado)
   │  │  └─ Mapeia CNPJ para nome de certificado
   │  ├─ Atualiza último NSU processado
   │  └─ Se ultNSU == maxNSU: Termina
   └─ Limite de segurança: 100 iterações
5. Registra estatísticas finais
```

**Estrutura CT-e**:
```python
from modules.cte_service import CTeService

cte_svc = CTeService(path, senha, cnpj, cuf, ambiente='producao')
```

**Extração de Documentos**:
```python
for nsu, xml_cte, schema in cte_svc.extrair_documentos(resp_cte):
    # nsu: "000000000123456"
    # xml_cte: XML completo descompactado
    # schema: "procCTe_v4.00.xsd"
    
    chave = extrair_chave_cte(xml_cte)
    dados_cte = extrair_cte_detalhado(xml_cte, parser, db, chave, informante, nsu)
    db.salvar_nota_detalhada(dados_cte)
```

**Mapeamento CNPJ → Nome**:
```python
# Padronização: sempre usa NOME do certificado na pasta
nome_cert = db.get_cert_nome_by_informante(informante)
# Exemplo: "ALFA COMPUTADORES" em vez de "03232675000154"

salvar_xml_por_certificado(
    xml=xml_cte,
    cnpj_cpf=informante,
    pasta_base="xmls",
    nome_certificado=nome_cert
)
```

**Tratamento de Erros**:
```python
if cStat_cte == '656':
    logger.warning(f"🔒 CT-e: Erro 656 - Consumo indevido")
    logger.warning(f"   ⚠️ IMPORTANTE: NSU NÃO será atualizado")
    logger.info(f"   ⏰ Bloqueio - aguarde 65 minutos")
    break  # Mantém NSU atual para retomar depois
```

---

### `processar_nfse()`
**Arquivo**: `nfe_search.py`  
**Linha**: 4085-4320  
**Descrição**: Processa NFS-e (Nota Fiscal de Serviço Eletrônica) para um certificado.

**Assinatura**:
```python
def processar_nfse(cert_data: tuple, db: DatabaseManager) -> None
```

**Características NFS-e**:
- Competência municipal (cada cidade tem seu provedor)
- Diferentes provedores: GINFES, Betha, ISSNet, etc.
- Estrutura XML diferente de NF-e/CT-e
- Sem NSU federal (usa controles municipais)

**Fluxo**:
```python
from modules.nfse_service import NFSeService

cnpj, path, senha, inf, cuf = cert_data
nfse_svc = NFSeService(path, senha, cnpj, ambiente='producao')

# Busca última competência processada
ultima_competencia = db.get_ultima_competencia_nfse(inf)

# Loop por competências (ex: "202401", "202402", ...)
for competencia in range(ultima_competencia, competencia_atual + 1):
    resp = nfse_svc.consultar_por_competencia(competencia)
    
    for xml_nfse in nfse_svc.extrair_documentos(resp):
        dados_nfse = extrair_nfse_detalhada(xml_nfse, inf)
        db.salvar_nota_detalhada(dados_nfse)
```

---

### `run_single_cycle()`
**Arquivo**: `nfe_search.py`  
**Linha**: 4440-4550  
**Descrição**: Executa UMA iteração completa de busca (NF-e, CT-e e NFS-e) para todos os certificados.

**Assinatura**:
```python
def run_single_cycle() -> None
```

**Uso**: Chamado pela interface gráfica quando usuário clica "Buscar Agora" ou pelo scheduler automático.

**Fluxo Completo**:
```
1. Inicializa DatabaseManager
2. Para cada certificado cadastrado:
   ├─ Processa NF-e (via NFeService)
   ├─ Processa CT-e (via processar_cte)
   └─ Processa NFS-e (via processar_nfse)
3. Gera relatório final:
   ├─ Total de documentos baixados
   ├─ NSU inicial e final
   └─ Duração da execução
```

**Exemplo de Saída**:
```
=== Início da busca: 2024-01-15T14:30:00 ===
📥 Fase 1: Buscando documentos (NFe, CT-e e NFS-e)...
  📄 Certificado: ALFA COMPUTADORES (03232675000154)
    ✅ NF-e: 15 novos documentos (NSU 123456 → 123471)
    ✅ CT-e: 3 novos documentos (NSU 654321 → 654324)
    ✅ NFS-e: 0 novos documentos
  📄 Certificado: EMPRESA TESTE (33251845000109)
    ✅ NF-e: 0 novos documentos
    ✅ CT-e: 0 novos documentos
=== Fim da busca: 2024-01-15T14:35:23 ===
⏱️ Duração: 5min 23s
📊 Total: 18 documentos baixados
```

---

<a name="funcoes-armazenamento"></a>
## 4️⃣ Funções de Armazenamento

### `salvar_xml_por_certificado()`
**Arquivo**: `nfe_search.py`  
**Linha**: 811-1050  
**Descrição**: Salva XML em múltiplos perfis de armazenamento simultaneamente com suporte a diferentes hierarquias de pastas.

**Assinatura**:
```python
def salvar_xml_por_certificado(
    xml: str, 
    cnpj_cpf: str, 
    pasta_base: str = "xmls", 
    nome_certificado: Optional[str] = None, 
    formato_mes: Optional[str] = None
) -> Optional[str]
```

**Parâmetros**:
- `xml`: String contendo XML completo
- `cnpj_cpf`: CNPJ/CPF do certificado (informante)
- `pasta_base`: Pasta base para salvamento (pode ser ignorada se usar perfis)
- `nome_certificado`: Nome legível do certificado (ex: "ALFA COMPUTADORES")
- `formato_mes`: Formato de pasta mensal: "YYYY-MM", "MM-YYYY", "MMYYYY", "YYYYMM"

**Perfis de Armazenamento**:

#### Perfil 1: CERTIFICADO_TIPO (Default)
```
C:\Arquivo Walter - Empresas\Notas\NFs\
├─ ALFA COMPUTADORES\
│  ├─ 012026\
│  │  ├─ NFe\
│  │  │  ├─ 35210133251845000109550010001234561009581385.xml
│  │  │  └─ ...
│  │  ├─ PDFs NFe\
│  │  │  ├─ 35210133251845000109550010001234561009581385.pdf
│  │  │  └─ ...
│  │  ├─ CTe\
│  │  └─ PDFs CTe\
│  └─ 022026\
│     ├─ NFe\
│     └─ ...
└─ EMPRESA TESTE\
   └─ ...
```

**Estrutura**:
- Nível 1: Nome do certificado
- Nível 2: Mês/Ano (012026 = Janeiro 2026)
- Nível 3: Tipo de documento (NFe, CTe, NFSe)
- Nível 4: "PDFs NFe", "PDFs CTe" para PDFs

#### Perfil 2: TIPO_CERTIFICADO (Importação Domínio)
```
C:\Arquivo Walter - Empresas\Notas\DominioWeb\
├─ NFe\
│  ├─ ALFA COMPUTADORES\
│  │  └─ 012026\
│  │     ├─ 35210133251845000109550010001234561009581385.xml
│  │     ├─ 35210133251845000109550010001234561009581385.pdf
│  │     └─ ...
│  └─ EMPRESA TESTE\
│     └─ ...
├─ CTe\
│  ├─ ALFA COMPUTADORES\
│  └─ ...
└─ NFSe\
   └─ ...
```

**Estrutura**:
- Nível 1: Tipo de documento (NFe, CTe, NFSe)
- Nível 2: Nome do certificado
- Nível 3: Mês/Ano
- XMLs e PDFs juntos na mesma pasta

**⚠️ Importante**: Modo TIPO_CERTIFICADO **ignora eventos intencionalmente** (linhas 17497-17504 de Busca NF-e.py):
```python
if organizacao_tipo == 'TIPO_CERTIFICADO':
    nome_arquivo = arquivo_xml.name.upper()
    if any(palavra in nome_arquivo for palavra in ['EVENTO', 'CANCELAMENTO', 'CARTA', 'CORRECAO', 'CCE']):
        print(f"[IGNORADO] Evento não copiado no modo TIPO_CERTIFICADO")
        continue
```

**Validação de Protocolo** (linha 955-966):
```python
xml_lower = xml.lower()
is_only_protocol = (
    '<retconssit' in xml_lower and 
    '<protnfe' in xml_lower and
    '<nfeproc' not in xml_lower and
    '<nfe' not in xml_lower.replace('nferesultmsg', '').replace('protnfe', '')
)

if is_only_protocol:
    logger.warning("XML contém apenas protocolo, não será salvo")
    return None  # Bloqueia salvamento de protocolo vazio
```

**Multi-perfil Automático**:
```python
# Busca perfis ativos no banco
perfis_ativos = db.get_perfis_ativos()

for perfil in perfis_ativos:
    nome = perfil['nome']
    pasta_base = perfil['pasta_base']
    organizacao = perfil['organizacao_tipo']  # CERTIFICADO_TIPO ou TIPO_CERTIFICADO
    formato = perfil['formato_pasta_mes']     # YYYY-MM, MM-YYYY, etc.
    
    # Constrói caminho específico do perfil
    caminho_final = construir_caminho_perfil(
        pasta_base, organizacao, nome_cert, data_emissao, tipo_doc, formato
    )
    
    # Salva XML
    with open(caminho_final / f"{chave}.xml", "w", encoding="utf-8") as f:
        f.write(xml)
    
    logger.info(f"✅ XML salvo em perfil '{nome}': {caminho_final}")
```

**Formatação de Pasta Mensal**:
```python
def formatar_mes(data_emissao: str, formato: str) -> str:
    """
    Formata pasta de mês conforme configuração.
    
    Args:
        data_emissao: "2026-01-15" (ISO format)
        formato: "YYYY-MM", "MM-YYYY", "MMYYYY", "YYYYMM"
    
    Returns:
        String formatada: "012026", "01-2026", "2026-01", "202601"
    """
    ano = data_emissao[:4]
    mes = data_emissao[5:7]
    
    formatos = {
        'YYYY-MM': f"{ano}-{mes}",
        'MM-YYYY': f"{mes}-{ano}",
        'MMYYYY': f"{mes}{ano}",
        'YYYYMM': f"{ano}{mes}"
    }
    
    return formatos.get(formato, f"{mes}{ano}")  # Default: MMYYYY
```

**Sanitização de Nomes**:
```python
def sanitize_filename(s: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos/pastas."""
    # Remove: \ / : * ? " < > |
    invalidos = r'[\\/:*?"<>|]'
    return re.sub(invalidos, '_', s)

# Exemplo:
sanitize_filename("ALFA COMPUTADORES S/A")
# Retorna: "ALFA COMPUTADORES S_A"
```

---

### `save_debug_soap()`
**Arquivo**: `nfe_search.py`  
**Linha**: 38-55  
**Descrição**: Salva XMLs de debug SOAP (request/response) para troubleshooting.

**Assinatura**:
```python
def save_debug_soap(
    informante: str, 
    tipo: str, 
    conteudo: str, 
    prefixo: str = ""
) -> None
```

**Parâmetros**:
- `informante`: CNPJ/CPF do certificado
- `tipo`: "request", "response" ou "fault"
- `conteudo`: XML ou mensagem de erro
- `prefixo`: Prefixo do arquivo (ex: "nfe_dist", "cte_consulta")

**Estrutura de Pastas**:
```
debug_soap/
├─ 03232675000154/
│  ├─ nfe_dist_request_20260115_143025.xml
│  ├─ nfe_dist_response_20260115_143026.xml
│  ├─ nfe_dist_chave_request_20260115_143530.xml
│  └─ cte_consulta_fault_20260115_144512.xml
└─ 33251845000109/
   └─ ...
```

**Uso**:
```python
# Antes de enviar
xml_request = etree.tostring(distInt, encoding='utf-8').decode()
save_debug_soap(self.informante, "request", xml_request, prefixo="nfe_dist")

try:
    resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
    xml_response = etree.tostring(resp, encoding='utf-8').decode()
    save_debug_soap(self.informante, "response", xml_response, prefixo="nfe_dist")
except Fault as fault:
    save_debug_soap(self.informante, "fault", str(fault), prefixo="nfe_dist")
```

---

<a name="funcoes-banco"></a>
## 5️⃣ Funções de Banco de Dados (DatabaseManager)

### `DatabaseManager.__init__()`
**Arquivo**: `nfe_search.py`  
**Linha**: 1500-1700  
**Descrição**: Inicializa conexão com banco SQLite e cria estrutura de tabelas.

**Assinatura**:
```python
class DatabaseManager:
    def __init__(self, db_path: Path):
```

**Tabelas Criadas**:
1. **notas_detalhadas**: 36 colunas (chave, numero, valores, etc.)
2. **certificados**: Registro de certificados A1
3. **nsu**: Controle de NSU por informante
4. **xmls_baixados**: Registro de XMLs salvos
5. **perfis_armazenamento**: Configuração multi-perfil
6. **nf_status**: Status de NF-e consultadas
7. **config**: Configurações gerais
8. **notas_verificadas**: Controle de verificação

**Índices Criados**:
```sql
CREATE INDEX IF NOT EXISTS idx_cnpj_emitente ON notas_detalhadas(cnpj_emitente)
CREATE INDEX IF NOT EXISTS idx_cnpj_destinatario ON notas_detalhadas(cnpj_destinatario)
CREATE INDEX IF NOT EXISTS idx_data_emissao ON notas_detalhadas(data_emissao)
CREATE INDEX IF NOT EXISTS idx_informante ON notas_detalhadas(informante)
CREATE INDEX IF NOT EXISTS idx_tipo ON notas_detalhadas(tipo)
CREATE INDEX IF NOT EXISTS idx_nsu ON notas_detalhadas(nsu)
```

---

### `DatabaseManager.salvar_nota_detalhada()`
**Arquivo**: `nfe_search.py`  
**Linha**: 1850-1950  
**Descrição**: Salva nota completa no banco (INSERT OR REPLACE).

**Assinatura**:
```python
def salvar_nota_detalhada(self, nota: dict) -> bool
```

**Campos Obrigatórios**:
```python
CAMPOS_OBRIGATORIOS = [
    'chave',              # PRIMARY KEY
    'numero',
    'cnpj_emitente',
    'nome_emitente',
    'cnpj_destinatario',
    'nome_destinatario',
    'valor',
    'data_emissao',
    'tipo',
    'nsu',               # CRÍTICO para rastreamento
    'informante'
]
```

**SQL**:
```sql
INSERT OR REPLACE INTO notas_detalhadas (
    chave, numero, serie, modelo,
    cnpj_emitente, nome_emitente,
    cnpj_destinatario, nome_destinatario,
    valor, data_emissao, tipo, cfop, ncm, uf,
    natureza, base_icms, valor_icms, vencimento,
    nsu, informante, status, atualizado_em
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**Validação**:
```python
if not nota.get('chave'):
    logger.error("Tentativa de salvar nota sem chave")
    return False

if not nota.get('nsu'):
    logger.warning(f"⚠️ Nota {nota['chave']} sem NSU - rastreamento comprometido")
```

---

### `DatabaseManager.get_certificados()`
**Arquivo**: `nfe_search.py`  
**Linha**: 1750-1820  
**Descrição**: Retorna lista de certificados com senhas descriptografadas.

**Assinatura**:
```python
def get_certificados(self) -> List[tuple]
```

**Retorno**: Lista de tuplas:
```python
[
    (cnpj, caminho, senha, informante, cuf),
    ("03232675000154", "C:\\certs\\alfa.pfx", "senha123", "03232675000154", 50),
    ("33251845000109", "C:\\certs\\empresa.pfx", "senha456", "33251845000109", 35),
    ...
]
```

**SQL**:
```sql
SELECT cnpj_cpf, caminho, senha_encrypted, informante, cUF_autor
FROM certificados
WHERE ativo = 1
ORDER BY nome_certificado
```

**Descriptografia de Senha**:
```python
from cryptography.fernet import Fernet

def descriptografar_senha(senha_encrypted: str) -> str:
    """Descriptografa senha do certificado usando Fernet."""
    cipher = Fernet(CHAVE_CRIPTOGRAFIA)
    senha_bytes = cipher.decrypt(senha_encrypted.encode())
    return senha_bytes.decode()
```

---

### `DatabaseManager.get_last_nsu()`
**Arquivo**: `nfe_search.py`  
**Linha**: 2050-2080  
**Descrição**: Obtém último NSU processado para um certificado (NF-e).

**Assinatura**:
```python
def get_last_nsu(self, informante: str) -> str
```

**Retorno**: String de 15 dígitos (ex: "000000000123456")

**SQL**:
```sql
SELECT ultimo_nsu
FROM nsu
WHERE informante = ?
```

**Comportamento**:
- Se não existe registro: retorna "000000000000000" (zero)
- Se existe: retorna último NSU salvo

**Uso**:
```python
db = DatabaseManager("notas.db")
ultimo_nsu = db.get_last_nsu("03232675000154")
# Retorna: "000000000123456"

# Usa na próxima consulta
proximo_nsu = str(int(ultimo_nsu) + 1).zfill(15)
# Retorna: "000000000123457"
```

---

### `DatabaseManager.set_last_nsu()`
**Arquivo**: `nfe_search.py`  
**Linha**: 2082-2120  
**Descrição**: Atualiza último NSU processado (NF-e).

**Assinatura**:
```python
def set_last_nsu(self, informante: str, nsu: str) -> None
```

**Validações**:
```python
# 1. NSU deve ter 15 dígitos
if len(nsu) != 15:
    logger.error(f"NSU inválido (deve ter 15 dígitos): {nsu}")
    return

# 2. NSU deve ser numérico
if not nsu.isdigit():
    logger.error(f"NSU inválido (deve ser numérico): {nsu}")
    return

# 3. NSU não pode ser menor que o último salvo
ultimo_nsu = self.get_last_nsu(informante)
if int(nsu) < int(ultimo_nsu):
    logger.warning(f"NSU {nsu} menor que último salvo {ultimo_nsu} - ignorando")
    return
```

**SQL**:
```sql
INSERT OR REPLACE INTO nsu (informante, ultimo_nsu, atualizado_em)
VALUES (?, ?, datetime('now'))
```

**Uso**:
```python
# Após processar lote de documentos
db.set_last_nsu("03232675000154", "000000000123470")
logger.info(f"✅ NSU atualizado para 000000000123470")
```

---

### `DatabaseManager.get_last_nsu_cte()`
**Arquivo**: `nfe_search.py`  
**Linha**: 2122-2150  
**Descrição**: Obtém último NSU processado para CT-e (separado de NF-e).

**Assinatura**:
```python
def get_last_nsu_cte(self, informante: str) -> str
```

**Diferença de NF-e**:
- NF-e e CT-e possuem **contadores NSU independentes**
- Cada certificado tem 2 NSU: um para NF-e e outro para CT-e

**SQL**:
```sql
SELECT ultimo_nsu_cte
FROM nsu
WHERE informante = ?
```

**Tabela NSU**:
```sql
CREATE TABLE nsu (
    informante TEXT PRIMARY KEY,
    ultimo_nsu TEXT DEFAULT '000000000000000',      -- NF-e
    ultimo_nsu_cte TEXT DEFAULT '000000000000000',  -- CT-e
    max_nsu_conhecido TEXT,
    atualizado_em TIMESTAMP
)
```

---

### `DatabaseManager.get_cert_nome_by_informante()`
**Arquivo**: `nfe_search.py`  
**Linha**: 2700-2730  
**Descrição**: Retorna nome legível do certificado pelo CNPJ/CPF.

**Assinatura**:
```python
def get_cert_nome_by_informante(self, informante: str) -> Optional[str]
```

**SQL**:
```sql
SELECT nome_certificado
FROM certificados
WHERE informante = ?
```

**Uso**:
```python
nome = db.get_cert_nome_by_informante("03232675000154")
# Retorna: "ALFA COMPUTADORES"

# Usa no caminho de arquivo (em vez do CNPJ)
caminho = f"xmls/{nome}/012026/NFe/"
# Resulta: "xmls/ALFA COMPUTADORES/012026/NFe/"
```

**🚨 Importante**: Sempre usar nome na estrutura de pastas (nunca CNPJ direto)

---

### `DatabaseManager.get_perfis_ativos()`
**Arquivo**: `nfe_search.py`  
**Linha**: 2950-3000  
**Descrição**: Retorna lista de perfis de armazenamento ativos.

**Assinatura**:
```python
def get_perfis_ativos(self) -> List[dict]
```

**SQL**:
```sql
SELECT *
FROM perfis_armazenamento
WHERE ativo = 1
ORDER BY nome
```

**Retorno**:
```python
[
    {
        'id': 1,
        'nome': 'Perfil 1',
        'pasta_base': 'C:\\Arquivo Walter - Empresas\\Notas\\NFs',
        'formato_pasta_mes': 'MMYYYY',
        'organizacao_tipo': 'CERTIFICADO_TIPO',
        'salvar_xml': 1,
        'salvar_pdf': 1,
        'ativo': 1
    },
    {
        'id': 2,
        'nome': 'Importação para Dominio',
        'pasta_base': 'C:\\Arquivo Walter - Empresas\\Notas\\DominioWeb',
        'formato_pasta_mes': 'MMYYYY',
        'organizacao_tipo': 'TIPO_CERTIFICADO',
        'salvar_xml': 1,
        'salvar_pdf': 1,
        'ativo': 1
    }
]
```

**Uso em salvar_xml_por_certificado()**:
```python
perfis = db.get_perfis_ativos()

for perfil in perfis:
    # Salva em cada perfil ativo
    salvar_em_perfil(xml, perfil)
```

---

<a name="funcoes-interface"></a>
## 6️⃣ Funções da Interface GUI (Busca NF-e.py)

### `MainWindow._executar_busca_por_chaves()`
**Arquivo**: `Busca NF-e.py`  
**Linha**: 8454-8700  
**Descrição**: Executa busca manual de documentos pela chave de acesso (interface "Busca por Chave").

**Assinatura**:
```python
def _executar_busca_por_chaves(self, chaves: List[str]) -> None
```

**Parâmetros**:
- `chaves`: Lista de chaves de 44 dígitos

**Fluxo**:
```
1. Cria dialog de progresso
2. Para cada chave:
   ├─ Detecta tipo (NF-e ou CT-e) pela posição 20-21
   ├─ Extrai UF da chave (2 primeiros dígitos)
   ├─ Ordena certificados por UF compatível
   ├─ Tenta cada certificado até obter sucesso:
   │  ├─ Inicializa NFeService
   │  ├─ Se CT-e: chama fetch_prot_cte()
   │  ├─ Se NF-e: chama fetch_prot_nfe()
   │  ├─ Valida resposta (cStat 100, 101, 110, 150)
   │  ├─ Extrai dados detalhados
   │  ├─ Salva no banco
   │  ├─ Salva XML em arquivo
   │  └─ Registra em xmls_baixados
   └─ Se todos certificados falharem: adiciona aos erros
3. Exibe resumo:
   ├─ X chaves encontradas
   ├─ Y chaves não encontradas
   └─ Lista de erros (se houver)
```

**Detecção de Modelo**:
```python
modelo = chave[20:22] if len(chave) >= 22 else '55'
is_cte = modelo == '57'
tipo_doc = 'CT-e' if is_cte else 'NF-e'

# Exemplos:
# 35210133251845000109550010001234561009581385
#                     ^^
#                  modelo 55 = NF-e
#
# 50251203232675000154570010056290311009581385
#                     ^^
#                  modelo 57 = CT-e
```

**Ordenação de Certificados por UF**:
```python
uf_chave = chave[:2]  # Ex: "35" (São Paulo)

# Ordena: certificados da mesma UF primeiro
ordem_certs = sorted(
    range(len(certificados)),
    key=lambda i: (
        0 if certificados[i][4] == int(uf_chave) else 1,  # UF match = prioridade
        i  # Ordem original como desempate
    )
)
```

**Validação de Resposta**:
```python
cStat_validos = ['100', '101', '110', '150']

if cStat in cStat_validos:
    logger.info(f"✅ Documento autorizado: cStat={cStat}")
    # Processa documento
else:
    logger.warning(f"❌ Documento não autorizado: cStat={cStat}, xMotivo={xMotivo}")
    # Tenta próximo certificado
```

---

### `MainWindow._baixar_xml_e_pdf()`
**Arquivo**: `Busca NF-e.py`  
**Linha**: 5223-5600  
**Descrição**: Baixa XML completo e gera PDF de um documento listado na interface principal.

**Assinatura**:
```python
def _baixar_xml_e_pdf(self, item: Dict[str, Any], silent_mode: bool = False) -> None
```

**Parâmetros**:
- `item`: Dicionário com dados da nota (da tabela)
- `silent_mode`: Se True, não exibe popups de sucesso/erro

**Fluxo Completo**:
```
1. Detecta modelo (NF-e ou CT-e)
2. Se NF-e:
   ├─ Verifica manifestações existentes
   ├─ Se não manifestado: Manifesta ciência (210210)
   └─ Aguarda 5 segundos para processamento
3. Busca XML completo:
   ├─ Método 1: Distribuição DFe por chave (fetch_by_chave_dist)
   ├─ Método 2: Consulta Protocolo (fetch_prot_nfe/cte)
   └─ Se ambos falharem: Exibe erro
4. Atualiza banco de dados:
   ├─ Se nota existe: UPDATE campos vazios
   └─ Se não existe: INSERT completo
5. Gera PDF:
   ├─ Determina pasta destino (mesmo local do XML)
   ├─ Chama serviço de geração de PDF
   └─ Salva PDF na estrutura de pastas
6. Atualiza interface:
   ├─ Recarrega linha da tabela
   └─ Exibe mensagem de sucesso
```

**Manifestação Automática** (apenas NF-e):
```python
from modules.manifestacao_service import ManifestacaoService

manif_svc = ManifestacaoService(cert_path, cert_senha, cert_cnpj, cert_cuf)

# Tipo 210210 = Ciência da Operação (obrigatório para download)
resultado = manif_svc.manifestar(
    chave=chave,
    tipo_evento='210210',
    justificativa=None  # Ciência não precisa de justificativa
)

if resultado['sucesso']:
    logger.info(f"✅ Manifestação registrada: {resultado['protocolo']}")
    time.sleep(5)  # Aguarda processamento SEFAZ
else:
    logger.error(f"❌ Erro na manifestação: {resultado['motivo']}")
```

**Métodos de Download**:
```python
# Método 1: Distribuição DFe (preferencial - disponibilidade maior)
xml_completo = svc.fetch_by_chave_dist(chave)

if not xml_completo:
    # Método 2: Consulta Protocolo (fallback)
    if is_cte:
        xml_completo = svc.fetch_prot_cte(chave)
    else:
        xml_completo = svc.fetch_prot_nfe(chave)

if not xml_completo:
    # Ambos falharam
    QMessageBox.warning(self, "Erro", "XML não disponível na SEFAZ")
    return
```

**Update Seletivo**:
```python
# Se nota já existe no banco, atualiza APENAS campos vazios
nota_existente = db.get_nota_by_chave(chave)

if nota_existente:
    # Cria dict com campos vazios
    nota_update = {
        'chave': chave
    }
    
    # Atualiza somente se campo está vazio
    if not nota_existente.get('nome_emitente'):
        nota_update['nome_emitente'] = nota_nova['nome_emitente']
    
    if not nota_existente.get('valor'):
        nota_update['valor'] = nota_nova['valor']
    
    # ... outros campos
    
    db.update_nota_parcial(nota_update)
else:
    # Nota não existe, insere completa
    db.salvar_nota_detalhada(nota_nova)
```

---

### `MainWindow._apply_profile()` (Storage Button)
**Arquivo**: `Busca NF-e.py`  
**Linha**: 17197-17600  
**Descrição**: Aplica configuração de perfil de armazenamento, copiando XMLs de backup local para destinos configurados.

**Assinatura**:
```python
def _apply_profile(
    self, 
    nome_perfil: str, 
    pasta_base: str, 
    organizacao_tipo: str, 
    formato_mes: str
) -> None
```

**Parâmetros**:
- `nome_perfil`: Nome do perfil (ex: "Perfil 1")
- `pasta_base`: Pasta destino (ex: "C:\\NFs")
- `organizacao_tipo`: "CERTIFICADO_TIPO" ou "TIPO_CERTIFICADO"
- `formato_mes`: "MMYYYY", "YYYY-MM", etc.

**Origem dos XMLs**:
```python
pasta_backup = Path("xmls_backup")
# Estrutura:
# xmls_backup/
# ├─ 03232675000154/
# │  ├─ NFe/
# │  │  ├─ 35210133251845000109550010001234561009581385.xml
# │  │  └─ ...
# │  └─ CTe/
# └─ 33251845000109/
#    └─ ...
```

**Fluxo de Cópia**:
```
1. Valida pasta_base (cria se não existir)
2. Para cada certificado em xmls_backup:
   ├─ Obtém nome legível (via get_cert_nome_by_informante)
   ├─ Para cada XML:
   │  ├─ Extrai data de emissão (3 níveis de fallback):
   │  │  ├─ Nível 1: Tags XML (dhEmi, dhRecbto)
   │  │  ├─ Nível 2: Estrutura de pastas (YYYY-MM)
   │  │  └─ Nível 3: Data atual
   │  ├─ Formata pasta mensal (conforme formato_mes)
   │  ├─ Constrói caminho destino (conforme organizacao_tipo)
   │  ├─ Se TIPO_CERTIFICADO: IGNORA eventos
   │  ├─ Copia XML
   │  └─ Copia PDF correspondente (se existir)
   └─ Atualiza contador
3. Exibe resumo: X arquivos copiados
```

**Extração de Data** (3 níveis):
```python
def extrair_data_emissao(xml_path: Path) -> str:
    """Extrai data de emissão com 3 níveis de fallback."""
    
    # Nível 1: Tags XML (mais confiável)
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_txt = f.read()
            tree = etree.fromstring(xml_txt.encode())
            
            # NF-e
            dhEmi = tree.findtext('.//{http://www.portalfiscal.inf.br/nfe}dhEmi')
            if dhEmi:
                return dhEmi[:10]  # "2021-02-15T10:30:00" → "2021-02-15"
            
            # CT-e
            dhEmi = tree.findtext('.//{http://www.portalfiscal.inf.br/cte}dhEmi')
            if dhEmi:
                return dhEmi[:10]
    except:
        pass
    
    # Nível 2: Estrutura de pastas
    # xmls_backup/03232675000154/NFe/2021-02/arquivo.xml
    #                                -------
    pasta_pai = xml_path.parent.name
    if re.match(r'\d{4}-\d{2}', pasta_pai):  # YYYY-MM
        return f"{pasta_pai}-01"  # "2021-02" → "2021-02-01"
    
    # Nível 3: Data atual (fallback final)
    return datetime.now().strftime("%Y-%m-%d")
```

**Construção de Caminho**:
```python
if organizacao_tipo == 'CERTIFICADO_TIPO':
    # Certificado/Mês/Tipo
    caminho_destino = (
        Path(pasta_base) / 
        nome_cert /           # "ALFA COMPUTADORES"
        formatar_mes(data) /  # "012026"
        tipo_doc              # "NFe"
    )
    
elif organizacao_tipo == 'TIPO_CERTIFICADO':
    # Tipo/Certificado/Mês
    caminho_destino = (
        Path(pasta_base) /
        tipo_doc /            # "NFe"
        nome_cert /           # "ALFA COMPUTADORES"
        formatar_mes(data)    # "012026"
    )
```

**Bloqueio de Eventos** (TIPO_CERTIFICADO):
```python
if organizacao_tipo == 'TIPO_CERTIFICADO':
    nome_arquivo = arquivo_xml.name.upper()
    palavras_evento = ['EVENTO', 'CANCELAMENTO', 'CARTA', 'CORRECAO', 'CCE', 'INUT']
    
    if any(palavra in nome_arquivo for palavra in palavras_evento):
        print(f"[IGNORADO] Evento não copiado no modo TIPO_CERTIFICADO: {nome_arquivo}")
        continue  # Pula para próximo arquivo
```

**Cópia de PDFs**:
```python
# Verifica se existe PDF correspondente
pdf_path = xml_path.with_suffix('.pdf')

if pdf_path.exists():
    # Copia para mesma pasta do XML
    shutil.copy2(pdf_path, caminho_destino / pdf_path.name)
    print(f"  📄 PDF copiado: {pdf_path.name}")
```

---

## 7️⃣ Funções Auxiliares

### `validar_xml_auto()`
**Arquivo**: `nfe_search.py`  
**Linha**: 1100-1250  
**Descrição**: Valida XML contra schema XSD automaticamente.

**Assinatura**:
```python
def validar_xml_auto(xml: str, default_xsd: str) -> bool
```

**Schemas Disponíveis**:
```python
SCHEMAS = {
    'distDFeInt_v1.01.xsd': 'schemas/distDFeInt_v1.01.xsd',
    'consSitNFe_v4.00.xsd': 'schemas/consSitNFe_v4.00.xsd',
    'consSitCTe_v4.00.xsd': 'schemas/consSitCTe_v4.00.xsd',
    'procNFe_v4.00.xsd': 'schemas/procNFe_v4.00.xsd',
    'procCTe_v4.00.xsd': 'schemas/procCTe_v4.00.xsd'
}
```

**Uso**:
```python
xml_request = """<distDFeInt xmlns="..." versao="1.01">...</distDFeInt>"""

try:
    validar_xml_auto(xml_request, 'distDFeInt_v1.01.xsd')
    logger.info("✅ XML válido")
except Exception as e:
    logger.error(f"❌ XML inválido: {e}")
    # Continua mesmo assim (XSD pode estar desatualizado)
```

---

### `setup_logger()`
**Arquivo**: `nfe_search.py`  
**Linha**: 68-110  
**Descrição**: Configura sistema de logs com saída para console e arquivo.

**Configuração**:
```python
# Pasta de logs
BASE / 'logs' / 'nfe_search_YYYYMMDD.log'

# Níveis de log
logger.setLevel(logging.DEBUG)  # Captura tudo

# Console: INFO e acima
console_handler.setLevel(logging.INFO)

# Arquivo: DEBUG e acima
file_handler.setLevel(logging.DEBUG)

# Formato
formato = '%(asctime)s [%(levelname)s] %(message)s'
```

**Rotação de Arquivos**:
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/nfe_search.log',
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5                # Mantém 5 arquivos
)
# Gera: nfe_search.log, nfe_search.log.1, nfe_search.log.2, ...
```

---

## 8️⃣ Resumo de Localizações Rápidas

### Top 10 Funções Mais Usadas

| # | Função | Arquivo | Linha | Uso Principal |
|---|--------|---------|-------|---------------|
| 1 | `extrair_nota_detalhada()` | nfe_search.py | 630 | Extrair dados de XML |
| 2 | `salvar_xml_por_certificado()` | nfe_search.py | 811 | Salvar XML em perfis |
| 3 | `NFeService.fetch_by_cnpj()` | nfe_search.py | 3280 | Buscar por NSU |
| 4 | `consultar_nfe_por_chave()` | nfe_search.py | 4396 | Buscar por chave |
| 5 | `processar_cte()` | nfe_search.py | 3688 | Processar CT-e |
| 6 | `DatabaseManager.salvar_nota_detalhada()` | nfe_search.py | 1850 | Salvar no banco |
| 7 | `DatabaseManager.get_last_nsu()` | nfe_search.py | 2050 | Obter último NSU |
| 8 | `DatabaseManager.get_cert_nome_by_informante()` | nfe_search.py | 2700 | Obter nome certificado |
| 9 | `MainWindow._baixar_xml_e_pdf()` | Busca NF-e.py | 5223 | Download manual GUI |
| 10 | `MainWindow._apply_profile()` | Busca NF-e.py | 17197 | Copiar XMLs (botão) |

---

## 9️⃣ Pontos Críticos de Atenção

### ⚠️ NSU Obrigatório
**Local**: `extrair_nota_detalhada()` linha 648-652

```python
if not nsu_documento:
    logger.error(f"🚨 CRÍTICO: extrair_nota_detalhada chamado SEM NSU")
    logger.error(f"   Documento será salvo mas NSU ficará vazio!")
```

**Impacto**: Sem NSU, não há rastreamento. Sistema pode reprocessar o mesmo documento infinitamente.

---

### ⚠️ Protocolo-Only Blocking
**Local**: `salvar_xml_por_certificado()` linha 955-966

```python
is_only_protocol = ('<retconssit' in xml_lower and '<protnfe' in xml_lower and '<nfeproc' not in xml_lower)

if is_only_protocol:
    return None  # Bloqueia salvamento
```

**Motivo**: NF-e emitidas consultadas por chave retornam apenas protocolo de autorização (sem dados fiscais).

---

### ⚠️ Erro 656 - NSU Preservation
**Local**: `processar_cte()` linha 3745-3750

```python
if cStat_cte == '656':
    logger.warning(f"🔒 CT-e: Erro 656 - Consumo indevido")
    logger.warning(f"   ⚠️ IMPORTANTE: NSU NÃO será atualizado")
    break  # Mantém NSU atual
```

**Motivo**: Em caso de bloqueio temporário, preservar NSU permite retomar do ponto correto após 65 minutos.

---

### ⚠️ Eventos Ignorados em TIPO_CERTIFICADO
**Local**: `_apply_profile()` linha 17497-17504

```python
if organizacao_tipo == 'TIPO_CERTIFICADO':
    if 'EVENTO' in nome_arquivo or 'CANCELAMENTO' in nome_arquivo:
        continue  # Ignora eventos
```

**Motivo**: Manter estrutura limpa com apenas documentos principais (NF-e e CT-e).

---

## 🔗 Referências

- **Documentação Completa**: Ver `README.md` na mesma pasta
- **Schemas**: Ver `SCHEMAS.md` para estruturas de banco e XML
- **Exemplos de Código**: Ver `EXEMPLOS.md` para implementações práticas
- **Manual SEFAZ**: [Portal da Nota Fiscal Eletrônica](http://www.nfe.fazenda.gov.br/)

---

**Última Atualização**: 15/01/2026  
**Versão do Sistema**: 6.2.1  
**Autor**: Sistema Busca NF-e/CT-e - Documentação Técnica
