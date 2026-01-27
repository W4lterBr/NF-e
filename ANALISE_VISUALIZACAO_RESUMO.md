# 📊 ANÁLISE: Por que NF-e RESUMO não aparecem na interface?

**Data**: 12/01/2026

## 🔍 RESULTADO DO REPROCESSAMENTO

✅ **13 NF-e atualizadas com sucesso** (2.9%)  
⚠️ **439 NF-e não encontradas na SEFAZ** (97.1%)  

---

## ❓ POR QUE AS NF-e RESUMO NÃO APARECEM?

### Resposta Curta:
**SIM**, elas DEVEM aparecer na interface, mas provavelmente estão sendo **filtradas** por falta de dados.

### Explicação Detalhada:

#### 1. **O que acontece com xml_status='RESUMO'**

Quando uma NF-e é salva com `xml_status='RESUMO'`, os campos ficam vazios:
```
✅ Chave: 35260172381189... → PREENCHIDA
✅ NSU: 000000000034788 → PREENCHIDO
✅ Informante: 01773924000193 → PREENCHIDO
❌ Data emissão: NULL ou 'N/A' → VAZIO
❌ Nome emitente: NULL ou 'N/A' → VAZIO
❌ Número: NULL ou 'N/A' → VAZIO
❌ Valor: NULL ou 'N/A' → VAZIO
```

#### 2. **Como a interface busca as NF-e**

A interface provavelmente usa queries SQL como:

```sql
SELECT * FROM notas_detalhadas 
WHERE tipo = 'NFe' 
AND informante = '...'
AND data_emissao IS NOT NULL  -- ⚠️ FILTRO
AND data_emissao != ''  -- ⚠️ FILTRO
ORDER BY data_emissao DESC
```

**Resultado**: NF-e com status RESUMO são **excluídas** porque `data_emissao` está vazia!

#### 3. **Por que isso foi projetado assim**

É uma decisão de design **intencional**:

✅ **Vantagem**: 
- Evita mostrar NF-e "quebradas" ao usuário
- Interface fica limpa e profissional
- Usuário vê apenas documentos completos

❌ **Desvantagem**:
- NF-e não aparecem mesmo existindo no banco
- Usuário não sabe que há documentos pendentes
- Parece que o sistema "perdeu" as notas

---

## 🔧 POSSÍVEIS SOLUÇÕES

### Solução 1: **Mostrar na interface com indicador visual** (RECOMENDADO)

Modificar query da interface para incluir RESUMO com indicação clara:

```sql
SELECT *, 
    CASE 
        WHEN xml_status = 'RESUMO' THEN 'Aguardando download'
        ELSE 'Completo'
    END as status_visual
FROM notas_detalhadas 
WHERE tipo = 'NFe'
AND informante = '...'
ORDER BY data_emissao DESC NULLS LAST  -- Vazias aparecem no final
```

Na interface:
```
┌──────────────────────────────────────────────┐
│ 📄 Chave: 3526...                           │
│ ⏳ STATUS: Aguardando download               │
│ 📋 NSU: 34788                               │
│ ⚠️ Dados não disponíveis - clique para      │
│    tentar baixar novamente                  │
└──────────────────────────────────────────────┘
```

### Solução 2: **Não salvar RESUMO no banco** (ALTERNATIVA)

Modificar código para NÃO salvar resNFe até obter XML completo:

```python
if root_tag == 'resNFe':
    # Tenta buscar XML completo
    xml_completo = svc.fetch_by_chave_dist(chave_resumo)
    
    if xml_completo:
        # Salva XML completo
        nota = extrair_nota_detalhada(xml_completo, ...)
        db.salvar_nota_detalhada(nota)
    else:
        # NÃO SALVA NO BANCO!
        # Adiciona à fila de pendentes para retry
        db.add_to_retry_queue(chave_resumo, informante, nsu)
        logger.warning(f"⏳ resNFe {chave_resumo} adicionado à fila de retry")
```

**Vantagem**: Banco só tem NF-e completas  
**Desvantagem**: Precisa criar sistema de fila/retry

### Solução 3: **Filtro "Mostrar Pendentes"** (HÍBRIDO)

Adicionar checkbox na interface:

```
☐ Mostrar apenas completas
☑ Incluir pendentes (aguardando download)
☑ Incluir canceladas/denegadas
```

Query ajusta conforme seleção.

---

## 📊 SITUAÇÃO ATUAL DOS SEUS DADOS

### Antes do Reprocessamento:
- **452 NF-e com status RESUMO** (dados vazios)
- Todas invisíveis na interface

### Após o Reprocessamento:
- ✅ **13 NF-e convertidas para COMPLETO** (agora visíveis)
- ⚠️ **439 ainda com status RESUMO** (continuam invisíveis)

### Por que 439 não foram baixadas?

A SEFAZ retornou resposta de **437 bytes** (muito pequena), indicando:

```xml
<retDistDFeInt>
    <cStat>656</cStat> <!-- ou outro erro -->
    <xMotivo>Rejeição...</xMotivo>
</retDistDFeInt>
```

**Possíveis motivos**:
1. **Destinatário não autorizado** - Essas NF-e não são "suas"
2. **Chaves inválidas** - Dados corrompidos
3. **NF-e canceladas/denegadas** - Não mais disponíveis
4. **Erro 656 em massa** - Muitas consultas simultâneas
5. **Timeout/problema de rede**

---

## 🎯 RECOMENDAÇÃO FINAL

### Para resolver 100%:

1. **Imediato**: Execute novamente o reprocessamento **com intervalo** entre consultas:
   ```python
   # Adicionar sleep entre consultas
   import time
   time.sleep(2)  # 2 segundos entre cada busca
   ```

2. **Curto prazo**: Modificar interface para mostrar NF-e RESUMO com indicador visual

3. **Médio prazo**: Implementar sistema de retry automático em background

4. **Longo prazo**: Criar dashboard de "Documentos Pendentes"

---

## 📋 RESPOSTA À SUA PERGUNTA

> **"E não deveria mostrar na interface essas NF-e RESUMO?"**

**Resposta**: Depende do design da interface!

- **Se a query filtra por `data_emissao IS NOT NULL`** → ❌ Não aparecem
- **Se a query busca apenas por `tipo='NFe' AND informante='...'`** → ✅ Aparecem (mas com campos vazios)

**Para saber com certeza**, precisamos ver o código da interface onde as NF-e são listadas.

**Onde olhar**:
- `Busca NF-e.py` (arquivo principal)
- `interface_pyqt5.py` (se usar PyQt5)
- Procure por query SQL que busca `notas_detalhadas`

---

## ✅ PRÓXIMOS PASSOS SUGERIDOS

1. Verificar código da interface para confirmar filtros SQL
2. Decidir se quer mostrar RESUMO ou não
3. Se sim: Adicionar indicador visual e botão "Tentar download"
4. Se não: Implementar fila de retry automática
5. Reprocessar as 439 NF-e novamente (com intervalo maior)

---

**Conclusão**: As NF-e RESUMO **estão no banco**, mas provavelmente **não aparecem** por filtro SQL. Você pode escolher mostrá-las (com indicação) ou escondê-las até obter dados completos.
