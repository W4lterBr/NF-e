import sqlite3

# Verificar nfe_data.db
print("📊 Analisando nfe_data.db:")
conn = sqlite3.connect('nfe_data.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tabelas: {tables}\n")

for table in tables:
    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  📋 {table}: {count} registros")
    
    if 'certif' in table.lower():
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"    Colunas: {columns}")
        
        # Mostrar certificado do CNPJ 33251845000109
        cursor = conn.execute(f"SELECT * FROM {table} WHERE cnpj_cpf = '33251845000109' LIMIT 1")
        row = cursor.fetchone()
        if row:
            # Mapear colunas para valores
            cursor2 = conn.execute(f"PRAGMA table_info({table})")
            cols = [c[1] for c in cursor2.fetchall()]
            for i, col in enumerate(cols):
                print(f"      {col}: {row[i]}")



