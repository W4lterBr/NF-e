import sqlite3
from pathlib import Path

db_path = Path(r"C:\Users\Nasci\AppData\Roaming\Busca XML\notas.db")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Lista tabelas
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tabelas encontradas: {tables}\n")

# Conta XMLs em cada tabela
for table in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count} registros")
    except Exception as e:
        print(f"{table}: Erro - {e}")

conn.close()
