# 🧪 Ambiente de Teste - NF-e Homologação

Este diretório contém arquivos para testar a busca de NF-e/CT-e no **ambiente de homologação** da SEFAZ (tpAmb=2).

## ⚠️ IMPORTANTE

**NÃO use estes arquivos em produção!**

- Os documentos do ambiente de homologação NÃO têm validade fiscal
- Servem apenas para testes e desenvolvimento
- Use `nfe_search.py` (não `nfe_search_test.py`) para produção

## 📁 Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `nfe_search_test.py` | Versão modificada para homologação (tpAmb=2) |
| `run_test.py` | Script para executar os testes facilmente |
| `README_TEST.md` | Este arquivo (documentação) |

## 🔧 Como Usar

### 1. Executar Teste Simples

```powershell
python run_test.py
```

Este comando vai:
- ✅ Conectar aos servidores de homologação da SEFAZ
- ✅ Buscar documentos de teste usando seus certificados
- ✅ Salvar XMLs em `xmls_test/`
- ✅ Criar banco de dados separado `notas_test.db`
- ✅ Gerar log detalhado em `test_run.log`

### 2. Ver Logs Detalhados HTTP

```powershell
Get-Content test_run.log | Select-String "HTTP REQUEST|HTTP RESPONSE|🌐"
```

Isso mostrará todas as requisições HTTP feitas aos servidores da SEFAZ.

### 3. Verificar XMLs Baixados

```powershell
Get-ChildItem -Recurse xmls_test/
```

### 4. Consultar Banco de Dados de Teste

Use um visualizador SQLite para abrir `notas_test.db` e ver as notas processadas.

## 🔍 O Que Foi Modificado

Em relação ao `nfe_search.py` original:

### URLs Alteradas
```python
# PRODUÇÃO (nfe_search.py)
"https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"

# HOMOLOGAÇÃO (nfe_search_test.py)
"https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"
```

### Ambiente (tpAmb)
```xml
<!-- PRODUÇÃO -->
<tpAmb>1</tpAmb>

<!-- HOMOLOGAÇÃO -->
<tpAmb>2</tpAmb>
```

### Banco e Pastas
- **Produção**: `notas.db` + `xmls/`
- **Homologação**: `notas_test.db` + `xmls_test/`

## 🎯 Casos de Uso

### Testar Novos Certificados
Antes de usar um certificado novo em produção, teste aqui:
```powershell
python run_test.py
```

### Validar Alterações no Código
Antes de fazer deploy de mudanças no código:
1. Modifique `nfe_search_test.py`
2. Execute `python run_test.py`
3. Verifique se funciona corretamente
4. Só depois aplique as mudanças em `nfe_search.py`

### Debug de Problemas de Comunicação
Se estiver tendo problemas com a SEFAZ:
1. Execute no ambiente de teste
2. Analise os logs HTTP em `test_run.log`
3. Compare com o comportamento em produção

## 🚨 Limitações

1. **Documentos Falsos**: Os documentos no ambiente de homologação são apenas para teste
2. **Disponibilidade**: Servidores de homologação podem estar offline ou instáveis
3. **Dados**: Podem haver poucos ou nenhum documento disponível para seu CNPJ
4. **Performance**: Servidores de teste podem ser mais lentos

## 📊 Interpretando Resultados

### cStat Comuns

| Código | Significado |
|--------|-------------|
| 137 | Nenhum documento encontrado |
| 138 | Operação realizada (documentos baixados) |
| 656 | Consumo indevido (aguarde 1 hora) |

### Exemplo de Log Sucesso
```
🌐 [47539664000197] HTTP REQUEST Distribuição:
   📍 URL: https://hom.nfe.fazenda.gov.br/...
   📦 Método: POST (SOAP)
   📋 Payload: distDFeInt (ultNSU=000000000026923, cUF=52)

✅ [47539664000197] HTTP RESPONSE Distribuição recebida
   📊 cStat: 138
   📦 Documentos: 5 processados
```

## 🔐 Certificados

Você pode usar o **mesmo certificado** de produção para testes em homologação.
Não precisa de certificado especial de teste.

## 📝 Logs

### test_run.log
Log completo com todos os detalhes HTTP, parsing XML, etc.

### Ver apenas erros
```powershell
Get-Content test_run.log | Select-String "ERROR|ERRO|❌"
```

### Ver apenas sucessos
```powershell
Get-Content test_run.log | Select-String "INFO|✅"
```

## ❓ Perguntas Frequentes

### P: Posso usar isso com a interface gráfica?
**R:** Não diretamente. A interface usa `nfe_search.py`. Este é apenas para testes via linha de comando.

### P: Os XMLs de teste servem para contabilidade?
**R:** NÃO! São apenas para teste. Use apenas XMLs de produção (tpAmb=1).

### P: Como voltar para produção?
**R:** Use `nfe_search.py` normalmente. Os arquivos de teste não afetam produção.

### P: Recebi erro 656, e agora?
**R:** Normal. Aguarde 65 minutos antes de tentar novamente.

## 🆘 Suporte

Se encontrar problemas:
1. Verifique `test_run.log`
2. Compare com comportamento em produção
3. Verifique se certificado está válido
4. Confirme conexão com internet

## 📚 Referências

- [Manual de Integração NF-e](http://www.nfe.fazenda.gov.br/portal/principal.aspx)
- [NT 2014.002 - Distribuição DFe](http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=tnsYMik15F0=)
- [Ambientes de Homologação](http://www.nfe.fazenda.gov.br/portal/disponibilidade.aspx?versao=0.00&tipoConteudo=Iy/5Qol1YbE=)
