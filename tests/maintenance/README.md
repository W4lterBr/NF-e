# 🔧 Scripts de Manutenção

Scripts para limpeza, organização e manutenção do sistema.

## 📋 Scripts Disponíveis

### Limpeza
- `limpar_protocolos.py` - Limpa protocolos antigos
- `remover_resumos_vazios.py` - Remove resumos sem dados

### Processamento
- `processar_eventos.py` - Processa eventos pendentes
- `listar_resumos.py` - Lista resumos disponíveis

## 🚀 Como Usar

### Limpeza
```bash
# Limpar protocolos
python limpar_protocolos.py

# Remover resumos vazios
python remover_resumos_vazios.py
```

### Processamento
```bash
# Processar eventos
python processar_eventos.py

# Listar resumos
python listar_resumos.py
```

## ⚠️ ATENÇÃO

**Scripts de manutenção podem modificar dados!**

- 🛑 **Faça backup antes** de executar
- 🔍 **Leia o código** antes de usar
- 📝 **Registre as ações** em log
- 🧪 **Teste em ambiente dev** primeiro

## 📊 Boas Práticas

1. **Sempre faça backup:**
   ```bash
   copy notas.db notas.db.backup
   ```

2. **Execute com cautela:**
   - Leia os logs gerados
   - Verifique resultados
   - Mantenha histórico

3. **Em produção:**
   - Agende para horários de baixo uso
   - Monitore execução
   - Tenha plano de rollback

## 🔗 Links Relacionados

- [Scripts de Migração](../migration/)
- [README Principal](../README.md)
