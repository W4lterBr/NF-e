"""
Correção FORÇADA de xml_status - Versão simplificada e robusta
"""
import sqlite3
from pathlib import Path

db_path = 'notas.db'

print("=" * 80)
print("CORREÇÃO FORÇADA DE XML_STATUS")
print("=" * 80)

try:
    conn = sqlite3.connect(db_path, timeout=30)
    
    # 1. Verificar estado atual
    cursor = conn.execute("SELECT xml_status, COUNT(*) FROM notas_detalhadas GROUP BY xml_status")
    print("\n📊 ANTES DA CORREÇÃO:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # 2. Buscar todas as notas RESUMO com XML registrado
    cursor = conn.execute('''
        SELECT nd.chave, xb.caminho_arquivo
        FROM notas_detalhadas nd
        INNER JOIN xmls_baixados xb ON nd.chave = xb.chave
        WHERE nd.xml_status = 'RESUMO'
          AND xb.caminho_arquivo IS NOT NULL
          AND xb.caminho_arquivo != ''
    ''')
    
    todas_notas = cursor.fetchall()
    print(f"\n🔍 Encontradas {len(todas_notas)} notas RESUMO com caminho registrado")
    
    # 3. Verificar quais arquivos existem
    notas_corrigir = []
    print("\n🔍 Verificando existência física dos arquivos...")
    
    for i, (chave, caminho) in enumerate(todas_notas, 1):
        if i % 100 == 0:
            print(f"   Verificadas {i}/{len(todas_notas)}...")
        
        if caminho and Path(caminho).exists():
            notas_corrigir.append(chave)
    
    print(f"\n✅ {len(notas_corrigir)} arquivos confirmados no disco")
    
    # 4. Atualizar em lotes
    if notas_corrigir:
        print("\n🔄 Atualizando status no banco...")
        
        # Atualizar em lotes de 100
        batch_size = 100
        for i in range(0, len(notas_corrigir), batch_size):
            batch = notas_corrigir[i:i+batch_size]
            placeholders = ','.join(['?'] * len(batch))
            
            conn.execute(
                f"UPDATE notas_detalhadas SET xml_status = 'COMPLETO' WHERE chave IN ({placeholders})",
                batch
            )
            
            if (i + batch_size) % 500 == 0:
                print(f"   Atualizadas {min(i + batch_size, len(notas_corrigir))}/{len(notas_corrigir)}...")
        
        # Commit final
        conn.commit()
        print(f"\n✅ COMMIT realizado! {len(notas_corrigir)} registros atualizados")
    
    # 5. Verificar resultado
    cursor = conn.execute("SELECT xml_status, COUNT(*) FROM notas_detalhadas GROUP BY xml_status")
    print("\n📊 DEPOIS DA CORREÇÃO:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    conn.close()
    print("\n" + "=" * 80)
    print("✅ Correção concluída com sucesso!")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()
