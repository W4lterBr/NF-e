"""
Script para corrigir xml_status das notas que têm XML no disco
mas estão marcadas como RESUMO
"""
import sqlite3
from pathlib import Path

db_path = 'notas.db'
conn = sqlite3.connect(db_path)

print("=" * 80)
print("CORRIGINDO STATUS DE XMLs")
print("=" * 80)

# Buscar todas as notas RESUMO que têm XML registrado
cursor = conn.execute('''
    SELECT nd.chave, xb.caminho_arquivo
    FROM notas_detalhadas nd
    INNER JOIN xmls_baixados xb ON nd.chave = xb.chave
    WHERE nd.xml_status = 'RESUMO'
      AND xb.caminho_arquivo IS NOT NULL
      AND xb.caminho_arquivo != ''
''')

notas_corrigir = []
for chave, caminho in cursor.fetchall():
    if caminho and Path(caminho).exists():
        notas_corrigir.append(chave)

print(f"\n✅ Encontradas {len(notas_corrigir)} notas RESUMO com XML no disco")

if notas_corrigir:
    print("\n🔄 Atualizando status para COMPLETO...")
    
    for i, chave in enumerate(notas_corrigir, 1):
        conn.execute(
            "UPDATE notas_detalhadas SET xml_status = 'COMPLETO' WHERE chave = ?",
            (chave,)
        )
        if i % 100 == 0:
            print(f"   Processadas {i}/{len(notas_corrigir)}...")
    
    conn.commit()
    print(f"\n✅ {len(notas_corrigir)} notas atualizadas para COMPLETO!")
    
    # Verificar resultado
    cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
    total_completo = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
    total_resumo = cursor.fetchone()[0]
    
    print("\n📊 RESULTADO FINAL:")
    print(f"   COMPLETO: {total_completo}")
    print(f"   RESUMO: {total_resumo}")
else:
    print("\n❌ Nenhuma nota precisa ser corrigida")

conn.close()
print("\n" + "=" * 80)
print("✅ Correção concluída!")
print("=" * 80)
