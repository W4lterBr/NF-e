import sqlite3

conn = sqlite3.connect('notas.db')

print('\n🏷️  DOCUMENTOS NA INTERFACE:\n')
print(f'{"Tipo":<15} {"Qtd":>10} {"Valor Total":>20}')
print('-'*50)

cursor = conn.execute('''
    SELECT tipo, COUNT(*) as total, SUM(CAST(valor AS REAL)) as valor_total 
    FROM notas_detalhadas 
    GROUP BY tipo
''')

for row in cursor.fetchall():
    tipo = row[0] or 'Sem tipo'
    qtd = row[1]
    valor = row[2] if row[2] else 0
    print(f'{tipo:<15} {qtd:>10} {f"R$ {valor:,.2f}":>20}')

print('\n📋 AMOSTRA DE NFS-e NA INTERFACE:\n')

cursor = conn.execute('''
    SELECT numero, nome_emitente, nome_destinatario, data_emissao, valor, uf
    FROM notas_detalhadas 
    WHERE tipo = 'NFS-e'
    ORDER BY data_emissao DESC
    LIMIT 10
''')

print(f'{"Número":<20} {"Prestador":<40} {"Tomador":<40} {"Data":<12} {"Valor":>12} {"UF":>4}')
print('-'*135)

for row in cursor.fetchall():
    numero = row[0][:18] if row[0] else 'N/A'
    prestador = (row[1][:38] + '..') if len(row[1] or '') > 40 else (row[1] or 'N/A')
    tomador = (row[2][:38] + '..') if len(row[2] or '') > 40 else (row[2] or 'N/A')
    data = row[3][:10] if row[3] else 'N/A'
    valor = float(row[4]) if row[4] else 0
    uf = row[5] or ''
    
    print(f'{numero:<20} {prestador:<40} {tomador:<40} {data:<12} {f"R$ {valor:,.2f}":>12} {uf:>4}')

conn.close()
