# 🔍 Troubleshooting: Eventos Não Aparecem

## Problema Identificado

Quando você clica em "Ver Eventos" e nenhum evento aparece, mesmo tendo eventos nos XMLs, o problema pode ter várias causas.

---

## ✅ Verificações Realizadas

### 1. Código de Processamento de Eventos
- ✅ **Status**: Implementado corretamente
- **Localização**: [nfe_search.py](nfe_search.py) linhas 2080-2150
- **Funcionalidade**: Detecta eventos (resEvento, procEventoNFe, evento) e os salva

### 2. Sistema de Logs
- ✅ **Status**: Funcionando
- **Arquivo**: `logs/busca_nfe_2026-01-04.log`
- **O que procurar**:
  ```
  🔧 VERSÃO DO CÓDIGO: Processamento de eventos ATIVADO (v2026-01-04)
  📋 Evento detectado (NSU=...)
  💾 Evento salvo na pasta Eventos/
  ```

### 3. Busca Local de Eventos
- ✅ **Status**: Funcionando
- **Localização**: [interface_pyqt5.py](interface_pyqt5.py) método `_mostrar_eventos()`
- **Performance**: ~600ms (1.6ms banco + 595ms arquivos XML)
- **Cobertura**: 22 pastas de Eventos, 3101 arquivos XML

---

## ❌ Causa Raiz do Problema

**O processo `nfe_search.py` está rodando com código desatualizado!**

### Como Isso Aconteceu?

1. O processo `nfe_search.py` foi iniciado **às 11:06:52**
2. As modificações no código foram feitas **DEPOIS das 11:06**
3. Python carrega o código uma vez na memória quando inicia
4. Mesmo salvando as alterações, o processo em execução continua usando o código antigo

### Evidência no Log

```log
2026-01-04 10:11:11,474 [INFO] 📦 [33251845000109] NF-e: Encontrados 50 documento(s) na resposta
2026-01-04 10:11:11,474 [INFO] 📄 [33251845000109] NF-e: Processando doc 1/50, NSU=000000000059057
```

**Falta a linha**: `🔧 VERSÃO DO CÓDIGO: Processamento de eventos ATIVADO (v2026-01-04)`

Isso comprova que o código em execução é a versão antiga.

---

## 🔧 Solução: Reiniciar o Processo

### Opção 1: Reiniciar pela Interface ✅ RECOMENDADO

1. Feche a aplicação PyQt5 (interface_pyqt5.py)
2. Aguarde alguns segundos
3. Reabra a aplicação

**Vantagem**: Automático e seguro

### Opção 2: Encerrar Processo Manualmente

```powershell
# Encontra processos Python relacionados ao bot
Get-Process | Where-Object { $_.ProcessName -eq "python" } | Select-Object Id, StartTime, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet64/1MB,2)}}

# Encerra processo específico (substitua XXXXX pelo ID)
Stop-Process -Id XXXXX -Force

# Ou encerra TODOS os processos Python (use com cuidado!)
Get-Process | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force
```

### Opção 3: Reiniciar o Computador

Se nada mais funcionar, reinicie o computador. Isso garante que todos os processos antigos sejam encerrados.

---

## 📊 Como Verificar se Funcionou

### 1. Após Reiniciar, Execute uma Busca

Clique em **"Buscar"** na interface.

### 2. Verifique o Log Atual

```powershell
Get-Content "logs\busca_nfe_$(Get-Date -Format 'yyyy-MM-dd').log" | Select-String "VERSÃO DO CÓDIGO"
```

**Se aparecer algo**, o código está atualizado! ✅

**Exemplo de saída esperada**:
```
2026-01-04 11:15:22,123 [INFO] 🔧 [47539664000197] VERSÃO DO CÓDIGO: Processamento de eventos ATIVADO (v2026-01-04)
```

### 3. Execute uma Busca e Verifique Eventos

```powershell
Get-Content "logs\busca_nfe_$(Get-Date -Format 'yyyy-MM-dd').log" | Select-String "Evento detectado|Evento salvo"
```

**Saída esperada** (se houver eventos novos):
```
2026-01-04 11:15:23,456 [INFO] 📋 [47539664000197] NF-e: Evento detectado (NSU=000000000059123)
2026-01-04 11:15:23,789 [INFO] 💾 [47539664000197] Evento salvo na pasta Eventos/
```

---

## 🌐 Estrutura de Eventos

### Onde os Eventos São Salvos

```
xmls/
└── [CNPJ_INFORMANTE]/
    └── [ANO-MÊS]/
        └── Eventos/
            ├── [NUMERO]-EVENTO_[TIPO].xml
            ├── 000123456-EVENTO_210210.xml  # Ciência da Operação
            ├── 000789012-EVENTO_210200.xml  # Confirmação da Operação
            ├── 001234567-EVENTO_110111.xml  # Cancelamento
            └── ...
```

### Tipos de Eventos Comuns

| Código | Descrição |
|--------|-----------|
| `110111` | Cancelamento de NF-e |
| `110110` | Carta de Correção Eletrônica |
| `210200` | Confirmação da Operação |
| `210210` | Ciência da Operação |
| `210220` | Desconhecimento da Operação |
| `210240` | Operação não Realizada |
| `610514` | Registro de Passagem (MDF-e/CT-e) |

