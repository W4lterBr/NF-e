-- =====================================================
-- SCHEMA NFS-e - PostgreSQL
-- =====================================================
-- Este script cria todas as tabelas necessárias para o
-- sistema de busca e armazenamento de NFS-e
-- =====================================================

-- Remover tabelas se existirem (apenas para desenvolvimento)
-- DROP TABLE IF EXISTS nsu_nfse CASCADE;
-- DROP TABLE IF EXISTS rps CASCADE;
-- DROP TABLE IF EXISTS nfse_baixadas CASCADE;
-- DROP TABLE IF EXISTS nfse_config CASCADE;

-- =====================================================
-- TABELA: nfse_config
-- =====================================================
-- Armazena configurações de acesso aos provedores de NFS-e
-- por CNPJ/CPF e município
-- =====================================================

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
    
    -- Constraint: Um CNPJ/CPF só pode ter uma configuração por município
    CONSTRAINT uk_nfse_config_cnpj_municipio UNIQUE (cnpj_cpf, codigo_municipio)
);

-- Índices para performance
CREATE INDEX idx_nfse_config_cnpj ON nfse_config(cnpj_cpf);
CREATE INDEX idx_nfse_config_provedor ON nfse_config(provedor);
CREATE INDEX idx_nfse_config_municipio ON nfse_config(codigo_municipio);
CREATE INDEX idx_nfse_config_ativo ON nfse_config(ativo);

-- Comentários
COMMENT ON TABLE nfse_config IS 'Configurações de acesso aos provedores NFS-e';
COMMENT ON COLUMN nfse_config.cnpj_cpf IS 'CNPJ ou CPF do prestador (sem formatação)';
COMMENT ON COLUMN nfse_config.provedor IS 'Nome do provedor (GINFES, ISS.NET, etc)';
COMMENT ON COLUMN nfse_config.codigo_municipio IS 'Código IBGE do município (7 dígitos)';
COMMENT ON COLUMN nfse_config.inscricao_municipal IS 'Inscrição municipal do prestador';
COMMENT ON COLUMN nfse_config.url_customizada IS 'URL customizada do webservice (opcional)';

-- =====================================================
-- TABELA: nfse_baixadas
-- =====================================================
-- Armazena as NFS-e baixadas dos provedores
-- =====================================================

CREATE TABLE nfse_baixadas (
    numero_nfse VARCHAR(50) PRIMARY KEY,
    cnpj_prestador VARCHAR(14) NOT NULL,
    cnpj_tomador VARCHAR(14),
    data_emissao TIMESTAMP NOT NULL,
    valor_servico NUMERIC(15, 2) NOT NULL,
    xml_content TEXT,
    data_download TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provedor VARCHAR(50),
    codigo_municipio VARCHAR(7),
    situacao VARCHAR(20) DEFAULT 'NORMAL',
    numero_rps VARCHAR(50),
    serie_rps VARCHAR(5),
    
    -- Constraints
    CONSTRAINT chk_valor_positivo CHECK (valor_servico >= 0)
);

-- Índices para queries comuns
CREATE INDEX idx_nfse_cnpj_prestador ON nfse_baixadas(cnpj_prestador);
CREATE INDEX idx_nfse_cnpj_tomador ON nfse_baixadas(cnpj_tomador);
CREATE INDEX idx_nfse_data_emissao ON nfse_baixadas(data_emissao);
CREATE INDEX idx_nfse_provedor ON nfse_baixadas(provedor);
CREATE INDEX idx_nfse_municipio ON nfse_baixadas(codigo_municipio);
CREATE INDEX idx_nfse_situacao ON nfse_baixadas(situacao);

-- Índice composto para relatórios por período
CREATE INDEX idx_nfse_prestador_data ON nfse_baixadas(cnpj_prestador, data_emissao DESC);

