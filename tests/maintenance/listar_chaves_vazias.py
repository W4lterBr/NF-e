import sqlite3

conn = sqlite3.connect('notas.db')

cursor = conn.execute("""
    SELECT chave, nsu, xml_status, informante 
    FROM notas_detalhadas 
    WHERE (tipo='NFe' OR tipo='NF-e') 
    AND (data_emissao IS NULL OR data_emissao='' OR data_emissao='N/A') 
    ORDER BY atualizado_em DESC 
    LIMIT 5
""")

print("Chaves das NF-e vazias:")
for row in cursor:
    print(f"  Chave: {row[0]}")
    print(f"  NSU: {row[1]}")
    print(f"  XML_Status: {row[2]}")
    print(f"  Informante: {row[3]}")
    print()

conn.close()
