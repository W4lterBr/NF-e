# 📚 Notas Técnicas SEFAZ - Distribuição DFe

## 📋 Legislação Oficial

### 1️⃣ NF-e - Nota Técnica 2014.002
**Título:** Web Service - NFeDistribuicaoDFe  
**Link:** https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=TDqtb7RW4%20Y=  
**Versão:** 1.01  
**Aplicação:** Consulta de NF-e via NSU

#### Principais Regras (NT 2014.002):
- ✅ **Intervalo mínimo entre consultas**: 1 hora quando não há documentos (cStat=137 ou ultNSU=maxNSU)
- ✅ **Erro 656**: "Rejeição: Consumo Indevido" - Consultas muito frequentes
- ✅ **cStat=137**: Nenhum documento localizado → Aguardar 1 hora
- ✅ **cStat=138**: Documento(s) localizado(s) → Processar documentos
- ✅ **Limite por consulta**: Até 50 documentos por requisição
- ✅ **maxNSU=0**: Indica que não há documentos disponíveis (NORMAL)

---

### 2️⃣ CT-e - Nota Técnica 2015.002
**Título:** Web Service - CTeDistribuicaoDFe  
**Link:** http://www.cte.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=lcBaMwgtOOM=  
**Versão:** 1.04  
**Aplicação:** Consulta de CT-e via NSU

#### Principais Regras (NT 2015.002 CT-e):
- ✅ **Intervalo mínimo entre consultas**: 1 hora quando não há documentos
- ✅ **Erro 656**: Consumo Indevido - Aguardar 1 hora
- ✅ **cStat=137**: Nenhum documento → Aguardar 1 hora
- ✅ **cStat=138**: Documentos disponíveis → Processar
- ✅ **Limite por consulta**: Até 50 documentos por requisição
- ✅ **Estrutura similar à NF-e**: Mesmos códigos de status

---

### 3️⃣ MDF-e - Nota Técnica 2015.002
**Título:** Web Service - MDFeDistribuicaoDFe  
**Link:** https://dfe-portal.svrs.rs.gov.br/MDFE/DownloadArquivoEstatico/?sistema=MDFE&tipoArquivo=3&nomeArquivo=MDFe_NotaTecnica_2015_002_WS_Distribuicao_DFE_v1.01.pdf  
**Versão:** 1.01  
**Aplicação:** Consulta de MDF-e via NSU

#### Principais Regras (NT 2015.002 MDF-e):
- ✅ **Intervalo mínimo entre consultas**: 1 hora quando não há documentos
- ✅ **Estrutura similar à NF-e e CT-e**: Mesma lógica de consulta
- ✅ **Limite por consulta**: Até 50 documentos por requisição

---

## 🎯 Implementação no Sistema

### ✅ Conformidade com Notas Técnicas

Nosso sistema implementa **TODAS** as regras das Notas Técnicas:

| Regra | NT | Status | Implementação |
|-------|-----|--------|---------------|
| Intervalo 1h (cStat=137) | 2014.002 | ✅ | `registrar_sem_documentos()` |
| Intervalo 1h (ultNSU=maxNSU) | 2014.002 | ✅ | Verifica após processar docs |
| Tratamento erro 656 | 2014.002 | ✅ | `registrar_erro_656()` - 65 min |
| Processar cStat=138 | 2014.002 | ✅ | Loop de processamento |
| Limite 50 docs/consulta | 2014.002 | ✅ | Automático (SEFAZ) |
| Salvar ultNSU progressivo | 2014.002 | ✅ | `set_last_nsu()` |
| CT-e: Mesmas regras | 2015.002 | ✅ | `processar_cte()` |
| maxNSU=0 é normal | Todas | ✅ | Logs explicativos |

---

## 📊 Códigos de Status (cStat)

### Códigos Principais (Distribuição DFe):

| cStat | Descrição | Ação do Sistema | NT Referência |
|-------|-----------|-----------------|---------------|
| **137** | Nenhum documento localizado | Aguarda 1h | 2014.002 / 2015.002 |
| **138** | Documento(s) localizado(s) | Processa documentos | 2014.002 / 2015.002 |
| **656** | Consumo Indevido | Aguarda 65 min | 2014.002 / 2015.002 |
| **138** + ultNSU=maxNSU | Sincronizado após processar | Aguarda 1h | 2014.002 |

---

## 🔍 Campos da Resposta SEFAZ

### Estrutura retDistDFeInt:

```xml
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
    <tpAmb>1</tpAmb>                          <!-- Ambiente: 1=Produção -->
    <verAplic>1.7.6</verAplic>                <!-- Versão aplicativo SEFAZ -->
    <cStat>138</cStat>                        <!-- Status: 137, 138, 656... -->
    <xMotivo>Documento(s) localizado(s)</xMotivo>
    <dhResp>2026-01-09T10:16:51-03:00</dhResp>
    <ultNSU>000000000001620</ultNSU>          <!-- Último NSU retornado -->
    <maxNSU>000000000001620</maxNSU>          <!-- Maior NSU disponível -->
    <loteDistDFeInt>
        <docZip NSU="..." schema="...">       <!-- Documentos (até 50) -->
            ... (base64 + gzip)
        </docZip>
    </loteDistDFeInt>
</retDistDFeInt>
```

### Significado dos Campos:

