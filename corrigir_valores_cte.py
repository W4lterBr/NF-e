import sqlite3
import re

conn = sqlite3.connect('notas.db')

print('🔧 CORRIGINDO VALORES DOS CT-e NO BANCO...\n')

# Busca todos CT-e
cursor = conn.execute("SELECT chave, valor FROM notas_detalhadas WHERE tipo = 'CTe'")
ctes = cursor.fetchall()

print(f'📊 Total de CT-e encontrados: {len(ctes)}')

corrigidos = 0
erros = 0

for chave, valor in ctes:
    if not valor:
        continue
    
    try:
        # Remove formatação: "R$ 12.345,67" -> "12345.67"
        valor_limpo = valor.replace('R$', '').strip()
        valor_limpo = valor_limpo.replace('.', '')  # Remove separador de milhar
        valor_limpo = valor_limpo.replace(',', '.')  # Troca vírgula por ponto decimal
        
        # Tenta converter para float para validar
        valor_float = float(valor_limpo)
        
        # Atualiza no banco com valor numérico
        conn.execute(
            "UPDATE notas_detalhadas SET valor = ? WHERE chave = ?",
            (str(valor_float), chave)
        )
        
        corrigidos += 1
        
        if corrigidos <= 5:
            print(f'   ✓ {chave[:20]}... | "{valor}" → "{valor_float}"')
    
    except Exception as e:
        erros += 1
        if erros <= 3:
            print(f'   ✗ {chave[:20]}... | Erro: {e}')

conn.commit()

print(f'\n✅ Correção concluída!')
print(f'   Corrigidos: {corrigidos}')
print(f'   Erros: {erros}')

# Verifica resultado
cursor = conn.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CAST(valor AS REAL)) as soma_total,
        MIN(CAST(valor AS REAL)) as minimo,
        MAX(CAST(valor AS REAL)) as maximo,
        AVG(CAST(valor AS REAL)) as media
    FROM notas_detalhadas 
    WHERE tipo = 'CTe'
''')

row = cursor.fetchone()
print(f'\n📊 ESTATÍSTICAS APÓS CORREÇÃO:')
print(f'   Total CT-e: {row[0]}')
print(f'   Soma total: R$ {row[1]:,.2f}')
print(f'   Valor mínimo: R$ {row[2]:,.2f}')
print(f'   Valor máximo: R$ {row[3]:,.2f}')
print(f'   Valor médio: R$ {row[4]:,.2f}')

# Compara totais
print(f'\n📋 COMPARAÇÃO GERAL:')
cursor = conn.execute('''
    SELECT tipo, COUNT(*) as qtd, SUM(CAST(valor AS REAL)) as total
    FROM notas_detalhadas
    GROUP BY tipo
''')

print(f'{"Tipo":<10} {"Quantidade":>12} {"Valor Total":>20}')
print('-'*45)
for row in cursor.fetchall():
    tipo = row[0]
    qtd = row[1]
    total = row[2] if row[2] else 0
    print(f'{tipo:<10} {qtd:>12} {f"R$ {total:,.2f}":>20}')

conn.close()
print('\n✅ Banco atualizado com sucesso!')
