import sqlite3
conn = sqlite3.connect('notas.db')
tables = [row[0] for row in conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()]
print("Tabelas:", tables)

# Busca certificados
if 'certs' in tables:
    certs = conn.execute('SELECT cnpj_cpf, nome FROM certs').fetchall()
    print("\nCertificados:")
    for c in certs:
        print(f"  {c[0]} - {c[1]}")
elif 'certificados' in tables:
    certs = conn.execute('SELECT cnpj_cpf, nome FROM certificados').fetchall()
    print("\nCertificados:")
    for c in certs:
        print(f"  {c[0]} - {c[1]}")

conn.close()
