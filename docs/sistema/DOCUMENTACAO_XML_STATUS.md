# 📋 Documentação: Sistema de Status de XMLs

## 🎯 Visão Geral

O sistema possui **dois estados críticos** para gerenciar XMLs:

1. **`xml_status` em `notas_detalhadas`**: Status visual (COMPLETO/RESUMO/EVENTO)
2. **`caminho_arquivo` em `xmls_baixados`**: Caminho físico do XML no disco

### Valores de `xml_status`:
- **COMPLETO**: XML completo disponível (mostra ícone verde ✅)
- **RESUMO**: Apenas dados resumidos (sem ícone, fundo cinza)
- **EVENTO**: Registro de evento (cancelamento, carta correção, etc.)

---

## 🐛 Problema Histórico Resolvido (27/01/2026)

### **Sintoma:**
- XMLs baixados com sucesso da SEFAZ
- Arquivos salvos corretamente no disco
- Registros em `xmls_baixados` corretos
- **MAS ícones não apareciam na interface** ❌

### **Causa Raiz:**
O método `salvar_nota_detalhada()` apenas **validava e downgrade** (COMPLETO → RESUMO), mas **nunca fazia upgrade** (RESUMO → COMPLETO) quando XML era baixado posteriormente.

**Fluxo Antigo (INCORRETO):**
```
1. Nota salva como RESUMO (primeira vez)
2. XML baixado e salvo no disco ✅
3. Registro em xmls_baixados criado ✅
4. xml_status permanecia RESUMO ❌ (não atualizava)
5. Ícone não aparecia na interface ❌
```

### **Impacto:**
- **1509 notas** estavam com status incorreto
- Usuários não viam indicação visual de XMLs completos
- XMLs existiam mas eram "invisíveis" na interface

---

## ✅ Solução Implementada

### **1. Correção Retroativa**
Script criado: `corrigir_status_xmls.py`

**Função:**
- Busca notas com `xml_status = 'RESUMO'`
- Verifica se tem registro em `xmls_baixados`
- Confirma existência física do arquivo
- Atualiza para `xml_status = 'COMPLETO'`

**Execução:**
```bash
python corrigir_status_xmls.py
```

**Resultado:**
- ✅ 1509 notas corrigidas
- ✅ Ícones passaram a aparecer imediatamente

---

### **2. Auto-detecção Bidirecional**

Modificação em `nfe_search.py` → método `salvar_nota_detalhada()`:

**Nova Lógica:**
```python
# 🔍 AUTO-DETECÇÃO: Verifica SEMPRE se existe XML em disco

# 1. Consulta xmls_baixados
cursor = conn.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
row = cursor.fetchone()

# 2. UPGRADE: Se tem XML e está como RESUMO → COMPLETO
if row and row[0] and Path(row[0]).exists():
    xml_status = 'COMPLETO'  ✅

# 3. DOWNGRADE: Se não tem XML e está como COMPLETO → RESUMO  
else:
    xml_status = 'RESUMO'  ⬇️
```

**Características:**
- ✅ **Bidirecional**: Faz upgrade E downgrade
- ✅ **Automático**: Não depende de parâmetro manual
- ✅ **Confiável**: Verifica disco, não apenas banco
- ✅ **Com logs**: Registra todas as correções

---

## 🔍 Scripts de Diagnóstico

### **1. diagnostico_xmls.py**

**Verifica 5 cenários críticos:**

```bash
python diagnostico_xmls.py
```

**Saída:**
- 1️⃣ COMPLETO mas NÃO REGISTRADO em xmls_baixados
- 2️⃣ COMPLETO mas SEM CAMINHO em xmls_baixados
- 3️⃣ Arquivos XML no disco mas marcados como RESUMO
- 4️⃣ Estatísticas gerais
- 5️⃣ Chaves para testar buscas

**Quando usar:**
- Após importações em massa
- Quando ícones não aparecem
- Verificação mensal de consistência
- Após migrações de banco

---

### **2. corrigir_status_xmls.py**

**Corrige inconsistências automaticamente:**

```bash
python corrigir_status_xmls.py
```

**O que faz:**
- Busca XMLs físicos no disco
- Compara com status no banco
- Atualiza `xml_status` quando necessário
- Mostra estatísticas antes/depois