| Campo | Significado | Exemplo | Nota Técnica |
|-------|-------------|---------|--------------|
| **ultNSU** | Último NSU da resposta atual | 000000000001620 | NT 2014.002 |
| **maxNSU** | Maior NSU disponível no ambiente | 000000000001620 | NT 2014.002 |
| **maxNSU=0** | Não há documentos disponíveis (NORMAL) | 000000000000000 | NT 2014.002 |
| **cStat** | Código de status da consulta | 137, 138, 656 | NT 2014.002 |

---

## ⚠️ Regras de Bloqueio

### NT 2014.002 - Seção 3.3 (Regras de Negócio):

> **"Deve ser aguardado 1 hora para efetuar nova solicitação caso não existam mais documentos a serem pesquisados"**

### Quando aguardar 1 hora:

1. **cStat=137** (Nenhum documento localizado)
   ```python
   if cStat == '137':
       db.registrar_sem_documentos(inf)  # Aguarda 1h
   ```

2. **ultNSU == maxNSU** (Sistema sincronizado)
   ```python
   if ult and max_nsu and ult == max_nsu:
       db.registrar_sem_documentos(inf)  # Aguarda 1h
   ```

3. **Erro 656** (Consumo Indevido)
   ```python
   if cStat == '656':
       db.registrar_erro_656(inf, nsu)  # Aguarda 65 min (nosso sistema)
   ```

---

## 📝 Fluxo de Consulta Conforme NT

### Fluxo Oficial (NT 2014.002):

```
┌─────────────────────────────┐
│ 1. Consulta NSU inicial     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ 2. SEFAZ retorna resposta   │
│    - cStat                  │
│    - ultNSU                 │
│    - maxNSU                 │
│    - Documentos (0-50)      │
└──────────┬──────────────────┘
           │
           ▼
    ┌──────────────┐
    │ cStat=656?   │──── SIM ──► Aguarda 1h (Consumo Indevido)
    └──────┬───────┘
           │ NÃO
           ▼
    ┌──────────────┐
    │ cStat=137?   │──── SIM ──► Aguarda 1h (Sem documentos)
    └──────┬───────┘
           │ NÃO (cStat=138)
           ▼
┌─────────────────────────────┐
│ 3. Processa documentos      │
│    - Extrai XMLs            │
│    - Valida                 │
│    - Salva no banco         │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ 4. Atualiza ultNSU          │
└──────────┬──────────────────┘
           │
           ▼
    ┌──────────────────┐
    │ ultNSU=maxNSU?   │──── SIM ──► Aguarda 1h (Sincronizado)
    └──────┬───────────┘
           │ NÃO
           ▼
┌─────────────────────────────┐
│ 5. Nova iteração            │
│    (busca próximos 50 docs) │
└─────────────────────────────┘
```

---

## 🔐 Segurança e Certificado Digital

### NT 2014.002 - Seção 4 (Requisitos Técnicos):

- ✅ Certificado Digital A1 ou A3 obrigatório
- ✅ Conexão TLS/SSL com certificado válido
- ✅ Assinatura digital nas requisições
- ✅ Timeout recomendado: 30 segundos

### Implementação:

```python
# Configuração TLS e certificado
session = Session()
session.cert = (cert_path, senha)
session.verify = True  # Valida certificado SEFAZ

transport = Transport(
    session=session,
    timeout=30,
    operation_timeout=30
)
```

---

## 📈 Limites Técnicos

### Conforme Notas Técnicas:

| Limite | Valor | NT Referência |
|--------|-------|---------------|
| Documentos por consulta | 50 | NT 2014.002 |
| Intervalo mínimo (sem docs) | 1 hora | NT 2014.002 |
| Intervalo erro 656 | 1 hora | NT 2014.002 |
| Timeout requisição | 30s (recomendado) | NT 2014.002 |
| Tamanho máximo NSU | 15 dígitos | NT 2014.002 |

---

## ✅ Checklist de Conformidade

### Sistema está em conformidade com:

- [x] NT 2014.002 (NF-e) - Distribuição DFe
- [x] NT 2015.002 (CT-e) - Distribuição DFe
- [x] Intervalo de 1 hora quando sem documentos
- [x] Tratamento de erro 656 (Consumo Indevido)
- [x] Processamento de até 50 documentos por consulta
- [x] Atualização progressiva de NSU
- [x] Validação de certificado digital
- [x] Timeout de 30 segundos
- [x] Logs detalhados de todas as operações
- [x] Explicação clara de maxNSU=0

---

## 📞 Links de Referência

### Portais Oficiais:

- **NF-e:** https://www.nfe.fazenda.gov.br/
- **CT-e:** http://www.cte.fazenda.gov.br/
- **MDF-e:** https://dfe-portal.svrs.rs.gov.br/MDFE

### Downloads:

- **NT 2014.002 (NF-e):** https://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=TDqtb7RW4%20Y=
- **NT 2015.002 (CT-e):** http://www.cte.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=lcBaMwgtOOM=
- **NT 2015.002 (MDF-e):** https://dfe-portal.svrs.rs.gov.br/MDFE/DownloadArquivoEstatico/?sistema=MDFE&tipoArquivo=3&nomeArquivo=MDFe_NotaTecnica_2015_002_WS_Distribuicao_DFE_v1.01.pdf

---

## 📝 Histórico de Versões

| Data | Versão | Alteração |
|------|--------|-----------|
| 2026-01-09 | 1.0 | Documentação inicial com links oficiais NT |
| 2026-01-09 | 1.1 | Validação de conformidade com legislação |

---

**Nota:** Este documento serve como referência rápida para as regras de Distribuição DFe. Consulte sempre as Notas Técnicas oficiais para informações atualizadas e detalhadas.
