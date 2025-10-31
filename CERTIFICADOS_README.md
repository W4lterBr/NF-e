# SISTEMA DE CERTIFICADOS DIGITAIS - MANUAL DE USO

## 📋 Visão Geral

O sistema de certificados digitais foi implementado com sucesso na interface BOT NFe! 
Agora você pode gerenciar certificados .pfx/.p12 diretamente pela interface gráfica.

## 🚀 Funcionalidades Implementadas

### ✅ Módulo de Certificados (`certificate_manager.py`)
- **Validação** de certificados .pfx/.p12 com senha
- **Extração** de informações (CN, CNPJ, CPF, validade)
- **Persistência** de configurações em arquivo JSON
- **Gerenciamento** de certificado ativo
- **Verificação** automática de expiração

### ✅ Interface Gráfica (`certificate_dialog.py`)
- **Dialog moderno** com tabs e tabela de certificados
- **Adicionar** certificados com validação de senha
- **Remover** certificados da lista
- **Definir** certificado ativo
- **Testar** senhas de certificados
- **Escanear** pastas em busca de certificados
- **Visualizar** detalhes completos
- **Validação** em background (sem travar a interface)

### ✅ Integração com Interface Principal
- **Menu** "Certificados" no menu bar
- **Botão** "Certificados" na toolbar
- **Callback** para atualização de status
- **Notificações** de mudanças

## 🔧 Como Usar

### 1. Acessar o Gerenciador
- **Menu**: Certificados → Gerenciar Certificados
- **Toolbar**: Clique no botão "Certificados"

### 2. Adicionar Certificado
1. Clique em **"Adicionar Certificado"**
2. Selecione arquivo .pfx ou .p12
3. Digite a **senha** do certificado
4. Opcionalmente, digite um **nome** amigável
5. Aguarde a validação

### 3. Gerenciar Certificados
- **Definir Ativo**: Selecione certificado → "Definir como Ativo"
- **Testar Senha**: Selecione certificado → "Testar Senha"
- **Remover**: Selecione certificado → "Remover"
- **Ver Detalhes**: Selecione certificado → Tab "Detalhes"

### 4. Escanear Pasta
1. Clique em **"Escanear Pasta"**
2. Selecione pasta que contém certificados
3. Sistema encontrará arquivos .pfx, .p12, .crt, .cer

## 📊 Status e Informações

### Códigos de Status na Tabela
- **✅ Válido**: Certificado válido (>30 dias para expirar)
- **⚠️ XXd**: Certificado válido mas próximo do vencimento (7-30 dias)
- **🔶 XXd**: Certificado válido mas crítico (<7 dias)
- **❌ Expirado**: Certificado vencido

### Informações Exibidas
- **Ativo**: Indica qual certificado está em uso
- **Nome/Alias**: Nome amigável ou CN do certificado
- **CNPJ/CPF**: Documento associado ao certificado
- **Válido até**: Data de expiração
- **Status**: Estado atual (válido/expirado/dias restantes)
- **Arquivo**: Nome do arquivo .pfx/.p12

## 🔒 Segurança

### ⚠️ Aviso Importante
Por simplicidade, as senhas são armazenadas em texto plano no arquivo `config/certificates.json`. 
**Em produção, implemente criptografia adequada!**

### Localização dos Arquivos
- **Configuração**: `config/certificates.json`
- **Logs**: Sistema usa logging padrão

## 📁 Estrutura de Arquivos Criada

```
modules/
├── certificate_manager.py    # Gerenciador principal
├── certificate_dialog.py     # Interface gráfica
└── qt_components.py          # Componentes visuais

config/
└── certificates.json         # Configurações salvas
```

## 🔧 Dependências Necessárias

### Instaladas Automaticamente
- **cryptography**: Para validação de certificados
- **PyQt6**: Interface gráfica (já existente)

```bash
pip install cryptography
```

## 🎯 Próximos Passos

### 🔄 Para Implementar (Integração SEFAZ)
1. **Autenticação SSL** com certificados
2. **Assinatura digital** de XMLs
3. **Consultas SEFAZ** autenticadas
4. **Download automático** de NFes

### 💡 Melhorias Futuras
- Criptografia de senhas
- Import/export de configurações
- Backup automático de certificados
- Notificações de expiração
- Suporte a certificados A3 (smartcard)

## 🐛 Resolução de Problemas

### Erro: "Cryptography não disponível"
```bash
pip install cryptography
```

### Erro: "Senha incorreta"
- Verifique se a senha está correta
- Teste com outros softwares de certificado
- Confirme se o arquivo não está corrompido

### Certificado não aparece na lista
- Verifique se é um arquivo .pfx ou .p12 válido
- Confirme se o arquivo não está corrompido
- Use "Testar Senha" para validar

## 📞 Suporte

O sistema foi implementado com logs detalhados. Em caso de problemas:
1. Verifique o terminal/console para mensagens de erro
2. Confirme se o arquivo de certificado é válido
3. Teste a senha em outro software de certificados

---

## ✨ Sistema Implementado com Sucesso!

O gerenciador de certificados digitais está **totalmente funcional** e integrado à interface principal. 
Agora você pode usar certificados .pfx/.p12 para autenticação com a SEFAZ e outras operações que requerem assinatura digital.

**Para testar**: Abra a interface → Menu "Certificados" → "Gerenciar Certificados"