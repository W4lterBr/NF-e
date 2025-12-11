# Changelog - BOT Busca NFE

## [1.0.20] - 2025-12-11

### Adicionado
- ⏰ **Status com última busca** exibido ao iniciar
- Mostra hora da última busca: "14:30"
- Mostra tempo decorrido: "há 15min", "há 2.5h", "há 1.2d"
- Atualização automática a cada segundo
- Fallback: "Pronto - Nenhuma busca realizada" se nunca buscou

### Melhorado
- Usuário vê imediatamente quando foi a última busca
- Mais contexto sobre o estado do sistema
- Interface mais informativa

🕒 Sempre sabe quando foi a última busca!

## [1.0.19] - 2025-12-11

### Alterado
- 📁 **Nova estrutura de pastas**: XMLs agora separados por tipo
- Estrutura: `xmls/<CNPJ>/<TIPO>/<YYYY-MM>/arquivo.xml`
- Pastas separadas: `NFE/` e `CTE/`
- Busca inteligente: tenta nova estrutura primeiro, depois antiga
- Compatibilidade total com XMLs já baixados (estrutura antiga)

### Melhorado
- Organização mais clara dos documentos
- Fácil localizar NFes vs CTes
- Manutenção facilitada

🗂️ Pasta organizada por tipo!

## [1.0.18] - 2025-12-11

### Adicionado
- 📊 **Resumo de busca em tempo real** na barra de status
- Contador de NFes e CTes encontrados durante busca
- Progress bar compacta mostrando busca em andamento
- Tempo decorrido da busca
- Último certificado processado (4 dígitos)
- Resumo final após conclusão: "✅ NFes: X | CTes: Y | Tempo: Zs"

### Melhorado
- Feedback visual instantâneo sem precisar abrir janela de debug
- Estatísticas sempre visíveis na interface
- Progress bar some automaticamente após conclusão

🚀 Busca totalmente monitorada!

## [1.0.17] - 2025-12-11

### Corrigido
- ☠️ **CRÍTICO**: Sistema não fecha mais após busca SEFAZ concluída
- Criada função `run_single_cycle()` para executar apenas uma iteração
- Removido loop infinito `while True` quando chamado pela interface
- Removido `time.sleep(INTERVALO)` que travava o sistema

### Melhorado
- Busca SEFAZ agora retorna controle para interface imediatamente
- Interface responsável por agendar próxima busca
- Mensagem clara: "Próxima busca será agendada pela interface..."

✅ Sistema permanece aberto após busca!

## [1.0.16] - 2025-12-11

### Corrigido
- 🚫 **BUG CRÍTICO**: Duplo clique não abre mais nova interface
- Forçado uso de pasta temp do Windows para PDFs temporários
- Validação rigorosa: só abre arquivos .pdf
- Tratamento de erro ao abrir PDF com mensagens claras

### Melhorado
- PDFs temporários salvos em %TEMP%\BOT_Busca_NFE_PDFs
- Mensagens de erro mais descritivas

👍 Duplo clique agora só abre PDF!

## [1.0.15] - 2025-12-11

### Corrigido
- 🔧 Janela "Buscar na SEFAZ" agora exibe logs em tempo real
- Logger do nfe_search agora conectado ao progress callback
- Handler de logging adicionado para capturar mensagens INFO/DEBUG

### Melhorado
- Feedback visual durante busca na SEFAZ
- Usuário vê progresso em tempo real

📊 Busca totalmente visível!

## [1.0.14] - 2025-12-11

### Corrigido
- 🛡️ Instalador agora executa programa com privilégios de administrador após instalação
- Flag `shellexec` adicionada ao Inno Setup para permitir UAC prompt
- Manifesto de aplicação configurado para solicitar elevação automaticamente

### Adicionado
- Manifest Windows (`app.manifest`) com `requireAdministrator`
- Compatibilidade Windows 7/8/8.1/10/11
- DPI Awareness ativado

🔐 Sem mais erro 740!

## [1.0.13] - 2025-12-11

### Corrigido
- ✨ Título da janela agora atualiza após aplicar atualizações
- Versão exibida corretamente sem precisar reiniciar
- Função _update_window_title() criada para atualizar título dinamicamente

### Melhorado
- Usuário vê imediatamente a nova versão após atualizar
- Melhor feedback visual após atualizações

🎯 Versão sempre atualizada no título!

## [1.0.12] - 2025-12-11

### Melhorado
- ✨ sandbox_task_runner.py agora é incluído nas atualizações automáticas
- Sistema pode receber correções sem recompilação
- Atualizações via GitHub baixam todos os arquivos necessários

### Corrigido
- Erro de PDF agora corrigível via atualização remota
- Não precisa mais reinstalar para receber correções

🎯 Sistema 100% atualizável remotamente!

## [1.0.11] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Erro "No such file or directory: _temp_runner.py" em executável compilado
- sandbox_worker agora busca sandbox_task_runner.py em múltiplas localizações
- Fallback usa pasta temporária do sistema (evita permissão negada)
- PDFs de CTe/NFe gerados corretamente via duplo clique

### Melhorado
- Busca inteligente de arquivos em 4 possíveis caminhos
- Usa tempfile.gettempdir() para evitar problemas de permissão
- Mais robusto em ambiente compilado PyInstaller

🎯 Duplo clique funciona em qualquer cenário agora!

