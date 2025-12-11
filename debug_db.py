import sqlite3

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

print('=== CERTIFICADOS ===')
certs = conn.execute('SELECT informante, cnpj_cpf FROM certificados').fetchall()
for c in certs:
    print(f"informante: '{c['informante']}', cnpj_cpf: '{c['cnpj_cpf']}'")

print('\n=== NOTAS (amostra de 10) ===')
notas = conn.execute('SELECT informante, numero, nome_emitente FROM notas_detalhadas LIMIT 10').fetchall()
for n in notas:
    print(f"informante: '{n['informante']}', numero: '{n['numero']}', emitente: '{n['nome_emitente']}'")

print('\n=== CONTAGEM POR INFORMANTE ===')
counts = conn.execute('SELECT informante, COUNT(*) as total FROM notas_detalhadas GROUP BY informante').fetchall()
for c in counts:
    print(f"informante: '{c['informante']}' - {c['total']} notas")

conn.close()
