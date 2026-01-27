"""
🔍 DIAGNÓSTICO COMPLETO - NF-e APÓS 02/01/2026
================================================

Este script investiga por que as NF-e após 02/01/2026 não estão aparecendo.
"""

import sqlite3
from datetime import datetime, timedelta

print("=" * 80)
print("🔍 DIAGNÓSTICO: NF-e AUSENTES APÓS 02/01/2026")
print("=" * 80)

conn = sqlite3.connect('notas.db')

# 1. Verificar últimas notas por empresa
print("\n📊 1. ÚLTIMAS NF-e POR EMPRESA (todas as datas)")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        informante,
        MAX(data_emissao) as ultima_data,
        COUNT(*) as total_notas,
        COUNT(CASE WHEN date(data_emissao) >= '2026-01-02' THEN 1 END) as notas_apos_02_01
    FROM notas_detalhadas
    WHERE tipo = 'NF-e'
    GROUP BY informante
    ORDER BY ultima_data DESC
""")

for row in cursor:
    print(f"\nInformante: {row[0]}")
    print(f"  Última nota: {row[1]}")
    print(f"  Total de NF-e: {row[2]}")
    print(f"  NF-e após 02/01/2026: {row[3]}")
    
    if row[3] == 0 and row[1]:
        # Verifica diferença de dias
        try:
            ultima = datetime.strptime(row[1], '%Y-%m-%d')
            hoje = datetime.now()
            diff = (hoje - ultima).days
            if diff > 5:
                print(f"  ⚠️ ATENÇÃO: Última nota há {diff} dias!")
        except:
            pass

# 2. Contar notas por mês/ano
print("\n\n📊 2. NF-e POR MÊS")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        strftime('%Y-%m', data_emissao) as mes,
        COUNT(*) as total
    FROM notas_detalhadas
    WHERE tipo = 'NF-e'
    GROUP BY mes
    ORDER BY mes DESC
    LIMIT 6
""")

for row in cursor:
    print(f"  {row[0]}: {row[1]} notas")

# 3. Verificar NSU atual vs último processado
print("\n\n📊 3. NSU ATUAL DE CADA EMPRESA")
print("-" * 80)

cursor = conn.execute("""
    SELECT informante, ult_nsu
    FROM nsu
    ORDER BY informante
""")

nsus = {}
for row in cursor:
    nsus[row[0]] = row[1]
    print(f"\nInformante: {row[0]}")
    print(f"  NSU atual no banco: {row[1]}")

# 4. Verificar histórico NSU - últimas consultas
print("\n\n📊 4. HISTÓRICO DE CONSULTAS NSU (Últimas 10)")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        informante,
        nsu_consultado,
        total_xmls_retornados,
        total_nfe,
        total_eventos,
        data_hora_consulta,
        status
    FROM historico_nsu
    ORDER BY id DESC
    LIMIT 10
""")

for row in cursor:
    print(f"\nInformante: {row[0]}")
    print(f"  NSU consultado: {row[1]}")
    print(f"  XMLs retornados: {row[2]} (NF-e: {row[3]}, Eventos: {row[4]})")
    print(f"  Data/Hora: {row[5]}")
    print(f"  Status: {row[6]}")

# 5. Verificar bloqueios por erro 656
print("\n\n📊 5. BLOQUEIOS POR ERRO 656")
print("-" * 80)

cursor = conn.execute("""
    SELECT informante, ultimo_erro, nsu_bloqueado
    FROM erro_656
""")

bloqueios = cursor.fetchall()
if bloqueios:
    for row in bloqueios:
        print(f"\nInformante: {row[0]}")
        print(f"  Último erro: {row[1]}")
        print(f"  NSU bloqueado: {row[2]}")
        
        # Calcula tempo desde último erro
        try:
            ultimo = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
            agora = datetime.now()
            diff_min = (agora - ultimo).total_seconds() / 60
            print(f"  Tempo desde bloqueio: {diff_min:.0f} minutos")
            if diff_min > 65:
                print(f"  ✅ Bloqueio expirado - pode buscar novamente")
            else:
                print(f"  🔒 Bloqueado por mais {65-diff_min:.0f} minutos")
        except:
            pass
else:
    print("  ✅ Nenhum bloqueio ativo")

# 6. Verificar últimas 20 notas de QUALQUER tipo
print("\n\n📊 6. ÚLTIMAS 20 NOTAS/DOCUMENTOS (TODOS OS TIPOS)")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        chave,
        tipo,
        numero,
        data_emissao,
        nome_emitente,
        valor,
        informante,
        nsu
    FROM notas_detalhadas
    ORDER BY data_emissao DESC, atualizado_em DESC
    LIMIT 20
""")

print(f"\n{'Data':<12} {'Tipo':<8} {'Número':<10} {'Emitente':<30} {'NSU':<18} {'Informante':<16}")
print("-" * 120)

for row in cursor:
    data = row[3] if row[3] else 'N/A'
    tipo = row[1] if row[1] else 'N/A'
    numero = row[2] if row[2] else 'N/A'
    emitente = (row[4][:27] + '...') if row[4] and len(row[4]) > 30 else (row[4] if row[4] else 'N/A')
    nsu = row[7] if row[7] else 'SEM NSU'
    informante = row[6] if row[6] else 'N/A'
    
    print(f"{data:<12} {tipo:<8} {numero:<10} {emitente:<30} {nsu:<18} {informante:<16}")

