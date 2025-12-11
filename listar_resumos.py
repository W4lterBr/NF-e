import sqlite3

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

resumos = conn.execute("SELECT chave, numero, nome_emitente, cnpj_emitente, data_emissao FROM notas_detalhadas WHERE xml_status='RESUMO'").fetchall()

print(f"Total de resumos no banco: {len(resumos)}\n")

for r in resumos:
    print(f"Chave: {r['chave']}")
    print(f"  Número: {r['numero']}")
    print(f"  Emitente: {r['nome_emitente']}")
    print(f"  CNPJ: {r['cnpj_emitente']}")
    print(f"  Data: {r['data_emissao']}")
    print()

if resumos:
    print("\n⚠ AÇÃO: Remover todos os resumos do banco? (s/n)")
    resposta = input("Resposta: ")
    if resposta.lower() == 's':
        cursor = conn.cursor()
        for r in resumos:
            cursor.execute("DELETE FROM notas_detalhadas WHERE chave = ?", (r['chave'],))
        conn.commit()
        print(f"\n✓ {len(resumos)} resumos removidos")
    else:
        print("\nCancelado")

conn.close()
