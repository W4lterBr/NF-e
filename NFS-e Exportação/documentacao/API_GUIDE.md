# 📡 Guia de APIs NFS-e

## Visão Geral

O sistema de NFS-e trabalha com **três tipos de APIs**:

1. **SOAP Municipal** (padrão ABRASF) - Maioria dos municípios
2. **REST ADN Nacional** - Apenas emissão (limitado)
3. **REST Nuvem Fiscal** - Agregador terceirizado (moderno)

---

## 🌍 Tipos de APIs

### Comparação

| Característica | SOAP Municipal | ADN REST | Nuvem Fiscal REST |
|---|---|---|---|
| **Protocolo** | SOAP/XML | REST/JSON | REST/JSON |
| **Autenticação** | Certificado A1 | Certificado A1 | OAuth2 |
| **Padrão** | ABRASF 1.0/2.0/2.02 | Nacional | Proprietário |
| **Cobertura** | Por município | Nacional | Multi-município |
| **Consulta NFS-e** | ✅ Sim | ❌ Não (só emissão) | ✅ Sim |
| **Emissão NFS-e** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Manutenção** | Municipal | Nacional | Terceirizado |
| **Estabilidade** | ⚠️ Variável | ✅ Boa | ✅ Alta |

---

## 1️⃣ SOAP Municipal (ABRASF)

### Padrão ABRASF

A **ABRASF** (Associação Brasileira das Secretarias de Finanças das Capitais) define o padrão nacional de NFS-e.

**Versões**:
- **1.00** - Primeira versão (legado)
- **2.00** - Segunda versão (mais comum)
- **2.02** - Versão mais recente (recomendada)

### Endpoints Comuns

#### ConsultarNfseEnvio (Buscar NFS-e)

**Operação**: Consultar NFS-e por período, prestador ou tomador.

**URL Exemplo**:
```
POST https://nfse.municipio.uf.gov.br/ServiceGinfesImpl
```

**Headers**:
```http
Content-Type: text/xml; charset=utf-8
SOAPAction: ""
```

**Request (SOAP 1.1)**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <ConsultarNfseEnvioRequest xmlns="http://www.ginfes.com.br">
            <nfseCabecMsg><![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<cabecalho versao="3" xmlns="http://www.abrasf.org.br/nfse.xsd">
    <versaoDados>3</versaoDados>
</cabecalho>]]></nfseCabecMsg>
            
            <nfseDadosMsg><![CDATA[<ConsultarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Prestador>
        <Cnpj>12345678000199</Cnpj>
        <InscricaoMunicipal>12345</InscricaoMunicipal>
    </Prestador>
    <PeriodoEmissao>
        <DataInicial>2025-01-01</DataInicial>
        <DataFinal>2025-01-31</DataFinal>
    </PeriodoEmissao>
</ConsultarNfseEnvio>]]></nfseDadosMsg>
        </ConsultarNfseEnvioRequest>
    </soap:Body>
