import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

print("=" * 80)
print("ANÁLISE DE NFS-e NO BANCO")
print("=" * 80)

# Total por tipo
cursor.execute("SELECT COUNT(*), tipo FROM notas_detalhadas GROUP BY tipo")
print("\n📊 Documentos por tipo:")
for count, tipo in cursor.fetchall():
    print(f"  {tipo}: {count}")

# Verifica se tabela nfse existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nfse'")
tem_tabela_nfse = cursor.fetchone()
print(f"\n📁 Tabela 'nfse' existe: {bool(tem_tabela_nfse)}")

if tem_tabela_nfse:
    cursor.execute("SELECT COUNT(*) FROM nfse")
    total_nfse = cursor.fetchone()[0]
    print(f"  Total na tabela nfse: {total_nfse}")

# Verifica NFS-e em notas_detalhadas
cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo LIKE '%NFS%'")
nfse_count = cursor.fetchone()[0]
print(f"\n🔍 NFS-e em notas_detalhadas: {nfse_count}")

if nfse_count > 0:
    cursor.execute("SELECT chave, numero, nome_emitente, data_emissao, valor FROM notas_detalhadas WHERE tipo LIKE '%NFS%' LIMIT 5")
    print("\n  Exemplos:")
    for row in cursor.fetchall():
        print(f"    - Chave: {row[0][:30]}... | NF {row[1]} | {row[2][:30]} | {row[3]} | R$ {row[4]}")

# Verifica xml_status das NFS-e
cursor.execute("SELECT xml_status, COUNT(*) FROM notas_detalhadas WHERE tipo LIKE '%NFS%' GROUP BY xml_status")
print("\n📋 Status das NFS-e:")
for status, count in cursor.fetchall():
    print(f"  {status}: {count}")

conn.close()
print("\n" + "=" * 80)
