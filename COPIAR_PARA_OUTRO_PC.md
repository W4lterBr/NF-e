# 📦 ARQUIVOS PARA INSTALAÇÃO EM OUTRO PC

## 📋 Checklist de Arquivos

### ✅ **Arquivos Essenciais (COPIAR OBRIGATORIAMENTE)**

```
✅ Busca NF-e.py                 (Aplicação principal)
✅ nfe_search.py                 (Motor de busca SEFAZ)
✅ nfse_search.py                (Busca NFS-e)
✅ updater_launcher.py           (Sistema de atualização)
✅ version.txt                   (Versão atual)
✅ requirements.txt              (Dependências flexíveis)
✅ requirements-frozen.txt       (Dependências exatas)
✅ INSTALACAO.md                 (Guia de instalação)
✅ instalar_auto.bat             ⭐ (Instalador INTELIGENTE - RECOMENDADO)
✅ instalar.bat                  (Script instalação Windows)
✅ executar.bat                  (Script execução rápida)
✅ verificar_instalacao.py       (Verificação do ambiente)
```

### 📁 **Pastas Essenciais**

```
✅ modules/                      (Todos os módulos Python)
✅ Arquivo_xsd/                  (Schemas XSD para validação)
✅ Icone/                        (Ícones da interface)
✅ docs/                         (Documentação completa)
```

### 📄 **Arquivos de Configuração (Opcional)**

```
⚠️  Logo.ico                     (Ícone do executável)
⚠️  Logo.png                     (Logo original)
⚠️  app.manifest                 (Manifest Windows)
⚠️  README.md                    (Documentação principal)
⚠️  BUILD_README.md              (Guia de build)
```

### ❌ **NÃO COPIAR (Gerados localmente)**

```
❌ .venv/                        (Ambiente virtual - recriar no destino)
❌ __pycache__/                  (Cache Python)
❌ build/                        (Build temporário)
❌ dist/                         (Executável compilado)
❌ Output/                       (PDFs gerados)
❌ xmls/                         (XMLs baixados - dados do usuário)
❌ logs/                         (Logs do sistema)
❌ notas.db                      (Banco de dados - dados do usuário)
❌ *.pyc                         (Arquivos compilados)
```

---

## 🚀 INSTALAR NO OUTRO PC

### **Passo 1: Copiar Projeto**

```bash
# Opção A: Clone do GitHub
git clone https://github.com/W4lterBr/NF-e.git
cd NF-e

# Opção B: Extrair ZIP
# Extrair arquivo do projeto para: C:\Busca NFE\
```

### **Passo 2: Instalação Automática** ⭐

```bash
# RECOMENDADO - Script INTELIGENTE (detecta Python automaticamente):
instalar_auto.bat

# Alternativo - Script simples:
instalar.bat

# Manual (se preferir):
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**O que o `instalar_auto.bat` faz:**
- ✅ Detecta Python automaticamente (py, python, python3, locais comuns)
- ✅ Verifica versão compatível (3.10+)
- ✅ Cria e valida ambiente virtual
- ✅ Atualiza pip automaticamente
- ✅ Instala dependências com retry (3 tentativas)
- ✅ Verifica pacotes críticos
- ✅ Relatório detalhado de progresso

### **Passo 3: Verificar Instalação**

```bash
python verificar_instalacao.py
```

### **Passo 4: Executar Sistema**

```bash
# Opção A: Atalho rápido
executar.bat

# Opção B: Manual
.venv\Scripts\activate
python "Busca NF-e.py"
```

---

## 📦 CRIAR PACOTE PARA DISTRIBUIÇÃO

### **Método 1: ZIP Completo (Desenvolvimento)**

Compactar apenas os arquivos essenciais:

```
Busca_NFE_v1.0.96_SOURCE.zip
├── *.py (todos os arquivos Python)
├── requirements*.txt
├── modules/
├── Arquivo_xsd/
├── Icone/
├── docs/
├── *.bat (scripts)
├── *.md (documentação)
└── version.txt
```

**Tamanho aproximado:** ~15-20 MB

### **Método 2: Instalador EXE (Usuário Final)**

Use o instalador já compilado:

```
Output\Busca_XML_Setup_v1.0.96.exe
```

**Tamanho aproximado:** ~50-60 MB  
**Vantagens:**
- ✅ Não precisa instalar Python
- ✅ Não precisa instalar dependências
- ✅ Interface de instalação profissional
- ✅ Desinstalador incluído

---

## 🔐 DADOS DO USUÁRIO

### **Backup Antes de Copiar**

Se já existe instalação anterior, faça backup de:

```
✅ notas.db                      (Banco de dados)
✅ xmls/                         (XMLs baixados)
✅ Output/                       (PDFs gerados)
✅ logs/                         (Logs - opcional)
```

### **Localização dos Dados (Executável)**

Quando instalado via `.exe`, os dados ficam em:

```
C:\Users\[USUARIO]\AppData\Roaming\Busca XML\
├── notas.db
├── logs/
└── (xmls/ e Output/ conforme configuração)
```

---

## 📋 REQUISITOS DO SISTEMA

- **SO:** Windows 10/11 (64-bit)
- **Python:** 3.10, 3.11 ou 3.12
- **RAM:** 4GB mínimo (8GB recomendado)
- **Disco:** 500 MB livres
- **Internet:** Conexão estável

---

## 🆘 SUPORTE

- **Documentação completa:** [INSTALACAO.md](INSTALACAO.md)
- **Guia de build:** [BUILD_README.md](BUILD_README.md)
- **GitHub Issues:** https://github.com/W4lterBr/NF-e/issues
- **Documentação técnica:** [docs/README.md](docs/README.md)

---

**Desenvolvido por:** DWM System Developer  
**Versão:** 1.0.96  
**Data:** 06/02/2026
