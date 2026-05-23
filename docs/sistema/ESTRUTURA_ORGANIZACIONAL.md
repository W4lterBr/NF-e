# 🗂️ Nova Estrutura Organizacional - BOT Busca NFE

**Data:** 29/01/2026  
**Status:** ✅ Reorganizado e Otimizado

---

## 📋 Visão Geral

O projeto foi reorganizado para melhor manutenção e clareza:

### ✨ Mudanças Principais

1. **📚 Documentação** → Movida para `docs/` com subpastas temáticas
2. **🧪 Testes** → Consolidados em `tests/` 
3. **📄 Raiz** → Apenas arquivos essenciais

---

## 📂 Estrutura Completa

```
BOT - Busca NFE/
│
├── 📄 Busca NF-e.py                    # 🚀 Aplicação principal (PyQt5)
├── 📄 nfe_search.py                    # ⚙️ Motor de busca SEFAZ
├── 📄 nfse_search.py                   # 📑 Busca NFS-e standalone
├── 📄 interface_pyqt5.py               # 🖥️ Interface gráfica (legado)
├── 📄 DownloadAllXmls.py               # 📥 Download em lote
├── 📄 nuvem_fiscal_api.py              # ☁️ API Nuvem Fiscal
│
├── 📄 requirements.txt                 # 📦 Dependências
├── 📄 version.txt                      # 🔢 Versão atual
├── 📄 CHANGELOG.md                     # 📝 Histórico de mudanças
├── 📄 README.md                        # 📖 Este documento
│
├── 📄 BOT_Busca_NFE.spec              # 📦 Config PyInstaller
├── 📄 installer.iss                    # 💿 Config Inno Setup
├── 📄 build.bat                        # 🔨 Script de build
├── 📄 deploy.bat                       # 🚀 Script de deploy
│
├── 📄 api_credentials.csv              # 🔑 Credenciais (gitignored)
├── 📄 app.manifest                     # ⚙️ Manifest Windows
│
├── 📁 modules/                         # 🧩 MÓDULOS DO SISTEMA
│   ├── database.py                    # 💾 Gerenciamento de banco
│   ├── cte_service.py                 # 🚛 Serviço CT-e
│   ├── nfse_service.py                # 📄 Serviço NFS-e (API REST)
│   ├── updater.py                     # 🔄 Sistema de atualização
│   ├── pdf_simple.py                  # 📄 Geração de PDF
│   ├── theme_manager.py               # 🎨 Gerenciador de temas
│   └── ...
│
├── 📁 docs/                            # 📚 DOCUMENTAÇÃO COMPLETA
│   ├── README.md                      # Índice da documentação
│   │
│   ├── 📁 instalacao/                 # 🔧 Instalação e Setup
│   │   ├── INSTALACAO.md
│   │   ├── ESTRUTURA_INSTALACAO.md
│   │   ├── BUILD_README.md
│   │   ├── GERAR_EXE.md
│   │   ├── CHECKLIST_MIGRACAO.md
│   │   ├── UPDATE_GUIDE.md
│   │   └── VERIFICACAO_INSTALACAO.md
│   │
│   ├── 📁 certificados/               # 🔐 Certificados Digitais
│   │   ├── CERTIFICADOS_README.md
│   │   ├── CERTIFICADOS_CORREÇÕES.md
│   │   └── CERTIFICADOS_TROUBLESHOOTING.md
│   │
│   ├── 📁 nfse/                       # 📄 NFS-e (Notas de Serviço)
│   │   ├── NFSE_DOCUMENTACAO_COMPLETA.md
│   │   ├── NFSE_BUSCA_README.md
│   │   ├── NFSE_INTERFACE_VISUAL.md
│   │   └── NFSE_NOTAS_DETALHADAS.md
│   │
│   ├── 📁 sistema/                    # ⚙️ Arquitetura e Técnicas
│   │   ├── DOCUMENTACAO_SISTEMA.md
│   │   ├── DOCUMENTACAO_NSU_ZERO.md
│   │   ├── HISTORICO_NSU_COMPLETO.md
│   │   ├── MELHORIAS_IMPLEMENTADAS.md
│   │   ├── ATUALIZACAO.md
│   │   ├── CONSULTA_POR_CHAVE_vs_NSU.md
│   │   ├── CRIPTOGRAFIA.md
│   │   ├── DISTRIBUICAO.md
│   │   ├── MANIFESTACAO_AUTOMATICA.md
│   │   ├── PORTABILIDADE.md
│   │   ├── SEGURANCA.md
│   │   ├── CACHE_PDF_IMPLEMENTACAO.md
│   │   ├── FLUXO_SALVAMENTO_XMLS.md
│   │   ├── IMPLEMENTACAO_VISUALIZACAO_RESUMO.md
│   │   ├── INICIALIZACAO_AUTOMATICA.md
│   │   ├── MENU_INICIALIZACAO.md
│   │   ├── PADRAO_ARQUIVAMENTO.md
│   │   ├── PROGRESSO_MANIFESTACAO.md
│   │   ├── REFATORACAO_NFE_2026-01-06.md
│   │   ├── BRASILNFE_INTEGRACAO.md
│   │   ├── NOTAS_TECNICAS_SEFAZ.md
│   │   ├── EXPLICACAO_MAXNSU_ZERO.md
│   │   ├── GUIA_TESTE_NSU.md
│   │   ├── TEMAS_README.md
│   │   ├── TEMAS_GUIA_RAPIDO.md
│   │   ├── COMO_TESTAR_EXPORT.md
│   │   └── LISTA_ARQUIVOS.md
│   │
│   ├── 📁 troubleshooting/            # 🔍 Solução de Problemas
│   │   ├── DIAGNOSTICO_ERRO_656.md
│   │   ├── CORRECAO_EVENTOS_ERROS.md
│   │   ├── ANALISE_LOGS_2026-01-12.md
│   │   ├── BUG_NSU_MAXNSU_PERDENDO_DOCUMENTOS.md
│   │   ├── DEBUG_ANALISE_SEFAZ.md
│   │   ├── EVENTOS_PDF_CORREÇÃO.md
│   │   ├── EVENTOS_TROUBLESHOOTING.md
│   │   └── RELATORIO_NFE_AUSENTES.md
│   │
│   └── 📁 outros/
│       ├── SUPORTE_CTE_NFSE.md
│       └── README_DOCUMENTACOES.md
│
├── 📁 tests/                           # 🧪 TESTES E SCRIPTS
│   ├── README.md                      # Guia de testes
│   │
│   ├── 🔬 Testes Unitários
│   │   ├── test_nfse_direto.py
│   │   ├── test_adn_api.py
│   │   ├── test_adn_endpoints.py
│   │   ├── test_busca_logs.py
│   │   ├── test_crypto.py
│   │   ├── test_cte.py
│   │   ├── test_input.txt
│   │   ├── test_numeric_sort.py
│   │   ├── test_table_sorting.py
│   │   ├── teste_nuvem_fiscal_integracao.py
│   │   └── run_test.py
│   │
│   ├── 🔍 Verificações
│   │   ├── check_db.py
│   │   ├── check_cte_db.py
│   │   ├── check_resumo.py
│   │   ├── check_cert.py
│   │   ├── verificar_informante.py
│   │   ├── verificar_instalacao.py
│   │   ├── verificar_notas_emitidas.py
│   │   └── verificar_notas_incompletas.py
│   │
│   ├── 🐛 Debug
│   │   ├── debug_db.py
│   │   ├── debug_filtro.py
│   │   ├── _analyze_db.py
│   │   ├── _check_db.py
│   │   └── _check_structure.py
│   │
│   ├── 🔧 Manutenção
│   │   ├── limpar_protocolos.py
│   │   ├── remover_resumos_vazios.py
│   │   ├── processar_eventos.py
│   │   ├── corrigir_informante.py
│   │   └── fix_informante.py
│   │
│   ├── 🔄 Migração
│   │   ├── migrate_encrypt_passwords.py
│   │   ├── migrate_to_portable.py
│   │   └── run_migration.bat
│   │
│   ├── 📝 Setup e Criação
│   │   ├── setup_test_db.py
│   │   ├── criar_nota_teste_resumo.py
│   │   └── listar_resumos.py
│   │
│   └── 📖 Exemplos
│       ├── exemplo_manifestacao.py
│       ├── fetch_swagger_endpoints.py
│       └── testar_status.py
│
├── 📁 config/                          # ⚙️ Configurações
├── 📁 logs/                            # 📊 Logs do sistema
├── 📁 Arquivo_xsd/                     # 📋 Schemas XSD SEFAZ
├── 📁 Icone/                           # 🎨 Ícones da interface
│
├── 📁 xmls/                            # 💾 ARMAZENAMENTO (Backup)
│   └── [CNPJ]/
│       └── [ANO-MES]/
│           ├── NFe/
│           ├── CTe/
│           ├── NFS-e/
│           ├── Eventos/
│           └── Resumos/
│
├── 📁 xml_extraidos/                   # 📤 XMLs extraídos
├── 📁 xml_NFs/                         # 📄 XMLs de NF-e
├── 📁 xml_envio/                       # 📤 XMLs de envio
├── 📁 xml_resposta_sefaz/              # 📥 Respostas SEFAZ
├── 📁 xmls_chave/                      # 🔑 XMLs por chave
├── 📁 xmls_nfce/                       # 🧾 XMLs de NFC-e
│
├── 📁 Output/                          # 📄 PDFs gerados
├── 📁 build/                           # 🔨 Build artifacts
├── 📁 scripts/                         # 📜 Scripts auxiliares
│
└── 📁 __pycache__/                     # 🐍 Cache Python
```

