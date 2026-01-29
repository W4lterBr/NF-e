# 🔍 Análise Técnica: Busca Completa vs Busca na SEFAZ

## 📊 Resumo Executivo

Ao cadastrar um **certificado novo**, você deve:
1. **Primeiro**: Executar **"Busca Completa"** (uma única vez)
2. **Depois**: Usar **"Busca na SEFAZ"** (para atualizações periódicas)

---

## 🔄 Diferenças Técnicas

### 1️⃣ **Busca Completa** (`do_busca_completa()`)

**Localização:** `Busca NF-e.py` linha 7643  
**Menu:** Configurações → Busca Completa  
**Ícone:** Não tem (só no menu)

#### O que faz:

```python
def do_busca_completa(self):
    # 1. Confirma com o usuário
    QMessageBox.question(
        "Esta operação irá:\n"
        "• Resetar o NSU para 0 (zero) - NFe e CTe\n"
        "• Limpar todos os bloqueios de erro 656\n"
        "• Buscar TODOS os XMLs desde o início\n"
    )
    
    # 2. RESETA NSU PARA ZERO
    for informante in certificados:
        conn.execute(
            "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, ?)",
            (informante, '000000000000000')  # ← NSU = 0
        )
        conn.execute(
            "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, ?)",
            (informante, '000000000000000')  # ← NSU = 0
        )
    
    # 3. LIMPA BLOQUEIOS DE ERRO 656
    conn.execute("DELETE FROM erro_656")
    
    # 4. EXECUTA A BUSCA
    run_search()  # ← Chama a mesma função que "Busca na SEFAZ"
```

#### Características:

| Item | Valor |
|------|-------|
| **NSU inicial** | `000000000000000` (ZERO) |
| **Limpa bloqueios** | ✅ SIM (erro 656, sem documentos) |
| **Documentos buscados** | TODOS desde o início da SEFAZ |
| **Tempo de execução** | ⚠️ MUITO LONGO (horas/dias dependendo do volume) |
| **Uso recomendado** | **UMA VEZ** ao cadastrar certificado novo |

---

### 2️⃣ **Busca na SEFAZ** (`do_search()`)

**Localização:** `Busca NF-e.py` linha 5301  
**Botão:** Barra de ferramentas - "Buscar na SEFAZ"  
**Ícone:** 🔍 (lupa)

#### O que faz:

```python
def do_search(self):
    # 1. Marca busca em andamento
    self._search_in_progress = True
    
    # 2. NÃO RESETA NSU - Usa NSU atual do banco
    # (Continua de onde parou)
    
    # 3. NÃO LIMPA BLOQUEIOS
    # (Respeita bloqueios de erro 656 e intervalos de 1h)
    
    # 4. EXECUTA A BUSCA
    run_search()  # ← Chama a mesma função que "Busca Completa"
    
    # 5. AGENDA PRÓXIMA BUSCA AUTOMÁTICA
    intervalo_horas = self.spin_intervalo.value()  # Ex: 3 horas
    self._next_search_time = datetime.now() + timedelta(hours=intervalo_horas)
    QTimer.singleShot(intervalo_horas * 3600 * 1000, self._executar_busca_agendada)
```

#### Características:

| Item | Valor |
|------|-------|
| **NSU inicial** | NSU atual salvo no banco (continua de onde parou) |
| **Limpa bloqueios** | ❌ NÃO (respeita regras da SEFAZ) |
| **Documentos buscados** | Apenas **NOVOS** desde último NSU |
| **Tempo de execução** | ⚡ RÁPIDO (minutos) |
| **Uso recomendado** | **SEMPRE** após a primeira "Busca Completa" |
| **Agendamento** | ✅ Automático (configurável: 1-24 horas) |

---

## 🎯 Função Comum: `run_search()`

**Localização:** `Busca NF-e.py` linha 119

Ambos os botões chamam a **mesma função** `run_search()`, que por sua vez chama `run_single_cycle()` do módulo `nfe_search.py`.

```python
def run_search(progress_cb):
    # Importa módulo nfe_search.py
    import nfe_search
    
    # Captura progresso em tempo real
    sys.stdout = ProgressCapture()
    
    # EXECUTA BUSCA
    nfe_search.run_single_cycle()  # ← Busca NFe e CTe
    
    return {"ok": True}
```

### `run_single_cycle()` - Lógica Principal

**Localização:** `nfe_search.py` linha 2429

