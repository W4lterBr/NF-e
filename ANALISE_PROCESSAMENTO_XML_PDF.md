# 🔍 Análise Técnica: Processamento de XMLs para PDF

## 📊 Resumo Executivo

O sistema processa XMLs em PDF em **dois momentos distintos**:

1. **IMEDIATAMENTE** ao salvar XML (se for completo)
2. **EM LOTE** após busca na SEFAZ (varredura de faltantes)

---

## 🔄 Fluxo Completo: Da SEFAZ ao PDF

### **Passo 1: Recebimento do XML da SEFAZ**

**Arquivo:** `nfe_search.py`, função `processar_nfe()` (linha ~2600)

```python
# Sistema recebe resposta da SEFAZ
resp = svc.fetch_by_cnpj("CNPJ", last_nsu)

# Extrai documentos (até 50 por consulta)
docs_list = parser.extract_docs(resp)  # Lista de (nsu, xml)

for nsu, xml in docs_list:
    # Para cada documento...
```

**Tipos de XML recebidos:**
- ✅ **NF-e completa** (`<nfeProc>`) → Gera PDF
- ✅ **CT-e completo** (`<cteProc>`) → Gera PDF
- ❌ **Resumo NF-e** (`<resNFe>`) → NÃO gera PDF
- ❌ **Evento** (`<resEvento>`, `<procEventoNFe>`) → NÃO gera PDF

---

### **Passo 2: Salvamento do XML no Disco**

**Arquivo:** `nfe_search.py`, função `salvar_xml_por_certificado()` (linha 693)

```python
def salvar_xml_por_certificado(xml, cnpj_cpf, pasta_base="xmls", nome_certificado=None):
    """
    Salva XML organizando por:
    - CNPJ do certificado
    - Ano-Mês de emissão
    - Tipo de documento (NFe, CTe, Resumos, Eventos)
    
    Estrutura: xmls/{CNPJ}/{ANO-MES}/{TIPO}/{CHAVE}.xml
    """
    
    # 1. Parse do XML
    root = etree.fromstring(xml.encode("utf-8"))
    root_tag = root.tag.split('}')[-1]  # Ex: nfeProc, resNFe, resEvento
    
    # 2. Identifica tipo do documento
    if root_tag in ['nfeProc', 'NFe']:
        tipo_pasta = "NFe"
        tipo_doc = "NFe"
        is_completo = True  # ✅ Gera PDF
    elif root_tag in ['cteProc', 'CTe']:
        tipo_pasta = "CTe"
        tipo_doc = "CTe"
        is_completo = True  # ✅ Gera PDF
    elif root_tag == 'resNFe':
        tipo_pasta = "Resumos"
        tipo_doc = "ResNFe"
        is_completo = False  # ❌ NÃO gera PDF
    elif root_tag in ['resEvento', 'procEventoNFe', 'evento']:
        tipo_pasta = "Eventos"
        tipo_doc = "Evento"
        is_completo = False  # ❌ NÃO gera PDF
    
    # 3. Extrai chave de acesso (44 dígitos)
    chave = extrair_chave(xml)  # Ex: 52260115045348000172570010014777191002562584
    
    # 4. Extrai data de emissão
    data_emissao = extrair_data(xml)  # Ex: 2026-01
    
    # 5. Cria estrutura de pastas
    pasta_dest = os.path.join(
        pasta_base,           # xmls/
        cnpj_cpf,             # 12345678000199/
        data_emissao,         # 2026-01/
        tipo_pasta            # NFe/
    )
    os.makedirs(pasta_dest, exist_ok=True)
    
    # 6. Nome do arquivo: SEMPRE a chave
    nome_arquivo = f"{chave}.xml"
    caminho_xml = os.path.join(pasta_dest, nome_arquivo)
    
    # 7. Salva XML no disco
    with open(caminho_xml, "w", encoding="utf-8") as f:
        f.write(xml)
    
    print(f"[SALVO {tipo_doc}] {caminho_xml}")
    
    # 8. 🔥 GERAÇÃO AUTOMÁTICA DE PDF (IMEDIATA)
    if tipo_doc in ["NFe", "CTe"]:  # Apenas documentos completos
        try:
            caminho_pdf = caminho_xml.replace('.xml', '.pdf')
            if not os.path.exists(caminho_pdf):  # Só gera se não existe
                from modules.pdf_simple import generate_danfe_pdf
                success = generate_danfe_pdf(xml, caminho_pdf, tipo_doc)
                if success:
                    print(f"[PDF GERADO] {caminho_pdf}")
        except Exception as pdf_err:
            print(f"[AVISO] Erro ao gerar PDF: {pdf_err}")
    
    return os.path.abspath(caminho_xml)
```

