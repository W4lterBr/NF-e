# 📊 Como as NFS-e Aparecem na Interface

## ✅ Status Atual

As NFS-e já estão **100% integradas** e aparecerão automaticamente na interface principal ([Busca NF-e.py](Busca%20NF-e.py)) junto com NF-e e CT-e!

---

## 🖥️ Visualização na Interface

### Tabela Principal (Busca NF-e.py)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  Tipo: [Todos ▼]  NFS-e aparece aqui!                                              │
│        └─ NFe                                                                       │
│        └─ CTe                                                                       │
│        └─ NFS-e  ← NOVO! ✨                                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Número          Emitente              Destinatário          Data        Valor     │
│  ──────────────────────────────────────────────────────────────────────────────────│
│  🟢 2500000001578  GLOBAL CREDIT        MATPARCG IND...      2025-01-02  R$ 30.88  │
│  🟢 114            OZEIAS PEREIRA       MATPARCG IND...      2024-11-29  R$ 2.439  │
│  🟢 106            OZEIAS PEREIRA       MATPARCG IND...      2024-11-19  R$ 120    │
│  🟢 100            OZEIAS PEREIRA       MATPARCG IND...      2024-11-01  R$ 1.200  │
│  🟢 343            ANDRE LUIZ PANIAGO   MATPARCG IND...      2024-10-08  R$ 320    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Estatísticas de Documentos

Após a integração, a interface mostrará:

| Tipo     | Quantidade | Valor Total       |
|----------|------------|-------------------|
| **NFe**  | 2.661      | R$ 4.262.646,18  |
| **CTe**  | 768        | R$ 0,00          |
| **NFS-e**| 87         | R$ 78.610,06     | ✨ NOVO!

**Total Geral:** 3.516 documentos

---

## 🔍 Filtros Disponíveis

### 1. Filtro por Tipo
```
┌─────────────────┐
│ Tipo: [Todos ▼] │
├─────────────────┤
│ □ Todos         │
│ □ NFe           │
│ □ CTe           │
│ ☑ NFS-e         │ ← Selecionar para ver só NFS-e
└─────────────────┘
```

### 2. Filtro por Data
```
De: [01/01/2024] Até: [31/12/2024]
```

### 3. Busca por Texto
```
🔍 Buscar: [GLOBAL CREDIT]  → Encontra prestadores/tomadores
```

---

## 📄 Detalhes da NFS-e (Double-Click)

Ao clicar duas vezes em uma NFS-e, abrirá janela com:

```
╔═══════════════════════════════════════════════════════════════╗
║  DETALHES DA NFS-e - Número: 2500000001578                   ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📝 Dados Gerais                                             ║
║  ├─ Número: 2500000001578                                   ║
║  ├─ Data Emissão: 02/01/2025                                ║
║  ├─ Valor: R$ 30,88                                         ║
║  ├─ Município: Belo Horizonte/MG                            ║
║  └─ Status: AUTORIZADA                                      ║
║                                                               ║
║  🏢 Prestador (Emitente)                                     ║
║  ├─ Nome: GLOBAL CREDIT SISTEMAS LTDA                        ║
║  ├─ CNPJ: 13.891.738/0001-38                                ║
║  └─ IM: 02945540015                                         ║
║                                                               ║
║  👤 Tomador (Destinatário)                                   ║
║  ├─ Nome: MATPARCG IND COM ESTRUTURAS PRE MOLDADAS           ║
║  ├─ CNPJ: 33.251.845/0001-09                                ║
║  └─ Município: Campo Grande/MS                               ║
║                                                               ║
║  💰 Valores                                                  ║
║  ├─ Valor Serviços: R$ 30,88                                ║
║  ├─ Alíquota ISS: 2,50%                                     ║
║  ├─ Valor ISS: R$ 0,77                                      ║
║  └─ Valor Líquido: R$ 30,88                                 ║
║                                                               ║
║  📋 Ações                                                    ║
║  [Visualizar XML]  [Salvar XML]  [Download DANFSE (PDF)]    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🎨 Identificação Visual

### Ícones por Tipo de Documento

- 📄 **NFe** - Nota Fiscal Eletrônica (verde)
- 🚚 **CTe** - Conhecimento de Transporte (azul)
- 📋 **NFS-e** - Nota Fiscal de Serviço (roxo) ✨ NOVO!

### Cores de Status

| Status      | Cor    | Ícone |
|-------------|--------|-------|
| AUTORIZADA  | 🟢 Verde | ✓ |
| CANCELADA   | 🔴 Vermelha | ✗ |
| DENEGADA    | 🟡 Amarelo | ⚠ |

---

## 📁 Estrutura de Arquivos

As NFS-e serão salvas em:

```
xmls/
└── {CNPJ_Prestador}/
    └── {MM-YYYY}/
        └── NFSe/
            ├── NFSe_2500000001578.xml
            ├── NFSe_114.xml
            ├── NFSe_106.xml
            └── ...