## [1.0.10] - 2025-12-11

### Adicionado
- ✨ Versão agora é exibida no título da janela: "Busca de Notas Fiscais - v1.0.10"
- Leitura automática de version.txt ao iniciar aplicação

### Melhorado
- Usuário pode ver imediatamente qual versão está usando
- Facilita verificação de atualizações

🎯 Versão sempre visível na barra de título!

## [1.0.9] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Erro ao gerar PDF pelo duplo clique na tabela
- FileNotFoundError: '_temp_runner.py' não encontrado em executável compilado
- Criado sandbox_task_runner.py permanente no projeto
- PDFs agora são gerados corretamente via duplo clique

### Melhorado
- Sandbox worker mais robusto e confiável
- Melhor tratamento de erros com traceback completo
- Sistema de geração de PDF mais estável

🎯 Duplo clique em CTe/NFe funciona perfeitamente!

## [1.0.8] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Erro ao gerar PDF de CTe (usando Danfe em vez de Dacte)
- AttributeError 'NoneType' object has no attribute 'attrib' ao processar CTe
- Agora usa Dacte para CTe e Danfe para NFe corretamente

### Melhorado
- Detecção automática do tipo de documento (NFe vs CTe)
- Geração de DACTE (Documento Auxiliar de CTe) correta
- Mensagens de log mais específicas por tipo de documento

🎯 PDFs de CTe gerados corretamente agora!

## [1.0.7] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Interface travava durante validação XML
- Removido print() que imprimia XMLs gigantes (milhares de linhas)
- Substituídos prints de debug por logger.debug/warning
- Validação XSD agora não trava a interface

### Melhorado
- Performance muito melhor durante busca
- Mensagens de debug vão apenas para log (não para interface)
- Sistema mais responsivo

🎯 Busca executa sem travamentos agora!

## [1.0.6] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Sistema fechava após primeira busca (faltava loop infinito)
- Função main() agora executa em loop contínuo com sleep de 65 minutos
- Tratamento de erros durante ciclo com retry automático após 5 minutos
- Suporte a KeyboardInterrupt para parada controlada

### Melhorado
- Sistema mantém busca contínua automaticamente
- Logs mais informativos sobre intervalo de sleep
- Recuperação automática de erros durante execução

🎯 Sistema agora roda indefinidamente como esperado!

## [1.0.5] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: AttributeError ao redirecionar stdout em executável compilado
- `old_stdout` agora usa `sys.__stdout__` como fallback garantido
- ProgressCapture protegido contra stdout None
- Tratamento robusto de erros na captura de progresso

### Melhorado
- Sistema de captura de progresso funciona em qualquer ambiente
- Proteção contra falhas no redirecionamento de stdout
- Melhor compatibilidade com PyInstaller (console=False)

🎯 Busca executa sem erros de stdout agora!

## [1.0.4] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Erro de permissão ao criar backups durante atualização
- GitHubUpdater agora aceita backup_dir opcional
- Backups salvos em %APPDATA%\BOT Busca NFE\backups
- Arquivos atualizados em Program Files (só leitura dos .py)

### Melhorado
- Sistema de atualização 100% funcional sem admin
- Separação correta: arquivos em Program Files, backups em AppData

🎯 Atualizações funcionam perfeitamente agora!

## [1.0.3] - 2025-12-11

### Corrigido
- 🔒 **CRÍTICO**: Erro de permissão ao criar logs em Program Files
- setup_logger() agora usa get_data_dir() corretamente
- Logs criados em %APPDATA%\BOT Busca NFE\logs ao invés de Program Files
- Ordem correta de inicialização no nfe_search.py

### Garantido
- ✅ Sistema funciona sem permissão de administrador
- ✅ Logs sempre gravados com sucesso
- ✅ Nenhum erro de acesso negado

## [1.0.2] - 2025-12-11

### Corrigido
- ⚡ Sistema de atualização agora baixa TODOS os arquivos Python
- Lista completa de módulos incluindo interface_pyqt5.py
- Versão atualizada em installer.iss

### Melhorado
- Sistema de atualização mais robusto e completo
- Atualizações funcionam corretamente agora

## [1.0.1] - 2025-12-11

### Corrigido
- 🐛 **CRÍTICO**: Sistema não fecha mais durante execução da busca
- Tratamento completo de exceções em run_search()
- Proteção contra SystemExit no nfe_search.main()
- Thread SearchWorker com tratamento de erros fatais
- Mensagem de finalização da busca para interface detectar fim
- Correção na estrutura de instalação (evita duplicação de .py)

### Melhorado
- Sistema de build atualizado (BOT_Busca_NFE.spec, build.bat)
- Instalador Inno Setup simplificado
- Botão de atualizações movido para menu Tarefas (Ctrl+U)

### Documentação
- Adicionado ESTRUTURA_INSTALACAO.md com guia completo

## [1.0.0] - 2025-12-11

### Adicionado
- Sistema de atualização automática via GitHub
- Suporte completo a CT-e (Conhecimento de Transporte Eletrônico)
- Campo "informante" para filtro por certificado
- Modo onedir para facilitar atualizações

### Corrigido
- Bug de seleção de certificado na interface
- Criação automática de tabelas nsu_cte e erro_656
- Paths para funcionar em executável compilado (AppData)

### Melhorado
- Performance na listagem de notas
- Sistema de logging
- Documentação de build
