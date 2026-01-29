# 📋 Integração Automática de NFS-e

## Visão Geral

O sistema agora possui **busca automática de NFS-e** integrada ao fluxo principal de atualização de notas. A busca de NFS-e é executada automaticamente após as buscas de NF-e e CT-e, sem intervenção manual.

---

## 🔄 Fluxo de Execução

### 1. Trigger Automático

A busca de NFS-e é acionada automaticamente em **duas situações**:

#### a) Refresh Manual (`refresh_all()`)
```
Usuário clica "Atualizar" → Carrega notas do banco → 2 segundos depois → Busca NFS-e
```

#### b) Busca Automática Agendada
```
Sistema inicia no Startup → 10 minutos depois → refresh_all() → Busca NFS-e
```

### 2. Arquitetura de Threads

```
┌─────────────────────────┐
│   Thread Principal      │  ← Interface gráfica (PyQt5)
│   (UI Thread)           │
└───────────┬─────────────┘
            │
            ├─ QTimer (2 segundos) → _buscar_nfse_automatico()
            │
            └─ Cria NFSeBuscaWorker (QThread)
                      │
                      └─ Executa subprocess: buscar_nfse_auto.py
                              │
                              └─ Busca NFS-e via ADN API
                                      │
                                      ├─ Salva XMLs em xmls/{CNPJ}/...
                                      ├─ Salva no banco (notas_detalhadas)
                                      └─ Baixa DANFSe (PDFs oficiais)
```

**Vantagens desta arquitetura:**
- ✅ **Não bloqueia a UI** - usuário continua usando o sistema
- ✅ **Timeout de 5 minutos** - previne travamentos
- ✅ **Processo isolado** - erros não afetam a aplicação principal
- ✅ **Logs separados** - facilita diagnóstico

---

## 📁 Estrutura de Arquivos

### Scripts Principais

| Arquivo | Função |
|---------|--------|
| **Busca NF-e.py** | Interface principal - Coordena todas as buscas |
| **buscar_nfse_auto.py** | Motor de busca NFS-e (executado como subprocesso) |
| **nfse_search.py** | Módulo de processamento de NFS-e (parse XML, banco de dados) |
| **modules/nfse_service.py** | Cliente REST API para comunicação com ADN |

### Fluxo de Dados

```
Busca NF-e.py (_buscar_nfse_automatico)
    ↓
buscar_nfse_auto.py (main)
    ↓
buscar_todos_certificados()
    ↓
processar_certificado()
    ↓
consultar_nfse_incremental() [modules/nfse_service.py]
    ↓
API ADN (https://adn.nfse.gov.br)
    ↓
salvar_nfse_detalhada() [nfse_search.py]
    ↓
notas_detalhadas (banco SQLite)
```

---

## ⚙️ Configuração

### 1. Busca Incremental (Padrão)

Por padrão, o sistema faz **busca incremental**:
- Consulta apenas documentos **novos** desde o último NSU
- Rápido e eficiente
- Executado automaticamente

```python
# Código: buscar_nfse_auto.py
buscar_todos_certificados(busca_completa=False)  # Padrão
```

### 2. Busca Completa (Manual)

Para buscar **todos** os documentos desde o início:

```bash
# Via linha de comando
python buscar_nfse_auto.py --completa

# Ou
python buscar_nfse_auto.py --all
```

⚠️ **Atenção**: Busca completa pode demorar muito (minutos/horas) dependendo do volume de NFS-e.

---

## 🗄️ Armazenamento de Dados

### Banco de Dados (SQLite)

Todas as NFS-e são salvas na tabela **`notas_detalhadas`**:

```sql
-- Campos principais
SELECT 
    chave,              -- Chave de acesso NFS-e (44 dígitos)
    tipo_documento,     -- "NFSe"
    numero,             -- Número da NFS-e
    data_emissao,       -- Data de emissão
    cnpj_emitente,      -- CNPJ do prestador
    cnpj_destinatario,  -- CNPJ do tomador
    valor_total,        -- Valor total do serviço
    xml_status          -- "disponível" se XML foi baixado
FROM notas_detalhadas
WHERE tipo_documento = 'NFSe';
```

### Arquivos Físicos

XMLs e PDFs são salvos em:

```
xmls/
└── {CNPJ}/
    └── {MES-ANO}/
        └── NFSe/
            ├── NFSe_123.xml      ← XML da NFS-e
            └── NFSe_123.pdf      ← DANFSe oficial
```

Exemplo:
```
xmls/47539664000197/12-2023/NFSe/
├── NFSe_9.xml
├── NFSe_9.pdf
├── NFSe_10.xml
└── NFSe_10.pdf
```

---

## 🔍 Logs e Monitoramento

### Logs da Aplicação Principal

```
[NFS-e] Iniciando busca automática de NFS-e...
[NFS-e] Thread de busca NFS-e iniciada
[NFS-e] ✅ Busca de NFS-e concluída com sucesso
```

### Logs do Script NFS-e

Arquivo: `logs/busca_nfe_2026-01-29.log`

```
======================================================================
BUSCANDO NFS-e VIA AMBIENTE NACIONAL
======================================================================
CNPJ: 47539664000197
Informante: 47539664000197
✅ Serviço NFS-e inicializado com sucesso
📍 Modo: BUSCA INCREMENTAL (últimos documentos)
✅ 42 documento(s) encontrado(s)
💾 XML salvo: C:\...\xmls\47539664000197\12-2023\NFSe\NFSe_9.xml
✅ NFS-e 9: R$ 6000.00 salva em notas_detalhadas
✅ DANFSe OFICIAL salvo: C:\...\NFSe_9.pdf
```

