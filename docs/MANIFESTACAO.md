# Manifestação do Destinatário — Documentação Técnica

> **Sistema:** Busca NF-e v1.2.5  
> **Data:** 2026-04-24  
> **Módulo principal:** `modules/manifestacao_service.py`

---

## 1. O que é a Manifestação do Destinatário?

A **Manifestação do Destinatário** é um conjunto de eventos eletrônicos previstos na legislação brasileira (NT 2011/002 — SEFAZ Nacional) que permite ao **destinatário** de uma NF-e (modelo 55) ou CT-e (modelo 57) comunicar à SEFAZ a sua ciência ou posição em relação à operação fiscal documentada.

Esses eventos são enviados ao **Ambiente Nacional (cOrgão = 91)**, independentemente da UF do emitente.

### Por que isso importa?

| Sem manifestação | Com manifestação |
|---|---|
| Emitente pode cancelar a NF-e a qualquer momento | Após Confirmação (210200), o cancelamento é **bloqueado** |
| SEFAZ não sabe se o destinatário recebeu o documento | SEFAZ registra a ciência/posição do destinatário |
| Possíveis inconsistências fiscais | Conformidade legal para o destinatário |

---

## 2. Tipos de Evento

### NF-e (modelo 55)

| Código | Nome | Descrição | Requer Justificativa? |
|--------|------|-----------|----------------------|
| **210210** | Ciência da Operação | Destinatário tem ciência da existência da NF-e, mas **não confirma** a operação. Não bloqueia cancelamento. Geralmente o **primeiro evento** enviado ao baixar uma nota nova. | Não |
| **210200** | Confirmação da Operação | Destinatário confirma que a operação ocorreu. **Bloqueia cancelamento** pelo emitente. | Não |
| **210220** | Desconhecimento da Operação | Destinatário declara que não reconhece a operação. | Não |
| **210240** | Operação não Realizada | Destinatário informa que a operação descrita não se realizou. | **Sim** (mínimo 15 caracteres) |

### CT-e (modelo 57)

| Código | Nome |
|--------|------|
| **610110** | Ciência CT-e |
| **610112** | Confirmação CT-e |

---

## 3. Fluxo de Manifestação no Sistema

```
Usuário clica "Baixar XML Completo" ou "Manifestar"
        │
        ▼
Sistema verifica se a nota já possui manifestação local
(tabela eventos_nfe / xml_completo armazenado)
        │
        ├─ SIM → Já manifestada → Baixa XML diretamente
        │
        └─ NÃO → Envia Ciência da Operação (210210)
                        │
                        ▼
              ManifestacaoService.enviar_manifestacao()
                        │
                        ▼
              Assina XML com certificado PKCS12
              (_assinar_evento_pkcs12)
                        │
                        ▼
              Envia para SEFAZ via PyNFe
              (ComunicacaoSefaz, uf='AN', cOrgao=91)
                        │
                        ├─ cStat=135 → SUCESSO → salva protocolo
                        ├─ cStat=573 → Duplicidade → considera sucesso
                        └─ Outro   → REJEIÇÃO → exibe erro
                        │
                        ▼
              Aguarda 3s (SEFAZ processar)
                        │
                        ▼
              Baixa XML completo da SEFAZ
                        │
                        ▼
              Gera PDF Comprovante
              (comprovantes_manifestacao/)
```

---

## 4. Onde é Disparada

### 4.1 Automática — ao baixar XML completo

Quando o usuário clica em **"Baixar XML Completo"** para uma nota que ainda não tem manifestação:

```python
# Busca NF-e.py ~linha 6366
# Ciência da Operação (210210) — primeira manifestação ao receber/baixar a nota
# ⚠️ Usa 210210 (Ciência), NÃO 210200 (Confirmação):
#    - 210210 = destinatário ciente da existência (não bloqueia cancelamento)
#    - 210200 = destinatário confirma a operação  (bloqueia cancelamento emitente)
manifesta_service = ManifestacaoService(cert_path, cert_senha)
sucesso, protocolo, mensagem, xml_resposta = manifesta_service.enviar_manifestacao(
    chave=chave,
    tipo_evento='210210',
    cnpj_destinatario=cnpj_destinatario,
    justificativa=None
)
```

### 4.2 Manual — botão "Manifestação Manual"

O usuário pode manifestar qualquer documento digitando a chave manualmente:

- **Toolbar** → botão **"Manifestação Manual"**
- Abre diálogo com campos: Certificado, Senha, Chave de Acesso, Tipo de Evento
- Suporta certificado cadastrado no sistema **ou** arquivo `.pfx`/`.p12` externo
- Após o envio, abre PDF comprovante automaticamente

### 4.3 Via duplo-clique / menu de contexto

Ao clicar em uma nota já carregada na tabela, o sistema verifica a manifestação existente e exibe tooltip informativo.

---

## 5. Módulo `ManifestacaoService`

**Arquivo:** `modules/manifestacao_service.py`

### Construtor

