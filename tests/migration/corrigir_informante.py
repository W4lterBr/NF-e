"""
Script para corrigir o campo 'informante' vazio nas notas_detalhadas.
Analisa os XMLs salvos para descobrir qual certificado baixou cada nota.
"""
import sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).parent
XMLS_DIR = BASE_DIR / "xmls"

conn = sqlite3.connect('notas.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Busca notas com informante vazio
notas_vazias = cursor.execute(
    "SELECT chave FROM notas_detalhadas WHERE informante IS NULL OR informante = ''"
).fetchall()

print(f"Encontradas {len(notas_vazias)} notas com informante vazio")

atualizado = 0
nao_encontrado = 0

# Mapa de chaves para certificados
chave_to_cert = {}

# Primeiro, indexa todos os XMLs
print("Indexando XMLs...")
for cert_dir in XMLS_DIR.iterdir():
    if not cert_dir.is_dir():
        continue
    
    cnpj_certificado = cert_dir.name
    xml_count = 0
    
    # Procura em todas as pastas do certificado
    for xml_file in cert_dir.rglob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Remove namespace
            xml_str = ET.tostring(root, encoding='unicode')
            
            # Procura pela tag chNFe ou infNFe Id
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]
                
                # Chave pode estar em vários lugares
                if tag == 'chNFe' or tag == 'chCTe':
                    chave = elem.text
                    if chave and len(chave) == 44:
                        chave_to_cert[chave] = cnpj_certificado
                        xml_count += 1
                        break
                elif tag == 'infNFe' or tag == 'infCTe':
                    id_attr = elem.get('Id', '')
                    if id_attr.startswith('NFe') or id_attr.startswith('CTe'):
                        chave = id_attr[3:]  # Remove prefixo
                        if len(chave) == 44:
                            chave_to_cert[chave] = cnpj_certificado
                            xml_count += 1
                            break
        except Exception as e:
            continue
    
    if xml_count > 0:
        print(f"  {cnpj_certificado}: {xml_count} XMLs")

print(f"\nTotal de chaves indexadas: {len(chave_to_cert)}")
print("\nAtualizando banco de dados...")

# Agora atualiza as notas
for nota in notas_vazias:
    chave = nota['chave']
    
    if chave in chave_to_cert:
        cnpj = chave_to_cert[chave]
        cursor.execute(
            "UPDATE notas_detalhadas SET informante = ? WHERE chave = ?",
            (cnpj, chave)
        )
        atualizado += 1
        print(f"✓ {chave[:10]}... → {cnpj}")
    else:
        nao_encontrado += 1

conn.commit()
conn.close()

print(f"\n=== RESULTADO ===")
print(f"Atualizados: {atualizado}")
print(f"Não encontrados: {nao_encontrado}")
print(f"\nReinicie a interface para ver as mudanças!")
