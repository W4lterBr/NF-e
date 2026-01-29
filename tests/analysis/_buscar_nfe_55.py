import sqlite3
conn = sqlite3.connect('notas.db')
cur = conn.execute("SELECT chave FROM notas_detalhadas WHERE informante='33251845000109' AND SUBSTR(chave, 21, 2)='55' LIMIT 5")
for row in cur.fetchall():
    chave = row[0]
    print(f"{chave} - Modelo: {chave[20:22]}")
conn.close()
