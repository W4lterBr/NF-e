# 📂 Lista Completa de Arquivos do Sistema

## Arquivos Essenciais (OBRIGATÓRIOS)

### Scripts Principais
```
interface_pyqt5.py          # Interface gráfica principal (PyQt5)
nfe_search.py               # Motor de busca NF-e e CT-e
nfse_search.py              # Motor de busca NFS-e
nuvem_fiscal_api.py         # API Nuvem Fiscal (NFS-e)
```

### Módulos (pasta modules/)
```
modules/__init__.py                    # Inicializador do pacote
modules/database.py                    # Gerenciador banco de dados
modules/sandbox_worker.py              # Worker para tarefas isoladas
modules/sandbox_task_runner.py         # Runner de tarefas
modules/pdf_generator.py               # Gerador de PDF (principal)
modules/pdf_simple.py                  # Gerador de PDF (fallback simples)
modules/certificate_manager.py         # Gerenciador de certificados
modules/cte_service.py                 # Serviço CT-e
modules/updater.py                     # Sistema de atualização
modules/utils.py                       # Utilitários gerais
```

### Schemas XSD (pasta Arquivo_xsd/)
```
Arquivo_xsd/retDistDFeInt_v1.01.xsd   # Schema distribuição DFe
Arquivo_xsd/resNFe_v1.01.xsd          # Schema resumo NFe
Arquivo_xsd/resEvento_v1.01.xsd       # Schema resumo evento
Arquivo_xsd/procNFe_v4.00.xsd         # Schema NFe processada
Arquivo_xsd/nfe_v4.00.xsd             # Schema NFe
Arquivo_xsd/leiauteNFe_v4.00.xsd      # Leiaute NFe
Arquivo_xsd/tiposBasico_v4.00.xsd     # Tipos básicos
Arquivo_xsd/xmldsig-core-schema_v1.01.xsd  # Assinatura digital
... (todos os XSDs são necessários para validação)
```

### Ícones (pasta Icone/)
```
Icone/xml.png               # Ícone XML para interface
Icone/Logo.png              # Logo do sistema (opcional)
```

### Configuração
```
requirements.txt            # Dependências Python
api_credentials.csv         # Credenciais Nuvem Fiscal (criar manualmente)
.gitignore                  # Ignorar arquivos Git
```

---

## Arquivos Criados Automaticamente

### Bancos de Dados
```
notas.db                    # Banco principal (SQLite)
configuracoes.db            # Configurações (criado se necessário)
```

### Pastas de Dados
```
xmls/                       # XMLs baixados organizados por CNPJ/Data
xmls_chave/                 # XMLs consultados por chave
logs/                       # Logs do sistema
xml_envio/                  # XMLs de envio (eventos)
xml_resposta_sefaz/         # Respostas SEFAZ
```

---

## Arquivos Opcionais (Desenvolvimento/Teste)

### Scripts de Teste
```
teste_nuvem_fiscal_integracao.py    # Teste integração Nuvem Fiscal
exemplo_manifestacao.py             # Exemplo controle manifestações
test_cte.py                         # Teste CT-e
test_nfse_direto.py                 # Teste NFS-e
verificar_informante.py             # Debug informante
processar_eventos.py                # Processar eventos locais
```

### Documentação
```
INSTALACAO.md               # Guia de instalação (este arquivo)
MANIFESTACAO_AUTOMATICA.md  # Doc sistema manifestações
DOCUMENTACAO_NSU_ZERO.md    # Doc busca NSU zero
CERTIFICADOS_README.md      # Doc certificados
README.md                   # Readme principal
CHANGELOG.md                # Histórico de mudanças
```

### Build (Executável)
```
BOT_Busca_NFE.spec          # Configuração PyInstaller
build.bat                   # Script build Windows
installer.iss               # Inno Setup (instalador)
app.manifest                # Manifesto Windows
version.txt                 # Versão do build
```

---

## Estrutura de Pastas Após Instalação

```
C:\BOT-Busca-NFE\
│
├── 📄 interface_pyqt5.py           ← Arquivo principal
├── 📄 nfe_search.py
├── 📄 nfse_search.py
├── 📄 nuvem_fiscal_api.py
├── 📄 requirements.txt
├── 📄 api_credentials.csv          ← Criar manualmente se usar NFS-e
│
├── 📁 modules\                     ← OBRIGATÓRIO
│   ├── __init__.py
│   ├── database.py
│   ├── sandbox_worker.py
│   ├── sandbox_task_runner.py
│   ├── pdf_generator.py
│   ├── pdf_simple.py
│   ├── certificate_manager.py
│   ├── cte_service.py
│   ├── updater.py
│   └── utils.py
│
├── 📁 Arquivo_xsd\                 ← OBRIGATÓRIO (todos os .xsd)
│   ├── retDistDFeInt_v1.01.xsd
│   ├── resNFe_v1.01.xsd
│   ├── procNFe_v4.00.xsd
│   ├── nfe_v4.00.xsd
│   └── ... (56 arquivos XSD no total)
│
├── 📁 Icone\                       ← OBRIGATÓRIO
│   └── xml.png
│
├── 📁 .venv\                       ← Criado durante instalação
│   └── ... (ambiente virtual Python)
│
├── 📁 xmls\                        ← Criado automaticamente
│   └── <CNPJ>\
│       └── <ANO-MES>\
│           └── <CHAVE>.xml
│
├── 📁 logs\                        ← Criado automaticamente
│   └── busca_nfe_2025-12-18.log
│
└── 🗄️ notas.db                     ← Criado automaticamente
```

---

## Arquivos Mínimos para Executar

**Absolutamente essenciais:**

1. **Scripts Python:**
   - `interface_pyqt5.py`
   - `nfe_search.py`
   - `nfse_search.py` (se usar NFS-e)

2. **Pasta modules/ completa:**
   - Todos os arquivos `.py` dentro de `modules/`

3. **Pasta Arquivo_xsd/ completa:**
   - Todos os arquivos `.xsd` (56 no total)

4. **Pasta Icone/:**
   - `xml.png` (mínimo)

5. **requirements.txt:**
   - Para instalação de dependências

---

## Tamanho Estimado

| Item | Tamanho |
|------|---------|
| Scripts Python | ~500 KB |
| modules/ | ~200 KB |
| Arquivo_xsd/ | ~1.5 MB |
| Icone/ | ~50 KB |
| .venv/ (ambiente virtual) | ~400 MB |
| **Total (sem .venv)** | **~2 MB** |
| **Total (com .venv)** | **~402 MB** |

---

## Checklist de Instalação em Novo PC

- [ ] Python 3.10+ instalado
- [ ] Pasta `BOT-Busca-NFE` criada
- [ ] Arquivos copiados:
  - [ ] Scripts principais (.py)
  - [ ] Pasta `modules/` completa
  - [ ] Pasta `Arquivo_xsd/` completa
  - [ ] Pasta `Icone/` com xml.png
  - [ ] `requirements.txt`
- [ ] Ambiente virtual criado (`.venv`)
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Certificado digital configurado
- [ ] Primeira busca executada com sucesso

---

## Arquivos que NÃO devem ser copiados

❌ **Não copie** de um PC para outro:
- `.venv/` (recriar em cada PC)
- `__pycache__/` (cache Python)
- `.git/` (se usar Git, clonar repositório)
- Arquivos `.db` pessoais (a menos que queira migrar dados)

✅ **Pode copiar** (migração de dados):
- `notas.db` (contém histórico de notas)
- `xmls/` (XMLs baixados)
- `api_credentials.csv` (suas credenciais)

---

**Última atualização**: 18/12/2025