---

## 🎯 Benefícios da Reorganização

### ✅ Para Desenvolvedores
- 📚 Documentação centralizada e organizada por tema
- 🧪 Testes isolados em pasta própria
- 🔍 Fácil navegação e localização de arquivos
- 📖 READMEs em cada pasta explicando conteúdo

### ✅ Para Usuários
- 📄 README principal limpo e objetivo
- 🔗 Links diretos para documentação relevante
- 📚 Guias organizados por categoria
- 🚀 Instalação mais clara

### ✅ Para Manutenção
- 🗂️ Estrutura escalável
- 🔄 Fácil adicionar nova documentação
- 🧹 Raiz do projeto limpa
- 📦 Separação clara de responsabilidades

---

## 🚀 Próximos Passos

1. ✅ Estrutura de pastas criada
2. ✅ Arquivos movidos para locais apropriados
3. ✅ READMEs criados em cada pasta
4. ✅ README principal atualizado
5. 🔄 Atualizar links em arquivos (se necessário)
6. 📝 Documentar novos recursos

---

## 📖 Como Navegar

### Para Instalar
1. Leia [`README.md`](../README.md) principal
2. Siga [`docs/instalacao/INSTALACAO.md`](./docs/instalacao/INSTALACAO.md)
3. Configure [`docs/certificados/CERTIFICADOS_README.md`](./docs/certificados/CERTIFICADOS_README.md)

### Para Desenvolver
1. Clone o repositório
2. Explore [`modules/`](./modules/) para módulos
3. Veja [`tests/`](./tests/) para exemplos de teste
4. Consulte [`docs/sistema/`](./docs/sistema/) para arquitetura

### Para Resolver Problemas
1. Verifique [`docs/troubleshooting/`](./docs/troubleshooting/)
2. Consulte logs em [`logs/`](./logs/)
3. Execute scripts de verificação em [`tests/`](./tests/)

---

**© 2025 DWM System Developer. Todos os direitos reservados.**
