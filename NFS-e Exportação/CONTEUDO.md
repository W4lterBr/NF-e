# 📦 Conteúdo da Exportação - Sistema de Busca NFS-e

## ✅ Exportação Completa

Esta pasta contém **TUDO** necessário para migrar o sistema de busca de NFS-e para uma plataforma web.

---

## 📊 Resumo

| Categoria | Quantidade | Linhas Totais |
|-----------|------------|---------------|
| **Código-fonte** | 1 arquivo | 1.506 linhas |
| **Documentação** | 5 arquivos | ~3.200 linhas |
| **Exemplos** | 3 arquivos | ~600 linhas |
| **SQL** | 2 arquivos | ~500 linhas |
| **Total** | **11 arquivos** | **~5.800 linhas** |

---

## 📁 Estrutura Detalhada

### 📂 **codigo/** (Código-fonte)

#### ✅ `nfse_search.py` (1.506 linhas)
- **Conteúdo**: Sistema completo de busca de NFS-e
- **Classes principais**:
  - `NFSeDatabase`: Gerencia banco de dados SQLite
  - `NFSeService`: Integração com APIs SOAP e REST
- **Documentação**: Docstrings completas em todos os métodos
- **APIs suportadas**:
  - SOAP Municipal (GINFES, ISS.NET, BETHA, eISS, WebISS, SimplISS)
  - REST ADN Nacional (limitação: apenas emissão)
  - REST Nuvem Fiscal (agregador terceirizado)
- **Funcionalidades**:
  - Busca de NFS-e por período
  - Armazenamento em banco SQLite
  - Autenticação com certificado A1 (.pfx)
  - Logging completo
  - Tratamento de erros

---

### 📂 **documentacao/** (Documentação Técnica)

#### ✅ `ARQUITETURA.md` (~800 linhas)
- **Conteúdo**: Arquitetura completa do sistema
- **Tópicos**:
  - Diagramas de arquitetura (ASCII art)
  - Camadas do sistema (Dados, Lógica, Interface)
  - Fluxo de dados (SOAP e REST)
  - Classes e métodos documentados
  - Padrões de integração (CLI, PyQt5 threads)
  - Fluxos de autenticação (Certificado A1, OAuth2)
  - Sistema de logging
  - Performance e timeouts

#### ✅ `DATABASE_SCHEMA.md` (~600 linhas)
- **Conteúdo**: Estrutura completa do banco de dados
- **Tópicos**:
  - **Tabelas** (4 tabelas):
    - `nfse_config`: Configurações de acesso aos provedores
    - `nfse_baixadas`: NFS-e baixadas e armazenadas
    - `rps`: Recibos Provisórios de Serviços
    - `nsu_nfse`: Controle de NSU para distribuição
  - Relacionamentos e chaves estrangeiras
  - Índices para performance
  - **Migração SQLite → PostgreSQL**:
    - Scripts completos de conversão
    - Alterações de tipos
    - Ajustes de constraints
  - Queries comuns e otimizações
  - Views úteis (resumo_prestador, config_ativa, rps_pendentes)
  - Tabelas de auditoria (recomendações)

#### ✅ `API_GUIDE.md` (~700 linhas)
- **Conteúdo**: Guia completo de APIs
- **Tópicos**:
  - **SOAP Municipal (ABRASF)**:
    - Operações disponíveis (RecepcionarLoteRps, ConsultarNfse, CancelarNfse)
    - Exemplos de XML (request e response)
    - Parse de respostas com namespaces
    - Códigos de erro (E001-E006)
  - **REST ADN Nacional**:
    - ⚠️ **LIMITAÇÃO CRÍTICA**: Apenas emissão, SEM endpoint de consulta
    - Endpoints disponíveis
    - JSON request/response
    - Autenticação com certificado
  - **REST Nuvem Fiscal**:
    - OAuth2 authentication flow
    - Endpoints completos
    - Paginação (top/skip)
    - Exemplos de código Python
    - Rate limiting e retry strategies
  - **Certificado A1**:
    - Formato PKCS#12 (.pfx)
    - Uso com requests-pkcs12
    - Validação e troubleshooting
  - Cache e performance

