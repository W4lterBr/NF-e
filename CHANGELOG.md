# Changelog - BOT Busca NFE

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
