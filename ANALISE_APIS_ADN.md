# ANÁLISE COMPLETA - APIs ADN Nacional

## 📋 APIs Descobertas

### 1. API ADN Contribuinte (swagger 3.json)
**Endpoints**:
```
GET /DFe/{NSU}
    Parâmetros:
    - cnpjConsulta (string, opcional)
    - lote (boolean, default: true)

GET /NFSe/{ChaveAcesso}/Eventos
```

---

### 2. API ADN Município (swagger 4.json) ⭐ DIFERENÇA!
**Endpoints**:
```
GET /DFe/{NSU}
    Parâmetros:
    - tipoNSU (string) ⭐ NOVO!
        • "RECEPCAO"     → NSU de recepção (emissão)
        • "DISTRIBUICAO" → NSU de distribuição
        • "GERAL"        → Todos os NSUs
        • "MEI"          → Específico para MEI
    - lote (boolean, default: true)

GET /NFSe/{ChaveAcesso}/Eventos
```

---

### 3. API ADN Recepção
**Endpoints**:
```
POST /
    Body: {
        "LoteXmlGZipB64": ["xml1_gzip_b64", "xml2_gzip_b64", ...]
    }
    
    Response 201: Lote processado
```

---

## 🔍 HIPÓTESE: Por que notas 2025/2026 não aparecem?

### **Problema: NSU Recepção ≠ NSU Distribuição**

```
FLUXO DA NOTA:
┌─────────────────────────────────────────────────────────────┐
│ 1. EMISSÃO (Recepção)                                       │
│    POST /adn/DFe                                            │
│    → Gera NSU de RECEPÇÃO (ex: 51, 52, 53...)              │
│    → Nota visível no portal para o emissor                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
                      (Processamento)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. DISTRIBUIÇÃO                                             │
│    GET /DFe/{NSU} (sem tipoNSU)                            │
│    → Usa NSU de DISTRIBUIÇÃO por padrão                    │
│    → Pode ter delay ou não ocorrer                         │
│    → Notas podem não estar disponíveis aqui ainda!         │
└─────────────────────────────────────────────────────────────┘
```

### **Situação Atual**:
- ✅ Notas de 2025/2026 **recepcionadas** (visíveis no portal)
- ❌ Notas de 2025/2026 **não distribuídas** (não aparecem na API)

---

## 💡 SOLUÇÃO: Usar tipoNSU="RECEPCAO" ou "GERAL"

### **Teste 1: NSU de Recepção**
```http
GET /DFe/51?tipoNSU=RECEPCAO&lote=true
```
→ Busca no NSU de recepção (quando nota foi emitida)

### **Teste 2: NSU Geral (ambos)**
```http
GET /DFe/51?tipoNSU=GERAL&lote=true
```
→ Busca em todos os tipos de NSU

### **Teste 3: Sem tipoNSU (atual)**
```http
GET /DFe/51?lote=true
```
→ Usa DISTRIBUICAO por padrão (não encontra notas recentes)

---

## 🎯 AÇÃO IMEDIATA

### **Modificar consulta para incluir tipoNSU**:

**Antes** (só encontra distribuídas):
```python
GET /contribuintes/DFe/{NSU}?lote=true
```

**Depois** (encontra recepcionadas também):
```python
GET /contribuintes/DFe/{NSU}?tipoNSU=GERAL&lote=true
# ou
GET /contribuintes/DFe/{NSU}?tipoNSU=RECEPCAO&lote=true
```

---

## 📊 Tipos de NSU Explicados

### RECEPCAO
- NSU gerado quando nota é **emitida/recepcionada**
- Disponível imediatamente após emissão
- **Usa esse para notas recém-emitidas**

### DISTRIBUICAO
- NSU gerado quando nota é **distribuída**
- Pode ter delay após recepção
- Usado por padrão se não especificar

### GERAL
- **Todos os NSUs** (recepção + distribuição)
- **Recomendado usar esse!**

### MEI
- Específico para Microempreendedor Individual
- Não se aplica ao nosso caso

---

## ✅ CONCLUSÃO

**Por que as notas de 2025/2026 não apareceram**:
1. Foram **emitidas** (NSU de RECEPCAO criado)
2. Ainda não foram **distribuídas** (NSU de DISTRIBUICAO não criado)
3. Nossa busca usava endpoint sem `tipoNSU` (padrão = DISTRIBUICAO)
4. Por isso não encontramos!

**Solução**:
- Adicionar `tipoNSU=GERAL` ou `tipoNSU=RECEPCAO`
- Buscar nos mesmos NSUs (51+) mas com tipo correto
- Isso deve revelar as notas de 2025/2026!
