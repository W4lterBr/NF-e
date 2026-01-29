import sqlite3

conn = sqlite3.connect('notas_test.db')

# Lista todas as tabelas
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("=== TABELAS NO BANCO ===")
for table in tables:
    print(f"  - {table[0]}")

# Tenta encontrar NSU em alguma tabela
print("\n=== PROCURANDO NSU ===")
for table in tables:
    try:
        cur = conn.execute(f"PRAGMA table_info({table[0]})")
        cols = [col[1] for col in cur.fetchall()]
        if any('nsu' in col.lower() for col in cols):
            print(f"\n📊 Tabela '{table[0]}' tem coluna NSU:")
            print(f"   Colunas: {', '.join(cols)}")
            
            # Tenta buscar dados
            cur = conn.execute(f"SELECT * FROM {table[0]} LIMIT 5")
            rows = cur.fetchall()
            if rows:
                print(f"   Registros encontrados: {len(rows)}")
                for row in rows[:2]:
                    print(f"   {row}")
    except Exception as e:
        print(f"   Erro ao ler {table[0]}: {e}")

conn.close()
