# 🌐 Guia de Migração para Web

## Visão Geral

Este guia orienta a migração do sistema de busca de NFS-e de **desktop (Python CLI)** para **aplicação web** moderna, escalável e segura.

---

## 🎯 Objetivos da Migração

### Benefícios

✅ **Acessibilidade**: Acesso via navegador de qualquer lugar  
✅ **Escalabilidade**: Múltiplos usuários simultâneos  
✅ **Manutenção**: Atualizações centralizadas (não precisa atualizar em cada máquina)  
✅ **Banco Robusto**: PostgreSQL/MySQL em vez de SQLite  
✅ **Segurança**: Certificados em HSM ou cloud (AWS KMS, Azure Key Vault)  
✅ **Performance**: Cache, filas, processamento assíncrono  
✅ **Monitoramento**: Logs centralizados, métricas, alertas  

---

## 🏗️ Arquitetura Recomendada

### Stack Tecnológica

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (SPA)                            │
│                                                              │
│  • React ou Vue.js com TypeScript                           │
│  • Material-UI ou Tailwind CSS                              │
│  • Axios para HTTP requests                                 │
│  • React Query para cache e estado                          │
└────────────┬────────────────────────────────────────────────┘
             │ HTTPS/REST API (JSON)
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (API)                             │
│                                                              │
│  • Python 3.10+ com FastAPI ou Django REST Framework        │
│  • Pydantic para validação                                  │
│  • SQLAlchemy ou Django ORM                                 │
│  • Alembic para migrations                                  │
│  • JWT para autenticação                                    │
└────────────┬──────────────┬─────────────────────────────────┘
             │              │
             ▼              ▼
┌─────────────────────┐ ┌────────────────────────────────┐
│  FILA DE TAREFAS    │ │  CACHE                         │
│                     │ │                                │
│  • Celery           │ │  • Redis                       │
│  • RabbitMQ/Redis   │ │  • Memcached                   │
│  (broker)           │ │                                │
└─────────────────────┘ └────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    PERSISTÊNCIA                              │
│                                                              │
│  • PostgreSQL ou MySQL                                      │
│  • Schemas separados (multi-tenant)                         │
│  • Replicação master-slave                                  │
│  • Backup automático                                        │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                 SERVIÇOS EXTERNOS                            │
│                                                              │
│  • AWS KMS ou Azure Key Vault (certificados)                │
│  • S3 ou Azure Blob Storage (XMLs/PDFs)                     │
│  • CloudWatch ou Datadog (monitoramento)                    │
│  • Sentry (error tracking)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Mudanças Necessárias

### 1. Banco de Dados

#### Antes (SQLite)

```python
import sqlite3

conn = sqlite3.connect("notas.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM nfse_baixadas WHERE cnpj_prestador = ?", (cnpj,))
```

#### Depois (PostgreSQL com SQLAlchemy)

```python
from sqlalchemy import create_engine, Column, String, DateTime, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class NfseBaixada(Base):
    __tablename__ = 'nfse_baixadas'
    
    numero_nfse = Column(String(50), primary_key=True)
    cnpj_prestador = Column(String(14), nullable=False, index=True)
    cnpj_tomador = Column(String(14), index=True)
    data_emissao = Column(DateTime, nullable=False, index=True)
    valor_servico = Column(Numeric(15, 2), nullable=False)
    xml_content = Column(String)
    data_download = Column(DateTime, default=datetime.utcnow)

# Conexão
engine = create_engine('postgresql://user:pass@localhost/nfse_db')
Session = sessionmaker(bind=engine)
session = Session()

# Query
notas = session.query(NfseBaixada).filter_by(cnpj_prestador=cnpj).all()
```

### 2. Armazenamento de Certificados

#### Antes (Arquivo Local)

```python
service = NFSeService(
    certificado_path="/caminho/local/certificado.pfx",
    senha="senha_hardcoded",
    cnpj="12345678000199"
)
```

#### Depois (AWS KMS)

```python
import boto3
from base64 import b64decode

def get_certificate_from_kms(cert_id):
    """Busca certificado criptografado no AWS KMS"""
    kms = boto3.client('kms')
    
    # Busca certificado criptografado do S3
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket='certificados-nfse', Key=f"{cert_id}.pfx.encrypted")
    encrypted_cert = obj['Body'].read()
    
    # Descriptografa com KMS
    response = kms.decrypt(CiphertextBlob=encrypted_cert)
    decrypted_cert = response['Plaintext']
    
    return decrypted_cert

# Uso
service = NFSeService(
    certificado_data=get_certificate_from_kms('empresa-12345678000199'),  # bytes
    senha=get_secret('nfse/certificado/senha'),  # AWS Secrets Manager
    cnpj="12345678000199"
)
```

