-- =====================================================
-- DADOS DE EXEMPLO - Sistema NFS-e
-- =====================================================
-- Este script insere dados de exemplo para testes
-- e desenvolvimento
-- =====================================================

-- =====================================================
-- CONFIGURAÇÕES DE ACESSO (nfse_config)
-- =====================================================

-- Empresa fictícia: Acme Ltda
-- CNPJ: 12345678000199

-- Configuração para Campo Grande/MS (GINFES)
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada, ativo)
VALUES (
    '12345678000199',
    'GINFES',
    '5002704',  -- Campo Grande/MS
    '12345',
    NULL,
    TRUE
);

-- Configuração para São Paulo/SP (ISS.NET)
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada, ativo)
VALUES (
    '12345678000199',
    'ISS.NET',
    '3550308',  -- São Paulo/SP
    '67890',
    'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx',
    TRUE
);

-- Configuração para Curitiba/PR (eISS)
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada, ativo)
VALUES (
    '12345678000199',
    'EISS',
    '4106902',  -- Curitiba/PR
    'ABC123',
    NULL,
    TRUE
);

-- Configuração inativa (exemplo de configuração desabilitada)
INSERT INTO nfse_config (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada, ativo)
VALUES (
    '12345678000199',
    'BETHA',
    '4205407',  -- Florianópolis/SC
    '54321',
    NULL,
    FALSE
);

-- =====================================================
-- NFS-e BAIXADAS (nfse_baixadas)
-- =====================================================

-- NFS-e de Janeiro/2025
INSERT INTO nfse_baixadas (
    numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, 
    valor_servico, provedor, codigo_municipio, situacao, numero_rps, serie_rps
) VALUES
(
    '12345', '12345678000199', '98765432000187', '2025-01-05 10:30:00',
    1500.00, 'GINFES', '5002704', 'NORMAL', '1001', '1'
),
(
    '12346', '12345678000199', '11223344000155', '2025-01-08 14:15:00',
    2300.50, 'GINFES', '5002704', 'NORMAL', '1002', '1'
),
(
    '12347', '12345678000199', '55667788000199', '2025-01-12 09:45:00',
    850.00, 'ISS.NET', '3550308', 'NORMAL', '1003', '1'
);

-- NFS-e de Fevereiro/2025
INSERT INTO nfse_baixadas (
    numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, 
    valor_servico, provedor, codigo_municipio, situacao, numero_rps, serie_rps
) VALUES
(
    '12348', '12345678000199', '98765432000187', '2025-02-03 11:00:00',
    1800.00, 'GINFES', '5002704', 'NORMAL', '1004', '1'
),
(
    '12349', '12345678000199', '22334455000166', '2025-02-10 16:30:00',
    3200.00, 'ISS.NET', '3550308', 'NORMAL', '1005', '1'
),
(
    '12350', '12345678000199', '11223344000155', '2025-02-15 10:00:00',
    1250.75, 'EISS', '4106902', 'NORMAL', '1006', '1'
);

-- NFS-e cancelada (exemplo)
INSERT INTO nfse_baixadas (
    numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, 
    valor_servico, provedor, codigo_municipio, situacao, numero_rps, serie_rps
) VALUES
(
    '12351', '12345678000199', '98765432000187', '2025-02-20 14:00:00',
    1000.00, 'GINFES', '5002704', 'CANCELADA', '1007', '1'
);

-- NFS-e com XML (exemplo simplificado)
INSERT INTO nfse_baixadas (
    numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, 
    valor_servico, xml_content, provedor, codigo_municipio, situacao
) VALUES
(
    '12352', '12345678000199', '55667788000199', '2025-02-25 09:30:00',
    4500.00, 
    '<?xml version="1.0" encoding="UTF-8"?>
<CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd">
  <Nfse>
    <InfNfse Id="NFS12352">
      <Numero>12352</Numero>
      <CodigoVerificacao>ABCD1234</CodigoVerificacao>
      <DataEmissao>2025-02-25T09:30:00</DataEmissao>
      <IdentificacaoRps>
        <Numero>1008</Numero>
        <Serie>1</Serie>
      </IdentificacaoRps>
      <PrestadorServico>
        <IdentificacaoPrestador>
          <Cnpj>12345678000199</Cnpj>
        </IdentificacaoPrestador>
      </PrestadorServico>
      <TomadorServico>
        <IdentificacaoTomador>
          <CpfCnpj>
            <Cnpj>55667788000199</Cnpj>
          </CpfCnpj>
        </IdentificacaoTomador>
      </TomadorServico>
      <ValoresNfse>
        <ValorServicos>4500.00</ValorServicos>
      </ValoresNfse>
    </InfNfse>
  </Nfse>
</CompNfse>',
    'GINFES', '5002704', 'NORMAL'
);