# 7. Análise específica: NF-e após 02/01/2026
print("\n\n📊 7. NF-e ESPECÍFICAS APÓS 02/01/2026")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        chave,
        numero,
        data_emissao,
        nome_emitente,
        informante,
        nsu
    FROM notas_detalhadas
    WHERE tipo = 'NF-e' 
    AND date(data_emissao) >= '2026-01-02'
    ORDER BY data_emissao DESC
    LIMIT 50
""")

resultados = cursor.fetchall()

if resultados:
    print(f"\n✅ ENCONTRADAS {len(resultados)} NF-e APÓS 02/01/2026:")
    print(f"\n{'Data':<12} {'Número':<10} {'Emitente':<30} {'NSU':<18} {'Informante':<16}")
    print("-" * 100)
    
    for row in resultados:
        data = row[2] if row[2] else 'N/A'
        numero = row[1] if row[1] else 'N/A'
        emitente = (row[3][:27] + '...') if row[3] and len(row[3]) > 30 else (row[3] if row[3] else 'N/A')
        nsu = row[5] if row[5] else 'SEM NSU'
        informante = row[4] if row[4] else 'N/A'
        
        print(f"{data:<12} {numero:<10} {emitente:<30} {nsu:<18} {informante:<16}")
else:
    print("\n❌ NENHUMA NF-e ENCONTRADA APÓS 02/01/2026 NO BANCO DE DADOS!")
    print("\n🔍 Investigando possíveis causas...")
    
    # Verifica se há CT-e após essa data
    cursor = conn.execute("""
        SELECT COUNT(*) 
        FROM notas_detalhadas
        WHERE tipo = 'CT-e' 
        AND date(data_emissao) >= '2026-01-02'
    """)
    
    ct_count = cursor.fetchone()[0]
    print(f"\n   CT-e após 02/01/2026: {ct_count}")
    
    # Verifica última data com NF-e
    cursor = conn.execute("""
        SELECT MAX(data_emissao)
        FROM notas_detalhadas
        WHERE tipo = 'NF-e'
    """)
    
    ultima_nfe = cursor.fetchone()[0]
    print(f"   Última NF-e no banco: {ultima_nfe}")

# 8. Verificar registros sem data de emissão
print("\n\n📊 8. REGISTROS SEM DATA DE EMISSÃO")
print("-" * 80)

cursor = conn.execute("""
    SELECT 
        COUNT(*) as total,
        tipo
    FROM notas_detalhadas
    WHERE data_emissao IS NULL OR data_emissao = ''
    GROUP BY tipo
""")

sem_data = cursor.fetchall()
if sem_data:
    for row in sem_data:
        print(f"  {row[1]}: {row[0]} registros sem data")
else:
    print("  ✅ Todos os registros têm data de emissão")

# 9. Análise por informante - buscar lacunas de NSU
print("\n\n📊 9. ANÁLISE DE NSU POR INFORMANTE")
print("-" * 80)

for informante, nsu_atual in nsus.items():
    print(f"\n📋 Informante: {informante}")
    print(f"   NSU atual: {nsu_atual}")
    
    # Busca NSU mínimo e máximo no banco
    cursor = conn.execute("""
        SELECT 
            MIN(CAST(nsu AS INTEGER)) as min_nsu,
            MAX(CAST(nsu AS INTEGER)) as max_nsu,
            COUNT(*) as total_docs
        FROM notas_detalhadas
        WHERE informante = ? 
        AND nsu IS NOT NULL 
        AND nsu != ''
        AND nsu != '000000000000000'
    """, (informante,))
    
    result = cursor.fetchone()
    if result and result[0]:
        print(f"   NSU no banco: {result[0]} → {result[1]} ({result[2]} documentos)")
        
        nsu_atual_int = int(nsu_atual)
        max_nsu_banco = result[1]
        
        if nsu_atual_int > max_nsu_banco:
            diff = nsu_atual_int - max_nsu_banco
            print(f"   ⚠️ GAP detectado: {diff} NSUs entre último no banco e NSU atual!")
            print(f"   🔍 Possível causa: Documentos não foram salvos no banco")

# 10. Resumo e diagnóstico
print("\n\n" + "=" * 80)
print("📋 RESUMO DO DIAGNÓSTICO")
print("=" * 80)

# Total de NF-e no banco
cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo = 'NF-e'")
total_nfe = cursor.fetchone()[0]

# Total após 02/01/2026
cursor = conn.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE tipo = 'NF-e' 
    AND date(data_emissao) >= '2026-01-02'
""")
nfe_apos_02_01 = cursor.fetchone()[0]

print(f"\n📊 Estatísticas:")
print(f"   Total de NF-e no banco: {total_nfe}")
print(f"   NF-e após 02/01/2026: {nfe_apos_02_01}")

if nfe_apos_02_01 == 0:
    print("\n❌ PROBLEMA CONFIRMADO: Nenhuma NF-e após 02/01/2026")
    print("\n🔍 Possíveis causas:")
    print("   1. Sistema não está buscando novos documentos")
    print("   2. Erro 656 bloqueando buscas")
    print("   3. NSU não está avançando")
    print("   4. Documentos sendo baixados mas não salvos no banco")
    print("   5. Filtro na interface impedindo visualização")
else:
    print(f"\n✅ Existem {nfe_apos_02_01} NF-e após 02/01/2026 no banco")
    print("\n🔍 Possíveis causas da não-visualização:")
    print("   1. Filtro ativo na interface")
    print("   2. Ordenação incorreta")
    print("   3. CNPJ/Certificado específico não selecionado")

conn.close()

print("\n" + "=" * 80)
print("✅ Diagnóstico completo!")
print("=" * 80)
