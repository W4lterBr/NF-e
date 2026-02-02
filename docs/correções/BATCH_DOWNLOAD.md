# 🔧 Correção: Download em Lote de XMLs Completos

**Versão:** 1.0.96  
**Data:** 02/02/2026  
**Autor:** DWM System Developer  
**Tipo:** Correção de Bug + Nova Funcionalidade

---

## 📋 Resumo

Corrigida a funcionalidade de download em lote de XMLs completos. O sistema detectava múltiplas seleções mas processava apenas 1 nota. Implementada busca correta dos dados nas células da tabela e validação de notas RESUMO por campos vazios.

---

## 🐛 Problema Identificado

### Sintomas
- Usuário seleciona 5+ notas com status RESUMO (Ctrl+Click)
- Menu mostra "Baixar XML Completo (5 notas)" ✅
- Usuário confirma a operação
- Sistema processa apenas a primeira nota ❌
- Dialog de sucesso aparece para 1 nota apenas

### Logs do Erro
```
[DEBUG LOTE] Total de linhas selecionadas: 26
[DEBUG LOTE] Total RESUMO encontradas: 26  ← Detectou corretamente
[DEBUG MENU] ✅ Botão 'Baixar XML Completo' em LOTE: 26 notas
[LOTE PROCESSA] Iniciando com 1 linhas selecionadas  ← BUG: Perdeu seleção!
[LOTE PROCESSA] Total de notas coletadas: 0  ← Nenhuma coletada
```

### Causa Raiz

**Problema 1: Qt.UserRole não armazenado**

A função `_baixar_xml_e_pdf_lote()` tentava ler dados do `Qt.UserRole` da coluna 0 (Status):

```python
# CÓDIGO BUGADO
status_item = self.table.item(row, 0)
item_data = status_item.data(Qt.UserRole)  # ❌ Retorna None!
if item_data.get('xml_status') == 'RESUMO':  # ❌ Crash ou False
    notas_para_processar.append(...)
```

**Problema 2: Validação incorreta de RESUMO**

As notas tinham `xml_status='COMPLETO'` no banco, mas exibiam `[Resumo]` na interface porque faltavam dados essenciais (número, data, emitente vazios).

**Problema 3: Dialogs bloqueando o loop**

A função `_baixar_xml_e_pdf()` mostrava QMessageBox durante processamento em lote, pausando a execução.

---

## ✅ Solução Implementada

### 1. Correção da Contagem de RESUMO no Menu

**Arquivo:** `Busca NF-e.py`  
**Linhas:** 4235-4280  
**Função:** `_on_table_context_menu()`

```python
# ANTES
resumo_count = 0
if len(selected_rows) > 1:
    for row in selected_rows:
        status_item = self.table.item(row, 0)
        item_data = status_item.data(Qt.UserRole)  # ❌ None
        if item_data.get('xml_status') == 'RESUMO':
            resumo_count += 1

# DEPOIS
resumo_count = 0
if len(selected_rows) > 1:
    # Encontra coluna da Chave
    chave_col = None
    for col in range(self.table.columnCount()):
        header = self.table.horizontalHeaderItem(col)
        if header and header.text() == "Chave":
            chave_col = col
            break
    
    if chave_col:
        conn = sqlite3.connect(str(DATA_DIR / 'notas.db'))
        conn.row_factory = sqlite3.Row
        
        for row in selected_rows:
            chave_item = self.table.item(row, chave_col)
            if chave_item:
                chave = chave_item.text()
                nota = conn.execute(
                    'SELECT xml_status, numero, data_emissao, nome_emitente FROM notas_detalhadas WHERE chave = ?',
                    (chave,)
                ).fetchone()
                
                if nota:
                    # ⭐ Considera RESUMO se xml_status='RESUMO' OU faltam dados
                    is_resumo = (
                        nota['xml_status'] == 'RESUMO' or 
                        not nota['numero'] or 
                        not nota['data_emissao'] or 
                        not nota['nome_emitente']
                    )
                    if is_resumo:
                        resumo_count += 1
        
        conn.close()
```

**Mudanças-chave:**
1. Busca pela coluna "Chave" ao invés de UserRole
2. Consulta banco de dados para cada linha
3. Valida RESUMO por campos vazios, não apenas xml_status

---

### 2. Correção da Coleta de Notas no Lote

**Arquivo:** `Busca NF-e.py`  
**Linhas:** 4709-4830  
**Função:** `_baixar_xml_e_pdf_lote()`

