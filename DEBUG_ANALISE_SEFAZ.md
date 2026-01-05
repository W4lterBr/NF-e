# 🔍 Análise de Debug - Respostas da SEFAZ

## Pasta de Debug

Todos os arquivos de debug são salvos em:
```
xmls/Debug de notas/
```

## 📋 Tipos de Arquivos Gerados

### 1. Resposta Completa da SEFAZ
**Padrão**: `[TIMESTAMP]_[CNPJ]_analise_resposta_sefaz_completa.xml`

**Conteúdo**:
- Cabeçalho com informações da consulta (CNPJ, NSU, timestamp, UF)
- XML completo retornado pela SEFAZ
- Inclui envelope de resposta com todos os documentos

**Exemplo**:
```
20260104_112345_47539664000197_analise_resposta_sefaz_completa.xml
```

**Quando é gerado**: A cada resposta bem-sucedida da SEFAZ

---

### 2. Resumo de Documentos
**Padrão**: `[TIMESTAMP]_[CNPJ]_analise_resumo_documentos.xml`

**Conteúdo**:
- Total de documentos encontrados
- cStat, ultNSU, maxNSU
- Lista detalhada de cada documento:
  - NSU
  - Tag raiz (resEvento, nfeProc, etc)
  - Tamanho em bytes
  - Tipo (NF-e, Evento, NFC-e)
  - Chave (se aplicável)
  - Código e descrição do evento (se for evento)
  - Status (processado, ignorado)

**Exemplo de conteúdo**:
```
=== RESUMO DOS DOCUMENTOS ENCONTRADOS ===
Total de documentos: 50
cStat: 138
ultNSU: 000000000059107
maxNSU: 000000000059107

Doc 1 - NSU 000000000059057:
  Tag raiz: resEvento
  Tamanho: 1245 bytes
  Tipo: EVENTO
  Código: 610514
  Descrição: Registro de Passagem de NFe propagado pelo MDFe/CTe
  Chave: 41250894623741000334550300001180321938209800

Doc 2 - NSU 000000000059058:
  Tag raiz: nfeProc
  Tamanho: 8932 bytes
  Tipo: NF-e (modelo 55)
  Chave: 35250912345678000190550010000123451234567890

...

=== RESUMO FINAL ===
Total processado com sucesso: 45
Informante: 47539664000197
CNPJ: 47539664000197
```

**Quando é gerado**: Após processar todos os documentos de uma resposta

---

### 3. Eventos Individuais
**Padrão**: `[TIMESTAMP]_[CNPJ]_extraido_evento_[CODIGO]_NSU[NSU].xml`

**Conteúdo**:
- XML completo do evento extraído da resposta SEFAZ

**Exemplo**:
```
20260104_112346_47539664000197_extraido_evento_610514_NSU000000000059057.xml
```

**Quando é gerado**: Sempre que um evento é detectado e processado

**Tipos de eventos comuns**:
- `610514` - Registro de Passagem (MDF-e/CT-e)
- `110111` - Cancelamento
- `110110` - Carta de Correção
- `210200` - Confirmação da Operação
- `210210` - Ciência da Operação
- `210220` - Desconhecimento da Operação
- `210240` - Operação não Realizada

---

### 4. NF-e Individuais
**Padrão**: `[TIMESTAMP]_[CNPJ]_extraido_nfe_NSU[NSU]_chave[8PRIMEIROS].xml`

**Conteúdo**:
- XML completo da NF-e extraída da resposta SEFAZ

**Exemplo**:
```
20260104_112347_47539664000197_extraido_nfe_NSU000000000059058_chave35250912.xml
```

**Quando é gerado**: Sempre que uma NF-e (modelo 55) é detectada e processada

---

### 5. Requests e Responses SOAP
**Padrão**: `[TIMESTAMP]_[CNPJ]_nfe_dist_[request|response].xml`

**Conteúdo**:
- **request**: Envelope SOAP enviado para SEFAZ
- **response**: Resposta SOAP recebida (antes de extrair documentos)