---

### **Passo 3: Registro no Banco de Dados**

**Arquivo:** `nfe_search.py`, classe `DatabaseManager` (linha 1433)

```python
def registrar_xml(self, chave, cnpj, caminho_arquivo=None):
    """
    Registra XML na tabela xmls_baixados.
    Permite rastreamento de onde cada XML está salvo.
    """
    with self._connect() as conn:
        conn.execute('''
            INSERT INTO xmls_baixados (chave, cnpj_cpf, caminho_arquivo, baixado_em)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(chave) DO UPDATE SET
                caminho_arquivo = excluded.caminho_arquivo,
                baixado_em = datetime('now')
        ''', (chave, cnpj, caminho_arquivo))
        conn.commit()
```

---

### **Passo 4: Geração de PDFs Faltantes (Varredura em Lote)**

**Arquivo:** `Busca NF-e.py`, função `_gerar_pdfs_faltantes()` (linha 704)

**Quando é executado:**
- Após **"Busca na SEFAZ"** (linha 5433)
- Após **"Busca Completa"** (linha 1863)
- Ao iniciar o sistema (linha 688)

```python
def _gerar_pdfs_faltantes(self):
    """
    Varre TODOS os XMLs do sistema procurando por arquivos sem PDF.
    Executa em background para não travar a interface.
    """
    def _worker():
        xmls_dir = DATA_DIR / "xmls"
        
        print("[VERIFICAÇÃO] Procurando XMLs sem PDF...")
        count = 0
        
        # Percorre TODOS os XMLs recursivamente
        for xml_file in xmls_dir.rglob("*.xml"):
            
            # ⛔ FILTROS: Pula tipos que NÃO devem ter PDF
            
            # 1. Pula pasta "Eventos"
            if "Eventos" in str(xml_file.parent):
                continue
            
            # 2. Pula nomes específicos
            nome = xml_file.stem.upper()
            if any(keyword in nome for keyword in 
                   ['EVENTO', 'CIENCIA', 'CANCELAMENTO', 'CORRECAO', 'RESUMO']):
                continue
            
            # 3. Verifica se PDF já existe
            pdf_file = xml_file.with_suffix('.pdf')
            if pdf_file.exists():
                continue  # Já tem PDF
            
            # 4. Lê o XML e verifica se é documento completo
            xml_text = xml_file.read_text(encoding='utf-8')
            
            # ⛔ Só gera PDF para documentos COMPLETOS
            if '<nfeProc' not in xml_text and '<cteProc' not in xml_text:
                continue  # Não é documento completo (é resumo ou evento)
            
            # 5. ✅ GERA PDF
            tipo = "CTe" if "<CTe" in xml_text else "NFe"
            
            from modules.pdf_simple import generate_danfe_pdf
            success = generate_danfe_pdf(xml_text, str(pdf_file), tipo)
            
            if success:
                count += 1
                print(f"[PDF GERADO] {pdf_file.name}")
        
        print(f"[CONCLUÍDO] {count} PDFs gerados")
    
    # Executa em thread separada (não trava interface)
    Thread(target=_worker, daemon=True).start()
```

---

## 📦 Biblioteca de Geração de PDF

**Arquivo:** `modules/pdf_simple.py` (linha 9)

### Ordem de Tentativa:

