# 🚀 Menu de Inicialização Implementado

## 📍 Localização

O menu de inicialização está em:

```
Menu Principal → Configurações → 🚀 Inicialização
```

## 🎯 Estrutura do Menu

```
╔════════════════════════════════════════════════════════════╗
║ 📋 Configurações                                           ║
╠════════════════════════════════════════════════════════════╣
║ Atualizar                                        F5        ║
║ 🔄 Sincronizar XMLs                         Ctrl+Shift+S   ║
║ 📥 Baixar XMLs Faltantes                    Ctrl+Shift+D   ║
║ ─────────────────────────────────────────────────────────  ║
║ Buscar na SEFAZ                                 Ctrl+B     ║
║ Busca Completa                              Ctrl+Shift+B   ║
║ ─────────────────────────────────────────────────────────  ║
║ Busca por chave                                 Ctrl+K     ║
║ 📤 Exportar                                     Ctrl+E     ║
║ Certificados…                               Ctrl+Shift+C   ║
║ 📁 Importar XMLs                                Ctrl+I     ║
║ ─────────────────────────────────────────────────────────  ║
║ ⚙️ Gerenciador de Trabalhos                Ctrl+Shift+G   ║
║ ─────────────────────────────────────────────────────────  ║
║ 💾 Armazenamento…                           Ctrl+Shift+A   ║
║ ─────────────────────────────────────────────────────────  ║
║ ⏱️ Intervalo de Busca Automática          ▶               ║
║    ├─ 1 hora                                               ║
║    ├─ 2 horas                                              ║
║    ├─ 3 horas                                              ║
║    ├─ 4 horas                                              ║
║    ├─ 6 horas                                              ║
║    ├─ 8 horas                                              ║
║    ├─ 12 horas                                             ║
║    ├─ 16 horas                                             ║
║    ├─ 20 horas                                             ║
║    └─ 23 horas                                             ║
║ ─────────────────────────────────────────────────────────  ║
║ 🚀 Inicialização                           ▶               ║  ◄── NOVO!
║    ├─ ☑️ Iniciar automaticamente com o Windows            ║
║    ├─────────────────────────────────────────             ║
║    ├─ ⏱️ Gerenciador de Tarefas Agendadas                 ║
║    ├─────────────────────────────────────────             ║
║    └─ ℹ️ Busca automática após 10 minutos (modo startup)  ║
║ ─────────────────────────────────────────────────────────  ║
║ 🔄 Atualizações                                 Ctrl+U     ║
║ ─────────────────────────────────────────────────────────  ║
║ Limpar                                      Ctrl+Shift+L   ║
║ ─────────────────────────────────────────────────────────  ║
║ Abrir XMLs                                  Ctrl+Shift+X   ║
║ Abrir logs                                      Ctrl+L     ║
║ ─────────────────────────────────────────────────────────  ║
║ Usar PDF simples (modo seguro)                            ║
╚════════════════════════════════════════════════════════════╝
```

## ✨ Funcionalidades do Submenu

### 1. ☑️ Iniciar automaticamente com o Windows

- **Tipo**: Checkbox (marcável/desmarcável)
- **Função**: Habilita/desabilita inicialização automática
- **Status**: Mostra estado atual (marcado = ativo)
- **Registro**: Cria entrada em `HKCU\...\Run`

**Quando ativado:**
- ✅ Aplicativo inicia com Windows
- ✅ Fica na bandeja do sistema
- ✅ Agenda busca automática para 10 minutos
- ✅ Aparece em Configurações > Aplicativos > Inicialização

**Quando desativado:**
- ❌ Não inicia automaticamente
- ❌ Remove entrada do registro

### 2. ⏱️ Gerenciador de Tarefas Agendadas

- **Tipo**: Ação (clique único)
- **Função**: Abre janela do gerenciador
- **Atalho**: Também disponível no menu da bandeja

**O que mostra:**
- 📋 Lista de tarefas agendadas
- ⏱️ Countdown em tempo real
- ▶️ Status (Agendada/Em execução/Cancelada)
- ❌ Botão para cancelar tarefas

### 3. ℹ️ Busca automática após 10 minutos

- **Tipo**: Informativo (não clicável)
- **Função**: Informa sobre comportamento do modo startup
- **Detalhes**: 
  - Busca executada automaticamente
  - Apenas quando inicia via `--startup`
  - Timer de 600 segundos (10 minutos)

## 🔄 Sincronização

O menu está sincronizado com:

1. **Menu da Bandeja (System Tray)**
   - Mesma funcionalidade
   - Estado compartilhado
   - Atualização automática

2. **Registro do Windows**
   - Leitura do estado atual
   - Escrita ao alternar
   - Validação automática

