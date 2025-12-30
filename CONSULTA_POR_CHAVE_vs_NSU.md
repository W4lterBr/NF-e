# 📋 Consulta por Chave vs Consulta por NSU

## 🔍 Duas Formas de Buscar XMLs na SEFAZ

### 1️⃣ **Consulta por NSU (Distribuição DFe)**
- **Endpoint**: `NFeDistribuicaoDFe` 
- **Método**: `distDFeInt`
- **O que faz**: Busca TODOS os documentos fiscais disponíveis para o CNPJ
- **Como funciona**: Sequencial, do NSU 0 até o último disponível

#### ✅ Vantagens:
- Busca automática de TODOS os documentos
- Eficiente para varredura completa
- Encontra documentos que você não conhece

#### ❌ Desvantagens:
- **ERRO 656**: Bloqueio de ~60 minutos se consultar < 1 hora
- Muitas requisições seguidas = bloqueio
- Não pode consultar frequentemente

#### 📊 Limitações:
```
Consultas permitidas: ~1 a cada 60 minutos
Erro 656: "Consumo Indevido - Aguarde 1 hora"
Bloqueio: Por CNPJ/certificado
Documentos por consulta: Até 50 por lote
```

---

### 2️⃣ **Consulta por Chave (Consulta Protocolo)**
- **Endpoint**: `NFeConsultaProtocolo`
- **Método**: `consChNFe` / `consSitNFe`
- **O que faz**: Busca XML completo de UMA nota específica pela chave de 44 dígitos

#### ✅ Vantagens:
- **SEM erro 656!** Não tem bloqueio de 1 hora
- Pode consultar com mais frequência
- Retorna XML completo com protocolo
- Ideal para consultas pontuais

#### ❌ Desvantagens:
- Só funciona se você **já tem a chave**
- Consulta uma nota por vez (mais lento para muitas notas)
- Limite de ~50 requisições por minuto

#### 📊 Limitações:
```
Consultas permitidas: ~50 por minuto (aprox.)
Sem erro 656: ✅ Pode consultar frequentemente
Bloqueio: Por requisições/minuto (rate limit)
Documentos por consulta: 1 XML por requisição
```

---

## 🎯 Quando Usar Cada Uma?

### Use **Consulta por NSU** quando:
- ✅ Precisa baixar TODOS os XMLs disponíveis
- ✅ Primeira vez buscando documentos (NSU = 0)
- ✅ Busca periódica automática (1x por hora)
- ✅ Não sabe quais notas existem

### Use **Consulta por Chave** quando:
- ✅ Já tem a chave e quer o XML completo
- ✅ Recebeu erro 656 e precisa buscar urgente
- ✅ Cliente/fornecedor enviou apenas a chave
- ✅ Quer validar status de uma nota específica
- ✅ Precisa buscar várias notas conhecidas rapidamente

---

## 💡 Estratégia Híbrida (Recomendado)

### Cenário Ideal:
1. **Busca periódica por NSU** (1x por hora)
   - Busca automática em background
   - Pega todos os documentos disponíveis
   
2. **Consulta por chave sob demanda**
   - Quando usuário colar chave específica
   - Quando tiver erro 656 e precisar buscar urgente
   - Para notas que faltam e você tem a chave

### Exemplo de Uso:

```python
# BUSCA AUTOMÁTICA (NSU) - 1x por hora
def busca_automatica():
    if not tem_erro_656():
        buscar_por_nsu()  # Busca tudo
    else:
        print("Aguardando fim do bloqueio 656...")

# BUSCA MANUAL (CHAVE) - Sempre disponível
def busca_manual(chave):
    # Sempre funciona, mesmo com erro 656!
    xml = consultar_por_chave(chave)
    return xml
```

---

## 🚀 Implementação no Sistema

### Situação Atual:
- ✅ Sistema já tem consulta por NSU implementada
- ✅ Sistema já tem função `buscar_por_chave` na interface
- ✅ Sistema já trata erro 656 corretamente

### O que pode melhorar:

#### 1. **Baixar XMLs Faltantes por Chave**
Se a interface mostra chaves mas não tem XML:
```python
def baixar_xmls_faltantes():
    chaves_sem_xml = buscar_chaves_sem_xml()
    for chave in chaves_sem_xml:
        if not tem_xml_completo(chave):
            xml = consultar_por_chave(chave)
            salvar_xml(chave, xml)
```

#### 2. **Botão "Baixar XML" Individual**
Para cada nota na tabela:
- Se não tem XML → Botão "📥 Baixar"
- Clique → Consulta por chave → Salva XML

#### 3. **Busca em Lote por Chave**
Com rate limit de ~50/min:
```python
def baixar_lote_por_chave(chaves):
    for i, chave in enumerate(chaves):
        xml = consultar_por_chave(chave)
        salvar_xml(chave, xml)
        
        # Rate limit: ~50 por minuto
        if (i + 1) % 50 == 0:
            time.sleep(60)  # Aguarda 1 minuto
```

---

## 📊 Comparação Prática

| Aspecto | Consulta por NSU | Consulta por Chave |
|---------|-----------------|-------------------|
| **Erro 656** | ❌ Sim (60 min) | ✅ Não |
| **Frequência** | ~1x/hora | ~50x/minuto |
| **Uso** | Busca completa | Busca específica |
| **Pré-requisito** | Certificado | Certificado + Chave |
| **Retorno** | Múltiplos XMLs | 1 XML por vez |
| **Ideal para** | Automação | Sob demanda |

---

## 🎓 Exemplo Real

### Situação: Erro 656 às 11:38

**❌ Opção RUIM**: Aguardar até 12:38
```
11:38 - Erro 656 (bloqueado)
12:38 - Pode consultar por NSU novamente
```

**✅ Opção BOA**: Usar consulta por chave
```
11:38 - Erro 656 no NSU
11:39 - Consulta por chave funciona! ✅
11:40 - Mais uma por chave ✅
11:41 - Mais uma por chave ✅
...
12:38 - NSU desbloqueado, volta ao normal
```

---

## 🔧 Implementação Proposta

### 1. Novo Botão: "Sincronizar XMLs"
- Verifica registros sem XML
- Baixa usando consulta por chave
- Mostra progresso e resumo

### 2. Coluna na Tabela: "Status XML"
- ✅ XML completo
- ⚠️ Só metadados (sem XML)
- 📥 Pode baixar por chave

### 3. Menu de Contexto:
- Clique direito na nota
- "Baixar XML por chave" (se não tem)
- "Atualizar XML" (se tem mas quer reconsultar)

---

## 📝 Resumo Final

### Para o Usuário:
- **NSU**: Busca automática 1x/hora (pode ter erro 656)
- **Chave**: Busca manual sempre disponível (sem erro 656)

### Recomendação:
✅ Use **ambas as estratégias**:
- NSU para automação (background)
- Chave para buscar específicas (quando preciso)

### Próximo Passo:
Implementar função para baixar XMLs faltantes usando consulta por chave, respeitando rate limit de 50 req/min.
