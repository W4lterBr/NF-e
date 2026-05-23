# 🚀 Guia de Instalação - Busca NFE

## 📋 Requisitos do Sistema

- **Sistema Operacional:** Windows 10/11 (64-bit)
- **Python:** 3.10, 3.11 ou 3.12
- **Espaço em disco:** ~500 MB para o projeto + dependências
- **RAM:** Mínimo 4GB (Recomendado 8GB)

---

## 📥 Instalação em Outro PC

### **Método 0: Instalação AUTOMÁTICA** ⭐ **NOVO!**

**O jeito mais fácil!** Script inteligente que detecta tudo automaticamente:

```bash
# 1. Extraia ou clone o projeto
# 2. Execute o instalador automático:
instalar_auto.bat
```

**Pronto!** O script faz tudo sozinho:
- ✅ Detecta Python automaticamente (py, python, python3, locais comuns)
- ✅ Verifica versão (3.10+)
- ✅ Cria ambiente virtual
- ✅ Instala todas as dependências
- ✅ Verifica pacotes críticos
- ✅ Sistema de retry (3 tentativas)

📖 **Documentação completa:** [README_INSTALADOR.md](README_INSTALADOR.md)

---

### **Método 1: Instalação Rápida (Manual)**

```bash
# 1. Clone ou extraia o projeto
git clone https://github.com/W4lterBr/NF-e.git
cd NF-e

# 2. Crie ambiente virtual
python -m venv .venv

# 3. Ative o ambiente virtual
.venv\Scripts\activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Execute o sistema
python "Busca NF-e.py"
```

---

### **Método 2: Instalação com Versões Exatas**

Use este método se precisar reproduzir o ambiente **exatamente** como está neste PC:

```bash
# Siga passos 1-3 do Método 1, depois:

# 4. Instale versões exatas
pip install -r requirements-frozen.txt

# 5. Execute o sistema
python "Busca NF-e.py"
```

---

### **Método 3: Instalador Executável (Usuário Final)**

Para usuários que **não precisam do ambiente de desenvolvimento**:

1. Baixe o instalador: `Output\Busca_XML_Setup_v1.0.96.exe`
2. Execute o instalador
3. Siga as instruções na tela
4. Pronto! O sistema está instalado e pronto para uso

---

## 🔧 Verificação da Instalação

Após instalar, verifique se tudo está correto:

```bash
# Com ambiente virtual ativado
python -c "import PyQt5, lxml, requests, cryptography; print('✅ Instalação OK!')"
```

Ou execute o script de verificação:

```bash
python verificar_instalacao.py
```

---

## 📦 Estrutura de Pastas Necessárias

O sistema criará automaticamente as pastas necessárias na primeira execução:

```
Busca NFE/
├── .venv/              # Ambiente virtual
├── modules/            # Módulos do sistema
├── Arquivo_xsd/        # Schemas XSD (incluído no projeto)
├── Icone/              # Ícones da interface (incluído no projeto)
├── xmls/               # XMLs baixados (criado automaticamente)
├── logs/               # Logs do sistema (criado automaticamente)
└── Output/             # PDFs gerados (criado automaticamente)
```

---

## 🐛 Problemas Comuns

### **Erro: "No module named 'PyQt5'"**

```bash
pip install PyQt5==5.15.11
```

### **Erro: "Microsoft Visual C++ 14.0 is required"**

1. Baixe: [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Instale apenas "Desktop development with C++"
3. Reinicie e tente novamente

### **Erro: "lxml installation failed"**

```bash
pip install --upgrade pip wheel
pip install lxml==5.2.2
```

---

## 🔐 Certificados Digitais

O sistema requer certificados digitais A1 (.pfx) para comunicação com a SEFAZ.

**Primeira execução:**
1. Abra o sistema
2. Menu **Configurações → Certificados**
3. Clique em **"Adicionar Certificado"**
4. Selecione seu arquivo `.pfx` e informe a senha

---

## 📚 Documentação Completa

- **Build:** [BUILD_README.md](BUILD_README.md)
- **Sistema:** [docs/sistema/DOCUMENTACAO_SISTEMA.md](docs/sistema/DOCUMENTACAO_SISTEMA.md)
- **Certificados:** [docs/certificados/CERTIFICADOS_README.md](docs/certificados/CERTIFICADOS_README.md)
- **Troubleshooting:** [docs/troubleshooting/](docs/troubleshooting/)

---

## 💻 Desenvolvimento

Para contribuir com o projeto:

```bash
# Instale dependências de desenvolvimento
pip install PyInstaller autopep8 pylint pytest

# Execute testes
pytest tests/

# Compile executável
.\build.bat
```

---

## 📞 Suporte

- **GitHub:** https://github.com/W4lterBr/NF-e
- **Issues:** https://github.com/W4lterBr/NF-e/issues
- **Documentação:** [docs/README.md](docs/README.md)

---

**Desenvolvido por:** DWM System Developer  
**Site:** https://dwmsystems.up.railway.app/  
**Versão:** 1.0.96  
**Última atualização:** 06/02/2026
