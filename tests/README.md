# 🧪 Testes - BOT Busca NFE

Pasta contendo scripts de teste, verificação e utilitários de desenvolvimento.

---

## 📂 Estrutura Organizada

```
tests/
├── README.md                    # Este arquivo
│
├── 📁 unit/                     # 🧪 Testes Unitários
│   ├── test_*.py               # Testes automatizados
│   ├── *_test.py               # Testes específicos
│   └── README.md
│
├── 📁 integration/              # 🔗 Testes de Integração
│   ├── teste_*.py              # Testes com APIs reais
│   └── README.md
│
├── 📁 debug/                    # 🐛 Scripts de Debug
│   ├── debug_*.py              # Debug de componentes
│   └── README.md
│
├── 📁 analysis/                 # 📊 Scripts de Análise
│   ├── _*.py                   # Análise profunda
│   └── README.md
│
├── 📁 verification/             # ✅ Scripts de Verificação
│   ├── check_*.py              # Verificações não-destrutivas
│   ├── verificar_*.py          # Validações do sistema
│   └── README.md
│
├── 📁 maintenance/              # 🔧 Scripts de Manutenção
│   ├── limpar_*.py             # Limpeza de dados
│   ├── remover_*.py            # Remoção de registros
│   ├── processar_*.py          # Processamento
│   ├── listar_*.py             # Listagem
│   └── README.md
│
├── 📁 migration/                # 🔄 Scripts de Migração
│   ├── migrate_*.py            # Migrações de dados
│   ├── fix_*.py                # Correções automáticas
│   ├── corrigir_*.py           # Correções específicas
│   └── README.md
│
└── 📁 examples/                 # 📖 Exemplos e Setup
    ├── exemplo_*.py            # Exemplos de uso
    ├── setup_*.py              # Scripts de configuração
    ├── criar_*.py              # Criação de dados teste
    ├── fetch_*.py              # Scripts de busca
    ├── testar_*.py             # Testes manuais
    └── README.md
```

---

## 🚀 Início Rápido

### Para Desenvolvedores

```bash
# 1. Ativar ambiente virtual
.venv\Scripts\Activate.ps1

# 2. Executar testes unitários
cd tests\unit
python run_test.py

# 3. Verificar sistema
cd ..\verification
python verificar_instalacao.py
```

### Para Usuários Finais

```bash
# Verificar instalação
python tests\verification\verificar_instalacao.py

# Verificar banco de dados
python tests\verification\check_db.py
```

---

## 📋 Guias por Categoria

### 🧪 [Testes Unitários](./unit/README.md)
Testes automatizados de componentes individuais:
- API NFS-e, ADN, Nuvem Fiscal
- Criptografia, logs, ordenação
- Motor de busca

**Uso:**
```bash
cd unit
python test_nfse_direto.py
python test_crypto.py
```

### 🔗 [Testes de Integração](./integration/README.md)
Testes com sistemas externos:
- Integração com APIs reais
- Validação de certificados mTLS
- Comunicação SOAP/REST

**Uso:**
```bash
cd integration
python teste_nuvem_fiscal_integracao.py
```

### 🐛 [Debug](./debug/README.md)
Scripts de debug e diagnóstico:
- Debug de banco de dados
- Debug de filtros
- Inspeção detalhada

**Uso:**
```bash
cd debug
python debug_db.py
```

### 📊 [Análise](./analysis/README.md)
Análise profunda do sistema:
- Análise completa do banco
- Verificação de integridade
- Análise de estrutura

**Uso:**
```bash
cd analysis
python _analyze_db.py
```

### ✅ [Verificação](./verification/README.md)
Verificações não-destrutivas:
- Integridade do banco
- Status de certificados
- Notas incompletas

**Uso:**
```bash
cd verification
python check_db.py
python verificar_notas_incompletas.py
```

### 🔧 [Manutenção](./maintenance/README.md)
Scripts de limpeza e organização:
- Limpar protocolos antigos
- Remover resumos vazios
- Processar eventos

**⚠️ ATENÇÃO:** Podem modificar dados!

