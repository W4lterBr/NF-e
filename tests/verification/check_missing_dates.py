import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

print("Verificando notas sem data que poderiam ser extraídas da chave...")
print("=" * 70)

# Busca notas sem data mas com chave válida
c.execute("""
    SELECT COUNT(*) FROM notas_detalhadas 
    WHERE (data_emissao IS NULL OR data_emissao = '')
    AND LENGTH(chave) = 44
    AND chave NOT LIKE 'NFSE_%'
""")
sem_data = c.fetchone()[0]

print(f"Total de notas sem data mas com chave válida: {sem_data}")

if sem_data > 0:
    print(f"\nEssas {sem_data} notas PODEM ter data extraída da chave!")
    print("\nExemplos:")
    c.execute("""
        SELECT chave, numero, xml_status, nome_emitente
        FROM notas_detalhadas 
        WHERE (data_emissao IS NULL OR data_emissao = '')
        AND LENGTH(chave) = 44
        AND chave NOT LIKE 'NFSE_%'
        LIMIT 5
    """)
    for row in c.fetchall():
        chave = row[0]
        if chave and len(chave) >= 6:
            aa = chave[2:4]
            mm = chave[4:6]
            data_extraida = f"20{aa}-{mm}-01"
        else:
            data_extraida = "N/A"
        print(f"  Chave: {chave[:20]}... | Numero: {row[1]} | Status: {row[2]} | Data extraível: {data_extraida}")
    
    print("\n" + "=" * 70)
    print("SUGESTÃO: As notas sem data mostrarão '(Resumo)' na interface")
    print("           Mas ao abrir, a data será extraída da chave automaticamente")
    print("=" * 70)
else:
    print("\n✅ Todas as notas têm data ou não podem extrair da chave!")

conn.close()
