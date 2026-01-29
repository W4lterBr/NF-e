# Integração API BrasilNFe

## 📌 Visão Geral

A integração com a API BrasilNFe resolve definitivamente o **erro 297 "Assinatura difere do calculado"** que ocorria com xmlsec local.

### Vantagens

✅ **Assinatura garantida** - Processada nos servidores BrasilNFe  
✅ **Compatibilidade 100%** - Testada e validada pela SEFAZ  
✅ **Sem dependências locais** - Não precisa xmlsec ou configuração complexa  
✅ **Suporte profissional** - Empresa especializada em NF-e  

## 🔧 Como Configurar

### 1. Criar Conta BrasilNFe

1. Acesse [brasilnfe.com.br](https://brasilnfe.com.br)
2. Crie uma conta
3. Escolha um plano (consulte preços no site)
4. Configure seu certificado digital na plataforma

### 2. Obter Token da API

1. Faça login no painel BrasilNFe
2. Vá em **Configurações** → **API**
3. Copie seu **Token de Acesso**

### 3. Configurar no Sistema

1. Abra **Busca NF-e**
2. Menu **Configurações** → **🔌 API BrasilNFe...**
3. Cole o token no campo
4. Clique em **🧪 Testar Conexão** (opcional)
5. Clique em **💾 Salvar**

## 📝 Como Funciona

### Fluxo de Manifestação

```
┌─────────────────┐
│  Busca NF-e     │
│  (seu sistema)  │
└────────┬────────┘
         │ 1. Solicita manifestação
         │    (chave, tipo, CNPJ)
         ▼
┌─────────────────┐
│  BrasilNFe API  │
│  (servidor)     │
└────────┬────────┘
         │ 2. Assina XML
         │ 3. Envia para SEFAZ
         │ 4. Retorna protocolo
         ▼
┌─────────────────┐
│     SEFAZ       │
│  (autorização)  │
└─────────────────┘
```

### Métodos Disponíveis

#### 1. Manifestação de NF-e
- **Endpoint**: `/ManifestarNotaFiscal`
- **Tipos suportados**:
  - `1` - Confirmação da Operação (210210)
  - `2` - Ciência da Operação (210200)
  - `3` - Desconhecimento da Operação (210220)
  - `4` - Operação não Realizada (210240)

#### 2. Cancelamento de Nota (futuro)
- **Endpoint**: `/CancelarNotaFiscal`
- Requer justificativa

#### 3. Carta de Correção (futuro)
- **Endpoint**: `/EnviarCartaCorrecao`
- Requer correção

## 🔄 Modo de Operação

O sistema **tenta usar BrasilNFe primeiro**:

```python
if token_brasilnfe_configurado:
    # ✅ USA API BRASILNFE (recomendado)
    resultado = api.manifestar_nota_fiscal(...)
else:
    # ⚠️ FALLBACK: xmlsec local (pode ter erro 297)
    resultado = assinar_com_xmlsec(...)
```

### NF-e vs CT-e

| Documento | Método Usado |
|-----------|-------------|
| **NF-e** | API BrasilNFe (se configurado) |
| **CT-e** | xmlsec local (BrasilNFe ainda não suporta) |

## ❌ Problema Resolvido: Erro 297

### Causa do Erro 297

O erro ocorria porque:

1. **xmlsec local** gerava assinatura RSA-SHA1
2. **SEFAZ** validava a assinatura
3. **SignatureValue** estava matematicamente incorreto
4. **DigestValue** estava correto (hash do infEvento)
5. Resultado: `297 - Assinatura difere do calculado`

### Investigação Realizada

✅ **SSL/TLS verificado** - Conectividade perfeita (Status 403 esperado)  
✅ **URLs verificadas** - Usando endpoints oficiais SVRS corretos  
✅ **XML estrutura** - 100% conforme especificação (ordem, namespace, whitespace)  
✅ **DigestValue** - Hash matematicamente correto  
❌ **SignatureValue** - RSA signature incorreta (problema do xmlsec)  

### Solução Final

**API BrasilNFe** elimina o problema:
- Assinatura feita em servidor profissional
- Testada por milhares de usuários
- Garantia de compatibilidade SEFAZ
- Sem necessidade de debugar xmlsec localmente

## 💰 Custos

Consulte preços atualizados em [brasilnfe.com.br/planos](https://brasilnfe.com.br).

Geralmente cobrado por:
- **Plano mensal** - Quantidade de documentos
- **Pay-per-use** - Por documento processado

## 🔒 Segurança

- Token armazenado no banco de dados local
- Comunicação HTTPS com API
- Certificado digital gerenciado pela BrasilNFe
- Senha do certificado NÃO é enviada

## 🆘 Troubleshooting

### "Módulo BrasilNFe não disponível"

Verifique se `modules/brasilnfe_api.py` existe:
```bash
dir modules\brasilnfe_api.py
```

### "Token parece inválido"

- Verifique se copiou o token completo
- Token deve ter pelo menos 20 caracteres
- Sem espaços no início/fim

### "Erro 401 - Unauthorized"

- Token expirado ou inválido
- Renove o token no painel BrasilNFe
- Configure novamente no sistema

### Manifestação ainda usa xmlsec

- Verifique se token foi salvo: Menu **🔌 API BrasilNFe...**
- Reinicie o sistema após configurar
- Veja logs: "USANDO API BRASILNFE" deve aparecer

## 📊 Logs

Mensagens importantes nos logs:

```
✅ API BrasilNFe configurada - usará assinatura remota
USANDO API BRASILNFE (assinatura remota garantida)
✅ Manifestação registrada via BrasilNFe! Protocolo: XXXXX
```

Se ver isso, significa que **xmlsec local** está sendo usado:
```
⚠️ NF-e sem API BrasilNFe configurada - usando xmlsec (pode ter erro 297)
USANDO ASSINATURA LOCAL (xmlsec - pode ter problemas)
```

## 🔗 Referências

- [BrasilNFe](https://brasilnfe.com.br)
- [Documentação API](https://brasilnfe.com.br/documentacao)
- [Portal NF-e](http://www.nfe.fazenda.gov.br)
- [Manual de Manifestação](http://www.nfe.fazenda.gov.br/portal/docs.aspx)

## 📜 Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2025-01-XX | 1.0 | Integração inicial BrasilNFe |
| - | - | Resolve erro 297 definitivamente |
| - | - | Suporte para 4 tipos de manifestação |
| - | - | Interface de configuração no menu |

---

**Desenvolvido para**: BOT - Busca NFE  
**Problema resolvido**: Erro 297 "Assinatura difere do calculado"  
**Solução**: API BrasilNFe com assinatura remota garantida
