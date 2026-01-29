import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Verifica os 28 NFe que NÃO estão nos primeiros 1839
c.execute("""
    WITH primeiros_1839 AS (
        SELECT chave 
        FROM notas_detalhadas 
        ORDER BY data_emissao DESC 
        LIMIT 1839
    )
    SELECT numero, data_emissao, nome_emitente, valor
    FROM notas_detalhadas
    WHERE tipo = 'NFe'
      AND chave NOT IN (SELECT chave FROM primeiros_1839)
    ORDER BY data_emissao ASC
    LIMIT 30
""")

print("Os 28 NFe mais ANTIGOS (fora do LIMIT 1839):")
for num, data, nome, valor in c.fetchall():
    print(f"  N: {num}, Data: {data}, Emit: {nome[:35] if nome else 'N/A'}..., R$ {valor}")

conn.close()
