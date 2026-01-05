import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("📋 Tabelas no banco notas.db:")
tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"   - {t[0]}")

conn.close()
