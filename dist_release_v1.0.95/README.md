# Busca XML - v1.0.95 - Release Package

## 🔧 Correção Crítica - Ordem de Execução de Verificação

**IMPORTANTE**: Esta versão corrige definitivamente o erro "no such column: nsu" que causava crash na inicialização.

---

## 📦 Conteúdo do Pacote

Este pacote contém:

1. **Busca XML.exe** (18.5 MB)
   - Executável standalone (não requer instalação)
   - Versão: 1.0.95
   - Para uso portátil ou testes

2. **Busca_XML_Setup.exe** (54.2 MB)
   - Instalador completo para Windows
   - Cria atalhos no Menu Iniciar
   - Instalação em `C:\Program Files\Busca XML\`
   - **RECOMENDADO para uso em produção**

3. **version.txt**
   - Arquivo de versão (1.0.95)
   - Usado pelo sistema de auto-update

---

## 🐛 Problema Corrigido

### O que estava acontecendo (v1.0.92-1.0.94):
```
Erro: sqlite3.OperationalError: no such column: nsu
Local: nfe_search.py, linha 1631, método get_last_nsu()
Causa: Verificação de coluna executava DEPOIS da query (linha 1692)
```

### Solução implementada (v1.0.95):
- ✅ Verificação de coluna 'nsu' movida para **INÍCIO** do método `get_last_nsu()` (linha ~1674)
- ✅ Execução ANTES de qualquer SELECT query que possa falhar
- ✅ Retorno seguro `"000000000000000"` se coluna não existir
- ✅ Criação forçada da coluna via `criar_tabela_detalhada()`
- ✅ Logs detalhados: `🔍 [get_last_nsu] Colunas encontradas: [...]`
- ✅ Try-except com fallback seguro em caso de erro

### Fluxo corrigido:
```
ANTES (v1.0.94 - FALHOU):
  Linha 1631: SELECT MAX(nsu) ❌ CRASH
  Linha 1692: Verifica coluna 🔒 TARDE DEMAIS

AGORA (v1.0.95 - CORRIGIDO):
  Linha ~1674: Verifica coluna PRIMEIRO ✅
  Linha ~1700+: SELECT queries (SEGURO) ✅
```

---

## 📥 Instalação

### Opção 1: Instalador Completo (RECOMENDADO)

1. **Feche o aplicativo** Busca XML se estiver em execução
2. **Clique com botão direito** em `Busca_XML_Setup.exe`
3. Selecione **"Executar como administrador"**
4. Siga o assistente de instalação
5. Pronto! O atalho estará no Menu Iniciar

**Por que precisa de admin?**
- Instalação em `C:\Program Files\` requer privilégios elevados
- Sobrescreve versões anteriores de forma segura

### Opção 2: Executável Portátil

1. Copie `Busca XML.exe` para qualquer pasta
2. Execute diretamente (duplo clique)
3. Dados salvos em: `%APPDATA%\Busca XML\`

**Limitações do modo portátil:**
- Não cria atalhos automáticos
- Sem integração com Menu Iniciar
- Auto-update pode ter permissões limitadas

---

## 🔄 Após Instalação

### Primeira Execução (Migração Automática):

Se você tinha uma versão anterior com banco de dados sem coluna `nsu`:

```log
🔧 Inicializando banco de dados: C:\Users\...\nfe_data.db
🔧 _initialize() concluído
🔧 criar_tabela_detalhada() concluído
✅ Banco inicializado com sucesso

📄 Iniciando busca de NF-e para 49068153000160
🔍 [get_last_nsu] Colunas encontradas: ['chave', 'ie_tomador', ...]
❌ CRÍTICO: Coluna 'nsu' NÃO EXISTE! Forçando criação imediata...
🔍 Colunas existentes em notas_detalhadas: ['chave', ...]
✅ Coluna 'nsu' adicionada à tabela notas_detalhadas
✅ Coluna 'nsu' confirmada!
✅ criar_tabela_detalhada() executado de get_last_nsu
⚠️ Retornando NSU zero devido à recriação de estrutura

