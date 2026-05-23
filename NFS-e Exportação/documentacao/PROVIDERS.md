# 🏢 Provedores de NFS-e

## Visão Geral

No Brasil, cada município pode escolher seu próprio provedor de NFS-e, resultando em **centenas de sistemas diferentes** com APIs, formatos e regras distintas.

---

## 🌎 Provedores Principais

### 1. Ginfes (Sistema Nacional)

**Empresa**: ABRASF (Associação Brasileira das Secretarias de Finanças)

**Características**:
- Padrão **ABRASF 2.02** (mais moderno)
- Usado por **muitos municípios** em todo Brasil
- API SOAP padronizada

**URL Base**: `https://nfse.ginfes.com.br/ServiceGinfesImpl`

**Municípios Cobertos**: 500+

**Exemplo de Municípios**:
- Belo Horizonte/MG
- Brasília/DF
- Fortaleza/CE
- Salvador/BA
- Vitória/ES

**Configuração**:
```python
{
    "provedor": "GINFES",
    "versao": "2.02",
    "url": "https://nfse.ginfes.com.br/ServiceGinfesImpl",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 2. ISS.NET (IPM Sistemas)

**Empresa**: IPM Sistemas

**Características**:
- Muito usado em **São Paulo** e região
- Interface web moderna  
- API SOAP ABRASF 2.00

**URL Padrão**: `https://issnetonline.com.br/{cidade}/ws/nfse.asmx`

**Municípios Cobertos**: 200+

**Exemplo de Municípios**:
- São Paulo/SP (próprio)
- Campinas/SP
- Santos/SP
- Ribeirão Preto/SP
- Sorocaba/SP