</soap:Envelope>
```

**Response (Sucesso)**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
            <ListaNfse>
                <CompNfse>
                    <Nfse>
                        <InfNfse Id="NFS-e123456">
                            <Numero>123456</Numero>
                            <CodigoVerificacao>ABC123</CodigoVerificacao>
                            <DataEmissao>2025-01-15T10:30:00</DataEmissao>
                            <NaturezaOperacao>1</NaturezaOperacao>
                            <RegimeEspecialTributacao>1</RegimeEspecialTributacao>
                            <OptanteSimplesNacional>1</OptanteSimplesNacional>
                            <IncentivadorCultural>2</IncentivadorCultural>
                            <Competencia>2025-01-15</Competencia>
                            <Servico>
                                <Valores>
                                    <ValorServicos>1500.00</ValorServicos>
                                    <ValorDeducoes>0.00</ValorDeducoes>
                                    <ValorPis>0.00</ValorPis>
                                    <ValorCofins>0.00</ValorCofins>
                                    <ValorInss>0.00</ValorInss>
                                    <ValorIr>0.00</ValorIr>
                                    <ValorCsll>0.00</ValorCsll>
                                    <IssRetido>2</IssRetido>
                                    <ValorIss>75.00</ValorIss>
                                    <ValorIssRetido>0.00</ValorIssRetido>
                                    <OutrasRetencoes>0.00</OutrasRetencoes>
                                    <BaseCalculo>1500.00</BaseCalculo>
                                    <Aliquota>5.0</Aliquota>
                                    <ValorLiquidoNfse>1500.00</ValorLiquidoNfse>
                                </Valores>
                                <ItemListaServico>01.01</ItemListaServico>
                                <CodigoTributacaoMunicipio>010101</CodigoTributacaoMunicipio>
                                <Discriminacao>Serviços de consultoria</Discriminacao>
                                <CodigoMunicipio>5002704</CodigoMunicipio>
                            </Servico>
                            <PrestadorServico>
                                <IdentificacaoPrestador>
                                    <Cnpj>12345678000199</Cnpj>
                                    <InscricaoMunicipal>12345</InscricaoMunicipal>
                                </IdentificacaoPrestador>
                                <RazaoSocial>EMPRESA PRESTADORA LTDA</RazaoSocial>
                                <Endereco>
                                    <Endereco>Rua Exemplo</Endereco>
                                    <Numero>123</Numero>
                                    <Bairro>Centro</Bairro>
                                    <CodigoMunicipio>5002704</CodigoMunicipio>
                                    <Uf>MS</Uf>
                                    <Cep>79000000</Cep>
                                </Endereco>
                                <Contato>
                                    <Telefone>6733334444</Telefone>
                                    <Email>contato@empresaprestadora.com.br</Email>
                                </Contato>
                            </PrestadorServico>
                            <TomadorServico>
                                <IdentificacaoTomador>
                                    <CpfCnpj>
                                        <Cnpj>98765432000100</Cnpj>
                                    </CpfCnpj>
                                </IdentificacaoTomador>
                                <RazaoSocial>EMPRESA TOMADORA LTDA</RazaoSocial>
                                <Endereco>
                                    <Endereco>Av Cliente</Endereco>
                                    <Numero>456</Numero>
                                    <Bairro>Jd America</Bairro>
                                    <CodigoMunicipio>5002704</CodigoMunicipio>
                                    <Uf>MS</Uf>
                                    <Cep>79010000</Cep>
                                </Endereco>
                                <Contato>
                                    <Email>contato@tomadora.com.br</Email>
                                </Contato>
                            </TomadorServico>
                        </InfNfse>
                    </Nfse>
                </CompNfse>
            </ListaNfse>
        </ConsultarNfseResposta>
    </soap:Body>
</soap:Envelope>
```

**Response (Erro)**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <ConsultarNfseResposta xmlns="http://www.abrasf.org.br/nfse.xsd">
            <ListaMensagemRetorno>
                <MensagemRetorno>
                    <Codigo>E001</Codigo>
                    <Mensagem>CNPJ do prestador não cadastrado no município</Mensagem>
                    <Correcao>Verifique o CNPJ informado e a inscrição municipal</Correcao>
                </MensagemRetorno>
            </ListaMensagemRetorno>
        </ConsultarNfseResposta>
    </soap:Body>
</soap:Envelope>
```

### Códigos de Erro SOAP Comuns

| Código | Descrição | Solução |
|--------|-----------|---------|
| **E001** | CNPJ não cadastrado | Verificar CNPJ e inscrição municipal |
| **E002** | Certificado inválido | Renovar certificado digital |
| **E003** | Data inválida | Verificar formato (AAAA-MM-DD) |
| **E004** | Período muito extenso | Reduzir período de consulta (máx 90 dias) |
| **E005** | Nenhuma nota encontrada | Sem notas no período informado |
| **E006** | Erro de autenticação | Verificar certificado e senha |

### Parse de Resposta SOAP

```python
from lxml import etree

