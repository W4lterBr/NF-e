"""
Script para reorganizar TODOS os arquivos salvos em pastas sem data
Move de: CERT/CTe/, CERT/Eventos/, CERT/NFe/
Para: CERT/YYYY-MM/CTe/, CERT/YYYY-MM/NFe/Eventos/, CERT/YYYY-MM/NFe/
"""

import os
import sys
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

def extract_date_and_type(xml_path):
    """Extrai a data e tipo de documento de um XML"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Remove namespace
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # NFe completa
        if root_tag in ['nfeProc', 'NFe']:
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            ide = root.find('.//nfe:ide', ns)
            if ide is not None:
                dhEmi = ide.findtext('nfe:dhEmi', None, ns)
                dEmi = ide.findtext('nfe:dEmi', None, ns)
                data = dhEmi or dEmi
                if data:
                    return data.split('T')[0][:7], 'NFe'
        
        # CTe completo
        elif root_tag in ['cteProc', 'CTe']:
            ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
            ide = root.find('.//cte:ide', ns)
            if ide is not None:
                dhEmi = ide.findtext('cte:dhEmi', None, ns)
                dEmi = ide.findtext('cte:dEmi', None, ns)
                data = dhEmi or dEmi
                if data:
                    return data.split('T')[0][:7], 'CTe'
        
        # Evento (resEvento, procEventoNFe, infEvento)
        elif root_tag in ['resEvento', 'procEventoNFe', 'evento', 'infEvento']:
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Tenta extrair chave do XML
            chNFe = root.findtext('.//nfe:chNFe', None, ns)
            
            # Se não achou, tenta extrair do nome do arquivo (infEvento)
            if not chNFe or len(chNFe) != 44:
                nome = xml_path.stem  # Nome sem extensão
                if len(nome) == 44 and nome.isdigit():
                    chNFe = nome
            
            if chNFe and len(chNFe) >= 44:
                ano = "20" + chNFe[2:4]
                mes = chNFe[4:6]
                
                # Detecta se é evento de NFe ou CTe
                modelo = chNFe[20:22]
                if modelo == '57':
                    return f"{ano}-{mes}", 'CTe/Eventos'
                else:
                    return f"{ano}-{mes}", 'NFe/Eventos'
            
            # Tenta data do evento
            dhEvento = root.findtext('.//nfe:dhEvento', None, ns)
            if dhEvento:
                return dhEvento.split('T')[0][:7], 'NFe/Eventos'
        
        # Resumo
        elif root_tag == 'resNFe':
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            chNFe = root.findtext('nfe:chNFe', None, ns)
            if chNFe and len(chNFe) >= 44:
                ano = "20" + chNFe[2:4]
                mes = chNFe[4:6]
                return f"{ano}-{mes}", 'Resumos'
        
        return None, None
    except Exception as e:
        print(f"    ❌ Erro ao ler XML: {e}")
        return None, None

def main():
    print("=" * 80)
    print("REORGANIZAÇÃO COMPLETA - Correção de estrutura de pastas")
    print("=" * 80)
    
    # Pasta de armazenamento
    storage_path = Path("c:/Arquivo Walter - Empresas/Notas/NFs")
    if not storage_path.exists():
        print(f"❌ Pasta não encontrada: {storage_path}")
        return
    
    print(f"\n📂 Processando: {storage_path}\n")
    
    pastas_problematicas = ['CTe', 'Eventos', 'NFe']
    total_movidos = 0
    total_erros = 0
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
            print(f"   {len(xmls)} arquivo(s) para processar")
            print(f"{'='*80}")
            
            total_arquivos += len(xmls)
            
            for xml_file in xmls:
                try:
                    # Extrai data e tipo correto
                    ano_mes, tipo_correto = extract_date_and_type(xml_file)
                    
                    if not ano_mes or not tipo_correto:
                        print(f"   ⚠️ {xml_file.name}: Não foi possível extrair data")
                        total_erros += 1
                        continue
                    
                    # Define pasta destino correta
                    pasta_destino = cert_folder / ano_mes / tipo_correto
                    pasta_destino.mkdir(parents=True, exist_ok=True)
                    
                    # Move o arquivo
                    destino = pasta_destino / xml_file.name
                    
                    if destino.exists():
                        # Verifica se são idênticos
                        if xml_file.stat().st_size == destino.stat().st_size:
                            print(f"   🔄 {xml_file.name}: Duplicado (removendo)")
                            xml_file.unlink()
                        else:
                            print(f"   ⚠️ {xml_file.name}: Conflito (mantendo ambos)")
                            destino = pasta_destino / f"{xml_file.stem}_dup{xml_file.suffix}"
                            shutil.move(str(xml_file), str(destino))
                    else:
                        shutil.move(str(xml_file), str(destino))
                        print(f"   ✅ {xml_file.name} → {destino.relative_to(cert_folder)}")
                    
                    # Move PDF se existir
                    pdf_file = xml_file.with_suffix('.pdf')
                    if pdf_file.exists():
                        pdf_destino = destino.with_suffix('.pdf')
                        if not pdf_destino.exists():
                            shutil.move(str(pdf_file), str(pdf_destino))
                            print(f"      + PDF movido")
                        else:
                            pdf_file.unlink()  # Remove PDF duplicado
                    
                    total_movidos += 1
                    
                except Exception as e:
                    print(f"   ❌ Erro ao processar {xml_file.name}: {e}")
                    total_erros += 1
            
            # Remove pasta se estiver vazia
            try:
                if not any(pasta.iterdir()):
                    pasta.rmdir()
                    print(f"   🗑️ Pasta removida (vazia)")
            except:
                pass
    
    print("\n" + "=" * 80)
    print(f"✅ Reorganização concluída!")
    print(f"   📦 Total de arquivos: {total_arquivos}")
    print(f"   ✅ Movidos: {total_movidos}")
    if total_erros > 0:
        print(f"   ⚠️ Erros: {total_erros}")
    print("=" * 80)

if __name__ == "__main__":
    main()
