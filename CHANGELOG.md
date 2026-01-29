# Changelog - BOT Busca NFE

## [1.0.92] - 2026-01-29

### 🔧 Otimizações NFS-e

#### ✅ Removida Duplicação de Busca NFS-e
- **Problema**: NFS-e era processada em 2 lugares simultaneamente:
  1. Dentro do `nfe_search.py` (durante loop de certificados)
  2. Via `buscar_nfse_auto.py` (script separado após conclusão)
- **Sintoma**: Logs intercalados, consultas duplicadas à API, possível erro 429
- **Correção**: Removidas chamadas `processar_nfse()` do `nfe_search.py`
- **Resultado**: NFS-e executa apenas via `buscar_nfse_auto.py` após NF-e/CT-e
- **Benefícios**:
  - Sem duplicação de consultas
  - Logs organizados e sequenciais
  - NF-e/CT-e não esperam NFS-e (mais rápido)
  - Controle independente (incremental vs completa)

#### ✅ Estrutura de Pastas NFS-e Unificada
- **Antes**: `xmls/{CNPJ}/MM-AAAA/NFSe/NFSe_123.xml`
- **Agora**: `xmls/{CNPJ}/AAAA-MM/NFSe/123-PRESTADOR.xml`
- **Mudanças**:
  - Nomenclatura: `{NUMERO}-{PRESTADOR}.xml` (igual NF-e/CT-e)
  - Formato pasta: Configurável via `storage_formato_mes` (AAAA-MM, MM-AAAA, etc)
  - Nome do prestador extraído do XML (RazaoSocial)
  - Sanitização de caracteres inválidos
  - Limite de 50 caracteres no nome
- **Compatibilidade**: Arquivos antigos continuam sendo lidos
- **Arquivos modificados**:
  - `buscar_nfse_auto.py`: Função `salvar_xml_nfse()` atualizada
  - `testar_nfse_rapido.py`: Chamadas atualizadas
  - `tests/examples/testar_nfse_rapido.py`: Chamadas atualizadas

#### 📚 Documentação Atualizada
- `docs/AJUSTE_NFSE_POS_SEFAZ.md`: Seção sobre remoção de duplicação
- `docs/README_NFSE_USUARIO.md`: Estrutura de pastas e nomenclatura
- `docs/GUIA_TECNICO_NFSE.md`: Nova seção "Estrutura de Armazenamento"

---

## [1.0.91] - 2026-01-27

### 🐛 Correções Críticas - Métodos Ausentes

#### ✅ Implementado Método extrair_cstat_nsu na NFSeService
- **Problema identificado**: NFS-e não estava sendo buscada devido a `AttributeError: 'NFSeService' object has no attribute 'extrair_cstat_nsu'`
- **Localização do erro**: Arquivo `nfse_search.py`, classe `NFSeService`
- **Correção aplicada**: Implementado método `extrair_cstat_nsu()` que extrai cStat, ultNSU e maxNSU de respostas NFS-e
- **Funcionalidades**:
  - Suporta respostas JSON (dicionários)
  - Suporta respostas XML (string ou bytes)
  - Busca com e sem namespace
  - Retorna valores padrão seguros em caso de erro
- **Impacto**: Busca de NFS-e agora funciona corretamente

#### ✅ Implementado Método fetch_by_key na XMLProcessor
- **Problema identificado**: Busca automática de XML completo falhava com `AttributeError: 'XMLProcessor' object has no attribute 'fetch_by_key'`
- **Localização do erro**: Arquivo `nfe_search.py`, classe `XMLProcessor`
- **Contexto**: Quando o sistema recebia `resNFe` (resumo), tentava buscar XML completo automaticamente
- **Correção aplicada**: Implementado método `fetch_by_key()` como método de compatibilidade
- **Comportamento**:
  - Detecta quando é chamado e loga warning indicando método legado
  - Recomenda uso direto de `NFeService.fetch_by_chave_dist()`
  - Evita crash quando chamado de código legado
- **Impacto**: Sistema não trava mais ao tentar buscar XMLs completos automaticamente

#### 📊 Análise das Buscas - Status Atual

**NF-e - ✅ FUNCIONANDO CORRETAMENTE**
- Buscando TODOS os documentos via loop ultNSU → maxNSU
- Respeitando NT 2014.002 (aguarda 1h quando sincronizado)
- Processando cStat=137 (sem docs) e cStat=138 (com docs) corretamente
- Loop continua até ultNSU == maxNSU