3. **Task Scheduler**
   - Gerenciador compartilhado
   - Tarefas visíveis em ambos

## 🎨 Comportamento Visual

### Estado Marcado (✓)
```
☑️ Iniciar automaticamente com o Windows
```
- Checkbox marcado
- Indica que está ativo
- Verde/destaque (tema padrão)

### Estado Desmarcado
```
☐ Iniciar automaticamente com o Windows
```
- Checkbox vazio
- Indica que está desabilitado
- Cinza/normal

## 💬 Mensagens ao Usuário

### Ao Ativar:
```
┌─────────────────────────────────────────────┐
│ Inicialização Automática Ativada           │
├─────────────────────────────────────────────┤
│ ✓ O aplicativo agora iniciará              │
│   automaticamente com o Windows.            │
│                                             │
│ • Aparecerá apenas na bandeja do sistema   │
│ • Busca automática será executada após     │
│   10 minutos                                │
│ • Você pode desabilitar a qualquer momento │
│                                             │
│ Verifique em:                               │
│ Configurações do Windows >                  │
│ Aplicativos > Inicialização                 │
│                                             │
│                 [ OK ]                      │
└─────────────────────────────────────────────┘
```

### Ao Desativar:
```
Status Bar: "✓ Inicialização automática desabilitada"
(Mensagem rápida, 3 segundos)
```

### Em Caso de Erro:
```
┌─────────────────────────────────────────────┐
│ Erro                                        │
├─────────────────────────────────────────────┤
│ Não foi possível alterar a configuração    │
│ de inicialização automática.                │
│                                             │
│ Verifique se você tem permissões           │
│ administrativas.                            │
│                                             │
│                 [ OK ]                      │
└─────────────────────────────────────────────┘
```

## 🔧 Código de Referência

### Criação do Menu:
```python
# Submenu: Inicialização
inicializacao_submenu = tarefas.addMenu("🚀 Inicialização")

# Ação: Iniciar com Windows (checkbox)
self._act_iniciar_windows = QAction("Iniciar automaticamente com o Windows", self)
self._act_iniciar_windows.setCheckable(True)
self._act_iniciar_windows.setChecked(self.startup_manager.is_startup_enabled())
self._act_iniciar_windows.triggered.connect(self._toggle_startup_menu)
inicializacao_submenu.addAction(self._act_iniciar_windows)
```

### Toggle da Funcionalidade:
```python
def _toggle_startup_menu(self):
    """Habilita/desabilita inicialização automática"""
    success = self.startup_manager.toggle_startup()
    
    # Atualiza checkbox
    self._act_iniciar_windows.setChecked(
        self.startup_manager.is_startup_enabled()
    )
    
    # Sincroniza com menu tray
    self._update_startup_action_text()
    
    # Mostra mensagem ao usuário
    if success:
        self.set_status(f"✓ Inicialização automática ativada", 3000)
```

## 📊 Fluxo de Uso

```
Usuário clica no menu
        ↓
Configurações → 🚀 Inicialização
        ↓
Marca/Desmarca "Iniciar automaticamente..."
        ↓
Sistema chama _toggle_startup_menu()
        ↓
StartupManager.toggle_startup()
        ↓
Altera registro do Windows
        ↓
Atualiza interface (checkbox + tray)
        ↓
Mostra mensagem de confirmação
        ↓
Salva estado
```

## 🧪 Como Testar

1. **Abrir menu:**
   ```
   Configurações → 🚀 Inicialização
   ```

2. **Marcar checkbox:**
   - Deve abrir mensagem de confirmação
   - Checkbox deve ficar marcado
   - Menu tray deve sincronizar

3. **Verificar registro:**
   ```powershell
   reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "BOT Busca NFE"
   ```
   Deve retornar:
   ```
   BOT Busca NFE    REG_SZ    "C:\...\Busca XML.exe" --startup
   ```

4. **Desmarcar checkbox:**
   - Checkbox deve desmarcar
   - Status bar deve mostrar mensagem
   - Registro deve ser removido

5. **Verificar Windows:**
   - Abrir: Configurações > Aplicativos > Inicialização
   - "BOT Busca NFE" deve aparecer na lista
   - Estado deve corresponder ao checkbox

## ✅ Validação

- ✅ Menu criado no local correto
- ✅ Checkbox funcional
- ✅ Sincronização com tray menu
- ✅ Mensagens informativas
- ✅ Gerenciador de tarefas acessível
- ✅ Item informativo sobre busca automática
- ✅ Ícones apropriados
- ✅ Estado persistido no registro

---

**Autor:** Sistema Implementado
**Data:** 11/01/2026
**Versão:** 1.1.0