def parse_soap_response(xml_string):
    root = etree.fromstring(xml_string.encode('utf-8'))
    
    # Namespace ABRASF
    ns = {'nfse': 'http://www.abrasf.org.br/nfse.xsd'}
    
    # Buscar erros
    erros = root.xpath('//nfse:MensagemRetorno', namespaces=ns)
    if erros:
        return {
            'status': 'erro',
            'erros': [
                {
                    'codigo': erro.findtext('nfse:Codigo', namespaces=ns),
                    'mensagem': erro.findtext('nfse:Mensagem', namespaces=ns)
                }
                for erro in erros
            ]
        }
    
    # Buscar notas
    notas = root.xpath('//nfse:CompNfse', namespaces=ns)
    
    resultado = []
    for nota in notas:
        resultado.append({
            'numero': nota.findtext('.//nfse:Numero', namespaces=ns),
            'data_emissao': nota.findtext('.//nfse:DataEmissao', namespaces=ns),
            'valor': float(nota.findtext('.//nfse:ValorServicos', namespaces=ns) or 0),
            'prestador_cnpj': nota.findtext('.//nfse:Prestador//nfse:Cnpj', namespaces=ns),
            'tomador_cnpj': nota.findtext('.//nfse:Tomador//nfse:Cnpj', namespaces=ns),
            'xml': etree.tostring(nota, encoding='unicode')
        })
    
    return {
        'status': 'sucesso',
        'total': len(resultado),
        'notas': resultado
    }
```

---

## 2️⃣ REST ADN Nacional

### ⚠️ LIMITAÇÃO IMPORTANTE

O ADN (Ambiente de Distribuição Nacional) possui APIs REST, **MAS**:

✅ **Disponível**: Emissão de NFS-e (`POST /adn/DFe`)  
❌ **NÃO DISPONÍVEL**: Consulta/distribuição de NFS-e existentes

Para **consultar** NFS-e já emitidas, é necessário usar **SOAP municipal**.

### Endpoints ADN

**Base URL**: `https://adn.producaorestrita.nfse.gov.br`

#### POST /adn/DFe (Emissão)

**Descrição**: Emitir uma nova NFS-e.

**Headers**:
```http
Content-Type: application/json
Accept: application/json
```

**Request**:
```json
{
  "LoteXmlGZipB64": [
    "H4sIAAAAAAAAA... (XML compactado em GZIP e codificado em Base64)"
  ]
}
```

**Response (Sucesso)**:
```json
{
  "TipoAmbiente": "PRODUCAO",
  "Lote": [
    {
      "StatusProcessamento": "PROCESSADO",
      "XmlGZipB64": "H4sIAAAAAAAAA...",
      "Erros": []
    }
  ]
}
```

**Response (Erro)**:
```json
{
  "TipoAmbiente": "PRODUCAO",
  "Lote": [
    {
      "StatusProcessamento": "ERRO",
      "Erros": [
        {
          "Codigo": "E1242",
          "Descricao": "Tipo DF-e não tratado pelo Sistema Nacional NFS-e"
        }
      ]
    }
  ]
}
```

#### GET /danfse/{chaveAcesso}

**Descrição**: Visualizar DANFSe (PDF da nota).

**Request**:
```http
GET /danfse/50123456789012345678901234567890123456 HTTP/1.1
```

**Response**: PDF da NFS-e

---

## 3️⃣ REST Nuvem Fiscal (Agregador)

### Sobre Nuvem Fiscal

**Nuvem Fiscal** é um agregador terceirizado que oferece API REST moderna para emissão e consulta de NFS-e em vários municípios.

✅ **Vantagens**:
- API REST moderna (não precisa lidar com SOAP)
- OAuth2 (não precisa certificado A1)
- Unifica acesso a múltiplos municípios
- Documentação completa e suporte técnico

⚠️ **Desvantagens**:
- Serviço pago (custo por operação)
- Depende de terceiro
- Nem todos municípios disponíveis

### Autenticação OAuth2

#### 1. Obter Token

```http
POST /oauth/token HTTP/1.1
Host: api.nuvemfiscal.com.br
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=seu_client_id
&client_secret=seu_client_secret
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

#### 2. Usar Token

```http
GET /api/v1/nfse?parametros HTTP/1.1
Host: api.nuvemfiscal.com.br
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Consultar NFS-e

**Endpoint**: `GET /api/v1/nfse`

**Query Parameters**:
- `cpf_cnpj` (obrigatório): CPF/CNPJ do prestador
- `data_inicial` (obrigatório): Data inicial (YYYY-MM-DD)
- `data_final` (obrigatório): Data final (YYYY-MM-DD)
- `codigo_municipio` (opcional): Código IBGE
- `ambiente` (opcional): producao | homologacao
- `top` (opcional): Limite de resultados (padrão: 10, máx: 100)
- `skip` (opcional): Paginação (offset)

