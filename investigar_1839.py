import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Verifica todas as combinações de filtros que resultam em ~1839
print("Possíveis filtros que resultam em 1839 documentos:")
print("\n" + "="*70)

# 1. Com LIMIT 1839?
c.execute("SELECT COUNT(*) FROM (SELECT * FROM notas_detalhadas ORDER BY data_emissao DESC LIMIT 1839)")
count = c.fetchone()[0]
print(f"LIMIT 1839: {count} documentos")

# 2. Por tipo e limite
c.execute("""
    SELECT tipo, COUNT(*) 
    FROM (SELECT * FROM notas_detalhadas ORDER BY data_emissao DESC LIMIT 1839) 
    GROUP BY tipo
""")
print("\nComposição dos primeiros 1839 documentos:")
for tipo, cnt in c.fetchall():
    print(f"  {tipo}: {cnt}")

print("\n" + "="*70)

# 3. Verifica se 1839 = 1867 NFe - alguma coisa
nfe_total = c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFe'").fetchone()[0]
print(f"\nTotal NFe: {nfe_total}")
print(f"Diferença (1867 - 28 = 1839): {nfe_total - 28}")

# 4. Com xml_status
c.execute("""
    SELECT xml_status, COUNT(*) 
    FROM notas_detalhadas 
    WHERE tipo='NFe'
    GROUP BY xml_status
""")
print("\nNFe por xml_status:")
for status, cnt in c.fetchall():
    print(f"  {status}: {cnt}")

# 5. Verifica se há linhas vazias que não foram pegas
c.execute("""
    SELECT COUNT(*) 
    FROM notas_detalhadas 
    WHERE numero IS NOT NULL AND numero != ''
      AND data_emissao IS NOT NULL AND data_emissao != ''
""")
total_valid = c.fetchone()[0]
print(f"\n" + "="*70)
print(f"Documentos COM dados válidos: {total_valid}")

conn.close()
