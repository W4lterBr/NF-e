# 📋 Busca Automática de NFS-e - Guia do Usuário

## O que é?

O sistema agora **baixa automaticamente** suas NFS-e (Notas Fiscais de Serviço Eletrônicas) junto com suas NF-e e CT-e. Você não precisa fazer nada - é tudo automático!

---

## ✨ Como Funciona

### Busca Automática

Sempre que você clicar em **"Atualizar"**, o sistema:

1. ✅ Busca suas NF-e (como sempre fez)
2. ✅ Busca seus CT-e (como sempre fez)  
3. ✅ **NOVO**: Busca suas NFS-e automaticamente

Tudo em **segundo plano** - você pode continuar usando o sistema normalmente!

### Onde Ficam as NFS-e?

As NFS-e aparecem nas **mesmas abas** das outras notas:

- **"Emitidos por terceiros"** → NFS-e que VOCÊ recebeu (é o tomador)
- **"Emitidos pela empresa"** → NFS-e que VOCÊ emitiu (é o prestador)

---

## 🔍 Como Ver suas NFS-e

### Na Interface

1. Abra o sistema "Busca XML"
2. Clique em **"Atualizar"** (ou espere a busca automática)
3. Veja suas NFS-e nas tabelas, junto com NF-e e CT-e

**Filtrar apenas NFS-e:**
- Use o campo **"Tipo"** e selecione **"NFSe"**

### Arquivos no Disco

As NFS-e são salvas seguindo o **mesmo padrão de NF-e e CT-e**:

```
📁 xmls/
  └── 📁 [SEU_CNPJ]/
      └── 📁 [ANO-MES]/
          └── 📁 NFSe/
              ├── 📄 123-NOME_PRESTADOR.xml  ← XML da nota
              └── 📄 123-NOME_PRESTADOR.pdf  ← PDF oficial (DANFSe)
```

**Formato da pasta ANO-MES:**
O formato respeita a configuração `storage_formato_mes` do banco:
- **AAAA-MM** (padrão): `2026-01`
- **MM-AAAA**: `01-2026`
- **AAAA/MM**: `2026/01`
- **MM/AAAA**: `01/2026`

**Exemplo real:**
```
xmls/47539664000197/2026-01/NFSe/
├── 9-EMPRESA_SERVICOS_LTDA.xml
├── 9-EMPRESA_SERVICOS_LTDA.pdf
├── 10-CONSULTORIA_ABC.xml
└── 10-CONSULTORIA_ABC.pdf
```

**Nomenclatura dos arquivos:**
- Padrão: `{NUMERO}-{NOME_PRESTADOR}.xml`
- Nome do prestador é extraído do XML (RazaoSocial)
- Mesmo padrão usado em NF-e (`{NUMERO}-{FORNECEDOR}.xml`)
- Facilita identificação visual dos arquivos

---

## ⏱️ Frequência de Busca

### Automática

O sistema busca NFS-e automaticamente:

- ✅ Quando você clica **"Atualizar"**
- ✅ **10 minutos** após iniciar (se iniciou com o Windows)
- ✅ A cada **intervalo agendado** (se configurado)

### Manual

Se quiser forçar uma busca completa (reprocessar tudo):

1. Abra o PowerShell no diretório do sistema
2. Digite:
   ```powershell
   .\.venv\Scripts\python.exe buscar_nfse_auto.py --completa
   ```

⚠️ **Atenção**: Busca completa pode demorar vários minutos!

---

## ❓ Perguntas Frequentes

### Não vejo minhas NFS-e. Por quê?

**Possíveis motivos:**

1. **Seu município não usa o Sistema Nacional**
   - Nem todos os municípios já aderiram ao padrão nacional
   - Consulte: https://www.gov.br/nfse

2. **Você não emite/recebe NFS-e**
   - Sistema só baixa o que existe no governo
   - Verifique no portal da prefeitura se você tem NFS-e

3. **Empresa nova (sem histórico)**
   - Sistema só baixa notas existentes
   - Emita/receba sua primeira NFS-e e tente novamente

### Como sei se a busca está funcionando?

Verifique os **logs** em:

```
📁 logs/
  └── 📄 busca_nfe_2026-01-29.log
```

