# 🔧 Correção: Perfis de Armazenamento - Estrutura Certificado → Tipo → Data

## 📋 Versão: v1.1.28
**Data**: 2026-01-02  
**Tipo**: Correção de Bug + Nova Funcionalidade

---

## ❌ Problema Identificado

### Discrepância entre Interface e Código

A interface mostrava 2 opções de organização:
- **"Certificado → Tipo → Mês (padrão)"** → valor: `CERTIFICADO_TIPO`
- **"Tipo → Certificado → Mês (novo)"** → valor: `TIPO_CERTIFICADO`

Porém, o código fazia:
```python
# CERTIFICADO_TIPO (rótulo dizia "Cert → Tipo → Mês")
pasta_dest = pasta_certificado/ano_mes/tipo_pasta
# Resultado: 61-MATPARCG/012025/NFe/  ❌ CERT → DATA → TIPO

# TIPO_CERTIFICADO (rótulo dizia "Tipo → Cert → Mês")
pasta_dest = tipo_base/pasta_certificado/ano_mes
# Resultado: NFe/61-MATPARCG/012025/  ✅ TIPO → CERT → DATA
```

### O que o usuário esperava
Com base no rótulo "Certificado → Tipo → Mês", o usuário esperava:
```
61-MATPARCG/NFe/012025/
```

Mas recebia:
```
61-MATPARCG/012025/NFe/
```

---

## ✅ Solução Implementada

### 1. Nova Opção: `CERTIFICADO_TIPO_DATA`

Adicionada nova opção de organização que produz a estrutura esperada:
- **Certificado → Tipo → Data**
- Exemplo: `61-MATPARCG/NFe/012025/`

### 2. Rótulos Corrigidos

As 3 opções agora disponíveis (com rótulos CORRETOS):

| Opção | Rótulo | Estrutura Real | Exemplo |
|-------|--------|----------------|---------|
| `CERTIFICADO_TIPO_DATA` | **Certificado → Tipo → Data** 📅⭐ | `Cert/Tipo/Data` | `61-MATPARCG/NFe/012025/` |
| `TIPO_CERTIFICADO` | **Tipo → Certificado → Data** | `Tipo/Cert/Data` | `NFe/61-MATPARCG/012025/` |
| `CERTIFICADO_TIPO` | **Certificado → Data → Tipo** (antigo) | `Cert/Data/Tipo` | `61-MATPARCG/012025/NFe/` |

### 3. Código Atualizado

**nfe_search.py** - Linha 1288-1298:
```python
elif organizacao_tipo == 'CERTIFICADO_TIPO_DATA':
    # 🎨 PERFIL: CERTIFICADO → TIPO → DATA (novo v1.1.28)
    pasta_dest = os.path.join(pasta_base, pasta_certificado, tipo_base, ano_mes)
    logger.debug(f"📂 [PERFIL CERT_TIPO_DATA] {pasta_certificado}/{tipo_base}/{ano_mes}/")
```

**Busca NF-e.py** - Interface atualizada:
```python
combo_org.addItem("Certificado → Tipo → Data 📅", "CERTIFICADO_TIPO_DATA")
combo_org.addItem("Tipo → Certificado → Data", "TIPO_CERTIFICADO")
combo_org.addItem("Certificado → Data → Tipo (antigo)", "CERTIFICADO_TIPO")
```

### 4. Perfil DominioWeb Atualizado

O perfil "Importação para Dominio" foi atualizado:
```
Antes: organizacao_tipo = 'CERTIFICADO_TIPO'
Depois: organizacao_tipo = 'CERTIFICADO_TIPO_DATA'
```

---

## 🎯 Comportamento Esperado

### Com formato MMAAAA (012025, 022025...):
```
DominioWeb/
├── 61-MATPARCG/
│   ├── NFe/
│   │   ├── 012025/  ← Janeiro 2025
│   │   ├── 022025/  ← Fevereiro 2025
│   │   └── 032025/  ← Março 2025
│   ├── CTe/
│   │   └── 042025/  ← Abril 2025
│   └── NFS-e/
│       └── 052025/  ← Maio 2025
├── 33-OUTRAEMPRESA/
│   └── NFe/
│       └── 012025/
```

### Com formato AAAA-MM (2025-01, 2025-02...):
```
DominioWeb/
├── 61-MATPARCG/
│   ├── NFe/
│   │   ├── 2025-01/
│   │   ├── 2025-02/
│   │   └── 2025-03/
│   └── CTe/
│       └── 2025-04/
```

---

## 📝 Arquivos Modificados

1. **nfe_search.py**:
   - Linha 1288-1298: Adicionada lógica `CERTIFICADO_TIPO_DATA`
   - Linha 936-944: Atualizada documentação
   - Linha 1291: Renomeado log de `CERT_TIPO` → `CERT_DATA_TIPO`

2. **Busca NF-e.py**:
   - Linha 17207-17213: Combo de organização atualizado
   - Linha 17221-17232: Função `atualizar_exemplo()` com nova opção
   - Linha 17147-17161: Label de hierarquia com 3 opções
   - Linha 17570-17578: Texto de organização para aplicar perfil
   - Linha 17889-17897: Mapeamento de texto para mensagem final
   - Linha 17660-17667: Documentação de parâmetro

3. **Novos arquivos**:
   - `atualizar_perfil_dominio_tipo_data.py`: Script de atualização do perfil

---

## 🔄 Como Aplicar aos Arquivos Existentes

Os arquivos novos serão salvos automaticamente na nova estrutura. Para reorganizar arquivos antigos:

1. Abra a aplicação
2. Vá em **Configurações** → **Perfis de Armazenamento**
3. Selecione o perfil "Importação para Dominio"
4. Clique em **"▶️ Aplicar Perfil"**
5. Selecione a pasta `xmls` como origem
6. Confirme a operação

Isso copiará todos os arquivos para a nova estrutura.

---

## ⚠️ Compatibilidade

- **Perfis antigos**: Continuam funcionando com `CERTIFICADO_TIPO` (antigo)
- **Backup local**: Não afetado, continua usando `TIPO → CNPJ → DATA`
- **Novos perfis**: Recomendado usar `CERTIFICADO_TIPO_DATA` (⭐ marcado)

---

## 🧪 Testes Realizados

✅ Verificação de sintaxe: Sucesso  
✅ Atualização do banco de dados: Sucesso  
✅ Interface de criação de perfil: Atualizada  
✅ Interface de edição de perfil: Atualizada  
✅ Exemplo visual: Funcionando  
✅ Script de atualização: Executado com sucesso  

---

## 📊 Status do Perfil Atual

```
🔹 PERFIL #3: Importação para Dominio
   Pasta base: C:\Arquivo Walter - Empresas\Notas\DominioWeb
   Formato mês: MMAAAA ✅
   XML/PDF separados: False
   Organização: CERTIFICADO_TIPO_DATA ✅
   Status: ✅ Ativo
```

---

## 🎓 Lições Aprendidas

1. **Sempre validar rótulos da UI contra o código real**
2. **Documentar claramente com exemplos concretos**
3. **Manter compatibilidade com versões antigas**
4. **Criar scripts de migração para facilitar atualizações**

---

## 👤 Desenvolvido por
**GitHub Copilot** (Claude Sonnet 4.5)  
**Data**: 2026-01-02  
**Solicitação**: Análise 100% da funcionalidade de perfis de armazenamento
