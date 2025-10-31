# 📁 **ORGANIZAÇÃO POR TIPOS DE DOCUMENTO**

## 🎯 **NOVA ESTRUTURA DE PASTAS**

Agora os XMLs são **automaticamente organizados por tipo de documento fiscal**! Cada NFe, CTe e NFS-e é salvo em sua própria pasta específica.

---

## 📂 **ESTRUTURA HIERÁRQUICA**

### **🗂️ Layout das Pastas**
```
xmls/
├── 47539664000197/              # CNPJ do emitente/informante
│   ├── NFe/                     # 📄 Notas Fiscais Eletrônicas
│   │   ├── 2025-01/            # Ano-Mês de emissão
│   │   │   ├── 00123-EMPRESA_ABC_LTDA.xml
│   │   │   ├── 00124-DISTRIBUIDORA_XYZ.xml
│   │   │   └── 00125-COMERCIO_123.xml
│   │   ├── 2025-02/
│   │   └── 2025-03/
│   │
│   ├── CTe/                     # 🚛 Conhecimentos de Transporte
│   │   ├── 2025-01/
│   │   │   ├── CTE-00456-TRANSPORTADORA_ABC.xml
│   │   │   └── CTE-00457-LOGISTICA_XYZ.xml
│   │   └── 2025-02/
│   │
│   └── NFS-e/                   # 🏢 Notas Fiscais de Serviços
│       ├── 2025-01/
│       │   ├── NFSE-00789-PRESTADOR_SERVICOS.xml
│       │   └── NFSE-00790-CONSULTORIA_ABC.xml
│       └── 2025-02/
│
└── 98765432000198/              # Outro CNPJ
    ├── NFe/
    ├── CTe/
    └── NFS-e/
```

---

## 🔍 **DETECÇÃO AUTOMÁTICA DO TIPO**

### **📋 Como o Sistema Identifica Cada Tipo:**

#### **🧾 NFe (Nota Fiscal Eletrônica)**
- **Tags Detectadas:** `NFe`, `nfeProc`, `procNFe`, `resNFe`
- **Namespace:** `http://www.portalfiscal.inf.br/nfe`
- **Pasta:** `xmls/{CNPJ}/NFe/{ANO-MES}/`
- **Nomenclatura:** `{numero}-{nome_emitente}.xml`

#### **🚛 CTe (Conhecimento de Transporte)**
- **Tags Detectadas:** `CTe`, `procCTe`, `resCTe`
- **Namespace:** `http://www.portalfiscal.inf.br/cte`
- **Pasta:** `xmls/{CNPJ}/CTe/{ANO-MES}/`
- **Nomenclatura:** `CTE-{numero}-{nome_emitente}.xml`

#### **🏢 NFS-e (Nota Fiscal de Serviços)**
- **Tags Detectadas:** `NFSe`, `procNFSe`, `resNFSe`
- **Namespace:** `http://www.abrasf.org.br/nfse.xsd`
- **Pasta:** `xmls/{CNPJ}/NFS-e/{ANO-MES}/`
- **Nomenclatura:** `NFSE-{numero}-{nome_prestador}.xml`

---

## 📊 **VANTAGENS DA SEPARAÇÃO**

### **✅ Organização Perfeita**
| Antes | Depois |
|-------|--------|
| ❌ Todos misturados na mesma pasta | ✅ Separados por tipo automaticamente |
| ❌ Difícil encontrar documentos específicos | ✅ Busca direta por categoria |
| ❌ NFe, CTe e NFS-e juntos | ✅ Cada tipo em sua pasta |

### **🔍 Facilita Localização**
- **NFe:** `xmls/47539664000197/NFe/2025-01/` - Apenas notas fiscais
- **CTe:** `xmls/47539664000197/CTe/2025-01/` - Apenas conhecimentos de transporte  
- **NFS-e:** `xmls/47539664000197/NFS-e/2025-01/` - Apenas notas de serviços

### **📈 Melhora Performance**
- **Menos arquivos por pasta** = navegação mais rápida
- **Busca específica** por tipo de documento
- **Backup seletivo** por categoria

---

## 🏷️ **NOMENCLATURA DOS ARQUIVOS**

