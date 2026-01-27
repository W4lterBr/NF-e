import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Data mais recente e mais antiga de cada tipo
print("Datas dos documentos:\n")

for tipo in ['NFe', 'CTe', 'NFS-e']:
    c.execute(f"SELECT MIN(data_emissao), MAX(data_emissao), COUNT(*) FROM notas_detalhadas WHERE tipo='{tipo}'")
    row = c.fetchone()
    print(f"{tipo}:")
    print(f"  Mais antiga: {row[0]}")
    print(f"  Mais recente: {row[1]}")
    print(f"  Total: {row[2]}")
    print()

# Verifica quantos docs existem DEPOIS das NFS-e mais recentes
c.execute("SELECT MAX(data_emissao) FROM notas_detalhadas WHERE tipo='NFS-e'")
nfse_max = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE data_emissao > ?", (nfse_max,))
docs_depois = c.fetchone()[0]

print(f"Documentos MAIS RECENTES que a NFS-e mais nova: {docs_depois}")

# Simula o que a interface carrega (últimos 1000)
c.execute("SELECT tipo, COUNT(*) FROM (SELECT * FROM notas_detalhadas ORDER BY data_emissao DESC LIMIT 1000) GROUP BY tipo")
print("\nDocumentos carregados com LIMIT 1000:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