```python
def run_single_cycle():
    # 1. Carrega certificados do banco
    certificados = db.load_certificates()
    
    # 2. Para cada certificado:
    for cert in certificados:
        informante = cert['informante']
        
        # 3. BUSCA NFe
        last_nsu = db.get_last_nsu(informante)  # ← Usa NSU salvo (0 ou atual)
        
        # Verifica bloqueios (erro 656, sem documentos)
        if db.tem_bloqueio(informante):
            logger.info(f"Certificado {informante} bloqueado, aguardando...")
            continue
        
        # Loop de busca NFe
        while True:
            resp = svc.fetch_by_cnpj("CNPJ", last_nsu)
            cStat = parser.extract_cStat(resp)
            
            if cStat == '656':  # Consumo Indevido
                db.registrar_erro_656(informante, last_nsu)
                break
            
            if cStat == '137':  # Sem documentos
                db.registrar_sem_documentos(informante)
                break
            
            if cStat == '138':  # Documentos encontrados
                docs = parser.extract_docs(resp)
                for nsu, xml in docs:
                    # Processa e salva documento
                    db.registrar_xml(xml)
                
                # Atualiza NSU
                last_nsu = parser.extract_last_nsu(resp)
                db.set_last_nsu(informante, last_nsu)  # ← SALVA PROGRESSO
                
                # Se ultNSU == maxNSU → Sincronizado
                if last_nsu == parser.extract_max_nsu(resp):
                    db.registrar_sem_documentos(informante)
                    break
        
        # 4. BUSCA CTe (mesmo processo)
        last_nsu_cte = db.get_last_nsu_cte(informante)
        # ... (lógica similar)
```

---

## 📋 Fluxo de Uso Recomendado

### **Cenário 1: Certificado NOVO** (Primeira vez)

```
┌────────────────────────────────┐
│ 1. Cadastrar Certificado       │
│    - CNPJ: 12345678000199      │
│    - NSU no banco: NULL        │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 2. Executar "BUSCA COMPLETA"   │
│    • Reseta NSU → 0            │
│    • Busca TODOS os docs       │
│    • Pode demorar horas        │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 3. Sistema baixa documentos    │
│    NSU: 0 → 1 → 2 → ... → 5000│
│    (exemplo: 5000 documentos)  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 4. Busca finalizada            │
│    • NSU salvo: 5000           │
│    • 5000 XMLs no banco        │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 5. Usar "BUSCA NA SEFAZ" após  │
│    • Busca apenas novos docs   │
│    • NSU: 5000 → 5001 → ...    │
│    • Agendamento automático    │
└────────────────────────────────┘
```

### **Cenário 2: Certificado EXISTENTE** (Uso diário)

```
┌────────────────────────────────┐
│ 1. Sistema inicializado        │
│    - NSU atual: 5000           │
│    - Última busca: hoje 08:00  │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 2. Clicar "BUSCA NA SEFAZ"     │
│    ou aguardar busca automática│
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 3. Sistema consulta SEFAZ      │
│    • NSU inicial: 5000         │
│    • Busca novos: 5001-5010    │
│    • 10 documentos novos       │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ 4. NSU atualizado: 5010        │
│    • 10 XMLs novos no banco    │
│    • Próxima busca: +3h        │
└────────────────────────────────┘
```

---

## ⚠️ Situações Especiais

### **Erro 656 (Consumo Indevido)**

#### Busca Completa:
- **LIMPA o bloqueio** antes de iniciar
- Permite buscar mesmo após erro 656 recente
- ⚠️ Pode gerar novo erro 656 se usado muito frequentemente

#### Busca na SEFAZ:
- **RESPEITA o bloqueio** de 65 minutos
- Pula certificado se tiver bloqueio ativo
- ✅ Segue regras da NT 2014.002

### **Sistema Sincronizado (ultNSU = maxNSU)**

#### Busca Completa:
- **LIMPA registro** de sincronização
- Força nova consulta desde NSU=0

#### Busca na SEFAZ:
- **RESPEITA intervalo** de 1 hora
- Não consulta se sincronizado há menos de 1h
- ✅ Evita erro 656

---

## 📊 Comparação Lado a Lado

