# 📦 Guia de Instalação - BOT Busca NFE

## Sistema de Busca e Gerenciamento de NF-e, CT-e e NFS-e

---

## 📋 Requisitos do Sistema

### Windows
- **Sistema Operacional**: Windows 10 ou 11 (64-bit)
- **Python**: 3.10 ou superior
- **RAM**: Mínimo 4GB (Recomendado 8GB)
- **Espaço em Disco**: 500MB livres
- **Internet**: Conexão estável para comunicação com SEFAZ

### Linux (Opcional)
- Ubuntu 20.04+, Debian 11+, ou distribuições compatíveis
- Python 3.10+
- Pacotes: `python3-dev`, `libxml2-dev`, `libxslt1-dev`

---

## 🚀 Instalação Passo a Passo

### 1️⃣ Instalar Python

#### Windows:
1. Baixe Python em: https://www.python.org/downloads/
2. **IMPORTANTE**: Marque a opção "Add Python to PATH"
3. Escolha "Install Now"
4. Verifique a instalação:
   ```cmd
   python --version
   ```

#### Linux:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
sudo apt install libxml2-dev libxslt1-dev  # Para lxml
```

---

### 2️⃣ Baixar o Sistema

**Opção A - Download ZIP:**
1. Baixe o arquivo ZIP do sistema
2. Extraia para uma pasta (ex: `C:\BOT-Busca-NFE\`)

**Opção B - Git (Recomendado):**
```bash
git clone <URL_DO_REPOSITORIO> C:\BOT-Busca-NFE
cd C:\BOT-Busca-NFE
```

---

### 3️⃣ Criar Ambiente Virtual

```cmd
# Windows (CMD)
cd C:\BOT-Busca-NFE
python -m venv .venv

# Ativar ambiente virtual
.venv\Scripts\activate
```

```bash
# Linux
cd /caminho/para/BOT-Busca-NFE
python3 -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate
```

**✅ Você verá `(.venv)` no início do prompt**

---

### 4️⃣ Instalar Dependências

```cmd
# Com ambiente virtual ATIVADO:
pip install --upgrade pip
pip install -r requirements.txt
```

**⏱️ Aguarde 5-10 minutos para instalação completa**

---

### 5️⃣ Verificar Instalação

Execute o script de verificação:

```cmd
python -c "import PyQt5; import lxml; import requests; import cryptography; print('✅ Todas as dependências instaladas com sucesso!')"
```

---

## 📁 Estrutura de Pastas Obrigatórias

O sistema criará automaticamente, mas você pode criar manualmente:

```
BOT-Busca-NFE/
├── modules/              # Módulos Python (OBRIGATÓRIO)
├── Arquivo_xsd/          # Schemas XSD para validação (OBRIGATÓRIO)
├── Icone/                # Ícones da interface (OBRIGATÓRIO)
│   └── xml.png
├── xmls/                 # XMLs baixados (CRIADO AUTOMATICAMENTE)
├── logs/                 # Logs do sistema (CRIADO AUTOMATICAMENTE)
├── .venv/                # Ambiente virtual Python
├── notas.db              # Banco de dados (CRIADO AUTOMATICAMENTE)
├── api_credentials.csv   # Credenciais Nuvem Fiscal (OPCIONAL)
└── requirements.txt      # Dependências Python
```

---

## 🔧 Configuração Inicial

### 1. Certificados Digitais

1. Inicie o sistema:
   ```cmd
   python interface_pyqt5.py
   ```

2. Vá em **Certificados > Adicionar Certificado**

3. Preencha:
   - **Caminho**: Selecione arquivo `.pfx` ou `.p12`
   - **Senha**: Senha do certificado
   - **CNPJ/CPF**: Titular do certificado
   - **Informante**: CNPJ que irá buscar notas (pode ser diferente)
   - **UF**: Estado (código UF, ex: 35 para SP)

4. Clique em **Salvar**

### 2. Credenciais Nuvem Fiscal (Opcional - para NFS-e)

Crie o arquivo `api_credentials.csv`:

```csv
Client ID,Client Secret
seu_client_id,seu_client_secret
```

---

## ▶️ Executando o Sistema

### Modo Interface Gráfica (Recomendado)

```cmd
# Ative o ambiente virtual primeiro
.venv\Scripts\activate

