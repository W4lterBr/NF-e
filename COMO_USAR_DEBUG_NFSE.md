# 🔍 Sistema de Debug NFS-e - v1.1.15

## 📍 Onde encontrar o log

O arquivo de debug é automaticamente criado em:

```
%APPDATA%\Roaming\Busca XML\logs\nfse_pdf_debug.log
```

Caminho completo típico:
```
C:\Users\SEU_USUARIO\AppData\Roaming\Busca XML\logs\nfse_pdf_debug.log
```

## 🎯 Como usar

1. **Instale v1.1.16**
2. **Abra o programa**
3. **Dê duplo clique em uma NFS-e**
4. **Abra o log**:
   - Pressione `Win + R`
   - Digite: `%APPDATA%\Roaming\Busca XML\logs`
   - Abra o arquivo `nfse_pdf_debug.log`

## 📋 O que o log registra

### ✅ Informações capturadas:

1. **Timestamp** de cada operação
2. **Chave de acesso** extraída do XML
3. **Certificado** encontrado (CNPJ, informante, CUF)
4. **Tentativa de API**:
   - Criação do NFSeService
   - Chamada consultar_danfse()
   - Resultado (sucesso/erro)
5. **Fallbacks**:
   - DANFSe profissional local
   - Reportlab simples
6. **Erros detalhados** com stack trace

### 📝 Exemplo de log de sucesso (API):

```
[2026-02-08 14:10:30] ================================================================================
[2026-02-08 14:10:30] INÍCIO GERAÇÃO PDF NFS-e
[2026-02-08 14:10:30] Arquivo destino: C:\Users\...\27486306.pdf
[2026-02-08 14:10:30] Tentando baixar PDF oficial da API...
[2026-02-08 14:10:30] Extraindo chave de acesso do XML...
[2026-02-08 14:10:30] Atributo Id encontrado: NFS35260204117990915...
[2026-02-08 14:10:30] ✅ Chave extraída: 3526020411...0915000001 (len=50)
[2026-02-08 14:10:30] Chave válida (50 dígitos) - buscando certificado...
[2026-02-08 14:10:30] ✅ Certificado encontrado:
[2026-02-08 14:10:30]    CNPJ: 14380200000393
[2026-02-08 14:10:30]    Informante: IFOOD COM AGENCIA DE RESTAURANTES ONLINE S.A.
[2026-02-08 14:10:30]    CUF: 35
[2026-02-08 14:10:30]    Cert: C:\...\certificado.pfx
[2026-02-08 14:10:30] Criando NFSeService...
[2026-02-08 14:10:30] ✅ NFSeService criado com sucesso
[2026-02-08 14:10:30] Chamando consultar_danfse(chave=3526020411..., retry=2)...
[2026-02-08 14:10:32] ✅✅✅ PDF OFICIAL SALVO DA API (125,489 bytes)
[2026-02-08 14:10:32] Arquivo: C:\Users\...\27486306.pdf
[2026-02-08 14:10:32] ================================================================================
```

### ⚠️ Exemplo de log de fallback local:

```
[2026-02-08 14:15:20] ================================================================================
[2026-02-08 14:15:20] INÍCIO GERAÇÃO PDF NFS-e
[2026-02-08 14:15:20] Arquivo destino: C:\Users\...\27486306.pdf
[2026-02-08 14:15:20] Tentando baixar PDF oficial da API...
[2026-02-08 14:15:20] Extraindo chave de acesso do XML...
[2026-02-08 14:15:20] ✅ Chave extraída: 3526020411...0915000001 (len=50)
[2026-02-08 14:15:20] Chave válida (50 dígitos) - buscando certificado...
[2026-02-08 14:15:20] ✅ Certificado encontrado: ...
[2026-02-08 14:15:20] Criando NFSeService...
[2026-02-08 14:15:20] ✅ NFSeService criado com sucesso
[2026-02-08 14:15:20] Chamando consultar_danfse(chave=3526020411..., retry=2)...
[2026-02-08 14:15:25] ❌ ERRO na API: Timeout: Request timeout after 45 seconds
[2026-02-08 14:15:25] Tentando gerar DANFSe profissional localmente...
[2026-02-08 14:15:26] ✅ DANFSe profissional gerado localmente: C:\Users\...\27486306.pdf
[2026-02-08 14:15:26] ================================================================================
```

### ❌ Exemplo de log de erro:

```
[2026-02-08 14:20:10] ================================================================================
[2026-02-08 14:20:10] INÍCIO GERAÇÃO PDF NFS-e
[2026-02-08 14:20:10] Arquivo destino: C:\Users\...\27486306.pdf
[2026-02-08 14:20:10] Tentando baixar PDF oficial da API...
[2026-02-08 14:20:10] Extraindo chave de acesso do XML...
[2026-02-08 14:20:10] ❌ Elemento infNFSe não encontrado no XML
[2026-02-08 14:20:10] ❌ Chave de acesso não foi extraída do XML
[2026-02-08 14:20:10] Tentando gerar DANFSe profissional localmente...
[2026-02-08 14:20:10] ⚠️ USANDO FALLBACK REPORTLAB SIMPLES (todos os métodos anteriores falharam)
[2026-02-08 14:20:10] Informações extraídas: ['Número', 'Status']
[2026-02-08 14:20:10] ⚠️ PDF SIMPLES salvo (reportlab): C:\Users\...\27486306.pdf
[2026-02-08 14:20:10] ================================================================================
```

## 🔎 O que procurar no log

### Se o PDF está sendo gerado simples:

1. **Procure por**: `"❌ Nenhum certificado configurado"`
   - **Solução**: Configure um certificado no programa

2. **Procure por**: `"❌ ERRO na API"`
   - **Solução**: API está indisponível, use fallback local (normal)

3. **Procure por**: `"❌ Elemento infNFSe não encontrado"`
   - **Solução**: XML está em formato diferente do esperado

4. **Procure por**: `"⚠️ USANDO FALLBACK REPORTLAB SIMPLES"`
   - **Causa**: Todos os métodos (API + local profissional) falharam
   - **Veja stack trace** acima para identificar erro específico

### Se receber PDF oficial:

- Verá: `"✅✅✅ PDF OFICIAL SALVO DA API"`
- Tamanho típico: 100-200 KB
- Layout: Padrão governo com brasão

### Se receber PDF profissional local:

- Verá: `"✅ DANFSe profissional gerado localmente"`
- PDF com QR Code e layout organizado
- Quando API está offline/lenta

## 📧 Enviando log para suporte

Se precisar de ajuda:

1. Reproduza o problema (duplo clique em NFS-e)
2. Localize o arquivo `nfse_pdf_debug.log`
3. Copie as últimas 50 linhas do log
4. Envie com descrição do problema

---
**Desenvolvido por**: DWM System Developer  
**Versão**: 1.1.16  
**Data**: 08/02/2026
