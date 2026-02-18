# -*- coding: utf-8 -*-
"""
Verifica se há outros perfis excluídos e restaura se necessário
"""
import sqlite3

db_path = 'notas.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("🔍 VERIFICAÇÃO COMPLETA DE PERFIS")
print("="*80)
print()

# Busca TODOS os perfis (incluindo inativos)
cursor.execute("""
    SELECT 
        id,
        nome,
        pasta_base,
        ativo
    FROM perfis_armazenamento
    ORDER BY id
""")

perfis = cursor.fetchall()

print(f"📊 Total de perfis no banco: {len(perfis)}")
print()

ativos = []
inativos = []

for pid, nome, pasta, ativo in perfis:
    if ativo:
        ativos.append((pid, nome, pasta))
        print(f"✅ PERFIL #{pid}: {nome}")
    else:
        inativos.append((pid, nome, pasta))
        print(f"❌ PERFIL #{pid}: {nome}")
    
    print(f"   Pasta: {pasta}")
    print(f"   Status: {'Ativo' if ativo else 'Inativo'}")
    print()

print("="*80)
print(f"📊 RESUMO:")
print(f"   ✅ Ativos: {len(ativos)}")
print(f"   ❌ Inativos: {len(inativos)}")
print("="*80)
print()

# Se o usuário quer ter 2 perfis (NFs + DominioWeb)
if len(ativos) == 1 and 'DominioWeb' in ativos[0][2]:
    print("⚠️  ATENÇÃO:")
    print("   Você tem apenas o perfil DominioWeb ativo")
    print()
    print("💡 Opções:")
    print()
    print("1️⃣  MANTER apenas DominioWeb")
    print("   • Todos os XMLs vão para DominioWeb")
    print("   • Estrutura: DominioWeb/CERTIFICADO/MÊS/TIPO/")
    print()
    print("2️⃣  CRIAR perfil adicional NFs")
    print("   • XMLs salvos em 2 locais (DominioWeb + NFs)")
    print("   • Cada um com sua estrutura")
    print()
    
    if inativos:
        print("3️⃣  REATIVAR perfil inativo existente")
        for pid, nome, pasta in inativos:
            print(f"   • Perfil #{pid}: {nome} ({pasta})")
        print()
    
    print("4️⃣  CANCELAR (não fazer nada)")
    print()
    print("="*80)
    
    escolha = input("Digite sua escolha (1-4): ").strip()
    
    if escolha == '1':
        print()
        print("✅ Mantendo apenas DominioWeb ativo")
        print("   Todos os XMLs serão salvos em:")
        print("   C:\\Arquivo Walter - Empresas\\Notas\\DominioWeb")
        print()
        print("   Estrutura: CERTIFICADO/MÊS/TIPO/")
    
    elif escolha == '2':
        print()
        print("🆕 CRIANDO NOVO PERFIL NFs...")
        
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
        
        print("✅ Perfil NFs criado!")
        print("   Pasta: C:\\Arquivo Walter - Empresas\\Notas\\NFs")
        print("   Organização: CERTIFICADO_TIPO")
        print("   XML/PDF: Separados")
        print()
        print("💡 Agora os XMLs serão salvos em AMBOS os locais:")
        print("   1. DominioWeb (padrão)")
        print("   2. NFs")
    
    elif escolha == '3' and inativos:
        print()
        print("📋 Perfis inativos:")
        for i, (pid, nome, pasta) in enumerate(inativos, 1):
            print(f"   {i}. Perfil #{pid}: {nome}")
        
        print()
        perfil_escolhido = input("Digite o número do perfil para reativar: ").strip()
        
        try:
            idx = int(perfil_escolhido) - 1
            if 0 <= idx < len(inativos):
                pid_reativar = inativos[idx][0]
                
                cursor.execute("""
                    UPDATE perfis_armazenamento
                    SET ativo = 1
                    WHERE id = ?
                """, (pid_reativar,))
                
                conn.commit()
                
                print(f"✅ Perfil #{pid_reativar} reativado!")
            else:
                print("❌ Opção inválida")
        except:
            print("❌ Opção inválida")
    
    else:
        print()
        print("ℹ️  Mantido como está")

else:
    print("✅ Configuração atual está OK")
    print()
    if len(ativos) > 1:
        print(f"   {len(ativos)} perfis ativos (salvamento em múltiplos locais)")

print()
print("="*80)

conn.close()
