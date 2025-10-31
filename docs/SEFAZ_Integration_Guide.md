# 🔐 Guia de Integração SEFAZ - Certificados Digitais

## Visão Geral
O sistema agora conta com integração completa entre o gerenciamento de certificados e as consultas SEFAZ. Isso permite:

- ✅ **Sincronização automática** de certificados do gerenciador para SEFAZ
- ✅ **Ativação/desativação** individual de certificados para consultas
- ✅ **Configuração de UF** por certificado
- ✅ **Busca automática** usando apenas certificados ativos

## Como Usar

### 1. Gerenciar Certificados
1. Acesse: **Menu Certificados → Gerenciar**
2. Adicione seus certificados `.pfx` ou `.p12`
3. Configure senhas e aliases
4. Verifique se estão válidos

### 2. Configurar para SEFAZ
1. Acesse: **Menu Certificados → Configurar SEFAZ**
2. Clique em **"🔄 Sincronizar Certificados"**
3. Configure para cada certificado:
   - ✅ **Status**: Marque para ativar nas consultas
   - 🌐 **UF**: Selecione a UF de autorização
   - 🗑️ **Remover**: Remove da configuração SEFAZ (não apaga o arquivo)

### 3. Executar Busca NFe
1. Use o botão **"Buscar NFe"** na interface
2. O sistema usará automaticamente apenas certificados ativos
3. Cada certificado buscará em sua UF configurada

## Funcionalidades da Configuração SEFAZ

### 📊 Tabela de Certificados
| Coluna | Descrição |
|--------|-----------|
| **CNPJ/CPF** | Identificação extraída do certificado |
| **Nome do Certificado** | Subject Name do certificado |
| **Validade** | Data de expiração + dias restantes |
| **Status** | Checkbox para ativar/desativar |
| **UF** | Dropdown com UFs disponíveis |
| **Ações** | Botão para remover da configuração |

### 🎨 Indicadores Visuais
- 🟢 **Verde**: Certificado válido (>90 dias)
- 🟠 **Laranja**: Próximo ao vencimento (30-90 dias)
- 🔴 **Vermelho**: Vence em menos de 30 dias

### 🔄 Sincronização
- Sincroniza certificados do gerenciador para a base SEFAZ
- Preserva configurações existentes (UF, status)
- Atualiza informações de validade

## Estados de Função (UF) Disponíveis

O sistema suporta todas as UFs brasileiras:

| Código | Estado | Código | Estado |
|--------|--------|--------|--------|
| **43** | RS - Rio Grande do Sul | **35** | SP - São Paulo |
| **33** | RJ - Rio de Janeiro | **31** | MG - Minas Gerais |
| **41** | PR - Paraná | **42** | SC - Santa Catarina |
| **50** | MS - Mato Grosso do Sul | **51** | MT - Mato Grosso |
| **52** | GO - Goiás | **53** | DF - Distrito Federal |
| ... | (todos os estados) | **91** | AN - Ambiente Nacional |

## Fluxo de Trabalho Recomendado

### 🔄 Configuração Inicial
1. **Importar certificados** no gerenciador
2. **Sincronizar** com SEFAZ
3. **Ativar** certificados desejados
4. **Configurar UF** de cada certificado
5. **Testar** com uma busca

### 📅 Manutenção
- **Verificar validade** dos certificados regularmente
- **Renovar** certificados antes do vencimento
- **Re-sincronizar** após adicionar novos certificados
- **Ajustar UF** conforme necessário

## Resolução de Problemas

### ❌ "Nenhum certificado encontrado"
- Verifique se certificados estão no gerenciador
- Execute sincronização
- Verifique se pelo menos um está ativo

### ❌ "Erro na busca"
- Verifique conectividade com internet
- Confirme se certificado não expirou
- Verifique se UF está correta
- Veja logs para detalhes específicos

### ❌ "Módulo não disponível"
- Verifique se dependências estão instaladas:
  ```bash
  pip install cryptography requests requests-pkcs12 zeep lxml
  ```

## Integração com Sistema Legado

O sistema mantém compatibilidade com bases existentes:

- ✅ **Migração automática** de certificados antigos
- ✅ **Fallback** para tabela legada se necessário
- ✅ **Preservação** de NSU e histórico
- ✅ **Sem perda** de configurações existentes

## Logs e Monitoramento

O sistema registra todas as operações:

```
[INFO] Sincronizados 3 certificados com SEFAZ
[DEBUG] Certificado 12.345.678/0001-90 ativado
[INFO] UF do certificado 12.345.678/0001-90 configurada para 43
[INFO] Certificado 98.765.432/0001-10 removido da base SEFAZ
```

---

## 🚀 Próximos Passos

Com a integração completa, você pode:

1. **Configurar certificados** conforme suas necessidades
2. **Executar buscas automáticas** com confiança
3. **Monitorar validade** dos certificados
4. **Escalar operações** com múltiplas empresas

Para suporte adicional, verifique os logs da aplicação ou consulte a documentação técnica.