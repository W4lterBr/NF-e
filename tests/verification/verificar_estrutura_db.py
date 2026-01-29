import sqlite3

conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

print("=== TABELAS NO BANCO notas.db ===")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for table in tables:
    print(f"\n📋 Tabela: {table[0]}")
    count = cursor.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
    print(f"   Registros: {count}")

# Verificar se existe tabela de certificados
cert_tables = [t[0] for t in tables if 'cert' in t[0].lower()]
if cert_tables:
    print(f"\n✅ Tabelas de certificados encontradas: {cert_tables}")
    for ct in cert_tables:
        print(f"\n   📄 Estrutura de {ct}:")
        cols = cursor.execute(f"PRAGMA table_info({ct})").fetchall()
        for col in cols:
            print(f"      - {col[1]} ({col[2]})")
        
        # Mostrar primeiros registros
        print(f"\n   📝 Primeiros 3 registros de {ct}:")
        rows = cursor.execute(f"SELECT * FROM {ct} LIMIT 3").fetchall()
        for row in rows:
            print(f"      {row}")
else:
    print("\n❌ Nenhuma tabela de certificados encontrada!")

conn.close()
