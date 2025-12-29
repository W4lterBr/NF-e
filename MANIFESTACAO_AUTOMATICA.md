# 🔄 Sistema de Controle de Manifestações Automáticas

## Objetivo

Evitar o envio de manifestações duplicadas (especialmente **Ciência da Operação - 210210**) para o mesmo XML.

## ✅ Implementação Concluída

### 1. Tabela `manifestacoes` no Banco de Dados

```sql
CREATE TABLE manifestacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL,
    tipo_evento TEXT NOT NULL,
    informante TEXT NOT NULL,
    data_manifestacao TEXT NOT NULL,
    status TEXT,
    protocolo TEXT,
    UNIQUE(chave, tipo_evento, informante)
)

-- Índices para busca rápida
CREATE INDEX idx_manifestacoes_chave ON manifestacoes(chave)
CREATE INDEX idx_manifestacoes_informante ON manifestacoes(informante)
```

### 2. Métodos Disponíveis em `DatabaseManager`

#### Verificar se já foi manifestada

```python
from modules.database import DatabaseManager

db = DatabaseManager()

# Verifica se já enviou ciência para esta nota
ja_manifestada = db.check_manifestacao_exists(
    chave="35241234567890123456789012345678901234567890",
    tipo_evento="210210",  # Ciência da Operação
    informante="12345678000190"  # CNPJ do informante
)

if ja_manifestada:
    print("⏭️ Ciência já manifestada - pulando")
else:
    print("✅ Pode enviar manifestação")
```

#### Registrar manifestação enviada

```python
# Após enviar a manifestação com sucesso
sucesso = db.register_manifestacao(
    chave="35241234567890123456789012345678901234567890",
    tipo_evento="210210",
    informante="12345678000190",
    status="ENVIADA",
    protocolo="135240123456789"  # Protocolo retornado pela SEFAZ
)

if sucesso:
    print("✅ Manifestação registrada")
else:
    print("⚠️ Manifestação já estava registrada")
```

## 📋 Tipos de Eventos

| Código | Tipo | Descrição |
|--------|------|-----------|
| **210210** | Ciência da Operação | ❓ Reconhece o recebimento da NF-e |
| **210200** | Confirmação da Operação | 📬 Confirma a operação |
| **210220** | Desconhecimento da Operação | ⛔ Informa desconhecimento |
| **210240** | Operação não Realizada | 🚫 Informa que não realizou a operação |
| **110111** | Cancelamento | ❌ Cancela a NF-e (emitente) |
| **110110** | Carta de Correção | ✏️ Corrige dados da NF-e |

## 🔧 Como Integrar no Código de Manifestação Automática

### Exemplo de Integração

```python
from modules.database import DatabaseManager
from nfe_search import NFEService  # ou módulo que envia eventos

def manifestar_ciencia_automatica(chave_nfe: str, cnpj_informante: str):
    """
    Envia Ciência da Operação automaticamente, evitando duplicatas.
    
    Args:
        chave_nfe: Chave de acesso de 44 dígitos
        cnpj_informante: CNPJ do destinatário que está manifestando
    
    Returns:
        dict: Resultado da operação
    """
    db = DatabaseManager()
    tipo_evento = "210210"  # Ciência da Operação
    
    # 1️⃣ VERIFICA SE JÁ FOI MANIFESTADA
    if db.check_manifestacao_exists(chave_nfe, tipo_evento, cnpj_informante):
        print(f"⏭️ Ciência já manifestada para {chave_nfe[:10]}... - pulando")
        return {
            'ok': True,
            'mensagem': 'Manifestação já registrada anteriormente',
            'duplicada': True
        }
    
    # 2️⃣ ENVIA A MANIFESTAÇÃO PARA A SEFAZ
    try:
        nfe_service = NFEService()
        resultado = nfe_service.enviar_evento(
            chave=chave_nfe,
            tipo_evento=tipo_evento,
            cnpj_informante=cnpj_informante,
            justificativa="Ciencia da operacao"  # Opcional para 210210
        )
        
        if resultado.get('ok') and resultado.get('protocolo'):
            # 3️⃣ REGISTRA NO BANCO PARA EVITAR DUPLICATA
            db.register_manifestacao(
                chave=chave_nfe,
                tipo_evento=tipo_evento,
                informante=cnpj_informante,
                status="ENVIADA",
                protocolo=resultado['protocolo']
            )
            
            print(f"✅ Ciência manifestada com sucesso: {chave_nfe[:10]}...")
            return {
                'ok': True,
                'mensagem': 'Manifestação enviada e registrada',
                'protocolo': resultado['protocolo']
            }
        else:
            print(f"❌ Erro ao enviar ciência: {resultado.get('erro')}")
            return {
                'ok': False,
                'mensagem': resultado.get('erro', 'Erro desconhecido')
            }
    
    except Exception as e:
        print(f"❌ Exceção ao manifestar ciência: {e}")
        return {
            'ok': False,
            'mensagem': str(e)
        }


# 🔄 EXEMPLO DE USO EM LOOP DE PROCESSAMENTO
def processar_nfes_recebidas(nfes: list, cnpj_destinatario: str):
    """Processa lista de NF-es recebidas e manifesta ciência."""
    
    for nfe in nfes:
        chave = nfe.get('chave')
        
        if not chave or len(chave) != 44:
            continue
        
        # Manifesta ciência automaticamente
        resultado = manifestar_ciencia_automatica(chave, cnpj_destinatario)
        
        if resultado.get('duplicada'):
            print(f"  ⏭️ {chave[:10]}... - já manifestada")
        elif resultado.get('ok'):
            print(f"  ✅ {chave[:10]}... - ciência enviada")
        else:
            print(f"  ❌ {chave[:10]}... - erro: {resultado.get('mensagem')}")
```

