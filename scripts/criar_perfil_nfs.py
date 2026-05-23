# -*- coding: utf-8 -*-
"""
Cria perfil adicional para pasta NFs
"""
import sqlite3

db_path = 'notas.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("🆕 CRIANDO PERFIL ADICIONAL: NFs")
print("="*80)
print()

# Verifica se já existe
cursor.execute("SELECT COUNT(*) FROM perfis_armazenamento WHERE nome = 'Perfil NFs'")
count = cursor.fetchone()[0]

if count > 0:
    print("⚠️  Perfil 'Perfil NFs' já existe!")
    print()
    cursor.execute("""
        SELECT id, pasta_base, ativo
        FROM perfis_armazenamento
        WHERE nome = 'Perfil NFs'
    """)
    perfil = cursor.fetchone()
    print(f"   ID: {perfil[0]}")
    print(f"   Pasta: {perfil[1]}")
    print(f"   Status: {'Ativo ✅' if perfil[2] else 'Inativo ⭕'}")
    print()
    
    resposta = input("Deseja reativar este perfil? (S/N): ").strip().upper()
    
    if resposta == 'S':
        cursor.execute("""
            UPDATE perfis_armazenamento
            SET ativo = 1
            WHERE nome = 'Perfil NFs'
        """)
        conn.commit()
        print("✅ Perfil reativado!")
    else:
        print("ℹ️  Mantido como está")
else:
    # Cria novo perfil
    print("📋 Criando novo perfil...")
    
    cursor.execute("""
        INSERT INTO perfis_armazenamento 
        (nome, pasta_base, formato_pasta_mes, xml_pdf_separado, organizacao_tipo, ativo, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'Perfil NFs',
        'C:\\Arquivo Walter - Empresas\\Notas\\NFs',
        'MMAAAA',
        1,  # XML/PDF separados
        'CERTIFICADO_TIPO',
        1,  # Ativo
        0   # Não é padrão
    ))
    
    conn.commit()
    new_id = cursor.lastrowid
    
    print()
    print("✅ Perfil criado com sucesso!")
    print()
    print(f"📋 ID: {new_id}")
    print(f"📂 Pasta: C:\\Arquivo Walter - Empresas\\Notas\\NFs")
    print(f"📅 Formato: MMAAAA (exemplo: 022026)")
    print(f"🏗️  Organização: CERTIFICADO_TIPO (CNPJ/MÊS/TIPO)")
    print(f"📁 XML/PDF: Separados")
    print(f"⚡ Status: Ativo ✅")
    print()

# Lista todos os perfis ativos
print("="*80)
print("📊 PERFIS ATIVOS NO SISTEMA:")
print("="*80)
print()

cursor.execute("""
    SELECT id, nome, pasta_base, formato_pasta_mes, organizacao_tipo, is_default
    FROM perfis_armazenamento
    WHERE ativo = 1
    ORDER BY is_default DESC, id ASC
""")

perfis = cursor.fetchall()

for perfil in perfis:
    pid, nome, pasta, formato, org_tipo, is_default = perfil
    
    padrao_icon = "⭐" if is_default else ""
    
    print(f"✅ {padrao_icon} PERFIL #{pid}: {nome}")
    print(f"   📂 Pasta: {pasta}")
    print(f"   📅 Formato: {formato}")
    
    if org_tipo == 'TIPO_CERTIFICADO':
        print(f"   🏗️  Estrutura: NFe/CNPJ/012026/")
    else:
        print(f"   🏗️  Estrutura: CNPJ/012026/NFe/")
    
    print()

print("="*80)
print(f"💡 TOTAL DE PERFIS ATIVOS: {len(perfis)}")
print("="*80)
print()
print("🔄 FUNCIONAMENTO:")
print("   • Quando BUSCAR novos XMLs, eles serão salvos nos", len(perfis), "perfis automaticamente")
print("   • Para COPIAR XMLs existentes, use a interface 'Armazenamento' no programa")
print()

conn.close()
