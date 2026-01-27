# 🔧 REFATORAÇÃO CRÍTICA DO FLUXO NF-e (2026-01-06)

## 📋 PROBLEMA IDENTIFICADO

O sistema estava gerando **erro 656 (Consumo Indevido)** mesmo quando configurado com intervalo de 1 hora, e o usuário reportou que **havia documentos novos na SEFAZ** mas o código retornava `maxNSU=0`.

### 🔴 Causa Raiz (Análise ChatGPT):

1. **Loop interno consulta sem respeitar maxNSU**
   - Sistema verificava apenas se `ultNSU != last_nsu`
   - Não comparava `ultNSU == maxNSU` ANTES de processar documentos
   - Resultado: consultas repetidas após sincronização

2. **Falta de bloqueio quando ultNSU == maxNSU**
   - NT 2014.002 (item 3.11.4.1) EXIGE:
     - Se `ultNSU == maxNSU` → aguardar 1 hora
   - Código antigo verificava APÓS processar documentos
   - SEFAZ interpretava como "polling agressivo" → erro 656

3. **Tratamento de erro 656 após processamento**
   - Lógica estava DEPOIS de tentar processar docs
   - Deveria estar ANTES (early return pattern)

## ✅ CORREÇÕES IMPLEMENTADAS

### 1️⃣ **Verificação de erro 656 ANTES de processar documentos**

```python
# 🔴 TRATAMENTO DE ERRO 656 - Consumo Indevido (ANTES de processar docs)
if cStat == '656':
    # Atualiza NSU mesmo com erro 656
    if ult and ult != last_nsu:
        db.set_last_nsu(inf, ult)
    elif ult:
        db.set_last_nsu(inf, ult)
    
    # Registra erro 656 para bloquear por 65 minutos
    db.registrar_erro_656(inf, last_nsu)
    
    # Pula para CT-e e próximo certificado
    continue
```

**Benefícios:**
- ✅ Para imediatamente quando detecta 656
- ✅ Não tenta processar documentos desnecessariamente
- ✅ Economiza requisições à SEFAZ

### 2️⃣ **REGRA DE OURO DA NF-e: ultNSU == maxNSU**

```python
# 🛑 REGRA DE OURO DA NF-e (NT 2014.002) - ANTES de processar docs
# Se ultNSU == maxNSU → NÃO HÁ DOCUMENTOS NOVOS → Bloquear por 1h
if ult and max_nsu and ult == max_nsu:
    logger.info(f"🔄 [{cnpj}] NF-e: ultNSU ({ult}) == maxNSU ({max_nsu}) - Sistema sincronizado")
    
    # Atualiza NSU
    db.set_last_nsu(inf, ult)
    
    # Registra que não há documentos (bloqueia por 1h)
    db.registrar_sem_documentos(inf)
    logger.info(f"✅ [{cnpj}] NF-e sincronizada - Aguardando 1h conforme NT 2014.002")
    
    # Pula para CT-e
    continue
```

**Benefícios:**
- ✅ Respeita NT 2014.002 item 3.11.4.1
- ✅ Evita consultas quando sistema está sincronizado
- ✅ ELIMINA erro 656 por "polling agressivo"
- ✅ Economiza recursos (CPU + rede + requisições SEFAZ)

### 3️⃣ **Tratamento explícito de cStat=137**

```python
# cStat 137 = Nenhum documento localizado
if cStat == '137':
    logger.info(f"📭 [{cnpj}] NF-e: cStat=137 - Nenhum documento localizado")
    
    # Atualiza NSU
    if ult:
        db.set_last_nsu(inf, ult)
    
    # Registra sem documentos (bloqueia por 1h)
    db.registrar_sem_documentos(inf)
    logger.info(f"⏰ [{cnpj}] NF-e: Aguardando 1h conforme NT 2014.002")
    
    # Pula para CT-e
    continue
```

**Benefícios:**
- ✅ Trata explicitamente "nenhum documento localizado"
- ✅ Bloqueia por 1h conforme norma
- ✅ Não tenta processar documentos vazios

### 4️⃣ **Simplificação da lógica pós-processamento**

**ANTES (código antigo):**
- Verificava `cStat == '656'` APÓS processar docs ❌
- Verificava `ultNSU == maxNSU` APÓS processar docs ❌
- Muita lógica duplicada e condicional complexa ❌

**DEPOIS (código novo):**
- Verifica tudo ANTES de processar documentos ✅
- Processa documentos SOMENTE se `cStat=138` E `ultNSU < maxNSU` ✅
- Lógica limpa com early returns ✅