**Request Exemplo**:
```http
GET /api/v1/nfse?cpf_cnpj=12345678000199&data_inicial=2025-01-01&data_final=2025-01-31&codigo_municipio=5002704&top=50 HTTP/1.1
Host: api.nuvemfiscal.com.br
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/json
```

**Response**:
```json
{
  "count": 15,
  "data": [
    {
      "id": "60d5ec49f8b4c70001234567",
      "numero": "123456",
      "codigo_verificacao": "ABC123DEF",
      "data_emissao": "2025-01-15T10:30:00",
      "status": "AUTORIZADA",
      "ambiente": "PRODUCAO",
      "codigo_municipio": "5002704",
      "declaracao_prestacao_servico": {
        "prestador": {
          "cpf_cnpj": "12345678000199",
          "inscricao_municipal": "12345",
          "razao_social": "EMPRESA PRESTADORA LTDA"
        },
        "tomador": {
          "cpf_cnpj": "98765432000100",
          "razao_social": "EMPRESA TOMADORA LTDA",
          "endereco": {
            "logradouro": "Av Cliente",
            "numero": "456",
            "bairro": "Jd America",
            "codigo_municipio": "5002704",
            "uf": "MS",
            "cep": "79010000"
          }
        },
        "servicos": [
          {
            "codigo_cnae": "6201500",
            "codigo_tributacao_municipio": "010101",
            "discriminacao": "Serviços de consultoria",
            "codigo_municipio": "5002704",
            "item_lista_servico": "01.01",
            "aliquota": 5.0,
            "valor_servicos": 1500.00,
            "valor_deducoes": 0.00,
            "valor_pis": 0.00,
            "valor_cofins": 0.00,
            "valor_inss": 0.00,
            "valor_ir": 0.00,
            "valor_csll": 0.00,
            "iss_retido": false,
            "valor_iss": 75.00,
            "valor_iss_retido": 0.00,
            "outras_retencoes": 0.00,
            "base_calculo": 1500.00,
            "valor_liquido_nfse": 1500.00
          }
        ]
      },
      "pdf_url": "https://api.nuvemfiscal.com.br/pdf/60d5ec49f8b4c70001234567"
    }
  ],
  "has_more": false
}
```

### Códigos de Erro Nuvem Fiscal

| Status | Código | Descrição |
|--------|--------|-----------|
| **400**  | `bad_request` | Parâmetros inválidos |
| **401** | `unauthorized` | Token inválido ou expirado |
| **403** | `forbidden` | Sem permissão (plano insuficiente) |
| **404** | `not_found` | Recurso não encontrado |
| **429** | `rate_limit_exceeded` | Limite de requisições excedido |
| **500** | `internal_error` | Erro interno do servidor |
| **503** | `service_unavailable` | Serviço municipal offline |

### Implementação Python

```python
import requests

class NuvemFiscalAPI:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.nuvemfiscal.com.br"
        self.token = None
    
    def authenticate(self):
        """Obtém token OAuth2"""
        response = requests.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        response.raise_for_status()
        self.token = response.json()['access_token']
    
    def consultar_nfse(self, cpf_cnpj, data_inicial, data_final, codigo_municipio=None, top=50):
        """Consulta NFS-e"""
        if not self.token:
            self.authenticate()
        
        params = {
            "cpf_cnpj": cpf_cnpj,
            "data_inicial": data_inicial,
            "data_final": data_final,
            "top": top
        }
        
        if codigo_municipio:
            params["codigo_municipio"] = codigo_municipio
        
        response = requests.get(
            f"{self.base_url}/api/v1/nfse",
            headers={"Authorization": f"Bearer {self.token}"},
            params=params
        )
        response.raise_for_status()
        return response.json()
```

---

## 🔐 Certificado Digital (SOAP e ADN)

### Formato PKCS#12 (.pfx)

```python
import requests_pkcs12

# Requisição com certificado A1
response = requests_pkcs12.post(
    url="https://nfse.municipio.gov.br/ws/nfse.asmx",
    data=xml_soap,
    headers={'Content-Type': 'text/xml; charset=utf-8'},
    pkcs12_filename="/caminho/certificado.pfx",
    pkcs12_password="senha_do_certificado",
    verify=False,  # Desabilita verificação SSL (muitos municípios têm certificados auto-assinados)
    timeout=15
)
```

