# 📄 Correção: Abertura de PDFs em Eventos

## 🐛 Problema Identificado

Ao clicar duas vezes em documentos vinculados (CTe, MDFe, etc.) dentro da guia **Eventos** ou **Vínculos**, o sistema exibia a mensagem "PDF não encontrado", mesmo quando o documento existia e podia ser visualizado normalmente na interface principal.

### Sintomas
- ✅ Chave extraída corretamente do XML de evento
- ✅ Documento encontrado no banco de dados
- ❌ PDF não localizado no sistema de arquivos
- ✅ Mesmo documento abre corretamente ao clicar na tabela principal

### Log de Erro
```
[DEBUG ABRIR PDF EVENTO] ✅ Encontrou no banco
[DEBUG ABRIR PDF EVENTO] Tipo: CTe, Número: 22132
[DEBUG ABRIR PDF EVENTO] ❌ PDF não encontrado após verificar 0 pastas PDF
```

## 🔍 Causa Raiz

O código de abertura de PDFs em eventos estava utilizando uma lógica de busca **incorreta e desatualizada**:

```python
# ❌ CÓDIGO ANTIGO (INCORRETO)
for pasta_cert in xmls_root.iterdir():
    pdf_folder = pasta_cert / "PDF"  # ← Pasta "PDF" não existe!
    if pdf_folder.exists():
        for pdf_file in pdf_folder.glob("*.pdf"):
            if chave_vinculada in pdf_file.stem:
                pdf_encontrado = pdf_file
```

### Problemas da Abordagem Antiga
1. **Pasta inexistente**: Procurava em `xmls/{CNPJ}/PDF/`, estrutura que não é usada pelo sistema
2. **Ignorava estrutura por data**: Não considerava as pastas de ano-mês
3. **Ignorava estrutura por tipo**: Não considerava as pastas por tipo de documento (NFe, CTe, MDFe)
4. **Resultado**: 0 pastas PDF verificadas, nenhum arquivo encontrado

## ✅ Estrutura Correta de Armazenamento

O sistema organiza PDFs da seguinte forma:

```
xmls/
├── {CNPJ_INFORMANTE}/
│   ├── {ANO-MES}/
│   │   ├── {TIPO}/              ← Estrutura NOVA (padrão atual)
│   │   │   ├── {CHAVE}.pdf
│   │   │   └── {CHAVE}.xml
│   │   └── {CHAVE}.pdf          ← Estrutura ANTIGA (compatibilidade)
```

### Exemplos Reais

**Estrutura Nova (Preferencial):**
```
xmls/01773924000193/2026-01/CTE/35260148740351002109570000163878191764708610.pdf
xmls/33251845000109/2025-11/NFE/35251160433778000116550010002487861137250079.pdf
xmls/47539664000197/2025-12/MDFE/52251247539664000197580000001234561000123456.pdf
```

**Estrutura Antiga (Compatibilidade):**
```
xmls/01773924000193/2026-01/35260148740351002109570000163878191764708610.pdf
xmls/33251845000109/2025-11/35251160433778000116550010002487861137250079.pdf
```

## 🔧 Solução Implementada

O código foi atualizado para seguir **exatamente a mesma lógica** utilizada pela tabela principal, com 3 etapas de busca:

### Etapa 1: Busca Direta (Rápida)
```python
# Estrutura nova: xmls/{CNPJ}/{ANO-MES}/{TIPO}/{CHAVE}.pdf
specific_path = xmls_root / informante / year_month / tipo_normalized / f"{chave_vinculada}.pdf"

# Se não encontrar, tenta estrutura antiga
old_path = xmls_root / informante / year_month / f"{chave_vinculada}.pdf"
```

**Vantagens:**
- ⚡ Extremamente rápida (acesso direto ao arquivo)
- 🎯 Usa informações do banco (data_emissao, tipo, informante)
- ✅ Suporta estrutura nova e antiga

### Etapa 2: Busca Recursiva (Fallback)
```python
# Busca em todas as pastas de ano-mês
folders = list(sorted(pasta_informante.glob("20*"), reverse=True))
folders.extend(sorted(pasta_informante.glob("*/20*"), reverse=True))

for year_month_folder in folders[:20]:
    potential_pdf = year_month_folder / f"{chave_vinculada}.pdf"
    if potential_pdf.exists():
        pdf_encontrado = potential_pdf
        break
```

**Vantagens:**
- 🔄 Varre estrutura por data (mais recente primeiro)
- 📂 Suporta múltiplas estruturas de pasta
- 🛡️ Garante encontrar o arquivo mesmo em cenários incomuns

### Etapa 3: Geração de PDF (Último Recurso)
Se o PDF não for encontrado após as buscas, oferece gerar um novo PDF a partir do XML.

## 📊 Resultado da Correção

### Antes
```
[DEBUG ABRIR PDF EVENTO] ❌ PDF não encontrado após verificar 0 pastas PDF
```

