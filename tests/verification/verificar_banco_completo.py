import sqlite3

conn = sqlite3.connect('notas_test.db')
cursor = conn.cursor()

print('=== Estrutura e Conteúdo do Banco ===\n')

# NSU
print('📋 Tabela NSU:')
cursor.execute('PRAGMA table_info(nsu)')
cols = [col[1] for col in cursor.fetchall()]
print(f'   Colunas: {", ".join(cols)}')

cursor.execute('SELECT * FROM nsu LIMIT 3')
rows = cursor.fetchall()
print(f'   Registros: {len(rows)}')
for i, row in enumerate(rows, 1):
    print(f'   {i}. {row[:5]}...' if len(row) > 5 else f'   {i}. {row}')

# NSU_CTE  
print('\n📋 Tabela NSU_CTE:')
cursor.execute('PRAGMA table_info(nsu_cte)')
cols = [col[1] for col in cursor.fetchall()]
print(f'   Colunas: {", ".join(cols)}')

cursor.execute('SELECT * FROM nsu_cte LIMIT 3')
rows = cursor.fetchall()
print(f'   Registros: {len(rows)}')
for i, row in enumerate(rows, 1):
    print(f'   {i}. {row[:5]}...' if len(row) > 5 else f'   {i}. {row}')

# Notas detalhadas
print('\n📋 Tabela NOTAS_DETALHADAS:')
cursor.execute('SELECT chave, numero, nome_emitente, tipo, xml_status FROM notas_detalhadas')
rows = cursor.fetchall()
print(f'   Total: {len(rows)}')
for i, (chave, num, emit, tipo, status) in enumerate(rows, 1):
    print(f'   {i}. NF {num} - {emit}')
    print(f'      Tipo: {tipo} | Status: {status}')
    print(f'      Chave: {chave[:25]}...')

# XMLs baixados com arquivos
print('\n📋 XMLs_BAIXADOS (com arquivo):')
cursor.execute('SELECT chave, caminho_arquivo FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL LIMIT 5')
rows = cursor.fetchall()
print(f'   Total: {len(rows)}')
for i, (chave, path) in enumerate(rows, 1):
    from pathlib import Path
    existe = '✅' if Path(path).exists() else '❌'
    print(f'   {i}. {chave[:25]}...')
    print(f'      {existe} {Path(path).name}')

conn.close()
