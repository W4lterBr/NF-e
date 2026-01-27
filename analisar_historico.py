import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.execute('''
    SELECT id, certificado, informante, nsu_consultado, 
           total_xmls_retornados, total_nfe, total_cte, total_eventos, 
           data_hora_consulta, status
    FROM historico_nsu 
    ORDER BY id DESC 
    LIMIT 10
''')

print("=" * 80)
print("📊 ÚLTIMOS 10 REGISTROS DO HISTÓRICO NSU")
print("=" * 80)

for row in cursor:
    print(f"\nID: {row[0]}")
    print(f"  📜 Certificado: {row[1]}")
    print(f"  🏢 Informante: {row[2]}")
    print(f"  🔢 NSU: {row[3]}")
    print(f"  📦 Total XMLs: {row[4]}")
    print(f"  📄 NF-e: {row[5]}, CT-e: {row[6]}, Eventos: {row[7]}")
    print(f"  📅 Data/Hora: {row[8]}")
    print(f"  ✅ Status: {row[9]}")

# Estatísticas gerais
cursor = conn.execute('''
    SELECT 
        COUNT(*) as total_consultas,
        SUM(total_xmls_retornados) as total_xmls,
        SUM(total_nfe) as total_nfe,
        SUM(total_cte) as total_cte,
        SUM(total_eventos) as total_eventos
    FROM historico_nsu
''')

stats = cursor.fetchone()

print("\n" + "=" * 80)
print("📊 ESTATÍSTICAS GERAIS DO HISTÓRICO")
print("=" * 80)
print(f"Total de consultas registradas: {stats[0]}")
print(f"Total de XMLs processados: {stats[1]}")
print(f"  - NF-e: {stats[2]}")
print(f"  - CT-e: {stats[3]}")
print(f"  - Eventos: {stats[4]}")

# Verifica se há divergências (mesmo NSU consultado múltiplas vezes)
cursor = conn.execute('''
    SELECT informante, nsu_consultado, COUNT(*) as num_consultas
    FROM historico_nsu
    GROUP BY informante, nsu_consultado
    HAVING COUNT(*) > 1
''')

divergencias = cursor.fetchall()

if divergencias:
    print(f"\n⚠️ DIVERGÊNCIAS DETECTADAS: {len(divergencias)} NSUs consultados múltiplas vezes")
    for div in divergencias:
        print(f"  - Informante {div[0]}, NSU {div[1]}: {div[2]} consultas")
else:
    print("\n✅ Nenhuma divergência detectada (cada NSU consultado apenas 1 vez)")

conn.close()

print("\n" + "=" * 80)