```python
service = ManifestacaoService(
    certificado_path="C:/certs/empresa.pfx",
    certificado_senha="senha123"
)
```

### Método principal

```python
sucesso, protocolo, mensagem, xml_resposta = service.enviar_manifestacao(
    chave="35260112345678000195550010000123451234567890",  # 44 dígitos
    tipo_evento="210210",   # ver tabela seção 2
    cnpj_destinatario="12345678000195",
    justificativa=None      # obrigatório apenas para 210240
)
```

**Retorno:**

| Posição | Tipo | Descrição |
|---------|------|-----------|
| `sucesso` | `bool` | `True` se SEFAZ retornou cStat 135 ou 573 |
| `protocolo` | `str` | Número do protocolo SEFAZ (`nProt`) |
| `mensagem` | `str` | Mensagem de retorno da SEFAZ (`xMotivo`) |
| `xml_resposta` | `str` | XML completo da resposta SEFAZ |

### Assinatura Digital (`_assinar_evento_pkcs12`)

O sistema usa assinatura PKCS12 direta para contornar incompatibilidade entre **PyNFe** e **signxml >= 4.0**:

- PyNFe's `AssinaturaA1` remove os headers PEM do certificado
- `signxml >= 4.0` exige PEM completo ou `List[x509.Certificate]`
- **Solução**: passa `x509.Certificate` diretamente para `signxml`, que insere `X509Certificate` no XML automaticamente

```python
# Bibliotecas usadas
from cryptography.hazmat.primitives.serialization import pkcs12
from pynfe.utils import CustomXMLSigner
import signxml
```

---

## 6. Comprovante PDF

Após cada manifestação bem-sucedida, o sistema gera automaticamente um **PDF comprovante** inspirado no layout visual da página SEFAZ "Consulta NF-e Completa":

- **Paleta**: laranja-âmbar (`#C8924A`) — cabeçalho, `#CC7700` — seções
- **Conteúdo**: Chave, Tipo de Evento, Protocolo, CNPJ Manifestante, Data/Hora, Mensagem SEFAZ, dados derivados da chave (UF, emitente, série, número, modelo)
- **Local de armazenamento**: `comprovantes_manifestacao/`
- **Nomenclatura**: `ComprovManif_{NSU}_{YYYYMMDD}_{HHMMSS}.pdf`
- **Abertura automática**: sim, via `subprocess.Popen(["cmd", "/c", "start", "", pdf_path])`

**Método responsável:** `_gerar_pdf_comprovante_manifestacao(dados)` em `Busca NF-e.py`

---

## 7. Banco de Dados

A manifestação é rastreada via tabela de eventos:

```sql
-- Verificar manifestações existentes de uma nota
SELECT tipo_evento, data_evento, protocolo
FROM eventos_nfe
WHERE chave_acesso = '...'
  AND tipo_evento IN ('210200','210210','210220','210240');
```

Códigos de evento que indicam manifestação registrada:

```python
EVENTOS_MANIFESTACAO = {'210200', '210210', '210220', '210240'}
```

---

## 8. Tratamento de Erros Comuns

| cStat | Significado | Ação do sistema |
|-------|-------------|-----------------|
| `135` | Evento registrado e vinculado | ✅ Sucesso — salva protocolo |
| `573` | Duplicidade de evento | ✅ Considera sucesso (evento já registrado) |
| `650` | Nota cancelada | ⚠️ Marca nota como cancelada no banco |
| `694` | Rejeição: CNPJ inválido | ❌ Erro — verificar CNPJ manifestante |
| `472` | Erro de assinatura | ❌ Verificar certificado e senha |

---

## 9. Dependências

```
pynfe           # EventoManifestacaoDest, ComunicacaoSefaz, SerializacaoXML
signxml >= 4.0  # Assinatura XML enveloped (rsa-sha1 / sha1)
cryptography    # Leitura PKCS12 (pkcs12.load_key_and_certificates)
lxml            # Parse e serialização XML
reportlab       # Geração do PDF comprovante
```

---

## 10. Configuração de Certificado

O certificado digital (A1) deve ser:

- **Formato**: `.pfx` ou `.p12` (PKCS12)
- **Tipo**: e-CNPJ ou e-CPF emitido por AC credenciada ICP-Brasil
- **Cadastro**: Menu **Configurações → Certificados** na interface do sistema

Para manifestação manual sem certificado cadastrado, o sistema extrai o CNPJ automaticamente do CN (Common Name) do certificado:

```
CN = "EMPRESA LTDA:01773924000193"
CNPJ = últimos 14 dígitos numéricos
```

---

## 11. Referências Legais e Técnicas

- **NT 2011/002** — Nota Técnica de Manifestação do Destinatário (SEFAZ Nacional)
- **cOrgão 91** — Ambiente Nacional, usado para todos os eventos de manifestação
- **Endpoint SEFAZ**: `https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx`
- **Schema XSD**: `leiauteEventoManifDestNFe_v1.00.xsd`
- **Modelo 55** = NF-e | **Modelo 57** = CT-e