#### ✅ `PROVIDERS.md` (~400 linhas)
- **Conteúdo**: Mapeamento completo de provedores
- **Tópicos**:
  - **8 Provedores Principais**:
    - **GINFES**: 500+ municípios, ABRASF 2.02
    - **ISS.NET**: 200+ municípios, foco em São Paulo
    - **Betha**: 1.000+ municípios, cobertura nacional
    - **eISS**: 150+ municípios, Paraná (Curitiba)
    - **WebISS**: 50+ municípios, Rio de Janeiro
    - **SimplISS**: 300+ municípios, cidades pequenas
    - **Nuvem Fiscal**: Agregador REST/OAuth2 (pago)
    - **ADN Nacional**: Federal, REST, apenas emissão
  - **Mapeamento por Estado**:
    - São Paulo (SP): 50+ municípios listados
    - Mato Grosso do Sul (MS): 20+ municípios
    - Paraná (PR): 30+ municípios
    - Rio de Janeiro (RJ): 15+ municípios
    - Minas Gerais (MG): 40+ municípios
  - Configuração por provedor (código Python)
  - URLs de produção e homologação
  - Comparação de provedores (tabela)
  - Suporte e contatos
  - Como adicionar novo provedor

#### ✅ `WEB_MIGRATION.md` (~1.000 linhas)
- **Conteúdo**: Guia completo de migração para web
- **Tópicos**:
  - **Arquitetura Web**:
    - Frontend: React/Vue.js + TypeScript
    - Backend: FastAPI ou Django REST Framework
    - Banco: PostgreSQL ou MySQL
    - Fila: Celery + RabbitMQ/Redis
    - Cache: Redis
  - **Mudanças Necessárias**:
    - SQLite → PostgreSQL (com SQLAlchemy)
    - Certificados locais → AWS KMS / Azure Key Vault
    - Processamento síncrono → Celery tasks assíncronas
    - Autenticação: Certificado A1 + JWT + OAuth2
  - **API REST Design**:
    - Endpoints FastAPI
    - Schemas Pydantic
    - Status de tasks
    - Paginação
  - **Frontend**:
    - Componentes React
    - Serviços Axios
    - Polling de status
  - **Segurança**:
    - Certificados em cloud (AWS/Azure)
    - Secrets management
    - JWT authentication
    - HTTPS/TLS
  - **Cache e Performance**:
    - Redis caching
    - Decorators de cache
    - Query optimization
  - **Docker e Deploy**:
    - Dockerfile
    - docker-compose.yml
    - Kubernetes manifests
  - **Monitoramento**:
    - Logging JSON estruturado
    - Prometheus metrics
    - Sentry error tracking
  - **Checklist Completo** (7 fases):
    - Preparação, Backend, Segurança, Frontend, Performance, Monitoramento, Deploy

---

### 📂 **database/** (SQL Scripts)

#### ✅ `schema.sql` (~400 linhas)
- **Conteúdo**: Schema completo PostgreSQL
- **Inclui**:
  - CREATE TABLE (4 tabelas)
  - Índices otimizados
  - Constraints e Foreign Keys
  - UNIQUE constraints
  - Views úteis (vw_resumo_prestador, vw_config_ativa, vw_rps_pendentes)
  - Triggers (update timestamp automático)
  - Auditoria (audit_log table + triggers)
  - Funções úteis:
    - `buscar_nfse_periodo()`: Busca NFS-e por período
    - `total_nfse_mensal()`: Agregação mensal
  - Comentários COMMENT ON TABLE/COLUMN
  - Pode ser executado diretamente no PostgreSQL

#### ✅ `sample_data.sql` (~100 linhas)
- **Conteúdo**: Dados de exemplo para testes
- **Inclui**:
  - Empresa fictícia: Acme Ltda (CNPJ 12345678000199)
  - Configurações de acesso:
    - Campo Grande/MS (GINFES)
    - São Paulo/SP (ISS.NET)
    - Curitiba/PR (eISS)
    - Configuração inativa (exemplo)
  - NFS-e de exemplo:
    - Janeiro/2025: 3 notas
    - Fevereiro/2025: 4 notas
    - Nota cancelada (exemplo)
    - Nota com XML completo
  - RPS:
    - Convertidos em NFS-e
    - Pendentes
    - Com erro
  - NSU (controle de distribuição)
  - Queries de teste comentadas

---

### 📂 **exemplos/** (Exemplos de Código)

#### ✅ `exemplo_basico.py` (~150 linhas)
- **Conteúdo**: Exemplo de busca simples
- **Demonstra**:
  - Inicialização do serviço
  - Busca em um município (GINFES)
  - Validação de certificado
  - Exibição de resultados
  - Salvamento opcional no banco
  - Tratamento de erros
  - Consulta ao banco de dados
