# 🗄️ Esquema do Banco de Dados NFS-e

## Visão Geral

O sistema utiliza **SQLite** para persistência local de dados. Para ambiente web, recomenda-se migrar para **PostgreSQL** ou **MySQL**.

**Banco principal**: `notas.db` (compartilhado com sistema NF-e/CT-e)

---

## 📊 Tabelas NFS-e

### 1. nfse_config

**Propósito**: Armazena configurações de provedores NFS-e por CNPJ e município.

```sql
CREATE TABLE IF NOT EXISTS nfse_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_cpf TEXT NOT NULL,
    provedor TEXT NOT NULL,
    codigo_municipio TEXT,
    inscricao_municipal TEXT,
    url_customizada TEXT,
    ativo INTEGER DEFAULT 1,
    UNIQUE(cnpj_cpf, codigo_municipio)
);
```

#### Colunas

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `id` | INTEGER | Chave primária auto-incremento | 1 |
| `cnpj_cpf` | TEXT | CNPJ/CPF do prestador (sem formatação) | 12345678000199 |
| `provedor` | TEXT | Nome do provedor | GINFES, ISSNET, NUVEMFISCAL |
| `codigo_municipio` | TEXT | Código IBGE do município (7 dígitos) | 5002704 |
| `inscricao_municipal` | TEXT | Inscrição municipal do prestador | 12345 |
| `url_customizada` | TEXT | URL customizada (opcional) | https://customurl.com/ws |
| `ativo` | INTEGER | Flag ativo (1) ou inativo (0) | 1 |

#### Constraints

- **PRIMARY KEY**: `id`
- **UNIQUE**: `(cnpj_cpf, codigo_municipio)` - Um CNPJ não pode ter configuração duplicada para o mesmo município

#### Índices Recomendados

```sql
CREATE INDEX idx_nfse_config_cnpj ON nfse_config(cnpj_cpf);
CREATE INDEX idx_nfse_config_ativo ON nfse_config(ativo);
CREATE INDEX idx_nfse_config_municipio ON nfse_config(codigo_municipio);
```

#### Queries Comuns

```sql
-- Buscar configurações ativas de um CNPJ
SELECT provedor, codigo_municipio, inscricao_municipal, url_customizada
FROM nfse_config
WHERE cnpj_cpf = '12345678000199' AND ativo = 1;

-- Listar todos os municípios configurados
SELECT DISTINCT codigo_municipio, COUNT(*) as total_empresas
FROM nfse_config
WHERE ativo = 1
GROUP BY codigo_municipio
ORDER BY total_empresas DESC;

-- Buscar empresas que usam determinado provedor
SELECT cnpj_cpf, codigo_municipio
FROM nfse_config
WHERE provedor = 'GINFES' AND ativo = 1;
```

---

### 2. nfse_baixadas

**Propósito**: Armazena todas as NFS-e já baixadas do sistema.

```sql
CREATE TABLE IF NOT EXISTS nfse_baixadas (
    numero_nfse TEXT PRIMARY KEY,
    cnpj_prestador TEXT,
    cnpj_tomador TEXT,
    data_emissao TEXT,
    valor_servico REAL,
    xml_content TEXT,
    data_download TEXT
);
```

#### Colunas

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `numero_nfse` | TEXT | Número da NFS-e (chave primária) | 123456 |
| `cnpj_prestador` | TEXT | CNPJ do prestador (emitente) | 12345678000199 |
| `cnpj_tomador` | TEXT | CNPJ do tomador (cliente) | 98765432000100 |
| `data_emissao` | TEXT | Data de emissão (ISO 8601) | 2025-01-15T10:30:00 |
| `valor_servico` | REAL | Valor total do serviço | 1500.00 |
| `xml_content` | TEXT | XML completo da NFS-e | `<CompNfse>...</CompNfse>` |
| `data_download` | TEXT | Data/hora do download (ISO 8601) | 2025-01-13T14:25:30 |

#### Constraints

- **PRIMARY KEY**: `numero_nfse`

#### Índices Recomendados

