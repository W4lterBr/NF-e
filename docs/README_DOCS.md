# 📚 Documentação do Sistema - Busca NF-e/CT-e/NFS-e

**Sistema:** BOT - Busca NFE  
**Versão:** 1.0.96  
**Última Atualização:** 02/02/2026  
**Desenvolvedor:** DWM System Developer

---

## 📑 Índice Geral

### 🚀 Começando
- [README.md](../README.md) - Visão geral do projeto
- [INSTALACAO.md](INSTALACAO.md) - Guia de instalação completo
- [UPDATE_GUIDE.md](UPDATE_GUIDE.md) - Como atualizar o sistema
- [GERAR_EXE.md](GERAR_EXE.md) - Compilar executável com PyInstaller

### 🏗️ Arquitetura
- [ESTRUTURA_INSTALACAO.md](ESTRUTURA_INSTALACAO.md) - Estrutura de pastas e arquivos
- [LISTA_ARQUIVOS.md](LISTA_ARQUIVOS.md) - Descrição de todos os arquivos do projeto
- [DOCUMENTACAO_SISTEMA.md](DOCUMENTACAO_SISTEMA.md) - Documentação técnica completa

### 🔧 Funcionalidades
- [DISTRIBUICAO.md](DISTRIBUICAO.md) - Sistema de distribuição DFe
- [MANIFESTACAO_AUTOMATICA.md](MANIFESTACAO_AUTOMATICA.md) - Manifestação de destinatário
- [CONSULTA_POR_CHAVE_vs_NSU.md](CONSULTA_POR_CHAVE_vs_NSU.md) - Diferenças entre métodos
- [ATUALIZACAO_TIPOS_DOCUMENTOS.md](ATUALIZACAO_TIPOS_DOCUMENTOS.md) - Suporte a múltiplos tipos

### 🔒 Segurança
- [CERTIFICADOS_README.md](CERTIFICADOS_README.md) - Gestão de certificados digitais
- [CERTIFICADOS_CORREÇÕES.md](CERTIFICADOS_CORREÇÕES.md) - Correções de certificados
- [CERTIFICADOS_TROUBLESHOOTING.md](CERTIFICADOS_TROUBLESHOOTING.md) - Solução de problemas
- [CRIPTOGRAFIA.md](CRIPTOGRAFIA.md) - Sistema de criptografia de senhas
- [SEGURANCA.md](SEGURANCA.md) - Políticas de segurança

### 📦 Build & Deploy
- [BUILD_README.md](BUILD_README.md) - Processo de build detalhado
- [PORTABILIDADE.md](PORTABILIDADE.md) - Portabilidade do sistema
- [CHECKLIST_MIGRACAO.md](CHECKLIST_MIGRACAO.md) - Checklist de migração

### 📊 Histórico
- [CHANGELOG.md](CHANGELOG.md) - Registro de todas as mudanças
- [MELHORIAS_IMPLEMENTADAS.md](MELHORIAS_IMPLEMENTADAS.md) - Melhorias recentes
- [ATUALIZACAO.md](ATUALIZACAO.md) - Notas de atualização

### 🐛 Correções (v1.0.96)
- [correções/BATCH_DOWNLOAD.md](correções/BATCH_DOWNLOAD.md) - Download em lote de XMLs
- [correções/NFSE_DUPLO_CLIQUE.md](correções/NFSE_DUPLO_CLIQUE.md) - Busca de XML/PDF NFS-e

### 🔍 Diagnósticos
- [DIAGNOSTICO_ERRO_656.md](DIAGNOSTICO_ERRO_656.md) - Erro 656 (certificado)
- [DOCUMENTACAO_NSU_ZERO.md](DOCUMENTACAO_NSU_ZERO.md) - Problema de NSU zerado

### 🧪 Testes
- [README_TEST.md](README_TEST.md) - Guia de testes do sistema

---

## 🆕 Novidades da v1.0.96 (02/02/2026)

### ✅ Correções Críticas

1. **Download em Lote de XMLs Completos** ([BATCH_DOWNLOAD.md](correções/BATCH_DOWNLOAD.md))
   - Problema: Apenas 1 nota processada ao selecionar múltiplas
   - Solução: Busca por chave na tabela + validação de campos vazios
   - Impacto: Funcionalidade crítica restaurada

2. **Busca de XML/PDF NFS-e** ([NFSE_DUPLO_CLIQUE.md](correções/NFSE_DUPLO_CLIQUE.md))
   - Problema: PDFs/XMLs de NFS-e não encontrados no duplo clique
   - Causa: Padrão de nomenclatura mudou (`NFSe_952.pdf` → `952-NOME.pdf`)
   - Solução: Busca com wildcard + fallback para compatibilidade
   - Impacto: NFS-e completamente funcional

### 🎯 Melhorias de Código

- Logs detalhados para debug de problemas
- Validação robusta de notas RESUMO (xml_status + campos vazios)
- Progress dialog com contadores de sucesso/erro
- Supressão inteligente de dialogs durante operações em lote
- Retrocompatibilidade mantida em todas as alterações

---

## 🏗️ Estrutura do Projeto

```
BOT - Busca NFE/
├── 📄 Busca NF-e.py          # Interface principal (PyQt5)
├── 📄 nfe_search.py           # Core: busca, parse, salvamento
├── 📄 nfse_search.py          # Busca específica de NFS-e
├── 📂 modules/                # Módulos auxiliares
│   ├── database.py            # Gestão de banco SQLite
│   ├── pdf_simple.py          # Geração de DANFE
│   ├── manifestacao_service.py # Manifestação do destinatário
│   ├── crypto_portable.py     # Criptografia de senhas
│   └── nfse_service.py        # Serviços NFS-e
├── 📂 docs/                   # 📚 TODA A DOCUMENTAÇÃO
│   ├── README_DOCS.md         # Este arquivo (índice)
│   ├── correções/             # Correções documentadas
│   │   ├── BATCH_DOWNLOAD.md
│   │   └── NFSE_DUPLO_CLIQUE.md
│   ├── INSTALACAO.md
│   ├── CHANGELOG.md
│   └── ... (todos os .md)
├── 📂 xmls/                   # XMLs baixados
├── 📂 logs/                   # Logs do sistema
├── 📂 Icone/                  # Ícones da interface
└── 📄 notas.db                # Banco de dados SQLite
```

---

## 🔗 Links Rápidos

### Para Desenvolvedores
- [Estrutura de Instalação](ESTRUTURA_INSTALACAO.md)
- [Lista de Arquivos](LISTA_ARQUIVOS.md)
- [Documentação do Sistema](DOCUMENTACAO_SISTEMA.md)
- [Build README](BUILD_README.md)

### Para Usuários
- [Instalação](INSTALACAO.md)
- [Guia de Atualização](UPDATE_GUIDE.md)
- [Certificados](CERTIFICADOS_README.md)
- [Solução de Problemas](CERTIFICADOS_TROUBLESHOOTING.md)

### Para Suporte
- [Diagnóstico Erro 656](DIAGNOSTICO_ERRO_656.md)
- [Correções v1.0.96](correções/)
- [Changelog](CHANGELOG.md)

---

## 📞 Suporte

**GitHub:** https://github.com/W4lterBr/NF-e  
**Desenvolvedor:** DWM System Developer

---

## 📄 Licença

Todos os direitos reservados © 2026 DWM System Developer