- **Casos de uso**: Primeiro contato com o sistema

#### ✅ `exemplo_multiplos_municipios.py` (~250 linhas)
- **Conteúdo**: Busca em múltiplos municípios
- **Demonstra**:
  - Classe `ProcessadorMultiplasNFSe`
  - Buscar configurações do banco
  - Iterar sobre municípios
  - Seleção automática de provedor
  - Salvamento automático
  - Estatísticas e resumo
  - Processamento em batch
  - Exemplo adicional: processamento mensal (ano completo)
- **Casos de uso**: Empresas que atuam em várias cidades

#### ✅ `exemplo_nuvem_fiscal.py` (~200 linhas)
- **Conteúdo**: Uso da API REST Nuvem Fiscal
- **Demonstra**:
  - Classe `NuvemFiscalAPI`
  - Autenticação OAuth2
  - Renovação automática de token
  - Busca via REST (sem certificado)
  - Paginação automática
  - Baixar XML de NFS-e específica
  - Salvamento no banco
- **Casos de uso**: Integração moderna sem SOAP

---

### 📄 **Arquivos Raiz**

#### ✅ `README.md` (~560 linhas)
- **Conteúdo**: Ponto de entrada da documentação
- **Seções**:
  - Visão geral do sistema
  - O que é NFS-e (diferenças com NF-e)
  - Estrutura do projeto
  - Dependências
  - Instalação e configuração
  - Links para documentação técnica
  - Exemplos de uso
  - Migração para web
  - Troubleshooting
  - Suporte

#### ✅ `requirements.txt` (~80 linhas)
- **Conteúdo**: Dependências Python
- **Inclui**:
  - Dependências obrigatórias (lxml, requests, requests-pkcs12)
  - Dependências opcionais para web (FastAPI, SQLAlchemy, Celery, etc)
  - Dependências de desenvolvimento (pytest, black, flake8)
  - Instruções de instalação comentadas

#### ✅ `CONTEUDO.md` (este arquivo)
- **Conteúdo**: Manifesto completo da exportação
- **Uso**: Visão geral rápida do que foi exportado

---

## 🎯 Como Usar Esta Exportação

### 1️⃣ **Para Entender o Sistema Atual**

1. Comece pelo [README.md](README.md)
2. Leia [ARQUITETURA.md](documentacao/ARQUITETURA.md)
3. Veja o código em [codigo/nfse_search.py](codigo/nfse_search.py)
4. Execute [exemplos/exemplo_basico.py](exemplos/exemplo_basico.py)

### 2️⃣ **Para Migrar para Web**

1. Leia [WEB_MIGRATION.md](documentacao/WEB_MIGRATION.md) (PRIORIDADE)
2. Estude [DATABASE_SCHEMA.md](documentacao/DATABASE_SCHEMA.md)
3. Execute [database/schema.sql](database/schema.sql) no PostgreSQL
4. Adapte o código usando os exemplos como referência
5. Siga o checklist no WEB_MIGRATION.md (7 fases)

### 3️⃣ **Para Integrar APIs**

1. Leia [API_GUIDE.md](documentacao/API_GUIDE.md)
2. Consulte [PROVIDERS.md](documentacao/PROVIDERS.md)
3. Teste com [exemplos/exemplo_nuvem_fiscal.py](exemplos/exemplo_nuvem_fiscal.py) (REST)
4. ⚠️ **IMPORTANTE**: ADN só emite, não consulta. Use SOAP municipal.

### 4️⃣ **Para Adicionar Municípios**

1. Consulte [PROVIDERS.md](documentacao/PROVIDERS.md)
2. Identifique o provedor do município
3. Configure no banco usando `nfse_config`
4. Teste com [exemplos/exemplo_basico.py](exemplos/exemplo_basico.py)

---

## 🚀 Próximos Passos Recomendados

### Fase 1: Validação (1-2 dias)
- [ ] Ler toda a documentação
- [ ] Executar exemplos Python
- [ ] Testar busca em 2-3 municípios
- [ ] Validar certificado A1

### Fase 2: Banco de Dados (1 semana)
- [ ] Instalar PostgreSQL
- [ ] Executar schema.sql
- [ ] Executar sample_data.sql
- [ ] Migrar dados existentes do SQLite
- [ ] Testar queries e views

### Fase 3: Backend API (2-3 semanas)
- [ ] Criar projeto FastAPI
- [ ] Implementar endpoints REST
- [ ] Integrar com nfse_search.py
- [ ] Configurar Celery para tasks assíncronas
- [ ] Implementar autenticação JWT
- [ ] Testes unitários e integração

