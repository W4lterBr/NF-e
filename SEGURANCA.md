# 🔒 Guia de Segurança - BOT Busca NFE

## ⚠️ AVISO IMPORTANTE

Este sistema **NÃO está protegido** contra engenharia reversa por padrão.

---

## 🔓 Vulnerabilidades Atuais

### 1. Código Python em Texto Puro
- **Risco**: Qualquer pessoa pode ler o código-fonte
- **Impacto**: Lógica de negócio exposta, algoritmos visíveis
- **Mitigação**: Veja seção "Compilação e Ofuscação"

### 2. Senhas em Texto Claro (CRÍTICO)
```sql
-- Banco de dados: notas.db
-- Tabela: certificados_sefaz
-- Campo: senha ← TEXTO CLARO!
```
- **Risco**: Senha do certificado digital acessível
- **Impacto**: Acesso não autorizado ao certificado .pfx
- **Mitigação**: Veja seção "Criptografia de Dados"

### 3. Credenciais da API Expostas
```csv
# Arquivo: api_credentials.csv
client_id,client_secret
XXXX,YYYY ← TEXTO CLARO!
```
- **Risco**: Client Secret da Nuvem Fiscal exposto
- **Impacto**: Uso não autorizado da API
- **Mitigação**: Veja seção "Gestão de Credenciais"

### 4. Banco de Dados Desprotegido
- **Risco**: Arquivo `notas.db` SQLite sem criptografia
- **Impacto**: Acesso a todo histórico de notas
- **Mitigação**: Veja seção "Criptografia de Banco"

### 5. Logs com Informações Sensíveis
- **Risco**: Logs podem conter tokens e respostas completas
- **Impacto**: Exposição de dados fiscais
- **Mitigação**: Veja seção "Logs Seguros"

---

## 🛡️ Níveis de Proteção

### 🟢 NÍVEL 1: Básico (Implementação Imediata)

#### 1.1 Criptografia de Senhas no Banco

**Implementação:**
```python
# modules/crypto_utils.py
from cryptography.fernet import Fernet
from pathlib import Path
import os

class CryptoManager:
    """Gerenciador de criptografia para dados sensíveis"""
    
    def __init__(self):
        self.key_file = Path.home() / '.bot_nfe' / 'key.bin'
        self.key = self._load_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """Carrega ou cria chave de criptografia"""
        if self.key_file.exists():
            return self.key_file.read_bytes()
        
        # Cria nova chave
        key = Fernet.generate_key()
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)
        
        # Protege arquivo (Windows)
        try:
            import win32security
            import ntsecuritycon as con
            
            # Remove permissões de outros usuários
            sd = win32security.GetFileSecurity(
                str(self.key_file),
                win32security.DACL_SECURITY_INFORMATION
            )
            dacl = win32security.ACL()
            # Apenas usuário atual
            sid = win32security.GetTokenInformation(
                win32security.OpenProcessToken(
                    win32api.GetCurrentProcess(),
                    win32security.TOKEN_QUERY
                ),
                win32security.TokenUser
            )[0]
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_ALL_ACCESS,
                sid
            )
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                str(self.key_file),
                win32security.DACL_SECURITY_INFORMATION,
                sd
            )
        except ImportError:
            # Linux: chmod 600
            os.chmod(self.key_file, 0o600)
        
        return key
    
    def encrypt(self, data: str) -> str:
        """Criptografa string"""
        if not data:
            return ""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Descriptografa string"""
        if not encrypted_data:
            return ""
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception:
            return ""  # Senha já descriptografada ou inválida

# Uso no código:
crypto = CryptoManager()

# Ao salvar certificado:
senha_criptografada = crypto.encrypt(senha)
conn.execute(
    "INSERT INTO certificados_sefaz (senha) VALUES (?)",
    (senha_criptografada,)
)

# Ao carregar certificado:
senha_criptografada = row[2]
senha_real = crypto.decrypt(senha_criptografada)
```

