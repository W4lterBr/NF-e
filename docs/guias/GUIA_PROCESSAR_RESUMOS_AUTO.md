# 📋 GUIA: Processar Resumos Automaticamente

## 🎯 Problema:
Você tem **781 CT-e com status RESUMO** que precisam ser convertidos para COMPLETO baixando o XML completo de cada um pela chave.

## ✅ Solução: Use o Agendador de Tarefas! (v1.1.27)

### 🆕 Nova Tarefa Adicionada:
**"Processar Resumos (RESUMO → COMPLETO)"** - Tarefa #8

Esta tarefa:
- 🔍 Busca TODAS as notas com `xml_status = 'RESUMO'` no banco
- 📞 Consulta cada chave individualmente na SEFAZ
- 📥 Baixa o XML completo
- ✅ Atualiza status de RESUMO para COMPLETO
- 💾 Salva XML em `xmls/[TIPO]/[CNPJ]/[DATA]/`

---

## 📖 Como Usar:

### ⚡ NOVO! Opção Express: Executar Agora (v1.1.27)

**Quer processar os 781 resumos AGORA?**

1. **Abra o sistema** Busca NF-e

2. **Menu → Ferramentas → Agendador de Tarefas**
   - Ou pressione `Ctrl+Shift+T`

3. **Selecione a tarefa:**
   - Na lista, escolha: `"Processar Resumos (RESUMO → COMPLETO)"`

4. **Clique no botão AZUL:**
   - ▶️ **"Executar Agora"** (novo botão à esquerda!)
   
5. **Confirme e aguarde:**
   - Clique "Sim" no diálogo de confirmação
   - Tempo: ~15-20 minutos
   - Acompanhe o progresso na barra de status

**✨ Vantagem:** NÃO precisa configurar horários/intervalos! Executa imediatamente!

---

### Opção 1: Executar Manualmente (Tradicional)

1. **Abra o sistema** Busca NF-e

2. **Menu → Ferramentas → Agendador de Tarefas**
   - Ou pressione `Ctrl+Shift+T`

3. **Configure:**
   - **O que executar?** → Selecione `"Processar Resumos (RESUMO → COMPLETO)"`
   - **Quando executar?** → Deixe tudo desmarcado
   - Clique em **"Salvar"**

4. **Execute Agora:**
   - Menu → Ferramentas → **Executar Tarefa Agendada Agora**
   
5. **Acompanhe:**
   - Interface mostrará progresso: "Processando 1/781..."
   - Pode demorar algumas horas (taxa de ~50 consultas/minuto)

---

### Opção 2: Agendar para Horário Específico

**Exemplo: Executar todo dia às 03:00 da madrugada**

1. **Menu → Ferramentas → Agendador de Tarefas**

2. **Configure:**
   - **O que?** → `"Processar Resumos (RESUMO → COMPLETO)"`
   - **Quando?**
     - ☑️ Ativar **"Por horário específico"**
     - Horário: `03:00`
   - Clique em **"Salvar"**

3. **Pronto!** 
   - Sistema executará automaticamente todo dia às 03h
   - Processará novos resumos que aparecerem

---

### Opção 3: Agendar por Intervalo

**Exemplo: Executar a cada 6 horas**

1. **Menu → Ferramentas → Agendador de Tarefas**

2. **Configure:**
   - **O que?** → `"Processar Resumos (RESUMO → COMPLETO)"`
   - **Quando?**
     - ☑️ Ativar **"Por intervalo"**
     - Intervalo: `6` horas
   - Clique em **"Salvar"**

3. **Pronto!** 
   - Sistema executará a cada 6 horas
   - Primeira execução: imediatamente
   - Próximas: a cada 6h após a anterior

---

### Opção 4: Após Busca na SEFAZ (Encadeamento)

**Exemplo: Buscar novas → Processar resumos automaticamente**

1. **Menu → Ferramentas → Agendador de Tarefas**

2. **Configure:**
   - **O que?** → `"Buscar Notas na SEFAZ"`
   - **Quando?** → Configure como preferir (horário, intervalo, ao iniciar)
   - **E depois?**
     - ☑️ Ativar **"Executar outra tarefa após esta"**
     - Selecione: `"Processar Resumos (RESUMO → COMPLETO)"`
   - Clique em **"Salvar"**

