# ✅ Checklist de Migração para Outro PC

## BOT - Busca NFE - Guia Completo de Transferência

---

## 📋 ANTES DE COMEÇAR

### ⚠️ Informações Importantes

- **Tempo estimado**: 30-45 minutos
- **Requer**: Acesso admin no novo PC
- **Internet**: Necessária para download de dependências
- **Certificado**: Tenha o arquivo .pfx e senha em mãos

---

## 🎯 PARTE 1: PREPARAÇÃO (PC ORIGEM)

### ✅ 1.1 - Fazer Backup dos Dados

Copie estes arquivos/pastas para pendrive ou nuvem:

```
✅ notas.db                    (Banco de dados com histórico)
✅ xmls/                       (XMLs baixados - opcional)
✅ api_credentials.csv         (Se usar NFS-e - opcional)
✅ Certificado .pfx            (Se não tiver cópia)
```

**NÃO copie:**
- ❌ `.venv/` (ambiente virtual - recriar no novo PC)
- ❌ `__pycache__/` (cache Python)
- ❌ `logs/` (logs antigos)
- ❌ `*.db-journal` (temporários)

---

### ✅ 1.2 - Anotar Configurações

Anote as seguintes informações:

```
CERTIFICADO:
- Caminho do arquivo .pfx: _______________________________
- Senha: _______________________________________________
- CNPJ/CPF titular: _____________________________________
- CNPJ informante: ______________________________________
- UF (código): __________________________________________

NUVEM FISCAL (se usar):
- Client ID: ____________________________________________
- Client Secret: ________________________________________

CONFIGURAÇÕES:
- Intervalo de busca (horas): ___________________________
- NSU atual: ____________________________________________
```

---

## 💻 PARTE 2: INSTALAÇÃO (PC NOVO)

### ✅ 2.1 - Verificar Requisitos

- [ ] Windows 10/11 (64-bit) OU Linux Ubuntu 20.04+
- [ ] Acesso admin ao sistema
- [ ] Conexão com internet estável
- [ ] 500MB de espaço em disco livre

---

### ✅ 2.2 - Instalar Python

#### Windows:

1. [ ] Baixe Python 3.10+ em: https://www.python.org/downloads/
2. [ ] **CRÍTICO**: Marque "Add Python to PATH"
3. [ ] Escolha "Install Now"
4. [ ] Abra CMD e teste:
   ```cmd
   python --version
   ```
   Deve mostrar: `Python 3.10.x` ou superior

#### Linux:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv python3-dev
sudo apt install libxml2-dev libxslt1-dev
python3 --version
```

---

### ✅ 2.3 - Baixar o Sistema

**Opção A - Copiar do PC antigo:**

1. [ ] Copie toda a pasta do sistema (sem `.venv/`)
2. [ ] Cole em local adequado (ex: `C:\BOT-Busca-NFE\`)

**Opção B - Baixar do repositório:**

```bash
# Se tiver Git
git clone <URL_REPOSITORIO> C:\BOT-Busca-NFE
cd C:\BOT-Busca-NFE
```

**Opção C - Download ZIP:**

1. [ ] Baixe o ZIP do sistema
2. [ ] Extraia para `C:\BOT-Busca-NFE\`

---

### ✅ 2.4 - Executar Instalador Automático

#### Windows:

```cmd
# Navegue até a pasta
cd C:\BOT-Busca-NFE

# Execute o instalador
instalar.bat
```

#### Linux:

```bash
# Navegue até a pasta
cd /caminho/para/BOT-Busca-NFE

# Torne executável
chmod +x instalar.sh

# Execute
./instalar.sh
```

**O instalador vai:**
- ✅ Criar ambiente virtual (`.venv/`)
- ✅ Atualizar pip
- ✅ Instalar todas as dependências
- ✅ Configurar o sistema

⏱️ **Aguarde 5-10 minutos**

---

### ✅ 2.5 - Verificar Instalação

```cmd
python verificar_instalacao.py
```

**Resultado esperado:**
```
✓ INSTALAÇÃO COMPLETA!

Todos os arquivos e dependências estão presentes.
```

**Se houver erros:**
- Verifique mensagens de erro
- Consulte seção "Solução de Problemas" abaixo
- Reinstale dependências: `pip install -r requirements.txt`

---

## 🔧 PARTE 3: CONFIGURAÇÃO

### ✅ 3.1 - Restaurar Dados (se fez backup)

1. [ ] Copie `notas.db` para a pasta do sistema
2. [ ] Copie `xmls/` (opcional - se quiser manter XMLs antigos)
3. [ ] Copie `api_credentials.csv` (se usar NFS-e)

---

### ✅ 3.2 - Configurar Certificado

1. [ ] Inicie o sistema:
   ```cmd
   python interface_pyqt5.py
   ```

2. [ ] Menu **Certificados** > **Adicionar Certificado**

3. [ ] Preencha com as informações anotadas:
   - **Caminho**: Selecione arquivo `.pfx` ou `.p12`
   - **Senha**: Digite a senha
   - **CNPJ/CPF**: CPF/CNPJ do titular
   - **Informante**: CNPJ que vai buscar (pode ser diferente)
   - **UF**: Código da UF (ex: 35 para SP, 33 para RJ)

4. [ ] Clique **Salvar**

5. [ ] Verifique se certificado aparece na lista

---

### ✅ 3.3 - Testar Busca

1. [ ] Clique no botão **"Buscar Notas"**

2. [ ] Aguarde (primeira busca pode demorar)

3. [ ] Verifique se notas aparecem na tabela

**Indicadores de sucesso:**
- ✅ Status bar mostra progresso
- ✅ Notas aparecem na tabela
- ✅ Log mostra "NSU avançou" ou "sincronizado"
- ✅ Pasta `xmls/` foi criada com XMLs

---

### ✅ 3.4 - Configurar Busca Automática (Opcional)

1. [ ] Menu **Tarefas** > **Configurações**

2. [ ] Configure:
   - **Intervalo**: Horas entre buscas (ex: 2 horas)
   - **Ativar**: Marque checkbox

3. [ ] Salve

**Sistema vai buscar automaticamente a cada X horas**

---

## 🧪 PARTE 4: TESTES

### ✅ 4.1 - Teste de Funcionalidades

- [ ] Buscar notas manualmente
- [ ] Duplo-clique em nota (gerar PDF)
- [ ] Filtrar por CNPJ
- [ ] Filtrar por data
- [ ] Visualizar eventos de uma nota
- [ ] Exportar para Excel (se disponível)

---

### ✅ 4.2 - Teste de Manifestação

1. [ ] Selecione uma nota não manifestada

2. [ ] Botão direito > **Manifestar Ciência**

3. [ ] Aguarde confirmação

4. [ ] Tente manifestar novamente a mesma nota

**Esperado:** Sistema deve avisar que já foi manifestada

---

## 🛠️ SOLUÇÃO DE PROBLEMAS

### ❌ Erro: "Python não encontrado"

**Solução:**
```cmd
# Verifique instalação
python --version

