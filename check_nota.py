import sqlite3

conn = sqlite3.connect('notas_test.db')
c = conn.cursor()
c.execute('SELECT informante, cnpj_destinatario FROM notas_detalhadas WHERE chave = ?', 
          ('35260172381189001001550010083154761637954119',))
r = c.fetchone()

if r:
    print(f"✅ Nota encontrada!")
    print(f"   Informante: {r[0]}")
    print(f"   CNPJ Destinatário: {r[1]}")
    print()
    if r[0] != "01773924000193":
        print(f"⚠️ PROBLEMA: Esta nota pertence ao CNPJ {r[0]}, não ao 01773924000193!")
        print(f"   Use o certificado correto para manifestar.")
    else:
        print(f"✅ Certificado correto!")
else:
    print("❌ Nota não encontrada no banco de dados!")
    print("   Teste com outra nota da lista")

conn.close()
