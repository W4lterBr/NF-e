import sqlite3

# Consulta as notas problemáticas
conn = sqlite3.connect('notas.db')
cursor = conn.execute('''
    SELECT numero, data_emissao, nome_emitente, cnpj_emitente, chave, xml_status
    FROM notas_detalhadas 
    WHERE numero IN ("673", "144", "266196", "134502", "8330289", "8330288", "8330287")
    LIMIT 10
''')

print("\n" + "="*80)
print("DADOS REAIS DO BANCO DE DADOS")
print("="*80)

rows = cursor.fetchall()
for r in rows:
    print(f"\nNota: {r[0]}")
    print(f"  Data Emissão: {r[1]}")
    print(f"  Emitente: {r[2]}")
    print(f"  CNPJ: {r[3]}")
    print(f"  Chave: {r[4]}")
    print(f"  Status XML: {r[5]}")

conn.close()
