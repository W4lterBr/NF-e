import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Buscando notas com números específicos da interface...")
numeros = [8361363, 137638, 112, 9258, 5497, 204359, 204358, 204360]

for num in numeros:
    c.execute('SELECT numero, data_emissao, nome_emitente FROM notas_detalhadas WHERE numero = ? LIMIT 1', (num,))
    row = c.fetchone()
    if row:
        print(f'Numero: {row[0]} | Data: {row[1]} | Emitente: {row[2][:30] if row[2] else "N/A"}')
    else:
        print(f'Numero: {num} | NÃO ENCONTRADO')

print("\n" + "=" * 70)
print("Verificando as 10 primeiras notas da interface (ordenadas)...")
c.execute('SELECT numero, data_emissao, nome_emitente FROM notas_detalhadas ORDER BY COALESCE(data_emissao, "9999-12-31") DESC LIMIT 10')
for row in c.fetchall():
    print(f'{row[0]} | {row[1]} | {row[2][:30] if row[2] else "N/A"}')

conn.close()
