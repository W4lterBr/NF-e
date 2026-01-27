"""
🔍 INVESTIGAÇÃO PROFUNDA - Por que NF-e não estão sendo salvas?
==============================================================

Este script vai investigar:
1. Se os XMLs têm NF-e nos detalhes_json
2. Se a função salvar_nota_detalhada está sendo chamada
3. Se há erros durante o salvamento
"""

import sqlite3
import json
from datetime import datetime

print("=" * 80)
print("🔍 INVESTIGAÇÃO: Por que NF-e não estão no banco?")
print("=" * 80)

conn = sqlite3.connect('notas.db')

# 1. Analisar detalhes_json do histórico
print("\n📊 1. ANÁLISE DO HISTÓRICO NSU - DETALHES DOS XMLs")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        id,
        informante,
        nsu_consultado,
        total_nfe,
        total_eventos,
        detalhes_json,
        data_hora_consulta
    FROM historico_nsu
    WHERE id >= 7
    ORDER BY id DESC
""")

registros = cursor.fetchall()

for row in registros:
    id_hist, informante, nsu, total_nfe, total_eventos, detalhes_json, data_hora = row
    
    print(f"\n🔍 Registro #{id_hist} - {data_hora}")
    print(f"   Informante: {informante}")
    print(f"   NSU: {nsu}")
    print(f"   Total NF-e: {total_nfe}")
    print(f"   Total Eventos: {total_eventos}")
    
    if detalhes_json:
        try:
            detalhes = json.loads(detalhes_json)
            print(f"   Documentos no JSON: {len(detalhes)}")
            
            # Analisa cada documento
            nfes_lista = []
            eventos_lista = []
            
            for doc in detalhes:
                if doc.get('tipo') == 'nfe':
                    nfes_lista.append({
                        'chave': doc.get('chave', 'N/A')[:15] + '...',
                        'numero': doc.get('numero', 'N/A')
                    })
                elif doc.get('tipo') == 'evento':
                    eventos_lista.append({
                        'chave': doc.get('chave', 'N/A')[:15] + '...',
                        'evento': doc.get('evento', 'N/A')
                    })
            
            if nfes_lista:
                print(f"\n   ✅ NF-e encontradas no JSON ({len(nfes_lista)}):")
                for nfe in nfes_lista[:5]:  # Mostra primeiras 5
                    print(f"      - Chave: {nfe['chave']}, Número: {nfe['numero']}")
                
                # IMPORTANTE: Verifica se essas NF-e estão no banco
                print(f"\n   🔍 Verificando se essas NF-e estão na tabela notas_detalhadas...")
                
                for nfe in nfes_lista:
                    chave_parcial = nfe['chave'].replace('...', '')
                    cursor_check = conn.execute("""
                        SELECT COUNT(*) 
                        FROM notas_detalhadas 
                        WHERE chave LIKE ? 
                        AND tipo = 'NF-e'
                    """, (chave_parcial + '%',))
                    
                    count = cursor_check.fetchone()[0]
                    if count > 0:
                        print(f"      ✅ Chave {nfe['chave']} ESTÁ no banco")
                    else:
                        print(f"      ❌ Chave {nfe['chave']} NÃO ESTÁ no banco!")
                        print(f"         ⚠️ PROBLEMA: NF-e foi processada mas não salva!")
            else:
                print(f"   📭 Nenhuma NF-e no JSON (apenas eventos)")
            
            if eventos_lista:
                print(f"\n   📋 Eventos encontrados ({len(eventos_lista)}):")
                for evt in eventos_lista[:3]:  # Mostra primeiros 3
                    print(f"      - Chave: {evt['chave']}, Tipo: {evt['evento']}")
        
        except json.JSONDecodeError as e:
            print(f"   ❌ Erro ao decodificar JSON: {e}")
    else:
        print(f"   ⚠️ Sem detalhes_json")

# 2. Verificar se há NF-e na tabela notas_detalhadas (TODOS os registros)
print("\n\n📊 2. NF-e NA TABELA notas_detalhadas")
print("-" * 80)

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE tipo = 'NF-e' OR tipo = 'NFe'
""")
total_nfe = cursor.fetchone()[0]

print(f"\nTotal de NF-e no banco: {total_nfe}")

if total_nfe == 0:
    print("\n❌ CONFIRMADO: ZERO NF-e no banco de dados!")
    print("\n🔍 Possíveis causas:")
    print("   1. A função salvar_nota_detalhada() não está sendo executada")
    print("   2. Há erro silencioso durante o INSERT")
    print("   3. O campo 'tipo' está sendo preenchido com valor diferente de 'NF-e'")
    print("   4. As NF-e estão sendo ignoradas durante processamento")
    
    # Verifica se há registros com outros tipos
    cursor = conn.execute("""
        SELECT tipo, COUNT(*) 
        FROM notas_detalhadas 
        GROUP BY tipo
    """)
    
    tipos = cursor.fetchall()
    if tipos:
        print("\n📊 Tipos de documentos no banco:")
        for tipo, count in tipos:
            print(f"   {tipo}: {count}")
    else:
        print("\n📭 Tabela notas_detalhadas está VAZIA!")

# 3. Verificar estrutura da tabela notas_detalhadas
print("\n\n📊 3. ESTRUTURA DA TABELA notas_detalhadas")
print("-" * 80)