```sql
CREATE INDEX idx_nfse_baixadas_prestador ON nfse_baixadas(cnpj_prestador);
CREATE INDEX idx_nfse_baixadas_tomador ON nfse_baixadas(cnpj_tomador);
CREATE INDEX idx_nfse_baixadas_data_emissao ON nfse_baixadas(data_emissao);
CREATE INDEX idx_nfse_baixadas_data_download ON nfse_baixadas(data_download);
```

#### Queries Comuns

```sql
-- Buscar todas as NFS-e de um prestador
SELECT numero_nfse, cnpj_tomador, data_emissao, valor_servico
FROM nfse_baixadas
WHERE cnpj_prestador = '12345678000199'
ORDER BY data_emissao DESC;

-- Total de serviços prestados em um período
SELECT 
    cnpj_prestador,
    COUNT(*) as total_notas,
    SUM(valor_servico) as valor_total
FROM nfse_baixadas
WHERE data_emissao BETWEEN '2025-01-01' AND '2025-01-31'
GROUP BY cnpj_prestador;

-- Buscar NFS-e por tomador
SELECT numero_nfse, data_emissao, valor_servico
FROM nfse_baixadas
WHERE cnpj_tomador = '98765432000100'
ORDER BY data_emissao DESC;

-- NFS-e mais recentes baixadas
SELECT numero_nfse, cnpj_prestador, data_ emissao, data_download
FROM nfse_baixadas
ORDER BY data_download DESC
LIMIT 10;
```

---

### 3. rps

**Propósito**: Armazena Recibos Provisórios de Serviço (RPS convertidos em NFS-e).

```sql
CREATE TABLE IF NOT EXISTS rps (
    numero_rps TEXT,
    serie_rps TEXT,
    cnpj_prestador TEXT,
    data_emissao TEXT,
    status TEXT,
    numero_nfse TEXT,
    PRIMARY KEY (numero_rps, serie_rps, cnpj_prestador)
);
```

#### Colunas

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `numero_rps` | TEXT | Número do RPS | 1001 |
| `serie_rps` | TEXT | Série do RPS | A1 |
| `cnpj_prestador` | TEXT | CNPJ do prestador | 12345678000199 |
| `data_emissao` | TEXT | Data de emissão do RPS | 2025-01-15 |
| `status` | TEXT | Status do RPS | CONVERTIDO, PENDENTE, CANCELADO |
| `numero_nfse` | TEXT | Número da NFS-e gerada (após conversão) | 123456 |

#### Constraints

- **PRIMARY KEY**: `(numero_rps, serie_rps, cnpj_prestador)` - Composta

#### Índices Recomendados

```sql
CREATE INDEX idx_rps_prestador ON rps(cnpj_prestador);
CREATE INDEX idx_rps_status ON rps(status);
CREATE INDEX idx_rps_nfse ON rps(numero_nfse);
```

#### Queries Comuns

```sql
-- Buscar RPS de um prestador
SELECT numero_rps, serie_rps, data_emissao, status, numero_nfse
FROM rps
WHERE cnpj_prestador = '12345678000199'
ORDER BY data_emissao DESC;

-- RPS ainda não convertidos
SELECT numero_rps, serie_rps, data_emissao
FROM rps
WHERE status = 'PENDENTE' AND cnpj_prestador = '12345678000199';

-- Verificar se RPS já foi convertido
SELECT numero_nfse
FROM rps
WHERE numero_rps = '1001' 
  AND serie_rps = 'A1' 
  AND cnpj_prestador = '12345678000199';
```

---

### 4. nsu_nfse

**Propósito**: Controle de NSU (Número Sequencial Único) para distribuição de NFS-e.

```sql
CREATE TABLE IF NOT EXISTS nsu_nfse (
    informante TEXT PRIMARY KEY,
    ult_nsu INTEGER DEFAULT 0,
    atualizado_em TEXT
);
```

#### Colunas

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `informante` | TEXT | CNPJ do informante (chave primária) | 12345678000199 |
| `ult_nsu` | INTEGER | Último NSU processado | 150 |
| `atualizado_em` | TEXT | Data/hora da última atualização | 2025-01-13T14:25:30 |

#### Constraints

- **PRIMARY KEY**: `informante`