# Se não funcionar, reinstale Python
# IMPORTANTE: Marque "Add Python to PATH"
```

---

### ❌ Erro: "ModuleNotFoundError: No module named 'PyQt5'"

**Solução:**
```cmd
# Ative ambiente virtual
.venv\Scripts\activate

# Reinstale
pip install -r requirements.txt
```

---

### ❌ Erro: "lxml installation failed" (Linux)

**Solução:**
```bash
sudo apt install python3-dev libxml2-dev libxslt1-dev
pip install lxml
```

---

### ❌ Interface não abre

**Solução:**
```cmd
# Verifique erros no terminal
python interface_pyqt5.py

# Reinstale PyQt5
pip uninstall PyQt5
pip install PyQt5
```

---

### ❌ Certificado inválido

**Solução:**
- Verifique se arquivo `.pfx` é acessível
- Confirme senha está correta
- Certifique-se que certificado está dentro da validade
- Tente exportar certificado novamente (ICP-Brasil)

---

### ❌ Firewall bloqueia conexão SEFAZ

**Solução Windows:**
1. Painel de Controle > Firewall
2. Permitir aplicativo
3. Adicione Python.exe:
   ```
   C:\BOT-Busca-NFE\.venv\Scripts\python.exe
   ```

**Solução Linux:**
```bash
sudo ufw allow out 443/tcp
sudo ufw allow out 80/tcp
```

---

## 📞 CHECKLIST FINAL

### ✅ Verificação Completa

- [ ] Python 3.10+ instalado
- [ ] Ambiente virtual criado (`.venv/`)
- [ ] Dependências instaladas (sem erros)
- [ ] `verificar_instalacao.py` passou
- [ ] Certificado configurado e válido
- [ ] Primeira busca executada com sucesso
- [ ] Notas aparecem na interface
- [ ] PDF é gerado ao clicar 2x
- [ ] Manifestação funciona
- [ ] Sistema não dá erro ao fechar

---

## 💾 BACKUP CONTÍNUO

### Dados Importantes

Faça backup regular de:

```
✅ notas.db                  (Banco de dados)
✅ xmls/                     (XMLs baixados)
✅ api_credentials.csv       (Credenciais)
✅ Certificado .pfx          (Certificado digital)
```

**Frequência sugerida:** Semanal

**Métodos:**
- Cópia manual para nuvem (Google Drive, OneDrive)
- Cópia para pendrive
- Backup automático Windows/Linux

---

## 🎓 PRÓXIMOS PASSOS

Após instalação bem-sucedida:

1. [ ] Leia [MANIFESTACAO_AUTOMATICA.md](MANIFESTACAO_AUTOMATICA.md)
2. [ ] Configure busca automática
3. [ ] Configure exportação Excel (se necessário)
4. [ ] Treine usuários no sistema
5. [ ] Estabeleça rotina de backup

---

## 📋 RESUMO RÁPIDO

```
1. Instalar Python 3.10+  (marcar "Add to PATH")
2. Copiar arquivos do sistema
3. Executar: instalar.bat (Windows) ou instalar.sh (Linux)
4. Executar: python verificar_instalacao.py
5. Iniciar: python interface_pyqt5.py
6. Adicionar certificado digital
7. Fazer primeira busca
8. Pronto! 🎉
```

---

## ⏱️ TEMPO ESTIMADO POR ETAPA

| Etapa | Tempo |
|-------|-------|
| Backup dados (PC antigo) | 5 min |
| Instalar Python | 10 min |
| Copiar sistema | 5 min |
| Executar instalador | 10 min |
| Configurar certificado | 5 min |
| Testar sistema | 10 min |
| **TOTAL** | **45 min** |

---

## 🏆 CONCLUSÃO

Seguindo este checklist, você terá o sistema funcionando perfeitamente no novo PC!

**Em caso de dúvidas:**
- Consulte logs em `logs/`
- Execute `python verificar_instalacao.py`
- Revise a documentação em [INSTALACAO.md](INSTALACAO.md)

---

**Versão do Checklist:** 1.0  
**Última atualização:** 18/12/2025  
**Compatível com:** BOT - Busca NFE v2.0+
