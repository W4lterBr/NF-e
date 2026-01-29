"""Verifica quantos CTe estão no database"""
import sqlite3

conn = sqlite3.connect("notas.db")
cursor = conn.cursor()

result = cursor.execute("""
    SELECT COUNT(*) as total, tipo 
    FROM notas_detalhadas 
    GROUP BY tipo
""").fetchall()

print("\n" + "="*60)
print("DOCUMENTOS NO DATABASE")
print("="*60)
for row in result:
    tipo = row[1] if row[1] else "Sem tipo"
    print(f"  {tipo}: {row[0]}")

# CTe específico
cte_count = cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='CTe'").fetchone()[0]
print(f"\n[RESULTADO] Total de CTe: {cte_count}")
print("="*60)

conn.close()