-- Comentários
COMMENT ON TABLE nfse_baixadas IS 'NFS-e baixadas dos provedores';
COMMENT ON COLUMN nfse_baixadas.numero_nfse IS 'Número da NFS-e (chave primária)';
COMMENT ON COLUMN nfse_baixadas.situacao IS 'Situação da nota: NORMAL, CANCELADA, SUBSTITUIDA';
COMMENT ON COLUMN nfse_baixadas.xml_content IS 'Conteúdo XML completo da NFS-e';

-- =====================================================
-- TABELA: rps
-- =====================================================
-- Armazena RPS (Recibo Provisório de Serviços)
-- que ainda não foram convertidos em NFS-e
-- =====================================================

CREATE TABLE rps (
    numero_rps VARCHAR(50) NOT NULL,
    serie_rps VARCHAR(5) DEFAULT '1' NOT NULL,
    cnpj_prestador VARCHAR(14) NOT NULL,
    data_emissao TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    numero_nfse VARCHAR(50),
    xml_rps TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    convertido_em TIMESTAMP,
    
    -- Chave primária composta
    PRIMARY KEY (numero_rps, serie_rps, cnpj_prestador),
    
    -- Foreign key para NFS-e (se já foi convertido)
    CONSTRAINT fk_rps_nfse FOREIGN KEY (numero_nfse) 
        REFERENCES nfse_baixadas(numero_nfse)
        ON DELETE SET NULL
);

-- Índices
CREATE INDEX idx_rps_prestador ON rps(cnpj_prestador);
CREATE INDEX idx_rps_status ON rps(status);
CREATE INDEX idx_rps_data ON rps(data_emissao);
CREATE INDEX idx_rps_nfse ON rps(numero_nfse);

-- Comentários
COMMENT ON TABLE rps IS 'Recibos Provisórios de Serviços (RPS)';
COMMENT ON COLUMN rps.status IS 'Status: PENDENTE, CONVERTIDO, ERRO';
COMMENT ON COLUMN rps.numero_nfse IS 'Número da NFS-e gerada (quando convertido)';

-- =====================================================
-- TABELA: nsu_nfse
-- =====================================================
-- Controle de NSU (Número Sequencial Único) para
-- distribuição de NFS-e via ADN/SEFAZ
-- =====================================================

CREATE TABLE nsu_nfse (
    informante VARCHAR(14) PRIMARY KEY,
    ult_nsu BIGINT DEFAULT 0,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Comentários
COMMENT ON TABLE nsu_nfse IS 'Controle de NSU para distribuição NFS-e';
COMMENT ON COLUMN nsu_nfse.informante IS 'CNPJ/CPF do informante (prestador ou tomador)';
COMMENT ON COLUMN nsu_nfse.ult_nsu IS 'Último NSU processado';

-- =====================================================
-- VIEWS ÚTEIS
-- =====================================================

-- View: Resumo por prestador
CREATE OR REPLACE VIEW vw_resumo_prestador AS
SELECT 
    cnpj_prestador,
    COUNT(*) as total_notas,
    SUM(valor_servico) as valor_total,
    MIN(data_emissao) as primeira_nota,
    MAX(data_emissao) as ultima_nota,
    COUNT(DISTINCT codigo_municipio) as total_municipios
FROM nfse_baixadas
WHERE situacao = 'NORMAL'
GROUP BY cnpj_prestador;

COMMENT ON VIEW vw_resumo_prestador IS 'Resumo de NFS-e por prestador';

-- View: Configurações ativas
CREATE OR REPLACE VIEW vw_config_ativa AS
SELECT 
    cnpj_cpf,
    provedor,
    codigo_municipio,
    inscricao_municipal,
    url_customizada
FROM nfse_config
WHERE ativo = TRUE;

COMMENT ON VIEW vw_config_ativa IS 'Configurações ativas de acesso aos provedores';

-- View: RPS pendentes
CREATE OR REPLACE VIEW vw_rps_pendentes AS
SELECT 
    numero_rps,
    serie_rps,
    cnpj_prestador,
    data_emissao,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - data_emissao) as dias_pendente
