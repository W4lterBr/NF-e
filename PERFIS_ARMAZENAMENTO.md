# 🗂️ Sistema de Perfis de Armazenamento Múltiplos

## 📋 O Que É?

O Sistema de Perfis permite que você configure **múltiplos locais de armazenamento** para seus XMLs e PDFs. Quando o sistema baixar arquivos, eles serão **automaticamente salvos em TODOS os perfis ativos** ao mesmo tempo!

## ✨ Benefícios

- ✅ **Backup Automático**: Salve em pasta local E pasta do contador simultaneamente
- ✅ **Organização Flexível**: Cada perfil pode ter formato de pasta diferente (AAAA-MM, MM-AAAA, etc.)
- ✅ **Sem Perda de Dados**: Arquivos já salvos não são apagados ao excluir perfis
- ✅ **Ativação/Desativação**: Desative temporariamente um perfil sem excluí-lo

## 🚀 Como Usar

### 1. Acessando Configurações

1. Clique no menu **"Configurações"** → **"Armazenamento"**
2. Você verá o **Perfil 1** já criado com suas configurações atuais

### 2. Visualizando Perfis

Na lista à esquerda, você verá:
- **✅ Perfil Ativo**: Com marca verde, arquivos serão salvos nele
- **⭕ Perfil Inativo**: Desativado temporariamente
- **⭐ Perfil Padrão**: O perfil principal do sistema

### 3. Criando Novo Perfil

1. Clique no botão **"➕ Novo Perfil"**
2. Digite um nome descritivo (ex: "Pasta do Contador", "Backup Nuvem")
3. O novo perfil será criado com as mesmas configurações do perfil atual
4. Edite as configurações conforme necessário:
   - **📝 Nome**: Identificação do perfil
   - **📂 Pasta Base**: Onde os arquivos serão salvos
   - **📅 Formato Mês**: Como organizar por mês (AAAA-MM, MM-AAAA, etc.)
   - **🗂️ XML/PDF**: Juntos ou em pastas separadas
   - **⚡ Status**: Ativo ou inativo
5. Clique em **"💾 Salvar Perfil"**

### 4. Editando Perfil Existente

1. Clique no perfil na lista à esquerda
2. Modifique as configurações desejadas
3. Clique em **"💾 Salvar Perfil"**

### 5. Desativando Perfil Temporariamente

1. Selecione o perfil
2. Desmarque **"✅ Perfil ativo"**
3. Salve
4. Arquivos NÃO serão mais salvos neste perfil (mas os existentes permanecem)

### 6. Excluindo Perfil

1. Selecione o perfil
2. Clique em **"🗑️ Excluir Perfil"**
3. Confirme a exclusão
4. **IMPORTANTE**: Arquivos já salvos **NÃO serão apagados**!

## 📦 Exemplo de Uso Prático

### Cenário: Empresa + Contador

**Perfil 1 (Empresa)**:
- Nome: "Arquivo Local da Empresa"
- Pasta: `C:\Empresa\Notas Fiscais`
- Formato: `AAAA-MM` (2025-01, 2025-02...)
- Status: ✅ Ativo

**Perfil 2 (Contador)**:
- Nome: "Pasta do Contador"
- Pasta: `\\Servidor\Contador\NFe`
- Formato: `MM-AAAA` (01-2025, 02-2025...)
- Status: ✅ Ativo

**Resultado**: Quando você baixar uma nota, ela será salva **automaticamente** em:
- `C:\Empresa\Notas Fiscais\33251845000109\2025-01\NFe\nota.xml`
- `\\Servidor\Contador\NFe\33251845000109\01-2025\NFe\nota.xml`

### Cenário: Local + Nuvem

**Perfil 1 (Local)**:
- Nome: "Backup Local"
- Pasta: `C:\XMLs`
- Status: ✅ Ativo

**Perfil 2 (Dropbox)**:
- Nome: "Sincronizar Dropbox"
- Pasta: `C:\Users\Usuario\Dropbox\NFe`
- Status: ✅ Ativo

**Perfil 3 (Google Drive)**:
- Nome: "Google Drive Backup"
- Pasta: `G:\Meu Drive\Notas Fiscais`
- Status: ⭕ Inativo (desativado temporariamente)

