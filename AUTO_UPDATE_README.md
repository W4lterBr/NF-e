# 🔄 Sistema de Auto-Update TRUE

Sistema de atualização automática que **substitui o executável** sem necessidade de reinstalação manual.

## 🎯 Como Funciona

### **Modo Executável (.exe)**

Quando o usuário clica em "🔄 Atualizações":

1. **Verifica versão**: Compara `version.txt` local com GitHub
2. **Baixa novo .exe**: Download da última release do GitHub
3. **Inicia launcher**: Script Python separado (`updater_launcher.py`)
4. **Fecha aplicação**: O app principal fecha
5. **Substitui exe**: Launcher substitui o executável antigo pelo novo
6. **Reinicia app**: Launcher inicia o novo executável
7. **Auto-destrói**: Processo completo automaticamente

### **Modo Desenvolvimento (.py)**

- Atualiza arquivos `.py` individuais do GitHub
- Reinicia aplicação com novos arquivos
- Usado apenas para desenvolvimento

---

## 📋 Requisitos para Funcionar

### 1. **Release no GitHub deve conter:**
```
✅ Busca XML.exe       (executável principal)
✅ version.txt          (arquivo de versão)
✅ Busca_XML_Setup.exe  (opcional - instalador completo)
```

### 2. **Arquivos necessários no projeto:**
```
✅ updater_launcher.py  (incluído no .spec)
✅ modules/updater.py   (sistema de atualização)
✅ version.txt          (versão atual)
```

### 3. **Dependências Python:**
```
✅ psutil   (gerenciamento de processos)
✅ requests (download de arquivos)
```

---

## 🚀 Como Criar uma Release

### **Passo 1: Atualizar versão**
```bash
echo "1.0.93" > version.txt
```

### **Passo 2: Compilar executável**
```bash
.\build.bat
```

### **Passo 3: Criar Release no GitHub**
1. Vá em `https://github.com/W4lterBr/NF-e/releases/new`
2. Tag: `v1.0.93`
3. Título: `Versão 1.0.93 - Correção banco de dados`
4. Descrição: Liste as mudanças
5. **Upload dos arquivos**:
   - `dist\Busca XML\Busca XML.exe` → Renomear para `Busca XML.exe`
   - `version.txt`
   - `Output\Busca_XML_Setup.exe` (opcional)
6. Publicar release

### **Passo 4: Testar atualização**
- Abra versão antiga instalada
- Clique em "🔄 Atualizações"
- Sistema detecta nova versão
- Confirma atualização
- Aplicação fecha e atualiza automaticamente
- Reabre com nova versão

---

## 💻 Fluxo Técnico Detalhado

### **Arquivo: `modules/updater.py`**

```python
# Método principal para executáveis
def update_executable(self, progress_callback=None):
    1. Verifica versão remota no GitHub
    2. Baixa executável da release
    3. Localiza updater_launcher.py
    4. Inicia launcher em background
    5. Retorna para fechar o app
```

### **Arquivo: `updater_launcher.py`**

```python
def main():
    1. Recebe caminhos: novo_exe, exe_destino
    2. Aguarda processo principal fechar (psutil)
    3. Cria backup do exe antigo (.exe.bak)
    4. Move novo exe para o lugar do antigo
    5. Inicia novo executável
    6. Finaliza (auto-destrói)
```

### **Arquivo: `Busca NF-e.py`**

```python
def check_updates(self):
    if getattr(sys, 'frozen', False):
        # MODO EXECUTÁVEL
        result = updater.update_executable(...)
        if result['restart_required']:
            QApplication.quit()  # Fecha para launcher substituir
    else:
        # MODO DESENVOLVIMENTO
        result = updater.apply_update(...)  # Atualiza .py
```

---

## 🛡️ Segurança e Backup

### **Backups Automáticos**
- Executável antigo: `Busca XML.exe.bak`
- Localização: Mesma pasta do executável
- Criado antes de cada atualização

### **Restauração em Caso de Erro**
Se algo der errado:
1. Launcher detecta falha
2. Restaura automaticamente o `.exe.bak`
3. Exibe erro ao usuário

### **Verificação de Integridade**
- Download via HTTPS do GitHub
- Verificação de arquivo antes de substituir
- Aguarda processo fechar antes de substituir

---

## 🔧 Troubleshooting

### **Erro: "updater_launcher.py não encontrado"**
**Solução**: Recompilar com `.spec` atualizado
```bash
pyinstaller BOT_Busca_NFE.spec
```

### **Erro: "Executável não encontrado na release"**
**Solução**: Verificar que release contém arquivo exatamente como:
- ✅ `Busca XML.exe`
- ❌ `Busca_XML.exe`
- ❌ `busca xml.exe`

### **Atualização não inicia automaticamente**
**Causa**: Processo não fechou corretamente
**Solução**: Launcher aguarda até 30 segundos, depois força

### **Erro de permissão ao substituir exe**
**Causa**: Antivírus ou permissões
**Solução**: 
1. Adicionar exceção no antivírus
2. Executar como administrador

---

## 📊 Comparação: Antes vs Depois

### **ANTES (Modo Manual)**
```
1. Usuário clica "Atualizar"
2. Sistema baixa instalador
3. Usuário executa instalador manualmente
4. Instalador sobrescreve arquivos
5. Usuário reinicia aplicação
```
❌ Requer intervenção manual  
❌ Processo em múltiplas etapas

### **DEPOIS (Auto-Update TRUE)**
```
1. Usuário clica "Atualizar"
2. Sistema baixa + substitui + reinicia
```
✅ Totalmente automático  
✅ Sem intervenção do usuário  
✅ Uma única etapa

---

## 🎓 Como Usar em Outros Projetos

### **1. Copiar arquivos**
```
updater_launcher.py     → Raiz do projeto
modules/updater.py      → Manter update_executable()
version.txt             → Raiz do projeto
```

### **2. Atualizar .spec**
```python
added_files = [
    ('updater_launcher.py', '.'),
    ('version.txt', '.'),
]
```

### **3. Modificar interface**
```python
def check_updates(self):
    if getattr(sys, 'frozen', False):
        result = updater.update_executable(...)
        if result['restart_required']:
            app.quit()
```

### **4. Requirements**
```
psutil>=5.9.0
requests>=2.31.0
```

---

## 📝 Changelog do Sistema

### **Versão 1.0.92** (02/02/2026)
- ✅ Implementado auto-update TRUE
- ✅ Criado updater_launcher.py
- ✅ Adicionado update_executable() em updater.py
- ✅ Modificado check_updates() em interface
- ✅ Atualizado .spec para incluir launcher
- ✅ Adicionado psutil aos requirements

---

## 🔗 Links Úteis

- **Repositório**: https://github.com/W4lterBr/NF-e
- **Releases**: https://github.com/W4lterBr/NF-e/releases
- **Documentação PyInstaller**: https://pyinstaller.org

---

## ✅ Checklist para Próxima Atualização

Antes de criar nova release:

- [ ] Atualizar `version.txt`
- [ ] Compilar com `build.bat`
- [ ] Testar executável gerado
- [ ] Criar release no GitHub
- [ ] Upload de `Busca XML.exe` (EXATAMENTE esse nome)
- [ ] Upload de `version.txt`
- [ ] Testar atualização em versão antiga

---

**Desenvolvido por**: DWM System Developer  
**Data**: 02/02/2026  
**Versão do Auto-Update**: 1.0
