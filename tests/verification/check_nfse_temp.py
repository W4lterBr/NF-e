import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Conta NFS-e por chave
c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE chave LIKE 'NFSE_%'")
nfse_chave = c.fetchone()[0]

# Conta NFS-e por tipo
c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo LIKE '%NFS%'")
nfse_tipo = c.fetchone()[0]

# Total de notas
c.execute("SELECT COUNT(*) FROM notas_detalhadas")
total = c.fetchone()[0]

print(f"Total de notas no banco: {total}")
print(f"NFS-e por chave (NFSE_*): {nfse_chave}")
print(f"NFS-e por campo tipo: {nfse_tipo}")

if nfse_chave > 0:
    print("\nExemplos de NFS-e:")
    c.execute("SELECT chave, numero, nome_emitente, tipo, data_emissao FROM notas_detalhadas WHERE chave LIKE 'NFSE_%' LIMIT 5")
    for row in c.fetchall():
        print(f"  {row}")

# Verifica distintos tipos
print("\nTipos de documentos no banco:")
c.execute("SELECT DISTINCT tipo, COUNT(*) as qtd FROM notas_detalhadas GROUP BY tipo")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
