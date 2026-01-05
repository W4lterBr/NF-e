# Correção do Sistema de Export - v1.0.79

## Problema Identificado

O sistema de export estava falhando ao tentar localizar arquivos XML/PDF, mostrando mensagens como:
```
❌ XML não encontrado em nenhum local
```

## Diagnóstico

Através do script `debug_export.py`, identificamos que:

1. **Tabela `xmls_baixados` estava praticamente vazia**
   - Apenas 1 registro
   - Campo `caminho_arquivo` estava `None` em todos
   - Os XMLs existiam fisicamente no disco, mas não estavam registrados no banco

2. **Arquivos existentes no disco**
   - 95 XMLs em `xmls_chave/`
   - 14.136 XMLs em `xmls/` (CTe e outros)
   - Total de 14.231 arquivos

3. **Descompasso entre banco e disco**
   - A tabela `notas_detalhadas` tinha registros
   - A tabela `xmls_baixados` NÃO tinha os caminhos dos arquivos
   - O sistema de export dependia de `xmls_baixados.caminho_arquivo`

## Causa Raiz

Quando os XMLs foram baixados anteriormente, o processo de salvamento no disco **não registrou os caminhos na tabela `xmls_baixados`**. Isso pode ter ocorrido por:
- Versão antiga do código que não fazia o INSERT correto
- Erro durante o processo de download
- Migração de dados incompleta

## Solução

### 1. Script de Diagnóstico (`debug_export.py`)

Script completo para analisar:
- Estrutura de diretórios (BASE_DIR vs DATA_DIR)
- Estado das tabelas do banco
- Localização física dos arquivos
- Teste de busca para uma chave específica

**Uso:**
```bash
python debug_export.py
```

### 2. Script de Correção (`corrigir_banco_xmls.py`)

Script que:
1. Varre todos os diretórios de XMLs
2. Extrai as chaves de 44 dígitos dos nomes dos arquivos
3. Atualiza ou insere registros em `xmls_baixados` com os caminhos corretos
4. Tenta buscar CNPJ correspondente em `notas_detalhadas`

**Resultado da execução:**
```
✅ Inseridos: 95 novos registros
📊 Total de registros com caminho: 95
```

**Uso:**
```bash
python corrigir_banco_xmls.py
```

### 3. Execução do Fix

Execute uma única vez:
```bash
python corrigir_banco_xmls.py
```

Agora o banco está sincronizado com os arquivos no disco.

## Como Prevenir no Futuro

### Em `nfe_search.py` e similares

Quando salvar um XML, **SEMPRE** registrar em `xmls_baixados`:

```python
def salvar_xml(self, chave, xml_content, cnpj):
    # Salva o arquivo
    caminho = Path("xmls_chave") / cnpj / f"{chave}.xml"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(xml_content, encoding='utf-8')
    
    # ✅ SEMPRE registrar no banco
    with self.db._connect() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO xmls_baixados 
            (chave, cnpj_cpf, caminho_arquivo, baixado_em)
            VALUES (?, ?, ?, datetime('now'))
        """, (chave, cnpj, str(caminho.absolute())))
```

### Verificação Periódica

Execute `debug_export.py` periodicamente para verificar se há descompassos:

```bash
python debug_export.py
```

Se aparecer muitos registros "Sem caminho", execute a correção novamente.

## Estrutura da Tabela `xmls_baixados`

```sql
CREATE TABLE xmls_baixados (
    chave TEXT PRIMARY KEY,
    cnpj_cpf TEXT,
    caminho_arquivo TEXT,  -- ✅ CRÍTICO: Caminho absoluto do XML
    xml_completo TEXT,
    baixado_em DATETIME
);
```

**Campos importantes:**
- `chave`: Chave de 44 dígitos (PRIMARY KEY)
- `caminho_arquivo`: **ESSENCIAL** para o export funcionar
- `baixado_em`: Data/hora do download

## Fluxo Correto de Download

```
1. Buscar XML via API Sefaz
2. Salvar arquivo no disco
3. Registrar em xmls_baixados com caminho
4. Extrair dados e registrar em notas_detalhadas
5. ✅ Ambas as tabelas sincronizadas
```

## Testando o Export Após Correção

1. Abra a interface
2. Selecione uma ou mais notas na tabela
3. Clique em "Exportar"
4. Escolha opções (XML/PDF)
5. Escolha destino
6. ✅ Deve funcionar para as 95 notas corrigidas

## Scripts Disponíveis

| Script | Função |
|--------|--------|
| `debug_export.py` | Diagnóstico completo do sistema |
| `corrigir_banco_xmls.py` | Corrige banco com arquivos existentes |
| `debug_db.py` | Debug geral do banco de dados |

## Versões

- **v1.0.78**: Debug logs detalhados no export
- **v1.0.79**: Scripts de diagnóstico e correção do banco

## Observações

1. **Uma nota sem arquivo**: A chave `42251033070814001123570090006208731045663011` está em `notas_detalhadas` mas não tem XML no disco. Isso é normal para notas resumidas que nunca tiveram o XML completo baixado.

2. **CTe vs NFe**: Os 14.136 arquivos em `xmls/` são CTe e outros documentos, com nomenclatura diferente. O script de correção foca nos XMLs em `xmls_chave/` que seguem o padrão `{chave}.xml`.

3. **DATA_DIR vs BASE_DIR**: Em desenvolvimento, DATA_DIR = BASE_DIR. Quando compilado como .exe, DATA_DIR = AppData. O sistema está preparado para ambos os casos.
