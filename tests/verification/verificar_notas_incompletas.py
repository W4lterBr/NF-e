"""
Verifica se há notas no banco com nomes genéricos ou sem dados válidos.
"""
import sqlite3

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

# Busca notas com número vazio ou nome vazio
notas_problematicas = conn.execute("""
    SELECT chave, numero, nome_emitente, cnpj_emitente, xml_status 
    FROM notas_detalhadas 
    WHERE numero IS NULL OR numero = '' OR nome_emitente IS NULL OR nome_emitente = ''
""").fetchall()

print(f"Encontradas {len(notas_problematicas)} notas com dados incompletos:\n")

for nota in notas_problematicas:
    print(f"Chave: {nota['chave']}")
    print(f"  Número: '{nota['numero']}'")
    print(f"  Emitente: '{nota['nome_emitente']}'")
    print(f"  CNPJ: '{nota['cnpj_emitente']}'")
    print(f"  Status: {nota['xml_status']}")
    print()

if notas_problematicas:
    resposta = input("\nDeseja remover estas notas do banco? (s/n): ")
    if resposta.lower() == 's':
        cursor = conn.cursor()
        for nota in notas_problematicas:
            cursor.execute("DELETE FROM notas_detalhadas WHERE chave = ?", (nota['chave'],))
        conn.commit()
        print(f"\n✓ {len(notas_problematicas)} notas removidas do banco")
    else:
        print("\nOperação cancelada")
else:
    print("✓ Nenhuma nota com dados incompletos encontrada")

conn.close()
