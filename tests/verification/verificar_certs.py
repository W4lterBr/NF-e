import sqlite3

conn = sqlite3.connect('notas.db')
print('Total certificados_sefaz ativos:', conn.execute('SELECT COUNT(*) FROM certificados_sefaz WHERE ativo=1').fetchone()[0])
print('\nCertificados ativos:')
for row in conn.execute('SELECT informante, cnpj_cpf FROM certificados_sefaz WHERE ativo=1'):
    print(f'  - {row[0]} ({row[1]})')
conn.close()
