import sqlite3

conn = sqlite3.connect('notas_test.db')
c = conn.cursor()

# Corrige o tipo de NFSe para NFS-e (com hífen)
c.execute("UPDATE notas_detalhadas SET tipo='NFS-e' WHERE tipo='NFSe'")
conn.commit()

# Verifica
c.execute("SELECT DISTINCT tipo FROM notas_detalhadas")
print("Tipos após correção:")
for row in c.fetchall():
    print(f"  - {row[0]}")

c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'")
total = c.fetchone()[0]
print(f"\nTotal NFS-e: {total}")

conn.close()
print("\n✅ Tipo corrigido para 'NFS-e'")
