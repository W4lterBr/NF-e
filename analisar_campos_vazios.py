import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Busca linhas com campos vazios importantes
print("Linhas com campos vazios críticos:")
c.execute("""
    SELECT tipo, numero, data_emissao, cnpj_emitente, nome_emitente, valor 
    FROM notas_detalhadas 
    WHERE numero IS NULL OR numero = '' 
       OR data_emissao IS NULL OR data_emissao = ''
    LIMIT 10
""")
print("Registros com número/data vazios:")
for row in c.fetchall():
    print(f"  Tipo: {row[0]}, Num: '{row[1]}', Data: '{row[2]}', CNPJ: '{row[3]}', Nome: '{row[4]}', Valor: '{row[5]}'")

print("\n" + "="*70)

# Analisa especificamente as NFS-e
print("\nAnálise das NFS-e:")
c.execute("""
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN numero IS NULL OR numero = '' THEN 1 END) as sem_numero,
           COUNT(CASE WHEN data_emissao IS NULL OR data_emissao = '' THEN 1 END) as sem_data,
           COUNT(CASE WHEN nome_emitente IS NULL OR nome_emitente = '' THEN 1 END) as sem_emitente,
           COUNT(CASE WHEN valor IS NULL OR valor = '' OR valor = '0' THEN 1 END) as sem_valor
    FROM notas_detalhadas 
    WHERE tipo='NFS-e'
""")
stats = c.fetchone()
print(f"Total NFS-e: {stats[0]}")
print(f"Sem número: {stats[1]}")
print(f"Sem data: {stats[2]}")
print(f"Sem emitente: {stats[3]}")
print(f"Sem valor/valor zero: {stats[4]}")

print("\n" + "="*70)

# Mostra amostra de NFS-e COM dados completos
print("\nAmostra de NFS-e COM dados:")
c.execute("""
    SELECT numero, data_emissao, nome_emitente, valor, cnpj_emitente
    FROM notas_detalhadas 
    WHERE tipo='NFS-e' 
      AND numero IS NOT NULL AND numero != ''
      AND data_emissao IS NOT NULL AND data_emissao != ''
    ORDER BY data_emissao DESC
    LIMIT 10
""")
print("NFS-e válidas:")
for row in c.fetchall():
    print(f"  N: {row[0]}, Data: {row[1]}, Emit: {row[2][:30] if row[2] else 'N/A'}, Valor: {row[3]}, CNPJ: {row[4]}")

print("\n" + "="*70)

# Verifica ordem de carregamento (últimos 5000)
print("\nÚltimos 10 documentos no banco (ordem de carregamento):")
c.execute("""
    SELECT tipo, numero, data_emissao, nome_emitente
    FROM notas_detalhadas 
    ORDER BY data_emissao DESC
    LIMIT 10
""")
for idx, row in enumerate(c.fetchall(), 1):
    print(f"  {idx}. {row[0]}: N={row[1]}, Data={row[2]}, Emit={row[3][:30] if row[3] else 'N/A'}")

conn.close()
