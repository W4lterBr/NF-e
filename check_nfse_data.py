import sqlite3
import os

conn = sqlite3.connect('nfe_data.db')

# Verificar estrutura da tabela nfse_baixadas
cursor = conn.execute("PRAGMA table_info(nfse_baixadas)")
print('Estrutura da tabela nfse_baixadas:')
for row in cursor:
    print(f'  {row[1]} ({row[2]})')

# Contar registros
cursor = conn.execute('SELECT COUNT(*) FROM nfse_baixadas')
total = cursor.fetchone()[0]
print(f'\nTotal de registros: {total}')

if total > 0:
    # Mostrar alguns registros
    cursor = conn.execute('SELECT * FROM nfse_baixadas LIMIT 5')
    cols = [desc[0] for desc in cursor.description]
    print('\nPrimeiros 5 registros:')
    print('Colunas:', cols)
    for row in cursor:
        print(f'\n  NSU: {row[0]}')
        for i, col in enumerate(cols[1:], 1):
            if row[i]:
                val = str(row[i])[:100] if isinstance(row[i], str) and len(str(row[i])) > 100 else row[i]
                print(f'    {col}: {val}')

# Verificar NSU salvo
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nsu_nfse'")
if cursor.fetchone():
    cursor = conn.execute('SELECT * FROM nsu_nfse')
    print('\n' + '='*80)
    print('NSU SALVO:')
    print('='*80)
    for row in cursor:
        print(f'  Informante: {row[0]}, Ultimo NSU: {row[1]}, Atualizado: {row[2]}')

conn.close()

# Verificar arquivos XML
xml_dir = 'xml_NFs'
if os.path.exists(xml_dir):
    nfse_files = [f for f in os.listdir(xml_dir) if 'NFSe' in f or 'nfse' in f.lower()]
    print(f'\n{"="*80}')
    print(f'ARQUIVOS XML NFS-e: {len(nfse_files)}')
    print('='*80)
    
    if nfse_files:
        print('\nPrimeiros 10:')
        for f in sorted(nfse_files)[:10]:
            size = os.path.getsize(os.path.join(xml_dir, f))
            print(f'  {f} ({size:,} bytes)')