### 3. Processamento Assíncrono

#### Antes (Síncrono)

```python
# Bloqueia a aplicação enquanto busca
resultado = service.buscar_ginfes("5002704", "12345", "01/01/2025", "31/01/2025")

for nota in resultado['notas']:
    db.salvar_nfse(...)
```

#### Depois (Celery Task)

```python
from celery import shared_task
from app.models import NfseBaixada
from app.services import NFSeService

@shared_task(bind=True, max_retries=3)
def buscar_nfse_async(self, empresa_id, cod_municipio, data_ini, data_fim):
    """
    Task assíncrona para buscar NFS-e.
    Roda em background sem bloquear API.
    """
    try:
        # Busca empresa e configurações
        empresa = Empresa.query.get(empresa_id)
        
        # Busca certificado do KMS
        cert_data = get_certificate_from_kms(empresa.cert_id)
        senha = get_secret(f"nfse/certificado/{empresa_id}/senha")
        
        # Inicializa serviço
        service = NFSeService(cert_data, senha, empresa.cnpj)
        
        # Busca NFS-e
        resultado = service.buscar_ginfes(cod_municipio, empresa.inscricao_municipal, data_ini, data_fim)
        
        # Salva no banco
        for nota in resultado['notas']:
            nfse = NfseBaixada(
                numero_nfse=nota['numero'],
                cnpj_prestador=empresa.cnpj,
                cnpj_tomador=nota['tomador_cnpj'],
                data_emissao=nota['data_emissao'],
                valor_servico=nota['valor'],
                xml_content=nota['xml']
            )
            db.session.add(nfse)
        
        db.session.commit()
        
        return {
            'status': 'sucesso',
            'total_notas': len(resultado['notas'])
        }
    
    except Exception as e:
        # Retry com exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

### 4. API REST (FastAPI)

```python
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import date

app = FastAPI(title="NFS-e API", version="1.0.0")
security = HTTPBearer()

# Schemas
class BuscarNfseRequest(BaseModel):
    empresa_id: int
    codigo_municipio: str
    data_inicial: date
    data_final: date

class BuscarNfseResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, PROCESSING, SUCCESS, FAILURE
    result: Optional[dict] = None
    error: Optional[str] = None