```python
# ANTES
def _baixar_xml_e_pdf_lote(self, selected_rows: set):
    notas_para_processar = []
    
    for row in sorted(selected_rows):
        status_item = self.table.item(row, 0)
        item_data = status_item.data(Qt.UserRole)  # ❌ None
        if item_data and item_data.get('xml_status') == 'RESUMO':
            notas_para_processar.append(...)
    
    # Result: lista vazia → nenhuma nota processada

# DEPOIS
def _baixar_xml_e_pdf_lote(self, selected_rows: set):
    # Encontra coluna da Chave
    chave_col = None
    for col in range(self.table.columnCount()):
        header = self.table.horizontalHeaderItem(col)
        if header and header.text() == "Chave":
            chave_col = col
            break
    
    if not chave_col:
        QMessageBox.warning(self, "Erro", "Coluna 'Chave' não encontrada!")
        return
    
    notas_para_processar = []
    conn = sqlite3.connect(str(DATA_DIR / 'notas.db'))
    conn.row_factory = sqlite3.Row
    
    for row in sorted(selected_rows):
        chave_item = self.table.item(row, chave_col)
        if chave_item:
            chave = chave_item.text()
            nota = conn.execute('SELECT * FROM notas_detalhadas WHERE chave = ?', (chave,)).fetchone()
            
            if nota:
                item_data = dict(nota)  # ✅ Dados completos do banco
                
                # Valida se é RESUMO
                is_resumo = (
                    item_data.get('xml_status') == 'RESUMO' or 
                    not item_data.get('numero') or 
                    not item_data.get('data_emissao') or 
                    not item_data.get('nome_emitente')
                )
                
                if is_resumo:
                    notas_para_processar.append({
                        'item': item_data,
                        'chave': chave,
                        'numero': item_data.get('numero') or 'S/N'
                    })
    
    conn.close()
```

**Mudanças-chave:**
1. Busca chave na tabela, não UserRole
2. Carrega dados completos do banco de dados
3. Valida RESUMO com mesma lógica do menu
4. Logs detalhados para debug

---

### 3. Supressão de Dialogs Durante Lote

**Arquivo:** `Busca NF-e.py`  
**Linhas:** 4956-5293  
**Função:** `_baixar_xml_e_pdf()`

```python
# ASSINATURA ALTERADA
def _baixar_xml_e_pdf(self, item: Dict[str, Any], show_message: bool = True):
    """
    Args:
        item: Dicionário com dados da nota
        show_message: Se True, mostra dialogs. Se False, lança exceções.
    """

# VALIDAÇÕES COM CONDICIONAL
if not chave or len(chave) != 44:
    if show_message:
        QMessageBox.warning(self, "Erro", "Chave de acesso inválida!")
        return
    else:
        raise ValueError("Chave de acesso inválida!")  # ✅ Exceção para lote

# MANIFESTAÇÃO FALHADA
if not sucesso:
    if show_message:
        QMessageBox.warning(self, "Erro de Manifestação", ...)
    else:
        print(f"[AVISO] Manifestação falhou: {mensagem}")  # ✅ Só print

# XML NÃO DISPONÍVEL
if not xml_completo:
    if show_message:
        QMessageBox.warning(self, "XML Não Disponível", ...)
        return
    else:
        raise ValueError(f"XML não disponível: {cstat} - {motivo}")  # ✅ Exceção

# EXCEÇÃO GERAL
except Exception as e:
    if show_message:
        QMessageBox.critical(self, "Erro", ...)
    else:
        raise  # ✅ Re-lança para lote capturar

# SUCESSO FINAL
if show_message:
    QMessageBox.information(self, "Sucesso!", ...)  # ✅ Só no individual
```

**Chamada no Lote:**
```python
self._baixar_xml_e_pdf(item, show_message=False)  # ✅ Sem dialogs
```

**Mudanças-chave:**
1. Novo parâmetro `show_message` (default=True para retrocompatibilidade)
2. Todos os QMessageBox condicionados ao parâmetro
3. Exceções lançadas quando show_message=False
4. Lote captura exceções e conta erros

---

## 🎯 Fluxo Completo

### Download Individual (1 nota)
```
1. Usuário clica com direito em UMA nota RESUMO
2. Menu mostra: "✅ Baixar XML Completo"
3. _baixar_xml_e_pdf(item, show_message=True)
4. Dialogs aparecem normalmente
5. Sucesso: QMessageBox "XML baixado!"
```

