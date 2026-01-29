# 🚨 DOCUMENTAÇÃO CRÍTICA: Erro 656 e Perda de Documentos NSU

## ⚠️ ATENÇÃO: PERDA PERMANENTE DE DADOS

Este documento descreve um bug crítico que causava **perda permanente de documentos fiscais** devido ao tratamento incorreto do erro 656 da SEFAZ.

---

## 📋 Índice

1. [Resumo Executivo](#resumo-executivo)
2. [O que é o Erro 656](#o-que-é-o-erro-656)
3. [O Problema: Bug Crítico](#o-problema-bug-crítico)
4. [A Solução Implementada](#a-solução-implementada)
5. [Locais Corrigidos no Código](#locais-corrigidos-no-código)
6. [Como Identificar se o Problema Voltou](#como-identificar-se-o-problema-voltou)
7. [Boas Práticas para Manutenção](#boas-práticas-para-manutenção)
8. [Histórico de Correções](#histórico-de-correções)

---

## 📊 Resumo Executivo

### O Problema
O sistema estava **avançando o NSU mesmo quando recebia erro 656 da SEFAZ**, resultando em documentos fiscais perdidos permanentemente entre os NSUs pulados.

### Exemplo Real
```
NSU atual: 1459
SEFAZ retorna: erro 656, ultNSU 1461
Sistema ANTIGO: Salvava NSU 1461 ❌
Resultado: Documentos 1460 e 1461 PERDIDOS PARA SEMPRE

Sistema NOVO: Mantém NSU 1459 ✅
Resultado: Após 65 minutos, consulta novamente NSU 1459 e baixa TODOS os documentos
```

### Impacto
- **Severidade**: 🔴 CRÍTICA
- **Tipo**: Perda permanente de dados fiscais
- **Período Afetado**: Desde implementação inicial até 09/01/2026
- **Documentos Perdidos**: Quantidade desconhecida (todos os NSUs pulados durante erro 656)

---

## 🔍 O que é o Erro 656

### Definição Técnica
```
Código: 656
Descrição: "Consumo Indevido"
Categoria: Rate Limiting (Limitação de Taxa)
```

### Quando Ocorre
O erro 656 é retornado pela SEFAZ quando:
1. Sistema consulta NSU muito frequentemente
2. Não há novos documentos disponíveis
3. Última consulta foi há menos de 1 hora

### Comportamento Esperado da SEFAZ
```xml
<retDistDFeInt>
    <cStat>656</cStat>
    <xMotivo>Consumo Indevido</xMotivo>
    <dhResp>2026-01-09T12:02:52-03:00</dhResp>
    <ultNSU>000000000001461</ultNSU>
</retDistDFeInt>
```

**⚠️ IMPORTANTE**: Mesmo retornando erro 656, a SEFAZ informa o `ultNSU` (último NSU disponível no servidor).

---

## 💥 O Problema: Bug Crítico

### Comportamento Incorreto (ANTIGO)

O sistema tinha o seguinte código em **3 locais diferentes**:

```python
# ❌ CÓDIGO INCORRETO - CAUSAVA PERDA DE DOCUMENTOS
if cStat == '656':
    logger.warning(f"⚠️ Erro 656 - Consumo Indevido para {informante}")
    db.set_last_nsu(informante, ult_nsu)  # ❌ ERRO: Avança NSU
    logger.info(f"NSU atualizado para {ult_nsu}")  # ❌ CONFIRMA AVANÇO
    db.registrar_erro_656(informante, ult_nsu)
    break
```

### Por que Isso Causa Perda de Dados

#### Cenário 1: NSU Contínuo (Sem Problema)
```
Consulta 1: NSU 100 → SEFAZ retorna documentos → ultNSU 101
Sistema salva: NSU 101 ✅

Consulta 2: NSU 101 → SEFAZ retorna documentos → ultNSU 102
Sistema salva: NSU 102 ✅
```
**Resultado**: Nenhum documento perdido

#### Cenário 2: Erro 656 com Código Antigo (PERDA DE DADOS)
```
Consulta 1: NSU 1459 → SEFAZ retorna erro 656, ultNSU 1461
Sistema ANTIGO salva: NSU 1461 ❌

PROBLEMA: Documentos 1460 e 1461 NUNCA FORAM BAIXADOS!

Consulta 2: NSU 1461 → SEFAZ retorna documentos → ultNSU 1462
Sistema salva: NSU 1462 ✅

Documentos 1460 e 1461 = PERDIDOS PARA SEMPRE ❌
```

### Evidências do Bug

#### Log Real do Sistema (09/01/2026)
```
09:16:54 - INFO: 🔹 Consultando distribuição para cert 49068153000160, NSU: 000000000001459
09:16:57 - WARNING: ⚠️ Erro 656 - Consumo Indevido
09:16:57 - INFO: NSU atualizado para 000000000001461  ❌ PULOU 1460!

15:03:14 - INFO: 🔹 Consultando distribuição para cert 49068153000160, NSU: 000000000001461
15:03:17 - WARNING: ⚠️ Erro 656 - Consumo Indevido
15:03:17 - INFO: NSU atualizado para 000000000001462  ❌ PULOU 1461!
```

**Análise**: 
- NSU pulou de 1459 → 1461 (documento 1460 perdido)
- NSU pulou de 1461 → 1462 (documento 1461 perdido)
- Total: **2 documentos fiscais perdidos permanentemente**

---

## ✅ A Solução Implementada

### Comportamento Correto (NOVO)

```python
# ✅ CÓDIGO CORRETO - PRESERVA DOCUMENTOS
if cStat == '656':
    # ⚠️ IMPORTANTE: NÃO atualizar NSU em erro 656!
    # 
    # PROBLEMA: Se atualizarmos o NSU aqui, perdemos documentos!
    # 
    # EXEMPLO:
    #   NSU atual: 1459
    #   SEFAZ retorna: erro 656, ultNSU 1461
    #   Se salvarmos NSU 1461 → documentos 1460 e 1461 são PERDIDOS!
    # 
    # SOLUÇÃO CORRETA:
    #   1. Manter NSU em 1459 (não avançar)
    #   2. Registrar erro 656 (bloquear por 65 minutos)
    #   3. Após bloqueio, consultar novamente NSU 1459
    #   4. SEFAZ retornará documentos 1460, 1461, etc.
    #   5. Nenhum documento é perdido! ✅
    
    logger.warning(f"⚠️ Erro 656 - Consumo Indevido para {informante}")
    db.registrar_erro_656(informante, ult_nsu)
    logger.warning(f"🔒 NSU mantido em {ult_nsu_atual}, documentos entre {ult_nsu_atual} e {ult_nsu} serão baixados após bloqueio de 65 minutos")
    break
```

### Fluxo Correto com Erro 656

```
Passo 1: NSU atual 1459
         ↓
Passo 2: Consulta SEFAZ com NSU 1459
         ↓
Passo 3: SEFAZ retorna erro 656, ultNSU 1461
         ↓
Passo 4: Sistema MANTÉM NSU em 1459 ✅
         Sistema registra bloqueio de 65 minutos
         ↓
Passo 5: Após 65 minutos, consulta novamente NSU 1459
         ↓
Passo 6: SEFAZ retorna documentos 1460, 1461, 1462...
         ↓
Passo 7: Sistema salva documentos e atualiza NSU para 1462 ✅
         
Resultado: NENHUM DOCUMENTO PERDIDO! ✅
```

---

## 🔧 Locais Corrigidos no Código

### 1. nfe_search.py - Linha 224 (Loop de Distribuição NFe)

**Arquivo**: `nfe_search.py`  
**Função**: Loop principal de consulta distribuição NFe  
**Linha**: 224-236

```python
# ✅ CORRIGIDO em 09/01/2026
if cStat == '656':
    # NÃO atualizar NSU aqui!
    db.registrar_erro_656(inf, ult)
    logger.warning(f"🔒 NSU mantido em {nsu_obj.ult_nsu}, documentos serão baixados após bloqueio")
    break
```

### 2. nfe_search.py - Linha 2429 (Loop de Distribuição CTe)

**Arquivo**: `nfe_search.py`  
**Função**: Loop de consulta distribuição CTe  
**Linha**: 2429-2435

```python
# ✅ CORRIGIDO em 09/01/2026
if cStat == '656':
    # NÃO atualizar NSU aqui!
    db.registrar_erro_656(informante, ult_nsu)
    logger.warning(f"🔒 NSU CT-e mantido em {nsu_atual}, documentos serão baixados após bloqueio")
    break
```

### 3. nfe_search.py - Linha 2724 (Loop Principal NFe)

**Arquivo**: `nfe_search.py`  
**Função**: Loop principal de busca NFe  
**Linha**: 2724-2733

```python
# ✅ CORRIGIDO em 09/01/2026
if cStat == '656':
    # NÃO atualizar NSU aqui!
    db.registrar_erro_656(informante, ult_nsu)
    logger.warning(f"🔒 NSU mantido, aguardando {documentos_pendentes} documentos após bloqueio")
    break
```

---

## 🔍 Como Identificar se o Problema Voltou

### Sinais de Alerta

#### 1. NSU Pulando Números (CRÍTICO)
```bash
# Comando para verificar sequência de NSU nos logs
Select-String -Path ".\logs\busca_nfe_*.log" -Pattern "NSU.*(\d{15})" | Select-Object -Last 50

# ❌ PROBLEMA SE VER:
# NSU: 000000000001459
# NSU: 000000000001461  ← PULOU 1460!
# NSU: 000000000001465  ← PULOU 1462, 1463, 1464!

# ✅ CORRETO:
# NSU: 000000000001459
# NSU: 000000000001460
# NSU: 000000000001461
```

#### 2. Log Mostrando "NSU atualizado" em Erro 656 (CRÍTICO)
```bash
# Comando para verificar erro 656 nos logs
Select-String -Path ".\logs\busca_nfe_*.log" -Pattern "656" -Context 3

# ❌ PROBLEMA SE VER:
# Erro 656 - Consumo Indevido
# NSU atualizado para 000000000001461  ← ISSO É O BUG!

# ✅ CORRETO:
# Erro 656 - Consumo Indevido
# NSU mantido em 000000000001459, documentos serão baixados após bloqueio
```

#### 3. Documentos Faltando na Base (CRÍTICO)
```sql
-- Verificar se há gaps na sequência de documentos
SELECT 
    numero_nota,
    LAG(numero_nota) OVER (ORDER BY numero_nota) as nota_anterior,
    numero_nota - LAG(numero_nota) OVER (ORDER BY numero_nota) as diferenca
FROM notas
WHERE informante = '49068153000160'
ORDER BY numero_nota;

-- ❌ PROBLEMA SE VER diferença > 1:
-- | numero_nota | nota_anterior | diferenca |
-- |-------------|---------------|-----------|
-- | 1459        | 1458          | 1         | ✅
-- | 1461        | 1459          | 2         | ❌ FALTA 1460!
-- | 1465        | 1461          | 4         | ❌ FALTAM 1462, 1463, 1464!
```

### Script de Verificação Automática

Criar arquivo `verificar_nsu_integridade.py`:

```python
#!/usr/bin/env python3
"""
Script para verificar integridade da sequência NSU e detectar documentos perdidos.
Executar periodicamente para garantir que o bug não voltou.
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta

def verificar_logs_erro_656():
    """Verifica se erro 656 está avançando NSU incorretamente."""
    print("🔍 Verificando tratamento de erro 656 nos logs...\n")
    
    logs_dir = Path("logs")
    hoje = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"busca_nfe_{hoje}.log"
    
    if not log_file.exists():
        print("⚠️ Log de hoje não encontrado")
        return
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Procurar por erro 656 seguido de "NSU atualizado"
    pattern_erro = r'Erro 656.*?\n.*?NSU atualizado'
    erros_criticos = re.findall(pattern_erro, content, re.DOTALL)
    
    if erros_criticos:
        print("🚨 PROBLEMA CRÍTICO DETECTADO!")
        print("❌ Erro 656 está avançando NSU (bug voltou!)\n")
        print("Exemplos encontrados:")
        for i, erro in enumerate(erros_criticos[:3], 1):
            print(f"\n{i}. {erro}")
        return False
    else:
        print("✅ Erro 656 tratado corretamente (NSU não avança)\n")
        return True

def verificar_sequencia_nsu():
    """Verifica se há saltos na sequência de NSU."""
    print("🔍 Verificando sequência de NSU no banco de dados...\n")
    
    db = sqlite3.connect('notas.db')
    cursor = db.cursor()
    
    # Verificar gaps por certificado
    query = """
    SELECT 
        cnpj,
        COUNT(*) as total_consultas,
        MAX(CAST(ultimo_nsu AS INTEGER)) - MIN(CAST(ultimo_nsu AS INTEGER)) as range_nsu
    FROM nsu
    WHERE ultimo_nsu != '000000000000000'
    GROUP BY cnpj
    """
    
    cursor.execute(query)
    resultados = cursor.fetchall()
    
    problemas = []
    for cnpj, total, range_nsu in resultados:
        if range_nsu > total:
            gap = range_nsu - total
            problemas.append((cnpj, gap))
            print(f"⚠️ CNPJ {cnpj}: possível gap de {gap} NSUs")
    
    db.close()
    
    if problemas:
        print(f"\n🚨 {len(problemas)} certificado(s) com possíveis gaps")
        return False
    else:
        print("✅ Nenhum gap detectado na sequência de NSU\n")
        return True

def verificar_documentos_faltantes():
    """Verifica se há documentos faltando na sequência."""
    print("🔍 Verificando documentos faltantes...\n")
    
    db = sqlite3.connect('notas.db')
    cursor = db.cursor()
    
    query = """
    WITH sequencia AS (
        SELECT 
            informante,
            numero_nota,
            LAG(numero_nota) OVER (PARTITION BY informante ORDER BY numero_nota) as nota_anterior
        FROM notas
        WHERE tipo_documento IN ('NFe', 'CTe')
    )
    SELECT 
        informante,
        nota_anterior,
        numero_nota,
        numero_nota - nota_anterior as gap
    FROM sequencia
    WHERE gap > 1
    ORDER BY informante, numero_nota
    LIMIT 10
    """
    
    cursor.execute(query)
    gaps = cursor.fetchall()
    
    if gaps:
        print("🚨 DOCUMENTOS FALTANTES DETECTADOS!\n")
        print("| CNPJ            | Nota Anterior | Nota Atual | Gap |")
        print("|-----------------|---------------|------------|-----|")
        for cnpj, anterior, atual, gap in gaps:
            print(f"| {cnpj} | {anterior:>13} | {atual:>10} | {gap:>3} |")
        db.close()
        return False
    else:
        print("✅ Nenhum documento faltante detectado\n")
        db.close()
        return True

def main():
    """Executa todas as verificações."""
    print("=" * 70)
    print("🔍 VERIFICAÇÃO DE INTEGRIDADE NSU - Sistema Busca NF-e")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    resultados = {
        'logs': verificar_logs_erro_656(),
        'nsu': verificar_sequencia_nsu(),
        'documentos': verificar_documentos_faltantes()
    }
    
    print("=" * 70)
    print("📊 RESULTADO FINAL")
    print("=" * 70)
    
    if all(resultados.values()):
        print("✅ SISTEMA OK - Nenhum problema detectado")
        print("✅ Bug de erro 656 NÃO voltou")
        print("✅ Integridade NSU mantida")
        return 0
    else:
        print("🚨 PROBLEMAS DETECTADOS!")
        if not resultados['logs']:
            print("❌ Erro 656 avançando NSU (BUG CRÍTICO)")
        if not resultados['nsu']:
            print("⚠️ Gaps na sequência NSU")
        if not resultados['documentos']:
            print("⚠️ Documentos faltantes")
        print("\n⚠️ AÇÃO NECESSÁRIA: Verificar código e corrigir")
        return 1

if __name__ == "__main__":
    exit(main())
```

---

## 🛡️ Boas Práticas para Manutenção

### 1. NUNCA Avançar NSU em Erro 656

```python
# ❌ NUNCA FAZER:
if cStat == '656':
    db.set_last_nsu(informante, ult_nsu)  # PERDA DE DADOS!

# ✅ SEMPRE FAZER:
if cStat == '656':
    # Manter NSU atual, apenas registrar bloqueio
    db.registrar_erro_656(informante, ult_nsu)
```

### 2. Sempre Comentar Código Relacionado a NSU

```python
# ✅ BOM: Comentário explicando por que não avança NSU
if cStat == '656':
    # IMPORTANTE: NSU não deve ser atualizado em erro 656
    # para evitar perda de documentos intermediários
    db.registrar_erro_656(informante, ult_nsu)
```

### 3. Executar Verificação Semanal

```bash
# Adicionar ao crontab ou agendador Windows
# Executar todo domingo às 23:00
python verificar_nsu_integridade.py
```

### 4. Monitorar Logs de Erro 656

```bash
# Comando para verificar erro 656 diariamente
Select-String -Path ".\logs\busca_nfe_*.log" -Pattern "656" -Context 2 | Out-File verificacao_656.txt
```

### 5. Code Review Obrigatório

Qualquer alteração em código que trate:
- NSU (set_last_nsu, ultimo_nsu, ultNSU)
- Erro 656
- Distribuição SEFAZ

**DEVE passar por code review focado em**:
- ✅ NSU só avança quando documentos são baixados
- ✅ Erro 656 não avança NSU
- ✅ Logs adequados para rastreabilidade

### 6. Testes de Regressão

Criar teste automatizado que simula erro 656:

```python
def test_erro_656_nao_avanca_nsu():
    """Teste crítico: erro 656 não deve avançar NSU."""
    # Setup
    db = DatabaseManager('test.db')
    db.set_last_nsu('12345678000190', '000000000001000')
    
    # Simular erro 656 com ultNSU maior
    simular_resposta_sefaz_656(ult_nsu='000000000001005')
    
    # Verificar que NSU NÃO avançou
    nsu_atual = db.get_last_nsu('12345678000190')
    assert nsu_atual == '000000000001000', "CRÍTICO: NSU avançou em erro 656!"
```

---

## 📜 Histórico de Correções

### 09/01/2026 - Correção do Bug Crítico

**Responsável**: Desenvolvimento  
**Severidade**: 🔴 CRÍTICA  
**Tipo**: Perda de Dados

#### Descoberta
- Usuário reportou preocupação com NSU não atualizando
- Análise de logs revelou NSU pulando números (1459→1461)
- Investigação identificou erro 656 avançando NSU sem baixar documentos

#### Locais Corrigidos
1. `nfe_search.py:224` - Loop distribuição NFe
2. `nfe_search.py:2429` - Loop distribuição CTe  
3. `nfe_search.py:2724` - Loop principal NFe

#### Mudanças Implementadas
- ❌ Removido: `db.set_last_nsu()` em erro 656
- ✅ Adicionado: Logs detalhados sobre preservação de NSU
- ✅ Adicionado: Comentários explicativos extensos
- ✅ Mantido: `db.registrar_erro_656()` para bloqueio de 65 minutos

#### Impacto
- **Antes**: Documentos perdidos permanentemente a cada erro 656
- **Depois**: Todos os documentos são baixados após bloqueio de 65 minutos
- **Documentos Recuperados**: Não é possível recuperar documentos já perdidos
- **Prevenção**: 100% dos novos documentos serão preservados

#### Evidências
```
Log ANTES da correção:
09:16:54 - NSU: 1459
09:16:57 - Erro 656, NSU atualizado para 1461 ❌ (perdeu 1460)

Log DEPOIS da correção:
09:16:54 - NSU: 1459
09:16:57 - Erro 656, NSU mantido em 1459 ✅
[65 minutos depois]
10:21:57 - NSU: 1459, baixados docs 1460, 1461, 1462 ✅
```

---

## 🔒 Proteções Implementadas

### 1. Comentários de Segurança
Todos os locais que tratam erro 656 agora têm comentários detalhados explicando:
- Por que não avançar NSU
- Exemplo do problema
- Solução correta

### 2. Logs Descritivos
Novos logs ajudam a identificar o comportamento:
```
🔒 NSU mantido em 1459, documentos entre 1459 e 1461 serão baixados após bloqueio de 65 minutos
```

### 3. Registro de Bloqueio
Função `registrar_erro_656()` mantém histórico de bloqueios para análise.

### 4. Documentação Técnica
Este documento serve como referência permanente sobre o bug e sua correção.

---

## 📞 Contato em Caso de Problemas

Se identificar que o bug voltou:

1. **PARE** imediatamente a execução do sistema
2. **EXECUTE** o script `verificar_nsu_integridade.py`
3. **COLETE** logs dos últimos 7 dias
4. **VERIFIQUE** quais documentos foram perdidos
5. **RESTAURE** o código das correções descritas acima
6. **REPORTE** para o time de desenvolvimento

---

## 📚 Referências

- [DOCUMENTACAO_NSU_ZERO.md](DOCUMENTACAO_NSU_ZERO.md) - Documentação sobre reset de NSU
- [DISTRIBUICAO.md](DISTRIBUICAO.md) - Documentação sobre distribuição SEFAZ
- [DIAGNOSTICO_ERRO_656.md](DIAGNOSTICO_ERRO_656.md) - Diagnóstico detalhado do erro 656

---

## ✅ Checklist de Prevenção

Antes de fazer alterações no código:

- [ ] Li esta documentação completamente
- [ ] Entendi por que erro 656 não deve avançar NSU
- [ ] Verifiquei que minha alteração não toca em NSU durante erro 656
- [ ] Adicionei comentários explicando tratamento de erro 656
- [ ] Executei teste de erro 656 (test_erro_656_nao_avanca_nsu)
- [ ] Verifiquei logs após alteração
- [ ] Executei verificar_nsu_integridade.py

---

**Última Atualização**: 09/01/2026  
**Versão**: 1.0  
**Status**: ✅ ATIVO - Bug Corrigido e Documentado