```python
def generate_danfe_pdf(xml_text: str, out_path: str, tipo: str = "NFe") -> bool:
    """
    Tenta gerar PDF usando múltiplas bibliotecas (fallback).
    """
    
    # 1️⃣ TENTATIVA 1: BrazilFiscalReport (MELHOR - PDF completo)
    try:
        if tipo.upper() == "CTE":
            from brazilfiscalreport.dacte import Dacte
            doc = Dacte(xml=xml_bytes)
            doc.output(str(out_path))
            return True  # ✅ SUCESSO
        else:  # NFe
            from brazilfiscalreport.danfe import Danfe
            doc = Danfe(xml=xml_bytes)
            doc.output(str(out_path))
            return True  # ✅ SUCESSO
    except ImportError:
        # Biblioteca não instalada
        pass
    except TypeError as te:
        if "'NoneType' object is not iterable" in str(te):
            # Caso especial: CT-e sem infCarga
            # Continua para próxima tentativa
            pass
    except Exception as e:
        # Erro na geração
        print(f"[PDF] Erro BrazilFiscalReport: {e}")
    
    # 2️⃣ TENTATIVA 2: brazilnum-python
    try:
        from brazilnum.nfe import render_pdf_from_xml
        pdf_bytes = render_pdf_from_xml(xml_text)
        Path(out_path).write_bytes(pdf_bytes)
        return True  # ✅ SUCESSO
    except ImportError:
        pass
    
    # 3️⃣ TENTATIVA 3: ReportLab (PDF simples)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        
        # Gera PDF básico com dados principais
        c = canvas.Canvas(str(out_path), pagesize=A4)
        c.drawString(50, 800, f"DOCUMENTO FISCAL - {tipo}")
        # ... extrai dados principais do XML
        c.save()
        return True  # ✅ SUCESSO
    except ImportError:
        pass
    
    # 4️⃣ ÚLTIMO RECURSO: Arquivo de texto com extensão .pdf
    Path(out_path).write_text(
        f"DOCUMENTO FISCAL ELETRÔNICO\n\n"
        f"Tipo: {tipo}\n\n"
        f"XML Content:\n{xml_text[:1000]}...",
        encoding='utf-8'
    )
    return True  # ⚠️ Gerou arquivo, mas não é PDF real
```

---

## 📊 Fluxograma Completo

```
┌──────────────────────────────────────┐
│ 1. SEFAZ retorna XML                 │
│    (nfeProc, cteProc, resNFe, etc)   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 2. parse XML (identifica tipo)      │
│    root_tag = nfeProc, resNFe, etc   │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ É completo?  │
        │ nfeProc/cteProc │
        └──────┬──────┘
               │
         ┌─────┴─────┐
         │           │
       SIM          NÃO
         │           │
         ▼           ▼
    ┌─────────┐  ┌──────────┐
    │ NFe ou  │  │ Resumo   │
    │ CTe     │  │ Evento   │
    │ completo│  │          │
    └────┬────┘  └────┬─────┘
         │            │
         │            │
         ▼            ▼
┌──────────────┐  ┌────────────┐
│ 3. Salva XML │  │ Salva XML  │
│ xmls/CNPJ/   │  │ pasta      │
│ ANO-MES/NFe/ │  │ específica │
│ {chave}.xml  │  └────────────┘
└──────┬───────┘         │
       │                 │
       │                 │
       ▼                 │
┌──────────────┐         │
│ 4. 🔥 GERA   │         │
│ PDF IMEDIATO │         │
│ {chave}.pdf  │         │
└──────┬───────┘         │
       │                 │
       ▼                 ▼
┌──────────────────────────────────────┐
│ 5. Registra no banco (xmls_baixados)│
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ 6. Após busca completa:              │
│    _gerar_pdfs_faltantes()           │
│    • Varre TODOS os XMLs             │
│    • Identifica faltantes            │
│    • Gera em lote (background)       │
└──────────────────────────────────────┘
```

---

## 🎯 Diferença: Resumo vs Completo

### **Resumo NF-e** (`<resNFe>`)

**O que contém:**
- Chave de acesso
- CNPJ emitente/destinatário
- Valor total
- Data de emissão
- **NÃO contém:** Itens da nota, impostos detalhados, assinatura

**Processamento:**
```python
Salva: xmls/12345678000199/2026-01/Resumos/52260115045348000172570010014777191002562584.xml
PDF:   ❌ NÃO GERA (resumo não tem dados suficientes)
```

