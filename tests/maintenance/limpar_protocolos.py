"""
Script para remover arquivos XML que contém apenas protocolos (sem dados das notas).
"""
from pathlib import Path
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).parent
XMLS_DIR = BASE_DIR / "xmls"

removidos = 0
mantidos = 0

print("Verificando XMLs salvos...")

for xml_file in XMLS_DIR.rglob("*.xml"):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        xml_str = ET.tostring(root, encoding='unicode').lower()
        
        # Detecta se é apenas protocolo
        is_only_protocol = (
            '<retconssit' in xml_str and 
            '<protnfe' in xml_str and
            '<nfeproc' not in xml_str and
            '<nfe' not in xml_str.replace('nferesultmsg', '').replace('protnfe', '')
        )
        
        # Ou se o arquivo tem nome genérico
        has_generic_name = 'SEM_NUMERO-SEM_NOME' in xml_file.name
        
        if is_only_protocol or has_generic_name:
            print(f"❌ Removendo: {xml_file.relative_to(XMLS_DIR)}")
            xml_file.unlink()
            removidos += 1
        else:
            mantidos += 1
            
    except Exception as e:
        print(f"⚠ Erro ao processar {xml_file.name}: {e}")
        continue

print(f"\n=== RESULTADO ===")
print(f"Removidos: {removidos}")
print(f"Mantidos: {mantidos}")