3. **Fluxo automático:**
   ```
   1. Busca novas notas na SEFAZ
      ↓
   2. Novas notas entram como RESUMO
      ↓
   3. Automaticamente processa RESUMOS → COMPLETO
      ↓
   4. Sistema 100% atualizado!
   ```

---

## 📊 Estatísticas Atuais:

```
📦 Total de CT-e: 854
   ├─ ✅ COMPLETOS: 73 (8.5%)
   └─ 📋 RESUMOS: 781 (91.5%)
```

**Por empresa:**
```
📌 47539664000197: 12 completos + 472 resumos = 484 CT-e
📌 33251845000109: 25 completos + 117 resumos = 142 CT-e
📌 01773924000193: 15 completos + 114 resumos = 129 CT-e
📌 48160135000140: 21 completos + 26 resumos = 47 CT-e
📌 Outros: 52 resumos
```

---

## ⏱️ Tempo Estimado:

**Para processar 781 resumos:**
- Taxa: ~50 consultas/minuto (limite SEFAZ)
- Tempo: **~15-20 minutos**
- Sucesso esperado: ~95% (alguns podem estar indisponíveis)

---

## 🔍 Como Verificar Progresso:

### Durante Execução:
```
Interface principal → Barra de status:
"⚙️ Processando resumos: 145/781..."
```

### Após Execução:
```bash
py analisar_cte_completos.py
```

Mostrará quantos foram convertidos de RESUMO → COMPLETO

---

## 🎯 Resultado Esperado:

**ANTES:**
```
✅ COMPLETOS: 73 (8.5%)
📋 RESUMOS: 781 (91.5%)
```

**DEPOIS (se 100% sucesso):**
```
✅ COMPLETOS: 854 (100%)
📋 RESUMOS: 0 (0%)
```

---

## 🆚 Diferença entre Tarefas:

### Tarefa 4: "Baixar XMLs Faltantes"
- Busca em `xmls_baixados` onde `caminho_arquivo IS NULL`
- Boa para XMLs específicos que faltam
- **NÃO processa a tabela `notas_detalhadas`**

### Tarefa 8: "Processar Resumos" 🆕
- Busca em `notas_detalhadas` onde `xml_status = 'RESUMO'`
- Processa NFe, CTe, NFS-e
- **Solução completa para os 781 resumos!**

---

## 💡 Dicas:

1. **Primeira vez?** Execute manualmente (Opção 1) para testar

2. **Muitos resumos?** Agende para madrugada (Opção 2) para não interferir no trabalho

3. **Manutenção contínua?** Use encadeamento (Opção 4) - 100% automático!

4. **Não quer processar TODOS?** 
   - Use duplo-clique em uma nota RESUMO específica
   - Menu de contexto → "Baixar XML Completo"

---

## 🚨 Importante:

- ✅ Pode executar **a qualquer momento** (não gera erro 656)
- ✅ Respeita **rate limit** da SEFAZ (50/min)
- ✅ Pode **cancelar** durante execução
- ✅ Já processados **não são reprocessados**
- ✅ Atualiza interface **automaticamente**

---

## 📞 Testando Agora:

### Método Express (Novo! ⚡):
```bash
# 1. Veja quantos resumos tem
py analisar_cte_completos.py

# 2. Abra o sistema e pressione Ctrl+Shift+T
# 3. Selecione "Processar Resumos (RESUMO → COMPLETO)"
# 4. Clique no botão AZUL "▶️ Executar Agora"
# 5. Confirme: "Sim"
# 6. Aguarde 15-20 minutos
# 7. Execute novamente:
py analisar_cte_completos.py

# Resultado: 781 → 0 resumos! 🎉
```

### Método Tradicional:
```bash
# 1. Veja quantos resumos tem
py analisar_cte_completos.py

# 2. Abra o sistema
# 3. Menu → Ferramentas → Agendador → Configure tarefa 8
# 4. Marque opção "Ao iniciar" ou "Horário específico"
# 5. Clique "Salvar"
# 6. Execute: Menu → Ferramentas → Executar Tarefa Agendada Agora
# 7. Aguarde 15-20 minutos
# 8. Execute novamente:
py analisar_cte_completos.py

# Resultado: 781 → 0 resumos! 🎉
```

---

## 🎉 Conclusão:

**SIM!** O agendador já tinha a estrutura, só faltava adicionar a tarefa específica para processar resumos. Agora está **100% funcional**! 

```
v1.1.27: ✅ Tarefa "Processar Resumos" adicionada ao agendador
```
