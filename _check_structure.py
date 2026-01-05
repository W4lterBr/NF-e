import sqlite3
from pathlib import Path

db_path = Path(r"C:\Users\Nasci\AppData\Roaming\Busca XML\notas.db")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

# Verifica estrutura da tabela xmls_baixados
cur.execute("PRAGMA table_info(xmls_baixados)")
columns_xmls = cur.fetchall()
print("Colunas de 'xmls_baixados':")
for col in columns_xmls:
    print(f"  - {col[1]} ({col[2]})")

print("\n" + "="*60 + "\n")

# Verifica estrutura da tabela notas_detalhadas
cur.execute("PRAGMA table_info(notas_detalhadas)")
columns_notas = cur.fetchall()
print("Colunas de 'notas_detalhadas':")
for col in columns_notas:
    print(f"  - {col[1]} ({col[2]})")

# Conta total
cur.execute("SELECT COUNT(*) FROM xmls_baixados")
print(f"\n✅ Total xmls_baixados: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM notas_detalhadas")
print(f"✅ Total notas_detalhadas: {cur.fetchone()[0]}")

# Mostra últimos 3 registros
print("\n" + "="*60)
print("ÚLTIMOS 3 XMLs BAIXADOS:")
print("="*60)
cur.execute("SELECT * FROM xmls_baixados ORDER BY rowid DESC LIMIT 3")
for row in cur.fetchall():
    print(row)

conn.close()
