# 🚨 UPLOAD URGENTE PARA GITHUB - v1.0.95

## ❌ PROBLEMA IDENTIFICADO

**O sistema de auto-update está falhando porque:**

1. GitHub tem apenas v1.0.93 como última release
2. Release v1.0.93 **NÃO CONTÉM "Busca XML.exe"** - só tem o instalador!
3. Sistema tenta baixar "Busca XML.exe" da release → Não encontra → **ERRO!**

## ✅ SOLUÇÃO

Você DEVE fazer upload de **3 arquivos** na release v1.0.95:

### 📦 Arquivos Obrigatórios

```
✅ Busca XML.exe        (17.68 MB) ← CRÍTICO! Sistema baixa este arquivo
✅ Busca_XML_Setup.exe  (51.68 MB) ← Instalador completo
✅ version.txt          (0 KB)     ← Contém "1.0.95"
```

---

## 📋 PASSO A PASSO - FAZER AGORA

### 1️⃣ Acessar GitHub Releases

👉 Abra este link: https://github.com/W4lterBr/NF-e/releases/new?tag=v1.0.95

### 2️⃣ Preencher Informações da Release

**Tag version:**
```
v1.0.95
```

**Release title:**
```
v1.0.95 - Correção Sistema NSU e Desinstalação Completa
```

**Description:**
```markdown
# 🎉 Versão 1.0.95

## ✨ Correções Críticas

### 🗄️ **Banco de Dados**
- ✅ Corrigido erro "sqlite3.OperationalError: no such column: nsu"
- ✅ Validação automática da estrutura da tabela antes de consultas
- ✅ Migração automática para adicionar coluna "nsu" em bancos antigos
- ✅ Verificação executada ANTES de queries (não mais depois)

### 🗑️ **Desinstalação Completa**
- ✅ Remove **100% dos arquivos** ao desinstalar
- ✅ Deleta pasta Program Files\Busca XML automaticamente
- ✅ Deleta %APPDATA%\Busca XML e dados do usuário
- ✅ **SEM confirmações** - tudo automático!

### 🔄 **Sistema de Auto-Update**
- ✅ Download automático de atualizações
- ✅ Substitui executável sem intervenção do usuário
- ✅ Reinicia aplicação automaticamente após atualização

---

## 📥 Como Atualizar

### **Opção 1: Auto-Update (Recomendado)**
1. Abra o Busca XML v1.0.93 ou anterior
2. Menu: **Configurações → 🔄 Atualizações**
3. Clique em **"Sim"**
4. Aguarde o download automático
5. Aplicação reiniciará automaticamente

### **Opção 2: Instalador Completo**
1. Baixe `Busca_XML_Setup.exe` abaixo
2. Execute o instalador
3. Pronto!

---

## ⚠️ Importante

**Ao desinstalar** (versão 1.0.95+), o sistema remove **TODOS os dados**:
- ✅ Executável principal
- ✅ Banco de dados SQLite
- ✅ XMLs baixados
- ✅ Certificados
- ✅ Configurações

**Faça backup antes se necessário!**

---

## 📊 Changelog Completo

**v1.0.95** (02/02/2026)
- [FIX] Erro "no such column: nsu" resolvido definitivamente
- [FIX] Verificação de estrutura movida para ANTES das queries
- [FIX] Desinstalador agora remove pasta Program Files completamente
- [FIX] Remoção de mensagens de confirmação na desinstalação
- [FEATURE] Sistema de auto-update TRUE funcional
- [IMPROVE] Validação de tabelas antes de cada operação

**v1.0.93** (02/02/2026)
- [FEATURE] Implementado sistema de auto-update
- [FEATURE] Download automático de atualizações do GitHub
- [FIX] Correções no banco de dados

---

## 🔗 Links Úteis

- 📖 **Documentação**: [README.md](https://github.com/W4lterBr/NF-e)
- 🐛 **Reportar Bug**: [Issues](https://github.com/W4lterBr/NF-e/issues)
- 💬 **Discussões**: [Discussions](https://github.com/W4lterBr/NF-e/discussions)

---

**Desenvolvido por**: DWM System Developer  
**Data**: 02 de fevereiro de 2026  
**Versão**: 1.0.95
```

### 3️⃣ Fazer Upload dos 3 Arquivos

**ARRASTE OS ARQUIVOS** desta pasta para a área de upload:

```
📁 dist_release_v1.0.95_COMPLETO\
   ├── Busca XML.exe         ← ARRASTE PARA O GITHUB
   ├── Busca_XML_Setup.exe   ← ARRASTE PARA O GITHUB
   └── version.txt           ← ARRASTE PARA O GITHUB
```

### 4️⃣ Publicar Release

✅ **NÃO** marque como "Pre-release"  
✅ **MARQUE** como "Set as the latest release"  
✅ Clique em **"Publish release"**

---

## ✅ VERIFICAÇÃO APÓS UPLOAD

Depois de publicar, verifique se os 3 arquivos aparecem na página da release:

👉 https://github.com/W4lterBr/NF-e/releases/tag/v1.0.95

**Deve mostrar:**
```
Assets 5
  📄 Busca XML.exe (17.68 MB)
  📄 Busca_XML_Setup.exe (51.68 MB)
  📄 version.txt (0 KB)
  📦 Source code (zip)
  📦 Source code (tar.gz)
```

---

## 🧪 TESTE FINAL

Após fazer upload:

1. Abra o aplicativo na versão **v1.0.0** (ou qualquer versão antiga)
2. Menu → **Configurações** → **🔄 Atualizações**
3. Sistema deve:
   - ✅ Detectar v1.0.95 disponível
   - ✅ Baixar "Busca XML.exe" (17.68 MB)
   - ✅ Substituir executável automaticamente
   - ✅ Reiniciar aplicação
   - ✅ Mostrar v1.0.95 na tela principal

---

## 🚨 ATENÇÃO

**SEM "Busca XML.exe" no GitHub = Auto-update quebrado!**

O sistema espera **exatamente** este arquivo:
- ✅ Nome: `Busca XML.exe` (com espaço)
- ❌ NÃO: `Busca_XML.exe` 
- ❌ NÃO: `busca xml.exe`
- ❌ NÃO: `BuscaXML.exe`

---

## 📞 Suporte

Se tiver problemas:
1. Verifique se os 3 arquivos foram carregados
2. Verifique se a release está marcada como "latest"
3. Aguarde 1-2 minutos (cache do GitHub)
4. Teste novamente

---

**FAÇA UPLOAD AGORA!** 🚀

👉 https://github.com/W4lterBr/NF-e/releases/new?tag=v1.0.95