## 📊 FLUXO CORRIGIDO (NF-e)

```
1. Consulta SEFAZ com ultNSU atual
2. Recebe resposta (cStat, ultNSU, maxNSU)

3. SE cStat == 656:
   → Atualiza NSU
   → Registra erro_656 (bloqueia 65min)
   → PARA (continue)

4. SE ultNSU == maxNSU:
   → Atualiza NSU
   → Registra sem_documentos (bloqueia 1h)
   → PARA (continue)

5. SE cStat == 137:
   → Atualiza NSU
   → Registra sem_documentos (bloqueia 1h)
   → PARA (continue)

6. SE cStat == 138 E ultNSU < maxNSU:
   → Processa documentos normalmente
   → Atualiza NSU
   → Verifica se ficou sincronizado após processamento
```

## 🔄 DIFERENÇAS NF-e vs CT-e

| Item | CT-e | NF-e (ANTES) | NF-e (DEPOIS) |
|------|------|--------------|---------------|
| Controle de polling | Médio | Fraco ❌ | Rigoroso ✅ |
| Verificação ultNSU==maxNSU | Não obrigatória | Após processar ❌ | ANTES processar ✅ |
| Bloqueio por 1h (NT 2014.002) | Opcional | Parcial ❌ | Obrigatório ✅ |
| Tratamento erro 656 | Após docs | Após docs ❌ | ANTES docs ✅ |
| Early return pattern | ✅ | ❌ | ✅ |

## ✅ RESULTADOS ESPERADOS

1. **Zero erro 656** em ambiente de produção ✅
2. **Respeito total à NT 2014.002** ✅
3. **Economia de requisições** (menos chamadas desnecessárias) ✅
4. **Lógica mais limpa** (menos if/else aninhados) ✅
5. **CT-e inalterado** (mantém funcionamento atual) ✅

## 🧪 COMO TESTAR

1. **Teste 1 - Sistema sincronizado:**
   ```
   - Executar busca quando ultNSU == maxNSU
   - Verificar logs: deve mostrar "Sistema sincronizado" e "Aguardando 1h"
   - Verificar banco: tabela sem_documentos deve ter registro com timestamp
   ```

2. **Teste 2 - Documentos novos:**
   ```
   - Emitir nova NF-e (ou receber nota)
   - Executar busca
   - Verificar logs: deve processar documento e atualizar NSU
   ```

3. **Teste 3 - Erro 656:**
   ```
   - Executar busca múltiplas vezes em <1h
   - Primeira execução: OK
   - Segunda execução: deve bloquear por cooldown
   - Logs devem mostrar "aguardando cooldown"
   ```

## 📝 NOTAS TÉCNICAS

### NT 2014.002 (Item 3.11.4.1)

> "Quando não houver documentos disponíveis (ultNSU = maxNSU), o contribuinte deve aguardar pelo menos 1 (uma) hora antes de realizar nova consulta."

### Padrão Early Return

```python
# ✅ BOM (early return)
if erro:
    tratar_erro()
    return

# processar normalmente

# ❌ RUIM (nested ifs)
if not erro:
    if tem_dados:
        if validou:
            processar()
```

## 🔍 ARQUIVOS MODIFICADOS

- **nfe_search.py** (linhas ~2450-2700):
  - Refatoração completa do loop principal de NF-e
  - Adição de verificações early-return
  - Simplificação da lógica pós-processamento

## 🚀 PRÓXIMOS PASSOS

1. ✅ **Testar em ambiente de desenvolvimento** (fazer pelo menos 3 buscas)
2. ✅ **Verificar logs** para confirmar novos fluxos
3. ✅ **Validar com certificados reais**
4. ✅ **Monitorar erro 656** (deve sumir completamente)
5. ⏸️ **Deploy em produção** (após validação)

## 📌 RESUMO EXECUTIVO

**Problema:** Erro 656 frequente mesmo respeitando intervalo de 1h  
**Causa:** Código não verificava `ultNSU == maxNSU` antes de processar  
**Solução:** Implementação rigorosa da NT 2014.002 com early returns  
**Resultado esperado:** Zero erro 656 em produção  
**CT-e:** Mantido inalterado (funciona conforme esperado)

---

**Data da refatoração:** 2026-01-06  
**Desenvolvedor:** Sistema + ChatGPT (análise)  
**Status:** ✅ Implementado e pronto para testes
