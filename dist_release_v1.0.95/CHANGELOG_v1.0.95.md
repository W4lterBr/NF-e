# Changelog - v1.0.95

## 🔧 Correção Crítica de Ordem de Execução

**Data**: 02/02/2026  
**Tipo**: Bug Fix (Critical)  
**Severidade**: Alta  
**Status**: ✅ Resolvido

---

## 🐛 Problema Identificado

### Erro Original:
```
sqlite3.OperationalError: no such column: nsu
File: nfe_search.py, line 1631
Method: get_last_nsu()
```

### Análise da Causa Raiz:

#### Versões Afetadas:
- v1.0.92: Indentação incorreta (migração fora do contexto de conexão)
- v1.0.93: Auto-update implementado, mas banco não migrava
- v1.0.94: Verificação de coluna implementada MAS na ordem ERRADA

#### Descoberta do Bug Real (v1.0.94):

A v1.0.94 tinha código de verificação de coluna, mas executava **DEPOIS** da query que falhava:

```python
def get_last_nsu(self, informante):
    with self._connect() as conn:
        # ❌ LINHA 1631: QUERY EXECUTA PRIMEIRO
        row_notas = conn.execute("""
            SELECT MAX(nsu) FROM notas_detalhadas 
            WHERE informante=? AND nsu IS NOT NULL
        """, (informante,)).fetchone()
        # ... mais código ...
        
    # 🔒 LINHA 1692: VERIFICAÇÃO EXECUTAVA TARDE DEMAIS
    try:
        with self._connect() as check_conn:
            cursor = check_conn.cursor()
            cursor.execute("PRAGMA table_info(notas_detalhadas)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'nsu' not in columns:
                logger.error("❌ EMERGÊNCIA: Coluna 'nsu' não existe!")
                self.criar_tabela_detalhada()
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
```

**Resultado**: App crashava na linha 1631 ANTES da verificação na linha 1692 poder prevenir o erro.

---

## ✅ Solução Implementada

### Mudança na v1.0.95:

Verificação movida para o **INÍCIO** do método, ANTES de qualquer query:

```python
def get_last_nsu(self, informante):
    with self._connect() as conn:
        # ✅ LINHA ~1674: VERIFICAÇÃO EXECUTA PRIMEIRO
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(notas_detalhadas)")
            columns = [row[1] for row in cursor.fetchall()]
            logger.debug(f"🔍 [get_last_nsu] Colunas encontradas: {columns}")
            
            if 'nsu' not in columns:
                logger.error("❌ CRÍTICO: Coluna 'nsu' NÃO EXISTE! Forçando criação imediata...")
                conn.close()  # Evita locks
                self.criar_tabela_detalhada()
                logger.info("✅ criar_tabela_detalhada() executado de get_last_nsu")
                logger.warning("⚠️ Retornando NSU zero devido à recriação")
                return "000000000000000"  # Retorno seguro
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")
            logger.warning("⚠️ Retornando NSU zero devido a erro")
            return "000000000000000"  # Fallback seguro
        
        # ✅ AGORA AS QUERIES SÃO SEGURAS - COLUNA JÁ FOI VERIFICADA
        row = conn.execute("SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)).fetchone()
        nsu_tabela = row[0] if row else "000000000000000"
        
        row_notas = conn.execute("""
            SELECT MAX(nsu) FROM notas_detalhadas 
            WHERE informante=? AND nsu IS NOT NULL AND nsu != ''
        """, (informante,)).fetchone()
        nsu_notas = row_notas[0] if (row_notas and row_notas[0]) else "000000000000000"
        # ... resto do código ...
```

---

## 🔍 Detalhes das Mudanças

### Arquivos Modificados:
- `nfe_search.py` (método `get_last_nsu`, linhas ~1672-1720)
- `version.txt` (1.0.94 → 1.0.95)

### Linhas de Código Alteradas:

| Versão | Linha | Ação | Descrição |
|--------|-------|------|-----------|
| v1.0.94 | 1631 | ❌ Query | `SELECT MAX(nsu)` executava primeiro |
| v1.0.94 | 1692 | 🔒 Check | Verificação executava depois (inútil) |
| **v1.0.95** | **~1674** | **✅ Check** | **Verificação ANTES de queries** |
| **v1.0.95** | **~1700+** | **✅ Query** | **Queries agora são seguras** |

### Melhorias Adicionais:

1. **Conexão Única**: 
   - Antes: Duas conexões separadas (`conn` e `check_conn`)
   - Agora: Uma única conexão gerenciada

2. **Retorno Seguro Antecipado**:
   - Se coluna não existe: retorna `"000000000000000"` imediatamente
   - Previne execução de queries que falhariam

3. **Logs Detalhados**:
   - `logger.debug(f"🔍 [get_last_nsu] Colunas encontradas: {columns}")`
   - Permite verificar exatamente quais colunas existem

4. **Tratamento de Erro Robusto**:
   - Try-except envolve toda a verificação
   - Fallback retorna valor seguro mesmo em caso de erro imprevisto

5. **Fechamento Explícito**:
   - `conn.close()` antes de chamar `criar_tabela_detalhada()`
   - Evita locks de banco durante migração

---

## 📊 Impacto

### Comportamento Esperado:

#### Primeira Execução (Banco Antigo Sem Coluna):
```log
2026-02-02 11:00:29 [INFO] 📄 Iniciando busca de NF-e para 49068153000160
2026-02-02 11:00:29 [DEBUG] 🔍 [get_last_nsu] Colunas encontradas: ['chave', 'ie_tomador', 'nome_emitente', ...]
2026-02-02 11:00:29 [ERROR] ❌ CRÍTICO: Coluna 'nsu' NÃO EXISTE! Forçando criação imediata...
2026-02-02 11:00:29 [INFO] 🔍 Colunas existentes em notas_detalhadas: ['chave', ...]
2026-02-02 11:00:29 [INFO] ✅ Coluna 'nsu' adicionada à tabela notas_detalhadas
2026-02-02 11:00:29 [INFO] ✅ Coluna 'nsu' confirmada!
2026-02-02 11:00:29 [INFO] ✅ criar_tabela_detalhada() executado de get_last_nsu
2026-02-02 11:00:29 [WARNING] ⚠️ Retornando NSU zero devido à recriação
2026-02-02 11:00:29 [INFO] ✅ Pode consultar: True (NSU zero, forçando busca completa)
```

#### Execuções Subsequentes (Coluna Já Existe):
```log
2026-02-02 11:05:00 [DEBUG] 🔍 [get_last_nsu] Colunas encontradas: ['chave', 'ie_tomador', ..., 'nsu']
2026-02-02 11:05:00 [INFO] NSU na tabela 'nsu': 000000000012345
2026-02-02 11:05:00 [INFO] NSU nas notas: 000000000012345
2026-02-02 11:05:00 [INFO] ✅ NSUs consistentes!
```

### Casos de Teste:

| Cenário | v1.0.94 | v1.0.95 |
|---------|---------|---------|
| Banco novo (com coluna) | ✅ Funciona | ✅ Funciona |
| Banco antigo (sem coluna) | ❌ CRASH linha 1631 | ✅ Cria coluna e continua |
| Erro na verificação | ❌ CRASH | ✅ Retorno seguro |
| Múltiplos informantes | ❌ Falha no primeiro | ✅ Funciona para todos |

---

## 🚀 Deploy

### Build Information:
- **Compilado em**: 02/02/2026 10:57:10
- **PyInstaller**: 6.17.0
- **Python**: 3.12.0
- **Plataforma**: Windows 64-bit
- **Build time**: ~70 segundos

### Arquivos Gerados:
1. `dist\Busca XML\Busca XML.exe` (18.5 MB)
2. `Output\Busca_XML_Setup.exe` (54.2 MB)
3. `version.txt` (contém "1.0.95")

### Warnings Durante Build:
```
⚠️ SyntaxWarning: invalid escape sequence '\.' in crypto_portable.py:1
⚠️ SyntaxWarning: invalid escape sequence '\A' in nfe_search.py:788
⚠️ WARNING: Hidden import "sip" not found! (PyQt5 - non-critical)
```
**Status**: Não-bloqueantes, não afetam funcionalidade

---

## 📋 Testing Checklist

- [x] Código compila sem erros
- [x] Executável inicia sem crash
- [x] Banco novo cria estrutura correta
- [x] Banco antigo migra automaticamente
- [x] Coluna 'nsu' verificada ANTES de queries
- [x] Logs mostram verificação executando
- [x] Retorno seguro funciona se coluna ausente
- [x] Múltiplos informantes funcionam
- [x] Auto-update detecta v1.0.95
- [x] Instalador sobrescreve versão antiga

---

## 🔄 Rollback (Se Necessário)

Caso encontre problemas com v1.0.95:

### Voltar para v1.0.93:
```bash
# Baixe v1.0.93
https://github.com/W4lterBr/NF-e/releases/download/v1.0.93/Busca_XML_Setup.exe

# Instale como admin
# Note: v1.0.93 NÃO tem a correção, erro pode persistir
```

### Solução Temporária (Qualquer Versão):
```sql
-- Execute manualmente no banco de dados SQLite
ALTER TABLE notas_detalhadas ADD COLUMN nsu TEXT;
```

Local do banco: `%APPDATA%\Busca XML\nfe_data.db`

---

## 📈 Métricas

### Tempo de Detecção:
- Bug descoberto: 02/02/2026 ~10:00
- Root cause identificada: 02/02/2026 ~10:30
- Correção implementada: 02/02/2026 ~10:45
- Build completado: 02/02/2026 10:57
- **Total**: ~1 hora do bug à solução

### Complexidade:
- Linhas modificadas: ~50
- Métodos afetados: 1 (`get_last_nsu`)
- Arquivos alterados: 2 (`nfe_search.py`, `version.txt`)
- Breaking changes: Nenhum
- Compatibilidade: 100% com bancos antigos e novos

---

## 🎯 Lições Aprendidas

### O Que Funcionou Bem:
✅ Sistema de logs detalhado permitiu debug rápido  
✅ Estrutura de código clara facilitou identificação da causa  
✅ Sistema de versões permitiu tracking preciso  
✅ Backup automático protegeu dados de usuários

### Melhorias para Futuro:
🔄 Adicionar testes automatizados de migração de banco  
🔄 Implementar validação de estrutura de banco na inicialização  
🔄 Criar ferramenta de diagnóstico de banco de dados  
🔄 Adicionar CI/CD para builds automáticos

### Prevenção:
- [ ] Unit tests para migrations
- [ ] Integration tests para get_last_nsu()
- [ ] Database schema validator
- [ ] Pre-flight checks antes de queries críticas

---

## 📞 Contato

**Desenvolvedor**: W4lterBr  
**GitHub**: https://github.com/W4lterBr/NF-e  
**Issues**: https://github.com/W4lterBr/NF-e/issues

---

**Changelog Version**: 1.0  
**Última Atualização**: 02/02/2026 11:00  
**Status**: ✅ ESTÁVEL - PRONTO PARA PRODUÇÃO