#### Queries Comuns

```sql
-- Obter último NSU de um informante
SELECT ult_nsu
FROM nsu_nfse
WHERE informante = '12345678000199';

-- Atualizar NSU
INSERT OR REPLACE INTO nsu_nfse (informante, ult_nsu, atualizado_em)
VALUES ('12345678000199', 151, datetime('now'));

-- Listar todos os informantes e seus NSUs
SELECT informante, ult_nsu, atualizado_em
FROM nsu_nfse
ORDER BY atualizado_em DESC;
```

---

## 🔗 Relacionamentos

### Diagrama ER

```
┌─────────────────────┐
│   certificados      │ (tabela do sistema principal)
│   (sistema pai)     │
│                     │
│  ○ cnpj_cpf (PK)    │
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
│  ○ id (PK)          │
│  ● cnpj_cpf (FK)    │───┐
│  • provedor         │   │
│  • codigo_municipio │   │
│  • inscricao_mun    │   │
│  • url_customizada  │   │
│  • ativo            │   │
└──────────┬──────────┘   │
           │              │
           │ 1            │
           │              │
           │ N            │
┌──────────▼──────────┐   │
│  nfse_baixadas      │   │
│                     │   │
│  ○ numero_nfse (PK) │   │
│  ● cnpj_prestador◄──┼───┘
│  • cnpj_tomador     │
│  • data_emissao     │
│  • valor_servico    │
│  • xml_content      │
│  • data_download    │
└─────────────────────┘

┌─────────────────────┐
│   rps               │
│                     │
│  ○ numero_rps (PK)  │
│  ○ serie_rps (PK)   │
│  ○ cnpj_prestador(PK)│
│  • data_emissao     │
│  • status           │
│  • numero_nfse      │──┐ (referência lógica)
└─────────────────────┘  │
                         │
                         ▼
              ┌─────────────────────┐
              │  nfse_baixadas      │
              │  numero_nfse        │
              └─────────────────────┘

┌─────────────────────┐
│   nsu_nfse          │
│                     │
│  ○ informante (PK)  │◄─── (referência lógica a cnpj_cpf)
│  • ult_nsu          │
│  • atualizado_em    │
└─────────────────────┘
```

### Legenda

- ○ = PRIMARY KEY
- ● = FOREIGN KEY (relação lógica, sem FK constraint no SQLite)
- • = Campo comum

---

## 🔄 Migração para PostgreSQL/MySQL

### Script de Migração (PostgreSQL)

```sql
-- Tabela nfse_config
CREATE TABLE nfse_config (
    id SERIAL PRIMARY KEY,
    cnpj_cpf VARCHAR(14) NOT NULL,
    provedor VARCHAR(50) NOT NULL,
    codigo_municipio VARCHAR(7),
    inscricao_municipal VARCHAR(50),
    url_customizada VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cnpj_cpf, codigo_municipio)
);

CREATE INDEX idx_nfse_config_cnpj ON nfse_config(cnpj_cpf);
CREATE INDEX idx_nfse_config_ativo ON nfse_config(ativo);
CREATE INDEX idx_nfse_config_municipio ON nfse_config(codigo_municipio);

-- Tabela nfse_baixadas
CREATE TABLE nfse_baixadas (
    numero_nfse VARCHAR(50) PRIMARY KEY,
    cnpj_prestador VARCHAR(14) NOT NULL,
    cnpj_tomador VARCHAR(14),
    data_emissao TIMESTAMP NOT NULL,
    valor_servico NUMERIC(15, 2) NOT NULL,
    xml_content TEXT,
    data_download TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nfse_baixadas_prestador ON nfse_baixadas(cnpj_prestador);
CREATE INDEX idx_nfse_baixadas_tomador ON nfse_baixadas(cnpj_tomador);
CREATE INDEX idx_nfse_baixadas_data_emissao ON nfse_baixadas(data_emissao);
CREATE INDEX idx_nfse_baixadas_data_download ON nfse_baixadas(data_download);

-- Tabela rps
CREATE TABLE rps (
    numero_rps VARCHAR(50),
    serie_rps VARCHAR(10),
    cnpj_prestador VARCHAR(14),
    data_emissao TIMESTAMP,
    status VARCHAR(20),
    numero_nfse VARCHAR(50),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (numero_rps, serie_rps, cnpj_prestador)
);

CREATE INDEX idx_rps_prestador ON rps(cnpj_prestador);
CREATE INDEX idx_rps_status ON rps(status);
CREATE INDEX idx_rps_nfse ON rps(numero_nfse);

-- Tabela nsu_nfse
CREATE TABLE nsu_nfse (
    informante VARCHAR(14) PRIMARY KEY,
    ult_nsu BIGINT DEFAULT 0,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para atualizar atualizado_em automaticamente
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_nfse_config_modtime
    BEFORE UPDATE ON nfse_config
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_rps_modtime
    BEFORE UPDATE ON rps
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();
```