# Execute a interface
python interface_pyqt5.py
```

### Modo Terminal (Busca Automática)

```cmd
python nfe_search.py
```

---

## 🛠️ Solução de Problemas

### ❌ Erro: "ModuleNotFoundError: No module named 'PyQt5'"
**Solução:**
```cmd
# Verifique se o ambiente virtual está ativado
.venv\Scripts\activate

# Reinstale
pip install PyQt5
```

### ❌ Erro: "lxml installation failed"
**Windows - Solução:**
```cmd
# Baixe wheel pré-compilado:
pip install lxml --only-binary :all:
```

**Linux - Solução:**
```bash
sudo apt install python3-dev libxml2-dev libxslt1-dev
pip install lxml
```

### ❌ Erro: "No module named 'modules'"
**Solução:**
```cmd
# Certifique-se de estar no diretório correto
cd C:\BOT-Busca-NFE

# Verifique se a pasta modules existe
dir modules
```

### ❌ Erro certificado: "Unable to read certificate"
**Solução:**
1. Verifique se o arquivo `.pfx` ou `.p12` está acessível
2. Confirme se a senha está correta
3. Tente exportar o certificado novamente (ICP-Brasil)

### ❌ Interface não abre no Linux
**Solução:**
```bash
sudo apt install python3-pyqt5
export QT_QPA_PLATFORM=xcb
python interface_pyqt5.py
```

---

## 📊 Primeiros Passos Após Instalação

1. **Adicione um Certificado Digital** (Menu Certificados)
2. **Configure Intervalo de Busca** (Menu Tarefas)
3. **Execute Busca Manual** (Botão "Buscar Notas")
4. **Verifique XMLs Baixados** na pasta `xmls/`
5. **Gere PDFs** clicando 2x nas notas

---

## 🔄 Atualizações

### Manual:
1. Baixe nova versão
2. Substitua arquivos (MANTENHA `notas.db` e `xmls/`)
3. Reinstale dependências:
   ```cmd
   pip install -r requirements.txt --upgrade
   ```

### Git:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

## 📞 Suporte

### Logs do Sistema:
- Localização: `logs/busca_nfe_YYYY-MM-DD.log`
- Útil para diagnóstico de erros

### Informações do Sistema:
```cmd
python --version
pip list
```

---

## ⚠️ Avisos Importantes

1. **Certificado Digital**: 
   - Obrigatório para NF-e e CT-e
   - Deve estar dentro da validade
   - Tipo A1 (arquivo .pfx)

2. **Conexão Internet**:
   - Necessária para comunicação com SEFAZ
   - Firewall pode bloquear - libere Python

3. **Antivírus**:
   - Pode bloquear execução
   - Adicione pasta à lista de exceções

4. **Backup**:
   - Faça backup regular de `notas.db`
   - XMLs estão em `xmls/` - também fazer backup

---

## 📝 Licença

Este sistema é proprietário. Uso restrito conforme contrato.

---

## 🎯 Recursos Principais

- ✅ Busca automática NF-e (Distribuição DFe)
- ✅ Busca automática CT-e
- ✅ Busca NFS-e (múltiplos municípios)
- ✅ Geração de PDF de NF-e/CT-e
- ✅ Manifestação de eventos (Ciência, Confirmação, etc.)
- ✅ Controle anti-duplicata de manifestações
- ✅ Filtros avançados por CNPJ, data, valor
- ✅ Exportação para Excel/CSV
- ✅ Atualização automática
- ✅ Multi-certificado (matriz e filiais)

---

**Versão do Documento**: 2.0  
**Última Atualização**: 18/12/2025  
**Compatível com**: Python 3.10+ | Windows 10/11 | Linux Ubuntu 20.04+
