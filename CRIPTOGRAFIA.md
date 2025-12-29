# 🔒 Criptografia de Senhas - Guia Rápido

## ✅ Status Atual

**Sistema PROTEGIDO com criptografia AES-128**

- ✅ Senhas de certificados criptografadas no banco de dados
- ✅ Chave de criptografia única por usuário/máquina
- ✅ Descriptografia automática ao carregar certificados
- ✅ Backup criado antes da migração

---

## 🔑 Arquivos Importantes

### Chave de Criptografia
```
%USERPROFILE%\.bot_nfe\key.bin
```
**⚠️ IMPORTANTE:** Este arquivo é CRÍTICO para o sistema funcionar. Se perdê-lo, as senhas não poderão ser recuperadas!

### Banco de Dados
```
notas.db  - Senhas CRIPTOGRAFADAS
notas_backup_*.db - Backup com senhas em texto claro (SE DESEJAR, PODE DELETAR)
```

---

## 🔐 Como Funciona

### 1. Salvar Certificado
```python
# Interface salva senha normalmente
db.save_certificate({
    'senha': 'minha_senha_123',  # ← Texto claro
    ...
})

# DatabaseManager criptografa automaticamente
# Salva no banco: gAAAAABpRBcs7zB1nWKF... (criptografado)
```

### 2. Carregar Certificado
```python
# DatabaseManager descriptografa automaticamente
certs = db.load_certificates()

# Retorna senha descriptografada
print(certs[0]['senha'])  # ← 'minha_senha_123' (texto claro)
```

---

## 🛡️ Segurança Implementada

### O que está protegido:
- ✅ **Senhas de certificados** - Criptografadas com AES-128
- ✅ **Chave de criptografia** - Armazenada com permissões restritas
- ✅ **Descriptografia automática** - Transparente para o usuário

### O que NÃO está protegido (ainda):
- ⚠️ **Código-fonte** - Python em texto claro
- ⚠️ **Banco de dados** - SQLite sem criptografia (apenas senhas)
- ⚠️ **Logs** - Podem conter informações sensíveis

Para proteção completa, consulte [SEGURANCA.md](SEGURANCA.md).

---

## 🔧 Migração Realizada

### O que foi feito:

1. ✅ Criado módulo `modules/crypto_utils.py`
2. ✅ Modificado `modules/database.py` para criptografar/descriptografar
3. ✅ Executado `migrate_encrypt_passwords.py`
4. ✅ Testado descriptografia
5. ✅ Verificado funcionamento do sistema

### Resultado:
- 5 certificados migrados
- 0 erros
- Senhas agora criptografadas: `gAAAAABp...`

---

## 🚨 Importante

### ⚠️ Backup da Chave de Criptografia

**RECOMENDAÇÃO:** Faça backup do arquivo de chave em local seguro:

```bash
# Windows
copy %USERPROFILE%\.bot_nfe\key.bin "D:\Backup Seguro\key.bin"

# Linux/Mac
cp ~/.bot_nfe/key.bin ~/backup_seguro/key.bin
```

### ⚠️ Ao Migrar Sistema para Outro PC

Para que o sistema funcione em outro PC, você precisa:

**Opção 1: Copiar a chave (RECOMENDADO)**
```bash
# Copiar chave do PC antigo para o novo
# PC Antigo: %USERPROFILE%\.bot_nfe\key.bin
# PC Novo:   %USERPROFILE%\.bot_nfe\key.bin
```

**Opção 2: Recadastrar certificados**
```
1. Não copiar a chave
2. Sistema criará nova chave
3. Recadastrar certificados manualmente
```

---

## 🧪 Testes

### Testar Criptografia
```bash
python modules/crypto_utils.py
```

### Testar Carregamento de Certificados
```bash
python test_crypto.py
```

### Ver Senhas Criptografadas no Banco
```bash
python -c "import sqlite3; conn = sqlite3.connect('notas.db'); cur = conn.execute('SELECT informante, substr(senha, 1, 50) FROM certificados'); [print(f'{row[0]}: {row[1]}...') for row in cur]"
```

---

## 📊 Antes vs Depois

### Antes (Texto Claro)
```sql
SELECT senha FROM certificados WHERE id = 1;
-- Resultado: 967********  ← VISÍVEL
```

### Depois (Criptografado)
```sql
SELECT senha FROM certificados WHERE id = 1;
-- Resultado: gAAAAABpRBcs7zB1nWKFQflo2_1KEFMzvwm2YXiRh05F6ozyv0...  ← PROTEGIDO
```

---

## ❓ FAQ

### Q: As senhas antigas ainda funcionam?
**A:** Sim! O sistema descriptografa automaticamente.

### Q: Preciso fazer algo diferente ao usar o sistema?
**A:** Não. Tudo funciona igual, mas agora protegido.

### Q: E se eu perder o arquivo `key.bin`?
**A:** As senhas não poderão ser recuperadas. Você precisará recadastrar os certificados.

### Q: Posso deletar os backups `notas_backup_*.db`?
**A:** Sim, após confirmar que tudo funciona. ANTES, verifique se não precisa deles.

### Q: Como ver a senha de um certificado?
**A:** Use a interface normalmente. O sistema descriptografa automaticamente.

### Q: A criptografia deixa o sistema mais lento?
**A:** Não. O impacto é imperceptível (<1ms por operação).

---

## 🎉 Conclusão

Seu sistema agora está **PROTEGIDO** contra acesso não autorizado às senhas!

- Senhas criptografadas com AES-128
- Chave única por usuário/máquina
- Funcionamento transparente

Para proteção adicional (código-fonte, banco completo), consulte [SEGURANCA.md](SEGURANCA.md).

---

**Implementado em:** 18/12/2025  
**Migração executada:** ✅ Sucesso (5 certificados)  
**Próximos passos:** Consultar [SEGURANCA.md](SEGURANCA.md) para proteção completa
