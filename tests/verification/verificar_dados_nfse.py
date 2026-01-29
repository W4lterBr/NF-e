import sqlite3

conn = sqlite3.connect('nfe_data.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM nfse_baixadas')
print(f'Total NFS-e: {cursor.fetchone()[0]}')

cursor.execute('''
    SELECT numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, valor_servico 
    FROM nfse_baixadas 
    LIMIT 5
''')

print('\nPrimeiras 5 NFS-e:')
for row in cursor.fetchall():
    print(f'  Nº {row[0]} | Prestador: {row[1]} | Tomador: {row[2]} | Data: {row[3]} | Valor: R$ {row[4]}')

cursor.execute('SELECT informante, ult_nsu FROM nsu_nfse')
print('\nÚltimo NSU processado:')
for row in cursor.fetchall():
    print(f'  CNPJ: {row[0]} | NSU: {row[1]}')

conn.close()