**Uso:**
```bash
cd maintenance
python limpar_protocolos.py
```

### 🔄 [Migração](./migration/README.md)
Migrações e correções de dados:
- Criptografar senhas
- Migrar para portátil
- Corrigir informante

**🛑 CRÍTICO:** Sempre faça backup antes!

**Uso:**
```bash
cd migration
# 1. BACKUP PRIMEIRO!
copy ..\..\notas.db ..\..\notas.db.backup

# 2. Executar migração
python migrate_encrypt_passwords.py
```

### 📖 [Exemplos](./examples/README.md)
Exemplos e scripts de setup:
- Exemplo de manifestação
- Setup de banco de teste
- Criar dados de teste

**Uso:**
```bash
cd examples
python setup_test_db.py
python exemplo_manifestacao.py
```

---

## 🎯 Fluxo de Trabalho Recomendado

### 1️⃣ Desenvolvimento
```bash
# Setup
cd examples
python setup_test_db.py

# Desenvolver funcionalidade
# ...

# Testar
cd ..\unit
python test_nova_funcionalidade.py

# Verificar
cd ..\verification
python check_db.py
```

### 2️⃣ Debug de Problemas
```bash
# 1. Verificar
cd verification
python verificar_instalacao.py

# 2. Analisar
cd ..\analysis
python _analyze_db.py

# 3. Debug
cd ..\debug
python debug_db.py
```

### 3️⃣ Manutenção
```bash
# 1. Backup
copy notas.db notas.db.backup

# 2. Verificar antes
cd verification
python check_db.py

# 3. Executar manutenção
cd ..\maintenance
python limpar_protocolos.py

# 4. Verificar depois
cd ..\verification
python check_db.py
```

---

## 📝 Convenções de Nomenclatura

| Prefixo | Propósito | Exemplo | Modifica Dados? |
|---------|-----------|---------|-----------------|
| `test_*` | Teste unitário | `test_crypto.py` | ❌ Não |
| `teste_*` | Teste integração | `teste_nuvem_fiscal.py` | ❌ Não |
| `check_*` | Verificação | `check_db.py` | ❌ Não |
| `verificar_*` | Validação | `verificar_instalacao.py` | ❌ Não |
| `debug_*` | Debug | `debug_db.py` | ❌ Não |
| `_*` | Análise interna | `_analyze_db.py` | ❌ Não |
| `limpar_*` | Limpeza | `limpar_protocolos.py` | ✅ Sim |
| `remover_*` | Remoção | `remover_resumos.py` | ✅ Sim |
| `processar_*` | Processamento | `processar_eventos.py` | ✅ Sim |
| `migrate_*` | Migração | `migrate_encrypt.py` | ✅ Sim |
| `fix_*` | Correção | `fix_informante.py` | ✅ Sim |
| `corrigir_*` | Correção | `corrigir_informante.py` | ✅ Sim |
| `exemplo_*` | Exemplo | `exemplo_manifestacao.py` | ❌ Não |
| `setup_*` | Setup | `setup_test_db.py` | ✅ Sim (teste) |

---

## 🔒 Níveis de Segurança

### 🟢 SEGURO (Apenas Leitura)
- ✅ Testes unitários
- ✅ Verificações
- ✅ Debug
- ✅ Análise

### 🟡 CUIDADO (Modifica Dados de Teste)
- ⚠️ Setup de teste
- ⚠️ Criar dados de teste
- ⚠️ Exemplos

### 🔴 CRÍTICO (Modifica Dados Reais)
- 🛑 Manutenção
- 🛑 Migração
- 🛑 Correções

**Regra de Ouro:** Sempre faça backup antes de executar scripts 🔴 CRÍTICOS!

---

## 📚 Links Úteis

- [Documentação Completa](../docs/README.md)
- [README Principal](../README.md)
- [Guia de Instalação](../docs/instalacao/INSTALACAO.md)
- [Solução de Problemas](../docs/troubleshooting/)

---

**Última atualização:** 29/01/2026  
**Organização:** ✅ Completa e Otimizada