# Autenticação
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# Endpoints
@app.post("/api/v1/nfse/buscar", response_model=BuscarNfseResponse)
async def buscar_nfse(
    request: BuscarNfseRequest,
    background_tasks: BackgroundTasks,
    user=Depends(verify_token)
):
    """
    Inicia busca de NFS-e em background.
    Retorna task_id para acompanhamento.
    """
    # Valida permissões
    if not user_has_access(user['id'], request.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    
    # Dispara task Celery
    task = buscar_nfse_async.delay(
        request.empresa_id,
        request.codigo_municipio,
        request.data_inicial.isoformat(),
        request.data_final.isoformat()
    )
    
    return BuscarNfseResponse(
        task_id=task.id,
        status="PENDING",
        message="Busca iniciada em background"
    )

@app.get("/api/v1/nfse/status/{task_id}", response_model=TaskStatusResponse)
async def status_busca(task_id: str, user=Depends(verify_token)):
    """Consulta status de uma busca em background"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'status': 'PENDING',
            'result': None
        }
    elif task.state == 'PROCESSING':
        response = {
            'task_id': task_id,
            'status': 'PROCESSING',
            'result': task.info  # Progresso
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'status': 'SUCCESS',
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'status': 'FAILURE',
            'error': str(task.info)
        }
    
    return TaskStatusResponse(**response)

@app.get("/api/v1/nfse/listar")
async def listar_nfse(
    cnpj_prestador: str,
    data_inicial: Optional[date] = None,
    data_final: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
    user=Depends(verify_token)
):
    """Lista NFS-e com filtros e paginação"""
    query = db.session.query(NfseBaixada).filter_by(cnpj_prestador=cnpj_prestador)
    
    if data_inicial:
        query = query.filter(NfseBaixada.data_emissao >= data_inicial)
    if data_final:
        query = query.filter(NfseBaixada.data_emissao <= data_final)
    
    total = query.count()
    notas = query.limit(limit).offset(offset).all()
    
    return {
        'total': total,
        'limit': limit,
        'offset': offset,
        'data': [
            {
                'numero': nota.numero_nfse,
                'data_emissao': nota.data_emissao.isoformat(),
                'valor': float(nota.valor_servico),
                'tomador_cnpj': nota.cnpj_tomador
            }
            for nota in notas
        ]
    }
```

### 5. Frontend (React)

```typescript
// services/nfseService.ts
import axios from 'axios';

const API_URL = 'https://api.seusite.com/api/v1';

export interface BuscarNfseRequest {
  empresa_id: number;
  codigo_municipio: string;
  data_inicial: string;
  data_final: string;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message?: string;
  result?: any;
  error?: string;
}

class NFSeService {
  private getHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }
  
  async buscarNfse(request: BuscarNfseRequest): Promise<TaskResponse> {
    const response = await axios.post(
      `${API_URL}/nfse/buscar`,
      request,
      { headers: this.getHeaders() }
    );
    return response.data;
  }
  
  async getTaskStatus(taskId: string): Promise<TaskResponse> {
    const response = await axios.get(
      `${API_URL}/nfse/status/${taskId}`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }
  
  async listarNfse(
    cnpjPrestador: string,
    dataInicial?: string,
    dataFinal?: string
  ): Promise<any> {
    const params = new URLSearchParams({ cnpj_prestador: cnpjPrestador });
    if (dataInicial) params.append('data_inicial', dataInicial);
    if (dataFinal) params.append('data_final', dataFinal);
    
    const response = await axios.get(
      `${API_URL}/nfse/listar?${params}`,
      { headers: this.getHeaders() }
    );
    return response.data;
  }
}

export default new NFSeService();
```

```tsx
// components/BuscarNfse.tsx
import React, { useState } from 'react';
import { Button, TextField, CircularProgress } from '@mui/material';
import nfseService from '../services/nfseService';

export const BuscarNfse: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  
  const handleBuscar = async () => {
    setLoading(true);
    
    try {
      const response = await nfseService.buscarNfse({
        empresa_id: 1,
        codigo_municipio: '5002704',
        data_inicial: '2025-01-01',
        data_final: '2025-01-31'
      });
      
      setTaskId(response.task_id);
      
      // Polling do status
      const interval = setInterval(async () => {
        const statusResponse = await nfseService.getTaskStatus(response.task_id);
        setStatus(statusResponse.status);
        
        if (statusResponse.status === 'SUCCESS') {
          clearInterval(interval);
          setLoading(false);
          alert(`Busca concluída! ${statusResponse.result.total_notas} notas encontradas`);
        } else if (statusResponse.status === 'FAILURE') {
          clearInterval(interval);
          setLoading(false);
          alert(`Erro: ${statusResponse.error}`);
        }
      }, 2000);  // Poll a cada 2 segundos
      
    } catch (error) {
      console.error(error);
      setLoading(false);
      alert('Erro ao iniciar busca');
    }
  };
  
  return (
    <div>
      <h2>Buscar NFS-e</h2>
      
      <TextField label="Data Inicial" type="date" />
      <TextField label="Data Final" type="date" />
      
      <Button 
        variant="contained" 
        onClick={handleBuscar} 
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} /> : 'Buscar'}
      </Button>
      
      {taskId && (
        <p>Task ID: {taskId} | Status: {status}</p>
      )}
    </div>
  );
};
```

---

## 🔐 Segurança

### 1. Certificados em Cloud

#### AWS KMS (Key Management Service)

```python
import boto3

def encrypt_certificate(cert_path, kms_key_id):
    """Criptografa certificado com KMS antes de armazenar"""
    kms = boto3.client('kms')
    s3 = boto3.client('s3')
    
    # Lê certificado
    with open(cert_path, 'rb') as f:
        cert_data = f.read()
    
    # Criptografa com KMS
    response = kms.encrypt(KeyId=kms_key_id, Plaintext=cert_data)
    encrypted_cert = response['CiphertextBlob']
    
    # Armazena no S3
    s3.put_object(
        Bucket='certificados-nfse',
        Key=f"{cnpj}.pfx.encrypted",
        Body=encrypted_cert,
        ServerSideEncryption='AES256'
    )
```

#### Azure Key Vault

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def store_certificate_azure(cert_path, vault_url, secret_name):
    """Armazena certificado no Azure Key Vault"""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    # Lê certificado e converte para base64
    with open(cert_path, 'rb') as f:
        cert_data = base64.b64encode(f.read()).decode()
    
    # Armazena no Key Vault
    client.set_secret(secret_name, cert_data)
```

### 2. Senhas e Secrets

```python
# ❌ ERRADO - hardcoded
senha = "senha_do_certificado"

# ✅ CORRETO - AWS Secrets Manager
import boto3

def get_secret(secret_name):
    sm = boto3.client('secretsmanager')
    response = sm.get_secret_value(SecretId=secret_name)
    return response['SecretString']

senha = get_secret('nfse/certificado/12345678000199/senha')
```

### 3. Autenticação JWT

```python
from datetime import datetime, timedelta
import jwt

SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

def create_access_token(user_id: int, empresa_id: int):
    """Gera JWT token"""
    payload = {
        'user_id': user_id,
        'empresa_id': empresa_id,
        'exp': datetime.utcnow() + timedelta(hours=8),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str):
    """Valida JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expirado')
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail='Token inválido')
```

---

## 📊 Cache e Performance

### Redis Cache

```python
import redis
import json
from functools import wraps

