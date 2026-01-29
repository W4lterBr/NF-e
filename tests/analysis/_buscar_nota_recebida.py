import sqlite3
from pathlib import Path

db_path = Path("notas.db")
conn = sqlite3.connect(db_path)

# Buscar uma nota emitida PARA o CNPJ (destinatário)
query = """
SELECT chave, nome_emitente, cnpj_emitente, data_emissao
FROM notas_detalhadas
WHERE informante='33251845000109'
  AND SUBSTR(chave, 21, 2)='55'
  AND cnpj_emitente != '33251845000109'
ORDER BY data_emissao DESC
LIMIT 5
"""

cur = conn.execute(query)
notas = cur.fetchall()

print("Notas RECEBIDAS (emitidas POR outros PARA 33251845000109):")
print("=" * 80)
for chave, nome_emit, cnpj_emit, data in notas:
    uf_codigo = chave[0:2]
    print(f"\nChave: {chave}")
    print(f"  UF: {uf_codigo}")
    print(f"  Emitente: {nome_emit}")
    print(f"  CNPJ Emitente: {cnpj_emit}")
    print(f"  Data: {data}")

conn.close()
