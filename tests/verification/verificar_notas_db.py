import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

c.execute('SELECT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo')
print('Documentos em notas.db:')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')

print()

c.execute('SELECT numero, valor, nome_emitente FROM notas_detalhadas WHERE tipo="NFS-e" LIMIT 5')
print('Amostra NFS-e:')
for r in c.fetchall():
    valor_fmt = f"R$ {float(r[1]):,.2f}" if r[1] else "R$ 0,00"
    print(f'  N: {r[0]}, {valor_fmt}, Emit: {r[2][:30] if r[2] else "N/A"}')

conn.close()
