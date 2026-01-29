# 🧪 Testes Unitários

Testes automatizados de componentes individuais do sistema.

## 📋 Testes Disponíveis

### API e Integração
- `test_nfse_direto.py` - Teste direto da API NFS-e
- `test_adn_api.py` - Teste API ADN (Ambiente Nacional)
- `test_adn_endpoints.py` - Teste endpoints ADN
- `teste_nuvem_fiscal_integracao.py` - Integração Nuvem Fiscal

### Funcionalidades do Sistema
- `test_busca_logs.py` - Teste do sistema de logs
- `test_crypto.py` - Teste de criptografia
- `test_cte.py` - Teste de CT-e
- `test_numeric_sort.py` - Teste de ordenação numérica
- `test_table_sorting.py` - Teste de ordenação de tabelas

### Scripts de Execução
- `run_test.py` - Runner principal de testes
- `nfe_search_test.py` - Testes do motor de busca

## 🚀 Como Executar

### Executar Todos os Testes
```bash
python run_test.py
```

### Executar Teste Específico
```bash
# Teste NFS-e
python test_nfse_direto.py

# Teste API ADN
python test_adn_api.py

# Teste Criptografia
python test_crypto.py
```

## 📝 Convenções

- **test_*.py** - Testes unitários puros
- **teste_*.py** - Testes de integração (movidos para ../integration/)
- Usar `pytest` quando possível
- Incluir docstrings explicativas
- Mock de APIs externas quando necessário

## ✅ Checklist de Qualidade

Antes de fazer commit:

- [ ] Todos os testes passando
- [ ] Cobertura > 80% (quando aplicável)
- [ ] Sem warnings ou erros
- [ ] Documentação atualizada
- [ ] Mocks apropriados para APIs

## 🔗 Links Relacionados

- [Testes de Integração](../integration/)
- [Scripts de Verificação](../verification/)
- [README Principal](../README.md)
