# Sistema de Busca NFS-e - Ambiente Nacional

## 📋 Visão Geral

Sistema integrado de busca de Notas Fiscais de Serviço Eletrônicas (NFS-e) via **Ambiente de Dados Nacional (ADN)** do Sistema Nacional de NFS-e, utilizando consulta própria com certificado digital A1.

Similar ao processo de NF-e e CT-e, com autenticação mTLS e consulta incremental via NSU.

---

## 🔍 Modos de Busca

### 1️⃣ Busca Incremental (Busca na Sefaz)

**Descrição:** Busca apenas documentos novos desde o último NSU processado.

**Uso:**
```bash
python buscar_nfse_auto.py
```

**Características:**
- ✅ Consulta incremental (continua do último NSU salvo)
- ✅ Rápido e eficiente
- ✅ Uso diário/regular
- ✅ Economiza requisições

**Exemplo de saída:**
```
📍 Modo: BUSCA INCREMENTAL (continuando do último NSU)
📍 BUSCA INCREMENTAL: Ultimo NSU processado: 51
🔍 Iniciando busca a partir do NSU 52
```

---

### 2️⃣ Busca Completa (Busca Todos)

**Descrição:** Busca TODOS os documentos desde o início (NSU=0).

**Uso:**
```bash
python buscar_nfse_auto.py --completa
# ou
python buscar_nfse_auto.py --all
```

**Características:**
- 🔄 Reset do NSU para 0
- 🔄 Busca todos documentos disponíveis
- ⚠️  Consome mais requisições
- 📅 Usar apenas em casos específicos:
  - Primeira configuração
  - Reprocessamento após problemas
  - Auditoria completa

**Exemplo de saída:**
```
🔄 Modo: BUSCA COMPLETA (resetando NSU para 0)
🔄 BUSCA COMPLETA: Iniciando do NSU=0 (todos os documentos)
🔍 Iniciando busca a partir do NSU 1
```

---

## 🛠️ Como Funciona

### Fluxo de Busca Incremental

```
1. Consulta último NSU salvo no banco (ex: 51)
2. Inicia busca do NSU 52 em diante
3. Para cada NSU:
   - GET /contribuintes/DFe/{NSU}
   - Processa LoteDFe array
   - Decodifica Base64 + gzip
   - Extrai dados do XML
   - Salva no banco e arquivo
4. Atualiza último NSU processado
5. Para após 5 NSUs seguidos sem documentos (404)
```

### Fluxo de Busca Completa

```
1. Ignora NSU salvo, inicia do 0
2. Busca todos documentos desde o início
3. Sobrescreve registros existentes
4. Atualiza NSU final
```

---

## 📊 Comparação com NF-e/CT-e

| Característica | NF-e/CT-e | NFS-e |
|----------------|-----------|-------|
| **Endpoint** | Sefaz Estadual | Ambiente Nacional |
| **Autenticação** | mTLS (A1) | mTLS (A1) |
| **NSU Incremental** | ✅ Sim (15 dígitos) | ✅ Sim (inteiro) |
| **Busca Completa** | NSU="000000000000000" | `busca_completa=True` |
| **Rate Limit** | Não documentado | 1 req/seg |
| **Formato Resposta** | XML | JSON + Base64(gzip(XML)) |

---

## 🎯 Casos de Uso

### Busca Incremental (Recomendado)
- ✅ Busca diária automática
- ✅ Integração com loop principal
- ✅ Monitoramento contínuo
- ✅ Baixo consumo de recursos

### Busca Completa (Casos Especiais)
- 🔧 Primeira configuração de certificado
- 🔧 Recuperação após falha
- 🔧 Mudança de servidor/banco
- 🔧 Auditoria completa
- 🔧 Reprocessamento de dados

---

## 💾 Estrutura de Dados

### Banco de Dados (`nfe_data.db`)

**Tabela `nfse_baixadas`:**
```sql
CREATE TABLE nfse_baixadas (
    numero_nfse TEXT,           -- Número da NFS-e
    cnpj_prestador TEXT,        -- CNPJ do prestador
    cnpj_tomador TEXT,          -- CNPJ do tomador
    data_emissao TEXT,          -- Data de emissão
    valor_servico REAL,         -- Valor do serviço
    xml_content TEXT,           -- XML completo
    data_download TEXT          -- Timestamp do download
);
```

**Tabela `nsu_nfse`:**
```sql
CREATE TABLE nsu_nfse (
    informante TEXT PRIMARY KEY,  -- CNPJ do informante
    ult_nsu INTEGER,              -- Último NSU processado
    atualizado_em TEXT            -- Timestamp da atualização
);
```

