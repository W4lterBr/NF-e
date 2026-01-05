#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar CT-e específico no banco de dados
"""

import sqlite3
from pathlib import Path

CHAVE = '50251203232675000154570010056290311009581385'

def main():
    db_path = Path('notas.db')
    
    if not db_path.exists():
        print(f"❌ Banco não encontrado: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    
    print("="*70)
    print("VERIFICANDO CT-e NO BANCO")
    print("="*70)
    print(f"Chave: {CHAVE}\n")
    
    # Buscar CT-e
    cursor = conn.execute("""
        SELECT chave, numero, tipo, xml_status, status, data_emissao, cnpj_emitente
        FROM notas_detalhadas 
        WHERE chave = ?
    """, (CHAVE,))
    
    row = cursor.fetchone()
    
    if row:
        print("✅ CT-e encontrado:")
        print(f"   Chave: {row[0]}")
        print(f"   Número: {row[1]}")
        print(f"   Tipo: {row[2]}")
        print(f"   XML Status: {row[3]}")
        print(f"   Status: {row[4]}")
        print(f"   Data Emissão: {row[5]}")
        print(f"   CNPJ Emitente: {row[6]}")
    else:
        print("❌ CT-e não encontrado no banco")
    
    print("\n" + "="*70)
    print("BUSCANDO EVENTOS RELACIONADOS")
    print("="*70)
    
    # Buscar eventos com essa chave
    cursor = conn.execute("""
        SELECT chave, tipo, xml_status, status 
        FROM notas_detalhadas 
        WHERE tipo = 'CTe' AND xml_status = 'EVENTO'
    """)
    
    eventos = cursor.fetchall()
    
    if eventos:
        print(f"\n📋 Encontrados {len(eventos)} eventos de CT-e no banco:")
        for ev in eventos[:10]:  # Mostrar primeiros 10
            print(f"   - Chave: {ev[0]}, Status: {ev[3]}")
    else:
        print("\n❌ Nenhum evento de CT-e com xml_status='EVENTO' encontrado")
    
    # Buscar qualquer registro com a chave (completo ou parcial)
    cursor = conn.execute("""
        SELECT chave, tipo, xml_status, status 
        FROM notas_detalhadas 
        WHERE chave LIKE ?
    """, (f"%{CHAVE[-20:]}%",))
    
    similares = cursor.fetchall()
    
    if len(similares) > 1:
        print(f"\n🔍 Encontrados {len(similares)} registros similares:")
        for sim in similares:
            print(f"   - Chave: {sim[0]}, Tipo: {sim[1]}, XML: {sim[2]}, Status: {sim[3]}")
    
    conn.close()

if __name__ == "__main__":
    main()
