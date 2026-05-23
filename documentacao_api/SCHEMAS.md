# 📊 Schemas e Estruturas de Dados

## Banco de Dados SQLite

### Tabela: `notas_detalhadas`

```sql
CREATE TABLE notas_detalhadas (
    -- Identificação
    chave TEXT PRIMARY KEY,
    numero TEXT,
    serie TEXT,
    tipo TEXT,                    -- 'NFe', 'CTe', 'NFSe'
    modelo TEXT,                  -- '55' (NFe), '57' (CTe)
    
    -- Datas
    data_emissao TEXT,
    data_saida TEXT,
    hora_saida TEXT,
    
    -- Emitente
    cnpj_emitente TEXT,
    nome_emitente TEXT,
    fantasia_emitente TEXT,
    uf_emitente TEXT,
    municipio_emitente TEXT,
    
    -- Destinatário
    cnpj_destinatario TEXT,
    nome_destinatario TEXT,
    uf_destinatario TEXT,
    municipio_destinatario TEXT,
    
    -- Valores Fiscais
    valor REAL,
    base_calculo REAL,
    valor_icms REAL,
    valor_ipi REAL,
    valor_pis REAL,
    valor_cofins REAL,
    valor_ibs REAL,
    valor_cbs REAL,
    
    -- Valores Adicionais
    valor_produtos REAL,
    valor_frete REAL,
    valor_seguro REAL,
    valor_desconto REAL,
    valor_outros REAL,
    
    -- Fiscal
    cfop TEXT,
    natureza_operacao TEXT,
    tipo_nf TEXT,
    finalidade_nf TEXT,
    
    -- Status
    status TEXT,
    status_motivo TEXT,
    xml_status TEXT,              -- 'COMPLETO', 'RESUMO', 'CANCELADO'
    
    -- Controle
    informante TEXT,
    nsu TEXT,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX idx_cnpj_emitente ON notas_detalhadas(cnpj_emitente);
CREATE INDEX idx_cnpj_destinatario ON notas_detalhadas(cnpj_destinatario);
CREATE INDEX idx_data_emissao ON notas_detalhadas(data_emissao);
CREATE INDEX idx_informante ON notas_detalhadas(informante);
CREATE INDEX idx_tipo ON notas_detalhadas(tipo);
CREATE INDEX idx_nsu ON notas_detalhadas(nsu);
```

### Tabela: `certificados`

