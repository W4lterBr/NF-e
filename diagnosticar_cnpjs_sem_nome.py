# -*- coding: utf-8 -*-
"""
Diagnostica CNPJs sem nome de certificado cadastrado
"""
import sqlite3
from pathlib import Path
import os

# Caminhos
db_path = 'notas.db'

# Tenta múltiplas localizações
caminhos_possiveis = [
    Path('xmls'),
    Path('data/xmls'),
    Path(r'C:\Arquivo Walter - Empresas\Notas\xmls')
]

xmls_folder = None
for caminho in caminhos_possiveis:
    if caminho.exists():
        xmls_folder = caminho
        print(f"✅ Pasta encontrada: {xmls_folder}")
        break

if not xmls_folder:
    print(f"❌ Pasta xmls/ não encontrada em nenhum local!")
    exit(1)

print("="*80)
print("🔍 DIAGNÓSTICO: CNPJs SEM CERTIFICADO CADASTRADO")
print("="*80)
print()

# Carrega certificados do banco
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT informante, nome_certificado, razao_social
    FROM certificados
    ORDER BY informante
""")

certificados = cursor.fetchall()
conn.close()

# Cria mapeamento CNPJ -> Nome
mapeamento = {}
for cnpj, nome_cert, razao in certificados:
    if cnpj and nome_cert:
        mapeamento[cnpj] = nome_cert
    elif cnpj and razao:
        mapeamento[cnpj] = razao

print(f"📋 Certificados cadastrados no banco: {len(mapeamento)}")
print()
for cnpj, nome in sorted(mapeamento.items()):
    print(f"   ✅ {cnpj}: {nome}")
print()

print("="*80)
print("📁 Analisando pastas em xmls/...")
print("="*80)
print()

# Lista pastas em xmls/
pastas_cnpj = []
for item in xmls_folder.iterdir():
    if item.is_dir():
        # Normaliza CNPJ (remove caracteres especiais)
        nome_pasta = item.name
        cnpj_normalizado = ''.join(c for c in nome_pasta if c.isdigit())
        
        if cnpj_normalizado:  # Só se tiver dígitos
            # Conta XMLs dentro
            xml_count = len(list(item.rglob('*.xml')))
            
            pastas_cnpj.append({
                'pasta': nome_pasta,
                'cnpj': cnpj_normalizado,
                'caminho': str(item),
                'xml_count': xml_count
            })

print(f"📊 Total de pastas CNPJ encontradas: {len(pastas_cnpj)}")
print()

# Separa em categorias
cnpjs_incompletos = []
cnpjs_nao_cadastrados = []
cnpjs_ok = []

for pasta in pastas_cnpj:
    cnpj = pasta['cnpj']
    
    if len(cnpj) < 14:  # CNPJ incompleto
        cnpjs_incompletos.append(pasta)
    elif cnpj not in mapeamento:  # CNPJ não cadastrado
        cnpjs_nao_cadastrados.append(pasta)
    else:  # OK
        cnpjs_ok.append(pasta)

# Mostra resultados
print("="*80)
print("✅ RESULTADO DA ANÁLISE")
print("="*80)
print()

print(f"✅ CNPJs com certificado cadastrado: {len(cnpjs_ok)}")
if cnpjs_ok:
    for pasta in sorted(cnpjs_ok, key=lambda x: x['cnpj']):
        nome_cert = mapeamento[pasta['cnpj']]
        print(f"   {pasta['cnpj']}: {nome_cert} ({pasta['xml_count']} XMLs)")
print()

print(f"⚠️  CNPJs INCOMPLETOS (pastas antigas?): {len(cnpjs_incompletos)}")
if cnpjs_incompletos:
    for pasta in sorted(cnpjs_incompletos, key=lambda x: x['cnpj']):
        print(f"   ❌ {pasta['pasta']} ({len(pasta['cnpj'])} dígitos) - {pasta['xml_count']} XMLs")
        print(f"      Caminho: {pasta['caminho']}")
print()

print(f"⚠️  CNPJs NÃO CADASTRADOS: {len(cnpjs_nao_cadastrados)}")
if cnpjs_nao_cadastrados:
    for pasta in sorted(cnpjs_nao_cadastrados, key=lambda x: x['cnpj']):
        print(f"   ❌ {pasta['cnpj']} - {pasta['xml_count']} XMLs")
        print(f"      Pasta: {pasta['pasta']}")
        print(f"      Caminho: {pasta['caminho']}")
        
        # Tenta descobrir nome da empresa dentro dos XMLs
        try:
            primeiro_xml = next(Path(pasta['caminho']).rglob('*.xml'), None)
            if primeiro_xml:
                from lxml import etree
                tree = etree.parse(str(primeiro_xml))
                root = tree.getroot()
                
                # Tenta achar xNome
                ns = '{http://www.portalfiscal.inf.br/nfe}'
                xnome = root.findtext(f'.//{ns}xNome') or root.findtext('.//xNome')
                
                if xnome:
                    print(f"      💡 Nome encontrado nos XMLs: {xnome}")
        except:
            pass
        print()

print()
print("="*80)
print("💡 RECOMENDAÇÕES:")
print("="*80)
print()

if cnpjs_incompletos:
    print("1️⃣  CNPJs INCOMPLETOS:")
    print("   • Essas pastas têm nomes truncados (ex: '61' em vez de '61950325000120')")
    print("   • São restos de versões antigas do sistema")
    print("   • SOLUÇÃO: Renomear ou mover para outro local")
    print()

if cnpjs_nao_cadastrados:
    print("2️⃣  CNPJs NÃO CADASTRADOS:")
    print("   • Esses CNPJs têm XMLs mas não estão no banco de certificados")
    print("   • OPÇÕES:")
    print("      a) Cadastrar certificado no sistema (Menu → Certificados → Adicionar)")
    print("      b) Mover XMLs para pasta de outro certificado já cadastrado")
    print("      c) Ignorar (arquivos não serão copiados ao aplicar perfil)")
    print()

if cnpjs_ok:
    print("3️⃣  CNPJs OK:")
    print(f"   • {len(cnpjs_ok)} CNPJ(s) funcionando corretamente")
    print("   • Esses serão copiados normalmente ao aplicar perfil")
    print()

print()
print("="*80)
print("📝 PRÓXIMOS PASSOS:")
print("="*80)
print()
print("Para corrigir:")
print("1. Execute: python corrigir_pastas_cnpj.py")
print()
print("Para listar certificados cadastrados:")
print("2. Abra o programa → Menu → Certificados")
print()
print("="*80)