### Arquivos XML

**Estrutura de pastas:**
```
xmls/
└── {CNPJ}/
    └── {MM-YYYY}/
        └── NFSe/
            ├── NFSe_{numero}.xml
            ├── NFSe_{numero}.xml
            └── ...
```

**Exemplo:**
```
xmls/33251845000109/01-2023/NFSe/NFSe_2300000001577.xml
```

---

## 🔐 Segurança e Rate Limiting

### Rate Limiting Implementado

```python
# 1 requisição por segundo
time.sleep(1)  

# Backoff em caso de 429 (Too Many Requests)
if status_code == 429:
    time.sleep(2)
```

### Autenticação mTLS

- Certificado digital A1 (ICP-Brasil)
- Senha criptografada no banco
- Validação automática de validade

---

## 📈 Estatísticas e Logs

### Logs Informativos

```
INFO: 📍 Ultimo NSU processado: 51
INFO: 🔍 Iniciando busca a partir do NSU 52
INFO: ✅ NSU 52: NFS-e processado
INFO: ✅ NSU 53: NFS-e processado
INFO: 💾 Ultimo NSU atualizado: 102
INFO: ✅ BUSCA CONCLUIDA: 50/50 documento(s) salvo(s)
```

### Resumo Final

```
RESUMO FINAL
======================================================================
Certificados processados: 4
Com configuracao NFS-e: 1
Total de notas encontradas: 50
======================================================================
```

---

## 🚀 Integração com Sistema Principal

### Via Linha de Comando

```bash
# Busca incremental (padrão)
python buscar_nfse_auto.py

# Busca completa
python buscar_nfse_auto.py --completa
```

### Via Código Python

```python
from buscar_nfse_auto import buscar_todos_certificados

# Busca incremental
buscar_todos_certificados(busca_completa=False)

# Busca completa
buscar_todos_certificados(busca_completa=True)
```

### Via Interface (Futuro)

Integração com [Busca NF-e.py](Busca NF-e.py):
- Botão "Busca na Sefaz" → Busca incremental
- Botão "Busca Completa" → Busca completa (NSU=0)

---

## ⚙️ Configuração

### Pré-requisitos

1. ✅ Certificado digital A1 cadastrado
2. ✅ CNPJ configurado com município (tabela `config_nfse`)
3. ✅ Senha descriptografada automaticamente

### Configurar Novo Certificado

```python
from nfse_search import NFSeDatabase

db = NFSeDatabase()

# Adicionar configuração NFS-e
db.conn.execute('''
    INSERT INTO config_nfse (cnpj, provedor, cod_municipio, inscricao_municipal)
    VALUES (?, ?, ?, ?)
''', ('33251845000109', 'Sistema Nacional', '5002704', '123456'))

db.conn.commit()
```

### Verificar Configurações

```bash
python -c "from nfse_search import NFSeDatabase; db = NFSeDatabase(); print(db.get_certificados())"
```

---

## 🐛 Troubleshooting

### Problema: NSU não avança

**Solução:**
```python
# Verificar último NSU
from nfse_search import NFSeDatabase
db = NFSeDatabase()
print(db.get_last_nsu_nfse('33251845000109'))

# Resetar NSU (busca completa)
python buscar_nfse_auto.py --completa
```

### Problema: Nenhum documento encontrado

**Verificações:**
1. Certificado válido e ativo?
2. CNPJ tem NFS-e emitidas/recebidas?
3. Configuração de município correta?
4. Rate limit sendo respeitado?

### Problema: Erro 429 (Too Many Requests)

**Solução:** Sistema já implementa:
- ✅ 1 req/segundo automático
- ✅ Backoff de 2s em caso de 429
- ✅ Limite de 50 docs por execução

---

## 📚 Referências

- **API Oficial:** https://adn.nfse.gov.br
- **Documentação:** [Sistema Nacional NFS-e](https://www.gov.br/nfse/)
- **Formato Resposta:** JSON com `LoteDFe` array
- **Encoding:** Base64 → gzip → XML UTF-8

---

## 🎯 Próximos Passos

- [ ] Integrar ao loop principal ([nfe_search.py](nfe_search.py))
- [ ] Adicionar à interface GUI ([Busca NF-e.py](Busca NF-e.py))
- [ ] Implementar download de DANFSE (PDF)
- [ ] Configurar certificados restantes (3)
- [ ] Adicionar filtros de busca avançados
- [ ] Dashboard de estatísticas NFS-e

---

**Última atualização:** 10/01/2026  
**Versão do sistema:** 1.0.0
