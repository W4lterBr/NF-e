import sqlite3

conn = sqlite3.connect('notas_test.db')
cursor = conn.cursor()

print('\n=== CNPJs com XMLs em pastas antigas ===')
cursor.execute("""
    SELECT DISTINCT cnpj_cpf, COUNT(*) as total
    FROM xmls_baixados 
    WHERE caminho_arquivo LIKE '%75-PARTNESS%' 
       OR caminho_arquivo LIKE '%79-ALFA%' 
       OR caminho_arquivo LIKE '%99-JL%'
       OR caminho_arquivo LIKE '%80-LUZ%'
       OR caminho_arquivo LIKE '%61-MATPARCG%'
    GROUP BY cnpj_cpf
    ORDER BY total DESC
""")

for row in cursor.fetchall():
    print(f'{row[0]} - {row[1]} arquivos')

conn.close()
