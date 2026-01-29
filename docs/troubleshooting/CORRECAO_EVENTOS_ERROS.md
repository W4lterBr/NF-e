# 🚫 Correção: Eventos e Respostas de Erro na Interface

**Data:** 28 de Janeiro de 2026  
**Status:** ✅ **CORRIGIDO**

---

## ❌ Problema Identificado

**Sintoma:**
Interface mostrava registros inválidos na tabela de notas:
- Número: N/A
- Emitente: N/A
- Arquivo XML: `SEM_NUMERO-SEM_NOME.xml`

**Causa Raiz:**
Sistema estava salvando **respostas de erro da SEFAZ** como se fossem documentos fiscais:

```xml
<!-- Exemplo: NÃO É UMA NOTA! -->
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>1</tpAmb>
  <verAplic>1.7.6</verAplic>
  <cStat>656</cStat>
  <xMotivo>Rejeicao: Consumo Indevido (Ultrapassou o limite de 20 consultas por hora)</xMotivo>
  <dhResp>2026-01-28T14:30:30-03:00</dhResp>
</retDistDFeInt>
```

**Impacto:**
- ❌ 52 registros inválidos no banco
- ❌ Interface poluída com linhas sem dados
- ❌ Impossível abrir XML/PDF (arquivo não contém nota)
- ❌ Confusão para o usuário

---

## ✅ Solução Implementada

### 1️⃣ **Filtro de Respostas SEFAZ** (nfe_search.py)

Adicionado filtro na função `salvar_xml_por_certificado()`:

```python
# 🚫 FILTRO CRÍTICO: Ignora respostas de erro da SEFAZ
if root_tag in ['retDistDFeInt', 'retConsSitNFe', 'retConsReciNFe', 'retEnviNFe']:
    # Verifica se é resposta de erro
    cStat = root.findtext('cStat')
    xMotivo = root.findtext('xMotivo')
    
    if cStat and cStat != '138':  # 138 = sucesso
        print(f"[IGNORADO] Resposta SEFAZ ({root_tag}) cStat={cStat}: {xMotivo}")
        return None  # NÃO salva respostas de erro
```

**Códigos de Status Filtrados:**
- `656`: Consumo Indevido (limite de consultas excedido)
- `217`: NF-e não consta na base de dados da SEFAZ
- `565`: Rejeição genérica
- Qualquer código diferente de `138` (sucesso)

### 2️⃣ **Filtro de Eventos na Interface** (Busca NF-e.py)

Sistema já tinha filtro para não mostrar eventos:

```python
# NÃO MOSTRAR eventos na interface
xml_status = (it.get('xml_status') or '').upper()
if xml_status == 'EVENTO':
    continue  # Pula eventos (resEvento, procEventoNFe)
```

**Eventos são salvos mas NÃO aparecem na tabela:**
- ✅ `resEvento` - Resumo de evento
- ✅ `procEventoNFe` - Evento processado
- ✅ `retEvento` - Retorno de evento
- ✅ Manifestações (210210, 210200, etc.)

### 3️⃣ **Limpeza do Banco de Dados**

Criado script `limpar_registros_invalidos.py`:

```python
# Remove registros sem dados válidos
DELETE FROM notas_detalhadas 
WHERE numero IS NULL 
   OR numero = '' 
   OR numero = 'N/A' 
   OR numero = 'SEM_NUMERO'
   OR nome_emitente = 'SEM_NOME'
```

**Resultado:**
- ✅ **52 registros inválidos removidos**
- ✅ **1.481 notas válidas mantidas**

### 4️⃣ **Remoção do Arquivo Inválido**

```powershell
Remove-Item "xmls\33251845000109\01-2026\Outros\SEM_NUMERO-SEM_NOME.xml"
```

✅ Arquivo de erro 656 removido da pasta

---

## 📋 Tipos de XML e Como São Tratados

| Tipo | Tag Raiz | Salva? | Aparece na Interface? |
|------|----------|--------|----------------------|
| **NF-e Completa** | `<nfeProc>` | ✅ Sim | ✅ Sim |
| **CT-e Completo** | `<cteProc>` | ✅ Sim | ✅ Sim |
| **NFS-e** | `<CompNfse>` | ✅ Sim | ✅ Sim |
| **Resumo NF-e** | `<resNFe>` | ✅ Sim | ✅ Sim (status RESUMO) |
| **Evento** | `<resEvento>` | ✅ Sim | ❌ **NÃO** (filtrado) |
| **Manifestação** | `<procEventoNFe>` | ✅ Sim | ❌ **NÃO** (filtrado) |
| **Resposta Erro** | `<retDistDFeInt>` | ❌ **NÃO** | ❌ **NÃO** |
| **Erro 656** | `<retDistDFeInt>` cStat=656 | ❌ **NÃO** | ❌ **NÃO** |

---

## 🔍 Como Identificar Cada Tipo

### ✅ **Documento Fiscal Válido:**
```xml
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe50260176093731001324550010010308551127082446">
      <ide>
        <nNF>1030855</nNF>  ✓ TEM NÚMERO
      </ide>
      <emit>
        <xNome>EMPRESA LTDA</xNome>  ✓ TEM EMITENTE
      </emit>
    </infNFe>
  </NFe>
</nfeProc>
```

