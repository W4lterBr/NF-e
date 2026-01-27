import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print('=== Buscando notas apenas_protocolo ===')
rows = c.execute('SELECT COUNT(*) FROM auto_verificacao WHERE observacao = "apenas_protocolo"').fetchone()
print(f'Total: {rows[0]}')

if rows[0] > 0:
    print('\nPrimeiras 3 chaves:')
    for row in c.execute('SELECT chave FROM auto_verificacao WHERE observacao = "apenas_protocolo" LIMIT 3').fetchall():
        print(row[0])

conn.close()
