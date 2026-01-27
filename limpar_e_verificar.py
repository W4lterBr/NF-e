import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# 1. Remove linhas totalmente vazias
print("Removendo linhas vazias...")
c.execute("""
    DELETE FROM notas_detalhadas 
    WHERE (numero IS NULL OR numero = '') 
      AND (data_emissao IS NULL OR data_emissao = '')
      AND (nome_emitente IS NULL OR nome_emitente = '')
""")
removidas = c.rowcount
print(f"✓ {removidas} linhas vazias removidas")

conn.commit()

# 2. Verifica status após limpeza
print("\n" + "="*70)
print("Status após limpeza:")

c.execute("SELECT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo ORDER BY tipo")
for tipo, count in c.fetchall():
    print(f"  {tipo}: {count}")

# 3. Mostra os 20 mais recentes (simulando LIMIT da interface)
print("\n" + "="*70)
print("Primeiros 20 documentos (ordem da interface):")
c.execute("""
    SELECT tipo, numero, data_emissao, nome_emitente, valor
    FROM notas_detalhadas 
    ORDER BY data_emissao DESC
    LIMIT 20
""")
for idx, row in enumerate(c.fetchall(), 1):
    print(f"  {idx}. {row[0]}: N={row[1]}, Data={row[2]}, Emit={row[3][:25] if row[3] else 'N/A'}..., R${row[4]}")

# 4. Conta NFS-e nos primeiros 1000
print("\n" + "="*70)
print("Documentos nos primeiros 1000 (LIMIT antigo):")
c.execute("""
    SELECT tipo, COUNT(*) 
    FROM (
        SELECT tipo FROM notas_detalhadas 
        ORDER BY data_emissao DESC 
        LIMIT 1000
    )
    GROUP BY tipo
""")
for tipo, count in c.fetchall():
    print(f"  {tipo}: {count}")

# 5. Conta NFS-e nos primeiros 5000
print("\n" + "="*70)
print("Documentos nos primeiros 5000 (LIMIT novo):")
c.execute("""
    SELECT tipo, COUNT(*) 
    FROM (
        SELECT tipo FROM notas_detalhadas 
        ORDER BY data_emissao DESC 
        LIMIT 5000
    )
    GROUP BY tipo
""")
for tipo, count in c.fetchall():
    print(f"  {tipo}: {count}")

conn.close()

print("\n" + "="*70)
print("IMPORTANTE:")
print("1. Feche COMPLETAMENTE a interface 'Busca NF-e.py'")
print("2. Reabra a aplicação")
print("3. Clique em 'Atualizar' ou 'Carregar Notas'")
print("4. Agora deve aparecer mais NFS-e!")
