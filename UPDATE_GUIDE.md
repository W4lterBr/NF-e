# Sistema de Atualização Automática - BOT Busca NFE

## 📦 Como funciona

O sistema de atualização baixa arquivos Python (.py) atualizados diretamente do GitHub e substitui os arquivos locais, sem precisar recompilar o executável.

## 🔄 Workflow de Desenvolvimento

### 1. Fazer alterações no código (VS Code)
```bash
# Edite os arquivos necessários:
# - nfe_search.py
# - modules/*.py
# - interface_pyqt5.py
```

### 2. Atualizar versão e changelog
```bash
# Edite version.txt
1.0.1

# Edite CHANGELOG.md
## [1.0.1] - 2025-12-11
### Corrigido
- Bug na busca de XMLs
```

### 3. Commitar e enviar para GitHub
```bash
git add .
git commit -m "fix: corrige bug na busca de XMLs"
git push origin main
```

### 4. Usuários aplicam atualização
- Abrem o aplicativo instalado
- Clicam em "🔄 Atualizações"
- Sistema verifica GitHub
- Baixa e substitui arquivos automaticamente
- Reinicia aplicativo (opcional)

## 📁 Arquivos que são atualizados

- `nfe_search.py` - Script principal de busca
- `modules/database.py` - Gerenciamento de banco de dados
- `modules/cte_service.py` - Serviço de CT-e
- `modules/updater.py` - Próprio sistema de atualização
- `modules/sandbox_worker.py` - Worker em sandbox
- `version.txt` - Controle de versão
- `CHANGELOG.md` - Histórico de mudanças

## 🛠️ Comandos Git Úteis

### Primeira vez (configurar repositório)
```bash
cd "C:\Users\Nasci\OneDrive\Documents\Programas VS Code\BOT - Busca NFE"

# Inicializa Git
git init

# Adiciona repositório remoto
git remote add origin git@github.com:W4lterBr/NF-e.git

# Primeiro commit
git add .
git commit -m "chore: versão inicial com sistema de atualização"

# Envia para GitHub
git branch -M main
git push -u origin main
```

### Fluxo normal de atualização
```bash
# 1. Editar arquivos no VS Code
# 2. Atualizar version.txt e CHANGELOG.md
# 3. Enviar para GitHub:

git add .
git commit -m "feat: adiciona nova funcionalidade X"
git push
```

### Ver histórico
```bash
git log --oneline
```

### Desfazer mudanças não commitadas
```bash
git restore arquivo.py
```

## 🎯 Estratégia de Versionamento

Use **Semantic Versioning** (X.Y.Z):
- **X** (major): Mudanças que quebram compatibilidade
- **Y** (minor): Novas funcionalidades (compatível)
- **Z** (patch): Correções de bugs

Exemplos:
- `1.0.0` → `1.0.1`: Correção de bug
- `1.0.1` → `1.1.0`: Nova funcionalidade
- `1.1.0` → `2.0.0`: Mudança que quebra compatibilidade

## 🔐 Segurança

- ✅ Faz backup de arquivos antes de sobrescrever
- ✅ Verifica integridade antes de aplicar
- ✅ Permite reverter para versão anterior (backups em `backups/`)
- ✅ Apenas arquivos .py são atualizados (não afeta .exe principal)

## 🚨 Importante

### O que NÃO é atualizado automaticamente:
- `interface_pyqt5.py` - Requer recompilação
- Bibliotecas Python (PyQt5, zeep, etc.) - Requer recompilação
- Executável principal (.exe) - Requer recompilação
- Arquivos de configuração do usuário
- Banco de dados (notas.db)
- Certificados

### Quando recompilar:
- Mudanças em `interface_pyqt5.py`
- Atualização de dependências (requirements.txt)
- Mudanças visuais (ícones, layout)
- Nova versão do PyQt5 ou outras libs

## 📝 Exemplo Completo

```bash
# 1. Corrigir bug em nfe_search.py
# Editar: nfe_search.py (linha 500)

# 2. Atualizar versão
echo "1.0.1" > version.txt

# 3. Atualizar changelog
# Editar: CHANGELOG.md

# 4. Commit e push
git add nfe_search.py version.txt CHANGELOG.md
git commit -m "fix: corrige erro ao processar XML vazio"
git push

# 5. Usuários clicam em "🔄 Atualizações" no app
# Sistema baixa automaticamente e substitui nfe_search.py
```

## 🔍 Verificar status do Git

```bash
# Ver arquivos modificados
git status

# Ver diferenças
git diff nfe_search.py

# Ver última alteração em arquivo específico
git log -1 -p nfe_search.py
```

## 🌐 Repositório GitHub

**URL**: https://github.com/W4lterBr/NF-e
**Clone**: `git@github.com:W4lterBr/NF-e.git`

## 📞 Suporte

Desenvolvido por: **DWM System Developer**  
Site: https://dwmsystems.up.railway.app/