### Banco de Dados

Manifestações são registradas na tabela `manifestacoes`:

```sql
SELECT * FROM manifestacoes WHERE chave = '52251215045348000172570010014772461002556120';
```

**Colunas**:
- `chave`: Chave de 44 dígitos do documento
- `tipo_evento`: Código do evento (ex: 210210)
- `informante`: CNPJ do certificado usado
- `data_manifestacao`: Timestamp do registro
- `status`: Status da manifestação (REGISTRADA, CONFIRMADA, etc.)
- `protocolo`: Número do protocolo SEFAZ

---

## 🐛 Debug Avançado

### Verificar Eventos Já Baixados

```powershell
# Conta total de XMLs de eventos
(Get-ChildItem -Path "xmls" -Recurse -Filter "*-EVENTO_*.xml").Count

# Lista eventos de um CNPJ específico
Get-ChildItem -Path "xmls\47539664000197" -Recurse -Filter "*-EVENTO_*.xml" | Select-Object Name, Directory
```

### Verificar Manifestações no Banco

```powershell
# Usando sqlite3 (instale se necessário)
sqlite3 notas.db "SELECT COUNT(*) AS total, tipo_evento, COUNT(DISTINCT chave) AS chaves_unicas FROM manifestacoes GROUP BY tipo_evento;"
```

### Testar Busca de Eventos na Interface

1. Abra a aplicação
2. Clique com botão direito em qualquer documento da lista
3. Selecione **"📋 Ver Eventos Locais"**
4. Observe os logs de debug:
   ```
   [DEBUG EVENTOS] FASE 1: Buscando no banco de dados
   [⏱️ TIMING] Busca no banco de dados: 0.0016s
   [DEBUG EVENTOS] FASE 2: Buscando em arquivos XML
   [⏱️ TIMING] Busca em arquivos XML: 0.5997s
   ```

---

## ⚠️ Erro 656 - Consultas Muito Frequentes

Se você vê no log:
```
⏰ Motivo do erro 656: Consultas muito frequentes (< 1 hora)
```

**O que significa**: A SEFAZ bloqueou consultas por 1 hora devido a requisições muito frequentes.

**Solução**: 
- Aguarde 1 hora desde a última consulta bem-sucedida
- O sistema tem cooldown automático e pulará certificados bloqueados
- Novos eventos **NÃO** serão baixados enquanto o certificado estiver em cooldown

**Verificar quando pode consultar novamente**:
```sql
SELECT informante, ultima_consulta, proximo_acesso 
FROM certificados_consulta 
WHERE bloqueado = 1;
```

---

## 📋 Checklist de Resolução

- [ ] **Passo 1**: Verificar se `nfe_search.py` está rodando
- [ ] **Passo 2**: Verificar hora de início do processo (deve ser DEPOIS das modificações)
- [ ] **Passo 3**: Fechar aplicação e aguardar processos terminarem
- [ ] **Passo 4**: Reabrir aplicação
- [ ] **Passo 5**: Clicar em "Buscar" para iniciar nova consulta
- [ ] **Passo 6**: Verificar log para confirmar versão atualizada: `🔧 VERSÃO DO CÓDIGO`
- [ ] **Passo 7**: Aguardar cooldown do erro 656 (se aplicável)
- [ ] **Passo 8**: Testar "Ver Eventos Locais" em um documento

---

## 🎯 Resultado Esperado

Após seguir todos os passos:

1. ✅ O log deve mostrar: **"VERSÃO DO CÓDIGO: Processamento de eventos ATIVADO (v2026-01-04)"**
2. ✅ Ao clicar com direito → "📋 Ver Eventos Locais", deve mostrar eventos (se existirem)
3. ✅ Novos eventos baixados da SEFAZ devem ser processados automaticamente
4. ✅ Eventos são salvos em `xmls/[CNPJ]/[ANO-MÊS]/Eventos/`
5. ✅ Manifestações são registradas na tabela `manifestacoes`

---

## 📞 Suporte Adicional

Se após reiniciar o processo os eventos ainda não aparecem:

1. **Verifique se há eventos nos XMLs**:
   ```powershell
   Get-ChildItem -Path "xmls" -Recurse -Filter "*-EVENTO_*.xml" | Measure-Object
   ```
   Se retornar 0, significa que **não há eventos salvos localmente**.

2. **Execute uma busca completa**:
   - Aguarde o cooldown do erro 656 terminar
   - Clique em "Buscar" e deixe processar
   - Novos eventos serão baixados e salvos

3. **Verifique permissões de arquivo**:
   Certifique-se de que o programa tem permissão para ler/escrever na pasta `xmls/`

4. **Consulte os logs detalhados**:
   ```powershell
   Get-Content "logs\busca_nfe_$(Get-Date -Format 'yyyy-MM-dd').log" | Out-File "debug_completo.txt"
   ```
   Analise o arquivo `debug_completo.txt` em busca de erros.

---

**Última atualização**: 04/01/2026 11:15  
**Versão do código**: v2026-01-04  
**Status**: Código implementado, aguardando reinício do processo
