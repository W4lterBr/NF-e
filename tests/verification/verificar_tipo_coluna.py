import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Valores ÚNICOS na coluna 'tipo':")
c.execute("SELECT DISTINCT tipo FROM notas_detalhadas ORDER BY tipo")
for (tipo,) in c.fetchall():
    print(f"  '{tipo}'")

print("\n" + "="*70)

print("\nContagem por tipo:")
c.execute("SELECT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo ORDER BY tipo")
for tipo, count in c.fetchall():
    print(f"  '{tipo}': {count}")

print("\n" + "="*70)

print("\nAmostra de NFS-e (primeiras 5):")
c.execute("""
    SELECT numero, data_emissao, tipo, nome_emitente 
    FROM notas_detalhadas 
    WHERE tipo LIKE '%NFS%' OR tipo LIKE '%nfs%'
    ORDER BY data_emissao DESC
    LIMIT 5
""")
for num, data, tipo, nome in c.fetchall():
    print(f"  N: {num}, Data: {data}, Tipo: '{tipo}', Emit: {nome[:30] if nome else 'N/A'}")

conn.close()
