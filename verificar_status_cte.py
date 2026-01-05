import sqlite3

chave = "50251203232675000154570010056290311009581385"

conn = sqlite3.connect('notas.db')
c = conn.cursor()

c.execute('SELECT chave, status, numero, data_emissao, valor FROM notas_detalhadas WHERE chave=?', (chave,))
r = c.fetchone()

if r:
    print(f"✅ CT-e encontrado no banco:")
    print(f"   Chave: {r[0]}")
    print(f"   Status: {r[1]}")
    print(f"   Número: {r[2]}")
    print(f"   Emissão: {r[3]}")
    print(f"   Valor: R$ {r[4]}")
else:
    print(f"❌ CT-e não encontrado no banco")
    
conn.close()