**Benefícios:**
- ✅ Senhas protegidas no banco
- ✅ Chave única por usuário/máquina
- ✅ Fácil implementação

**Limitações:**
- ⚠️ Chave ainda está no disco
- ⚠️ Admin do PC pode acessar

---

#### 1.2 Proteger Credenciais da API

**Implementação:**
```python
# Usar variáveis de ambiente em vez de CSV
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('NUVEM_FISCAL_CLIENT_ID')
CLIENT_SECRET = os.getenv('NUVEM_FISCAL_CLIENT_SECRET')

# Arquivo .env (não versionar!)
# NUVEM_FISCAL_CLIENT_ID=seu_client_id
# NUVEM_FISCAL_CLIENT_SECRET=seu_secret

# .gitignore
.env
api_credentials.csv
```

**Benefícios:**
- ✅ Credenciais fora do código
- ✅ Não vão para Git
- ✅ Fácil rotacionar

---

#### 1.3 Sanitizar Logs

**Implementação:**
```python
# modules/safe_logger.py
import re
import logging

class SensitiveDataFilter(logging.Filter):
    """Filtra dados sensíveis dos logs"""
    
    PATTERNS = [
        (r'<senha>.*?</senha>', '<senha>***</senha>'),
        (r'"senha"\s*:\s*"[^"]*"', '"senha":"***"'),
        (r'password=\w+', 'password=***'),
        (r'Authorization:\s*Bearer\s+\S+', 'Authorization: Bearer ***'),
        (r'\d{3}\.\d{3}\.\d{3}-\d{2}', '***.***.***-**'),  # CPF
        (r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', '**.***.***/****./**'),  # CNPJ
    ]
    
    def filter(self, record):
        message = record.getMessage()
        for pattern, replacement in self.PATTERNS:
            message = re.sub(pattern, replacement, message)
        record.msg = message
        return True

# Usar:
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())
```

---

### 🟡 NÍVEL 2: Intermediário (Compilação)

#### 2.1 Compilar com PyInstaller

**Instalação:**
```bash
pip install pyinstaller
```

**Compilação:**
```bash
# Executável único
pyinstaller --onefile --windowed --icon=Icone/xml.png interface_pyqt5.py

# Com proteção adicional
pyinstaller --onefile --windowed \
    --key "SUA_CHAVE_SECRETA_32_BYTES" \
    --icon=Icone/xml.png \
    --name "BOT_Busca_NFE" \
    interface_pyqt5.py
```

**Benefícios:**
- ✅ Código Python compilado em bytecode
- ✅ Mais difícil de descompilar
- ✅ Executável único

**Limitações:**
- ⚠️ Bytecode ainda pode ser extraído
- ⚠️ Ferramentas como `pyinstxtractor` + `uncompyle6`

---

#### 2.2 Ofuscação de Código

**Instalação:**
```bash
pip install pyarmor
```

**Ofuscação:**
```bash
# Ofuscar todo o projeto
pyarmor gen --recursive --output dist/ *.py modules/*.py

# Ofuscação avançada com proteção
pyarmor gen --restrict --enable-jit \
    --pack dist/interface_pyqt5.exe \
    interface_pyqt5.py
```

**Benefícios:**
- ✅ Código muito difícil de ler
- ✅ Nomes de variáveis ofuscados
- ✅ Controle de flow modificado

**Limitações:**
- ⚠️ Performance pode diminuir (~10-30%)
- ⚠️ Debugging mais difícil

---

### 🔴 NÍVEL 3: Avançado (Proteção Profissional)

#### 3.1 Criptografia de Banco de Dados

**Opção A: SQLCipher**
```bash
pip install sqlcipher3
```

```python
# Usar SQLCipher em vez de SQLite
import sqlcipher3 as sqlite3

conn = sqlite3.connect('notas.db')
conn.execute("PRAGMA key='SUA_SENHA_FORTE_AQUI'")
```

