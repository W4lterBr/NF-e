# Guia de Solução de Problemas - Certificados

## 🚨 Erros Comuns ao Adicionar Certificados

### 1. "Certificado inválido ou senha incorreta"

**Possíveis causas:**
- ✗ Senha do certificado está incorreta
- ✗ Arquivo .pfx/.p12 está corrompido
- ✗ Arquivo não é um certificado válido

**Soluções:**
```
1. Verifique a senha:
   • Teste a senha em outro software (ex: navegador)
   • Certifique-se de que não há espaços extras
   • Verifique se Caps Lock está ativado

2. Verifique o arquivo:
   • Confirme que é um arquivo .pfx ou .p12
   • Baixe novamente se suspeitar de corrupção
   • Teste com outro certificado conhecido

3. Teste manual:
   • Abra o PowerShell/Terminal
   • Execute: certlm.msc (no Windows)
   • Tente importar manualmente
```

### 2. "Arquivo de certificado não encontrado"

**Soluções:**
```
1. Verifique o caminho:
   • Arquivo foi movido ou deletado?
   • Caminho contém caracteres especiais?
   • Permissões de acesso corretas?

2. Use caminho absoluto:
   • Exemplo: C:\Certificados\meu_cert.pfx
   • Evite caminhos relativos
```

### 3. "Senha do certificado é obrigatória"

**Soluções:**
```
1. Certificados .pfx sempre têm senha
2. Se não lembra a senha:
   • Verifique documentação do emissor
   • Entre em contato com quem gerou o certificado
   • Alguns certificados têm senha padrão (ex: "123456")
```

### 4. Módulo cryptography não disponível

**Erro:** `ImportError: No module named 'cryptography'`

**Solução:**
```bash
# Ativar ambiente virtual
.venv\Scripts\activate

# Instalar cryptography
pip install cryptography

# Verificar instalação
python -c "import cryptography; print('OK')"
```

### 5. Certificado aparece como "Expirado"

**Soluções:**
```
1. Verificar data do sistema:
   • Data/hora do computador está correta?
   • Fuso horário correto?

2. Renovar certificado:
   • Entre em contato com a Autoridade Certificadora
   • Gere um novo certificado
```

## 🔧 Testes de Diagnóstico

### Teste 1: Verificar Cryptography
```python
# Execute no terminal Python
import cryptography
print(f"Versão: {cryptography.__version__}")
```

### Teste 2: Validar Certificado Manualmente
```python
# Substitua pelos seus dados
from modules.certificate_manager import certificate_manager

result = certificate_manager.validate_certificate(
    r"C:\caminho\para\certificado.pfx", 
    "sua_senha"
)
print(f"Válido: {result[0]}")
if result[1]:
    print(f"CN: {result[1].cn}")
    print(f"CNPJ: {result[1].cnpj}")
    print(f"Válido até: {result[1].not_valid_after}")
```

### Teste 3: Verificar Arquivo
```bash
# No PowerShell (Windows)
Get-ChildItem "certificado.pfx" | Select-Object Name, Length, LastWriteTime

# Verificar se não está vazio
if ((Get-Item "certificado.pfx").Length -eq 0) { 
    Write-Host "Arquivo vazio!" 
}
```

## 🏥 Logs de Diagnóstico

### Ativar Logs Detalhados
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Agora execute a operação de certificado
# Logs aparecerão no terminal
```

### Locais de Log
- **Terminal/Console**: Mensagens em tempo real
- **Arquivo config/certificates.json**: Configurações salvas
- **Erros na interface**: Caixas de diálogo com detalhes

## 📞 Suporte Técnico

### Informações para Coleta (em caso de problema)
1. **Sistema operacional**: Windows/Linux/Mac + versão
2. **Versão Python**: `python --version`
3. **Versão cryptography**: `pip show cryptography`
4. **Erro exato**: Copie a mensagem completa
5. **Arquivo de teste**: Use um certificado de teste se possível

### Formatos Suportados
- ✅ `.pfx` (PKCS#12)
- ✅ `.p12` (PKCS#12)
- ❌ `.crt` (apenas para scan, não para validação)
- ❌ `.cer` (apenas para scan, não para validação)

### Certificados Testados
- ✅ Certificados A1 (arquivo)
- ⚠️ Certificados A3 (smartcard) - suporte limitado
- ✅ Certificados de teste ICP-Brasil
- ✅ Certificados comerciais (.pfx padrão)

## 🎯 Dicas Importantes

1. **Sempre faça backup** dos certificados originais
2. **Teste a senha** antes de adicionar no sistema
3. **Monitore a validade** - renovar antes do vencimento
4. **Use senhas seguras** mas memoráveis
5. **Mantenha os certificados seguros** - não compartilhe

---

## ✅ Lista de Verificação Rápida

Antes de reportar um problema, verifique:

- [ ] Arquivo .pfx existe e não está vazio
- [ ] Senha está correta (teste em outro software)
- [ ] Cryptography está instalado (`pip list | grep cryptography`)
- [ ] Certificado não está expirado
- [ ] Caminho do arquivo está correto
- [ ] Permissões de leitura no arquivo
- [ ] Data/hora do sistema correta

Se todos os itens estão OK e ainda há erro, colete os logs e entre em contato.