# ✨ Nova Funcionalidade: Download em Lote de XMLs

## Visão Geral

O botão **"✅ Baixar XML Completo"** agora suporta **processamento em lote** de múltiplas notas fiscais simultaneamente!

## 🎯 O Que Foi Implementado

### Antes (v1.0.94)
- ❌ Download apenas de **1 nota por vez**
- ❌ Usuário precisava clicar repetidamente
- ❌ Processo manual e demorado

### Agora (v1.0.95)
- ✅ Download de **múltiplas notas** de uma vez
- ✅ Seleção com **Ctrl+Clique** ou **Shift+Clique**
- ✅ Barra de progresso em tempo real
- ✅ Resumo detalhado ao final
- ✅ Possibilidade de cancelar durante o processo

## 📝 Como Usar

### Passo 1: Selecionar Múltiplas Notas

Na tabela de notas, selecione múltiplas linhas:

- **Ctrl + Clique**: Seleciona notas individuais
- **Shift + Clique**: Seleciona intervalo de notas
- **Ctrl + A**: Seleciona todas as notas

### Passo 2: Menu de Contexto

Clique com o **botão direito** em qualquer nota selecionada.

O menu mostrará:
- **1 nota selecionada**: `✅ Baixar XML Completo`
- **2+ notas selecionadas**: `✅ Baixar XML Completo (X notas)`

### Passo 3: Confirmação

Um diálogo de confirmação mostrará:

```
Deseja baixar XML completo de X nota(s) selecionada(s)?

• Manifestação automática (se NF-e)
• Download do XML da SEFAZ
• Geração de PDF
• Atualização da interface

⏱️ Isso pode levar alguns minutos.
```

### Passo 4: Processamento

Uma barra de progresso aparecerá mostrando:

```
Processando nota 3/10
Número: 12345
Chave: 35240512...
✅ Sucesso: 2 | ❌ Erros: 0
```

**Informações exibidas:**
- Número da nota atual
- Chave de acesso (10 primeiros dígitos)
- Contador de sucessos
- Contador de erros
- Progresso visual (barra)

### Passo 5: Resumo Final

Ao finalizar, um diálogo mostrará:

```
✅ Download em lote concluído!

📊 Resumo:
   • Total processado: 10
   • Sucesso: 8
   • Erros: 2

❌ Detalhes dos erros:
   • Nota 12345: XML não disponível no SEFAZ
   • Nota 67890: Chave de acesso inválida
```

## 🔧 Detalhes Técnicos

### Arquivos Modificados

**Busca NF-e.py:**

1. **Linhas 4170-4200** - Menu de contexto:
   - Detecta múltiplas seleções
   - Conta notas RESUMO selecionadas
   - Ajusta texto do botão dinamicamente

2. **Linhas 4582-4730** - Nova função `_baixar_xml_e_pdf_lote()`:
   - Coleta todas as notas RESUMO selecionadas
   - Exibe diálogo de confirmação
   - Cria barra de progresso
   - Processa cada nota sequencialmente
   - Exibe resumo final

3. **Linhas 4731-4890** - Nova função `_baixar_xml_e_pdf_silencioso()`:
   - Versão silenciosa do download individual
   - Sem mensagens de sucesso (usado no lote)
   - Lança exceções para tratamento no lote

### Fluxo de Processamento

```
[Usuário seleciona múltiplas notas]
           ↓
[Clique direito → Menu de contexto]
           ↓
[Detecta múltiplas seleções (>1 RESUMO)]
           ↓
[Exibe "Baixar XML Completo (X notas)"]
           ↓
[Usuário confirma operação]
           ↓
┌─────────────────────────────────┐
│  Para cada nota selecionada:    │
│                                 │
│  1. Manifesta (se NF-e)        │
│  2. Busca XML na SEFAZ          │
│  3. Salva XML no disco          │
│  4. Atualiza banco de dados     │
│  5. Gera PDF automaticamente    │
│  6. Delay de 1 segundo          │
│                                 │
│  [Atualiza barra de progresso]  │
└─────────────────────────────────┘
           ↓
[Atualiza interface (cinza → verde)]
           ↓
[Exibe resumo: sucessos/erros]
```

### Proteções Implementadas

1. **Validação de Seleção**
   - Ignora notas já completas (xml_status != 'RESUMO')
   - Valida chaves de acesso (44 dígitos)
   - Ignora linhas sem dados válidos

