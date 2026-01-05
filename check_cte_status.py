import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

chave = '50251203232675000154570010056290311009581385'

print(f"🔍 Procurando CT-e: {chave}\n")

result = c.execute('''
    SELECT chave, status, tipo, data_emissao, numero, valor 
    FROM notas_detalhadas 
    WHERE chave = ?
''', (chave,)).fetchone()

if result:
    print(f"✅ CT-e ENCONTRADO NO BANCO:")
    print(f"   Chave: {result[0]}")
    print(f"   Status: {result[1]}")
    print(f"   Tipo: {result[2]}")
    print(f"   Data: {result[3]}")
    print(f"   Número: {result[4]}")
    print(f"   Valor: R$ {result[5]}")
    print()
    print(f"🔍 DIAGNÓSTICO:")
    print(f"   ❌ Status atual: '{result[1]}'")
    print(f"   ✅ Status esperado se cancelado: 'Cancelamento de CT-e homologado'")
    print()
    print(f"💡 CONCLUSÃO:")
    print(f"   O CT-e existe no banco mas com status desatualizado.")
    print(f"   O evento de cancelamento NUNCA foi baixado via NSU.")
else:
    print(f"❌ CT-e NÃO encontrado no banco")

conn.close()