FROM rps
WHERE status = 'PENDENTE';

COMMENT ON VIEW vw_rps_pendentes IS 'RPS ainda não convertidos em NFS-e';

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Trigger: Atualizar timestamp de modificação
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em nfse_config
CREATE TRIGGER update_nfse_config_modtime
    BEFORE UPDATE ON nfse_config
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- Aplicar trigger em nsu_nfse
CREATE TRIGGER update_nsu_nfse_modtime
    BEFORE UPDATE ON nsu_nfse
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- =====================================================
-- AUDITORIA (OPCIONAL - RECOMENDADO PARA PRODUÇÃO)
-- =====================================================

-- Tabela de auditoria
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    tabela VARCHAR(50) NOT NULL,
    operacao VARCHAR(10) NOT NULL,
    usuario VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dados_antigos JSONB,
    dados_novos JSONB
);

CREATE INDEX idx_audit_log_tabela ON audit_log(tabela);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);

COMMENT ON TABLE audit_log IS 'Log de auditoria de todas as operações';

-- Função genérica de auditoria
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO audit_log (tabela, operacao, dados_antigos)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD));
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO audit_log (tabela, operacao, dados_antigos, dados_novos)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (tabela, operacao, dados_novos)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Aplicar auditoria em nfse_config
CREATE TRIGGER audit_nfse_config
    AFTER INSERT OR UPDATE OR DELETE ON nfse_config
    FOR EACH ROW EXECUTE FUNCTION audit_trigger();

-- Aplicar auditoria em nfse_baixadas
CREATE TRIGGER audit_nfse_baixadas
    AFTER INSERT OR UPDATE OR DELETE ON nfse_baixadas
    FOR EACH ROW EXECUTE FUNCTION audit_trigger();

-- =====================================================
-- FUNÇÕES ÚTEIS
-- =====================================================

-- Função: Buscar NFS-e por período
CREATE OR REPLACE FUNCTION buscar_nfse_periodo(
    p_cnpj VARCHAR(14),
    p_data_inicial DATE,
    p_data_final DATE
)
RETURNS TABLE (
    numero_nfse VARCHAR(50),
    data_emissao TIMESTAMP,
    valor_servico NUMERIC(15,2),
    tomador_cnpj VARCHAR(14)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.numero_nfse,
        n.data_emissao,
        n.valor_servico,
        n.cnpj_tomador
    FROM nfse_baixadas n
    WHERE n.cnpj_prestador = p_cnpj
      AND n.data_emissao >= p_data_inicial
      AND n.data_emissao <= p_data_final
      AND n.situacao = 'NORMAL'
    ORDER BY n.data_emissao DESC;
END;
$$ LANGUAGE plpgsql;

-- Função: Total de NFS-e por mês
CREATE OR REPLACE FUNCTION total_nfse_mensal(
    p_cnpj VARCHAR(14),
    p_ano INTEGER
)
RETURNS TABLE (
    mes INTEGER,
    total_notas BIGINT,
    valor_total NUMERIC(15,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(MONTH FROM data_emissao)::INTEGER as mes,
        COUNT(*) as total_notas,
        SUM(valor_servico) as valor_total
    FROM nfse_baixadas
    WHERE cnpj_prestador = p_cnpj
      AND EXTRACT(YEAR FROM data_emissao) = p_ano
      AND situacao = 'NORMAL'
    GROUP BY EXTRACT(MONTH FROM data_emissao)
    ORDER BY mes;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- DADOS INICIAIS (OPCIONAL)
-- =====================================================

-- Inserir provedores conhecidos (pode ser útil para documentação)
-- Descomente se desejar popular com dados de exemplo

-- =====================================================
-- FIM DO SCHEMA
-- =====================================================
