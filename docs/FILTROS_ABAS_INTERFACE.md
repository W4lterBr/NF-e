# Documentação: Filtros das Abas da Interface

## 📋 Visão Geral

A interface possui **2 abas principais** que separam documentos fiscais por **direção do fluxo**:

1. **"Emitidos por terceiros"** - Documentos que **RECEBI** (eu sou destinatário)
2. **"Emitidos pela empresa"** - Documentos que **EMITI** (eu sou emitente)

---

## 🎯 Regras de Filtro

### ✅ Aba 1: "Emitidos por terceiros"

**Objetivo:** Mostrar notas de **COMPRAS/RECEBIMENTOS** (eu sou destinatário)

**Lógica do filtro:**
```python
# Carrega CNPJs dos certificados cadastrados
company_cnpjs = {normalizar_cnpj(c['cnpj_cpf']) for c in certificados}

# Exclui notas onde EU SOU O EMITENTE
cnpj_emitente_normalizado = normalizar_cnpj(nota['cnpj_emitente'])
if cnpj_emitente_normalizado in company_cnpjs:
    continue  # ❌ Pula esta nota (eu sou emitente)

# ✅ Mostra apenas notas onde cnpj_emitente NÃO está nos certificados
```

**Exemplos:**
- ✅ NF-e de fornecedor emitida para minha empresa
- ✅ CT-e de transportadora para entrega de mercadorias
- ✅ NFS-e de prestador de serviço

---

### ✅ Aba 2: "Emitidos pela empresa"

**Objetivo:** Mostrar notas de **VENDAS/EMISSÕES** (eu sou emitente)

**Lógica do filtro (quando "TODOS" selecionado):**
```python
# Carrega CNPJs dos certificados cadastrados
company_cnpjs = {normalizar_cnpj(c['cnpj_cpf']) for c in certificados}

# Mostra APENAS notas onde EU SOU O EMITENTE
placeholders = ','.join(['?' for _ in company_cnpjs])
WHERE cnpj_emitente IN (company_cnpjs)

# ✅ Mostra apenas notas onde cnpj_emitente ESTÁ nos certificados
```

**Lógica do filtro (quando certificado específico selecionado):**
```python
WHERE cnpj_emitente = certificado_selecionado
```

**Exemplos:**
- ✅ NF-e de venda emitida por mim para cliente
- ✅ CT-e de transporte emitido pela minha empresa
- ✅ NFS-e de serviço prestado por mim

---

## ⚠️ ERRO COMUM: Misturar as Abas

### ❌ Problema Identificado (Corrigido em 29/01/2026)

**Sintoma:**
```
Aba "Emitidos pela empresa" mostrava:
- Notas que EU emiti ✅
- Notas que RECEBI ❌ (ERRADO!)
```

**Causa Raiz:**
```python
# CÓDIGO ANTIGO (ERRADO):
if selected_cert:
    WHERE cnpj_emitente = selected_cert
else:
    # ❌ Mostra TODAS as notas do banco (sem filtro!)
    # Incluía notas de terceiros
```

**Correção Aplicada:**
```python
# CÓDIGO NOVO (CORRETO):
if selected_cert:
    WHERE cnpj_emitente = selected_cert
else:
    # ✅ Mostra apenas notas dos certificados cadastrados
    WHERE cnpj_emitente IN (company_cnpjs)
```

---

## 🔍 Como Verificar se o Filtro está Correto

### Teste 1: Aba "Emitidos por terceiros"
1. Abra a aba "Emitidos por terceiros"
2. Verifique a coluna **"Emissor CNPJ"**
3. ✅ **Nenhum CNPJ** deve corresponder aos certificados cadastrados

### Teste 2: Aba "Emitidos pela empresa"
1. Abra a aba "Emitidos pela empresa"
2. Verifique a coluna **"Emissor CNPJ"**
3. ✅ **Todos os CNPJs** devem corresponder aos certificados cadastrados

### Teste 3: Logs de Debug
Procure por estas mensagens no console:
```
[FILTERED_EMITIDOS] Iniciando filtro...
[DEBUG] 🏢 FILTRO EMITIDOS - Mostrando notas onde EU SOU O EMITENTE (cnpj_emitente nos certificados)
[DEBUG] CNPJs da empresa (normalizados): {'01773924000193', '33251845000109', ...}
```