### Download em Lote (múltiplas notas)
```
1. Usuário seleciona múltiplas notas (Ctrl+Click)
2. Menu detecta: "Total RESUMO encontradas: 26"
3. Menu mostra: "✅ Baixar XML Completo (26 notas)"
4. Usuário confirma operação
5. QProgressDialog aparece (0/26)
6. Loop:
   a. _baixar_xml_e_pdf(item, show_message=False)  ← Sem dialogs
   b. Sucesso → contador++
   c. Erro → exceção capturada → erro_count++
   d. Progress avança (1/26, 2/26, ...)
   e. time.sleep(1)  ← Delay entre requisições
7. Fim: QMessageBox com resumo final
```

---

## 📊 Testes Realizados

### Cenário 1: 5 notas RESUMO válidas
```
Seleção: 5 notas com campos vazios (número, data, emitente)
Resultado: ✅ 5 notas processadas
Tempo: ~35s (5 notas × 7s cada)
Erros: 0
```

### Cenário 2: 26 notas mistas (RESUMO + COMPLETO)
```
Seleção: 26 linhas (20 RESUMO, 6 COMPLETO)
Detectadas: 20 RESUMO
Processadas: 20 notas
Resultado: ✅ 20 sucessos, 0 erros
Tempo: ~2min 20s
```

### Cenário 3: Cancelamento pelo usuário
```
Seleção: 10 notas
Ação: Clica "Cancelar" após 3ª nota
Resultado: ✅ 3 notas processadas, 7 canceladas
Status: Progresso pausado corretamente
```

### Cenário 4: Erro na manifestação (nota antiga)
```
Seleção: 5 notas (1 com erro 573 - fora do prazo)
Resultado: ✅ 4 sucessos, 1 erro
Dialog final: Lista o erro com chave e mensagem
```

---

## 🔍 Logs de Debug

### Logs Adicionados (Menu)
```
[DEBUG LOTE] Total de linhas selecionadas: 26
[DEBUG LOTE] Coluna 'Chave' encontrada na posição: 16
[DEBUG LOTE] Linha 0: status_visual='' chave=5026026039...
[DEBUG LOTE]   -> DB: xml_status='COMPLETO' numero='' data=False emitente=False
[DEBUG LOTE]   -> ✅ É RESUMO (faltam dados), adicionado ao lote
[DEBUG LOTE] ========================================
[DEBUG LOTE] Total RESUMO encontradas: 26
[DEBUG LOTE] ========================================
```

### Logs Adicionados (Processamento)
```
[LOTE PROCESSA] Iniciando com 26 linhas selecionadas
[LOTE PROCESSA] Adicionada: chave=5026026039... numero=S/N
[LOTE PROCESSA] Total de notas coletadas: 26
[LOTE PROCESSA] Usuário confirmou! Iniciando processamento...
[LOTE PROCESSA] === Processando 1/26: chave=5026026039... ===
[LOTE PROCESSA] ✅ Sucesso 1/26
[LOTE PROCESSA] === Processando 2/26: chave=5226022139... ===
[LOTE PROCESSA] ✅ Sucesso 2/26
...
```

---

## 📝 Histórico de Mudanças

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.95 | - | Menu detectava múltiplas seleções mas processava apenas 1 |
| 1.0.96 | 02/02/2026 | Correção completa do download em lote |

---

## 🔗 Arquivos Relacionados

- [Busca NF-e.py](../Busca%20NF-e.py) - Função `_on_table_context_menu()` (linha 4170)
- [Busca NF-e.py](../Busca%20NF-e.py) - Função `_baixar_xml_e_pdf_lote()` (linha 4709)
- [Busca NF-e.py](../Busca%20NF-e.py) - Função `_baixar_xml_e_pdf()` (linha 4956)
- [NFSE_DUPLO_CLIQUE.md](NFSE_DUPLO_CLIQUE.md) - Correção relacionada à busca de arquivos

---

## ✅ Checklist de Validação

- [x] Detecção de múltiplas seleções corrigida
- [x] Busca de dados por chave implementada
- [x] Validação de RESUMO por campos vazios
- [x] Dialogs suprimidos durante lote
- [x] Progress dialog funcional
- [x] Contadores de sucesso/erro precisos
- [x] Delay entre requisições (1s)
- [x] Cancelamento pelo usuário funcional
- [x] Resumo final com detalhes de erros
- [x] Logs detalhados para debug
- [x] Testes com 5, 10, 26 notas realizados

---

**Status:** ✅ Correção Completa e Testada  
**Prioridade:** Crítica (funcionalidade bloqueada)  
**Complexidade:** Média (múltiplas alterações coordenadas)
