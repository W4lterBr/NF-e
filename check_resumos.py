import sqlite3

conn = sqlite3.connect('notas_test.db')
cur = conn.execute('SELECT chave, xml_status FROM notas_detalhadas WHERE xml_status = "RESUMO" LIMIT 5')
rows = cur.fetchall()

print(f"Total de RESUMOS: {len(rows)}")
for r in rows:
    print(f"  Chave: {r[0]}, Status: {r[1]}")
