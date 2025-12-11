# Changelog - BOT Busca NFE

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