## 🎯 Benefícios

✅ **Evita duplicatas**: Constraint UNIQUE no banco garante apenas 1 manifestação por (chave + tipo + informante)

✅ **Performance**: Índices permitem verificação rápida antes de enviar

✅ **Auditoria**: Registra data/hora, status e protocolo de cada manifestação

✅ **Consistência**: Mesmo que o processo rode múltiplas vezes, não enviará duplicatas

✅ **Histórico**: Mantém rastreamento de todas as manifestações enviadas

## 🔍 Consultas Úteis

### Ver todas as manifestações de um CNPJ

```python
import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.execute('''
    SELECT chave, tipo_evento, data_manifestacao, status, protocolo
    FROM manifestacoes
    WHERE informante = ?
    ORDER BY data_manifestacao DESC
    LIMIT 100
''', ('12345678000190',))

for row in cursor:
    print(f"{row[0][:10]}... | {row[1]} | {row[2]} | {row[3]}")
```

### Ver manifestações de uma nota específica

```python
cursor = conn.execute('''
    SELECT tipo_evento, informante, data_manifestacao, status, protocolo
    FROM manifestacoes
    WHERE chave = ?
''', ('35241234567890123456789012345678901234567890',))

for row in cursor:
    print(f"{row[0]} | {row[1]} | {row[2]}")
```

### Contar manifestações por tipo

```python
cursor = conn.execute('''
    SELECT tipo_evento, COUNT(*) as total
    FROM manifestacoes
    GROUP BY tipo_evento
    ORDER BY total DESC
''')

eventos = {
    '210210': 'Ciência',
    '210200': 'Confirmação',
    '210220': 'Desconhecimento',
    '210240': 'Não Realizada'
}

for row in cursor:
    nome = eventos.get(row[0], row[0])
    print(f"{nome}: {row[1]}")
```

## ⚠️ Observações Importantes

1. **Registro antes do XML**: Registre a manifestação no banco ANTES de salvar o XML do evento, para evitar processamento duplicado caso o processo seja interrompido.

2. **Tratamento de erros**: Se a SEFAZ rejeitar a manifestação, NÃO registre no banco. Só registre quando `cStat = 135` (evento registrado).

3. **Múltiplos CNPJs**: O sistema permite que diferentes CNPJs manifestem a mesma nota (ex: matriz e filial). A constraint UNIQUE diferencia por `(chave, tipo_evento, informante)`.

4. **Limpeza**: Considere limpar manifestações antigas (ex: mais de 1 ano) para manter o banco leve.

## 🚀 Próximos Passos

1. **Integrar no worker de distribuição**: Adicionar verificação antes de enviar eventos automáticos
2. **Interface gráfica**: Mostrar ícone ✅ na tabela quando manifestação já foi enviada
3. **Relatório**: Adicionar tela de relatório de manifestações enviadas
4. **Retry**: Sistema de re-tentativa para manifestações que falharam

---

**Documentação criada em**: 2025  
**Autor**: Sistema BOT - Busca NFE  
**Versão**: 1.0
