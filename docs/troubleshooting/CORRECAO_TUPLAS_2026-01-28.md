# 🔧 CORREÇÃO CRÍTICA - Problema de Tuplas no Salvamento de XMLs

**Data**: 2026-01-28  
**Severidade**: 🔴 CRÍTICA

## Resumo Executivo

Identificado e corrigido bug crítico que causava perda de ícones de XML na interface. A função `salvar_xml_por_certificado()` retornava tupla `(xml_path, pdf_path)`, mas código chamador esperava string, salvando representação de tupla no banco e quebrando auto-detecção.

## Correções Aplicadas

### Arquivos Modificados:
1. **Busca NF-e.py** (linhas 6181, 7215, 7274, 14543)
   - Manifestação automática
   - Busca por chave CT-e/NF-e
   - Reorganização de pastas

### Código Correto:
```python
# ✅ TRATAMENTO CORRETO DA TUPLA
resultado = salvar_xml_por_certificado(xml, cnpj)
caminho_xml = resultado[0] if isinstance(resultado, tuple) else resultado
db.registrar_xml(chave, cnpj, caminho_xml)  # Sempre string!
```

## Scripts de Correção

1. **corrigir_tuplas_caminhos.py** - Limpa tuplas do banco
2. **corrigir_forcado.py** - Atualiza xml_status

## Como Testar

```bash
# 1. Limpar tuplas do banco
python corrigir_tuplas_caminhos.py

# 2. Atualizar xml_status
python corrigir_forcado.py

# 3. Verificar na interface
# Ícones verdes devem aparecer para XMLs existentes
```

## Prevenção Futura

**Sempre extrair caminho da tupla antes de usar**:
```python
resultado = salvar_xml_por_certificado(...)
caminho = resultado[0] if isinstance(resultado, tuple) else resultado
```

Ver [FLUXO_SALVAMENTO_XMLS.md](FLUXO_SALVAMENTO_XMLS_DETALHADO.md) para documentação completa.
