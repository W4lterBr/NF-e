"""
Script para corrigir o campo informante vazio nas notas existentes.
Preenche o informante baseado no CNPJ do tomador (destinatário) da nota.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "notas.db"

def fix_informante():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Busca todos os certificados
    certs = cursor.execute("SELECT DISTINCT informante FROM certificados").fetchall()
    print(f"\n{'='*60}")
    print(f"CORRIGINDO CAMPO INFORMANTE")
    print(f"{'='*60}")
    print(f"Certificados encontrados: {len(certs)}")
    
    total_updated = 0
    
    for (cert_informante,) in certs:
        if not cert_informante:
            continue
        
        # 2. Busca notas onde informante está vazio mas o CNPJ destinatário corresponde
        cursor.execute("""
            SELECT COUNT(*) FROM notas_detalhadas 
            WHERE (informante IS NULL OR informante = '') 
            AND cnpj_destinatario = ?
        """, (cert_informante,))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            # 3. Atualiza informante dessas notas
            cursor.execute("""
                UPDATE notas_detalhadas 
                SET informante = ? 
                WHERE (informante IS NULL OR informante = '') 
                AND cnpj_destinatario = ?
            """, (cert_informante, cert_informante))
            
            print(f"  {cert_informante}: {count} notas atualizadas")
            total_updated += count
    
    conn.commit()
    
    # 4. Verifica quantas notas ainda têm informante vazio
    remaining = cursor.execute("""
        SELECT COUNT(*) FROM notas_detalhadas 
        WHERE informante IS NULL OR informante = ''
    """).fetchone()[0]
    
    print(f"\n{'='*60}")
    print(f"RESULTADO:")
    print(f"  Total atualizado: {total_updated}")
    print(f"  Ainda vazios: {remaining}")
    print(f"{'='*60}\n")
    
    conn.close()

if __name__ == "__main__":
    fix_informante()
