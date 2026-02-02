# 🚀 Instruções para Upload no GitHub

## Arquivos para Upload na Release v1.0.95

Você tem **2 opções** para fazer o upload:

---

## Opção 1: Upload do ZIP Completo (RECOMENDADO)

✅ **Mais fácil e rápido**

1. **Acesse**: https://github.com/W4lterBr/NF-e/releases/new?tag=v1.0.95

2. **Preencha**:
   - **Tag**: `v1.0.95`
   - **Title**: `v1.0.95 - Correção Crítica de Ordem de Execução`

3. **Faça upload deste arquivo**:
   - `dist_release_v1.0.95.zip` (68.16 MB)

4. **Description** (copie e cole):
```markdown
## 🔧 Correção Crítica - Ordem de Execução de Verificação

**IMPORTANTE**: Esta versão corrige definitivamente o erro "no such column: nsu".

### 📦 Conteúdo do Pacote

Este release contém:
- **Busca XML.exe** - Executável standalone (18.5 MB)
- **Busca_XML_Setup.exe** - Instalador completo (54.2 MB) ⭐ RECOMENDADO
- **README.md** - Documentação completa
- **CHANGELOG_v1.0.95.md** - Histórico detalhado de mudanças
- **version.txt** - Arquivo de versão

### 🐛 Problema Corrigido

#### O que estava acontecendo (v1.0.92-1.0.94):
```
Erro: sqlite3.OperationalError: no such column: nsu
Local: nfe_search.py, linha 1631, método get_last_nsu()
Causa: Verificação de coluna executava DEPOIS da query (linha 1692)
```

#### Solução implementada (v1.0.95):
- ✅ Verificação de coluna 'nsu' movida para **INÍCIO** do método
- ✅ Execução ANTES de qualquer SELECT query
- ✅ Retorno seguro se coluna não existir
- ✅ Criação automática da coluna
- ✅ Logs detalhados para debugging

### 📥 Como Instalar

**Baixe o arquivo ZIP** e extraia o conteúdo.

**Depois:**

1. **Feche** o aplicativo Busca XML se estiver em execução
2. **Clique com botão direito** em `Busca_XML_Setup.exe`
3. Selecione **"Executar como administrador"**
4. Siga o assistente de instalação

### 🔍 Primeira Execução

Se você tinha versão anterior, na primeira execução você verá nos logs:

```
🔍 [get_last_nsu] Colunas encontradas: [...]
❌ CRÍTICO: Coluna 'nsu' NÃO EXISTE! Forçando criação imediata...
✅ Coluna 'nsu' adicionada à tabela notas_detalhadas
✅ criar_tabela_detalhada() executado de get_last_nsu
⚠️ Retornando NSU zero devido à recriação
```

**Isso é normal!** O app detectou o problema e corrigiu automaticamente.

### ⚡ Auto-Update

Após instalar v1.0.95, futuras atualizações serão automáticas via botão "🔄 Atualizações" na interface.

### 📖 Documentação

Leia o arquivo **README.md** incluído no ZIP para:
- Instruções detalhadas de instalação
- Solução de problemas
- Detalhes técnicos
- Histórico completo de mudanças

---

### 🆘 Problemas?

Se após instalar v1.0.95 o erro persistir:
1. Verifique a versão instalada (deve mostrar "v1.0.95")
2. Verifique os logs em: `%APPDATA%\Busca XML\logs\`
3. Reporte no [Issues](https://github.com/W4lterBr/NF-e/issues)

---

**Data**: 02/02/2026  
**Build**: PyInstaller 6.17.0 | Python 3.12.0  
**Plataforma**: Windows 10/11 (64-bit)
```

5. **Marque**: ✅ "Set as the latest release"

6. **Clique**: "Publish release"

---

## Opção 2: Upload Individual dos Arquivos

Se preferir fazer upload arquivo por arquivo:

1. **Acesse**: https://github.com/W4lterBr/NF-e/releases/new?tag=v1.0.95

2. **Preencha** tag e title (mesmo da Opção 1)

3. **Faça upload destes 3 arquivos** (na pasta `dist_release_v1.0.95\`):
   - ✅ `Busca XML.exe` (18.5 MB)
   - ✅ `Busca_XML_Setup.exe` (54.2 MB) - **PRINCIPAL**
   - ✅ `version.txt` (6 bytes)

4. **Description**: Use a mesma descrição da Opção 1 (ajuste conforme necessário)

5. **Publish release**

---

## Após Publicar

### Verificação:

```powershell
# Teste se o auto-update consegue baixar
Invoke-RestMethod -Uri "https://api.github.com/repos/W4lterBr/NF-e/releases/latest" | Select-Object tag_name, name, published_at
```

**Deve retornar**:
```
tag_name     : v1.0.95
name         : v1.0.95 - Correção Crítica de Ordem de Execução
published_at : 2026-02-02T...
```

### URLs de Download Direto:

Após publicar, os arquivos estarão disponíveis em:

**ZIP Completo**:
```
https://github.com/W4lterBr/NF-e/releases/download/v1.0.95/dist_release_v1.0.95.zip
```

**Arquivos Individuais**:
```
https://github.com/W4lterBr/NF-e/releases/download/v1.0.95/Busca%20XML.exe
https://github.com/W4lterBr/NF-e/releases/download/v1.0.95/Busca_XML_Setup.exe
https://github.com/W4lterBr/NF-e/releases/download/v1.0.95/version.txt
```

---

## Notificação aos Usuários

### Via App (Auto-Update):

Usuários com v1.0.92, v1.0.93 ou v1.0.94 verão automaticamente:

```
🆕 Nova versão disponível!
Versão atual: 1.0.92 (ou 1.0.93/1.0.94)
Versão disponível: 1.0.95

[Detalhes] [Atualizar Agora] [Mais Tarde]
```

Ao clicar "Atualizar Agora":
- Baixa automaticamente de: `https://github.com/W4lterBr/NF-e/releases/download/v1.0.95/Busca%20XML.exe`
- Cria backup da versão atual
- Substitui arquivos
- Reinicia aplicação

### Via GitHub:

Crie uma [Discussion](https://github.com/W4lterBr/NF-e/discussions) ou pinne um Issue:

```markdown
🚨 IMPORTANTE: Atualização v1.0.95 Disponível

Esta versão corrige um erro crítico que causava crash na inicialização.

**Problema corrigido**: "no such column: nsu"

**Recomendamos atualização imediata para todos os usuários!**

👉 [Download v1.0.95](https://github.com/W4lterBr/NF-e/releases/tag/v1.0.95)
```

---

## Checklist Final

Antes de publicar:
- [x] Executável testado e funcionando (v1.0.95)
- [x] Instalador cria estrutura correta
- [x] README.md completo e claro
- [x] CHANGELOG detalhado
- [x] ZIP criado com todos os arquivos
- [x] Tamanho do ZIP razoável (68 MB)

Após publicar:
- [ ] Verificar se release aparece como "latest"
- [ ] Testar download dos arquivos
- [ ] Testar auto-update de versão antiga
- [ ] Confirmar que URLs de download funcionam
- [ ] Notificar usuários (se houver)

---

## 🎯 Link Rápido para Criar Release

**Clique aqui para começar**:
👉 https://github.com/W4lterBr/NF-e/releases/new?tag=v1.0.95

---

**Boa sorte com o release! 🚀**

Se precisar de ajuda, consulte: https://docs.github.com/pt/repositories/releasing-projects-on-github/managing-releases-in-a-repository
