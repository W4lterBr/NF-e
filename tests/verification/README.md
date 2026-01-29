# ✅ Scripts de Verificação

Scripts não-destrutivos para verificar integridade e status do sistema.

## 📋 Scripts Disponíveis

### Verificação de Banco
- `check_db.py` - Verifica integridade do banco SQLite
- `check_cte_db.py` - Verifica CT-e no banco
- `check_resumo.py` - Verifica resumos
- `check_cert.py` - Verifica certificados

### Verificação de Sistema
- `verificar_informante.py` - Verifica campo informante
- `verificar_instalacao.py` - Verifica instalação completa
- `verificar_notas_emitidas.py` - Verifica notas emitidas
- `verificar_notas_incompletas.py` - Identifica notas incompletas

## 🚀 Como Usar

### Verificação Geral
```bash
# Verificar instalação
python verificar_instalacao.py

# Verificar banco de dados
python check_db.py
```

### Verificações Específicas
```bash
# Verificar CT-e
python check_cte_db.py

# Verificar resumos
python check_resumo.py

# Verificar certificados
python check_cert.py

# Verificar notas incompletas
python verificar_notas_incompletas.py
```

## ✅ Características

- ✅ **Não-destrutivos** - Apenas leitura
- ✅ **Seguros** - Não modificam dados
- ✅ **Rápidos** - Execução otimizada
- ✅ **Informativos** - Relatórios claros

## 📊 Saída Típica

```
✅ Banco de dados: OK
✅ Certificados: 3 válidos
⚠️  Notas incompletas: 5 encontradas
✅ Estrutura: Íntegra
```

## 🔗 Links Relacionados

- [Scripts de Análise](../analysis/)
- [README Principal](../README.md)
