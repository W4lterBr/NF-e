# 🐛 Correção Crítica: UnicodeEncodeError na Busca

## Problema Identificado

**Sintoma:** "Erro na busca completa" - nenhuma nota encontrada, sem mensagens de erro nos logs

### Erro Real (Escondido)
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0
```

**Causa Raiz:**
- Windows usa codificação `cp1252` por padrão no terminal
- Código usa emojis Unicode (`✅`, `❌`, `🔧`, etc.) nos logs
- Python não conseguia escrever emojis no stdout com `cp1252`
- Exceção silenciosa no logger impedindo execução da busca
- **Logs vazios** porque o logger falhava antes de escrever

## Impacto

- **Gravidade:** 🔴 CRÍTICO (bloqueava 100% das buscas)
- **Afetados:** Todos os usuários no Windows ao fazer "Busca Completa"
- **Detectabilidade:** Baixa (erro não aparecia nos logs)

## Correções Aplicadas

### 1. Força Encoding UTF-8 no stdout

**Arquivo:** `Busca NF-e.py` - Função `run_search()` (linha ~150)

```python
def run_search(progress_cb: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Executa a busca de NFe/CTe na SEFAZ."""
    # ✅ FORÇA ENCODING UTF-8 NO STDOUT (Windows usa cp1252 por padrão)
    import io
    import sys
    
    # Reconfigura stdout para UTF-8 com tratamento de erros
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            errors='replace',  # ← Substitui caracteres inválidos em vez de crashar
            line_buffering=True
        )
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            errors='replace', 
            line_buffering=True
        )
```

**Efeito:**
- Todos os emojis são exibidos corretamente
- Nenhum crash por caracteres Unicode
- Logs funcionam normalmente

### 2. Emojis Substituídos em Prints Críticos

**Arquivo:** `nfe_search.py` - Função `setup_logger()` (linhas 100-150)

```python
# ANTES:
print(f"✅ Logger configurado: {log_filename}")
print(f"❌ ERRO ao configurar logger: {e}")
print(f"⚠️ Erro ao criar arquivo de log: {e}")

# DEPOIS:
print(f"[OK] Logger configurado: {log_filename}")
print(f"[ERRO] ERRO ao configurar logger: {e}")
print(f"[AVISO] Erro ao criar arquivo de log: {e}")
```

**Motivo:** Garante que mesmo sem UTF-8, mensagens críticas aparecem

### 3. Diretórios XML Criados Automaticamente

**Arquivo:** `Busca NF-e.py` (linhas 128-143 e 559)

```python
def ensure_xml_dirs():
    """Garante que todos os diretórios de XML necessários existam."""
    try:
        required_dirs = [
            DATA_DIR / "xmls",
            DATA_DIR / "xmls_chave",
            DATA_DIR / "xmls_nfce",
            DATA_DIR / "xml_NFs",
            DATA_DIR / "xml_envio",
            DATA_DIR / "xml_extraidos",
            DATA_DIR / "xml_resposta_sefaz",
        ]
        for dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[WARNING] Erro ao criar diretórios XML: {e}")

# Chamada na inicialização
ensure_logs_dir()
ensure_xml_dirs()  # ← Cria todos os diretórios necessários
```

**Efeito:** Elimina erros `[Errno 2] No such file or directory`

## Testes de Validação

### Teste 1: Busca Completa
1. Abrir aplicativo
2. Clicar em "Busca Completa"
3. ✅ **Esperado:** Busca inicia e progride normalmente
4. ✅ **Esperado:** Logs aparecem no terminal/arquivo

### Teste 2: Logs com Emojis
1. Verificar arquivo de log em `%APPDATA%\Busca XML\logs\`
2. ✅ **Esperado:** Emojis visíveis ou substituídos corretamente
3. ✅ **Esperado:** Nenhuma linha truncada

### Teste 3: Diretórios Automáticos
1. Limpar `%APPDATA%\Busca XML\`
2. Abrir aplicativo pela primeira vez
3. ✅ **Esperado:** Todos os 7 diretórios XML criados automaticamente
4. ✅ **Esperado:** Busca funciona sem erros de "file not found"

## Arquivos Modificados

| Arquivo | Linhas | Alteração |
|---------|--------|-----------|
| `Busca NF-e.py` | 128-143 | Nova função `ensure_xml_dirs()` |
| `Busca NF-e.py` | 147-165 | Encoding UTF-8 forçado em `run_search()` |
| `Busca NF-e.py` | 559 | Chamada `ensure_xml_dirs()` na init |
| `nfe_search.py` | 106-108 | Emoji `⚠️` → `[AVISO]` |
| `nfe_search.py` | 135 | Emoji `✅` → `[OK]` |
| `nfe_search.py` | 138 | Emoji `❌` → `[ERRO]` |
| `nfe_search.py` | 150 | Emoji `✅` → `[OK]` |

## Versão Corrigida

- **Versão:** 1.0.95
- **Executável:** `Busca XML.exe` (17.68 MB)
- **Instalador:** `Busca_XML_Setup.exe` (51.68 MB)
- **Data:** 2026-02-02
- **Compilador:** PyInstaller 6.17.0 + Python 3.12.0

## Notas Técnicas

### Por que o erro era "invisível"?

1. **Exceção no logger** → `setup_logger()` falhava silenciosamente
2. **Logger não inicializado** → Nenhuma mensagem gravada
3. **Busca parava** → `run_single_cycle()` não executava
4. **Interface genérica** → Apenas "Erro na busca completa"
5. **Logs vazios** → Usuário não sabia o que estava errado

### Por que `errors='replace'`?

```python
sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, 
    encoding='utf-8', 
    errors='replace',  # ← IMPORTANTE!
    line_buffering=True
)
```

**Opções:**
- `errors='strict'` → Crash no primeiro caractere inválido ❌
- `errors='ignore'` → Remove caracteres inválidos (perde informação) ⚠️
- `errors='replace'` → Substitui por `?` (mantém informação legível) ✅

### Por que manter emojis no logger?

- **Logs em arquivo** → UTF-8, emojis funcionam perfeitamente
- **Interface gráfica** → PyQt5 usa UTF-8 internamente
- **Apenas prints críticos** → Substituídos por `[OK]`, `[ERRO]`, etc.

## Histórico de Debug

**13:45** - Usuário reporta erro "Erro na busca completa"  
**13:50** - Verificado logs vazios em `%APPDATA%\Busca XML\logs`  
**13:52** - Testado `run_single_cycle()` diretamente → Encontrado `UnicodeEncodeError`  
**13:55** - Identificado emojis incompatíveis com `cp1252`  
**14:00** - Implementado encoding UTF-8 forçado  
**14:05** - Substituídos emojis em prints críticos  
**14:10** - Recompilado e testado → Busca funcionando  
**14:15** - Gerado novo instalador v1.0.95

## Próximos Passos

1. ✅ Usuário instala nova versão
2. ✅ Testa "Busca Completa"
3. ✅ Confirma logs funcionando
4. ⏳ Upload no GitHub Release
5. ⏳ Publicar release v1.0.95

---

**Desenvolvido por:** DWM System Developer  
**GitHub:** https://github.com/W4lterBr/NF-e  
**Tag:** v1.0.95  
**Commits:** encoding-utf8-fix, ensure-xml-dirs
