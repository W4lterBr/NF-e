"""
Diagnóstico de inconsistências entre XMLs no disco e status no banco
"""
import sqlite3
import os
from pathlib import Path

db_path = 'notas.db'
conn = sqlite3.connect(db_path)

print("=" * 80)
print("DIAGNÓSTICO: Status XML vs Arquivos no Disco")
print("=" * 80)

# 1. Notas marcadas como COMPLETO mas sem registro em xmls_baixados
print("\n1️⃣ COMPLETO mas NÃO REGISTRADO em xmls_baixados:")
print("-" * 80)
cursor = conn.execute('''
    SELECT nd.chave, nd.cnpj_emitente, nd.nome_emitente
    FROM notas_detalhadas nd
    LEFT JOIN xmls_baixados xb ON nd.chave = xb.chave
    WHERE nd.xml_status = 'COMPLETO' AND xb.chave IS NULL
    LIMIT 10
''')
rows = cursor.fetchall()
if rows:
    for chave, cnpj, razao in rows:
        print(f"  {chave[:25]}... | {cnpj} | {razao}")
else:
    print("  ✅ Nenhum problema encontrado")

# 2. Notas marcadas como COMPLETO mas sem caminho_arquivo
print("\n2️⃣ COMPLETO mas SEM CAMINHO em xmls_baixados:")
print("-" * 80)
cursor = conn.execute('''
    SELECT nd.chave, nd.cnpj_emitente, xb.caminho_arquivo
    FROM notas_detalhadas nd
    INNER JOIN xmls_baixados xb ON nd.chave = xb.chave
    WHERE nd.xml_status = 'COMPLETO' AND (xb.caminho_arquivo IS NULL OR xb.caminho_arquivo = '')
    LIMIT 10
''')
rows = cursor.fetchall()
if rows:
    for chave, cnpj, caminho in rows:
        print(f"  {chave[:25]}... | {cnpj} | caminho={caminho}")
else:
    print("  ✅ Nenhum problema encontrado")

# 3. XMLs fisicamente no disco mas marcados como RESUMO
print("\n3️⃣ Arquivos XML existem no disco mas marcados como RESUMO:")
print("-" * 80)
cursor = conn.execute('''
    SELECT nd.chave, nd.cnpj_emitente, xb.caminho_arquivo
    FROM notas_detalhadas nd
    INNER JOIN xmls_baixados xb ON nd.chave = xb.chave
    WHERE nd.xml_status = 'RESUMO' 
      AND xb.caminho_arquivo IS NOT NULL 
      AND xb.caminho_arquivo != ''
    LIMIT 20
''')
rows = cursor.fetchall()
resumo_com_xml = []
for chave, cnpj, caminho in rows:
    if caminho and os.path.exists(caminho):
        resumo_com_xml.append((chave, cnpj, caminho))
        print(f"  {chave[:25]}... | {cnpj}")
        print(f"     📁 {caminho}")

if not resumo_com_xml:
    print("  ✅ Nenhum problema encontrado")

# 4. Estatísticas gerais
print("\n4️⃣ ESTATÍSTICAS GERAIS:")
print("-" * 80)

cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'COMPLETO'")
completo_count = cursor.fetchone()[0]
print(f"  Total COMPLETO no banco: {completo_count}")

cursor = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status = 'RESUMO'")
resumo_count = cursor.fetchone()[0]
print(f"  Total RESUMO no banco: {resumo_count}")

cursor = conn.execute("SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL")
xml_registrado = cursor.fetchone()[0]
print(f"  Total registrado em xmls_baixados: {xml_registrado}")

# Contar XMLs físicos no disco
xml_dirs = ['xmls', 'xml_NFs', 'xmls_chave']
total_xmls_disco = 0
for xml_dir in xml_dirs:
    if os.path.exists(xml_dir):
        for root, dirs, files in os.walk(xml_dir):
            total_xmls_disco += len([f for f in files if f.endswith('.xml')])
print(f"  Total XMLs físicos no disco: {total_xmls_disco}")

# 5. TESTE: Buscar uma chave com XML que realmente existe
print("\n5️⃣ CHAVES PARA TESTAR (têm XML no disco):")
print("-" * 80)
if resumo_com_xml:
    print("  🎯 Use uma destas chaves para testar a busca:")
    for i, (chave, cnpj, caminho) in enumerate(resumo_com_xml[:3], 1):
        print(f"  {i}. {chave}")
        print(f"     Status atual: RESUMO")
        print(f"     Arquivo existe: ✅ {caminho}")
        print()
else:
    # Buscar qualquer XML no disco
    print("  🔍 Buscando XMLs no disco...")
    for xml_dir in ['xmls', 'xml_NFs', 'xmls_chave']:
        if os.path.exists(xml_dir):
            for root, dirs, files in os.walk(xml_dir):
                xml_files = [f for f in files if f.endswith('.xml')][:3]
                for xml_file in xml_files:
                    chave_from_file = xml_file.replace('.xml', '').replace('-procNFe', '')
                    if len(chave_from_file) == 44:
                        print(f"  📄 {chave_from_file}")
                        print(f"     📁 {os.path.join(root, xml_file)}")
                        print()
                if xml_files:
                    break
            if xml_files:
                break

conn.close()
print("=" * 80)
