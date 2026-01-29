import sqlite3
import sys
sys.path.append('modules')

from crypto_portable import PortableCryptoManager

crypto = PortableCryptoManager()
conn = sqlite3.connect('notas_test.db')

cnpj = '48160135000140'
nsu_correto = '000000000001609'

# Criptografa o CNPJ
cnpj_encrypted = crypto.encrypt(cnpj)

# Insere/atualiza o NSU
conn.execute(
    "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, ?)",
    (cnpj_encrypted, nsu_correto)
)
conn.commit()

print(f"✅ NSU atualizado para {cnpj}")
print(f"   NSU NF-e: {nsu_correto}")

# Também atualiza NSU CT-e para evitar problemas futuros
conn.execute(
    "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, ?)",
    (cnpj_encrypted, '000000000000000')
)
conn.commit()

print(f"   NSU CT-e: 000000000000000 (iniciado)")

# Verifica
row = conn.execute("SELECT ult_nsu FROM nsu WHERE informante=?", (cnpj_encrypted,)).fetchone()
print(f"\n📊 Verificação: NSU salvo = {row[0] if row else 'NÃO ENCONTRADO'}")

conn.close()
