import sqlite3

conn = sqlite3.connect('notas_test.db')
cursor = conn.cursor()

chaves = [
    '35251272381189001001550010082510781649547522',
    '35251272381189001001550010082510791964378593',
    '35251272381189001001550010082510821203752331',
    '35251272381189001001550010082510831908589897',
    '35251272381189001001550010082510941344927120'
]

print("=== Chaves com arquivos XML válidos ===")
for chave in chaves:
    cursor.execute("SELECT numero, nome_emitente FROM notas_detalhadas WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    if row:
        print(f"✅ {chave[:14]}... → NF {row[0]} - {row[1]}")
    else:
        print(f"❌ {chave[:14]}... → NÃO está em notas_detalhadas")

conn.close()
