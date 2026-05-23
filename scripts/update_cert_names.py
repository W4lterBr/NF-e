import sqlite3

conn = sqlite3.connect('notas.db')

# Atualiza nomes baseados na imagem do usuário
updates = [
    ("61-MATPARCG", "33251845000109"),
    ("75-PARTNESS FUTURA DIST", "47539664000197"),
    ("79-ALFA COMPUTADORES", "01773924000193"),
    ("80-LUZ COMERCIO ALIMENT", "49068153000160"),
    ("99-JL COMERCIO", "48160135000140"),
]

for nome, cnpj in updates:
    conn.execute('UPDATE certificados SET nome_certificado = ? WHERE informante = ?', (nome, cnpj))
    print(f"✅ {nome} → {cnpj}")

conn.commit()
conn.close()

print("\n✅ Todos os certificados atualizados!")
print("Agora os XMLs serão salvos em pastas amigáveis no armazenamento.")