**Opção B: Criptografia de Arquivo**
```python
from cryptography.fernet import Fernet

# Ao fechar aplicativo: criptografar DB
cipher = Fernet(key)
with open('notas.db', 'rb') as f:
    encrypted = cipher.encrypt(f.read())
with open('notas.db.enc', 'wb') as f:
    f.write(encrypted)
os.remove('notas.db')

# Ao iniciar: descriptografar
with open('notas.db.enc', 'rb') as f:
    decrypted = cipher.decrypt(f.read())
with open('notas.db', 'wb') as f:
    f.write(decrypted)
```

---

#### 3.2 Hardware Token / Dongle

**Implementação:**
```python
import usb.core

class HardwareProtection:
    """Proteção via USB Dongle"""
    
    VENDOR_ID = 0x1234  # ID do fabricante
    PRODUCT_ID = 0x5678
    
    def check_dongle(self) -> bool:
        """Verifica se dongle USB está presente"""
        device = usb.core.find(
            idVendor=self.VENDOR_ID,
            idProduct=self.PRODUCT_ID
        )
        return device is not None
    
    def get_license_key(self) -> str:
        """Lê chave de licença do dongle"""
        device = usb.core.find(...)
        # Ler dados do dispositivo
        key = device.read(...)
        return key

# No início do app:
hw = HardwareProtection()
if not hw.check_dongle():
    QMessageBox.critical(None, "Erro", "Dongle não encontrado!")
    sys.exit(1)
```

**Benefícios:**
- ✅ Proteção física contra cópia
- ✅ Licenciamento por hardware
- ✅ Muito difícil de contornar

**Desvantagens:**
- ⚠️ Custo de hardware (~R$ 50-200 por dongle)
- ⚠️ Usuário precisa do dispositivo

---

#### 3.3 Servidor de Licença

**Arquitetura:**
```python
# API de licenciamento (FastAPI)
from fastapi import FastAPI, HTTPException
import hashlib
import datetime

app = FastAPI()

LICENSES = {
    "CNPJ1": {
        "key": "abc123",
        "expiry": "2026-12-31",
        "machine_id": "HASH_PC_1"
    }
}

@app.post("/validate")
async def validate_license(cnpj: str, machine_id: str, key: str):
    lic = LICENSES.get(cnpj)
    
    if not lic:
        raise HTTPException(403, "Licença inválida")
    
    if lic['key'] != key:
        raise HTTPException(403, "Chave incorreta")
    
    if lic['machine_id'] != machine_id:
        raise HTTPException(403, "Máquina não autorizada")
    
    if datetime.date.fromisoformat(lic['expiry']) < datetime.date.today():
        raise HTTPException(403, "Licença expirada")
    
    return {"valid": True}

# No cliente (aplicativo):
import requests
import hashlib
import platform

def get_machine_id():
    """ID único da máquina"""
    import uuid
    mac = uuid.getnode()
    return hashlib.sha256(str(mac).encode()).hexdigest()

def check_license():
    response = requests.post('https://api.suaempresa.com/validate', json={
        'cnpj': '12345678000100',
        'machine_id': get_machine_id(),
        'key': 'abc123'
    })
    
    if response.status_code != 200:
        QMessageBox.critical(None, "Erro", "Licença inválida!")
        sys.exit(1)

# Verificar a cada inicialização + periodicamente
check_license()
```

**Benefícios:**
- ✅ Controle total de licenças
- ✅ Revogação remota
- ✅ Analytics de uso
- ✅ Amarração por máquina

---

#### 3.4 Code Signing (Assinatura Digital)

**Windows:**
```bash
# Certificado Code Signing (EV Certificate ~R$ 2.000/ano)
signtool sign /f certificado.pfx /p senha /t http://timestamp.digicert.com BOT_Busca_NFE.exe
```

**Benefícios:**
- ✅ Windows SmartScreen não bloqueia
- ✅ Usuários confiam mais
- ✅ Integridade verificável

---

## 📊 Comparação de Proteções

