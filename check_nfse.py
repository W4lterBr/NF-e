import sqlite3

conn = sqlite3.connect('notas_test.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFSe'")
total = c.fetchone()[0]
print(f'Total NFS-e: {total}')

c.execute("SELECT numero, valor, nome_emitente FROM notas_detalhadas WHERE tipo='NFSe' LIMIT 10")
rows = c.fetchall()
print('\nAmostra:')
for r in rows:
    numero = r[0] if r[0] else "VAZIO"
    valor = f"R$ {float(r[1]):,.2f}" if r[1] and float(r[1]) > 0 else "R$ 0,00"
    emitente = r[2] or "N/A"
    print(f'  N: {numero}, {valor}, Emit: {emitente[:30]}')

conn.close()