**Resultado**: Notas serão salvas no local E Dropbox, mas NÃO no Google Drive (inativo).

## 🔍 Perguntas Frequentes

### ❓ Posso ter quantos perfis?

Sim, **quantos quiser**! Não há limite de perfis.

### ❓ Todos os perfis precisam estar ativos?

Não! Você pode:
- Criar perfis e ativar apenas quando necessário
- Desativar temporariamente sem perder as configurações
- Manter perfis inativos como "templates" para uso futuro

### ❓ E se eu excluir um perfil?

- O perfil é **removido do sistema**
- Arquivos **JÁ SALVOS permanecem intactos**
- Novos arquivos **não serão mais salvos** naquele perfil

### ❓ Posso ter dois perfis na mesma pasta?

Tecnicamente sim, mas **não é recomendado**. Você terá arquivos duplicados.

### ❓ E se um perfil estiver em pasta de rede indisponível?

O sistema:
1. Tenta salvar em todos os perfis ativos
2. Se um perfil falhar (rede indisponível), **continua nos outros**
3. Exibe aviso no log sobre a falha
4. Nota é salva nos perfis disponíveis

### ❓ Preciso excluir o Perfil 1?

**NÃO!** O Perfil 1 foi criado com suas configurações atuais. Você pode:
- Mantê-lo como está
- Editar suas configurações
- Desativá-lo (mas manter pelo menos 1 perfil ativo)
- O sistema **exige pelo menos 1 perfil** para funcionar

### ❓ Como faço backup das configurações?

As configurações ficam no banco `notas.db`, tabela `perfis_armazenamento`. Faça backup regular do banco de dados.

## 🛠️ Informações Técnicas

### Estrutura do Banco de Dados

```sql
CREATE TABLE perfis_armazenamento (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    pasta_base TEXT NOT NULL,
    formato_pasta_mes TEXT DEFAULT 'AAAA-MM',
    xml_pdf_separado INTEGER DEFAULT 1,
    ativo INTEGER DEFAULT 1,
    is_default INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### Lógica de Salvamento

Quando um XML é baixado:

1. Sistema consulta `SELECT * FROM perfis_armazenamento WHERE ativo = 1`
2. Para cada perfil ativo:
   - Aplica formato de pasta do perfil
   - Cria estrutura de diretórios
   - Salva XML e PDF
3. Retorna caminho do primeiro perfil (principal)

### Migração Automática

Na primeira vez que você abrir as configurações após a atualização:
- Tabela `perfis_armazenamento` é criada automaticamente
- **Perfil 1** é gerado com suas configurações atuais
- Nada é perdido, tudo continua funcionando!

## 📝 Changelog

### v2.0 - Sistema de Perfis Múltiplos
- ✅ Tabela `perfis_armazenamento` criada
- ✅ Interface redesenhada com lista de perfis
- ✅ Salvamento simultâneo em múltiplos perfis
- ✅ CRUD completo de perfis (Criar, Ler, Editar, Excluir)
- ✅ Ativação/desativação de perfis
- ✅ Migração automática de configurações antigas

## 💡 Dicas Profissionais

1. **Backup Local + Remoto**: Sempre mantenha pelo menos 1 perfil local e 1 remoto
2. **Nomes Descritivos**: Use nomes claros como "Backup Contador - Janeiro" ou "Drive Empresa"
3. **Teste Antes**: Crie perfil de teste, baixe uma nota, confira se salvou correto
4. **Desative, Não Delete**: Se não usar temporariamente, desative em vez de excluir
5. **Organize por Propósito**: Crie perfis para diferentes necessidades (backup, contabilidade, auditoria)

## 🎯 Próximos Passos

1. ✅ Abra **Configurações** → **Armazenamento**
2. ✅ Veja o **Perfil 1** criado automaticamente
3. ✅ Clique em **"➕ Novo Perfil"** para adicionar mais
4. ✅ Configure pasta do contador, backup, etc.
5. ✅ Baixe uma nota e veja ela sendo salva em todos os perfis!

---

**Desenvolvido com ❤️ para facilitar sua gestão de documentos fiscais!**
