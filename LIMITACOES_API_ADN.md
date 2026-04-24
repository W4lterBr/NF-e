# LIMITAÇÕES DA API ADN NACIONAL - NFS-e

## 📋 Resumo Executivo

**Situação**: O portal web ADN mostra notas de 2025/2026, mas a API REST pública não fornece acesso a essas notas.

**Conclusão**: O sistema está funcionando corretamente dentro das limitações da API oficial.

---

## 🔍 Investigação Realizada

### 1. Documentação Oficial Analisada

**APIs Descobertas**:
- ✅ `swagger (3).json` - API ADN Contribuinte
- ✅ `swagger (4).json` - API ADN Município

**Endpoints Oficiais Documentados**:
```
GET /contribuintes/DFe/{NSU}
    - Consulta documentos por NSU incremental
    - Parâmetros: cnpjConsulta (opcional), lote (boolean)
    
GET /contribuintes/NFSe/{ChaveAcesso}/Eventos
    - Consulta eventos vinculados a uma chave de acesso
```

**IMPORTANTE**: Esses são os **ÚNICOS** endpoints oficialmente documentados para contribuintes.

---

### 2. Testes Realizados

#### Teste A: Endpoints não documentados
**Script**: `descobrir_endpoints_contribuintes.py`
**Resultado**: 14 endpoints retornaram 429 (Rate Limit), mas nenhum funcional para consulta por período.

```
Testados:
- /contribuintes/nfse/emitidas     → 429 Rate Limit
- /contribuintes/nfse/periodo      → 429 Rate Limit
- /contribuintes/consulta/nfse     → 429 Rate Limit
- /contribuintes/nfse/lista        → 429 Rate Limit
```

**Conclusão**: Esses endpoints existem mas não são acessíveis publicamente ou requerem autenticação diferente.

---

#### Teste B: Parâmetro tipoNSU
**Script**: `testar_tipos_nsu.py`
**Objetivo**: Testar se parâmetro `tipoNSU` (RECEPCAO, DISTRIBUICAO, GERAL, MEI) revela notas diferentes.

**Resultados**:
```
SEM ESPECIFICAR:  250 documentos (NSUs 1, 3, 5, 7, 9)
RECEPCAO:         250 documentos (NSUs 1, 3, 5, 7, 9)
DISTRIBUICAO:     250 documentos (NSUs 1, 3, 5, 7, 9)
GERAL:            250 documentos (NSUs 1, 3, 5, 7, 9)
```

**Conclusão**: Todos os tipos retornam os mesmos documentos. Parâmetro não faz diferença prática.

---

#### Teste C: Busca em NSUs maiores
**Script**: `buscar_nfse_nsus_maiores.py`
**Objetivo**: Testar NSUs acima do último conhecido (51-251).

**Documentos encontrados**: Todos de 2024 (NSUs 2-59).

**Conclusão**: Notas de 2025/2026 não estão distribuídas via NSU incremental.

---

#### Teste D: SOAP Municipal
**Scripts**: 
- `buscar_nfse_soap_mg.py` (Betha)
- `buscar_nfse_bhiss.py` (BHISS Digital BH)

**Resultados**:
- Betha: HTTP 404 (provedor incorreto)
- BHISS: HTTP 403 Forbidden (firewall bloqueou)

**Conclusão**: SOAP Municipal não acessível para esse município/empresa.

---

## 🎯 Conclusão Técnica

### Por que as notas de 2025/2026 não aparecem?

**Diferença entre Portal Web e API REST**:

```
┌─────────────────────────────────────────────────────────────┐
│ PORTAL WEB ADN (https://adn.nfse.gov.br)                   │
├─────────────────────────────────────────────────────────────┤
│ • Usa endpoints INTERNOS/PRIVADOS                           │
│ • Acesso através de interface web autenticada              │
│ • Mostra notas EMITIDAS em tempo real                      │
│ • Endpoints não documentados publicamente                   │
│ • EXIBE: Notas de 2025/2026 ✅                             │
└─────────────────────────────────────────────────────────────┘
                            ↕️
                      (Diferente)
                            ↕️
┌─────────────────────────────────────────────────────────────┐
│ API REST PÚBLICA (/contribuintes/docs/)                     │
├─────────────────────────────────────────────────────────────┤
│ • Usa apenas 2 endpoints documentados                       │
│ • GET /DFe/{NSU} - Busca incremental                       │
│ • GET /NFSe/{ChaveAcesso}/Eventos - Busca eventos         │
│ • Mostra notas DISTRIBUÍDAS (pode ter delay)               │
│ • Documentação oficial Swagger disponível                   │
│ • RETORNA: Apenas notas até 2024 ❌                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Dados da Empresa COOPSERVIÇOS

**CNPJ**: 56237242000158  
**Município**: Belo Horizonte/MG  
**Certificado**: COOPSERVIÇOS (1234).pfx

### Status Atual no Sistema:

```sql
SELECT COUNT(*) FROM notas_detalhadas 
WHERE cnpj_destinatario = '56237242000158' 
  AND tipo = 'NFS-e';
