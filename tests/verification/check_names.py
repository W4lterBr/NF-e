import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.execute('SELECT informante, nome_certificado FROM certificados')

print('\n📋 Certificados cadastrados:\n')
for row in cursor:
    print(f'   {row[0]} → {row[1] or "(sem nome)"}')

conn.close()
