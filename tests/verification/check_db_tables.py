import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas_test.db"
conn = sqlite3.connect(db_path)

print("=" * 80)
print("TABELAS NO BANCO notas_test.db")
print("=" * 80)

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for table in tables:
    print(f"\nTabela: {table[0]}")
    
    # Mostrar estrutura
    cursor = conn.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print("  Colunas:")
    for col in columns:
        print(f"    - {col[1]} ({col[2]})")
    
    # Contar registros
    count = conn.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
    print(f"  Registros: {count}")
    
    # Se for tabela de certificados, mostrar CNPJs
    if 'cert' in table[0].lower() or 'api' in table[0].lower():
        print("  CNPJs:")
        try:
            cursor = conn.execute(f"SELECT DISTINCT cnpj FROM {table[0]} LIMIT 5")
            for row in cursor:
                print(f"    - {row[0]}")
        except:
            pass

conn.close()
