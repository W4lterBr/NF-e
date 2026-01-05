import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

# Total de notas da empresa
cursor.execute(
    'SELECT COUNT(*) FROM notas_detalhadas WHERE chave LIKE ?',
    ('50251201773924000193550010000172%',)
)
total = cursor.fetchone()[0]
print(f'Total de notas da empresa 01773924000193: {total}')

# Últimas 5 notas
cursor.execute(
    'SELECT chave, cnpj_emitente, nome_emitente FROM notas_detalhadas WHERE chave LIKE ? ORDER BY chave DESC LIMIT 5',
    ('50251201773924000193550010000172%',)
)
rows = cursor.fetchall()
print('\nÚltimas 5 notas (por chave):')
for r in rows:
    nome = r[2] if r[2] else 'NULL'
    print(f'  Chave: ...{r[0][-15:]}')
    print(f'  CNPJ: [{r[1]}]')
    print(f'  Nome: {nome}')
    print()

# Verifica as 2 que deveriam ter sido adicionadas
print('Verificando as 2 novas chaves:')
chaves_novas = [
    '50251201773924000193550010000172661684493900',
    '50251201773924000193550010000172571753753565'
]
for ch in chaves_novas:
    cursor.execute(
        'SELECT chave, cnpj_emitente, nome_emitente, xml_status FROM notas_detalhadas WHERE chave = ?',
        (ch,)
    )
    row = cursor.fetchone()
    if row:
        print(f'\n  Chave ...{ch[-10:]}: ENCONTRADA')
        print(f'    CNPJ: [{row[1]}]')
        print(f'    Nome: {row[2] or "NULL"}')
        print(f'    XML Status: {row[3]}')
    else:
        print(f'\n  Chave ...{ch[-10:]}: NÃO ENCONTRADA')

conn.close()
