# -*- coding: utf-8 -*-
"""
Análise dos perfis de armazenamento ativos
"""
import sqlite3
import sys
import os

db_path = os.path.join(os.path.dirname(__file__), 'notas.db')

print("="*80)
print("📊 PERFIS DE ARMAZENAMENTO ATIVOS")
print("="*80)
print()

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Busca perfis ativos
    cursor.execute("""
        SELECT 
            id,
            nome,
            pasta_base,
            formato_pasta_mes,
            xml_pdf_separado,
            organizacao_tipo,
            ativo
        FROM perfis_armazenamento
        WHERE ativo = 1
        ORDER BY id
    """)
    
    perfis = cursor.fetchall()
    
    if not perfis:
        print("⚠️  Nenhum perfil ativo encontrado")
    else:
        print(f"✅ {len(perfis)} perfil(is) ativo(s):")
        print()
        
        for perfil in perfis:
            pid, nome, pasta, formato, separado, org_tipo, ativo = perfil
            print(f"🔹 PERFIL #{pid}: {nome}")
            print(f"   Pasta base: {pasta}")
            print(f"   Formato mês: {formato}")
            print(f"   XML/PDF separados: {bool(separado)}")
            print(f"   Organização: {org_tipo}")
            print(f"   Status: {'✅ Ativo' if ativo else '❌ Inativo'}")
            print()
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)

print("="*80)
