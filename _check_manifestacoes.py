import sqlite3

chave = "35260132668157000186570010002144121010570787"

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row

print(f"=== Procurando manifestações para chave {chave} ===")
manifestacoes = conn.execute('SELECT * FROM manifestacoes WHERE chave = ?', (chave,)).fetchall()

if manifestacoes:
    for m in manifestacoes:
        print(f"\nTipo: {m['tipo_evento']}")
        print(f"Protocolo: {m['protocolo']}")
        print(f"Status: {m['status']}")
        print(f"Data: {m['data_envio']}")
else:
    print("❌ Nenhuma manifestação encontrada no banco")

print(f"\n=== Verificando se o documento existe no banco ===")
nota = conn.execute('SELECT numero, nome_emitente, tipo_documento FROM notas_detalhadas WHERE chave = ?', (chave,)).fetchone()

if nota:
    print(f"✅ Documento encontrado:")
    print(f"   Número: {nota['numero']}")
    print(f"   Emitente: {nota['nome_emitente']}")
    print(f"   Tipo: {nota['tipo_documento']}")
else:
    print("❌ Documento NÃO encontrado no banco")

conn.close()
