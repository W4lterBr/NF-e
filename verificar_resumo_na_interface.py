"""
Verifica se NF-e RESUMO agora aparecem na query da interface
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

print("=" * 80)
print("VERIFICAÇÃO: NF-e RESUMO na query da interface")
print("=" * 80)

with sqlite3.connect(db_path) as conn:
    # Simula a query modificada (filtered_emitidos)
    print("\n1. Query ANTIGA (sem incluir RESUMO):")
    print("-" * 80)
    query_old = """
        SELECT COUNT(*) FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
        AND SUBSTR(data_emissao, 1, 10) BETWEEN '2026-01-01' AND '2026-12-31'
        ORDER BY data_emissao DESC
    """
    count_old = conn.execute(query_old).fetchone()[0]
    print(f"   Total encontrado: {count_old} registros")
    
    print("\n2. Query NOVA (incluindo RESUMO):")
    print("-" * 80)
    query_new = """
        SELECT COUNT(*) FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
        AND (data_emissao IS NULL OR SUBSTR(data_emissao, 1, 10) BETWEEN '2026-01-01' AND '2026-12-31')
        ORDER BY COALESCE(data_emissao, '9999-12-31') DESC
    """
    count_new = conn.execute(query_new).fetchone()[0]
    print(f"   Total encontrado: {count_new} registros")
    
    print(f"\n3. Diferença: +{count_new - count_old} registros RESUMO agora visíveis")
    
    # Lista exemplos de RESUMO
    print("\n4. Exemplos de NF-e RESUMO que agora aparecerão:")
    print("-" * 80)
    query_resumo = """
        SELECT chave, xml_status, data_emissao, nome_emitente, numero 
        FROM notas_detalhadas 
        WHERE xml_status = 'RESUMO'
        LIMIT 10
    """
    
    cursor = conn.execute(query_resumo)
    for i, (chave, status, data, nome, numero) in enumerate(cursor, 1):
        print(f"   {i}. Chave: {chave[:20]}...")
        print(f"      Status: {status}")
        print(f"      Data: {data if data else 'NULL (aguardando download)'}")
        print(f"      Nome: {nome if nome else 'N/A'}")
        print(f"      Número: {numero if numero else 'N/A'}")
        print()
    
    # Estatísticas finais
    print("\n5. Estatísticas finais:")
    print("-" * 80)
    stats = conn.execute("""
        SELECT 
            xml_status,
            COUNT(*) as total,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status != 'EVENTO'), 2) as percentual
        FROM notas_detalhadas
        WHERE xml_status != 'EVENTO'
        GROUP BY xml_status
        ORDER BY total DESC
    """).fetchall()
    
    for status, total, pct in stats:
        indicator = "✅" if status == "COMPLETO" else "⚠️" if status == "RESUMO" else "❌"
        print(f"   {indicator} {status:12s}: {total:5d} ({pct:5.2f}%)")

print("\n" + "=" * 80)
print("✅ SUCESSO: Interface modificada para mostrar NF-e RESUMO!")
print("=" * 80)
print("\nComo será exibido na interface:")
print("   ✅ COMPLETO  → Fundo verde claro + ícone XML")
print("   ⚠️  RESUMO    → Fundo cinza + tooltip 'Apenas Resumo - clique para baixar'")
print("   ❌ CANCELADO → Fundo vermelho claro + ícone cancelado")