**Exemplo**:
```
20260104_112345_47539664000197_nfe_dist_request.xml
20260104_112345_47539664000197_nfe_dist_response.xml
```

**Quando é gerado**: Em toda requisição ao serviço de distribuição

---

## 🔎 Como Analisar os Arquivos

### Passo 1: Identifique o Certificado/CNPJ

Os nomes dos arquivos contêm o CNPJ do informante. Procure por:
```powershell
Get-ChildItem "xmls\Debug de notas\" | Where-Object { $_.Name -like "*47539664000197*" } | Sort-Object LastWriteTime -Descending
```

### Passo 2: Verifique a Resposta Completa

Abra o arquivo `*_resposta_sefaz_completa.xml` mais recente:
```powershell
$arquivo = Get-ChildItem "xmls\Debug de notas\" -Filter "*_resposta_sefaz_completa.xml" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
notepad $arquivo.FullName
```

**O que procurar**:
- `<cStat>`: Status da consulta
  - `138` = Documentos localizados
  - `137` = Nenhum documento
  - `656` = Consulta muito frequente
- `<ultNSU>`: Último NSU consultado
- `<maxNSU>`: Maior NSU disponível
- `<docZip>`: Documentos compactados em Base64

### Passo 3: Analise o Resumo de Documentos

Abra o arquivo `*_resumo_documentos.xml`:
```powershell
$arquivo = Get-ChildItem "xmls\Debug de notas\" -Filter "*_resumo_documentos.xml" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
notepad $arquivo.FullName
```

**O que procurar**:
- Quantos documentos foram encontrados
- Quantos são eventos vs NF-e
- Quantos foram processados vs ignorados
- Chaves dos documentos

### Passo 4: Verifique Eventos Específicos

Liste todos os eventos extraídos:
```powershell
Get-ChildItem "xmls\Debug de notas\" -Filter "*_evento_*" | Select-Object Name, LastWriteTime | Sort-Object LastWriteTime -Descending
```

Conte eventos por tipo:
```powershell
Get-ChildItem "xmls\Debug de notas\" -Filter "*_evento_*" | ForEach-Object {
    if ($_.Name -match "evento_(\d+)_") {
        $matches[1]
    }
} | Group-Object | Select-Object Count, Name | Sort-Object Count -Descending
```

### Passo 5: Compare com Banco de Dados

Verifique se os eventos foram salvos no banco:
```sql
-- Total de manifestações
SELECT COUNT(*) FROM manifestacoes;

-- Últimas manifestações
SELECT * FROM manifestacoes ORDER BY data_manifestacao DESC LIMIT 10;

-- Manifestações por tipo
SELECT tipo_evento, COUNT(*) as total 
FROM manifestacoes 
GROUP BY tipo_evento 
ORDER BY total DESC;
```

---

## 🐛 Diagnóstico de Problemas

### Problema: "Nenhum evento aparece na interface"

**Verificações**:

1. **Há arquivos de evento no debug?**
   ```powershell
   Get-ChildItem "xmls\Debug de notas\" -Filter "*_evento_*" | Measure-Object
   ```
   - Se **0**: Eventos não estão sendo retornados pela SEFAZ
   - Se **>0**: Eventos estão sendo baixados mas não salvos corretamente

2. **O código está processando eventos?**
   ```powershell
   Get-Content "logs\busca_nfe_$(Get-Date -Format 'yyyy-MM-dd').log" | Select-String "VERSÃO DO CÓDIGO"
   ```
   - Se aparecer "v2026-01-04": Código atualizado ✅
   - Se não aparecer: Processo precisa ser reiniciado ❌

3. **Eventos estão sendo detectados?**
   ```powershell
   Get-Content "logs\busca_nfe_$(Get-Date -Format 'yyyy-MM-dd').log" | Select-String "Evento detectado"
   ```
   - Se aparecer: Eventos foram detectados ✅
   - Se não aparecer: Verificar resumo de documentos

