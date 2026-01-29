import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Buscando notas RESUMO com chaves...")
c.execute('SELECT chave, numero, data_emissao, xml_status FROM notas_detalhadas WHERE xml_status = "RESUMO" LIMIT 5')

for row in c.fetchall():
    chave = row[0]
    if chave and len(chave) >= 8:
        aa = chave[2:4]
        mm = chave[4:6]
        dd = chave[6:8]
        print(f"Chave: {chave[:20]}...")
        print(f"  Extraído: AA={aa}, MM={mm}, DD={dd}")
        print(f"  Data formada: 20{aa}-{mm}-{dd}")
        print(f"  Numero: {row[1]}, Data original: {row[2]}")
        print()

conn.close()
