import sqlite3
import sys
sys.path.append('modules')

from crypto_portable import PortableCryptoManager

crypto = PortableCryptoManager()
conn = sqlite3.connect('notas_test.db')

print("=== LIMPANDO REGISTROS CORROMPIDOS ===\n")

# 1. Lista registros corrompidos na tabela nsu
cur = conn.execute("SELECT informante, ult_nsu FROM nsu")
rows = cur.fetchall()

corrompidos_nsu = []
for row in rows:
    informante, nsu = row
    try:
        # Tenta descriptografar
        dec = crypto.decrypt(informante)
        # Se não é um CNPJ válido (14 dígitos), está corrompido
        if not dec.isdigit() or len(dec) not in [11, 14]:
            corrompidos_nsu.append(informante)
            print(f"❌ NSU NF-e corrompido: {informante[:30]}... → {dec} (NSU: {nsu})")
    except Exception as e:
        print(f"❌ NSU NF-e erro ao descriptografar: {informante[:30]}...")
        corrompidos_nsu.append(informante)

# 2. Lista registros corrompidos na tabela nsu_cte
cur = conn.execute("SELECT informante, ult_nsu FROM nsu_cte")
rows = cur.fetchall()

corrompidos_cte = []
for row in rows:
    informante, nsu = row
    try:
        dec = crypto.decrypt(informante)
        if not dec.isdigit() or len(dec) not in [11, 14]:
            corrompidos_cte.append(informante)
            print(f"❌ NSU CT-e corrompido: {informante[:30]}... → {dec} (NSU: {nsu})")
    except Exception as e:
        print(f"❌ NSU CT-e erro ao descriptografar: {informante[:30]}...")
        corrompidos_cte.append(informante)

print(f"\n📊 Total de registros corrompidos:")
print(f"   NSU NF-e: {len(corrompidos_nsu)}")
print(f"   NSU CT-e: {len(corrompidos_cte)}")

# 3. Remove registros corrompidos
if corrompidos_nsu:
    print(f"\n🧹 Removendo {len(corrompidos_nsu)} registros corrompidos de NSU NF-e...")
    for inf in corrompidos_nsu:
        conn.execute("DELETE FROM nsu WHERE informante = ?", (inf,))
    conn.commit()
    print("✅ NSU NF-e limpo")

if corrompidos_cte:
    print(f"\n🧹 Removendo {len(corrompidos_cte)} registros corrompidos de NSU CT-e...")
    for inf in corrompidos_cte:
        conn.execute("DELETE FROM nsu_cte WHERE informante = ?", (inf,))
    conn.commit()
    print("✅ NSU CT-e limpo")

# 4. Verifica estado final
print("\n=== ESTADO APÓS LIMPEZA ===\n")

cur = conn.execute("SELECT informante, ult_nsu FROM nsu")
rows = cur.fetchall()
print("NSU NF-e válidos:")
for row in rows:
    try:
        cnpj = crypto.decrypt(row[0])
        print(f"   ✅ {cnpj} → NSU {row[1]}")
    except:
        print(f"   ❓ {row[0][:30]}... → NSU {row[1]}")

cur = conn.execute("SELECT informante, ult_nsu FROM nsu_cte")
rows = cur.fetchall()
print("\nNSU CT-e válidos:")
for row in rows:
    try:
        cnpj = crypto.decrypt(row[0])
        print(f"   ✅ {cnpj} → NSU {row[1]}")
    except:
        print(f"   ❓ {row[0][:30]}... → NSU {row[1]}")

conn.close()
print("\n✅ Limpeza concluída!")
