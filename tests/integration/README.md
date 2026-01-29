# 🔗 Testes de Integração

Testes que verificam a integração entre múltiplos componentes do sistema.

## 📋 Testes Disponíveis

### Integração com APIs Externas
- `teste_nuvem_fiscal_integracao.py` - Integração completa com Nuvem Fiscal
- Testes de comunicação SOAP/REST
- Validação de certificados mTLS

## 🚀 Como Executar

```bash
# Executar teste de integração
python teste_nuvem_fiscal_integracao.py
```

## ⚠️ Pré-requisitos

- ✅ Certificado digital válido
- ✅ Conexão com internet
- ✅ Credenciais configuradas (se necessário)
- ✅ Variáveis de ambiente configuradas

## 📝 Convenções

- **teste_*.py** - Testes de integração
- Podem acessar APIs reais (não mockadas)
- Tempo de execução mais longo que testes unitários
- Podem ser pulados em CI/CD se sem credenciais

## 🔒 Segurança

⚠️ **ATENÇÃO:**
- Nunca commitar credenciais reais
- Usar variáveis de ambiente
- Certificados de teste em ambiente próprio
- Logs não devem expor dados sensíveis

## 🔗 Links Relacionados

- [Testes Unitários](../unit/)
- [README Principal](../README.md)