cursor = conn.execute("PRAGMA table_info(notas_detalhadas)")
colunas = cursor.fetchall()

print("\nColunas:")
for col in colunas:
    print(f"   {col[1]} ({col[2]})")

# 4. Verificar últimos registros (qualquer tipo)
print("\n\n📊 4. ÚLTIMOS 10 REGISTROS NA TABELA notas_detalhadas")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        tipo,
        chave,
        numero,
        data_emissao,
        nome_emitente,
        informante,
        nsu,
        atualizado_em
    FROM notas_detalhadas
    ORDER BY atualizado_em DESC
    LIMIT 10
""")

registros = cursor.fetchall()

if registros:
    print(f"\n{'Tipo':<10} {'Número':<10} {'Data Emissão':<12} {'Emitente':<30} {'NSU':<18}")
    print("-" * 100)
    
    for row in registros:
        tipo = row[0] if row[0] else 'N/A'
        numero = row[2] if row[2] else 'N/A'
        data_emissao = row[3] if row[3] else 'N/A'
        emitente = (row[4][:27] + '...') if row[4] and len(row[4]) > 30 else (row[4] if row[4] else 'N/A')
        nsu = row[6] if row[6] else 'SEM NSU'
        
        print(f"{tipo:<10} {numero:<10} {data_emissao:<12} {emitente:<30} {nsu:<18}")
else:
    print("\n📭 Nenhum registro na tabela notas_detalhadas")

# 5. Verificar se há XMLs salvos em xmls_baixados
print("\n\n📊 5. XMLs SALVOS (xmls_baixados)")
print("-" * 80)

cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM xmls_baixados
""")
total_xmls = cursor.fetchone()[0]

print(f"\nTotal de XMLs em xmls_baixados: {total_xmls}")

cursor = conn.execute("""
    SELECT 
        chave,
        informante,
        caminho_arquivo,
        baixado_em
    FROM xmls_baixados
    ORDER BY baixado_em DESC
    LIMIT 5
""")

xmls = cursor.fetchall()

if xmls:
    print("\nÚltimos 5 XMLs salvos:")
    for xml in xmls:
        chave = xml[0][:20] + '...'
        informante = xml[1] if xml[1] else 'N/A'
        caminho = xml[2] if xml[2] else 'N/A'
        baixado = xml[3] if xml[3] else 'N/A'
        print(f"   Chave: {chave}, Informante: {informante}, Baixado: {baixado}")

# 6. Análise crítica - Cruzar histórico com notas_detalhadas
print("\n\n📊 6. ANÁLISE CRÍTICA - Divergências")
print("-" * 80)

# Busca NF-e do histórico que deveriam estar no banco
cursor = conn.execute("""
    SELECT 
        id,
        informante,
        nsu_consultado,
        total_nfe,
        detalhes_json
    FROM historico_nsu
    WHERE total_nfe > 0
    AND id >= 7
""")

registros_com_nfe = cursor.fetchall()

print(f"\n🔍 Encontrados {len(registros_com_nfe)} registros no histórico COM NF-e")

divergencias = 0

for row in registros_com_nfe:
    id_hist, informante, nsu, total_nfe, detalhes_json = row
    
    print(f"\n📋 Histórico #{id_hist} - NSU {nsu}")
    print(f"   Total NF-e declarado: {total_nfe}")
    
    if detalhes_json:
        try:
            detalhes = json.loads(detalhes_json)
            nfes_json = [d for d in detalhes if d.get('tipo') == 'nfe']
            
            print(f"   NF-e no JSON: {len(nfes_json)}")
            
            # Para cada NF-e, verifica se está no banco
            for nfe in nfes_json:
                chave = nfe.get('chave', '')
                if chave and len(chave) >= 44:
                    cursor_check = conn.execute("""
                        SELECT COUNT(*) 
                        FROM notas_detalhadas 
                        WHERE chave = ?
                    """, (chave,))
                    
                    count = cursor_check.fetchone()[0]
                    if count == 0:
                        print(f"   ❌ NF-e AUSENTE: Chave {chave[:25]}...")
                        divergencias += 1
                    else:
                        print(f"   ✅ NF-e PRESENTE: Chave {chave[:25]}...")
        
        except Exception as e:
            print(f"   ❌ Erro ao analisar JSON: {e}")

if divergencias > 0:
    print(f"\n⚠️⚠️⚠️ PROBLEMA GRAVE: {divergencias} NF-e(s) foram processadas mas NÃO ESTÃO no banco!")
    print("\n🔍 Diagnóstico:")
    print("   As NF-e foram:")
    print("   1. ✅ Baixadas da SEFAZ")
    print("   2. ✅ Processadas pelo sistema")
    print("   3. ✅ Registradas no histórico")
    print("   4. ❌ NÃO SALVAS na tabela notas_detalhadas")
    print("\n   Possíveis causas:")
    print("   - Erro silencioso no db.salvar_nota_detalhada()")
    print("   - Exception sendo capturada sem log")
    print("   - Campo 'tipo' com valor diferente de 'NF-e'")
    print("   - Commit do banco não sendo executado")
else:
    print(f"\n✅ Todas as NF-e do histórico estão no banco")

conn.close()

print("\n" + "=" * 80)
print("✅ Investigação completa!")
print("=" * 80)