**Para obter XML completo:**
- Duplo clique na nota (interface)
- Sistema consulta chave na SEFAZ
- Baixa `<nfeProc>` completo
- Salva em: `xmls/12345678000199/2026-01/NFe/{chave}.xml`
- **Agora sim gera PDF**

### **NF-e Completa** (`<nfeProc>`)

**O que contém:**
- **TUDO** do resumo +
- Lista completa de produtos
- Impostos detalhados (ICMS, IPI, PIS, COFINS)
- Dados de transporte
- Assinatura digital
- Protocolo de autorização SEFAZ

**Processamento:**
```python
Salva: xmls/12345678000199/2026-01/NFe/52260115045348000172570010014777191002562584.xml
PDF:   ✅ GERA IMEDIATAMENTE (DANFE completo)
```

---

## ⚙️ Configurações e Performance

### **Quando PDFs são gerados:**

| Momento | Tipo | Local | Performance |
|---------|------|-------|-------------|
| **Ao salvar XML** | Completo (NFe/CTe) | `salvar_xml_por_certificado()` | ⚡ Imediato (1 PDF) |
| **Após busca SEFAZ** | Faltantes | `_gerar_pdfs_faltantes()` | 🔄 Lote (N PDFs) |
| **Ao iniciar sistema** | Faltantes | `_gerar_pdfs_faltantes()` | 🔄 Lote (N PDFs) |

### **Geração em Background:**

```python
# Thread separada - NÃO trava interface
Thread(target=_worker, daemon=True).start()
```

- ✅ Interface permanece responsiva
- ✅ Usuário pode continuar trabalhando
- ✅ PDFs gerados silenciosamente

---

## 📝 Estrutura de Pastas Final

```
xmls/
├── 12345678000199/              # CNPJ do certificado
│   ├── 2026-01/                 # Ano-Mês
│   │   ├── NFe/                 # NF-e completas
│   │   │   ├── 522601...84.xml  ✅ PDF GERADO
│   │   │   └── 522601...84.pdf  
│   │   ├── CTe/                 # CT-e completos
│   │   │   ├── 512601...45.xml  ✅ PDF GERADO
│   │   │   └── 512601...45.pdf  
│   │   ├── Resumos/             # Resumos NF-e
│   │   │   └── 522601...99.xml  ❌ SEM PDF
│   │   └── Eventos/             # Eventos (cancelamento, etc)
│   │       └── 522601...77.xml  ❌ SEM PDF
│   └── 2025-12/
│       └── ...
└── 98765432000188/              # Outro certificado
    └── ...
```

---

## 🔍 Como Identificar Problemas

### **1. PDF não foi gerado**

**Verificar:**
```python
# 1. É documento completo?
grep -i "nfeProc\|cteProc" arquivo.xml
# Se retornar vazio → É resumo, NÃO gera PDF

# 2. Erro na geração?
# Verificar logs: [AVISO] Erro ao gerar PDF: ...

# 3. Biblioteca instalada?
pip list | grep -i "brazilfiscalreport"
```

### **2. PDF incompleto ou com erro**

**Ordem de fallback:**
1. BrazilFiscalReport → PDF completo (DANFE/DACTE oficial)
2. brazilnum-python → PDF intermediário
3. ReportLab → PDF básico
4. Texto → Arquivo .pdf com conteúdo texto

**Instalar biblioteca recomendada:**
```bash
pip install brazilfiscalreport
```

---

## ✅ Resumo

### **Fluxo Automático:**

1. **XML chega da SEFAZ** → Sistema identifica tipo
2. **É completo** (nfeProc/cteProc)? → ✅ **Gera PDF IMEDIATAMENTE**
3. **É resumo/evento**? → ❌ **Salva XML, NÃO gera PDF**
4. **Após busca** → Varre faltantes e gera em lote

### **Bibliotecas:**

- **BrazilFiscalReport**: PDF completo e oficial (recomendado)
- **Fallbacks**: brazilnum, ReportLab, texto puro

### **Performance:**

- ⚡ **Imediato**: 1 PDF por documento completo ao salvar
- 🔄 **Lote**: N PDFs em background após busca
- ✅ **Não trava**: Tudo em threads separadas

**O sistema garante que todo documento COMPLETO tenha seu PDF gerado automaticamente!**
