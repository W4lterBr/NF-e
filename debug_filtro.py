"""Script de debug para verificar filtro de certificados"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

with sqlite3.connect(db_path) as conn:
    conn.row_factory = sqlite3.Row
    
    print("=" * 80)
    print("CERTIFICADOS:")
    print("=" * 80)
    certs = conn.execute("SELECT informante, cnpj_cpf FROM certificados ORDER BY informante").fetchall()
    for c in certs:
        print(f"  informante: '{c['informante']}', cnpj_cpf: '{c['cnpj_cpf']}'")
    
    print("\n" + "=" * 80)
    print("NOTAS DETALHADAS (primeiras 10):")
    print("=" * 80)
    notas = conn.execute("""
        SELECT chave, numero, nome_emitente, informante, xml_status 
        FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
        ORDER BY data_emissao DESC 
        LIMIT 10
    """).fetchall()
    
    for n in notas:
        print(f"  Num: {n['numero']:>6} | Emit: {n['nome_emitente'][:30]:<30} | Informante: '{n['informante']}' | Status: {n['xml_status']}")
    
    print("\n" + "=" * 80)
    print("CONTAGEM POR INFORMANTE (exceto eventos):")
    print("=" * 80)
    contagem = conn.execute("""
        SELECT informante, COUNT(*) as total 
        FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
        GROUP BY informante 
        ORDER BY total DESC
    """).fetchall()
    
    for c in contagem:
        inf = c['informante'] if c['informante'] else '(VAZIO)'
        print(f"  Informante: {inf:>15} -> {c['total']:>4} notas")
    
    print("\n" + "=" * 80)
    print("TESTE DE FILTRO:")
    print("=" * 80)
    
    # Testa filtro para cada certificado
    for cert in certs:
        informante = cert['informante']
        total = conn.execute("""
            SELECT COUNT(*) as cnt 
            FROM notas_detalhadas 
            WHERE informante = ? AND xml_status != 'EVENTO'
        """, (informante,)).fetchone()['cnt']
        print(f"  Certificado '{informante}' -> {total} notas filtradas")