-- =====================================================
-- RPS (Recibos Provisórios)
-- =====================================================

-- RPS já convertido em NFS-e
INSERT INTO rps (
    numero_rps, serie_rps, cnpj_prestador, data_emissao, 
    status, numero_nfse, convertido_em
) VALUES
(
    '1001', '1', '12345678000199', '2025-01-05 10:30:00',
    'CONVERTIDO', '12345', '2025-01-05 10:35:00'
),
(
    '1002', '1', '12345678000199', '2025-01-08 14:15:00',
    'CONVERTIDO', '12346', '2025-01-08 14:20:00'
);

-- RPS pendentes (ainda não convertidos)
INSERT INTO rps (
    numero_rps, serie_rps, cnpj_prestador, data_emissao, 
    status, xml_rps
) VALUES
(
    '1009', '1', '12345678000199', '2025-02-28 15:00:00',
    'PENDENTE',
    '<?xml version="1.0"?>
<Rps>
  <InfDeclaracaoPrestacaoServico>
    <Rps>
      <IdentificacaoRps>
        <Numero>1009</Numero>
        <Serie>1</Serie>
      </IdentificacaoRps>
    </Rps>
    <Servico>
      <Valores>
        <ValorServicos>2500.00</ValorServicos>
      </Valores>
    </Servico>
  </InfDeclaracaoPrestacaoServico>
</Rps>'
),
(
    '1010', '1', '12345678000199', '2025-02-28 16:30:00',
    'PENDENTE',
    NULL
);

-- RPS com erro
INSERT INTO rps (
    numero_rps, serie_rps, cnpj_prestador, data_emissao, 
    status
) VALUES
(
    '1008', '1', '12345678000199', '2025-02-27 11:00:00',
    'ERRO'
);

-- =====================================================
-- CONTROLE DE NSU
-- =====================================================

-- NSU para a empresa exemplo
INSERT INTO nsu_nfse (informante, ult_nsu, atualizado_em)
VALUES (
    '12345678000199',
    150,
    CURRENT_TIMESTAMP
);

-- NSU para outro informante (tomador)
INSERT INTO nsu_nfse (informante, ult_nsu, atualizado_em)
VALUES (
    '98765432000187',
    75,
    CURRENT_TIMESTAMP - INTERVAL '2 days'
);

-- =====================================================
-- QUERIES DE TESTE
-- =====================================================

-- Para testar se os dados foram inseridos corretamente,
-- execute estas queries:

-- 1. Listar todas as configurações ativas
-- SELECT * FROM vw_config_ativa;

-- 2. Resumo por prestador
-- SELECT * FROM vw_resumo_prestador;

-- 3. RPS pendentes
-- SELECT * FROM vw_rps_pendentes;

-- 4. NFS-e do último mês
-- SELECT 
--     numero_nfse,
--     data_emissao,
--     valor_servico,
--     situacao
-- FROM nfse_baixadas
-- WHERE data_emissao >= CURRENT_DATE - INTERVAL '30 days'
-- ORDER BY data_emissao DESC;

-- 5. Total de NFS-e por município
-- SELECT 
--     codigo_municipio,
--     provedor,
--     COUNT(*) as total,
--     SUM(valor_servico) as valor_total
-- FROM nfse_baixadas
-- WHERE situacao = 'NORMAL'
-- GROUP BY codigo_municipio, provedor
-- ORDER BY total DESC;

-- 6. Usar função para buscar por período
-- SELECT * FROM buscar_nfse_periodo(
--     '12345678000199',
--     '2025-01-01',
--     '2025-01-31'
-- );

-- 7. Total mensal de 2025
-- SELECT * FROM total_nfse_mensal('12345678000199', 2025);

-- =====================================================
-- LIMPEZA (se necessário)
-- =====================================================

-- Para limpar todos os dados de exemplo:
-- DELETE FROM nsu_nfse WHERE informante IN ('12345678000199', '98765432000187');
-- DELETE FROM rps WHERE cnpj_prestador = '12345678000199';
-- DELETE FROM nfse_baixadas WHERE cnpj_prestador = '12345678000199';
-- DELETE FROM nfse_config WHERE cnpj_cpf = '12345678000199';

-- =====================================================
-- FIM DOS DADOS DE EXEMPLO
-- =====================================================