```

**Exemplo:**
```
xmls/33251845000109/01-2025/NFSe/NFSe_2500000001578.xml
```

---

## 🔄 Atualização Automática

### Busca Incremental (Padrão)
Ao clicar no botão **"Busca na Sefaz"**:
1. ✅ Busca novos documentos (NFe, CTe, NFS-e)
2. ✅ Atualiza tabela automaticamente
3. ✅ NFS-e aparecem junto com os outros documentos

### Busca Completa
Ao clicar no botão **"Busca Completa"** ou via script:
```bash
python buscar_nfse_auto.py --completa
```
1. 🔄 Busca TODAS as NFS-e desde o início
2. 🔄 Atualiza registros existentes
3. 🔄 Popula interface automaticamente

---

## 💾 Dados Armazenados

### Banco de Dados: `notas.db`

**Tabela: `notas_detalhadas`**

| Campo             | NFS-e Exemplo                          |
|-------------------|----------------------------------------|
| chave             | NFSE_2500000001578_13891738000138     |
| nome_emitente     | GLOBAL CREDIT SISTEMAS LTDA            |
| cnpj_emitente     | 13891738000138                         |
| numero            | 2500000001578                          |
| data_emissao      | 2025-01-02                             |
| **tipo**          | **NFS-e** ✨                           |
| valor             | 30.88                                  |
| status            | AUTORIZADA                             |
| cnpj_destinatario | 33251845000109                         |
| nome_destinatario | MATPARCG IND COM ESTRUTURAS...         |
| uf                | MG                                     |
| xml_status        | COMPLETO                               |
| informante        | 13891738000138                         |

---

## 🚀 Próximos Passos

### ✅ Já Implementado
- [x] Busca via Ambiente Nacional
- [x] Decodificação Base64 + gzip
- [x] Extração de dados do XML
- [x] Salvamento no banco
- [x] Integração com interface
- [x] Filtro por tipo (NFS-e)
- [x] Busca incremental/completa

### 🔜 Próximas Melhorias
- [ ] Download de DANFSE (PDF visual)
- [ ] Visualizador XML específico para NFS-e
- [ ] Gráficos/relatórios por tipo de documento
- [ ] Exportação Excel separada por tipo
- [ ] Notificações de novas NFS-e
- [ ] Manifestação de eventos NFS-e

---

## 🎯 Resumo Visual

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACE PRINCIPAL (Busca NF-e.py)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Busca na Sefaz]  [Busca Completa]  [Exportar]           │
│                                                             │
│  Filtros:  Tipo: [NFS-e ▼]  De: [____]  Até: [____]       │
│                                                             │
│  📊 Resumo:                                                │
│  ├─ NFe: 2.661 docs (R$ 4.262.646,18)                     │
│  ├─ CTe: 768 docs (R$ 0,00)                               │
│  └─ NFS-e: 87 docs (R$ 78.610,06) ✨ NOVO!               │
│                                                             │
│  📋 Lista de Documentos:                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Tipo  Número    Emitente         Data       Valor    │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 📋 2500000001578 GLOBAL CREDIT  2025-01-02  R$ 30.88 │ │
│  │ 📋 114         OZEIAS PEREIRA   2024-11-29  R$ 2.439 │ │
│  │ 📋 106         OZEIAS PEREIRA   2024-11-19  R$ 120   │ │
│  │ ...                                                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  [< Anterior]  Página 1 de 10  [Próximo >]                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📞 Como Usar

1. **Abra a interface:**
   ```bash
   python "Busca NF-e.py"
   ```

2. **Filtre por NFS-e:**
   - Clique no dropdown "Tipo"
   - Selecione "NFS-e"

3. **Busque novas NFS-e:**
   - Clique em "Busca na Sefaz" (incremental)
   - Ou execute: `python buscar_nfse_auto.py`

4. **Visualize detalhes:**
   - Dê duplo-clique em qualquer NFS-e da lista

---

**Última atualização:** 10/01/2026  
**Total de NFS-e na interface:** 87 documentos (R$ 78.610,06)