### Diferenças SQLite vs PostgreSQL

| Recurso | SQLite | PostgreSQL |
|---------|--------|------------|
| **Tipo INTEGER PK** | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| **Boolean** | `INTEGER` (0/1) | `BOOLEAN` |
| **Timestamp** | `TEXT` (ISO 8601) | `TIMESTAMP` |
| **Decimal** | `REAL` | `NUMERIC(precision, scale)` |
| **Triggers** | Suportado | Suportado (mais robusto) |
| **Foreign Keys** | Opcional (precisa habilitar) | Padrão |

---

## 📈 Views Úteis

### View: Resumo de NFS-e por Prestador

```sql
CREATE VIEW vw_nfse_resumo_prestador AS
SELECT 
    n.cnpj_prestador,
    COUNT(*) as total_notas,
    SUM(n.valor_servico) as valor_total,
    MIN(n.data_emissao) as primeira_nota,
    MAX(n.data_emissao) as ultima_nota,
    AVG(n.valor_servico) as valor_medio
FROM nfse_baixadas n
GROUP BY n.cnpj_prestador;
```

### View: Configurações Ativas com Detalhes

```sql
CREATE VIEW vw_nfse_config_ativa AS
SELECT 
    c.id,
    c.cnpj_cpf,
    c.provedor,
    c.codigo_municipio,
    c.inscricao_municipal,
    c.url_customizada,
    COUNT(n.numero_nfse) as total_nfse_baixadas
FROM nfse_config c
LEFT JOIN nfse_baixadas n ON c.cnpj_cpf = n.cnpj_prestador
WHERE c.ativo = 1
GROUP BY c.id, c.cnpj_cpf, c.provedor, c.codigo_municipio, c.inscricao_municipal, c.url_customizada;
```

### View: RPS Pendentes de Conversão

```sql
CREATE VIEW vw_rps_pendentes AS
SELECT 
    r.numero_rps,
    r.serie_rps,
    r.cnpj_prestador,
    r.data_emissao,
    julianday('now') - julianday(r.data_emissao) as dias_pendente
FROM rps r
WHERE r.status = 'PENDENTE'
ORDER BY r.data_emissao;
```

---

## 🔍 Queries Avançadas

### Total de NFS-e por Município

```sql
SELECT 
    c.codigo_municipio,
    COUNT(DISTINCT n.numero_nfse) as total_nfse,
    SUM(n.valor_servico) as valor_total,
    COUNT(DISTINCT n.cnpj_prestador) as total_prestadores
FROM nfse_config c
LEFT JOIN nfse_baixadas n ON c.cnpj_cpf = n.cnpj_prestador
WHERE c.ativo = 1
GROUP BY c.codigo_municipio
ORDER BY total_nfse DESC;
```

### Análise de Prestadores Mais Ativos

```sql
SELECT 
    n.cnpj_prestador,
    COUNT(*) as total_notas,
    SUM(n.valor_servico) as valor_total,
    AVG(n.valor_servico) as ticket_medio,
    MIN(n.data_emissao) as primeira_emissao,
    MAX(n.data_emissao) as ultima_emissao
FROM nfse_baixadas n
WHERE n.data_emissao >= date('now', '-30 days')
GROUP BY n.cnpj_prestador
HAVING COUNT(*) > 10
ORDER BY total_notas DESC
LIMIT 10;
```

