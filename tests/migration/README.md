# 🔄 Scripts de Migração

Scripts para migração de dados, correção e atualização de estruturas.

## 📋 Scripts Disponíveis

### Migração de Dados
- `migrate_encrypt_passwords.py` - Migra senhas para formato criptografado
- `migrate_to_portable.py` - Migra para versão portátil
- `run_migration.bat` - Runner de migrações (Windows)

### Correção de Dados
- `fix_informante.py` - Corrige campo informante
- `corrigir_informante.py` - Correção alternativa de informante

## 🚀 Como Usar

### Migração Completa
```bash
# Windows
run_migration.bat

# Python direto
python migrate_to_portable.py
```

### Migrações Específicas
```bash
# Criptografar senhas
python migrate_encrypt_passwords.py

# Corrigir informante
python fix_informante.py
```

## ⚠️ ATENÇÃO CRÍTICA

**Scripts de migração modificam dados permanentemente!**

### ✅ Checklist PRÉ-MIGRAÇÃO

- [ ] **BACKUP COMPLETO do banco de dados**
- [ ] **BACKUP de arquivos XML/PDF**
- [ ] **Testar em ambiente de desenvolvimento**
- [ ] **Ler logs de teste**
- [ ] **Verificar espaço em disco**
- [ ] **Fechar aplicação principal**

### 🛑 Comandos de Backup

```bash
# Backup do banco
copy notas.db notas.db.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2%

# Backup de XMLs (exemplo)
xcopy xmls\* xmls_backup\ /E /I /Y
```

## 📊 Processo de Migração

### 1. Preparação
```bash
# 1. Parar aplicação
# 2. Fazer backup
copy notas.db notas.db.backup

# 3. Verificar integridade
python ../verification/check_db.py
```

### 2. Execução
```bash
# 4. Executar migração
python migrate_to_portable.py

# 5. Verificar logs
type migration.log
```

### 3. Validação
```bash
# 6. Verificar resultado
python ../verification/check_db.py

# 7. Testar aplicação
python "../../Busca NF-e.py"
```

### 4. Rollback (se necessário)
```bash
# 8. Restaurar backup
copy /Y notas.db.backup notas.db
```

## 📝 Logs

Migrações geram logs detalhados:
- `migration.log` - Log principal
- `migration_errors.log` - Erros (se houver)
- Logs na pasta `logs/`

## 🔒 Segurança

- ✅ Senhas são criptografadas após migração
- ✅ Dados sensíveis protegidos
- ✅ Histórico mantido em backup
- ✅ Reversível (com backup)

## 🆘 Em Caso de Problemas

1. **Não entre em pânico**
2. **Restaure o backup:**
   ```bash
   copy /Y notas.db.backup notas.db
   ```
3. **Verifique os logs**
4. **Reporte o erro com logs anexados**

## 🔗 Links Relacionados

- [Scripts de Manutenção](../maintenance/)
- [Scripts de Verificação](../verification/)
- [README Principal](../README.md)
- [Documentação de Segurança](../../docs/sistema/SEGURANCA.md)
