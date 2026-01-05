"""
Corrige xml_status das notas existentes verificando se arquivos realmente existem
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
db_path = BASE_DIR / 'notas_test.db'

print("=" * 80)
print("CORREÇÃO DE xml_status")
print("=" * 80)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Busca todas as notas marcadas como COMPLETO
cursor.execute("""
    SELECT n.chave, n.numero, n.nome_emitente, n.xml_status, x.caminho_arquivo
    FROM notas_detalhadas n
    LEFT JOIN xmls_baixados x ON n.chave = x.chave
    WHERE n.xml_status = 'COMPLETO'
""")

notas_completas = cursor.fetchall()
print(f"\n📊 Notas marcadas como COMPLETO: {len(notas_completas)}")

corrigidas = 0

for chave, numero, emitente, status, caminho in notas_completas:
    print(f"\n🔍 NF {numero} - {emitente}")
    print(f"   Chave: {chave[:25]}...")
    
    # Verifica se tem arquivo
    tem_arquivo = False
    
    if caminho:
        arquivo = Path(caminho)
        if arquivo.exists():
            tem_arquivo = True
            print(f"   ✅ Arquivo existe: {arquivo.name}")
        else:
            print(f"   ❌ Caminho registrado mas arquivo não existe")
            print(f"      {caminho}")
    else:
        print(f"   ❌ Sem caminho registrado em xmls_baixados")
    
    # Se não tem arquivo, corrige para RESUMO
    if not tem_arquivo:
        cursor.execute(
            "UPDATE notas_detalhadas SET xml_status = 'RESUMO' WHERE chave = ?",
            (chave,)
        )
        corrigidas += 1
        print(f"   🔧 Corrigido: COMPLETO → RESUMO")

conn.commit()

print(f"\n" + "=" * 80)
print(f"RESULTADO:")
print(f"   Total analisadas: {len(notas_completas)}")
print(f"   Corrigidas: {corrigidas}")
print(f"   Mantidas COMPLETO: {len(notas_completas) - corrigidas}")
print(f"=" * 80)

# Mostra situação final
cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
total_completas = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
total_resumo = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'EVENTO'")
total_eventos = cursor.fetchone()[0]

print(f"\n📊 Situação final:")
print(f"   COMPLETO: {total_completas}")
print(f"   RESUMO: {total_resumo}")
print(f"   EVENTO: {total_eventos}")

conn.close()

print(f"\n✅ Correção concluída!")
print(f"   Reinicie a interface para ver as mudanças.")
