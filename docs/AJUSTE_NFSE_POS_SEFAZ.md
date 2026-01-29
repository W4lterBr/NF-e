# ✅ AJUSTE CONCLUÍDO - Busca NFS-e após Buscas SEFAZ

## 📋 Mudanças Implementadas

### 🔄 **ATUALIZAÇÃO 2026-01-29**: Removida Duplicação de NFS-e

**Problema Identificado**:
- NFS-e estava sendo processada em **DOIS lugares simultaneamente**:
  1. Dentro do `nfe_search.py` (durante loop de certificados)
  2. Via `buscar_nfse_auto.py` (script separado após conclusão)
- Causava logs intercalados, duplicação de consultas à API e confusão

**Solução Implementada**:
- ✅ **Removido**: Chamadas `processar_nfse()` do `nfe_search.py` (linhas 3937 e 4411)
- ✅ **Mantido**: Apenas execução via `buscar_nfse_auto.py` após conclusão de NF-e/CT-e
- ✅ **Vantagens**:
  - Sem duplicação de consultas à API
  - Logs organizados e sequenciais
  - NF-e/CT-e não esperam NFS-e (mais rápido)
  - Controle independente (incremental vs completa)

**Arquivo modificado**: `nfe_search.py`
```python
# ANTES (linha ~3937):
try:
    processar_nfse((cnpj, path, senha, inf, cuf), db)
except Exception as e:
    logger.exception(f"Erro geral ao processar NFS-e para {inf}: {e}")

# DEPOIS:
# ⚠️ NFS-e REMOVIDA: Será executada pelo buscar_nfse_auto.py após busca completa
```

**Mensagem de conclusão atualizada**:
```python
# ANTES:
logger.info("✅ Fase 1 concluída: Todos os documentos foram buscados (NFe, CTe, NFS-e)!")

# DEPOIS:
logger.info("✅ Fase 1 concluída: Todos os documentos foram buscados (NFe e CTe)!")
logger.info("📋 NFS-e será processada separadamente pelo buscar_nfse_auto.py")
```

---

### 1. **Removido**: Busca Automática no `refresh_all()`

**Antes**:
```python
# refresh_all() → Busca NFS-e automaticamente após carregar dados
QTimer.singleShot(2000, self._buscar_nfse_automatico)
```

**Depois**:
```python
# refresh_all() → NÃO busca mais NFS-e automaticamente
# (removido)
```

**Motivo**: Usuário não quer buscar NFS-e ao simplesmente atualizar a visualização.

---

### 2. **Adicionado**: Busca NFS-e após "Buscar na SEFAZ"

**Arquivo**: `Busca NF-e.py` → Método `do_search()`

**Linha**: ~7434 (dentro de `on_finished()`)

```python
# Após busca SEFAZ concluir com sucesso
if res.get("ok"):
    # ... consulta de eventos ...
    # ... correção de status ...
    
    # 🆕 BUSCA DE NFS-e após busca SEFAZ
    print("[PÓS-BUSCA] Agendando busca automática de NFS-e...")
    QTimer.singleShot(5000, self._buscar_nfse_automatico)
```

**Quando executa**:
- ✅ Usuário clica em **"Buscar na SEFAZ"**
- ✅ Busca de NF-e e CT-e concluída com sucesso
- ✅ 5 segundos depois → Busca NFS-e **incremental** automaticamente

---

### 3. **Adicionado**: Busca NFS-e após "Busca Completa"

**Arquivo**: `Busca NF-e.py` → Método `do_busca_completa()`

**Linha**: ~9777 (dentro de `on_finished()`)

```python
# Após Busca Completa concluir com sucesso
# ... auto-verificação ...

# 🆕 BUSCA DE NFS-e após Busca Completa
print("[PÓS-BUSCA COMPLETA] Agendando busca completa de NFS-e...")
QTimer.singleShot(10000, lambda: self._buscar_nfse_automatico(busca_completa=True))
```

**Quando executa**:
- ✅ Usuário clica em **"Busca Completa"**
- ✅ NSU resetado para 0 (NF-e, CT-e **e NFS-e**)
- ✅ Busca completa de NF-e e CT-e concluída
- ✅ 10 segundos depois → Busca NFS-e **completa** (--completa) automaticamente

---

### 4. **Modificado**: Método `_buscar_nfse_automatico()`

**Parâmetro adicionado**: `busca_completa=False`

```python
def _buscar_nfse_automatico(self, busca_completa=False):
    """
    Executa busca automática de NFS-e.
    
    Args:
        busca_completa: Se True, executa busca completa (--completa).
                       Se False, busca incremental.
    """
```

