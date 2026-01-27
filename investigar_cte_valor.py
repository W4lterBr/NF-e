import sqlite3

conn = sqlite3.connect('notas.db')

print('\n🔍 INVESTIGANDO CT-e COM VALOR ZERO:\n')

# 1. Verificar tipos existentes
print('1️⃣ Tipos de documentos no banco:')
cursor = conn.execute("SELECT DISTINCT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo")
for row in cursor.fetchall():
    print(f'   {row[0]}: {row[1]} documentos')

print('\n2️⃣ Amostra de CT-e (primeiros 10):')
cursor = conn.execute('''
    SELECT numero, valor, data_emissao, nome_emitente 
    FROM notas_detalhadas 
    WHERE tipo = 'CTe' 
    LIMIT 10
''')

print(f'{"Número":<15} {"Valor":<20} {"Data":<12} {"Emitente":<40}')
print('-'*90)

for row in cursor.fetchall():
    numero = row[0] or 'N/A'
    valor = row[1] or 'NULL'
    data = row[2][:10] if row[2] else 'N/A'
    emitente = (row[3][:38] + '..') if len(row[3] or '') > 40 else (row[3] or 'N/A')
    print(f'{numero:<15} {valor:<20} {data:<12} {emitente:<40}')

print('\n3️⃣ Estatísticas de valores dos CT-e:')
cursor = conn.execute('''
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN valor IS NULL THEN 1 END) as nulos,
        COUNT(CASE WHEN valor = '' THEN 1 END) as vazios,
        COUNT(CASE WHEN CAST(valor AS REAL) = 0 THEN 1 END) as zeros,
        COUNT(CASE WHEN CAST(valor AS REAL) > 0 THEN 1 END) as com_valor
    FROM notas_detalhadas 
    WHERE tipo = 'CTe'
''')

row = cursor.fetchone()
print(f'   Total CT-e: {row[0]}')
print(f'   Valores NULL: {row[1]}')
print(f'   Valores vazios (""): {row[2]}')
print(f'   Valores = 0: {row[3]}')
print(f'   Valores > 0: {row[4]}')

print('\n4️⃣ CT-e com valores maiores que zero:')
cursor = conn.execute('''
    SELECT numero, valor, nome_emitente 
    FROM notas_detalhadas 
    WHERE tipo = 'CTe' AND CAST(valor AS REAL) > 0
    LIMIT 5
''')

rows = cursor.fetchall()
if rows:
    print(f'{"Número":<15} {"Valor":<20} {"Emitente":<40}')
    print('-'*80)
    for row in rows:
        print(f'{row[0]:<15} {row[1]:<20} {(row[2] or "N/A"):<40}')
else:
    print('   ⚠️  NENHUM CT-e possui valor > 0!')

conn.close()