**Configuração**:
```python
{
    "provedor": "ISSNET",
    "versao": "2.00",
    "url": "https://issnetonline.com.br/webservicenfse/1/nfse.asmx",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 3. eISS (Betha Sistemas - Curitiba)

**Empresa**: Betha Sistemas

**Características**:
- Focado no **Paraná** e Sul do Brasil
- Sistema robusto e estável
- Padrão ABRASF 1.00 (legado)

**URL Base**: `https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfse`

**Municípios Cobertos**: 150+

**Exemplo de Municípios**:
- Curitiba/PR
- Londrina/PR
- Maringá/PR
- Ponta Grossa/PR
- Cascavel/PR

**Configuração**:
```python
{
    "provedor": "EISS",
    "versao": "1.00",
    "url": "https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfse",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 4. Betha Sistemas (Nacional)

**Empresa**: Betha Sistemas

**Características**:
- Ampla cobertura **nacional**
- Usado por milhares de municípios pequenos/médios
- Suporte técnico robusto

**URL Padrão**: `https://{cidade}.betha.cloud/nfse/servicos`

**Municípios Cobertos**: 1000+

**Exemplo de Municípios**:
- Joinville/SC
- Blumenau/SC
- Chapecó/SC
- Lages/SC
- Florianópolis/SC (alguns serviços)

**Configuração**:
```python
{
    "provedor": "BETHA",
    "versao": "2.02",
    "url": "https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfse",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 5. WebISS

**Empresa**: WebISS

**Características**:
- Focado em **Rio de Janeiro**
- Interface amigável
- API SOAP proprietária

**URL Base**: `https://www.webiss.com.br/ws/nfse.asmx`

**Municípios Cobertos**: 50+

**Exemplo de Municípios**:
- Rio de Janeiro/RJ (alguns bairros)
- Niterói/RJ
- Nova Iguaçu/RJ
- Duque de Caxias/RJ

**Configuração**:
```python
{
    "provedor": "WEBISS",
    "versao": "1.00",
    "url": "https://www.webiss.com.br/ws/nfse.asmx",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 6. SimplISS

**Empresa**: Systempro

**Características**:
- Focado em **municípios pequenos**
- Interface simples
- Padrão ABRASF 2.00

**URL Padrão**: `https://sistema.simpliss.com.br/nfse/servicos`

**Municípios Cobertos**: 300+

**Configuração**:
```python
{
    "provedor": "SIMPLISS",
    "versao": "2.00",
    "url": "https://sistema.simpliss.com.br/nfse/servicos",
    "tipo_api": "SOAP",
    "requer_certificado": True
}
```

---

### 7. Nuvem Fiscal (Agregador Terceirizado) 🌐

**Empresa**: Nuvem Fiscal (SaaS)

**Características**:
- **REST API moderna** (não SOAP!)
- **OAuth2** (sem certificado A1)
- Unifica acesso a **múltiplos municípios**
- ⚠️ **Serviço pago** (custo por requisição)

**URL Base**: `https://api.nuvemfiscal.com.br`

**Municípios Cobertos**: Depende de integração (consultar site)

**Configuração**:
```python
{
    "provedor": "NUVEMFISCAL",
    "versao": "REST",
    "url": "https://api.nuvemfiscal.com.br",
    "tipo_api": "REST",
    "requer_certificado": False,  # Usa OAuth2
    "autenticacao": "OAuth2"
}
```

**Vantagens**:
- ✅ Sem complexidade de SOAP
- ✅ Sem necessidade de certificado A1
- ✅ API REST moderna (JSON)
- ✅ Documentação completa
- ✅ Suporte técnico

**Desvantagens**:
- ⚠️ Custo por operação
- ⚠️ Dependência de terceiro
- ⚠️ Nem todos municípios cobertos

---

### 8. ADN Nacional (Governo Federal)

**Empresa**: Governo Federal

**Características**:
- Sistema **nacional unificado**
- REST API
- ⚠️ **Apenas EMISSÃO** (sem consulta/distribuição)

**URL Base**: `https://adn.producaorestrita.nfse.gov.br`

**Municípios Cobertos**: Em expansão

**Configuração**:
```python
{
    "provedor": "ADN",
    "versao": "REST",
    "url": "https://adn.producaorestrita.nfse.gov.br",
    "tipo_api": "REST",
    "requer_certificado": True
}
```

**Limitação Crítica**:
```
⚠️ O ADN REST NÃO possui endpoint de CONSULTA de NFS-e.

Endpoints disponíveis:
✅ POST /adn/DFe → EMISSÃO de notas
✅ GET /danfse/{chave} → Visualizar PDF
❌ GET /consulta/nfse → NÃO EXISTE

Para consultar notas existentes, use SOAP municipal.
```

---

## 🗺️ Mapeamento por Estado

### São Paulo (SP)

| Município | Provedor | URL |
|-----------|----------|-----|
| São Paulo | Próprio | https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx |
| Campinas | ISS.NET | https://issnetonline.campinas.sp.gov.br |
| Santos | ISS.NET | https://issnetonline.santos.sp.gov.br |
| Ribeirão Preto | Ginfes | https://nfse.ginfes.com.br/ServiceGinfesImpl |

### Mato Grosso do Sul (MS)

| Município | Provedor | URL |
|-----------|----------|-----|
| Campo Grande | **Nuvem Fiscal** | https://api.nuvemfiscal.com.br |
| Dourados | IPM | https://issdigital.dourados.ms.gov.br |
| Três Lagoas | SimplISS | https://sistema.simpliss.com.br |

### Paraná (PR)

| Município | Provedor | URL |
|-----------|----------|-----|
| Curitiba | eISS | https://nfse.curitiba.pr.gov.br |
| Londrina | Betha | https://londrina.pr.gov.br/e-nota |
| Maringá | eISS | https://maringa.pr.gov.br/nfse |

### Rio de Janeiro (RJ)

| Município | Provedor | URL |
|-----------|----------|-----|
| Rio de Janeiro | Próprio | https://notacarioca.rio.gov.br |
| Niterói | WebISS | https://www.webiss.com.br/niteroi |
| Duque de Caxias | WebISS | https://www.webiss.com.br/duquedecaxias |

### Minas Gerais (MG)

| Município | Provedor | URL |
|-----------|----------|-----|
| Belo Horizonte | Ginfes | https://bhissdigital.pbh.gov.br |
| Uberlândia | Betha | https://udigital.uberlandia.mg.gov.br |
| Contagem | ISS.NET | https://issnetonline.contagem.mg.gov.br |

---

## 🔍 Como Identificar o Provedor

### 1. Via URL do Sistema

```python
def identificar_provedor_por_url(url):
    """Identifica provedor pela URL"""
    if "ginfes" in url:
        return "GINFES"
    elif "issnet" in url or "issdigital" in url:
        return "ISSNET"
    elif "betha" in url or "e-gov.betha" in url:
        return "BETHA"
    elif "webiss" in url:
        return "WEBISS"
    elif "simpliss" in url:
        return "SIMPLISS"
    elif "nuvemfiscal" in url:
        return "NUVEMFISCAL"
    elif "adn.producaorestrita.nfse.gov.br" in url:
        return "ADN"
    else:
        return "DESCONHECIDO"
```

### 2. Via Portal da Prefeitura

1. Acesse o site da prefeitura
2. Procure por **"Nota Fiscal Eletrônica"** ou **"NFS-e"**
3. Verifique o sistema usado (geralmente aparece no rodapé)
4. Anote a URL do portal

### 3. Via Consulta de Nota

1. Emita uma NFS-e de teste
2. Consulte a nota no portal
3. Veja o URL do sistema  principal
4. Identifique o provedor

---

## 🛠️ Configuração por Provedor

### Ginfes

```python
db.adicionar_config_nfse(
    cnpj="12345678000199",
    provedor="GINFES",
    cod_municipio="3106200",  # Belo Horizonte
    inscricao_municipal="12345",
    url="https://nfse.ginfes.com.br/ServiceGinfesImpl"
)
```

### ISS.NET

```python
db.adicionar_config_nfse(
    cnpj="12345678000199",
    provedor="ISSNET",
    cod_municipio="3509502",  # Campinas
    inscricao_municipal="12345",
    url="https://issnetonline.campinas.sp.gov.br/webservicenfse/1/nfse.asmx"
)
```

### Nuvem Fiscal

```python
# Não precisa configurar URL (REST API)
db.adicionar_config_nfse(
    cnpj="12345678000199",
    provedor="NUVEMFISCAL",
    cod_municipio="5002704",  # Campo Grande
    inscricao_municipal="12345",
    url=None  # API REST usa endpoint único
)
```

---

## 📊 Comparação de Provedores

| Provedor | Municípios | Estabilidade | Documentação | Suporte |
|----------|-----------|--------------|--------------|---------|
| **Ginfes** | 500+ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **ISS.NET** | 200+ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Betha** | 1000+ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **eISS** | 150+ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **WebISS** | 50+ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **SimplISS** | 300+ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Nuvem Fiscal** | Variável | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **ADN** | Em expansão | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 🔗 URLs de Homologação

### Ginfes
- **Produção**: `https://nfse.ginfes.com.br/ServiceGinfesImpl`
- **Homologação**: `https://homologacao.ginfes.com.br/ServiceGinfesImpl`

### ISS.NET
- **Produção**: `https://issnetonline.{cidade}.sp.gov.br/webservicenfse/1/nfse.asmx`
- **Homologação**: `https://homologacao.issnetonline.com.br/webservicenfse/1/nfse.asmx`

### Betha
- **Produção**: `https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfse`
- **Homologação**: `https://e-gov-homologacao.betha.com.br/e-nota-contribuinte-ws/nfse`

### Nuvem Fiscal
- **Produção**: `https://api.nuvemfiscal.com.br`
- **Homologação**: `https://api-sandbox.nuvemfiscal.com.br`

---

## 🆕 Adicionando Novo Provedor

### Passo 1: Identificar Padrão

```python
# Testar endpoint com WSDL
url_wsdl = "https://nfse.novoprovedor.com.br/ws/nfse.asmx?wsdl"
response = requests.get(url_wsdl)

if response.status_code == 200:
    print("✅ SOAP WSDL encontrado")
    # Parse WSDL para identificar métodos
```

### Passo 2: Adicionar ao Sistema

```python
# Em PROVEDORES_NFSE
PROVEDORES_NFSE["NOVO_PROVEDOR"] = {
    "nome": "Novo Provedor",
    "descricao": "Descrição do provedor",
    "url_base": "https://nfse.novoprovedor.com.br",
    "municipios": ["Cidade A", "Cidade B"],
    "versao": "2.02"
}

# Em URLS_MUNICIPIOS
URLS_MUNICIPIOS["1234567"] = {  # Código IBGE
    "nome": "Cidade Exemplo",
    "uf": "EX",
    "urls": ["https://nfse.novoprovedor.com.br/ws/nfse.asmx"],
    "versao": "2.02",
    "provedor": "NOVO_PROVEDOR"
}
```

### Passo 3: Implementar Método Específico

```python
def buscar_novo_provedor(self, codigo_municipio, inscricao_municipal, data_inicial, data_final):
    """Implementação específica para Novo Provedor"""
    # XML customizado se necessário
    # Tratamento de erros específicos
    # Parse de resposta customizado
    pass
```

---

## 📞 Suporte dos Provedores

### Ginfes
- **Site**: https://www.ginfes.com.br
- **Email**: suporte@ginfes.com.br
- **Telefone**: (11) 1234-5678

### ISS.NET (IPM)
- **Site**: https://www.ipmsistemas.com.br
- **Email**: suporte@ipmsistemas.com.br
- **Telefone**: (11) 2345-6789

### Betha
- **Site**: https://www.betha.com.br
- **Email**: atendimento@betha.com.br
- **Telefone**: (48) 3027-8000

### Nuvem Fiscal
- **Site**: https://nuvemfiscal.com.br
- **Email**: contato@nuvemfiscal.com.br
- **Docs**: https://docs.nuvemfiscal.com.br

---

## 📚 Recursos Adicionais

- [ABRASF - Padrão Nacional](https://abrasf.org.br)
- [Portal Nacional NFS-e](https://www.gov.br/nfse)
- [Lista Completa de Municípios e Provedores](https://nfse.prefeitura.sp.gov.br/links)

---

**Próximos Passos**

Para mais informações:
- [ARQUITETURA.md](ARQUITETURA.md) - Arquitetura completa
- [API_GUIDE.md](API_GUIDE.md) - Guia de APIs
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Estrutura do banco
- [WEB_MIGRATION.md](WEB_MIGRATION.md) - Migração para web
