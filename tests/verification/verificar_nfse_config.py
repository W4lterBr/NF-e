import sqlite3

conn = sqlite3.connect('notas.db')

print("=== Configurações NFS-e ===")
rows = conn.execute('SELECT * FROM nfse_config').fetchall()
if rows:
    cols = conn.execute('PRAGMA table_info(nfse_config)').fetchall()
    col_names = [col[1] for col in cols]
    print(f"Colunas: {col_names}\n")
    for row in rows:
        print(row)
else:
    print("❌ Nenhuma configuração encontrada")

print("\n=== Certificados ===")
certs = conn.execute('SELECT informante, cnpj_cpf, ativo FROM certificados WHERE ativo=1').fetchall()
for cert in certs:
    print(f"{cert[0]} - {cert[1]}")

conn.close()
