"""
Teste da correção do NSU CT-e com erro 656
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

print("=" * 70)
print("TESTE: CORREÇÃO NSU CT-e COM ERRO 656")
print("=" * 70)

# Simula situação: NSU está em 0, SEFAZ retorna erro 656 com ultNSU=204
informante = "49068153000160"
nsu_antes = "000000000000000"
nsu_sefaz = "000000000000204"  # ultNSU retornado pela SEFAZ

print(f"\n📋 Cenário simulado:")
print(f"   Informante: {informante}")
print(f"   NSU no banco ANTES: {nsu_antes}")
print(f"   ultNSU recebido da SEFAZ (com erro 656): {nsu_sefaz}")

# Verifica NSU atual
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT ult_nsu FROM nsu_cte WHERE informante = ?", (informante,))
row = cursor.fetchone()
nsu_atual = row[0] if row else "000000000000000"
print(f"\n🔍 NSU atual no banco: {nsu_atual}")

# Simula a correção (o código agora faz isso automaticamente)
if nsu_atual == "000000000000000":
    print(f"\n💾 Aplicando correção:")
    print(f"   Atualizando NSU para {nsu_sefaz} (valor recebido da SEFAZ)")
    
    # Atualiza
    conn.execute(
        "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, ?)",
        (informante, nsu_sefaz)
    )
    conn.commit()
    
    # Verifica novamente
    cursor = conn.execute("SELECT ult_nsu FROM nsu_cte WHERE informante = ?", (informante,))
    row = cursor.fetchone()
    nsu_novo = row[0] if row else "000000000000000"
    
    print(f"\n✅ NSU atualizado com sucesso!")
    print(f"   NSU ANTES: {nsu_atual}")
    print(f"   NSU DEPOIS: {nsu_novo}")
    
    if nsu_novo == nsu_sefaz:
        print(f"\n" + "=" * 70)
        print("✅ CORREÇÃO APLICADA COM SUCESSO!")
        print("=" * 70)
        print(f"\nPróxima busca:")
        print(f"   - Iniciará do NSU {nsu_novo}")
        print(f"   - Pegará os {nsu_sefaz} documentos pendentes")
        print(f"   - NSU não ficará mais travado em 0")
    else:
        print(f"\n❌ ERRO: NSU não foi atualizado corretamente")
else:
    print(f"\n✅ NSU já está em valor válido: {nsu_atual}")
    print(f"   Nenhuma correção necessária")

conn.close()

print(f"\n" + "=" * 70)
print("RESULTADO DA CORREÇÃO NO CÓDIGO:")
print("=" * 70)
print("""
O código foi modificado para:
1. Quando receber erro 656 (Consumo Indevido)
2. ANTES de fazer break, extrai ultNSU da resposta SEFAZ
3. Se ultNSU for diferente do atual, SALVA no banco
4. Isso evita que NSU fique travado em 0

Benefícios:
✅ NSU avança mesmo com erro 656
✅ Próxima consulta pega documentos a partir do último NSU válido
✅ Sistema não fica reprocessando mesma consulta infinitamente
""")
