"""
Remove resumos sem dados válidos (número, emitente, etc) do banco de dados.
"""
import sqlite3

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

# Busca resumos sem dados
resumos_vazios = conn.execute("""
    SELECT chave, numero, nome_emitente 
    FROM notas_detalhadas 
    WHERE xml_status='RESUMO' 
    AND (numero IS NULL OR numero = '' OR nome_emitente IS NULL OR nome_emitente = '')
""").fetchall()

print(f"Encontrados {len(resumos_vazios)} resumos sem dados válidos:\n")

for r in resumos_vazios:
    print(f"  • Chave: {r['chave'][:10]}...")

if resumos_vazios:
    cursor = conn.cursor()
    for r in resumos_vazios:
        cursor.execute("DELETE FROM notas_detalhadas WHERE chave = ?", (r['chave'],))
    conn.commit()
    print(f"\n✓ {len(resumos_vazios)} resumos removidos do banco")
else:
    print("✓ Nenhum resumo vazio encontrado")

conn.close()
print("\n➜ Reinicie a interface para ver as mudanças!")
