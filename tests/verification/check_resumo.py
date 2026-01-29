import sqlite3
import os

db_path = os.path.join(os.environ.get('APPDATA'), 'Busca XML', 'notas.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Conta notas com RESUMO
cur.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
total_resumo = cur.fetchone()[0]
print(f'\nNotas com status RESUMO: {total_resumo}')

# Conta notas com COMPLETO
cur.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
total_completo = cur.fetchone()[0]
print(f'Notas com status COMPLETO: {total_completo}')

# Conta eventos
cur.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'EVENTO'")
total_evento = cur.fetchone()[0]
print(f'Notas com status EVENTO: {total_evento}')

# Total
cur.execute("SELECT COUNT(*) FROM notas_detalhadas")
total = cur.fetchone()[0]
print(f'Total de notas: {total}\n')

# Mostra exemplos de RESUMO
if total_resumo > 0:
    print('Exemplos de notas RESUMO:')
    cur.execute("SELECT numero, nome_emitente, data_emissao FROM notas_detalhadas WHERE xml_status = 'RESUMO' LIMIT 5")
    for row in cur.fetchall():
        print(f'  Num: {row[0]}, Emit: {row[1][:40]}, Data: {row[2]}')
else:
    print('Não há notas com status RESUMO no banco!')
    print('\nPara testar a visualização, você pode:')
    print('1. Fazer uma busca na SEFAZ (algumas notas virão como RESUMO)')
    print('2. Ou criar uma nota teste no banco com INSERT')

conn.close()