```sql
CREATE TABLE certificados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_cpf TEXT UNIQUE NOT NULL,
    caminho TEXT NOT NULL,
    senha TEXT,                    -- Criptografada
    informante TEXT NOT NULL,      -- CNPJ principal
    cUF_autor INTEGER,             -- UF do certificado
    nome_certificado TEXT,         -- Nome amigável (ex: "61-MATPARCG")
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela: `nsu`

```sql
CREATE TABLE nsu (
    informante TEXT PRIMARY KEY,
    ultimo_nsu TEXT NOT NULL,
    max_nsu_conhecido TEXT,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela: `xmls_baixados`

```sql
CREATE TABLE xmls_baixados (
    chave TEXT NOT NULL,
    cnpj_cpf TEXT NOT NULL,
    caminho_arquivo TEXT,          -- Caminho completo do XML
    xml_completo TEXT,             -- XML armazenado (opcional)
    baixado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (chave, cnpj_cpf)
);
```

### Tabela: `perfis_armazenamento`

```sql
CREATE TABLE perfis_armazenamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    pasta_base TEXT NOT NULL,
    formato_pasta_mes TEXT DEFAULT 'AAAA-MM',
    xml_pdf_separado INTEGER DEFAULT 1,
    organizacao_tipo TEXT DEFAULT 'CERTIFICADO_TIPO',
    ativo INTEGER DEFAULT 1,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Estruturas XML

### NF-e Completa (procNFe)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe50260101773924000193550010000173831950403658" versao="4.00">
      
      <!-- Identificação -->
      <ide>
        <cUF>50</cUF>
        <cNF>95040365</cNF>
        <natOp>VENDA DE MERCADORIA</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>17383</nNF>
        <dhEmi>2026-02-13T17:30:00-04:00</dhEmi>
        <dhSaiEnt>2026-02-13T17:30:00-04:00</dhSaiEnt>
        <tpNF>1</tpNF>
        <idDest>2</idDest>
        <cMunFG>5002704</cMunFG>
        <tpImp>1</tpImp>
        <tpEmis>1</tpEmis>
        <cDV>8</cDV>
        <tpAmb>1</tpAmb>
        <finNFe>1</finNFe>
        <indFinal>0</indFinal>
        <indPres>1</indPres>
        <procEmi>0</procEmi>
        <verProc>4.0.0</verProc>
      </ide>
      
      <!-- Emitente -->
      <emit>
        <CNPJ>01773924000193</CNPJ>
        <xNome>ALFA COMPUTADORES LTDA</xNome>
        <xFant>ALFA COMPUTADORES</xFant>
        <enderEmit>
          <xLgr>RUA DAS FLORES</xLgr>
          <nro>123</nro>
          <xBairro>CENTRO</xBairro>
          <cMun>5002704</cMun>
          <xMun>CAMPO GRANDE</xMun>
          <UF>MS</UF>
          <CEP>79002001</CEP>
          <cPais>1058</cPais>
          <xPais>BRASIL</xPais>
          <fone>6733211234</fone>
        </enderEmit>
        <IE>283456789</IE>
        <CRT>3</CRT>
      </emit>
      
      <!-- Destinatário -->
      <dest>
        <CNPJ>33251845000109</CNPJ>
        <xNome>EMPRESA XPTO LTDA</xNome>
        <enderDest>
          <xLgr>AV PAULISTA</xLgr>
          <nro>1000</nro>
          <xBairro>BELA VISTA</xBairro>
          <cMun>3550308</cMun>
          <xMun>SAO PAULO</xMun>
          <UF>SP</UF>
          <CEP>01310100</CEP>
          <cPais>1058</cPais>
          <xPais>BRASIL</xPais>
        </enderDest>
        <indIEDest>1</indIEDest>
        <IE>123456789012</IE>
        <email>contato@xpto.com.br</email>
      </dest>
      
      <!-- Produtos -->
      <det nItem="1">
        <prod>
          <cProd>001</cProd>
          <cEAN>7891234567890</cEAN>
          <xProd>NOTEBOOK DELL INSPIRON 15</xProd>
          <NCM>84713012</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>10.0000</qCom>
          <vUnCom>5000.00</vUnCom>
          <vProd>50000.00</vProd>
          <cEANTrib>7891234567890</cEANTrib>
          <uTrib>UN</uTrib>
          <qTrib>10.0000</qTrib>
          <vUnTrib>5000.00</vUnTrib>
          <indTot>1</indTot>
        </prod>
        
        <imposto>
          <ICMS>
            <ICMS00>
              <orig>0</orig>
              <CST>00</CST>
              <modBC>0</modBC>
              <vBC>50000.00</vBC>
              <pICMS>12.00</pICMS>
              <vICMS>6000.00</vICMS>
            </ICMS00>
          </ICMS>
          
          <PIS>
            <PISAliq>
              <CST>01</CST>
              <vBC>50000.00</vBC>
              <pPIS>0.83</pPIS>
              <vPIS>412.50</vPIS>
            </PISAliq>
          </PIS>
          
          <COFINS>
            <COFINSAliq>
              <CST>01</CST>
              <vBC>50000.00</vBC>
              <pCOFINS>3.80</pCOFINS>
              <vCOFINS>1900.00</vCOFINS>
            </COFINSAliq>
          </COFINS>
        </imposto>
      </det>
      
      <!-- Totais -->
      <total>
        <ICMSTot>
          <vBC>50000.00</vBC>
          <vICMS>6000.00</vICMS>
          <vICMSDeson>0.00</vICMSDeson>
          <vFCP>0.00</vFCP>
          <vBCST>0.00</vBCST>
          <vST>0.00</vST>
          <vFCPST>0.00</vFCPST>
          <vFCPSTRet>0.00</vFCPSTRet>
          <vProd>50000.00</vProd>
          <vFrete>0.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vII>0.00</vII>
          <vIPI>0.00</vIPI>
          <vIPIDevol>0.00</vIPIDevol>
          <vPIS>412.50</vPIS>
          <vCOFINS>1900.00</vCOFINS>
          <vOutro>0.00</vOutro>
          <vNF>50000.00</vNF>
        </ICMSTot>
      </total>
      
      <!-- Transporte -->
      <transp>
        <modFrete>9</modFrete>
      </transp>
      
      <!-- Pagamento -->
      <pag>
        <detPag>
          <tPag>01</tPag>
          <vPag>50000.00</vPag>
        </detPag>
      </pag>
      
      <!-- Informações Adicionais -->
      <infAdic>
        <infCpl>Pedido 12345 - Entrega imediata</infCpl>
      </infAdic>
      
    </infNFe>
    
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
      <!-- Assinatura digital -->
    </Signature>
  </NFe>
  
  <!-- Protocolo de Autorização -->
  <protNFe versao="4.00">
    <infProt Id="ID150260006669469">
      <tpAmb>1</tpAmb>
      <verAplic>MS_7.0.22</verAplic>
      <chNFe>50260101773924000193550010000173831950403658</chNFe>
      <dhRecbto>2026-02-13T17:39:27-04:00</dhRecbto>
      <nProt>150260006669469</nProt>
      <digVal>spzCfmy93idz1pG3a+mI+SDLvR4=</digVal>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>
```

### Resumo NF-e (resNFe)

```xml
<resNFe versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe">
  <chNFe>50260101773924000193550010000173831950403658</chNFe>
  <CNPJ>01773924000193</CNPJ>
  <xNome>ALFA COMPUTADORES LTDA</xNome>
  <IE>283456789</IE>
  <UF>MS</UF>
  <dhEmi>2026-02-13T17:30:00-04:00</dhEmi>
  <tpNF>1</tpNF>
  <vNF>50000.00</vNF>
  <digVal>spzCfmy93idz1pG3a+mI+SDLvR4=</digVal>
  <dhRecbto>2026-02-13T17:39:27-04:00</dhRecbto>
  <nProt>150260006669469</nProt>
  <cSitNFe>1</cSitNFe>
</resNFe>
```

### Evento de Manifestação

```xml
<procEventoNFe versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">
  <evento versao="1.00">
    <infEvento Id="ID210210050260101773924000193550010000173831">
      <cOrgao>50</cOrgao>
      <tpAmb>1</tpAmb>
      <CNPJ>33251845000109</CNPJ>
      <chNFe>50260101773924000193550010000173831950403658</chNFe>
      <dhEvento>2026-02-14T10:00:00-03:00</dhEvento>
      <tpEvento>210210</tpEvento>
      <nSeqEvento>1</nSeqEvento>
      <verEvento>1.00</verEvento>
      <detEvento versao="1.00">
        <descEvento>Ciencia da Operacao</descEvento>
      </detEvento>
    </infEvento>
  </evento>
  
  <retEvento versao="1.00">
    <infEvento>
      <tpAmb>1</tpAmb>
      <verAplic>MS_7.0.22</verAplic>
      <cOrgao>50</cOrgao>
      <cStat>135</cStat>
      <xMotivo>Evento registrado e vinculado a NF-e</xMotivo>
      <chNFe>50260101773924000193550010000173831950403658</chNFe>
      <tpEvento>210210</tpEvento>
      <xEvento>Ciencia da Operacao</xEvento>
      <nSeqEvento>1</nSeqEvento>
      <dhRegEvento>2026-02-14T10:00:05-03:00</dhRegEvento>
      <nProt>150260006669470</nProt>
    </infEvento>
  </retEvento>
</procEventoNFe>
```

---

## Tipos de Eventos

| Código | Descrição |
|--------|-----------|
| **210200** | Confirmação da Operação |
| **210210** | Ciência da Operação |
| **210220** | Desconhecimento da Operação |
| **210240** | Operação não Realizada |
| **110110** | Carta de Correção |
| **110111** | Cancelamento |

---

## API Endpoints (Para Web)

### Estrutura JSON para Exportação

```json
{
  "api_version": "2.0",
  "endpoints": {
    "buscar_nfe": {
      "method": "POST",
      "path": "/api/v2/nfe/buscar",
      "description": "Busca NF-e por NSU ou chave",
      "request": {
        "tipo_busca": "nsu|chave",
        "cnpj_certificado": "string",
        "nsu_inicial": "string?",
        "chave": "string?",
        "limite": "integer?"
      },
      "response": {
        "success": "boolean",
        "total_encontradas": "integer",
        "documentos": [
          {
            "chave": "string",
            "numero": "string",
            "data_emissao": "date",
            "emitente": {
              "cnpj": "string",
              "nome": "string"
            },
            "destinatario": {
              "cnpj": "string",
              "nome": "string"
            },
            "valor": "decimal",
            "status": "string",
            "xml_url": "string",
            "pdf_url": "string"
          }
        ]
      }
    },
    "buscar_cte": {
      "method": "POST",
      "path": "/api/v2/cte/buscar",
      "description": "Busca CT-e por NSU ou chave",
      "request": "similar ao buscar_nfe",
      "response": "similar ao buscar_nfe"
    },
    "consultar_por_chave": {
      "method": "GET",
      "path": "/api/v2/documento/{chave}",
      "description": "Consulta documento específico",
      "response": {
        "chave": "string",
        "tipo": "NFe|CTe|NFSe",
        "dados_completos": {},
        "xml": "string",
        "pdf_base64": "string?"
      }
    },
    "listar_documentos": {
      "method": "GET",
      "path": "/api/v2/documentos",
      "description": "Lista documentos com filtros",
      "query_params": {
        "data_inicio": "date",
        "data_fim": "date",
        "cnpj_emitente": "string?",
        "cnpj_destinatario": "string?",
        "tipo": "NFe|CTe|NFSe?",
        "status": "string?",
        "limite": "integer?",
        "pagina": "integer?"
      }
    }
  }
}
```

---

Continua no próximo arquivo com exemplos práticos...
