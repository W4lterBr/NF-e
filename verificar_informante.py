import sqlite3

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

print('=== CERTIFICADOS ===')
certs = conn.execute('SELECT informante, cnpj_cpf FROM certificados LIMIT 5').fetchall()
for c in certs:
    print(f"informante: '{c['informante']}', cnpj_cpf: '{c['cnpj_cpf']}'")

print('\n=== NOTAS COMPLETAS (5 primeiras) ===')
notas = conn.execute('SELECT informante, numero, nome_emitente FROM notas_detalhadas WHERE xml_status="COMPLETO" LIMIT 5').fetchall()
for n in notas:
    print(f"informante: '{n['informante']}', num: {n['numero']}, emit: {n['nome_emitente'][:30]}")

conn.close()