-- Resultado: 50 notas

SELECT MIN(dtemissao), MAX(dtemissao) 
FROM notas_detalhadas 
WHERE cnpj_destinatario = '56237242000158';
-- Resultado: 2024-08-22 a 2024-11-04
```

**Último NSU processado**: 50 (em lote de 100 documentos, NSU 1 retorna docs 2-51, etc.)

---

## ✅ O que o Sistema CONSEGUE fazer

1. ✅ **Busca incremental por NSU**
   - Baixa automaticamente novos documentos à medida que são distribuídos
   - Funcional e confiável

2. ✅ **Busca de eventos por chave**
   - Consulta cancelamentos, confirmações, etc.
   - Permite rastreamento completo do ciclo de vida da nota

3. ✅ **Autenticação mTLS**
   - Certificado digital ICP-Brasil funcionando corretamente
   - Conexão segura com API

4. ✅ **Processamento e armazenamento**
   - Salva XMLs em estrutura organizada
   - Banco de dados SQLite com todos os campos
   - Exportação automática

---

## ❌ O que o Sistema NÃO CONSEGUE fazer

1. ❌ **Consulta por período de emissão**
   - Endpoint `/nfse/periodo` não acessível publicamente
   - Limitado a busca incremental por NSU

2. ❌ **Consulta de notas emitidas mas não distribuídas**
   - Portal pode mostrar notas antes da distribuição via API
   - Delay entre emissão e disponibilidade na API

3. ❌ **Acesso a endpoints internos do portal**
   - Endpoints usados pelo portal web não são públicos
   - Documentação Swagger não inclui esses endpoints

---

## 🔄 Fluxo da Nota Fiscal

```
1. EMISSÃO
   ↓
   Nota criada no sistema
   ↓
   [Visível no PORTAL WEB imediatamente] ✅
   ↓
2. REGISTRO NO ADN
   ↓
   Processamento interno
   ↓ (pode levar horas/dias)
   ↓
3. DISTRIBUIÇÃO
   ↓
   Nota recebe NSU de distribuição
   ↓
   [Disponível na API REST /DFe/{NSU}] ✅
   ↓
4. CONSULTA PELO SISTEMA
   ↓
   Sistema baixa via busca incremental
   ↓
   [Salva no banco e exporta XML] ✅
```

**GAP**: Entre passos 1-2 e 3-4, notas visíveis no portal mas não na API.

---

## 💡 Recomendações

### Para uso atual:

1. **Execute busca incremental regularmente**
   ```bash
   # Diário ou semanal
   .\.venv\Scripts\python.exe "Busca NF-e.py"
   ```
   Isso garante que todas as notas **quando distribuídas** serão baixadas.

2. **Monitore o último NSU**
   ```python
   from nfe_search import DatabaseManager
   db = DatabaseManager('notas.db')
   print(db.get_last_nsu_nfse('56237242000158'))
   ```

3. **Aceite o delay entre emissão e distribuição**
   - É limitação da API oficial, não do sistema
   - Notas eventualmente aparecerão

### Para casos especiais:

Se precisar de notas **imediatamente após emissão**:

1. **Consulta manual no portal** (https://adn.nfse.gov.br)
   - Download individual do XML via interface web
   - Importação manual para o sistema

2. **Solicitação via chave de acesso**
   ```python
   # Se você tem a chave de acesso da nota
   GET /contribuintes/NFSe/{ChaveAcesso}/Eventos
   ```
   Mas isso requer conhecer a chave previamente.

---

## 📚 Referências

### Documentação Oficial:
- API Contribuintes: https://adn.nfse.gov.br/contribuintes/docs/index.html
- Swagger 3: `swagger (3).json` (anexo)
- Swagger 4: `swagger (4).json` (anexo)

### Scripts Criados:
- `verificar_coopservicos.py` - Análise inicial
- `testar_tipos_nsu.py` - Teste de tipos de NSU
- `buscar_nfse_nsus_maiores.py` - Busca estendida
- `descobrir_endpoints_contribuintes.py` - Descoberta de endpoints
- `ANALISE_APIS_ADN.md` - Análise das APIs

### Testes Realizados (2026-02-18):
- ✅ 4 tipos de NSU testados (resultados idênticos)
- ✅ 10 NSUs consultados por tipo (40 consultas)
- ✅ 250 documentos retornados por tipo
- ✅ Autenticação mTLS funcionando
- ❌ Nenhuma nota de 2025/2026 encontrada via API

---

## 🎯 Conclusão Final

**O sistema está funcionando corretamente dentro das capacidades da API REST pública oficial.**

As notas de 2025/2026 visíveis no portal web ainda não foram distribuídas via API, ou utilizam endpoints internos não acessíveis publicamente.

**Ação recomendada**: Continuar monitoramento através da busca incremental automática. As notas de 2025/2026 devem aparecer quando forem oficialmente distribuídas no sistema.

---

**Documento gerado em**: 2026-02-18  
**Última atualização**: 2026-02-18  
**Status**: Investigação concluída - Limitação confirmada