Procure por linhas como:
```
BUSCANDO NFS-e VIA AMBIENTE NACIONAL
✅ 42 documento(s) encontrado(s)
✅ NFS-e 9: R$ 6000.00 salva
```

### Quanto tempo demora?

| Situação | Tempo |
|----------|-------|
| Sem NFS-e | 1-2 segundos |
| 10 NFS-e | 30-60 segundos |
| 50 NFS-e | 2-5 minutos |

O sistema trabalha em **segundo plano** - você não precisa esperar!

### Posso desativar a busca automática?

Sim! Entre em contato com o suporte técnico para desabilitar.

### A busca consome muita internet?

**Não**. Cada NFS-e tem em média:
- XML: ~10 KB
- PDF: ~200 KB

**Exemplo**: 100 NFS-e = ~20 MB (menos que 1 minuto de vídeo)

### Preciso configurar algo?

**Não!** Se você já usa o sistema para NF-e/CT-e, a busca de NFS-e funciona automaticamente.

O sistema usa os **mesmos certificados digitais** que você já cadastrou.

---

## 🆘 Problemas e Soluções

### "Timeout na busca de NFS-e"

**O que é**: Busca demorou mais de 5 minutos.

**Solução**:
1. Verifique sua conexão com internet
2. Tente novamente mais tarde (pode ser instabilidade do governo)
3. Execute busca manual (veja acima)

### "Servidor temporariamente indisponível"

**O que é**: Sistema do governo está fora do ar.

**Solução**:
- Sistema tenta 3 vezes automaticamente
- Se falhar, tente novamente em 10-30 minutos
- Problema é no servidor do governo, não no nosso sistema

### "Nenhum documento encontrado"

**O que é**: Você não tem NFS-e disponíveis.

**Não é erro!** Significa que:
- Seu município não aderiu ao sistema nacional, **OU**
- Você não emitiu/recebeu NFS-e ainda, **OU**
- Suas NFS-e são antigas (anteriores à adesão do município)

---

## 📊 O que Aparece na Interface

### Coluna "Tipo"

As NFS-e aparecem como:
```
NFSe
```

(Igual a "NFe" e "CTe")

### Coluna "Número"

O número da NFS-e:
```
123
456
789
```

### Coluna "Valor"

Valor total do serviço:
```
R$ 6.000,00
R$ 1.500,50
R$ 250,00
```

### Status do XML

Se você conseguiu baixar o XML:
- ✅ **Disponível** (verde) → XML foi baixado com sucesso
- ⚠️ **Não Disponível** (amarelo) → XML não pôde ser baixado

---

## 💡 Dicas

### Para Ver Apenas NFS-e

1. Use o filtro **"Tipo"** → Selecione **"NFSe"**
2. Ordene por **"Data"** para ver as mais recentes

### Para Exportar NFS-e

1. Filtre por **"NFSe"** (como acima)
2. Clique em **"Exportar"**
3. Escolha formato (Excel, CSV, etc.)

### Para Abrir o PDF

1. Dê **duplo clique** na linha da NFS-e
2. O PDF oficial será aberto automaticamente

Se não abrir:
- PDF está em: `xmls/[SEU_CNPJ]/[MES-ANO]/NFSe/`
- Abra manualmente pelo Windows Explorer

---

## 🎯 Benefícios

### Automação Total

✅ Nenhum trabalho manual  
✅ Tudo baixado automaticamente  
✅ XMLs e PDFs organizados por data

### Integração Perfeita

✅ NFS-e aparecem junto com NF-e/CT-e  
✅ Mesma interface para tudo  
✅ Mesmos filtros e buscas

### Compliance

✅ Todos XMLs salvos corretamente  
✅ PDFs oficiais (válidos legalmente)  
✅ Organizados para auditoria

---

## 📞 Suporte

Precisa de ajuda?

1. **Logs**: Veja `logs/busca_nfe_[DATA].log`
2. **Documentação técnica**: `docs/INTEGRACAO_NFSE.md`
3. **Suporte**: Entre em contato com nosso time

---

## 🎉 Pronto!

Você não precisa fazer **NADA**! O sistema cuida de tudo automaticamente.

Apenas use normalmente e suas NFS-e aparecerão junto com as outras notas. 🚀

---

**Sistema**: BOT Busca NFE v2.0  
**Recurso**: Busca Automática de NFS-e  
**Data**: 29/01/2026
