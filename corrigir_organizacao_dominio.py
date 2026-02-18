# -*- coding: utf-8 -*-
"""
Correção URGENTE - Organização do Perfil DominioWeb
"""
import sqlite3

db_path = 'notas.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("🔧 CORRIGINDO PERFIL DOMINIOWEB")
print("="*80)
print()

# Mostra estado atual
cursor.execute("""
    SELECT id, nome, organizacao_tipo, xml_pdf_separado, ativo
    FROM perfis_armazenamento
    WHERE id = 3
""")

perfil = cursor.fetchone()
pid, nome, org_tipo, separado, ativo = perfil

print("📋 ESTADO ATUAL:")
print(f"   ID: {pid}")
print(f"   Nome: {nome}")
print(f"   Organização: {org_tipo} {'❌ INCORRETO!' if org_tipo == 'TIPO_CERTIFICADO' else '✅'}")
print(f"   XML/PDF separados: {bool(separado)}")
print(f"   Status: {'✅ Ativo' if ativo else '❌ Inativo'}")
print()

if org_tipo == 'TIPO_CERTIFICADO':
    print("⚠️  PROBLEMA DETECTADO:")
    print("   Organização TIPO_CERTIFICADO cria estrutura:")
    print("   DominioWeb/NFe/CNPJ/2025-08/ ← TIPO NA RAIZ (errado!)")
    print()
    print("🔧 CORRIGINDO PARA CERTIFICADO_TIPO...")
    print("   Nova estrutura:")
    print("   DominioWeb/CNPJ/2025-08/NFe/ ← CNPJ NA RAIZ (correto!)")
    print()
    
    # Corrige organização
    cursor.execute("""
        UPDATE perfis_armazenamento
        SET organizacao_tipo = 'CERTIFICADO_TIPO'
        WHERE id = 3
    """)
    
    conn.commit()
    print("✅ Organização corrigida!")
    print()

# Verifica se precisa ativar XML/PDF separados
print("📁 CONFIGURAÇÃO XML/PDF:")
if not separado:
    print("   ⚠️  XML e PDF na mesma pasta")
    print("   💡 Deseja SEPARAR em subpastas XML/ e PDF/ ? (S/N): ", end='')
    
    resposta = input().strip().upper()
    
    if resposta == 'S':
        cursor.execute("""
            UPDATE perfis_armazenamento
            SET xml_pdf_separado = 1
            WHERE id = 3
        """)
        conn.commit()
        print("   ✅ XML e PDF serão salvos em pastas separadas")
    else:
        print("   ℹ️  Mantido: XML e PDF na mesma pasta")
else:
    print("   ✅ XML e PDF já estão separados")

print()

# Mostra estado final
cursor.execute("""
    SELECT id, nome, pasta_base, formato_pasta_mes, organizacao_tipo, xml_pdf_separado, ativo
    FROM perfis_armazenamento
    WHERE id = 3
""")

perfil = cursor.fetchone()
pid, nome, pasta, formato, org_tipo, separado, ativo = perfil

print("="*80)
print("✅ CONFIGURAÇÃO FINAL")
print("="*80)
print(f"📋 Perfil: {nome}")
print(f"📂 Pasta: {pasta}")
print(f"📅 Formato mês: {formato}")
print(f"🏗️  Organização: {org_tipo}")
print(f"📁 XML/PDF: {'Pastas separadas' if separado else 'Mesma pasta'}")
print(f"⚡ Status: {'✅ Ativo' if ativo else '❌ Inativo'}")
print()
print("📋 ESTRUTURA DOS ARQUIVOS:")
print(f"   {pasta}/")
print(f"   └─ CNPJ/              ← Certificado/Empresa")
print(f"      └─ {formato}/      ← Mês (exemplo: 022026)")
print(f"         └─ NFe/         ← Tipo de documento")

if separado:
    print(f"            ├─ XML/")
    print(f"            │  └─ 12345-FORNECEDOR.xml")
    print(f"            └─ PDF/")
    print(f"               └─ 12345-FORNECEDOR.pdf")
else:
    print(f"            ├─ 12345-FORNECEDOR.xml")
    print(f"            └─ 12345-FORNECEDOR.pdf")

print("="*80)

conn.close()