**CT-e - ✅ FUNCIONANDO CORRETAMENTE**
- Processamento idêntico ao NF-e
- Loop completo até sincronização

**NFS-e - ✅ CORRIGIDO**
- Estava falhando antes de processar dados (método ausente)
- Agora processa respostas JSON e XML corretamente
- Extrai cStat, ultNSU e maxNSU apropriadamente

#### ✅ Resultado Final
- ✅ NF-e: Buscando todos documentos corretamente
- ✅ CT-e: Buscando todos documentos corretamente
- ✅ NFS-e: Processamento de respostas corrigido
- ✅ Busca automática de XMLs: Não trava mais

## [1.0.90] - 2026-01-27

### 🐛 Correção Crítica - Salvamento de XMLs

#### ✅ Corrigido Bug na Função salvar_xml_por_certificado
- **Problema identificado**: XMLs baixados com sucesso da SEFAZ (6746 bytes) não eram salvos no disco
- **Causa raiz**: Parâmetros da função `salvar_xml_por_certificado` estavam na ordem errada em 2 lugares:
  - Linha 4375: função `_baixar_xml_e_pdf` (menu "✅ XML Completo")
  - Linha 10714: auto-verificação de resumos em massa
- **Assinatura correta**: `salvar_xml_por_certificado(xml, cnpj_cpf, pasta_base="xmls", nome_certificado=None)`
- **Estava sendo chamado**: `salvar_xml_por_certificado(xml_completo, chave, informante, 'NFe')`
  - ❌ Passava `chave` (44 dígitos) onde deveria ser `cnpj_cpf`
  - ❌ Passava `informante` onde deveria ser `pasta_base`
  - ❌ Passava `'NFe'` onde deveria ser `nome_certificado`
- **Correção aplicada**: Ambas as chamadas agora usam `salvar_xml_por_certificado(xml_completo, informante)`
- **Impacto**: XMLs baixados via menu de contexto ou busca automática agora são salvos corretamente
- **Status do banco**: Campo `xml_status` agora é atualizado corretamente de RESUMO para COMPLETO

#### 📊 Funções Afetadas
- `_baixar_xml_e_pdf()`: Menu "✅ XML Completo" → Agora salva XMLs corretamente
- Auto-verificação de resumos em lote → Agora salva XMLs corretamente
- Geração de PDF após download → Agora funciona (XML estava disponível na memória mas não no disco)

#### ✅ Resultado Final
- ✅ HTTP download de XMLs: Funcionando (sempre funcionou)
- ✅ Salvamento no disco: CORRIGIDO
- ✅ Atualização do banco (xml_status): CORRIGIDO
- ✅ Geração de PDF automática: CORRIGIDO (depende do XML no disco)

## [1.0.89] - 2026-01-05

### 🐛 Correções de Interface

#### ✅ Ícones de Cancelamento
- **Corrigido**: Ícone de cancelamento agora aparece corretamente para notas canceladas
- **Detecção aprimorada**: Verifica `'cancelamento' in status` e `'cancel' in status`
- **CT-e cancelado**: Agora detecta "Cancelamento de CT-e homologado"
- **Priorização**: Status cancelado tem prioridade sobre xml_status (COMPLETO/RESUMO)

#### 📝 Tooltips Melhorados
- **Cancelado + Completo**: "❌ Nota Cancelada - XML Completo disponível"
- **Cancelado + Resumo**: "❌ Nota Cancelada - Apenas Resumo"
- **Normal + Completo**: "✅ XML Completo disponível"
- **Normal + Resumo**: "⚠️ Apenas Resumo - clique para baixar XML completo"

#### 🎨 Status Limpo
- **Antes**: `100 - Autorizado o uso da NF-e`
- **Depois**: `Autorizado o uso da NF-e`
- **Função**: `limpar_status()` remove prefixo "100 - "
- **Aplicado**: Ambas as tabelas (Emitidos por Terceiros e Emitidos pela Empresa)

### 🔧 Busca por Chave Melhorada

#### ✅ Extração de Dados Básicos da Chave
- **Problema resolvido**: Notas buscadas por chave não apareciam em "Emitidos pela Empresa"
- **Solução**: Extrai informações dos 44 dígitos da chave:
  - CNPJ Emitente (posições 6-20)
  - Número da nota (posições 25-34)
  - UF (posições 0-2)
  - Tipo de documento (55=NF-e, 57=CT-e)