### Depois
```
[DEBUG ABRIR PDF EVENTO] 🔍 Procurando PDF...
[DEBUG ABRIR PDF EVENTO] Chave: 35260148740351002109570000163878191764708610
[DEBUG ABRIR PDF EVENTO] Informante: 01773924000193
[DEBUG ABRIR PDF EVENTO] Tipo: CTE
[DEBUG ABRIR PDF EVENTO] Data emissão: 2026-01-06
[DEBUG ABRIR PDF EVENTO] 📁 Estrutura nova: xmls\01773924000193\2026-01\CTE\35260148740351002109570000163878191764708610.pdf
[DEBUG ABRIR PDF EVENTO] ✅ Encontrado (estrutura nova)!
```

## 🎯 Tipos de Documentos Suportados

A correção funciona para todos os tipos de documentos fiscais eletrônicos:

| Tipo | Descrição | Pasta |
|------|-----------|-------|
| NFe | Nota Fiscal Eletrônica | `NFE/` |
| NFCe | NF Consumidor Eletrônica | `NFCE/` |
| CTe | Conhecimento de Transporte Eletrônico | `CTE/` |
| MDFe | Manifesto de Documentos Fiscais Eletrônico | `MDFE/` |
| NFSe | Nota Fiscal de Serviço Eletrônica | `NFSE/` |

## 🔑 Pontos-Chave da Implementação

1. **Consistência**: Eventos e tabela principal usam a **mesma lógica** de busca
2. **Priorização**: Busca direta primeiro (rápida), recursiva depois (segura)
3. **Compatibilidade**: Suporta estrutura nova e antiga
4. **Debug**: Logs detalhados para diagnóstico de problemas
5. **Fallback**: Oferece gerar PDF se não encontrar

## 📝 Código Modificado

**Arquivo:** `Busca NF-e.py`  
**Método:** `_abrir_pdf_evento()`  
**Linhas:** ~4025-4075

### Principais Mudanças
- ❌ Removido: Busca em pasta `PDF/` inexistente
- ✅ Adicionado: Busca em `{ANO-MES}/{TIPO}/`
- ✅ Adicionado: Busca em `{ANO-MES}/` (estrutura antiga)
- ✅ Adicionado: Busca recursiva com limite de 20 pastas
- ✅ Adicionado: Logs de debug detalhados

## 🧪 Teste de Validação

**Documento Testado:** CTe 22132  
**Chave:** `35251156910992000149570010000221321005016216`  
**Localização:** `xmls/33251845000109/2025-11/CTE/35251156910992000149570010000221321005016216.pdf`  
**Resultado:** ✅ PDF localizado e aberto com sucesso

**Documento Testado 2:** CTe 16387819  
**Chave:** `35260148740351002109570000163878191764708610`  
**Localização:** `xmls/01773924000193/2026-01/CTE/35260148740351002109570000163878191764708610.pdf`  
**Resultado:** ✅ PDF localizado e aberto com sucesso na estrutura nova

## 🚀 Funcionalidades do Sistema de Eventos

### Duplo Clique em Eventos
- **Eventos Próprios**: Mostra mensagem informativa (não são documentos vinculados)
- **Documentos Vinculados**: Abre o PDF do documento (CTe, MDFe, etc.)

### Guias do Diálogo de Eventos
1. **Manifestações**: Ciência, confirmação, desconhecimento, operação não realizada
2. **Eventos**: Cancelamentos, cartas de correção, etc.
3. **Vínculos**: Documentos de transporte (CTe, MDFe) vinculados à NFe

### Formatação de Dados
- **Datas**: Formato brasileiro `dd/mm/aaaa - hh:mm:ss`
- **Duplicatas**: Removidas automaticamente por chave única
- **Ordenação**: Cronológica (eventos mais antigos primeiro)

## 📌 Histórico de Correções Relacionadas

| Data | Fase | Problema | Solução |
|------|------|----------|---------|
| Jan/2026 | Fase 17 | Documento errado após ordenar colunas | Busca dinâmica de coluna "Chave" |
| Jan/2026 | Fase 17 | Datas em formato ISO | Formatação brasileira |
| Jan/2026 | Fase 17 | Eventos duplicados | Sistema de chave única |
| Jan/2026 | Fase 17 | Eventos fora de ordem | Ordenação cronológica |
| Jan/2026 | Fase 17 | **PDF de CTe não encontrado** | **Busca por estrutura correta** ✅ |

## 🎓 Lições Aprendidas

1. **Sempre reutilizar lógica testada**: A tabela principal já tinha a solução correta
2. **Estrutura de pastas importa**: Documentação da estrutura evita erros
3. **Debug logging é essencial**: Identificou exatamente onde estava o problema (0 pastas verificadas)
4. **Testar com dados reais**: CTe expôs o problema que NFe não mostraria

---

**Status:** ✅ Resolvido  
**Data:** Janeiro 2026  
**Versão:** Fase 17 (Reformulação do Sistema de Eventos)