---

## 🛡️ Tratamento de Erros

### Timeout

Se a busca demorar mais de **5 minutos**:

```python
subprocess.TimeoutExpired
↓
[NFS-e] ⚠️  Timeout na busca de NFS-e (5 minutos excedidos)
```

Solução: Processo é encerrado automaticamente, UI permanece responsiva.

### Erros de Conexão

Se a API ADN estiver indisponível:

```
⚠️  Servidor temporariamente indisponível (502)
🔄 Tentativa 2/3...
```

O sistema tenta até 3 vezes com backoff exponencial.

### Erro no Script

Se `buscar_nfse_auto.py` não existir:

```python
[NFS-e] ⚠️  Script não encontrado: C:\...\buscar_nfse_auto.py
```

### Busca Já em Execução

Se uma busca anterior ainda estiver rodando:

```python
[NFS-e] Busca NFS-e já em execução, pulando...
```

---

## 🎯 Comportamento por Situação

### Cenário 1: Sistema Sem NFS-e

Se o CNPJ não tiver documentos NFS-e no ADN:

```
Certificados processados: 5
Com configuração NFS-e: 0
Total de notas encontradas: 0
```

**Resultado**: Nenhum arquivo criado, nenhum erro gerado.

### Cenário 2: ADN com Documentos

Se existirem NFS-e disponíveis:

```
✅ 42 documento(s) encontrado(s)
💾 NFS-e 9 salva no banco
💾 NFS-e 10 salva no banco
...
Total de notas encontradas: 42
```

**Resultado**: 
- 42 registros em `notas_detalhadas`
- 42 XMLs salvos em `xmls/`
- 42 PDFs baixados (se API disponível)

### Cenário 3: Múltiplos Certificados

Se houver 5 certificados cadastrados:

```
🧪 TESTE 1/5 - CNPJ: 01773924000193 → 0 documentos
🧪 TESTE 2/5 - CNPJ: 33251845000109 → 0 documentos
🧪 TESTE 3/5 - CNPJ: 47539664000197 → 42 documentos ✅
🧪 TESTE 4/5 - CNPJ: 48160135000140 → 0 documentos
🧪 TESTE 5/5 - CNPJ: 49068153000160 → 0 documentos
```

**Resultado**: Apenas o certificado 3 teve NFS-e baixadas.

---

## 🔧 Manutenção e Troubleshooting

### Forçar Busca Completa

Para reprocessar **todos** os documentos:

1. Abra PowerShell no diretório do sistema
2. Execute:

```powershell
.\.venv\Scripts\python.exe buscar_nfse_auto.py --completa
```

### Verificar NSU Atual

Para ver qual foi o último NSU processado:

```sql
-- Via SQLite
SELECT informante, MAX(nsu) as ultimo_nsu
FROM nsu_nfse
GROUP BY informante;
```

### Resetar NSU (Reprocessar Tudo)

Para começar do zero:

```sql
-- ⚠️ ATENÇÃO: Isto vai reprocessar TODOS os documentos
DELETE FROM nsu_nfse WHERE informante = '47539664000197';
```

Depois execute busca completa.

### Desabilitar Busca Automática

Se quiser desativar a busca automática de NFS-e:

```python
# Em Busca NF-e.py, linha ~2554
# Comente esta linha:
# QTimer.singleShot(2000, self._buscar_nfse_automatico)
```

---

## 📊 Performance

### Tempo de Execução

| Situação | Tempo Médio |
|----------|-------------|
| Sem documentos (maxNSU=0) | 1-2 segundos |
| 10 documentos | 30-60 segundos |
| 50 documentos | 2-5 minutos |
| 100+ documentos | 5-10 minutos |

### Consumo de Recursos

- **CPU**: Baixo (~5-10% durante busca)
- **Memória**: ~50-100 MB
- **Rede**: Variável (depende do tamanho dos XMLs)
- **Disco**: ~50 KB por NFS-e (XML + PDF)

---

## 🚀 Melhorias Futuras

### Planejadas

- [ ] Notificação ao usuário quando busca NFS-e concluir
- [ ] Barra de progresso para busca de NFS-e
- [ ] Cache de chaves já processadas (evitar redownload)
- [ ] Agendamento customizável (intervalo configurável)

### Em Avaliação

- [ ] Busca paralela por certificado (mais rápido)
- [ ] Retry automático em caso de timeout
- [ ] Dashboard com estatísticas de NFS-e

---

## 📖 Referências

- **API ADN**: https://adn.nfse.gov.br
- **Documentação NFS-e**: [ERROS_DOCUMENTACAO_NFSE.md](ERROS_DOCUMENTACAO_NFSE.md)
- **Diagnóstico**: [DIAGNOSTICO_NFSE.md](DIAGNOSTICO_NFSE.md)
- **Código fonte**: `buscar_nfse_auto.py`, `nfse_search.py`, `modules/nfse_service.py`

---

## 🆘 Suporte

Em caso de problemas:

1. Verifique os logs em `logs/busca_nfe_YYYY-MM-DD.log`
2. Execute busca manual para diagnóstico: `python buscar_nfse_auto.py`
3. Consulte [DIAGNOSTICO_NFSE.md](DIAGNOSTICO_NFSE.md)

**Última atualização**: 29/01/2026
