import sqlite3
import sys
sys.path.append('modules')

from crypto_portable import PortableCryptoManager

crypto = PortableCryptoManager()
conn = sqlite3.connect('notas_test.db')

print("=== ADICIONANDO NSU CT-e para CNPJ 49068153000140 ===\n")

# Criptografa o CNPJ
cnpj = '49068153000140'
cnpj_encrypted = crypto.encrypt(cnpj)

# NSU correto retornado pela SEFAZ
nsu_correto = '000000000000201'

# Adiciona na tabela nsu_cte
conn.execute(
    "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, ?)",
    (cnpj_encrypted, nsu_correto)
)
conn.commit()

print(f"✅ NSU CT-e atualizado para {cnpj}")
print(f"   NSU: {nsu_correto}")

# Verifica
cur = conn.execute("SELECT informante, ult_nsu FROM nsu_cte WHERE informante = ?", (cnpj_encrypted,))
result = cur.fetchone()

if result:
    cnpj_dec = crypto.decrypt(result[0])
    print(f"\n📊 Verificação: CNPJ {cnpj_dec} → NSU {result[1]}")

conn.close()
print("\n✅ Correção concluída!")