**Quando usar:**
- Após restaurar backup
- Após mover/reorganizar XMLs
- Quando diagnóstico encontrar problemas
- Após importar XMLs de outro sistema

---

## 🛡️ Prevenção de Problemas

### **1. Fluxo Correto de Download**

**Sequência OBRIGATÓRIA:**

```python
# ✅ CORRETO
chave = "44261234567890123456789012345678901234567890"
cnpj = "12345678000190"

# 1. Salvar XML no disco
caminho_xml = salvar_xml_por_certificado(xml_content, cnpj, chave)

# 2. Registrar no banco (COM CAMINHO)
db.registrar_xml(chave, cnpj, caminho_xml)  # ⚠️ CAMINHO É OBRIGATÓRIO

# 3. Salvar nota detalhada (auto-detecção ativa)
db.salvar_nota_detalhada(nota)  # Detecta XML automaticamente
```

**❌ ERROS COMUNS:**

```python
# ❌ ERRADO: Registrar sem caminho
db.registrar_xml(chave, cnpj, None)  # Sem caminho = RESUMO

# ❌ ERRADO: Não registrar em xmls_baixados
salvar_xml_por_certificado(xml, cnpj, chave)
# db.registrar_xml() não chamado!  # XML "fantasma"

# ❌ ERRADO: Ordem invertida
db.registrar_xml(chave, cnpj, caminho)
salvar_xml_por_certificado(xml, cnpj, chave)  # Tarde demais!
```

---

### **2. Checklist de Desenvolvimento**

Ao modificar código que manipula XMLs:

- [ ] XML salvo no disco ANTES de registrar no banco
- [ ] `registrar_xml()` chamado COM parâmetro `caminho_arquivo`
- [ ] `salvar_nota_detalhada()` chamado DEPOIS de registrar XML
- [ ] Logs confirmam: "XML registrado: {chave} → {caminho}"
- [ ] Testes verificam ícones aparecem na interface

---

### **3. Monitoramento Contínuo**

**Query SQL para Dashboard:**

```sql
-- Estatísticas de XMLs
SELECT 
    xml_status,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM notas_detalhadas), 2) as percentual
FROM notas_detalhadas
GROUP BY xml_status;

-- Inconsistências (ALERTA!)
SELECT COUNT(*) as xmls_fantasma
FROM notas_detalhadas nd
LEFT JOIN xmls_baixados xb ON nd.chave = xb.chave
WHERE nd.xml_status = 'COMPLETO' AND xb.chave IS NULL;
```

**Alertas Críticos:**
- Se `xmls_fantasma > 0` → Investigar imediatamente
- Se `COMPLETO < RESUMO` após busca massiva → Rodar diagnóstico

---

## 🔧 Manutenção

### **Rotina Mensal:**

```bash
# 1. Diagnóstico
python diagnostico_xmls.py > diagnostico_$(date +%Y%m%d).txt

# 2. Se encontrar problemas
python corrigir_status_xmls.py

# 3. Backup
sqlite3 notas.db ".backup notas_backup_$(date +%Y%m%d).db"
```

---

### **Após Importação de XMLs:**

```bash
# 1. Importar XMLs (sua rotina normal)
python importar_xmls.py

# 2. Corrigir status
python corrigir_status_xmls.py

# 3. Verificar resultado
python diagnostico_xmls.py
```

---

## 📊 Métricas de Saúde

### **Sistema Saudável:**
```
✅ COMPLETO: 1509 (97%)
✅ RESUMO: 47 (3%)
✅ XMLs em xmls_baixados: 1509
✅ XMLs físicos no disco: 1509+
✅ Inconsistências: 0
```

### **Problemas Detectados:**
```
⚠️ COMPLETO: 0 (0%)  ← CRÍTICO!
⚠️ RESUMO: 1556 (100%)  ← Problema histórico
⚠️ XMLs em xmls_baixados: 1509
⚠️ XMLs físicos: 22984  ← Muitos arquivos órfãos
⚠️ Inconsistências: 1509  ← Correção necessária
```

---

## 🚨 Troubleshooting

### **Problema: Ícone não aparece após download**