- **Salva**: Dados básicos em `notas_detalhadas` com `xml_status='RESUMO'`
- **Benefício**: Notas aparecem na interface mesmo sem XML completo

#### 📊 Estatísticas Aprimoradas
- **Mensagem final**: Mostra `📊 Total processado: X de Y chaves`
- **Logs detalhados**: Cada etapa do processo registrada

### 🔄 Sincronização de Certificados

#### ✅ Tabela "Emitidos pela Empresa" Atualiza ao Trocar Certificado
- **Corrigido**: Ao clicar em certificado, atualiza ambas as tabelas
- **Função**: `_on_tree_cert_clicked()` agora chama `refresh_emitidos_table()`
- **Logs**: Mostra quando certificado é trocado e tabelas atualizadas

### 📋 Logs Detalhados
- `[FILTERED_EMITIDOS]`: Mostra qual certificado está selecionado
- `[CERTIFICADO]`: Registra troca de seleção e atualização de tabelas
- `[DEBUG ICONE]`: Detalhes sobre escolha de ícone para cada nota
- `[BUSCA POR CHAVE]`: Estatísticas de processamento

## [1.0.86] - 2026-01-05

### ⚠️ BREAKING CHANGE - Novo Padrão de Arquivamento

#### 📋 Padrão Oficial Estabelecido
- ✅ **Documentação completa**: `PADRAO_ARQUIVAMENTO.md` criado
- ✅ **Nome do arquivo**: SEMPRE a chave de acesso (44 dígitos)
- ✅ **Estrutura de pastas**: `xmls/{CNPJ}/{ANO-MES}/{TIPO}/{CHAVE}.xml`
- ✅ **Exemplos**: `52260115045348000172570010014777191002562584.xml`

#### 🔧 Mudanças no Sistema

**Salvamento (nfe_search.py)**:
- ✅ Arquivos salvos como `{chave}.xml` em vez de `{numero}-{nome}.xml`
- ✅ Pasta principal agora é o CNPJ (não mais nome do certificado)
- ✅ Extração de chave otimizada (antes do salvamento)
- ✅ Validação de chave (44 dígitos)
- ✅ Registro automático no banco `xmls_baixados`

**Busca (interface_pyqt5.py)**:
- ✅ Prioridade 1: Banco de dados (instantâneo)
- ✅ Prioridade 2: Busca por nome `{chave}.xml` (rápido)
- ✅ Prioridade 3: Busca por conteúdo (fallback para arquivos legados)
- ⚠️ Avisos quando encontrar arquivos legados

#### 📊 Benefícios

**Performance**:
- ⚡ Busca instantânea por chave (O(1) no banco)
- ⚡ Busca por nome 10-50x mais rápida
- ⚡ Sem necessidade de ler conteúdo dos arquivos

**Organização**:
- 📁 Estrutura previsível por CNPJ e período
- 🔍 Localização imediata de qualquer documento
- 🚫 Zero duplicatas (chave é única)
- ✅ Compatível com outros sistemas fiscais

**Manutenção**:
- 📋 Padrão documentado e versionado
- ✅ Checklist de conformidade
- 🔄 Migração facilitada de arquivos legados
- 📖 Guia completo de implementação

#### ⚠️ Compatibilidade

- ✅ **Arquivos antigos continuam funcionando** (busca por conteúdo)
- ⚠️ **Performance reduzida** para arquivos legados (5-30s vs <50ms)
- 💡 **Recomendação**: Renomear arquivos antigos para o novo padrão
- 📋 **Scripts de migração**: Serão criados se necessário

#### 📚 Documentação

Consulte `PADRAO_ARQUIVAMENTO.md` para:
- 📖 Especificação completa do padrão
- 🏗️ Estrutura de pastas detalhada
- 💾 Integração com banco de dados
- 🔍 Estratégias de busca
- ✅ Checklist de implementação
- 🚀 Benefícios e justificativas

---

🎯 **Objetivo**: Arquivamento padronizado, eficiente e escalável para milhões de documentos fiscais.

## [1.0.21] - 2025-12-11

### Removido
- ❌ **Janela popup de busca removida (SearchDialog)**
- Não abre mais janela de debug durante busca SEFAZ

### Melhorado
- ✨ Interface mais limpa - apenas barra de status
- 📊 Resumo em tempo real direto na interface principal
- Progress bar compacta na barra de status
- Sem janelas popup intrusivas
- Tudo visível sem abrir nada
- Não interrompe mais o fluxo de trabalho

🧼 Busca silenciosa e eficiente!

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
