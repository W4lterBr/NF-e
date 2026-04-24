# 📁 Padrão de Salvamento de Documentos Fiscais

> Busca NF-e — Documentação Técnica de Salvamento  
> Versão: 1.2.0 | Atualizado em: 2026-03-03

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Estrutura de Pastas](#2-estrutura-de-pastas)
3. [Fluxo de Salvamento](#3-fluxo-de-salvamento)
4. [Rastreamento no Banco de Dados](#4-rastreamento-no-banco-de-dados)
5. [Nomenclatura de Arquivos](#5-nomenclatura-de-arquivos)
6. [Perfis de Armazenamento](#6-perfis-de-armazenamento)
7. [Formatos de Mês Configuráveis](#7-formatos-de-mês-configuráveis)
8. [Busca e Localização de Arquivos](#8-busca-e-localização-de-arquivos)
9. [Fluxo de Código](#9-fluxo-de-código)
10. [Tabelas do Banco de Dados](#10-tabelas-do-banco-de-dados)

---

## 1. Visão Geral

Todo documento fiscal baixado (NF-e, CT-e, NFS-e) é salvo em **até três destinos simultâneos**:

| Destino | Tipo | Descrição |
|---------|------|-----------|
| `xmls/` | LOCAL | Backup interno, indexado por CNPJ |
| `storage_pasta_base` | STORAGE | Pasta de armazenamento configurada pelo usuário |
| Perfis ativos | PERFIL | Um ou mais perfis nomeados (ex.: `Importação para Domínio`) |

O caminho de **cada destino** é registrado automaticamente no banco de dados na tabela `xmls_caminhos`, garantindo rastreamento 100% de onde cada arquivo está.

---

## 2. Estrutura de Pastas

### 2.1 Backup LOCAL — `xmls/`

Organização fixa: **TIPO → CNPJ → DATA**

```
xmls/
├── NFe/
│   └── 48160135000140/
│       └── 022026/
│           ├── 000203-DELMA GRANATO MARTINS.xml
│           └── 000203-DELMA GRANATO MARTINS.pdf
├── CTe/
│   └── 47539664000197/
│       └── 012026/
│           └── 000118-TRANSPORTADORA XYZ.xml
├── NFSe/
│   └── 12345678000195/
│       └── 032026/
│           └── NFSe_000042.xml
├── Resumos/
│   └── 48160135000140/
│       └── 022026/
│           └── 000001-ResumoGeral.xml
└── Eventos/
    └── ...
```

> **Pasta do certificado** no backup local = CNPJ puro (14 dígitos)  
> Exemplo: `48160135000140`

---

### 2.2 Armazenamento STORAGE / PERFIL

A estrutura depende do `organizacao_tipo` configurado no perfil:

#### `TIPO_CERTIFICADO` — Tipo → Certificado → Data
```
C:\Arquivo Walter\Notas\NFs\
├── NFe/
│   └── 99-JL COMERCIO/
│       └── 022026/
│           └── 000203-DELMA GRANATO MARTINS.xml
```

#### `CERTIFICADO_TIPO_DATA` *(padrão recomendado)* — Certificado → Tipo → Data
```
C:\Arquivo Walter\Notas\DominioWeb\
├── 99-JL COMERCIO/
│   ├── NFe/
│   │   └── 022026/
│   │       └── 000203-DELMA GRANATO MARTINS.xml
│   └── CTe/
│       └── 012026/
│           └── 000118-TRANSPORTADORA XYZ.xml
```

#### `CERTIFICADO_TIPO` *(modo compatibilidade)* — Certificado → Data → Tipo
```
C:\Arquivo Walter\Notas\NFs\
├── 99-JL COMERCIO/
│   └── 022026/
│       └── NFe/
│           └── 000203-DELMA GRANATO MARTINS.xml
```

> **Pasta do certificado** no armazenamento = `nome_certificado` (nome amigável), ex.: `99-JL COMERCIO`

---

## 3. Fluxo de Salvamento

```
salvar_xml_por_certificado(xml, cnpj, pasta_base, nome_cert)
│
├── pasta_base = None  →  _salvar_xml_multiplos_perfis()
│       │
│       ├── Para cada perfil ativo em perfis_armazenamento:
│       │       _salvar_xml_single_profile(..., perfil_nome=nome_perfil)
│       │               └── _registrar_caminho_salvo(tipo='PERFIL')
│       └── Retorna caminho do primeiro perfil
│
└── pasta_base = "xmls" ou caminho absoluto
        │
        └── _salvar_xml_single_profile(xml, cnpj, pasta_base, ...)
                │
                ├── Detecta tipo do documento (NFe/CTe/NFSe/Resumo/Evento)
                ├── Extrai chave de acesso, número e nome do emitente
                ├── Calcula pasta destino conforme organizacao_tipo
                ├── Salva arquivo .xml
                ├── Gera PDF automaticamente (NFe e CTe completas)
                └── _registrar_caminho_salvo(chave, cnpj, caminho, tipo)
```

### Sequência completa ao baixar uma NF-e:

```
1. baixar_resumos_pendentes()  ou  run_single_cycle()
   │
   ├── XML recebido da SEFAZ
   │
   ├── salvar_xml_por_certificado(xml, cnpj, pasta_base="xmls")
   │       → Salva em:  xmls/NFe/{CNPJ}/{MM-AAAA}/{numero}-{nome}.xml
   │       → Registra:  xmls_caminhos  (tipo=LOCAL)
   │       → Atualiza:  xmls_baixados  (caminho_arquivo)
   │
   ├── storage_pasta_base configurado?
   │   └── salvar_xml_por_certificado(xml, cnpj, pasta_base=storage_base, nome_cert)
   │           → Salva em:  {storage_base}/{nome_cert}/{MM-AAAA}/{tipo}/{numero}-{nome}.xml
   │           → Registra:  xmls_caminhos  (tipo=STORAGE)
   │
   └── salvar_xml_por_certificado(xml, cnpj, pasta_base=None, nome_cert)
           → Para cada perfil ativo:
               → Salva em:  {pasta_perfil}/{...}/{numero}-{nome}.xml
               → Registra:  xmls_caminhos  (tipo=PERFIL, perfil_nome=nome)
```

---

## 4. Rastreamento no Banco de Dados

### Tabela `xmls_caminhos` — Todos os destinos

```sql
CREATE TABLE xmls_caminhos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chave       TEXT NOT NULL,          -- chave de acesso (44 dígitos)
    cnpj_cpf    TEXT,                   -- CNPJ do certificado
    caminho     TEXT NOT NULL,          -- caminho absoluto completo
    tipo        TEXT DEFAULT 'LOCAL',   -- LOCAL | STORAGE | PERFIL
    perfil_nome TEXT,                   -- nome do perfil (quando tipo=PERFIL)
    salvo_em    TEXT,                   -- data/hora do salvamento
    UNIQUE(chave, caminho)
);
```

### Tabela `xmls_baixados` — Caminho primário (compatibilidade)

```sql
CREATE TABLE xmls_baixados (
    chave           TEXT PRIMARY KEY,
    cnpj_cpf        TEXT,
    caminho_arquivo TEXT,   -- caminho do backup LOCAL (sincronizado automaticamente)
    xml_completo    TEXT,
    baixado_em      TEXT
);
```

> `xmls_baixados.caminho_arquivo` é mantido automaticamente em sincronia com o `caminho` do tipo LOCAL em `xmls_caminhos`.

### Consultas úteis

```sql
-- Todos os destinos de uma nota específica
SELECT tipo, perfil_nome, caminho, salvo_em
FROM xmls_caminhos
WHERE chave = '35260148160135000140550010002030000...'
ORDER BY tipo, salvo_em;

-- Notas sem nenhum caminho registrado
SELECT chave FROM notas_detalhadas
WHERE chave NOT IN (SELECT DISTINCT chave FROM xmls_caminhos);

-- Resumos de quantos arquivos por tipo de armazenamento
SELECT tipo, COUNT(*) AS total
FROM xmls_caminhos
GROUP BY tipo;

-- Notas com caminhos inválidos (arquivo deletado)
-- (rodar via Python — SQLite não tem acesso ao filesystem)
```

---

## 5. Nomenclatura de Arquivos

### Padrão: `{NUMERO}-{NOME}.xml`

| Campo | Fonte | Limite | Exemplo |
|-------|-------|--------|---------|
| `NUMERO` | Tag `<nNF>` (NFe), `<nCT>` (CTe), `<nNFSe>` (NFSe) | sem limite | `000203` |
| `NOME` | Tag `<xNome>` do emitente / prestador | 50 caracteres | `DELMA GRANATO MARTINS` |

**Exemplos:**
```
000203-DELMA GRANATO MARTINS.xml
000118-TRANSPORTADORA ABC LTDA.xml
NFSe_000042.xml      ← NFS-e usa schema próprio
```

**Eventos:**
```
000203-CANCELAMENTO.xml
000203-CARTA_CORRECAO.xml
```

**Caracteres proibidos** nos nomes são substituídos por `_`:
```
\ / * ? : " < > |
```

---

## 6. Perfis de Armazenamento

Configurados em **Tarefas → Armazenamento** (ou `Ctrl+Shift+A`).

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome amigável do perfil |
| `pasta_base` | Caminho raiz dos arquivos |
| `formato_pasta_mes` | Formato da subpasta de mês (ver seção 7) |
| `organizacao_tipo` | Hierarquia das pastas (ver seção 2.2) |
| `ativo` | `1` = ativo, `0` = inativo |
| `is_default` | Perfil prioritário (caminho retornado como principal) |

> Apenas documentos fiscais completos (NF-e, CT-e, NFS-e) são salvos nos perfis.  
> Resumos, Eventos e Ciências ficam **apenas** no backup local (`xmls/`).

---

## 7. Formatos de Mês Configuráveis

Configurado em **Configurações → `storage_formato_mes`**.

| Valor | Exemplo | Uso |
|-------|---------|-----|
| `AAAA-MM` | `2026-02` | Padrão — ordenação cronológica natural |
| `MM-AAAA` | `02-2026` | — |
| `MMAAAA` | `022026` | Compatibilidade Domínio Sistemas |
| `AAAAAMM` | `202602` | — |
| `AAAA/MM` | `2026/02` | Hierarquia de subpastas (cria subpasta extra) |
| `MM/AAAA` | `02/2026` | — |

---

## 8. Busca e Localização de Arquivos

Ao exportar documentos, o sistema localiza arquivos na seguinte ordem de prioridade:

### Para XML (`_encontrar_arquivo_xml`):

| Prioridade | Fonte | Descrição |
|-----------|-------|-----------|
| **1a** | `xmls_caminhos` | Todos os caminhos registrados (LOCAL, STORAGE, PERFIL) |
| **1b** | `xmls_baixados` | Caminho primário (compatibilidade legado) |
| **1.5** | `notas_detalhadas` | Constrói caminhos prováveis usando CNPJ, nome_cert, data e tipo |
| **2** | Varredura `rglob` | Varre toda a pasta `xmls/` em busca do conteúdo |
| **3** | Pastas legado | Verifica estruturas antigas de versões anteriores |

### Para PDF (`_encontrar_arquivo_pdf`):

Mesma hierarquia do XML, mas procura o `.pdf` ao lado de cada `.xml` encontrado.

---

## 9. Fluxo de Código

```
nfe_search.py
├── _registrar_caminho_salvo(chave, cnpj, caminho, tipo, perfil_nome)
│       Registra em xmls_caminhos + sincroniza xmls_baixados (se LOCAL)
│
├── salvar_xml_por_certificado(xml, cnpj, pasta_base, nome_cert)
│       Ponto de entrada público — roteia para single/multi perfil
│
├── _salvar_xml_multiplos_perfis(xml, cnpj, nome_cert)
│       Itera sobre perfis_armazenamento ativos
│       Chama _salvar_xml_single_profile com perfil_nome
│
└── _salvar_xml_single_profile(xml, cnpj, pasta_base, nome_cert, ..., perfil_nome)
        Lógica principal de salvamento
        Chama _registrar_caminho_salvo automaticamente após salvar

Busca NF-e.py
├── _encontrar_arquivo_xml(chave)
│       Consulta xmls_caminhos → xmls_baixados → busca inteligente → rglob
│
└── _encontrar_arquivo_pdf(chave)
        Consulta xmls_caminhos → xmls_baixados → busca inteligente → rglob
```

---

## 10. Tabelas do Banco de Dados

### Tabelas relacionadas ao salvamento:

```
notas.db
├── xmls_caminhos       ← NOVO (v1.2.0) — todos os destinos de cada documento
├── xmls_baixados       ← caminho LOCAL primário (compatibilidade)
├── notas_detalhadas    ← metadados do documento (chave, número, data, tipo, cnpj)
├── perfis_armazenamento← configurações de onde salvar
└── configuracoes       ← storage_pasta_base, storage_formato_mes, etc.
```

### Relação entre tabelas:

```
notas_detalhadas.chave (1)
    ├── (N) xmls_caminhos.chave  → um documento = múltiplos destinos
    └── (1) xmls_baixados.chave  → caminho LOCAL principal
```

---

*Documentação gerada automaticamente — Busca NF-e v1.2.0*