| Proteção | Dificuldade | Custo | Eficácia | Recomendado |
|----------|-------------|-------|----------|-------------|
| Senhas texto claro | 🔴 Nula | 💰 R$ 0 | 0% | ❌ NUNCA |
| Criptografia senhas | 🟢 Baixa | 💰 R$ 0 | 60% | ✅ MÍNIMO |
| PyInstaller | 🟡 Média | 💰 R$ 0 | 30% | ✅ Sim |
| Ofuscação (PyArmor) | 🟡 Média | 💰 R$ 0 | 70% | ✅ Sim |
| SQLCipher | 🟡 Média | 💰 R$ 0 | 80% | ✅ Sim |
| Dongle USB | 🔴 Alta | 💰💰 R$ 1k+ | 90% | ⚠️ Se comercial |
| Servidor Licença | 🔴 Alta | 💰💰 R$ 500+/mês | 95% | ⚠️ Se SaaS |
| Code Signing | 🟡 Média | 💰💰 R$ 2k/ano | 85% | ⚠️ Se distribuir |

---

## 🎯 Recomendação por Caso de Uso

### Uso Pessoal/Interno
```
✅ Criptografia de senhas
✅ PyInstaller básico
✅ .gitignore adequado
⚠️ Ofuscação opcional
```

### Distribuição para Clientes
```
✅ Criptografia completa (senhas + DB)
✅ PyInstaller + PyArmor
✅ Servidor de licença
✅ Code Signing
⚠️ Dongle se alto valor
```

### SaaS / Web
```
✅ Backend protegido
✅ API com autenticação
✅ Frontend pode ser exposto
✅ Rate limiting
✅ Logs de auditoria
```

---

## 🚀 Plano de Implementação Gradual

### Fase 1: Urgente (1 dia)
- [ ] Criptografar senhas no banco
- [ ] Mover credenciais para `.env`
- [ ] Atualizar `.gitignore`
- [ ] Sanitizar logs

### Fase 2: Curto Prazo (1 semana)
- [ ] Compilar com PyInstaller
- [ ] Ofuscar com PyArmor
- [ ] Implementar SQLCipher
- [ ] Testes de segurança

### Fase 3: Médio Prazo (1 mês)
- [ ] Servidor de licença
- [ ] Code Signing
- [ ] Documentação de segurança
- [ ] Treinamento usuários

---

## 🔍 Auditoria de Segurança

### Checklist de Verificação

**Dados em Repouso:**
- [ ] Senhas de certificados criptografadas
- [ ] Banco de dados criptografado
- [ ] Credenciais em variáveis de ambiente
- [ ] Logs não contêm dados sensíveis
- [ ] Arquivos temporários são limpos

**Código:**
- [ ] Ofuscado com PyArmor
- [ ] Compilado com PyInstaller
- [ ] Sem hardcoded secrets
- [ ] Sem comentários com senhas
- [ ] Validação de inputs

**Distribuição:**
- [ ] Executável assinado
- [ ] Licença implementada
- [ ] Verificação de integridade
- [ ] Atualizações seguras
- [ ] Documentação de segurança

**Runtime:**
- [ ] Verificação de depurador
- [ ] Anti-VM (se necessário)
- [ ] Logs de auditoria
- [ ] Tratamento seguro de erros
- [ ] Limpeza de memória

---

## 📞 Contato e Suporte

Em caso de dúvidas sobre segurança, consulte:

- Documentação oficial: [INSTALACAO.md](INSTALACAO.md)
- Exemplos: [exemplo_manifestacao.py](exemplo_manifestacao.py)

---

## ⚖️ Disclaimer Legal

**Este documento é fornecido apenas para fins educacionais.**

- A segurança de software é responsabilidade do desenvolvedor
- Nenhuma proteção é 100% inviolável
- Consulte profissionais de segurança para ambientes críticos
- Respeite leis de proteção de dados (LGPD, GDPR)

---

**Versão:** 1.0  
**Última atualização:** 18/12/2025  
**Status atual do sistema:** 🔴 DESPROTEGIDO (apenas .gitignore)
