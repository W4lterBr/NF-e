import sqlite3

conn = sqlite3.connect('notas.db')

# Buscar notas em situação RESUMO
query = """
SELECT chave, situacao 
FROM notas_detalhadas 
WHERE informante='33251845000109' 
  AND SUBSTR(chave, 21, 2)='55'
  AND (situacao LIKE '%resumo%' OR situacao LIKE '%Resumo%' OR situacao = '')
LIMIT 10
"""

cur = conn.execute(query)
notas = cur.fetchall()

if notas:
    print(f"Encontradas {len(notas)} notas:")
    for chave, situacao in notas:
        print(f"  {chave} - Situação: '{situacao}'")
else:
    print("Nenhuma nota em RESUMO encontrada. Listando primeiras 5 notas:")
    cur2 = conn.execute("""
        SELECT chave, situacao 
        FROM notas_detalhadas 
        WHERE informante='33251845000109'
          AND SUBSTR(chave, 21, 2)='55'
        LIMIT 5
    """)
    for chave, situacao in cur2.fetchall():
        print(f"  {chave} - Situação: '{situacao}'")

conn.close()