| Característica | Busca Completa | Busca na SEFAZ |
|----------------|----------------|----------------|
| **NSU inicial** | 0 (zero) | NSU atual do banco |
| **Reseta NSU** | ✅ SIM | ❌ NÃO |
| **Limpa bloqueios** | ✅ SIM | ❌ NÃO |
| **Respeita erro 656** | ❌ NÃO (força busca) | ✅ SIM |
| **Respeita sincronização** | ❌ NÃO (ignora) | ✅ SIM (aguarda 1h) |
| **Documentos** | TODOS (histórico completo) | NOVOS (desde último NSU) |
| **Tempo execução** | ⚠️ Horas/Dias | ⚡ Minutos |
| **Agendamento automático** | ❌ NÃO | ✅ SIM |
| **Uso recomendado** | 1x ao cadastrar | Uso diário |
| **Função chamada** | `run_search()` | `run_search()` |
| **Diferença** | Preparação (reset) | Execução normal |

---

## 🎯 Resposta Direta à Pergunta

> **"Ao cadastrar um certificado, eu executo o Busca Completa para pegar o máximo de documentos possíveis, e o Busca na Sefaz, busca como depois de clicar no Busca Completa?"**

### **Resposta:**

**SIM, exatamente!** Aqui está a sequência correta:

1. **Cadastra certificado novo** → NSU ainda não existe no banco

2. **Executa "Busca Completa"**:
   - Sistema **RESETA NSU para 0**
   - Busca **TODOS** os documentos desde o início
   - NSU vai de 0 → 1 → 2 → ... → 5000 (exemplo)
   - **Pode demorar horas** dependendo do volume
   - Ao finalizar, NSU fica salvo (ex: 5000)

3. **Depois usa "Busca na SEFAZ"**:
   - Sistema **CONTINUA do NSU salvo** (5000)
   - Busca apenas **novos** documentos (5001, 5002, ...)
   - **Rápido** (minutos) pois só busca o que é novo
   - **Automático** (configura intervalo e esquece)

### **Analogia:**

- **Busca Completa** = Baixar **todo** o histórico de e-mails de uma conta nova
- **Busca na SEFAZ** = Verificar **novos** e-mails periodicamente

---

## 💡 Dicas Importantes

1. ✅ **Use "Busca Completa" apenas UMA VEZ** por certificado
2. ✅ **Use "Busca na SEFAZ" para rotina diária**
3. ⚠️ Não execute "Busca Completa" com frequência (gera erro 656)
4. ⚠️ Configure intervalo de 3-6 horas na "Busca na SEFAZ"
5. ✅ Deixe o sistema em "Busca Automática" para atualização contínua

---

## 🔧 Código-Fonte das Diferenças

### Busca Completa - Preparação:
```python
# Arquivo: Busca NF-e.py, linha 7666
def do_busca_completa(self):
    # PREPARAÇÃO ESPECIAL:
    conn.execute(
        "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, ?)",
        (informante, '000000000000000')  # ← RESET NSU
    )
    conn.execute("DELETE FROM erro_656")  # ← LIMPA BLOQUEIOS
    
    # Depois chama a mesma função:
    run_search()  # ← BUSCA (com NSU=0)
```

### Busca na SEFAZ - Execução Normal:
```python
# Arquivo: Busca NF-e.py, linha 5301
def do_search(self):
    # SEM PREPARAÇÃO ESPECIAL
    # NSU permanece como está no banco
    # Bloqueios são respeitados
    
    # Chama diretamente:
    run_search()  # ← BUSCA (com NSU atual)
```

### Função Comum:
```python
# Arquivo: nfe_search.py, linha 2500
def processar_nfe():
    # 1. Lê NSU do banco (pode ser 0 ou qualquer valor)
    last_nsu = db.get_last_nsu(informante)
    
    # 2. Consulta SEFAZ com esse NSU
    resp = svc.fetch_by_cnpj("CNPJ", last_nsu)
    
    # 3. Processa documentos e atualiza NSU
    # (Lógica é IDÊNTICA para ambos os botões)
```

---

## ✅ Conclusão

**Ambos os botões executam a MESMA lógica de busca**, mas:

- **Busca Completa**: **Prepara** o sistema (reset NSU → 0) antes de buscar
- **Busca na SEFAZ**: **Continua** de onde parou (usa NSU atual)

É como **rebobinar uma fita** (Busca Completa) vs **continuar assistindo** (Busca na SEFAZ).

**Use corretamente:**
- 1️⃣ Certificado novo → **Busca Completa** (uma vez)
- 2️⃣ Uso diário → **Busca na SEFAZ** (sempre)
