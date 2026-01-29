# DIAGNÓSTICO: Problema com Busca de NFe

## 🔴 PROBLEMA IDENTIFICADO

**Status**: Erro 656 (Consumo Indevido) bloqueando consultas de NFe

### Evidências dos Logs (30/12/2025 às 11:38):

#### Certificado 33251845000109:
```xml
<cStat>656</cStat>
<xMotivo>Rejeicao: Consumo Indevido (Deve ser utilizado o ultNSU nas solicitacoes subsequentes. Tente apos 1 hora)</xMotivo>
<ultNSU>000000000061595</ultNSU>
```

#### Certificado 47539664000197:
```xml
<cStat>656</cStat>
<xMotivo>Rejeicao: Consumo Indevido (Deve ser utilizado o ultNSU nas solicitacoes subsequentes. Tente apos 1 hora)</xMotivo>
<ultNSU>000000000026923</ultNSU>
```

#### Certificado 49068153000160:
```
📊 [49068153000160] NF-e: cStat=656
⏸️ [49068153000160] NF-e: Consumo indevido (656) - aguardar intervalo antes de nova consulta
🔒 [49068153000160] NF-e bloqueada por 65 minutos - próxima consulta possível às 10:38:02
```

### CTe Funcionando Normalmente:
```xml
<cStat>137</cStat>
<xMotivo>Nenhum documento localizado.</xMotivo>
```
✅ CTe usa endpoint diferente e NÃO foi bloqueado

---

## 🧪 CAUSA RAIZ

### Erro 656: O que significa?

A SEFAZ retorna erro 656 quando:
1. **Consultas muito frequentes**: Menos de ~1 hora entre consultas ao mesmo endpoint
2. **Proteção contra spam**: Limita requisições para evitar sobrecarga
3. **Bloqueio por CNPJ**: Cada certificado (CNPJ) tem seu próprio contador

### Por que CTe funciona e NFe não?

- **NFe**: Usa servidor `www.nfe.fazenda.gov.br` (bloqueado)
- **CTe**: Usa servidor `www.cte.fazenda.gov.br` (não bloqueado)
- **Servidores independentes**: Bloqueio não afeta um ao outro

---

## ✅ SOLUÇÃO IMPLEMENTADA NO SISTEMA

### 1. Bloqueio Local (65 minutos):
```python
# Tabela erro_656 no banco de dados
CREATE TABLE erro_656 (
    informante TEXT PRIMARY KEY,
    ultimo_erro TIMESTAMP,
    nsu_bloqueado TEXT
)
```

Quando recebe erro 656:
- ✅ Registra timestamp do erro
- ✅ Bloqueia novas consultas por 65 minutos
- ✅ Atualiza NSU para o ultNSU retornado
- ✅ Continua processando CTe

### 2. Verificação Antes de Consultar:
```python
def pode_consultar_certificado(informante, nsu_atual):
    # Verifica se passou 65 minutos desde último erro 656
    # Verifica se NSU mudou (indica documentos novos)
```

---

## ⚠️ PROBLEMA ATUAL

### Situação em 30/12/2025 11:38:

1. **SEFAZ bloqueou** os certificados às ~10:33 (quando receberAM erro 656)
2. **Bloqueio expira** às ~11:33 (1 hora depois)
3. **Sistema tentou** consultar às 11:38 → AINDA BLOQUEADO
4. **Resultado**: Nenhuma NFe baixada

### Timeline:
```
10:33 - Primeira consulta → Erro 656 (SEFAZ bloqueia)
        Sistema registra bloqueio local (65 min)
        
11:38 - Busca Completa iniciada
        Sistema limpa tabela erro_656 (remove bloqueio local)
        Tenta consultar SEFAZ → AINDA BLOQUEADA (faltam ~2 min)
        SEFAZ retorna erro 656 novamente
        Sistema registra bloqueio local novamente
        
12:38 - Próxima tentativa possível (1h após 11:38)
```

---

## 🛠️ AÇÃO NECESSÁRIA

### Opção 1: AGUARDAR (Recomendado)
⏰ **Aguardar até 12:40** (1 hora após último erro às 11:38)
- Sistema automaticamente tentará novamente
- Bloqueio local expira às 12:43 (65 min)
- SEFAZ permite consulta às 12:38 (60 min)

### Opção 2: Verificar Manualmente
```sql
-- Ver bloqueios atuais
SELECT 
    informante,
    ultimo_erro,
    nsu_bloqueado,
    CAST((julianday('now') - julianday(ultimo_erro)) * 1440 AS INT) as minutos_passados,
    65 - CAST((julianday('now') - julianday(ultimo_erro)) * 1440 AS INT) as minutos_restantes
FROM erro_656
ORDER BY ultimo_erro DESC;
```

### Opção 3: Limpar Bloqueios (USE COM CAUTELA!)
```sql
-- ATENÇÃO: Só use se tiver CERTEZA que passou 1 hora desde erro 656
DELETE FROM erro_656;
```

---

## 📊 ESTATÍSTICAS

### Certificados Bloqueados:
- ❌ 33251845000109 (NFe) - Bloqueado às 11:38
- ❌ 47539664000197 (NFe) - Bloqueado às 11:38  
- ❌ 49068153000160 (NFe) - Bloqueado às 10:33
- ❌ 48160135000140 (NFe) - cStat 137 (sem documentos, não bloqueado)

### Documentos Encontrados:
- ✅ CTe: Consultando normalmente
- ❌ NFe: Bloqueadas por erro 656

---

## 🔍 COMO EVITAR NO FUTURO

### 1. Respeitar Intervalo Mínimo:
✅ **Sistema já configurado**: Intervalo mínimo de 1 hora entre buscas
- Configuração: "Intervalo de busca: X horas"
- Mínimo: 1 hora
- Máximo: 23 horas

### 2. Não Usar "Busca Completa" Frequentemente:
⚠️ **"Busca Completa" reseta NSU para 0**
- Causa: Sistema baixa TODOS os documentos desde o início
- Problema: Muitas consultas em sequência → Erro 656
- Recomendação: Use apenas quando realmente necessário

### 3. Monitorar Logs:
```bash
# Ver últimos erros 656
tail -f "C:\Users\Nasci\AppData\Roaming\Busca XML\logs\busca_nfe_*.log" | grep "656"
```

---

## ✨ MELHORIAS FUTURAS

### 1. Dashboard de Bloqueios:
- Mostrar certificados bloqueados na interface
- Countdown até próxima consulta possível
- Status em tempo real

### 2. Alertas Inteligentes:
- Aviso antes de fazer "Busca Completa"
- Notificação quando bloqueio expirar
- Sugestão de intervalo ideal

### 3. Otimização de Consultas:
- Consultar apenas certificados desbloqueados
- Priorizar CTe quando NFe bloqueada
- Log consolidado de bloqueios

---

## 📞 CONTATO

Se o problema persistir após 12:40:
1. Verificar logs em: `C:\Users\Nasci\AppData\Roaming\Busca XML\logs\`
2. Verificar tabela erro_656 no banco
3. Verificar se intervalo está configurado >= 1 hora