### **📄 NFe - Nota Fiscal Eletrônica**
```
Formato: {numero}-{nome_emitente}.xml
Exemplos:
├── 00123-EMPRESA_ABC_LTDA.xml
├── 00124-DISTRIBUIDORA_XYZ_SA.xml
└── 00125-COMERCIO_123_EIRELI.xml
```

### **🚛 CTe - Conhecimento de Transporte**
```
Formato: CTE-{numero}-{nome_transportadora}.xml
Exemplos:
├── CTE-00456-TRANSPORTADORA_ABC.xml
├── CTE-00457-LOGISTICA_XYZ_LTDA.xml
└── CTE-00458-FROTA_BRASIL_SA.xml
```

### **🏢 NFS-e - Nota Fiscal de Serviços**
```
Formato: NFSE-{numero}-{nome_prestador}.xml
Exemplos:
├── NFSE-00789-PRESTADOR_SERVICOS.xml
├── NFSE-00790-CONSULTORIA_ABC_LTDA.xml
└── NFSE-00791-MANUTENCAO_XYZ.xml
```

---

## 🚀 **COMPATIBILIDADE TOTAL**

### **✅ Documentos Suportados**
- **Resumos:** `resNFe`, `resCTe`, `resNFSe` → **Pasta correta automaticamente**
- **Completos:** `procNFe`, `procCTe`, `procNFSe` → **Pasta correta automaticamente**
- **Básicos:** `NFe`, `CTe`, `NFSe` → **Pasta correta automaticamente**

### **🔄 Retrocompatibilidade**
- **XMLs existentes:** Continuam funcionando normalmente
- **Sistema antigo:** Não é quebrado, apenas melhorado
- **Migração:** Opcional, novos XMLs já usam estrutura nova

---

## 🎯 **LOGS ESPECÍFICOS POR TIPO**

### **📝 Mensagens no Console**
```log
[SALVO NFe] xmls/47539664000197/NFe/2025-01/00123-EMPRESA_ABC.xml
[SALVO CTe] xmls/47539664000197/CTe/2025-01/CTE-00456-TRANSPORTADORA.xml  
[SALVO NFS-e] xmls/47539664000197/NFS-e/2025-01/NFSE-00789-PRESTADOR.xml
```

### **🔍 Identificação Automática**
```log
Detectado resumo NFE no NSU 123456 - salvando em pasta NFe
Detectado documento CTe completo - salvando em pasta CTe
Detectado NFS-e do padrão nacional - salvando em pasta NFS-e
```

---

## 🛠️ **CONFIGURAÇÃO**

### **📁 Pasta Base Padrão**
```python
pasta_base = "xmls"  # Pode ser alterada conforme necessário
```

### **🗂️ Estrutura Automática**
O sistema **cria automaticamente** todas as pastas necessárias:
- `xmls/` (pasta base)
- `{CNPJ}/` (por emitente/informante)  
- `{TIPO}/` (NFe, CTe, NFS-e)
- `{ANO-MES}/` (por período de emissão)

---

## 📋 **RESUMO**

### **🎉 Agora Você Tem:**
✅ **Separação automática** por tipo de documento  
✅ **Organização cronológica** por ano-mês  
✅ **Nomenclatura padronizada** com prefixos  
✅ **Detecção inteligente** do tipo fiscal  
✅ **Compatibilidade total** com todos os formatos  
✅ **Logs informativos** específicos por tipo  

**Resultado: Organização perfeita dos seus documentos fiscais eletrônicos!** 🚀

---

## 📁 **EXEMPLO PRÁTICO**

### **Antes (Tudo Misturado):**
```
xmls/47539664000197/2025-01/
├── 00123-EMPRESA.xml          # NFe? CTe? NFS-e? 🤔
├── 00456-TRANSPORTADORA.xml   # Não sabemos o tipo
└── 00789-PRESTADOR.xml        # Difícil identificar
```

### **Depois (Organizado por Tipo):**
```
xmls/47539664000197/
├── NFe/2025-01/
│   └── 00123-EMPRESA.xml           # ✅ Claramente uma NFe
├── CTe/2025-01/
│   └── CTE-00456-TRANSPORTADORA.xml # ✅ Claramente um CTe
└── NFS-e/2025-01/
    └── NFSE-00789-PRESTADOR.xml     # ✅ Claramente uma NFS-e
```

**Agora é impossível confundir os tipos de documento! 🎯**