2. **Controle de Requisições**
   - Delay de 1 segundo entre notas
   - Evita sobrecarga na SEFAZ
   - Respeita limites de requisição

3. **Tratamento de Erros**
   - Captura exceções individuais
   - Não interrompe o lote por 1 erro
   - Registra detalhes dos erros
   - Continua processando as próximas

4. **Cancelamento**
   - Botão "Cancelar" na barra de progresso
   - Interrompe processamento imediatamente
   - Mantém notas já processadas

## 🎯 Casos de Uso

### Caso 1: Baixar Todas as Notas do Dia
```
1. Filtrar por data (ex: 01/02/2026)
2. Ctrl+A (seleciona todas)
3. Botão direito → "Baixar XML Completo (50 notas)"
4. Confirmar
5. Aguardar processamento (~ 50 segundos)
```

### Caso 2: Baixar Apenas Notas de Um Fornecedor
```
1. Filtrar por emitente (ex: "ALFA LTDA")
2. Ctrl+A (seleciona todas)
3. Botão direito → "Baixar XML Completo (15 notas)"
4. Confirmar
5. Aguardar processamento (~ 15 segundos)
```

### Caso 3: Seleção Manual
```
1. Ctrl+Clique em nota 1
2. Ctrl+Clique em nota 5
3. Ctrl+Clique em nota 8
4. Botão direito → "Baixar XML Completo (3 notas)"
5. Confirmar
6. Aguardar processamento (~ 3 segundos)
```

## ⚡ Performance

| Quantidade | Tempo Estimado | Observação |
|------------|----------------|------------|
| 1 nota | ~3-5s | Manifestação + Download + PDF |
| 10 notas | ~30-50s | 1s delay entre cada |
| 50 notas | ~2-4min | Processamento sequencial |
| 100 notas | ~5-8min | Pode ser cancelado |

**Nota:** Tempos variam conforme velocidade da internet e disponibilidade da SEFAZ.

## 🐛 Limitações Conhecidas

1. **Processamento Sequencial**
   - Notas são processadas uma por vez
   - Não há paralelização (evita sobrecarga SEFAZ)

2. **Sem Retentativa Automática**
   - Erros não são retentados automaticamente
   - Usuário deve reprocessar notas com erro manualmente

3. **Delay Fixo**
   - Delay de 1 segundo não é configurável
   - Recomendado para evitar bloqueio SEFAZ

## 📊 Estatísticas

### Antes (Download Individual)
- **50 notas**: 50 cliques + ~2.5min (sem contar tempo de clique)
- **100 notas**: 100 cliques + ~5min

### Agora (Download em Lote)
- **50 notas**: 1 clique + ~2.5min
- **100 notas**: 1 clique + ~5min

**Economia de tempo:** ~50% (eliminando cliques repetitivos)

## 🔄 Compatibilidade

- ✅ **NF-e**: Manifesta automaticamente antes de baixar
- ✅ **CT-e**: Baixa diretamente (sem manifestação)
- ✅ **NFS-e**: Funciona normalmente
- ✅ **NFCe**: Baixa normalmente

## 📝 Changelog v1.0.95

### Adicionado
- ✅ Processamento em lote de múltiplas notas
- ✅ Detecção automática de seleções múltiplas
- ✅ Barra de progresso em tempo real
- ✅ Resumo detalhado ao final do processamento
- ✅ Possibilidade de cancelar durante execução

### Modificado
- 🔧 Menu de contexto agora mostra contador de notas
- 🔧 Função `_baixar_xml_e_pdf()` mantida para compatibilidade
- 🔧 Nova função `_baixar_xml_e_pdf_silencioso()` para lote

### Corrigido
- 🐛 Encoding UTF-8 para suportar emojis (bug anterior)
- 🐛 Diretórios XML criados automaticamente (bug anterior)

## 🚀 Próximas Melhorias

- [ ] Paralelização (download simultâneo de 5 notas)
- [ ] Configuração de delay personalizável
- [ ] Retentativa automática em caso de erro
- [ ] Exportação do resumo para CSV
- [ ] Filtro por tipo de documento (NF-e, CT-e, etc.)
- [ ] Agendamento de downloads em segundo plano

---

**Desenvolvido por:** DWM System Developer  
**GitHub:** https://github.com/W4lterBr/NF-e  
**Versão:** 1.0.95  
**Data:** 2026-02-02