# Conexão Redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expire_seconds=3600):
    """Decorator para cachear resultados no Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Gera chave do cache
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Tenta buscar do cache
            cached = redis_client.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit: {cache_key}")
                return json.loads(cached)
            
            # Executa função
            result = func(*args, **kwargs)
            
            # Salva no cache
            redis_client.setex(
                cache_key,
                expire_seconds,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

# Uso
@cache_result(expire_seconds=7200)  # Cache de 2 horas
def buscar_nfse_cached(cnpj, cod_municipio, data_ini, data_fim):
    service = NFSeService(...)
    return service.buscar_ginfes(cod_municipio, ..., data_ini, data_fim)
```

---

## 🐳 Docker e Deploy

### Dockerfile (Backend)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY . .

# Expõe porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nfse_db
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./:/app

  celery_worker:
    build: .
    command: celery -A app.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nfse_db
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery_beat:
    build: .
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=nfse_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## 📈 Monitoramento

### Logging

```python
import logging
from pythonjsonlogger import jsonlogger

# Configurar logger JSON
logger = logging.getLogger()
logHandler = logging.StreamHandler()

formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Uso
logger.info("Busca iniciada", extra={
    'cnpj': '12345678000199',
    'municipio': '5002704',
    'user_id': 123
})
```

### Métricas (Prometheus)

```python
from prometheus_client import Counter, Histogram, start_http_server

# Métricas
nfse_requests_total = Counter('nfse_requests_total', 'Total de buscas NFS-e')
nfse_duration_seconds = Histogram('nfse_duration_seconds', 'Tempo de busca NFS-e')

@nfse_duration_seconds.time()
def buscar_nfse(...):
    nfse_requests_total.inc()
    # ... lógica de busca
```

### Error Tracking (Sentry)

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="https://...@sentry.io/...",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0
)
```

---

## 🚀 Checklist de Migração

### Fase 1: Preparação
- [ ] Definir stack tecnológica
- [ ] Configurar ambiente de desenvolvimento
- [ ] Criar repositório Git
- [ ] Configurar CI/CD

### Fase 2: Backend
- [ ] Migrar banco SQLite → PostgreSQL
- [ ] Implementar API REST (FastAPI/Django)
- [ ] Implementar autenticação JWT
- [ ] Configurar Celery para tasks assíncronas
- [ ] Migrar lógica de busca NFS-e
- [ ] Implementar testes unitários
- [ ] Implementar testes de integração

### Fase 3: Segurança
- [ ] Migrar certificados para cloud (AWS KMS/Azure Key Vault)
- [ ] Implementar gestão de secrets (AWS Secrets Manager)
- [ ] Configurar HTTPS/TLS
- [ ] Implementar rate limiting
- [ ] Implementar auditoria

### Fase 4: Frontend
- [ ] Criar SPA com React/Vue
- [ ] Implementar autenticação
- [ ] Criar telas de busca NFS-e
- [ ] Criar telas de visualização/listagem
- [ ] Implementar paginação
- [ ] Implementar filtros

### Fase 5: Performance
- [ ] Implementar cache (Redis)
- [ ] Otimizar queries do banco
- [ ] Implementar CDN para assets
- [ ] Configurar compressão (gzip)
- [ ] Load testing

### Fase 6: Monitoramento
- [ ] Configurar logs centralizados
- [ ] Configurar métricas (Prometheus/Grafana)
- [ ] Configurar alertas
- [ ] Configurar error tracking (Sentry)
- [ ] Configurar APM (Application Performance Monitoring)

### Fase 7: Deploy
- [ ] Dockerizar aplicação
- [ ] Configurar Kubernetes (se necessário)
- [ ] Deploy em homologação
- [ ] Testes de aceitação
- [ ] Deploy em produção
- [ ] Rollback plan

---

## 📚 Recursos

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
- [AWS KMS](https://docs.aws.amazon.com/kms/)
- [Azure Key Vault](https://docs.microsoft.com/azure/key-vault/)

---

**Próximos Passos**

Para mais informações:
- [ARQUITETURA.md](ARQUITETURA.md) - Arquitetura atual
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Estrutura do banco
- [API_GUIDE.md](API_GUIDE.md) - APIs NFS-e
- [PROVIDERS.md](PROVIDERS.md) - Provedores disponíveis
