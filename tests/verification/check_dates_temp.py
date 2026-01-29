import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Verificando datas no banco...")
print("Numero | Data no Banco")
print("-" * 50)

c.execute('SELECT numero, data_emissao FROM notas_detalhadas WHERE numero IN (8361363, 137638, 112, 9258, 5497) ORDER BY numero LIMIT 10')
for row in c.fetchall():
    print(f'{row[0]} | {row[1]}')

print("\n" + "=" * 50)
print("Mais exemplos de datas:")
c.execute('SELECT numero, data_emissao FROM notas_detalhadas ORDER BY RANDOM() LIMIT 20')
for row in c.fetchall():
    print(f'{row[0]} | {row[1]}')

conn.close()
