import sqlite3
import re

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Verificando datas inválidas no banco...")
print("=" * 70)

# Busca datas com dia > 31
c.execute("""
    SELECT COUNT(*) FROM notas_detalhadas 
    WHERE data_emissao LIKE '____-__-%' 
    AND CAST(SUBSTR(data_emissao, 9, 2) AS INTEGER) > 31
""")
datas_invalidas = c.fetchone()[0]

print(f"Total de datas com dia > 31: {datas_invalidas}")

if datas_invalidas > 0:
    print("\nExemplos de datas inválidas:")
    c.execute("""
        SELECT chave, numero, data_emissao, nome_emitente 
        FROM notas_detalhadas 
        WHERE data_emissao LIKE '____-__-%' 
        AND CAST(SUBSTR(data_emissao, 9, 2) AS INTEGER) > 31
        LIMIT 10
    """)
    for row in c.fetchall():
        chave_preview = row[0][:20] if row[0] else "N/A"
        print(f"  Chave: {chave_preview}... | Numero: {row[1]} | Data: {row[2]} | Emitente: {row[3][:30] if row[3] else 'N/A'}")
    
    print("\n" + "=" * 70)
    print("AÇÃO NECESSÁRIA: Executar script de correção")
    print("=" * 70)
else:
    print("\n✅ Não há datas inválidas no banco!")

conn.close()
