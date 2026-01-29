# 🔧 Correção do Problema de Cooldown (2026-01-06)

## 📋 PROBLEMA IDENTIFICADO

Após implementar a refatoração completa do fluxo NF-e, o sistema continuava exibindo mensagens de cooldown mesmo horas após a última execução.

### 🔍 Diagnóstico

1. **Sintoma**: `Bloqueado por erro 656 - aguarde 267.9 minutos`
2. **Causa Raiz**: **Mistura de Timezones no banco de dados**
   
   - **Ao salvar**: Código usava `datetime('now')` do SQLite = **UTC**
   - **Ao comparar**: Código usava `datetime.now()` do Python = **Local (UTC-3 no Brasil)**
   
3. **Resultado**: Sistema pensava que bloqueios do futuro estavam ativos
   - Bloqueio registrado: `2026-01-06 15:21:53` (UTC)
   - Comparação com: `2026-01-06 12:06:00` (Local)
   - Diferença: **-175 minutos** (negativo = "bloqueio futuro")

### 📊 Evidências do Problema

```log
🔒 CNPJ: 33251845000109
   📅 Bloqueado em: 2026-01-06 15:21:53
   ⏱️  Faz -175.3 minutos      ← NEGATIVO!
   📊 NSU bloqueado: SYNC
   ⏰ ATIVO (bloqueado)
```

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. Correção das Funções de Registro (nfe_search.py)

#### `registrar_erro_656()` - Linha ~1312

**ANTES**:
```python
conn.execute(
    "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, datetime('now'), ?)",
    (informante, nsu)  # ❌ SQLite datetime('now') = UTC
)
```

**DEPOIS**:
```python
from datetime import datetime
agora_utc = datetime.utcnow().isoformat()
conn.execute(
    "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, ?)",
    (informante, agora_utc, nsu)  # ✅ Explicitamente UTC
)
```

#### `registrar_sem_documentos()` - Linha ~1323

**ANTES**:
```python
conn.execute(
    "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, datetime('now'), 'SYNC')",
    (informante,)  # ❌ SQLite datetime('now') = UTC
)
```

**DEPOIS**:
```python
from datetime import datetime
agora_utc = datetime.utcnow().isoformat()
conn.execute(
    "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, 'SYNC')",
    (informante, agora_utc)  # ✅ Explicitamente UTC
)
```

#### `pode_consultar_certificado()` - Linha ~1359

**ANTES**:
```python
ultimo_erro = datetime.fromisoformat(ultimo_erro_str)
agora = datetime.now()  # ❌ Local time (UTC-3)
diferenca = (agora - ultimo_erro).total_seconds() / 60
```

**DEPOIS**:
```python
ultimo_erro = datetime.fromisoformat(ultimo_erro_str)
agora = datetime.utcnow()  # ✅ UTC time
diferenca = (agora - ultimo_erro).total_seconds() / 60
```

#### `marcar_primeira_consulta()` - Linha ~1334

**ANTES**:
```python
conn.execute(
    "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, datetime('now'))",
    (f'primeira_consulta_{informante}',)  # ❌ SQLite datetime('now')
)
```

**DEPOIS**:
```python
from datetime import datetime
agora_utc = datetime.utcnow().isoformat()
conn.execute(
    "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
    (f'primeira_consulta_{informante}', agora_utc)  # ✅ Explicitamente UTC
)
```

### 2. Limpeza do Banco de Dados

Criado script `limpar_bloqueios.py` para:
1. Remover todos os bloqueios com timezone incorreto
2. Criar tabela `sem_documentos` (estava faltando)
3. Verificar estado final

**Execução**:
```bash
python limpar_bloqueios.py
```

**Resultado**:
```
✅ Todos os 5 bloqueios foram removidos
✅ Tabela sem_documentos criada com sucesso!

📋 ESTADO ATUAL:
   • Bloqueios erro_656: 0
   • Registros sem_documentos: 0
```

### 3. Script de Verificação

Criado `check_erro_656.py` para diagnóstico:
- Lista todos os bloqueios ativos
- Calcula tempo desde último erro
- Identifica bloqueios expirados vs. ativos

## 🎯 RESULTADO FINAL

### Antes da Correção:
```log
[48160135000140] Bloqueado por erro 656 - aguarde 267.9 minutos
⏭️ NF-e: Pulando consulta - aguardando cooldown de erro 656 anterior
```

### Depois da Correção:
- ✅ Timezones consistentes (sempre UTC)
- ✅ Bloqueios expirados removidos
- ✅ Sistema pode consultar SEFAZ sem cooldowns falsos
- ✅ Tabela `sem_documentos` criada e operacional

## 📝 ARQUIVOS MODIFICADOS

1. **nfe_search.py**:
   - `registrar_erro_656()` - linha ~1312
   - `registrar_sem_documentos()` - linha ~1323
   - `pode_consultar_certificado()` - linha ~1359
   - `marcar_primeira_consulta()` - linha ~1334

2. **Novos Scripts**:
   - `limpar_bloqueios.py` - Limpeza de bloqueios antigos
   - `check_erro_656.py` - Verificação de estado do banco

## 🔄 IMPACTO NAS FUNCIONALIDADES

### ✅ Comportamento Correto:
- Bloqueios de 65 minutos (erro 656) agora funcionam corretamente
- Bloqueios de 1 hora (ultNSU==maxNSU) agora funcionam corretamente
- Comparações de tempo precisas (UTC vs. UTC)

### 🚀 Melhorias:
- Timezone consistente em todo o sistema
- Logs mais precisos sobre tempo de bloqueio
- Tabela `sem_documentos` implementada (antes inexistente)

## 🧪 COMO TESTAR

1. **Executar limpeza** (se ainda houver bloqueios antigos):
   ```bash
   python limpar_bloqueios.py
   ```

2. **Verificar estado**:
   ```bash
   python check_erro_656.py
   ```

3. **Executar busca de NF-e**:
   ```bash
   python nfe_search.py
   ```

4. **Verificar logs**:
   - ✅ Deve consultar SEFAZ sem mensagens de cooldown
   - ✅ Se receber erro 656, deve bloquear por **exatamente 65 minutos**
   - ✅ Se ultNSU==maxNSU, deve bloquear por **exatamente 60 minutos**

## 🎓 LIÇÕES APRENDIDAS

1. **Sempre usar o mesmo timezone** para salvar e comparar timestamps
2. **UTC é preferível** para logs de sistema (evita problemas de horário de verão)
3. **Testar com dados reais** do banco antes de confiar em suposições
4. **Verificar criação de tabelas** durante migrações (sem_documentos estava faltando)

## 📚 DOCUMENTOS RELACIONADOS

- [REFATORACAO_NFE_2026-01-06.md](REFATORACAO_NFE_2026-01-06.md) - Refatoração do fluxo NF-e
- [DIAGNOSTICO_ERRO_656.md](DIAGNOSTICO_ERRO_656.md) - Análise original do erro 656
- [NT 2014.002](DOCUMENTACAO_SISTEMA.md#nt-2014002) - Regras da SEFAZ

---

**Data**: 2026-01-06  
**Status**: ✅ RESOLVIDO  
**Próximos passos**: Monitorar logs para confirmar comportamento correto