[Aplicativo continua normalmente]
```

### Execuções Subsequentes:

```log
🔍 [get_last_nsu] Colunas encontradas: ['chave', ..., 'nsu']
[Processa queries normalmente - coluna já existe]
```

---

## 🔍 Verificação de Logs

Se encontrar problemas, verifique os logs em:

```
Windows: %APPDATA%\Busca XML\logs\
Caminho completo: C:\Users\<SEU_USUARIO>\AppData\Roaming\Busca XML\logs\
```

Procure por estas mensagens:
- ✅ `🔍 [get_last_nsu] Colunas encontradas: [...]` - Verificação executada
- ✅ `❌ CRÍTICO: Coluna 'nsu' NÃO EXISTE!` - Detectou problema (primeira vez)
- ✅ `✅ criar_tabela_detalhada() executado de get_last_nsu` - Corrigiu automaticamente
- ✅ `⚠️ Retornando NSU zero devido à recriação` - Retorno seguro

---

## 🆕 Sistema de Auto-Update

Após instalar v1.0.95, o sistema de auto-update estará ativo:

1. **Verifica atualizações** automaticamente ao iniciar
2. **Notifica** quando nova versão disponível
3. **Atualiza** com um clique no botão "🔄 Atualizações"
4. **Backup automático** antes de atualizar
5. **Rollback** se algo der errado

**Configuração:**
- Repositório: https://github.com/W4lterBr/NF-e
- Releases: https://github.com/W4lterBr/NF-e/releases
- Branch: main

---

## 📊 Detalhes Técnicos

### Versão: 1.0.95

**Data de compilação**: 02/02/2026 10:57:10  
**Build system**: PyInstaller 6.17.0  
**Python**: 3.12.0  
**Plataforma**: Windows 10/11 (64-bit)

### Dependências incluídas:
- PyQt5 (Interface gráfica)
- cryptography 46.0.3 (Certificados digitais)
- lxml (Processamento XML)
- zeep 4.3.2 (SOAP/Web Services)
- reportlab (Geração de relatórios PDF)
- psutil (Monitoramento de sistema)

### Arquivos incluídos no executável:
- ✅ Schemas XSD (validação NFe/CTe/NFSe)
- ✅ Ícones e recursos visuais
- ✅ Sistema de auto-update
- ✅ Módulos de criptografia portátil

### Tamanho total: ~72 MB
- Executável: 18.5 MB
- Instalador: 54.2 MB (inclui executável + recursos + scripts)

---

## 🔒 Segurança

### Assinatura Digital:
- [ ] Certificado de código Windows (pendente)
- ✅ Executável verificado com antivírus
- ✅ Build reproduzível (código-fonte disponível)

### Criptografia:
- ✅ Senhas de certificados criptografadas com Fernet
- ✅ Chave de criptografia única por instalação
- ✅ Dados sensíveis nunca em texto plano

### Permissões necessárias:
- 📁 Leitura/escrita em `%APPDATA%\Busca XML\`
- 📋 Acesso à área de transferência (opcional)
- 🌐 Conexão internet (consulta SEFAZ/auto-update)
- 📄 Leitura de certificados digitais A1 (.pfx)

---

## ⚠️ Avisos Importantes

### Antivírus / Windows Defender:
Alguns antivírus podem bloquear executáveis PyInstaller por precaução:
- **Falso positivo comum** em apps Python compilados
- **Solução**: Adicione exceção no antivírus
- **Verificação**: Execute em https://www.virustotal.com

### Requisitos de Sistema:
- ✅ Windows 10 ou superior (64-bit)
- ✅ 4 GB RAM mínimo (8 GB recomendado)
- ✅ 500 MB espaço em disco
- ✅ Conexão com internet
- ✅ Certificado Digital A1 (.pfx) válido

### Compatibilidade:
- ✅ NFe versão 4.00
- ✅ CTe versão 4.00
- ✅ NFSe (Padrão Nacional)
- ✅ Distribuição DFe (NSU)
- ✅ Manifestação do Destinatário

---

## 🆘 Solução de Problemas

### Erro: "DLL não encontrada" ou "Faltam componentes"
**Solução**: Instale o [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### Erro: "Acesso negado" ao instalar
**Solução**: Execute o instalador como administrador (botão direito → "Executar como administrador")

### Erro: "Certificado inválido" ou "Senha incorreta"
**Solução**: 
1. Verifique se o certificado A1 (.pfx) está válido
2. Confirme a senha do certificado
3. Verifique a data de validade do certificado

### Erro persiste: "no such column: nsu"
Se após instalar v1.0.95 o erro persistir:
1. Verifique a versão instalada (deve mostrar "v1.0.95" na janela)
2. Delete o banco de dados: `%APPDATA%\Busca XML\nfe_data.db`
3. Reinicie o aplicativo (recriará o banco com estrutura correta)

### Logs não aparecem
Verifique se existe a pasta: `%APPDATA%\Busca XML\logs\`
- Se não existir, o app criará automaticamente
- Verifique permissões de escrita na pasta

---

## 📞 Suporte

### Reportar Bugs:
- 🐛 GitHub Issues: https://github.com/W4lterBr/NF-e/issues
- 📧 Email: contato via GitHub

### Contribuir:
- 💻 GitHub Repo: https://github.com/W4lterBr/NF-e
- 🔀 Pull Requests: Bem-vindos!
- 📖 Documentação: Veja pasta `/docs`

### Logs para Debug:
Ao reportar problemas, inclua:
1. Versão do app (1.0.95)
2. Sistema operacional (Windows 10/11)
3. Conteúdo do último arquivo `.log`
4. Print da mensagem de erro (se houver)

---

## 📝 Histórico de Versões

### v1.0.95 (02/02/2026) - ATUAL
🔧 **Correção Crítica**: Ordem de execução de verificação de coluna
- ✅ Fix: Verificação de coluna 'nsu' antes de queries
- ✅ Fix: Retorno seguro se coluna não existir
- ✅ Melhoria: Logs detalhados para debugging
- ✅ Segurança: Try-except com fallback

### v1.0.94 (02/02/2026)
🐛 Tentativa de correção com PRAGMA validation (falhou - ordem errada)

### v1.0.93 (02/02/2026)
✨ Sistema de auto-update TRUE implementado
⚡ Melhorias de performance

### v1.0.92 (02/02/2026)
🐛 Correção: Indentação de migração de banco

### Versões anteriores
📜 Ver CHANGELOG.md completo no repositório

---

## 📄 Licença

Este software é distribuído sob licença MIT.
Ver arquivo LICENSE no repositório para detalhes.

---

## 🙏 Créditos

**Desenvolvedor**: W4lterBr  
**Organização**: DWM System Developer  
**Ano**: 2025-2026

**Bibliotecas utilizadas**:
- PyQt5 - Interface gráfica
- cryptography - Segurança
- lxml - XML processing
- zeep - SOAP services
- requests - HTTP client
- reportlab - PDF generation

---

## ✅ Checklist de Instalação

Antes de instalar:
- [ ] Fechei o aplicativo antigo (se estava rodando)
- [ ] Tenho privilégios de administrador
- [ ] Tenho certificado digital A1 (.pfx) válido
- [ ] Sei a senha do certificado
- [ ] Conexão com internet ativa

Após instalar:
- [ ] App abre sem erros
- [ ] Versão mostra "v1.0.95" na janela
- [ ] Certificado carregado com sucesso
- [ ] Busca de NFe funciona
- [ ] Logs são gerados em `%APPDATA%\Busca XML\logs\`

---

## 🚀 Próximos Passos

1. **Instale** usando `Busca_XML_Setup.exe` como administrador
2. **Configure** seu certificado digital
3. **Teste** uma busca de NFe
4. **Verifique** os logs em caso de dúvidas
5. **Reporte** qualquer problema no GitHub

---

**Última atualização**: 02/02/2026  
**Versão do documento**: 1.0  
**Pacote**: dist_release_v1.0.95

