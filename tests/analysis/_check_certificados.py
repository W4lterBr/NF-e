import sqlite3
import sys
sys.path.append('modules')

from crypto_portable import PortableCryptoManager

crypto = PortableCryptoManager()
conn = sqlite3.connect('notas_test.db')

# Busca certificados
print("=== CERTIFICADOS NO BANCO ===")
cur = conn.execute("SELECT cnpj_cpf, caminho, senha, informante, cUF_autor FROM certificados")
rows = cur.fetchall()

for row in rows:
    cnpj, caminho, senha, informante, cuf = row
    
    print(f"\n📜 Certificado:")
    print(f"   CNPJ/CPF: {cnpj}")
    print(f"   Caminho: {caminho[:50]}...")
    
    # Tenta descriptografar senha
    try:
        if senha and crypto.is_encrypted(senha):
            senha_dec = crypto.decrypt(senha)
            print(f"   Senha (criptografada): {senha[:30]}...")
            print(f"   Senha (descriptografada): {senha_dec}")
        else:
            print(f"   Senha (texto plano): {senha}")
    except Exception as e:
        print(f"   Senha: ERRO ao descriptografar - {e}")
    
    # Tenta descriptografar informante
    try:
        if informante and crypto.is_encrypted(informante):
            inf_dec = crypto.decrypt(informante)
            print(f"   Informante (criptografado): {informante[:30]}...")
            print(f"   Informante (descriptografado): {inf_dec}")
        else:
            print(f"   Informante: {informante}")
    except Exception as e:
        print(f"   Informante: ERRO ao descriptografar - {e}")
    
    print(f"   UF: {cuf}")

conn.close()
