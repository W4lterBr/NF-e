"""Verifica NSU CT-e no banco de dados"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"
conn = sqlite3.connect(db_path)

print("=" * 60)
print("VERIFICAÇÃO DE NSU CT-e NO BANCO")
print("=" * 60)

# Verifica todos os NSU CT-e
cursor = conn.execute("SELECT informante, ult_nsu FROM nsu_cte ORDER BY informante")
rows = cursor.fetchall()

if rows:
    print(f"\n📊 Total de registros: {len(rows)}\n")
    for informante, nsu in rows:
        print(f"   {informante}: {nsu}")
else:
    print("\n⚠️ Nenhum registro encontrado na tabela nsu_cte")

# Verifica especificamente o problemático
print("\n" + "=" * 60)
print("VERIFICAÇÃO ESPECÍFICA: 49068153000160")
print("=" * 60)

cursor = conn.execute("SELECT informante, ult_nsu FROM nsu_cte WHERE informante = '49068153000160'")
row = cursor.fetchone()

if row:
    informante, nsu = row
    print(f"\n✅ Registro encontrado:")
    print(f"   Informante: {informante}")
    print(f"   Último NSU: {nsu}")
    
    if nsu == "000000000000000":
        print(f"\n⚠️ NSU está em ZERO!")
else:
    print(f"\n⚠️ Nenhum registro para 49068153000160")
    print(f"   (Quando não há registro, o sistema usa NSU = 0 por padrão)")

conn.close()