**Comportamento**:

| Parâmetro | Comando executado | Quando usar |
|-----------|-------------------|-------------|
| `busca_completa=False` | `python buscar_nfse_auto.py` | Após "Buscar na SEFAZ" |
| `busca_completa=True` | `python buscar_nfse_auto.py --completa` | Após "Busca Completa" |

**Timeout ajustado**:
- **Busca incremental**: 5 minutos (300 segundos)
- **Busca completa**: 10 minutos (600 segundos)

---

## 🎯 Fluxo Completo

### Cenário 1: Buscar na SEFAZ

```
Usuário clica "Buscar na SEFAZ"
    ↓
Sistema busca NF-e e CT-e na SEFAZ
    ↓
Busca concluída com sucesso (res.ok = True)
    ↓
3 segundos → Consulta eventos
    ↓
5 segundos → Busca NFS-e INCREMENTAL
    ↓
10 segundos → Correção de status XML
    ↓
Interface atualiza automaticamente com NFS-e
```

**Tempo total estimado**: ~20-60 segundos (depende de quantas NFS-e existem)

---

### Cenário 2: Busca Completa

```
Usuário clica "Busca Completa"
    ↓
Sistema reseta NSU (NF-e, CT-e e NFS-e)
    ↓
Busca TODOS os documentos desde o início
    ↓
Busca completa concluída (res.ok = True)
    ↓
3 segundos → Consulta eventos
    ↓
8 segundos → Auto-verificação de XMLs
    ↓
10 segundos → Busca NFS-e COMPLETA (--completa)
    ↓
Interface atualiza com TODAS NFS-e desde o início
```

**Tempo total estimado**: Vários minutos (depende do volume total)

---

### Cenário 3: Atualizar (refresh_all)

```
Usuário clica "Atualizar"
    ↓
Sistema recarrega dados do banco
    ↓
Popula tabelas com dados existentes
    ↓
NÃO busca NFS-e (apenas visualiza dados já baixados)
```

**Tempo total**: Instantâneo (1-2 segundos)

---

## ✨ NFS-e na Interface

### Onde Aparecem?

As NFS-e aparecem nas **mesmas abas** que NF-e e CT-e:

1. **"Emitidos por terceiros"** → NFS-e recebidas (você é o tomador)
2. **"Emitidos pela empresa"** → NFS-e emitidas (você é o prestador)

### Como Identificar?

Na tabela, NFS-e aparecem com:
- **Coluna "Tipo"**: `NFSe` (igual a `NFe` e `CTe`)
- **Coluna "Número"**: Número da NFS-e
- **Coluna "Valor"**: Valor do serviço

### Filtrar Apenas NFS-e

1. Clique no dropdown **"Tipo"**
2. Selecione **"NFSe"**
3. Tabela mostra apenas NFS-e

---

## 🗄️ Armazenamento

### Banco de Dados

Todas as NFS-e são salvas em:
```sql
SELECT * FROM notas_detalhadas 
WHERE tipo_documento = 'NFSe'
ORDER BY data_emissao DESC;
```

O método `load_notes()` já carrega NFS-e automaticamente (não precisa modificação).

### Arquivos Físicos

```
xmls/
└── {CNPJ}/
    └── {MES-ANO}/
        └── NFSe/
            ├── NFSe_123.xml  ← XML da nota
            └── NFSe_123.pdf  ← PDF oficial
```

---

## 🔍 Logs para Debug

### Busca Incremental

```
[PÓS-BUSCA] Agendando busca automática de NFS-e...
[NFS-e] Thread de busca INCREMENTAL NFS-e iniciada
[NFS-e] Iniciando busca INCREMENTAL de NFS-e...
[NFS-e] ✅ Busca INCREMENTAL de NFS-e concluída com sucesso
```

### Busca Completa

```
[PÓS-BUSCA COMPLETA] Agendando busca completa de NFS-e...
[NFS-e] Thread de busca COMPLETA NFS-e iniciada
[NFS-e] Iniciando busca COMPLETA de NFS-e...
[NFS-e] ✅ Busca COMPLETA de NFS-e concluída com sucesso
```

### Busca Já em Execução

```
[NFS-e] Busca NFS-e já em execução, pulando...
```

---

## ⏱️ Temporização

| Ação | Delay | Motivo |
|------|-------|--------|
| Consulta eventos | 3s | Aguarda busca NF-e/CT-e finalizar |
| **Busca NFS-e** | **5s** | Aguarda eventos e correções |
| Correção status XML | 10s | Aguarda eventos processarem |