---

## 🛡️ Boas Práticas para Prevenir Erros

### 1. **Sempre Filtrar por `cnpj_emitente`**
```python
# ✅ CORRETO: Usa cnpj_emitente para determinar emissão
WHERE cnpj_emitente IN (company_cnpjs)

# ❌ ERRADO: Usa informante (quem baixou a nota)
WHERE informante IN (company_cnpjs)
```

**Motivo:** `informante` indica quem **baixou** o documento, não quem **emitiu**.

### 2. **Normalizar CNPJs Antes de Comparar**
```python
def normalizar_cnpj(cnpj: str) -> str:
    """Remove pontuação: 12.345.678/0001-90 → 12345678000190"""
    return ''.join(c for c in str(cnpj or '') if c.isdigit())

# ✅ CORRETO:
if normalizar_cnpj(nota['cnpj_emitente']) in company_cnpjs:
    ...

# ❌ ERRADO: Comparação direta (pode falhar com formatação)
if nota['cnpj_emitente'] in company_cnpjs:
    ...
```

### 3. **Testar com Dados Reais**
Crie notas de teste nas duas direções:
- Nota emitida POR mim PARA cliente
- Nota emitida POR fornecedor PARA mim

Verifique se cada uma aparece na aba correta.

### 4. **Documentar Mudanças em Filtros**
Sempre que modificar a lógica de filtro, atualize:
- Este documento (`FILTROS_ABAS_INTERFACE.md`)
- Comentários no código (linhas 2680-2682, 2834-2845)
- CHANGELOG.md

---

## 📊 Campos Importantes do Banco de Dados

| Campo | Descrição | Uso para Filtro |
|-------|-----------|-----------------|
| `cnpj_emitente` | CNPJ de quem **emitiu** o documento | ✅ **PRINCIPAL** - Define emissão |
| `cnpj_destinatario` | CNPJ de quem **recebeu** o documento | ⚠️ Secundário (pode estar vazio em resumos) |
| `informante` | CNPJ do certificado que **baixou** a nota | ❌ **NÃO USAR** para filtro de emissão |
| `xml_status` | Status: COMPLETO/RESUMO/EVENTO | ✅ Usar para excluir EVENTO |

---

## 🔧 Arquivos Relacionados

| Arquivo | Linhas | Descrição |
|---------|--------|-----------|
| `Busca NF-e.py` | 2670-2690 | Filtro "Emitidos por terceiros" |
| `Busca NF-e.py` | 2830-2850 | Filtro "Emitidos pela empresa" |
| `modules/database.py` | 200-500 | Queries SQL para notas |
| `nfe_search.py` | 500-700 | Extração de dados do XML |

---

## 📝 Histórico de Correções

### 29/01/2026 - Correção de Filtro Duplicado
- **Problema:** Aba "Emitidos pela empresa" mostrava TODAS as notas quando "TODOS" selecionado
- **Causa:** Faltava filtro `WHERE cnpj_emitente IN (company_cnpjs)`
- **Solução:** Adicionado filtro para mostrar apenas notas dos certificados cadastrados
- **Commit:** `fix: corrige filtro de abas para separar emitidos/recebidos`

---

## 🚨 Checklist de Validação

Antes de considerar o filtro correto, verifique:

- [ ] CNPJs dos certificados são carregados corretamente
- [ ] CNPJs são normalizados (sem pontuação)
- [ ] Aba 1 **exclui** notas onde `cnpj_emitente` está nos certificados
- [ ] Aba 2 **inclui apenas** notas onde `cnpj_emitente` está nos certificados
- [ ] Eventos (`xml_status = 'EVENTO'`) não aparecem nas abas
- [ ] Filtros por status, tipo e data funcionam corretamente
- [ ] Logs de debug mostram quantidade esperada de notas

---

## 📞 Suporte

Se encontrar problemas com filtros:
1. Ative logs de debug: `[DEBUG]` no console
2. Verifique CNPJs cadastrados: Configurações → Certificados
3. Consulte este documento
4. Verifique CHANGELOG.md para mudanças recentes

---

**Última atualização:** 29/01/2026
**Versão:** 1.0.9.1