**Diagnóstico:**
```python
import sqlite3
conn = sqlite3.connect('notas.db')

chave = "SUA_CHAVE_AQUI"

# 1. Verificar status
cursor = conn.execute("SELECT xml_status FROM notas_detalhadas WHERE chave = ?", (chave,))
print(f"Status no banco: {cursor.fetchone()}")

# 2. Verificar registro
cursor = conn.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
print(f"Caminho registrado: {cursor.fetchone()}")

# 3. Verificar arquivo
import os
cursor = conn.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
row = cursor.fetchone()
if row:
    print(f"Arquivo existe: {os.path.exists(row[0])}")
```

**Soluções:**

| Situação | Status | Registro | Arquivo | Ação |
|----------|--------|----------|---------|------|
| Caso 1 | RESUMO | ✅ | ✅ | Rodar `corrigir_status_xmls.py` |
| Caso 2 | COMPLETO | ❌ | ✅ | Chamar `db.registrar_xml()` |
| Caso 3 | COMPLETO | ✅ | ❌ | Baixar XML novamente |
| Caso 4 | RESUMO | ❌ | ❌ | Normal, buscar na SEFAZ |

---

## 📝 Logs Importantes

### **Logs de Sucesso:**
```
✅ SALVO NFe 50260112345678901234...
XML registrado: 50260112345678901234... → C:\...\xmls\123456.xml
🔄 Auto-upgrade: 50260112345678901234... RESUMO → COMPLETO (XML encontrado)
```

### **Logs de Problema:**
```
⚠️ Nota 50260112345678901234... marcada como COMPLETO mas NÃO REGISTRADA em xmls_baixados
⚠️ Nota 50260112345678901234... registrada mas SEM CAMINHO
⚠️ Nota 50260112345678901234... tem caminho mas arquivo não existe
```

**Ação:** Investigar imediatamente se esses warnings aparecerem

---

## 🎓 Conceitos-Chave

### **Por que dois lugares?**

| Tabela | Propósito | Conteúdo |
|--------|-----------|----------|
| `notas_detalhadas` | Dados de negócio | Emitente, valor, data, **status visual** |
| `xmls_baixados` | Controle de arquivos | Chave, **caminho físico**, data download |

**Sincronização:**
- `xml_status` = "COMPLETO" ⟺ Arquivo existe em `xmls_baixados.caminho_arquivo`
- Auto-detecção mantém consistência automática

---

## 📚 Referências Técnicas

### **Arquivos Relevantes:**
- `nfe_search.py` → Método `salvar_nota_detalhada()` (linhas 1447-1510)
- `nfe_search.py` → Método `registrar_xml()` (linhas 2305-2360)
- `Busca NF-e.py` → Lógica de ícones (linhas 3305-3350)

### **Estrutura de Diretórios:**
```
xmls/
├── {cnpj}/
│   ├── {ano-mes}/
│   │   ├── NFe/
│   │   │   └── {numero}-{razao_social}.xml
│   │   ├── CTe/
│   │   └── NFCe/
```

### **Schema do Banco:**
```sql
-- Tabela principal
CREATE TABLE notas_detalhadas (
    chave TEXT PRIMARY KEY,
    xml_status TEXT DEFAULT 'RESUMO',  -- ⚠️ Campo crítico
    ...
);

-- Tabela de controle
CREATE TABLE xmls_baixados (
    chave TEXT PRIMARY KEY,
    caminho_arquivo TEXT,  -- ⚠️ Campo crítico
    ...
);
```

---

## ✅ Resumo Executivo

**O que foi feito:**
1. ✅ Diagnosticado problema de 1509 XMLs "invisíveis"
2. ✅ Corrigido retroativamente todos os status
3. ✅ Implementada auto-detecção bidirecional
4. ✅ Criados scripts de diagnóstico/correção
5. ✅ Documentado processo completo

**Garantias futuras:**
- ✅ XMLs baixados aparecem automaticamente
- ✅ Status sempre sincronizado com disco
- ✅ Scripts de manutenção disponíveis
- ✅ Logs detalhados para troubleshooting

**Ação necessária:**
- 🔄 Rodar `diagnostico_xmls.py` mensalmente
- 📊 Monitorar logs de warning
- 💾 Backup antes de correções massivas

---

**Última atualização:** 27/01/2026  
**Versão:** 1.0  
**Status:** ✅ Problema resolvido e prevenido
