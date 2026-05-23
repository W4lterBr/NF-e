# 🏢 Sistema de Busca de NFS-e - Documentação Completa

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [O que é NFS-e?](#o-que-é-nfs-e)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Dependências](#dependências)
5. [Instalação e Configuração](#instalação-e-configuração)
6. [Documentação Técnica](#documentação-técnica)
7. [Exemplos de Uso](#exemplos-de-uso)
8. [Migração para Web](#migração-para-web)
9. [Suporte e Contato](#suporte-e-contato)

---

## 🎯 Visão Geral

Este sistema permite **consultar e baixar automaticamente NFS-e (Notas Fiscais de Serviço Eletrônica)** de diversos municípios brasileiros.

### Características Principais

✅ **Multi-município**: Suporta consulta em diferentes cidades  
✅ **Multi-provedor**: Compatível com Ginfes, ISS.NET, eISS, Betha, WebISS e outros  
✅ **Certificado Digital**: Autenticação segura via certificado A1 (.pfx)  
✅ **APIs Modernas**: Suporta SOAP municipal e REST (Nuvem Fiscal)  
✅ **Banco de Dados**: SQLite para armazenamento local (migração para PostgreSQL/MySQL recomendada)  
✅ **Logging Completo**: Rastreabilidade total de todas as operações  

### Limitações Conhecidas

⚠️ **ADN Nacional**: O sistema ADN (Ambiente de Distribuição Nacional) possui apenas endpoint de **EMISSÃO** de NFS-e via REST. Para **CONSULTA** de notas existentes, é necessário usar SOAP municipal.

⚠️ **Manutenção Municipal**: Muitos municípios estão com servidores SOAP em manutenção (ex: Campo Grande/MS).

---

## 📚 O que é NFS-e?

### Diferenças entre NF-e e NFS-e

| Característica | NF-e | NFS-e |
|---|---|---|
| **Tipo de Operação** | Produtos | Serviços |
| **Centralização** | SEFAZ (estadual) | Prefeituras (municipal) |
| **Protocolo** | Webservices SEFAZ | SOAP municipal ou REST |
| **Padrão** | Nacional (mesmo webservice) | Descentralizado (cada cidade diferente) |
| **Distribuição** | DFe Nacional (NSU) | Sem distribuição unificada |

### NFS-e é Descentralizada

Cada município brasileiro pode ter:
- **Provedor diferente** (Ginfes, ISS.NET, Betha, etc.)
- **URLs diferentes** (sistemas próprios)
- **Versões diferentes** (ABRASF 1.0, 2.0, 2.02, etc.)
- **Regras de validação diferentes**

Isso torna a integração **muito mais complexa** que NF-e.

---

## 📁 Estrutura do Projeto

```
NFS-e Exportação/
│
├── codigo/                          # Código-fonte
│   └── nfse_search.py              # Sistema principal (1.506 linhas)
│
├── documentacao/                    # Documentação técnica
│   ├── ARQUITETURA.md              # Arquitetura do sistema
│   ├── DATABASE_SCHEMA.md          # Estrutura do banco de dados
│   ├── API_GUIDE.md                # Guia de APIs (SOAP e REST)
│   ├── PROVIDERS.md                # Provedores e municípios
│   └── WEB_MIGRATION.md            # Guia de migração para web
│
├── database/                        # Schema do banco
│   ├── schema.sql                  # Criação das tabelas
│   └── sample_data.sql             # Dados de exemplo
│
├── exemplos/                        # Exemplos de uso
│   ├── exemplo_basico.py           # Busca simples
│   ├── exemplo_multiplos_municipios.py
│   └── exemplo_nuvem_fiscal.py
│
└── README.md                        # Este arquivo
```

---

## 🔧 Dependências

### Python 3.8+

```bash
pip install lxml requests requests-pkcs12 sqlite3
```

### Bibliotecas Obrigatórias

```python
lxml            # Parse de XML (SOAP e NFS-e)
requests        # HTTP requests
requests-pkcs12 # Autenticação com certificado A1
sqlite3         # Banco de dados (built-in Python)
pathlib         # Manipulação de caminhos (built-in)
logging         # Sistema de logs (built-in)
```

### Bibliotecas Opcionais

```python
nuvem_fiscal_api  # Agregador terceirizado (API REST moderna)
```

### Certificado Digital A1

- Arquivo `.pfx` (PKCS#12)
- Senha do certificado
- Válido e dentro do prazo

---

## 🚀 Instalação e Configuração

### 1. Instalar Dependências

```bash
cd "NFS-e Exportação/codigo"
pip install -r requirements.txt
```

### 2. Configurar Banco de Dados

O sistema cria automaticamente as tabelas na primeira execução:

```python
from nfse_search import NFSeDatabase

db = NFSeDatabase()
# Tabelas criadas automaticamente:
# - nfse_config
# - nfse_baixadas
# - rps
# - nsu_nfse
```

### 3. Cadastrar Certificado

O sistema busca certificados da tabela `certificados` do banco principal. Certifique-se de que o certificado está cadastrado no sistema.

### 4. Configurar Município

```python
from nfse_search import NFSeDatabase

db = NFSeDatabase()

# Adicionar configuração
db.adicionar_config_nfse(
    cnpj="12345678000199",
    provedor="GINFES",
    cod_municipio="5002704",  # Campo Grande/MS
    inscricao_municipal="12345",
    url=None  # Opcional: URL customizada
)
```

### 5. Executar Busca

```bash
python nfse_search.py
```

Ou usar como módulo:

```python
from nfse_search import NFSeService, NFSeDatabase

# Inicializar
service = NFSeService(
    certificado_path="/caminho/certificado.pfx",
    senha="senha123",
    cnpj="12345678000199"
)

# Buscar NFS-e
resultado = service.buscar_ginfes(
    codigo_municipio="5002704",
    inscricao_municipal="12345",
    data_inicial="01/01/2025",
    data_final="31/01/2025"
)

print(f"Encontradas {len(resultado['notas'])} NFS-e")
```

---

## 📖 Documentação Técnica

### Arquivos de Documentação

#### 1. [ARQUITETURA.md](documentacao/ARQUITETURA.md)
Detalhes técnicos completos do sistema:
- Classes principais (`NFSeDatabase`, `NFSeService`)
- Fluxo de dados
- Diagramas de arquitetura
- Estrutura de pastas e módulos

#### 2. [DATABASE_SCHEMA.md](documentacao/DATABASE_SCHEMA.md)
Estrutura completa do banco de dados:
- Tabelas e colunas com tipos
- Relacionamentos
- Índices e chaves
- Queries de exemplo

#### 3. [API_GUIDE.md](documentacao/API_GUIDE.md)
Guia completo de APIs:
- SOAP municipal (padrão ABRASF)
- REST ADN Nacional (limitações)
- REST Nuvem Fiscal (agregador)
- Formatos de requisição e resposta
- Códigos de erro

#### 4. [PROVIDERS.md](documentacao/PROVIDERS.md)
Provedores de NFS-e:
- Lista completa de provedores
- Municípios por provedor
- URLs de produção e homologação
- Configurações específicas

#### 5. [WEB_MIGRATION.md](documentacao/WEB_MIGRATION.md)
Guia de migração para sistema web:
- Arquitetura web recomendada
- Mudanças necessárias
- Stack tecnológica sugerida
- Boas práticas de segurança
- Escalabilidade e performance

---

## 💡 Exemplos de Uso

### Exemplo 1: Busca Básica

```python
from nfse_search import NFSeService

service = NFSeService(
    certificado_path="certificado.pfx",
    senha="senha",
    cnpj="12345678000199"
)

resultado = service.buscar_ginfes(
    codigo_municipio="5002704",
    inscricao_municipal="12345",
    data_inicial="01/01/2025",
    data_final="31/01/2025"
)

for nota in resultado['notas']:
    print(f"NFS-e {nota['numero']}: R$ {nota['valor']:.2f}")
```

### Exemplo 2: Múltiplos Municípios

```python
from nfse_search import NFSeDatabase, NFSeService

db = NFSeDatabase()
service = NFSeService("cert.pfx", "senha", "12345678000199")

# Busca configurações do CNPJ
configs = db.get_config_nfse("12345678000199")

for provedor, cod_mun, insc_mun, url in configs:
    resultado = service.buscar_ginfes(cod_mun, insc_mun, "01/01/2025", "31/01/2025")
    print(f"Município {cod_mun}: {len(resultado['notas'])} notas")
```

### Exemplo 3: Nuvem Fiscal (REST)

```python
from nfse_search import NFSeService

service = NFSeService("cert.pfx", "senha", "12345678000199")

# Busca via Nuvem Fiscal (sem SOAP municipal)
notas = service.buscar_nuvemfiscal(
    cpf_cnpj="12345678000199",
    data_inicial="2025-01-01",
    data_final="2025-01-31",
    codigo_municipio="5002704",
    ambiente="producao"
)

print(f"Encontradas {len(notas)} NFS-e via Nuvem Fiscal")
```

Mais exemplos em: [`exemplos/`](exemplos/)

---

## 🌐 Migração para Web

### Por que Migrar?

- **Escalabilidade**: Múltiplos usuários simultâneos
- **Acessibilidade**: Acesso via navegador de qualquer lugar
- **Banco Robusto**: PostgreSQL ou MySQL em vez de SQLite
- **Fila de Processamento**: Celery + RabbitMQ para tarefas assíncronas
- **Cache**: Redis para otimizar consultas frequentes
- **HSM/Cloud**: Certificados em HSM ou AWS KMS (mais seguro)

### Stack Recomendada

```
Frontend:
├── React ou Vue.js
├── TypeScript
└── Material-UI ou Tailwind CSS

Backend:
├── Python 3.8+
├── FastAPI ou Django REST Framework
├── PostgreSQL ou MySQL
├── Celery (fila de tarefas)
├── RabbitMQ ou Redis (broker)
└── Nginx (proxy reverso)

Infraestrutura:
├── Docker + Docker Compose
├── Kubernetes (produção)
├── AWS/Azure/GCP
└── CI/CD (GitHub Actions, GitLab CI)
```

### Mudanças Necessárias

#### 1. **Banco de Dados**

```python
# Antes (SQLite):
import sqlite3
conn = sqlite3.connect("notas.db")

# Depois (PostgreSQL):
import psycopg2
conn = psycopg2.connect(
    host="localhost",
    database="nfse_db",
    user="postgres",
    password="senha"
)
```

#### 2. **Certificados**

```python
# Antes (arquivo local):
service = NFSeService(
    certificado_path="/caminho/local/cert.pfx",
    senha="senha",
    cnpj="12345678000199"
)

# Depois (AWS KMS ou HSM):
from cloud_storage import get_certificate_from_kms

cert_data = get_certificate_from_kms("arn:aws:kms:...")
service = NFSeService(
    certificado_data=cert_data,  # Bytes do certificado
    senha=decrypt_password(cert_id),
    cnpj="12345678000199"
)
```

#### 3. **Processamento Assíncrono**

```python
# Celery task para busca em background
from celery import shared_task

@shared_task
def buscar_nfse_async(cnpj, cod_municipio, data_ini, data_fim):
    service = NFSeService(...)
    resultado = service.buscar_ginfes(...)
    
    # Salva no banco
    db = NFSeDatabase()
    for nota in resultado['notas']:
        db.salvar_nfse(...)
    
    return len(resultado['notas'])
```

#### 4. **API REST (FastAPI)**

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/api/nfse/buscar")
async def buscar_nfse(
    cnpj: str,
    cod_municipio: str,
    data_inicial: str,
    data_final: str,
    background_tasks: BackgroundTasks
):
    # Dispara task em background
    task = buscar_nfse_async.delay(cnpj, cod_municipio, data_inicial, data_final)
    
    return {
        "task_id": task.id,
        "status": "processing",
        "message": "Busca iniciada em background"
    }

@app.get("/api/nfse/status/{task_id}")
async def status_busca(task_id: str):
    task = buscar_nfse_async.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None
    }
```

**Documentação completa**: [WEB_MIGRATION.md](documentacao/WEB_MIGRATION.md)

---

## 🔐 Segurança

### Certificados Digitais

- **NUNCA** commitar certificados no Git
- Usar variáveis de ambiente ou serviços de secrets (AWS Secrets Manager, Azure Key Vault)
- Certificados em produção devem estar em HSM

### Senhas

```python
# ❌ ERRADO - senha hardcoded
senha = "minha_senha_123"

# ✅ CORRETO - variável de ambiente
import os
senha = os.environ.get("CERT_PASSWORD")

# ✅ MELHOR - serviço de secrets
from aws_secrets import get_secret
senha = get_secret("nfse/certificado/senha")
```

### Logs

```python
# ❌ ERRADO - senha nos logs
logger.info(f"Usando certificado com senha: {senha}")

# ✅ CORRETO - não logar dados sensíveis
logger.info(f"Usando certificado: {cert_path}")
```

---

## 🐛 Troubleshooting

### Erro: "Certificado não encontrado"

```bash
# Verificar se arquivo existe
ls -la /caminho/certificado.pfx

# Verificar permissões
chmod 600 certificado.pfx
```

### Erro: "Senha incorreta"

```python
# Testar certificado manualmente
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

with open("cert.pfx", "rb") as f:
    pfx_data = f.read()

try:
    serialization.pkcs12.load_key_and_certificates(
        pfx_data,
        b"senha_teste",
        default_backend()
    )
    print("✅ Senha correta!")
except:
    print("❌ Senha incorreta!")
```

### Erro: "URL do município não responde"

```python
# Testar manualmente
import requests

url = "https://nfse.municipio.uf.gov.br/ws/nfse.asmx"

try:
    response = requests.get(url, timeout=5, verify=False)
    print(f"Status: {response.status_code}")
except requests.exceptions.Timeout:
    print("❌ Timeout - servidor não responde")
except requests.exceptions.ConnectionError:
    print("❌ Erro de conexão - verifique URL")
```

---

## 📞 Suporte e Contato

### Documentação Adicional

- [ARQUITETURA.md](documentacao/ARQUITETURA.md) - Detalhes técnicos
- [DATABASE_SCHEMA.md](documentacao/DATABASE_SCHEMA.md) - Estrutura do banco
- [API_GUIDE.md](documentacao/API_GUIDE.md) - APIs e integrações
- [PROVIDERS.md](documentacao/PROVIDERS.md) - Provedores de NFS-e
- [WEB_MIGRATION.md](documentacao/WEB_MIGRATION.md) - Migração para web

### Recursos Externos

- [ABRASF - Padrão NFS-e](https://abrasf.org.br)
- [ADN Nacional - Documentação](https://adn.producaorestrita.nfse.gov.br/docs/)
- [Nuvem Fiscal API](https://nuvemfiscal.com.br)
- [IBGE - Códigos de Municípios](https://servicodados.ibge.gov.br/api/docs/localidades)

### Changelog

- **2025-12-18**: Identificação de limitação do ADN (apenas emissão)
- **2025-01-XX**: Adição de suporte a Nuvem Fiscal (REST)
- **2024-XX-XX**: Implementação inicial com SOAP municipal

---

## 📄 Licença

Este código é proprietário e confidencial. Não distribuir sem autorização.

---

**Última atualização**: 13 de fevereiro de 2025  
**Versão do sistema**: 1.1.23  
**Autor**: Sistema Busca XML - NFS-e
