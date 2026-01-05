# 📋 Padrão de Arquivamento de Documentos Fiscais

## 🎯 Objetivo

Este documento estabelece o padrão oficial de arquivamento de documentos fiscais eletrônicos (NFe, CTe, Eventos, etc.) baixados da SEFAZ. O objetivo é garantir organização, facilitar buscas e manter um arquivo seguro e padronizado.

---

## 📁 Estrutura de Pastas

### Pasta de Origem (Arquivo Seguro)
Todos os documentos devem ser armazenados na pasta **`xmls/`** (pasta raiz de origem), organizada da seguinte forma:

```
xmls/
├── {CNPJ}/
│   ├── {ANO-MES}/
│   │   ├── NFe/
│   │   │   ├── {CHAVE}.xml
│   │   │   ├── {CHAVE}.pdf
│   │   │   └── ...
│   │   ├── CTe/
│   │   │   ├── {CHAVE}.xml
│   │   │   ├── {CHAVE}.pdf
│   │   │   └── ...
│   │   ├── Resumos/
│   │   │   ├── {CHAVE}.xml
│   │   │   └── ...
│   │   ├── Eventos/
│   │   │   ├── {CHAVE}.xml
│   │   │   └── ...
│   │   └── Outros/
│   │       └── ...
│   └── ...
└── ...
```

### Explicação da Estrutura

1. **`{CNPJ}/`**: CNPJ do certificado digital (formatado sem pontos/barras)
   - Exemplo: `47539664000197`
   - Se for CPF, usar o CPF sem pontos/traços

2. **`{ANO-MES}/`**: Ano e mês de emissão do documento (formato: `YYYY-MM`)
   - Exemplo: `2025-08`, `2026-01`
   - Extraído da data de emissão da nota ou da chave de acesso

3. **Tipo de Documento:**
   - **`NFe/`**: Notas Fiscais Eletrônicas completas
   - **`CTe/`**: Conhecimentos de Transporte Eletrônicos completos
   - **`Resumos/`**: Resumos de NFe (manifestação)
   - **`Eventos/`**: Eventos (cancelamento, carta de correção, ciência, etc.)
   - **`Outros/`**: Documentos que não se encaixam nas categorias acima

---

## 📝 Nomenclatura de Arquivos

### ⚠️ REGRA FUNDAMENTAL: SEMPRE USE A CHAVE DE ACESSO

**Todos os arquivos XML devem ser nomeados usando a CHAVE DE ACESSO de 44 dígitos.**

### Formato Padrão

```
{CHAVE}.xml
{CHAVE}.pdf
```

### Exemplos Práticos

✅ **CORRETO:**
```
52260115045348000172570010014777191002562584.xml
52260115045348000172570010014777191002562584.pdf
```

❌ **INCORRETO:**
```
1477719-NWF TRANSPORTES E LOGISTICA LTDA.xml  ❌ Não usar número + nome
nfe_001.xml                                     ❌ Não usar nome genérico
nota_empresa_123.xml                            ❌ Não usar nome customizado
```

### Por que usar a Chave?

1. ✅ **Unicidade**: Cada documento tem uma chave única de 44 dígitos
2. ✅ **Padronização**: Mesmo formato para todos os tipos de documento
3. ✅ **Busca Eficiente**: Localização instantânea por chave
4. ✅ **Integridade**: Chave é imutável e identifica o documento oficialmente
5. ✅ **Compatibilidade**: Facilita integração com outros sistemas

---

## 🔍 Tipos de Documentos e suas Chaves

### NFe (Nota Fiscal Eletrônica)
- **Tag XML**: `<nfeProc>` ou `<NFe>`
- **Chave**: Extraída de `<infNFe Id="NFe{CHAVE}">`
- **Pasta**: `NFe/`
- **Exemplo**: `35241234567890123456550010000123451234567890.xml`

### CTe (Conhecimento de Transporte Eletrônico)
- **Tag XML**: `<cteProc>` ou `<CTe>`
- **Chave**: Extraída de `<infCte Id="CTe{CHAVE}">`
- **Pasta**: `CTe/`
- **Exemplo**: `52241234567890123456570010000123451234567890.xml`