### Validação de Certificado

```python
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime

def validar_certificado(pfx_path, senha):
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()
    
    try:
        private_key, certificate, ca_chain = serialization.pkcs12.load_key_and_certificates(
            pfx_data,
            senha.encode(),
            default_backend()
        )
        
        # Verificar data de validade
        not_valid_after = certificate.not_valid_after
        
        if datetime.now() > not_valid_after:
            return {
                "valido": False,
                "mensagem": "Certificado expirado",
                "validade": not_valid_after.isoformat()
            }
        
        # Extrair CNPJ do certificado
        subject = certificate.subject
        cn = subject.get_attributes_for_oid(serialization.NameOID.COMMON_NAME)[0].value
        
        return {
            "valido": True,
            "cnpj": cn,
            "validade": not_valid_after.isoformat()
        }
    
    except Exception as e:
        return {
            "valido": False,
            "mensagem": f"Erro ao validar: {str(e)}"
        }
```

---

## 🔍 Descoberta Automática de URLs

```python
def descobrir_url_municipio(codigo_ibge, nome_municipio, uf):
    """
    Gera URLs padrão baseadas em convenções comuns.
    """
    nome_limpo = nome_municipio.lower().replace(' ', '').replace('á', 'a').replace('ã', 'a')
    uf_lower = uf.lower()
    
    urls_padrao = [
        # IPM Sistemas (muito comum)
        f"https://issdigital.{nome_limpo}.{uf_lower}.gov.br/nfse-web/services/NfseWSService",
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/IssWeb-ejb/IssWebWS/IssWebWS",
        
        # Betha Sistemas
        f"https://{nome_limpo}.{uf_lower}.gov.br/e-nota/ws/nfse.asmx",
        
        # Ginfes/ABRASF
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/ServiceGinfesImpl",
        
        # Sistemas próprios
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/ws/nfse.asmx",
    ]
    
    return urls_padrao
```

---

## 📊 Rate Limiting e Boas Práticas

### Limites Comuns

| Provedor | Limite | Período |
|----------|--------|---------|
| **SOAP Municipal** | Variável (5-20/min) | Por minuto |
| **ADN Nacional** | 100 requisições | Por minuto |
| **Nuvem Fiscal** | Conforme plano | Por mês (custo por requisição) |

### Implementação de Retry

```python
import time
from requests.exceptions import RequestException

def request_with_retry(func, max_retries=3, delay=2):
    """
    Executa requisição com retry automático.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}. Retentando em {delay}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"Todas as {max_retries} tentativas falharam")
                raise
```

###  Cache de Consultas

```python
import hashlib
import json
from datetime import datetime, timedelta

class NFSeCache:
    def __init__(self, ttl_hours=24):
        self.cache = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def _make_key(self, cnpj, cod_municipio, data_ini, data_fim):
        key_str = f"{cnpj}_{cod_municipio}_{data_ini}_{data_fim}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, cnpj, cod_municipio, data_ini, data_fim):
        key = self._make_key(cnpj, cod_municipio, data_ini, data_fim)
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                logger.info(f"✅ Cache hit para {cnpj}")
                return data
        
        return None
    
    def set(self, cnpj, cod_municipio, data_ini, data_fim, data):
        key = self._make_key(cnpj, cod_municipio, data_ini, data_fim)
        self.cache[key] = (data, datetime.now())
```

---

## 📚 Referências

- **ABRASF**: [Padrão Nacional NFS-e](https://abrasf.org.br)
- **ADN**: [Documentação Swagger](https://adn.producaorestrita.nfse.gov.br/docs/)
- **Nuvem Fiscal**: [API Docs](https://nuvemfiscal.com.br/docs)
- **requests-pkcs12**: [GitHub](https://github.com/m-click/requests_pkcs12)

---

**Próximos Passos**

Para mais informações:
- [ARQUITETURA.md](ARQUITETURA.md) - Arquitetura completa
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Estrutura do banco
- [PROVIDERS.md](PROVIDERS.md) - Lista de provedores
- [WEB_MIGRATION.md](WEB_MIGRATION.md) - Migração para web