### Detecção de Duplicatas

```sql
-- Buscar NFS-e com mesmo número (possível duplicata)
SELECT numero_nfse, COUNT(*) as duplicatas
FROM nfse_baixadas
GROUP BY numero_nfse
HAVING COUNT(*) > 1;

-- Buscar configurações duplicadas (não deveria existir por UNIQUE constraint)
SELECT cnpj_cpf, codigo_municipio, COUNT(*) as duplicatas
FROM nfse_config
GROUP BY cnpj_cpf, codigo_municipio
HAVING COUNT(*) > 1;
```

---

## 🛡️ Segurança e Auditoria

### Tabela de Auditoria (Recomendada para Web)

```sql
CREATE TABLE nfse_audit_log (
    id SERIAL PRIMARY KEY,
    tabela VARCHAR(50) NOT NULL,
    operacao VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    registro_id VARCHAR(100),
    usuario_id INTEGER,
    dados_antigos JSONB,
    dados_novos JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_tabela ON nfse_audit_log(tabela);
CREATE INDEX idx_audit_usuario ON nfse_audit_log(usuario_id);
CREATE INDEX idx_audit_criado_em ON nfse_audit_log(criado_em);
```

### Trigger de Auditoria (PostgreSQL)

```sql
CREATE OR REPLACE FUNCTION audit_nfse_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO nfse_audit_log (tabela, operacao, registro_id, dados_antigos)
        VALUES (TG_TABLE_NAME, 'DELETE', OLD.numero_nfse, row_to_json(OLD));
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO nfse_audit_log (tabela, operacao, registro_id, dados_antigos, dados_novos)
        VALUES (TG_TABLE_NAME, 'UPDATE', NEW.numero_nfse, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO nfse_audit_log (tabela, operacao, registro_id, dados_novos)
        VALUES (TG_TABLE_NAME, 'INSERT', NEW.numero_nfse, row_to_json(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_nfse_baixadas
    AFTER INSERT OR UPDATE OR DELETE ON nfse_baixadas
    FOR EACH ROW EXECUTE FUNCTION audit_nfse_changes();
```

---

## 📊 Estatísticas e Monitoramento

### Tamanho das Tabelas (SQLite)

```sql
SELECT 
    name as tabela,
    SUM(pgsize) / 1024 / 1024 as tamanho_mb
FROM dbstat
WHERE name IN ('nfse_config', 'nfse_baixadas', 'rps', 'nsu_nfse')
GROUP BY name
ORDER BY tamanho_mb DESC;
```

### Crescimento do Banco (PostgreSQL)

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public' AND tablename LIKE 'nfse%'
ORDER BY size_bytes DESC;
```

---

## 🔧 Manutenção

### Limpeza de Dados Antigos (SQLite)

```sql
-- Deletar NFS-e com mais de 5 anos
DELETE FROM nfse_baixadas
WHERE data_emissao < date('now', '-5 years');

-- Desativar configurações não usadas há mais de 1 ano
UPDATE nfse_config
SET ativo = 0
WHERE cnpj_cpf NOT IN (
    SELECT DISTINCT cnpj_prestador
    FROM nfse_baixadas
    WHERE data_download >= date('now', '-1 year')
);

-- Vacuum para recuperar espaço
VACUUM;
```

### Reindexação (PostgreSQL)

```sql
-- Reindexar todas as tabelas NFS-e
REINDEX TABLE nfse_config;
REINDEX TABLE nfse_baixadas;
REINDEX TABLE rps;
REINDEX TABLE nsu_nfse;

-- Atualizar estatísticas do query planner
ANALYZE nfse_config;
ANALYZE nfse_baixadas;
ANALYZE rps;
ANALYZE nsu_nfse;
```

---

## 📚 Referências

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)

---

**Próximos Passos**

Para mais informações, consulte:
- [ARQUITETURA.md](ARQUITETURA.md) - Arquitetura do sistema
- [API_GUIDE.md](API_GUIDE.md) - APIs e integrações
- [WEB_MIGRATION.md](WEB_MIGRATION.md) - Migração para web