**Por que 5 segundos para NFS-e?**
- ✅ Consulta de eventos (3s) tem prioridade
- ✅ Não sobrecarrega sistema imediatamente
- ✅ Usuário vê primeiro os resultados de NF-e/CT-e

---

## 🆘 Troubleshooting

### NFS-e não aparecem na interface

**1. Verifique se a busca executou**:
```bash
# Veja os logs
type logs\busca_nfe_2026-01-29.log | findstr NFS-e
```

**2. Verifique se há NFS-e no banco**:
```sql
SELECT COUNT(*) FROM notas_detalhadas WHERE tipo_documento = 'NFSe';
```

**3. Force refresh**:
- Clique em **"Atualizar"** após a busca concluir

### Busca NFS-e não inicia

**1. Verifique se busca SEFAZ teve sucesso**:
- Busca NFS-e só executa se `res.ok = True`
- Se busca SEFAZ falhou, NFS-e não será buscada

**2. Verifique se script existe**:
```bash
dir buscar_nfse_auto.py
```

**3. Teste manualmente**:
```bash
.\.venv\Scripts\python.exe buscar_nfse_auto.py
```

### Timeout na busca NFS-e

**Busca incremental**:
- Timeout: 5 minutos
- Se exceder, processo é encerrado automaticamente

**Busca completa**:
- Timeout: 10 minutos
- Pode demorar mais se tiver muitas NFS-e

**Solução**: Aumentar timeout no código (linha ~2614):
```python
timeout=600  # 10 minutos → Aumente se necessário
```

---

## ✅ Validação

### Como Testar

1. **Clique em "Buscar na SEFAZ"**
2. Aguarde busca NF-e/CT-e concluir
3. Observe logs:
   ```
   [PÓS-BUSCA] Agendando busca automática de NFS-e...
   [NFS-e] Thread de busca INCREMENTAL NFS-e iniciada
   ```
4. Após ~30-60 segundos, clique **"Atualizar"**
5. Verifique se NFS-e aparecem na tabela

### Teste com Busca Completa

1. **Clique em "Busca Completa"** → Confirme
2. Aguarde busca completa de NF-e/CT-e
3. Observe logs:
   ```
   [PÓS-BUSCA COMPLETA] Agendando busca completa de NFS-e...
   [NFS-e] Thread de busca COMPLETA NFS-e iniciada
   ```
4. Após ~5-10 minutos, clique **"Atualizar"**
5. Verifique se TODAS NFS-e foram baixadas

---

## 📊 Comportamento Esperado

### Após "Buscar na SEFAZ"

| Item | Esperado |
|------|----------|
| NF-e baixadas | ✅ Sim (novos documentos) |
| CT-e baixados | ✅ Sim (novos documentos) |
| NFS-e baixadas | ✅ Sim (novos documentos) |
| Interface atualiza | ✅ Automático (após cada busca) |
| Tempo total | ~20-60 segundos |

### Após "Busca Completa"

| Item | Esperado |
|------|----------|
| NSU resetado | ✅ Sim (NF-e, CT-e e NFS-e) |
| NF-e baixadas | ✅ Sim (TODOS desde início) |
| CT-e baixados | ✅ Sim (TODOS desde início) |
| NFS-e baixadas | ✅ Sim (TODOS desde início) |
| Interface atualiza | ✅ Automático |
| Tempo total | Vários minutos |

### Após "Atualizar"

| Item | Esperado |
|------|----------|
| NF-e baixadas | ❌ Não (apenas visualiza) |
| CT-e baixados | ❌ Não (apenas visualiza) |
| NFS-e baixadas | ❌ Não (apenas visualiza) |
| Interface atualiza | ✅ Sim (recarrega do banco) |
| Tempo total | Instantâneo (1-2s) |

---

## 🎉 Resultado Final

✅ **Busca NFS-e agora executa automaticamente após**:
- "Buscar na SEFAZ" → Busca incremental (5s delay)
- "Busca Completa" → Busca completa (10s delay)

✅ **NFS-e aparecem na interface** junto com NF-e e CT-e

✅ **Sistema não busca NFS-e** ao clicar "Atualizar" (apenas visualiza)

✅ **Timeout aumentado** para busca completa (10 minutos)

✅ **Logs informativos** em todas as etapas

---

**Data da implementação**: 29/01/2026  
**Versão**: BOT Busca NFE v2.0  
**Status**: ✅ PRONTO PARA USO