### Resumos (resNFe)
- **Tag XML**: `<resNFe>`
- **Chave**: Conteúdo da tag `<chNFe>`
- **Pasta**: `Resumos/`
- **Exemplo**: `35241234567890123456550010000123451234567890.xml`

### Eventos
- **Tag XML**: `<resEvento>`, `<procEventoNFe>`, `<evento>`
- **Chave**: Conteúdo da tag `<chNFe>` dentro do evento
- **Pasta**: `Eventos/`
- **Tipos de eventos**:
  - `110110`: Carta de Correção
  - `110111`: Cancelamento
  - `210200`: Confirmação da Operação
  - `210210`: Ciência da Operação
  - `210220`: Desconhecimento da Operação
  - `210240`: Operação Não Realizada
- **Exemplo**: `35241234567890123456550010000123451234567890.xml` (evento de cancelamento)
- **Observação**: Múltiplos eventos da mesma nota terão o mesmo nome base (a chave), mas podem ter sequências diferentes

---

## 💾 Banco de Dados (xmls_baixados)

### Registro Automático

Todo arquivo salvo deve ser **automaticamente registrado** na tabela `xmls_baixados` do banco de dados.

### Estrutura da Tabela

```sql
CREATE TABLE xmls_baixados (
    chave TEXT PRIMARY KEY,
    cnpj_cpf TEXT,
    caminho_arquivo TEXT NOT NULL,
    xml_completo INTEGER DEFAULT 1,
    baixado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Campos

- **`chave`**: Chave de acesso de 44 dígitos (PRIMARY KEY)
- **`cnpj_cpf`**: CNPJ/CPF do certificado usado
- **`caminho_arquivo`**: Caminho absoluto do arquivo XML
- **`xml_completo`**: 1 para XML completo, 0 para resumo
- **`baixado_em`**: Data/hora do download

### Fluxo de Registro

```python
# 1. Salvar XML no disco
caminho_xml = f"xmls/{cnpj}/{ano_mes}/{tipo}/{chave}.xml"
with open(caminho_xml, 'w') as f:
    f.write(xml_content)

# 2. Registrar no banco automaticamente
conn.execute('''
    INSERT OR REPLACE INTO xmls_baixados 
    (chave, cnpj_cpf, caminho_arquivo, baixado_em)
    VALUES (?, ?, ?, datetime('now'))
''', (chave, cnpj_cpf, os.path.abspath(caminho_xml)))
```

---

## 🔎 Busca e Localização de Arquivos

### Estratégia de Busca em Ordem de Prioridade

Quando o sistema precisa localizar um XML pela chave:

#### 1️⃣ **Busca no Banco de Dados (Mais Rápido)**
```python
cursor.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
result = cursor.fetchone()
if result and Path(result[0]).exists():
    return result[0]
```

#### 2️⃣ **Busca por Nome de Arquivo (Rápido)**
```python
# Busca recursiva por arquivo com nome exato
for xml_file in Path("xmls").rglob(f"{chave}.xml"):
    return xml_file