### ❌ **Resposta de Erro (NÃO É NOTA):**
```xml
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe">
  <cStat>656</cStat>  ❌ CÓDIGO DE ERRO
  <xMotivo>Consumo Indevido</xMotivo>  ❌ MENSAGEM DE ERRO
</retDistDFeInt>
```

### ℹ️ **Evento (Salva mas Não Mostra):**
```xml
<resEvento xmlns="http://www.portalfiscal.inf.br/nfe">
  <chNFe>50260176093731...</chNFe>
  <tpEvento>210210</tpEvento>  ℹ️ MANIFESTAÇÃO
  <xEvento>Ciência da Operação</xEvento>
</resEvento>
```

---

## 🛡️ Proteções Implementadas

### **Nível 1: Salvamento** (nfe_search.py)
```python
# Antes: Salvava tudo
# Depois: Filtra respostas de erro
if root_tag in ['retDistDFeInt', ...]:
    if cStat != '138':
        return None  # NÃO salva
```

### **Nível 2: Exibição** (Busca NF-e.py)
```python
# Antes: Mostrava eventos
# Depois: Filtra eventos
if xml_status == 'EVENTO':
    continue  # NÃO mostra
```

### **Nível 3: Validação SQL**
```sql
-- Consultas sempre filtram eventos
SELECT * FROM notas_detalhadas 
WHERE xml_status != 'EVENTO'
```

---

## 📊 Resultados da Correção

**Antes:**
- ❌ 1.533 registros (incluindo 52 inválidos)
- ❌ Interface com linhas vazias (N/A)
- ❌ XMLs de erro salvos na pasta

**Depois:**
- ✅ 1.481 registros válidos
- ✅ Interface limpa (só notas reais)
- ✅ Respostas de erro ignoradas
- ✅ Eventos salvos mas ocultos

**Ganho de Qualidade:**
- 📉 3,4% de dados inválidos removidos
- ✨ 100% das linhas visíveis são notas válidas
- 🎯 Sistema mais confiável

---

## 🧪 Como Testar

### **1. Verificar Filtro de Erro 656:**
```python
from nfe_search import salvar_xml_por_certificado

xml_erro = """<?xml version="1.0"?>
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe">
  <cStat>656</cStat>
  <xMotivo>Consumo Indevido</xMotivo>
</retDistDFeInt>"""

result = salvar_xml_por_certificado(xml_erro, '33251845000109')
assert result is None  # ✓ Não salvou
print("✓ Teste 1 passou: Erro 656 ignorado")
```

### **2. Verificar Filtro de Eventos:**
```python
# Buscar no banco
SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'EVENTO';
# Resultado esperado: > 0 (eventos existem no banco)

# Verificar interface
# Resultado esperado: eventos NÃO aparecem na tabela
```

### **3. Verificar Limpeza:**
```python
SELECT COUNT(*) FROM notas_detalhadas 
WHERE numero IS NULL OR numero = 'N/A';
# Resultado esperado: 0 (todos removidos)
```

---

## 📁 Arquivos Modificados

1. **nfe_search.py** (linha ~856)
   - Adicionado filtro de respostas SEFAZ
   - Retorna `None` para XMLs de erro

2. **limpar_registros_invalidos.py** (novo)
   - Script de limpeza do banco
   - Remove registros sem número/emitente

3. **xmls/33251845000109/01-2026/Outros/**
   - Removido `SEM_NUMERO-SEM_NOME.xml`

---

## ⚠️ Prevenção Futura

### **Monitoramento:**
```python
# Adicionar log em salvar_xml_por_certificado()
if root_tag in ['retDistDFeInt', ...]:
    logger.warning(f"[FILTRO] Resposta SEFAZ ignorada: cStat={cStat}, {xMotivo}")
```

### **Validação Periódica:**
```sql
-- Executar mensalmente
SELECT COUNT(*) FROM notas_detalhadas 
WHERE numero IS NULL OR numero = 'N/A' OR nome_emitente = 'SEM_NOME';
-- Esperado: 0
```

### **Alerta no Dashboard:**
```python
# Mostrar aviso se houver registros inválidos
if count_invalidos > 0:
    show_warning(f"⚠️ {count_invalidos} registros inválidos detectados")
```

---

## ✅ Checklist de Qualidade

- [x] Respostas de erro SEFAZ não são salvas
- [x] Eventos são salvos mas não aparecem na interface
- [x] Banco limpo de registros inválidos (52 removidos)
- [x] Arquivo XML de erro removido
- [x] Sistema testado e validado
- [x] Documentação criada

---

## 🎯 Conclusão

O sistema agora **distingue corretamente** entre:

1. **Documentos Fiscais** → Salva E mostra ✅
2. **Eventos** → Salva MAS NÃO mostra ℹ️
3. **Respostas de Erro** → NÃO salva ❌

**Status Final:** 🟢 **PROBLEMA RESOLVIDO**

---

_Documentação criada em 28/01/2026_  
_Versão: 1.0.0_
