# 📁 Sistema de Múltiplos Perfis de Armazenamento

## ✅ Status Atual

Você agora tem **2 perfis ativos**:

1. **Perfil #3**: Importação para Dominio
   - 📂 Pasta: `C:\Arquivo Walter - Empresas\Notas\DominioWeb`
   - 📅 Formato: MMAAAA (exemplo: 022026)
   - 🏗️ Estrutura: `CNPJ/022026/NFe/`
   - ⭐ **Padrão**: Sim

2. **Perfil #4**: Perfil NFs
   - 📂 Pasta: `C:\Arquivo Walter - Empresas\Notas\NFs`
   - 📅 Formato: MMAAAA (exemplo: 022026)
   - 🏗️ Estrutura: `CNPJ/022026/NFe/`
   - 📁 XML/PDF: Separados

---

## 🔄 Como Funciona

### 📥 **Buscando Novos XMLs** (Automático)

Quando você **buscar novos XMLs** (NF-e, CT-e, NFS-e, etc.), o sistema:

✅ Salva automaticamente em **TODOS os perfis ativos**

**Exemplo**:
```
Buscar XML → Sistema detecta 2 perfis ativos → Salva em:
   1. DominioWeb\CNPJ\022026\NFe\arquivo.xml
   2. NFs\CNPJ\022026\NFe\arquivo.xml + PDF
```

**✨ Você não precisa fazer nada!** O sistema salva automaticamente.

---

### 📋 **Copiando XMLs Existentes** (Manual)

Para copiar XMLs que já existem na pasta `xmls/` local:

1. Abra o programa **Busca NF-e**
2. Clique em **Menu → Configurações → Armazenamento**
3. Selecione o perfil desejado na lista
4. Clique no botão **"Aplicar Perfil (Copiar XMLs)"**

O sistema irá:
- Ler todos os XMLs da pasta `xmls/` local
- Copiar para o perfil selecionado
- Manter a estrutura correta (CNPJ/MÊS/TIPO)
- Preservar os arquivos originais

**⚠️ Importante**: 
- "Aplicar Perfil" copia apenas para **1 perfil por vez** (o selecionado)
- Se você tem 5 perfis, precisa aplicar em cada um separadamente
- XMLs **novos** serão salvos automaticamente nos 5 perfis

---

## 🎯 Cenários de Uso

### Cenário 1: Criar 5 Perfis Diferentes

```python
# Perfil 1: Pasta NFs
Pasta: C:\Arquivo Walter - Empresas\Notas\NFs
Estrutura: CNPJ/022026/NFe/

# Perfil 2: DominioWeb
Pasta: C:\Arquivo Walter - Empresas\Notas\DominioWeb
Estrutura: CNPJ/022026/NFe/

# Perfil 3: Backup Externo
Pasta: D:\Backup\XMLs
Estrutura: CNPJ/022026/NFe/

# Perfil 4: OneDrive
Pasta: C:\Users\...\OneDrive\Documentos\XMLs
Estrutura: CNPJ/022026/NFe/

# Perfil 5: Servidor de Rede
Pasta: \\SERVIDOR\XMLs
Estrutura: CNPJ/022026/NFe/
```

**Resultado**:
- Buscar 1 XML → Salvo automaticamente nos 5 locais
- Cada perfil pode ter formato de mês diferente
- Cada perfil pode ter estrutura diferente

---

### Cenário 2: Aplicar Perfil em XMLs Existentes

Você tem 10.000 XMLs em `xmls/` e quer copiar para o novo perfil:

1. Crie o novo perfil no menu Armazenamento
2. Configure a pasta e estrutura
3. Clique em **"Aplicar Perfil"**
4. Aguarde a cópia (pode demorar alguns minutos)

**📊 Progresso**: Barra de progresso mostra quantos arquivos foram copiados.

---

## 🛠️ Gerenciando Perfis

### Via Interface Gráfica (Recomendado)

**Menu → Configurações → Armazenamento**

Você pode:
- ➕ **Adicionar** novo perfil
- ✏️ **Editar** perfil existente
- 🗑️ **Excluir** perfil
- 📋 **Aplicar** perfil (copiar XMLs existentes)
- ⚡ **Ativar/Desativar** perfis

**Campos do Perfil**:
- **Nome**: Nome identificador (ex: "Backup Servidor")
- **Pasta Base**: Caminho completo da pasta
- **Formato Mês**: 
  - `MMAAAA` → 022026
  - `AAAA-MM` → 2026-02
  - `MM-AAAA` → 02-2026
- **Organização**: 
  - `Certificado → Tipo → Mês` (padrão)
  - `Tipo → Certificado → Mês` (novo)
