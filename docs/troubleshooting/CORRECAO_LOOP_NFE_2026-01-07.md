# Correção do Loop NF-e - 2026-01-07

## 🐛 Problema Identificado

O sistema processava apenas **50 documentos por execução** e parava, mesmo quando havia milhares de documentos disponíveis (ultNSU < maxNSU).

### Evidência do Problema

**Log 2026-01-07**:
```
ultNSU=59075, maxNSU=61722 (2.697 documentos restantes)
Sistema parou após processar 50 documentos
```

### Causa Raiz

**Arquitetura Inconsistente**: CT-e tinha loop while, NF-e não tinha.

```python
# ❌ NF-e ANTES (SEM LOOP)
resp = svc.fetch_by_cnpj("CNPJ", last_nsu)  # Uma única consulta
if not resp:
    logger.warning(...)
else:
    # Processa 50 docs e SAI
    # Não consulta novamente até próxima execução (1h depois)

# ✅ CT-e (COM LOOP)
while iteration_count < max_iterations:
    resp = svc_cte.fetch_by_cnpj(...)
    # Processa docs
    if ult == last_nsu_cte:
        break
    last_nsu_cte = ult  # Atualiza NSU e continua
```

## ✅ Solução Implementada

### 1. Adição de Loop While

```python
# ✅ NF-e DEPOIS (COM LOOP)
max_iterations = 100  # Limite de segurança
iteration_count = 0

while iteration_count < max_iterations:
    iteration_count += 1
    logger.info(f"🔄 [{cnpj}] NF-e iteração {iteration_count}/{max_iterations}, NSU atual: {last_nsu}")
    
    resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
    if not resp:
        logger.warning(f"Sem resposta NFe para {inf} na iteração {iteration_count}")
        break
    
    # Processa resposta (cStat, ultNSU, maxNSU)
    
    # Early returns (erro 656, sincronizado, sem documentos)
    if cStat == '656':
        # ...registra erro...
        break  # Sai do loop NF-e
    
    if ult == max_nsu:
        # ...registra sincronizado...
        break  # Sai do loop NF-e
    
    if cStat == '137':
        # ...registra sem documentos...
        break  # Sai do loop NF-e
    
    # [... processa documentos ...]
    
    # 🔄 Controle do loop
    if ult and max_nsu:
        if ult == max_nsu:
            logger.info(f"✅ Sincronizado")
            break
        else:
            # Ainda há documentos
            docs_restantes = int(max_nsu) - int(ult)
            logger.info(f"🔄 Ainda há ~{docs_restantes} documentos - continuando")
            
            # Atualiza NSU para próxima iteração
            last_nsu = ult
            db.set_last_nsu(inf, ult)
            continue  # Volta ao início do loop
```

### 2. Regras de Break

| Condição | Ação | Motivo |
|----------|------|--------|
| `cStat == '656'` | `break` | Erro 656 - aguardar 65 minutos |
| `ultNSU == maxNSU` | `break` | Sincronizado - aguardar 1h |
| `cStat == '137'` | `break` | Sem documentos - aguardar 1h |
| `ultNSU < maxNSU` | `continue` | **HÁ DOCUMENTOS - continuar imediatamente** |
| `iteration >= 100` | `break` | Limite de segurança |

## 📊 Comportamento Esperado

### Cenário 1: Há Documentos (ultNSU < maxNSU)

```
Iteração 1: NSU 59025 → 59075 (50 docs) ✅ Continua
Iteração 2: NSU 59075 → 59125 (50 docs) ✅ Continua
Iteração 3: NSU 59125 → 59175 (50 docs) ✅ Continua
...
Iteração 54: NSU 61675 → 61722 (47 docs) ✅ Sincronizado!
```

**Total**: 54 iterações, 2.697 documentos processados

### Cenário 2: Sistema Sincronizado (ultNSU == maxNSU)

```
Iteração 1: ultNSU=61722, maxNSU=61722
✅ BREAK imediato (não consulta SEFAZ)
⏰ Aguarda 1 hora
```

### Cenário 3: Erro 656

```
Iteração 1: cStat=656
🚫 BREAK imediato
🔒 Aguarda 65 minutos
```

## 🎯 Impacto

### Antes
- ❌ Processava apenas 50 documentos por execução
- ❌ Deixava milhares de documentos pendentes
- ❌ Usuário tinha que esperar 1h entre cada lote de 50
- ❌ Levaria **54 horas** para processar 2.697 documentos

### Depois
- ✅ Processa TODOS os documentos disponíveis em uma execução
- ✅ Loop automático até ultNSU == maxNSU
- ✅ **SEM ESPERA** quando ultNSU < maxNSU
- ✅ Processa 2.697 documentos em **~54 requisições** (poucos minutos)

## 🧪 Teste

Execute a simulação:

```bash
python test_nfe_loop.py
```

Resultado esperado:
- Cenário 1: 54 iterações, 2.697 documentos
- Cenário 2: 1 iteração, 0 documentos (sincronizado)
- Cenário 3: Break imediato (erro 656)
- Cenário 4: Break imediato (cStat 137)

## 📝 NT 2014.002 - Regra de Ouro

```
SE ultNSU < maxNSU:
    → HÁ DOCUMENTOS
    → CONSULTAR IMEDIATAMENTE (sem esperar)
    → Continuar até sincronizar

SE ultNSU == maxNSU:
    → SINCRONIZADO
    → AGUARDAR 1 HORA
    → Evita erro 656
```

## ✅ Arquivos Modificados

- [nfe_search.py](nfe_search.py) - Linhas ~2424-2720
  - Adicionado loop while (similar ao CT-e)
  - Adicionado controle de iterações
  - Adicionado lógica de break/continue
  - Adicionado atualização automática de NSU

## 🔗 Documentação Relacionada

- [REFATORACAO_NFE_2026-01-06.md](REFATORACAO_NFE_2026-01-06.md) - Early return pattern
- [CORRECAO_TIMEZONE_2026-01-06.md](CORRECAO_TIMEZONE_2026-01-06.md) - Correção de timezone
- [CONSULTA_POR_CHAVE_vs_NSU.md](CONSULTA_POR_CHAVE_vs_NSU.md) - Entendimento do NSU