```

#### 3️⃣ **Busca por Conteúdo (Lento - Apenas Fallback)**
```python
# Usado apenas para arquivos legados com nomes incorretos
# Lê conteúdo de arquivos para encontrar a chave
# Limitado a 1000 arquivos e primeiros 2KB de cada arquivo
```

#### 4️⃣ **Diretórios Legados (Obsoleto)**
```python
# Pastas antigas mantidas por compatibilidade:
# - xmls_chave/
# - xml_extraidos/
# - xml_NFs/
```

### Performance

- ✅ **Banco de Dados**: ~1ms (instantâneo)
- ✅ **Busca por Nome**: ~10-50ms (rápido)
- ⚠️ **Busca por Conteúdo**: ~5-30s (lento, apenas fallback)
- ⚠️ **Diretórios Legados**: ~2-10s (lento)

---

## 📤 Exportação de Documentos

### Funcionamento

Ao exportar documentos, o sistema:

1. Obtém a chave de acesso do documento selecionado
2. Busca o XML usando a estratégia de prioridade acima
3. Busca o PDF correspondente (mesmo nome, extensão .pdf)
4. Copia os arquivos para a pasta de destino

### Opções de Exportação

- **Exportar só XML**: Copia apenas o arquivo XML
- **Exportar só PDF**: Copia apenas o arquivo PDF
- **Exportar XML e PDF**: Copia ambos os arquivos
- **Nome Personalizado**: Renomeia para `{numero}_{nome_emitente}.{ext}`
- **Nome Padrão**: Mantém o nome original (chave)

---

## ✅ Checklist de Conformidade

Ao implementar ou modificar funcionalidades relacionadas a arquivos, verifique:

- [ ] XML salvo com nome = chave de acesso (44 dígitos)?
- [ ] Arquivo salvo na estrutura `xmls/{cnpj}/{ano-mes}/{tipo}/`?
- [ ] Chave extraída corretamente do XML?
- [ ] Caminho registrado automaticamente no banco `xmls_baixados`?
- [ ] PDF gerado com o mesmo nome do XML (quando aplicável)?
- [ ] Busca prioriza banco de dados antes de procurar no disco?
- [ ] Logs indicam claramente onde o arquivo foi salvo?

---

## 🚀 Benefícios do Padrão

### Para o Sistema
1. ✅ **Busca Instantânea**: Localização por chave é O(1) no banco
2. ✅ **Sem Duplicatas**: Chave é única, previne arquivos repetidos
3. ✅ **Manutenção Simples**: Estrutura previsível e organizada
4. ✅ **Escalabilidade**: Funciona com milhões de documentos

### Para o Usuário
1. ✅ **Organização Clara**: Pastas por CNPJ e período
2. ✅ **Facilita Auditoria**: Encontra documentos rapidamente
3. ✅ **Compatibilidade**: Arquivos podem ser usados em outros sistemas
4. ✅ **Backup Confiável**: Estrutura consistente facilita backups

---

## 📌 Observações Importantes

### Migração de Arquivos Legados

Arquivos salvos com nomes antigos (`{numero}-{nome}.xml`) ainda funcionarão através da busca por conteúdo, mas:

⚠️ **Recomenda-se renomear** arquivos antigos para o padrão novo usando scripts de migração.

### Eventos Múltiplos

Para eventos da mesma nota (ex: manifestação + cancelamento):
- Ambos terão o mesmo nome base (a chave)
- Sistema sobrescreverá o arquivo anterior
- **Solução futura**: Adicionar sufixo de sequência ou tipo de evento

### Arquivos Corrompidos

Se um XML não puder ser parseado para extrair a chave:
- Sistema salvará em `Outros/` com nome genérico
- Log registrará o erro para investigação manual

---

## 🔧 Implementação no Código

### Função Principal: `salvar_xml_por_certificado()`

**Arquivo**: `nfe_search.py`

**Responsabilidades**:
1. Parsear XML para identificar tipo e extrair chave
2. Criar estrutura de pastas `xmls/{cnpj}/{ano-mes}/{tipo}/`
3. Salvar arquivo como `{chave}.xml`
4. Registrar no banco `xmls_baixados`
5. Gerar PDF automaticamente (NFe/CTe completos)

### Função de Busca: `_encontrar_arquivo_xml()`

**Arquivo**: `interface_pyqt5.py`

**Responsabilidades**:
1. Consultar banco de dados primeiro
2. Buscar por nome de arquivo
3. Fallback: busca por conteúdo (arquivos legados)
4. Retornar caminho absoluto ou None

---

## 📅 Controle de Versão

- **Versão**: 1.0
- **Data**: Janeiro 2026
- **Status**: ✅ Ativo
- **Autor**: Sistema BOT Busca NFE

---

## 🔄 Histórico de Mudanças

### v1.0.85 - Janeiro 2026
- ✅ Implementação inicial do padrão
- ✅ Documentação criada
- ✅ Sistema de busca por prioridade
- ✅ Registro automático no banco

---

**📧 Em caso de dúvidas sobre o padrão, consulte este documento antes de fazer modificações no código.**