4. **Compare resumo com banco de dados**
   - Abra o resumo de documentos mais recente
   - Conte quantos eventos aparecem
   - Compare com `SELECT COUNT(*) FROM manifestacoes;`

---

### Problema: "cStat 656 - Consultas muito frequentes"

**O que fazer**:

1. Verifique quando pode consultar novamente:
   ```sql
   SELECT informante, ultima_consulta, proximo_acesso 
   FROM certificados_consulta;
   ```

2. Aguarde o tempo mínimo (1 hora entre consultas)

3. Durante o cooldown, novos eventos **não serão baixados**

---

### Problema: "Documentos estão sendo ignorados"

**Causas comuns**:

1. **NFC-e (modelo 65)** - Sistema busca apenas NF-e modelo 55
   ```
   Doc X - NSU XXXXX:
     Tag raiz: nfeProc
     Tipo: NFC-e (modelo 65) - IGNORADO
   ```

2. **Evento sem chave válida**
   ```
   Doc X - NSU XXXXX:
     Tag raiz: resEvento
     Tipo: EVENTO (chave inválida)
   ```

3. **XML sem infNFe**
   ```
   Doc X - NSU XXXXX:
     Tag raiz: desconhecido
     Tipo: Desconhecido (sem infNFe)
   ```

---

## 📊 Estatísticas Úteis

### Total de arquivos de debug gerados

```powershell
Get-ChildItem "xmls\Debug de notas\" | Measure-Object | Select-Object Count
```

### Tamanho total ocupado

```powershell
$size = (Get-ChildItem "xmls\Debug de notas\" -Recurse | Measure-Object -Property Length -Sum).Sum
"{0:N2} MB" -f ($size / 1MB)
```

### Arquivos por tipo

```powershell
Get-ChildItem "xmls\Debug de notas\" | Group-Object {
    if ($_.Name -like "*_evento_*") { "Eventos" }
    elseif ($_.Name -like "*_nfe_*") { "NF-e" }
    elseif ($_.Name -like "*_resumo_*") { "Resumos" }
    elseif ($_.Name -like "*_resposta_*") { "Respostas SEFAZ" }
    else { "Outros" }
} | Select-Object Name, Count
```

### Últimos 10 arquivos criados

```powershell
Get-ChildItem "xmls\Debug de notas\" | Sort-Object LastWriteTime -Descending | Select-Object -First 10 | Format-Table Name, LastWriteTime, @{N='Tamanho(KB)';E={[math]::Round($_.Length/1KB,2)}}
```

---

## 🧹 Limpeza de Arquivos Antigos

### Remover arquivos com mais de 7 dias

```powershell
$limite = (Get-Date).AddDays(-7)
Get-ChildItem "xmls\Debug de notas\" | Where-Object { $_.LastWriteTime -lt $limite } | Remove-Item -Force
```

### Manter apenas últimos 100 arquivos de cada tipo

```powershell
# Eventos
Get-ChildItem "xmls\Debug de notas\" -Filter "*_evento_*" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 100 | Remove-Item -Force

# NF-e
Get-ChildItem "xmls\Debug de notas\" -Filter "*_nfe_*" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 100 | Remove-Item -Force

# Resumos
Get-ChildItem "xmls\Debug de notas\" -Filter "*_resumo_*" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 50 | Remove-Item -Force
```

---

## 🎯 Conclusão

Os arquivos de debug fornecem visibilidade completa sobre:
- ✅ O que a SEFAZ está retornando
- ✅ Quais documentos estão sendo processados
- ✅ Quais eventos estão sendo detectados
- ✅ Por que alguns documentos são ignorados
- ✅ Performance e timing das operações

Use esses arquivos para diagnosticar qualquer problema de sincronização ou processamento de eventos.

---

**Última atualização**: 04/01/2026 11:20  
**Versão**: v2026-01-04-debug-enhanced
