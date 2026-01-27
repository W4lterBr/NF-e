"""
Script para diagnosticar XMLs salvos em pastas sem data (CTe, Eventos, NFe)
"""

import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

def extract_date_from_xml(xml_path):
    """Extrai a data de um XML"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Remove namespace
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # NFe
        if root_tag in ['nfeProc', 'NFe']:
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            ide = root.find('.//nfe:ide', ns)
            if ide is not None:
                dhEmi = ide.findtext('nfe:dhEmi', None, ns)
                dEmi = ide.findtext('nfe:dEmi', None, ns)
                data = dhEmi or dEmi
                if data:
                    return data.split('T')[0][:7], root_tag
        
        # CTe
        elif root_tag in ['cteProc', 'CTe']:
            ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
            ide = root.find('.//cte:ide', ns)
            if ide is not None:
                dhEmi = ide.findtext('cte:dhEmi', None, ns)
                dEmi = ide.findtext('cte:dEmi', None, ns)
                data = dhEmi or dEmi
                if data:
                    return data.split('T')[0][:7], root_tag
        
        # Evento
        elif root_tag in ['resEvento', 'procEventoNFe', 'evento']:
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            chNFe = root.findtext('.//nfe:chNFe', None, ns)
            if chNFe and len(chNFe) >= 44:
                ano = "20" + chNFe[2:4]
                mes = chNFe[4:6]
                return f"{ano}-{mes}", root_tag
            
            dhEvento = root.findtext('.//nfe:dhEvento', None, ns)
            if dhEvento:
                return dhEvento.split('T')[0][:7], root_tag
        
        # Resumo
        elif root_tag == 'resNFe':
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            chNFe = root.findtext('nfe:chNFe', None, ns)
            if chNFe and len(chNFe) >= 44:
                ano = "20" + chNFe[2:4]
                mes = chNFe[4:6]
                return f"{ano}-{mes}", root_tag
        
        return None, root_tag
    except Exception as e:
        return None, f"ERRO: {e}"

def main():
    print("=" * 80)
    print("DIAGNÓSTICO - Pastas sem estrutura de data")
    print("=" * 80)
    
    # Pasta de armazenamento
    storage_path = Path("c:/Arquivo Walter - Empresas/Notas/NFs")
    if not storage_path.exists():
        print(f"❌ Pasta não encontrada: {storage_path}")
        return
    
    print(f"\n📂 Verificando: {storage_path}\n")
    
    pastas_problematicas = ['CTe', 'Eventos', 'NFe']
    total_arquivos = 0
    
    for cert_folder in storage_path.iterdir():
        if not cert_folder.is_dir():
            continue
        
        for pasta_prob in pastas_problematicas:
            pasta = cert_folder / pasta_prob
            if not pasta.exists():
                continue
            
            xmls = list(pasta.glob("*.xml"))
            if not xmls:
                continue
            
            print(f"\n{'='*80}")
            print(f"📁 {pasta.relative_to(storage_path)}")
            print(f"   {len(xmls)} arquivo(s)")
            print(f"{'='*80}")
            
            for xml_file in xmls[:5]:  # Mostra apenas os 5 primeiros
                data_correta, tipo_doc = extract_date_from_xml(xml_file)
                print(f"   📄 {xml_file.name}")
                print(f"      Tipo: {tipo_doc}")
                print(f"      Data extraída: {data_correta or 'NÃO ENCONTRADA'}")
                if data_correta:
                    print(f"      ✅ Deveria estar em: {cert_folder.name}/{data_correta}/{pasta_prob}/")
                else:
                    print(f"      ⚠️ Não foi possível extrair data do XML")
                print()
            
            if len(xmls) > 5:
                print(f"   ... e mais {len(xmls) - 5} arquivo(s)\n")
            
            total_arquivos += len(xmls)
    
    print("\n" + "=" * 80)
    print(f"Total de arquivos em pastas incorretas: {total_arquivos}")
    print("=" * 80)

if __name__ == "__main__":
    main()
