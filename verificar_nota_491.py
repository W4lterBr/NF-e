"""
Verifica informações da nota que está dando erro 491
"""
import sqlite3

chave = "35260172381189001001550010083154761637954119"

conn = sqlite3.connect('notas_test.db')
cursor = conn.cursor()

# Busca a nota
cursor.execute("""
    SELECT 
        chave_acesso, 
        cnpj_destinatario, 
        informante,
        status_nota,
        xml_status,
        data_emissao,
        razao_social_emitente
    FROM notas_detalhadas 
    WHERE chave_acesso = ?
""", (chave,))

nota = cursor.fetchone()

print("🔍 Verificando nota que deu erro 491:\n")
print(f"Chave: {chave}\n")

if nota:
    print("✅ Nota encontrada no banco:\n")
    print(f"  CNPJ Destinatário: {nota[1]}")
    print(f"  Informante (quem baixou): {nota[2]}")
    print(f"  Status: {nota[3]}")
    print(f"  XML Status: {nota[4]}")
    print(f"  Data Emissão: {nota[5]}")
    print(f"  Emitente: {nota[6]}")
    
    print("\n📋 Análise:")
    
    if nota[2] != "01773924000193":
        print(f"  ⚠️ PROBLEMA: O informante ({nota[2]}) não é 01773924000193")
        print(f"     Esta nota foi baixada com outro certificado!")
        print(f"     Você precisa manifestar com o certificado correto: {nota[2]}")
    else:
        print(f"  ✅ Informante correto: {nota[2]}")
    
    if "cancel" in nota[3].lower() or "denega" in nota[3].lower():
        print(f"  ⚠️ PROBLEMA: Nota está {nota[3]}")
        print(f"     Não é possível fazer Ciência em nota Cancelada/Denegada")
    
    # Verifica se já tem manifestação
    cursor.execute("""
        SELECT tipo_evento, data_evento 
        FROM notas_detalhadas 
        WHERE xml_status = 'EVENTO' 
        AND chave_acesso LIKE ?
        ORDER BY data_evento DESC
    """, (f'%{chave}%',))
    
    eventos = cursor.fetchall()
    if eventos:
        print(f"\n  ⚠️ MANIFESTAÇÕES ANTERIORES ENCONTRADAS:")
        for evento in eventos:
            print(f"     - {evento[0]} em {evento[1]}")
        print(f"     A nota pode já ter sido manifestada!")
    
else:
    print("❌ Nota NÃO encontrada no banco!")
    print("   A nota pode não existir no SEFAZ ou você não a baixou ainda")

print("\n💡 SOLUÇÃO:")
print("   Teste com OUTRA NOTA da lista que:")
print("   1. Não esteja cancelada")
print("   2. Não tenha manifestação anterior")
print("   3. Seja do CNPJ correto (01773924000193)")

conn.close()