### Fase 4: Segurança (1 semana)
- [ ] Migrar certificados para AWS KMS ou Azure Key Vault
- [ ] Configurar AWS Secrets Manager
- [ ] Implementar HTTPS/TLS
- [ ] Rate limiting
- [ ] Auditoria

### Fase 5: Frontend (2 semanas)
- [ ] Criar projeto React/Vue
- [ ] Telas de busca NFS-e
- [ ] Telas de listagem e filtros
- [ ] Polling de status de tasks
- [ ] Dashboard

### Fase 6: Deploy (1 semana)
- [ ] Dockerizar aplicação
- [ ] docker-compose para desenvolvimento
- [ ] Deploy em homologação
- [ ] Testes de carga
- [ ] Deploy em produção

**TOTAL ESTIMADO: 8-10 semanas para MVP completo**

---

## ⚠️ Atenções Importantes

### 🔴 CRÍTICO

1. **ADN Nacional**:
   - ❌ NÃO possui endpoint REST de consulta/distribuição
   - ✅ Possui apenas endpoint de emissão
   - 🔧 Para consultas, usar SOAP municipal obrigatoriamente

2. **Certificado A1**:
   - Obrigatório para SOAP
   - Formato PKCS#12 (.pfx)
   - Precisa ser válido e dentro do prazo
   - Em produção web: usar HSM ou KMS

3. **Provedores Descentralizados**:
   - Cada município pode ter provedor diferente
   - URLs podem mudar sem aviso
   - Requer manutenção constante

### 🟡 IMPORTANTE

1. **SQLite → PostgreSQL**:
   - SQLite é para desenvolvimento local
   - PostgreSQL/MySQL obrigatório em produção
   - Scripts de migração incluídos

2. **Processamento Assíncrono**:
   - Busca de NFS-e pode demorar (5-30 segundos)
   - Em web, usar filas (Celery)
   - Não bloquear API

3. **Cache**:
   - Implementar Redis para performance
   - TTL recomendado: 2-4 horas
   - Invalidar ao salvar nova NFS-e

---

## 📞 Suporte

Para dúvidas sobre a exportação:

1. Consulte a documentação em `documentacao/`
2. Veja os exemplos em `exemplos/`
3. Execute queries de teste em `database/sample_data.sql`

---

## ✅ Checklist de Conferência

Use este checklist para garantir que você tem tudo:

- [ ] `README.md` - Documentação principal
- [ ] `requirements.txt` - Dependências Python
- [ ] `CONTEUDO.md` - Este arquivo

**Código**:
- [ ] `codigo/nfse_search.py` - Sistema completo (1.506 linhas)

**Documentação**:
- [ ] `documentacao/ARQUITETURA.md` - Arquitetura (~800 linhas)
- [ ] `documentacao/DATABASE_SCHEMA.md` - Banco (~600 linhas)
- [ ] `documentacao/API_GUIDE.md` - APIs (~700 linhas)
- [ ] `documentacao/PROVIDERS.md` - Provedores (~400 linhas)
- [ ] `documentacao/WEB_MIGRATION.md` - Migração Web (~1.000 linhas)

**Banco de Dados**:
- [ ] `database/schema.sql` - Schema PostgreSQL (~400 linhas)
- [ ] `database/sample_data.sql` - Dados exemplo (~100 linhas)

**Exemplos**:
- [ ] `exemplos/exemplo_basico.py` - Busca simples (~150 linhas)
- [ ] `exemplos/exemplo_multiplos_municipios.py` - Multi-cidades (~250 linhas)
- [ ] `exemplos/exemplo_nuvem_fiscal.py` - REST API (~200 linhas)

**TOTAL**: ✅ 12 arquivos | ~5.800 linhas | 100% completo

---

## 🎉 Conclusão

Esta exportação contém **TUDO** necessário para:

✅ Entender o sistema atual de busca de NFS-e  
✅ Migrar para plataforma web moderna  
✅ Integrar com APIs SOAP e REST  
✅ Configurar banco de dados PostgreSQL  
✅ Implementar segurança e escalabilidade  
✅ Adicionar novos municípios e provedores  

**Boa sorte com a migração! 🚀**

---

*Exportação gerada em: 13 de Fevereiro de 2025*  
*Sistema: Busca de NFS-e v1.0*  
*Documentação: Completa*
