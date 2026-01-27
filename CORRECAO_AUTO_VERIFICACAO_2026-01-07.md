# Correção: Auto-verificação não encontra XMLs - 2026-01-07

## 🐛 Problema Identificado

A **auto-verificação** mostrava que os XMLs não estavam sendo encontrados, mesmo após serem baixados com sucesso:

```
[AUTO-VERIFICAÇÃO] ⚠️ XML não encontrado: 50251230044541000182550010000009371851390330
[AUTO-VERIFICAÇÃO] ⚠️ XML não encontrado: 50251229067113042271550190000487471647302568
[AUTO-VERIFICAÇÃO] ⚠️ XML não encontrado: 52251208967878000102550010000292451002186327
```

**Log do processamento**:
```
💾 NF-e: Salvando em xmls/ (backup) - chave=50251230044541000182550010000009371851390330
💾 NF-e: Copiando para armazenamento (C:\Arquivo Walter - Empresas\Notas\NFs)
⚠️ Nota 5025123004454100018255001... marcada como COMPLETO mas sem arquivo em xmls_baixados. Corrigindo para RESUMO.
```

## 🔍 Causa Raiz

**Inconsistência no fluxo de salvamento/validação**:

1. **`salvar_xml_por_certificado()`** salvava o XML em disco
2. **`registrar_xml()`** registrava apenas `chave + cnpj` NO BANCO (SEM caminho do arquivo)
3. **`salvar_nota_detalhada()`** validava se existe `caminho_arquivo` na tabela `xmls_baixados`
4. **Validação falhava** porque `caminho_arquivo` era NULL!

### Código Problemático

```python
# registrar_xml() - Linha 1425 (ANTES)
def registrar_xml(self, chave, cnpj):
    conn.execute(
        "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",  # ❌ Não salva caminho!
        (chave, cnpj)
    )

# salvar_nota_detalhada() - Linha 1190 (VALIDAÇÃO)
cursor = conn.execute(
    "SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?",  # ❌ Busca caminho que não existe!
    (chave,)
)
if not row or not row[0]:  # ❌ Sempre vai falhar porque caminho_arquivo é NULL
    xml_status = 'RESUMO'  # ❌ Marca como RESUMO mesmo tendo o XML salvo!
    logger.warning(f"⚠️ Nota marcada como COMPLETO mas sem arquivo em xmls_baixados. Corrigindo para RESUMO.")
```

## ✅ Solução Implementada

### 1. Atualizada `registrar_xml()` para aceitar caminho

```python
def registrar_xml(self, chave, cnpj, caminho_arquivo=None):
    """
    Registra XML baixado no banco de dados.
    
    Args:
        chave: Chave de acesso (44 dígitos)
        cnpj: CNPJ/CPF do informante
        caminho_arquivo: Caminho completo onde o XML foi salvo (NOVO parâmetro)
    """
    with self._connect() as conn:
        if caminho_arquivo:
            # ✅ Registra ou atualiza com o caminho do arquivo
            conn.execute('''
                INSERT INTO xmls_baixados (chave, cnpj_cpf, caminho_arquivo, baixado_em)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(chave) DO UPDATE SET
                    caminho_arquivo = excluded.caminho_arquivo,
                    baixado_em = datetime('now')
            ''', (chave, cnpj, caminho_arquivo))
            logger.debug(f"XML registrado: {chave} → {caminho_arquivo}")
        else:
            # Fallback: mantém compatibilidade
            conn.execute(
                "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
                (chave, cnpj)
            )
        conn.commit()
```

### 2. Modificada `salvar_xml_por_certificado()` para retornar caminho

```python
def salvar_xml_por_certificado(xml, cnpj_cpf, pasta_base="xmls", nome_certificado=None):
    """
    Returns:
        str: Caminho absoluto onde o XML foi salvo, ou None se não foi salvo
    """
    try:
        # ... salva XML em disco ...
        
        caminho_absoluto = os.path.abspath(caminho_xml)
        return caminho_absoluto  # ✅ Retorna o caminho
        
    except Exception as e:
        return None  # ❌ Erro ao salvar
```

### 3. Atualizado fluxo de processamento NF-e

```python
# 1. Salva XML e obtém o caminho
logger.info(f"💾 [{cnpj}] NF-e: Salvando em xmls/ (backup) - chave={chave}")
caminho_xml = salvar_xml_por_certificado(xml, cnpj, pasta_base="xmls", nome_certificado=nome_cert)

# 2. Registra XML no banco COM o caminho do arquivo
if caminho_xml:
    db.registrar_xml(chave, cnpj, caminho_xml)  # ✅ Passa o caminho!
else:
    # Fallback: registra sem caminho
    db.registrar_xml(chave, cnpj)
    logger.warning(f"⚠️ [{cnpj}] XML salvo mas caminho não obtido: {chave}")
```

### 4. Script de correção para registros existentes

Criado `corrigir_caminhos_xmls.py` para atualizar os 1.920 registros que já estavam no banco sem caminho:

```bash
python corrigir_caminhos_xmls.py
```

**Resultado**:
```
✅ XMLs encontrados e atualizados: 1918
❌ XMLs não encontrados: 2
📈 Taxa de sucesso: 99.9%
```

## 🎯 Impacto

### Antes
- ❌ XMLs salvos em disco mas marcados como RESUMO no banco
- ❌ Auto-verificação falhava (não encontrava XMLs)
- ❌ Interface mostrava status cinza (RESUMO) para notas completas
- ❌ Usuário tinha que buscar manualmente os XMLs novamente

### Depois
- ✅ XMLs salvos E registrados com caminho completo no banco
- ✅ Auto-verificação funciona corretamente
- ✅ Interface mostra status correto (COMPLETO para notas baixadas)
- ✅ Sistema sabe exatamente onde está cada XML

## 📊 Estrutura da Tabela xmls_baixados

```sql
CREATE TABLE xmls_baixados (
    chave TEXT PRIMARY KEY,           -- Chave de acesso (44 dígitos)
    cnpj_cpf TEXT,                    -- CNPJ/CPF do certificado
    caminho_arquivo TEXT,             -- ✅ NOVO: Caminho completo do XML
    baixado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Manutenção Futura

**Sempre** que salvar um XML:
1. Chamar `salvar_xml_por_certificado()` e **guardar o caminho retornado**
2. Passar esse caminho para `registrar_xml(chave, cnpj, caminho_arquivo)`
3. Nunca chamar `registrar_xml()` sem o terceiro parâmetro

## 📝 Arquivos Modificados

- [nfe_search.py](nfe_search.py):
  - `registrar_xml()` - Linha ~1425 (aceita caminho_arquivo)
  - `salvar_xml_por_certificado()` - Linha ~687 (retorna caminho)
  - Fluxo de processamento NF-e - Linha ~2649 (passa caminho para registrar_xml)

- [corrigir_caminhos_xmls.py](corrigir_caminhos_xmls.py) - Novo script de correção

## ✅ Validação

Execute novamente o programa e verifique:

1. **Log não deve mais mostrar**: `"marcada como COMPLETO mas sem arquivo em xmls_baixados"`
2. **Interface deve mostrar**: Status verde (COMPLETO) para XMLs baixados
3. **Auto-verificação não deve falhar** para XMLs que existem em disco
4. **Banco deve ter**: `caminho_arquivo` preenchido para todos os novos XMLs

```sql
-- Verificar registros com caminho
SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL;

-- Verificar registros sem caminho (devem ser 0 após correção)
SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NULL;
```
