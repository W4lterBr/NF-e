# 🐛 Correção de Bug: Diretórios XML Ausentes

## Problema Identificado

**Erro:** `[Errno 2] No such file or directory`

### Causa Raiz
O aplicativo assumia que todos os diretórios XML já existiam, mas em instalações novas esses diretórios nunca eram criados automaticamente.

### Diretórios Afetados
```
%APPDATA%\Busca XML\
├── xmls\
├── xmls_chave\
├── xmls_nfce\
├── xml_NFs\
├── xml_envio\
├── xml_extraidos\
└── xml_resposta_sefaz\
```

## Solução Implementada

### 1. Criação da Função `ensure_xml_dirs()`

**Arquivo:** `Busca NF-e.py` (linhas 128-143)

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
```

### 2. Chamada na Inicialização

**Arquivo:** `Busca NF-e.py` (linha 559)

```python
ensure_logs_dir()
ensure_xml_dirs()  # ← NOVO: Garante que todas as pastas de XML existam
self.db = UIDB(DB_PATH)
```

## Resultado

✅ **Todos os diretórios XML são criados automaticamente na primeira execução**
✅ **Não há mais erros "[Errno 2]" ao buscar notas fiscais**
✅ **Instalações novas funcionam sem necessidade de configuração manual**

## Arquivos Modificados

- **Busca NF-e.py**
  - Linhas 128-143: Nova função `ensure_xml_dirs()`
  - Linha 559: Chamada na inicialização do `MainWindow`

## Versão Corrigida

- **Versão:** 1.0.95
- **Executável:** `Busca XML.exe` (17.68 MB)
- **Instalador:** `Busca_XML_Setup.exe` (51.68 MB)
- **Data:** 2025-01-28

## Teste de Validação

Para verificar se a correção funcionou:

1. Instale a nova versão
2. Abra o aplicativo
3. Vá em `Opções > Abrir Pasta de Dados`
4. Verifique se todos os diretórios XML foram criados automaticamente
5. Tente buscar uma nota fiscal - deve funcionar sem erros

## Impacto

- **Gravidade:** 🔴 CRÍTICO (bloqueava o uso do aplicativo em instalações novas)
- **Usuários Afetados:** Todos os novos usuários ou reinstalações limpas
- **Tempo de Correção:** 1 sessão de desenvolvimento
- **Backward Compatibility:** ✅ Total (não afeta instalações antigas)

---

**Desenvolvido por:** DWM System Developer  
**GitHub:** https://github.com/W4lterBr/NF-e  
**Tag:** v1.0.95
