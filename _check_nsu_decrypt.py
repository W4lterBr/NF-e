import sqlite3
import sys
sys.path.append('modules')

from crypto_portable import PortableCryptoManager

crypto = PortableCryptoManager()
conn = sqlite3.connect('notas_test.db')

# Busca todos os NSU
cur = conn.execute("SELECT informante, ult_nsu FROM nsu")
rows = cur.fetchall()

print("=== NSU NF-e no Banco ===")
for row in rows:
    try:
        cnpj = crypto.decrypt(row[0])
        nsu = row[1]
        print(f"CNPJ: {cnpj} → NSU: {nsu}")
        if cnpj == '48160135000140':
            print(f"   ⚠️ ESTE É O CNPJ DO USUÁRIO! NSU = {nsu}")
    except Exception as e:
        print(f"Erro ao descriptografar {row[0][:20]}...: {e}")

# Busca NSU CT-e também
print("\n=== NSU CT-e no Banco ===")
cur = conn.execute("SELECT informante, ult_nsu FROM nsu_cte")
rows = cur.fetchall()

for row in rows:
    try:
        cnpj = crypto.decrypt(row[0])
        nsu = row[1]
        print(f"CNPJ: {cnpj} → NSU: {nsu}")
        if cnpj == '48160135000140':
            print(f"   ⚠️ ESTE É O CNPJ DO USUÁRIO! NSU = {nsu}")
    except Exception as e:
        print(f"Erro ao descriptografar {row[0][:20]}...: {e}")

# Verifica erro 656
print("\n=== Bloqueios 656 ===")
cur = conn.execute("SELECT informante, ultimo_erro, nsu_bloqueado FROM erro_656")
rows = cur.fetchall()

for row in rows:
    print(f"CNPJ: {row[0]} → Último erro: {row[1]} → NSU bloqueado: {row[2]}")

conn.close()