- **XML/PDF**: Juntos ou Separados
- **Status**: Ativo/Inativo
- **Padrão**: Define perfil principal

---

### Via Scripts (Avançado)

#### Criar Novo Perfil
```python
python criar_perfil_nfs.py
```

#### Listar Todos os Perfis
```python
python listar_todos_perfis.py
```

#### Verificar Perfis Ativos
```python
python listar_perfis_ativos.py
```

#### Testar Salvamento Múltiplos Perfis
```python
python testar_multiperfis.py
```

---

## 📊 Estrutura de Pastas

### Organização: `CERTIFICADO_TIPO` (Padrão)

```
Pasta Base/
└── CERTIFICADO (ou CNPJ)/
    └── MÊS/
        └── TIPO/
            ├── XML/         (se separado)
            │   └── arquivo.xml
            └── PDF/         (se separado)
                └── arquivo.pdf

Exemplo:
DominioWeb/
└── 61-MATPARCG/
    └── 022026/
        └── NFe/
            ├── 000123-FORNECEDOR.xml
            └── 000123-FORNECEDOR.pdf
```

### Organização: `TIPO_CERTIFICADO` (Alternativa)

```
Pasta Base/
└── TIPO/
    └── CERTIFICADO/
        └── MÊS/
            ├── arquivo.xml
            └── arquivo.pdf

Exemplo:
DominioWeb/
└── NFe/
    └── 61-MATPARCG/
        └── 022026/
            ├── 000123-FORNECEDOR.xml
            └── 000123-FORNECEDOR.pdf
```

---

## 🎓 Perguntas Frequentes

### **P: Quantos perfis posso criar?**
**R**: Ilimitado! Você pode ter 5, 10, 50 perfis.

### **P: Posso desativar um perfil temporariamente?**
**R**: Sim! Edite o perfil e desmarque "Ativo". XMLs novos não serão mais salvos lá, mas os existentes permanecem.

### **P: Como sei se o XML foi salvo em todos os perfis?**
**R**: O log mostra: `✅ Perfil 'Nome': caminho\arquivo.xml` para cada perfil.

### **P: E se um perfil estiver em uma pasta de rede offline?**
**R**: O sistema registra erro no log, mas continua salvando nos outros perfis ativos.

### **P: Posso mudar a estrutura de um perfil depois?**
**R**: Sim, mas os arquivos existentes NÃO serão movidos automaticamente. Você precisaria reorganizar manualmente.

### **P: "Aplicar Perfil" apaga os XMLs da pasta original?**
**R**: **NÃO!** Ele apenas **COPIA**. Os originais em `xmls/` permanecem intactos.

### **P: Qual a diferença entre "Aplicar Perfil" e buscar novos XMLs?**
**R**: 
- **Aplicar Perfil**: Copia XMLs existentes para **1 perfil específico** (manual)
- **Buscar XMLs**: Salva XMLs novos em **TODOS os perfis ativos** (automático)

---

## 🚀 Próximos Passos

### 1. **Testar Sistema**
Execute: `python testar_multiperfis.py`

Verifique se o arquivo foi criado em:
- `DominioWeb\TESTE_MULTIPERFIS\022026\NFe\`
- `NFs\TESTE_MULTIPERFIS\022026\NFe\`

### 2. **Criar Mais Perfis (Opcional)**
Se você quer 5+ perfis, crie via interface ou script.

### 3. **Copiar XMLs Existentes**
Use "Aplicar Perfil" para copiar XMLs antigos para cada perfil novo.

### 4. **Buscar Novos XMLs**
Execute a busca normal. Os XMLs serão salvos automaticamente em todos os perfis ativos.

---

## 📝 Resumo Final

| **Ação** | **Comportamento** |
|----------|-------------------|
| Buscar novos XMLs | ✅ Salva em **TODOS os perfis ativos** automaticamente |
| Aplicar Perfil | 📋 Copia XMLs existentes para **1 perfil específico** |
| Criar perfil | ➕ Novo destino de salvamento |
| Desativar perfil | ⭕ XMLs novos não vão mais para lá |
| Excluir perfil | 🗑️ Remove do sistema (arquivos salvos permanecem) |

---

✅ **Sistema funcionando corretamente!**

- ✅ 2 perfis ativos (DominioWeb + NFs)
- ✅ Salvamento automático em múltiplos locais
- ✅ Estrutura correta: CNPJ → MÊS → TIPO
- ✅ Teste bem-sucedido

---

📧 **Dúvidas?** Consulte este documento ou execute os scripts de teste.
