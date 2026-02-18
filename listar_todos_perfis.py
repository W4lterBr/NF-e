# -*- coding: utf-8 -*-
"""
Lista TODOS os perfis (ativos e inativos)
"""
import sqlite3

db_path = 'notas.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("📊 TODOS OS PERFIS DE ARMAZENAMENTO")
print("="*80)
print()

cursor.execute("""
    SELECT 
        id,
        nome,
        pasta_base,
        formato_pasta_mes,
        xml_pdf_separado,
        organizacao_tipo,
        ativo,
        is_default
    FROM perfis_armazenamento
    ORDER BY id
""")

perfis = cursor.fetchall()

if not perfis:
    print("⚠️  Nenhum perfil encontrado")
else:
    for perfil in perfis:
        pid, nome, pasta, formato, separado, org_tipo, ativo, is_default = perfil
        
        status_icon = "✅" if ativo else "❌"
        default_icon = "⭐" if is_default else "  "
        
        print(f"{status_icon} {default_icon} PERFIL #{pid}: {nome}")
        print(f"   📂 Pasta: {pasta}")
        print(f"   📅 Formato: {formato}")
        print(f"   🏗️  Organização: {org_tipo}")
        print(f"   📁 XML/PDF: {'Separados' if separado else 'Mesma pasta'}")
        print(f"   ⚡ Status: {'Ativo' if ativo else 'Inativo'}")
        print(f"   ⭐ Padrão: {'Sim' if is_default else 'Não'}")
        
        # Mostra estrutura esperada
        print(f"   📋 Estrutura:")
        
        if org_tipo == 'CERTIFICADO_TIPO':
            print(f"      {pasta}/")
            print(f"      └─ CERTIFICADO/")
            print(f"         └─ {formato}/")
            print(f"            └─ TIPO/")
            if separado:
                print(f"               ├─ XML/")
                print(f"               └─ PDF/")
        elif org_tipo == 'TIPO_CERTIFICADO':
            print(f"      {pasta}/")
            print(f"      └─ TIPO/")
            print(f"         └─ CERTIFICADO/")
            print(f"            └─ {formato}/")
            if separado:
                print(f"               ├─ XML/")
                print(f"               └─ PDF/")
        
        print()

print("="*80)
print(f"📊 Total: {len(perfis)} perfil(is)")
print(f"   Ativos: {sum(1 for p in perfis if p[6])}")
print(f"   Inativos: {sum(1 for p in perfis if not p[6])}")
print("="*80)

conn.close()
