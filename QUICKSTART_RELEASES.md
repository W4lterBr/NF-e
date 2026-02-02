# 🚀 INÍCIO RÁPIDO - Upload Automático de Releases

## ⚡ Setup em 3 Passos

### 1️⃣ Instalar e Configurar GitHub CLI

Execute:
```powershell
.\setup_github_cli.ps1
```

Este script irá:
- ✅ Verificar se GitHub CLI está instalado
- ✅ Instalar automaticamente (se necessário)
- ✅ Guiar você pela autenticação
- ✅ Confirmar que tudo está pronto

### 2️⃣ Fazer Upload da Release

Execute:
```powershell
.\upload_github_release.ps1
```

### 3️⃣ Pronto! 🎉

A release estará disponível em:
```
https://github.com/W4lterBr/NF-e/releases/latest
```

---

## 📋 O Que Você Precisa

- ✅ PowerShell (já vem no Windows)
- ✅ Acesso à internet
- ✅ Conta no GitHub

**Não precisa instalar nada manualmente!** O script `setup_github_cli.ps1` faz tudo.

---

## 🎯 Comandos Rápidos

**Setup inicial (só uma vez):**
```powershell
.\setup_github_cli.ps1
```

**Upload de release:**
```powershell
.\upload_github_release.ps1
```

**Upload como rascunho:**
```powershell
.\upload_github_release.ps1 -Draft
```

**Ver ajuda:**
```powershell
Get-Help .\upload_github_release.ps1 -Full
```

---

## 🔄 Fluxo Completo

1. **Editar versão** → Altere `version.txt`
2. **Compilar** → Execute `build.bat`
3. **Upload automático** → Execute `upload_github_release.ps1`
4. **Testar** → Abra versão antiga e teste auto-update

---

## ❓ Problemas Comuns

### "Execution Policy" Error

Execute como Administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### GitHub CLI não instala via winget

Baixe manualmente:
```
https://cli.github.com/
```

### Erro de autenticação

Execute:
```powershell
gh auth login
```

---

## 📚 Documentação Completa

Para detalhes completos, leia: [GITHUB_RELEASE_AUTOMATION.md](GITHUB_RELEASE_AUTOMATION.md)

---

**Tempo estimado de setup:** 5 minutos  
**Tempo por release depois:** 30 segundos ⚡
