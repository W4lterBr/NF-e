#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica se NFS-e estão visíveis para a interface"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "notas.db"

print("\n" + "="*70)
print("VERIFICAÇÃO: NFS-e VISÍVEIS PARA A INTERFACE")
print("="*70)

with sqlite3.connect(db_path) as conn:
    # 1. Total de NFS-e
    total = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo LIKE '%NFS%'").fetchone()[0]
    print(f"\n✅ Total NFS-e em notas_detalhadas: {total}")
    
    # 2. Por tipo exato
    cursor = conn.execute("""
        SELECT tipo, COUNT(*) 
        FROM notas_detalhadas 
        WHERE tipo LIKE '%NFS%' 
        GROUP BY tipo
    """)
    print("\n📊 Por tipo:")
    for tipo, count in cursor.fetchall():
        print(f"  • {tipo}: {count}")
    
    # 3. Detalhes das NFS-e
    cursor = conn.execute("""
        SELECT tipo, numero, valor, nome_emitente, xml_status, informante
        FROM notas_detalhadas 
        WHERE tipo LIKE '%NFS%'
        ORDER BY numero
        LIMIT 10
    """)
    
    print(f"\n📋 Primeiras 10 NFS-e:")
    for row in cursor.fetchall():
        tipo, num, valor, nome, status, inf = row
        nome_curto = nome[:30] if nome else "N/A"
        print(f"  • {tipo} #{num} - R$ {valor} - {nome_curto} - {status} - {inf}")
    
    # 4. Verifica xml_status
    cursor = conn.execute("""
        SELECT xml_status, COUNT(*) 
        FROM notas_detalhadas 
        WHERE tipo LIKE '%NFS%'
        GROUP BY xml_status
    """)
    print(f"\n🔍 Por xml_status:")
    for status, count in cursor.fetchall():
        print(f"  • {status}: {count}")
    
    # 5. Query que a interface usa (sem filtro)
    cursor = conn.execute("""
        SELECT COUNT(*) 
        FROM notas_detalhadas 
        WHERE xml_status != 'EVENTO'
    """)
    total_interface = cursor.fetchone()[0]
    print(f"\n🖥️ Total que a interface deveria ver (xml_status != EVENTO): {total_interface}")

print("\n" + "="*70)
print("💡 INSTRUÇÕES:")
print("="*70)
print("1. Feche e reabra 'Busca NF-e.py'")
print("2. Clique no filtro 'Tipo' e selecione 'NFS-e'")
print("3. As NFS-e deverão aparecer com ícone verde (COMPLETO)")
print("="*70 + "\n")
