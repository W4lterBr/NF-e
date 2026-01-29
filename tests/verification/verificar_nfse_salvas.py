"""
Script para verificar NFS-e salvas no banco e arquivos
"""
import sqlite3
import os

# Verificar banco de dados
conn = sqlite3.connect('nfe_data.db')

# Contar total
cursor = conn.execute('SELECT COUNT(*) FROM nfse')
total = cursor.fetchone()[0]
print(f'Total NFS-e no banco: {total}')

if total > 0:
    # Mostrar primeiras NFS-e
    cursor = conn.execute('''
        SELECT numero_nfse, chave_acesso, cnpj_prestador, cnpj_tomador, 
               valor_servico, data_emissao 
        FROM nfse 
        ORDER BY data_emissao DESC
        LIMIT 10
    ''')
    
    print('\n' + '='*80)
    print('ULTIMAS 10 NFS-e SALVAS:')
    print('='*80)
    
    for row in cursor:
        numero, chave, prestador, tomador, valor, data = row
        print(f'\nNumero: {numero}')
        print(f'  Chave: {chave}')
        print(f'  Prestador: {prestador}')
        print(f'  Tomador: {tomador}')
        print(f'  Valor: R$ {valor:,.2f}' if valor else '  Valor: N/A')
        print(f'  Data: {data}')

# Verificar NSU salvo
cursor = conn.execute('SELECT informante, ult_nsu FROM nsu_nfse')
print('\n' + '='*80)
print('NSU SALVO POR INFORMANTE:')
print('='*80)
for row in cursor:
    print(f'  CNPJ: {row[0]} -> Ultimo NSU: {row[1]}')

conn.close()

# Verificar arquivos XML
xml_dir = 'xml_NFs'
if os.path.exists(xml_dir):
    nfse_files = [f for f in os.listdir(xml_dir) if 'NFSe' in f or 'nfse' in f.lower()]
    print(f'\n{"="*80}')
    print(f'ARQUIVOS XML NFS-e SALVOS: {len(nfse_files)}')
    print('='*80)
    
    if nfse_files:
        print('\nPrimeiros 10 arquivos:')
        for f in sorted(nfse_files)[:10]:
            size = os.path.getsize(os.path.join(xml_dir, f))
            print(f'  {f} ({size:,} bytes)')
