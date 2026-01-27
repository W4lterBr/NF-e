"""
Analisa os arquivos salvos recentemente para identificar problemas de estrutura
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

def analisar_estrutura(pasta_storage):
    """Analisa a estrutura de pastas e identifica problemas"""
    
    print("=" * 80)
    print("ANÁLISE DE SALVAMENTO RECENTE")
    print("=" * 80)
    print(f"\n📂 Pasta: {pasta_storage}\n")
    
    # Busca arquivos modificados nas últimas 24 horas
    agora = datetime.now()
    limite = agora - timedelta(hours=24)
    
    arquivos_recentes = []
    pastas_problematicas = ['CTe', 'NFe', 'Eventos', 'Resumos']
    
    # Procura em todos os certificados
    for cert_folder in Path(pasta_storage).iterdir():
        if not cert_folder.is_dir():
            continue
        
        print(f"🔍 Verificando certificado: {cert_folder.name}")
        
        # Verifica pastas problemáticas (sem data)
        for pasta_prob in pastas_problematicas:
            pasta = cert_folder / pasta_prob
            if pasta.exists():
                xmls = list(pasta.glob("*.xml"))
                if xmls:
                    print(f"   ⚠️ PROBLEMA: Pasta {pasta_prob}/ contém {len(xmls)} arquivo(s)")
                    for xml in xmls[:3]:
                        mod_time = datetime.fromtimestamp(xml.stat().st_mtime)
                        if mod_time > limite:
                            print(f"      🕐 {xml.name} (modificado há {(agora - mod_time).seconds // 60} min)")
                            arquivos_recentes.append((xml, pasta_prob, cert_folder.name))
        
        # Verifica estrutura correta (com data)
        for ano_mes_folder in cert_folder.glob("20*"):
            if not ano_mes_folder.is_dir():
                continue
            
            # Verifica todas as subpastas dentro da data
            for tipo_folder in ano_mes_folder.iterdir():
                if not tipo_folder.is_dir():
                    continue
                
                xmls = list(tipo_folder.rglob("*.xml"))
                for xml in xmls:
                    mod_time = datetime.fromtimestamp(xml.stat().st_mtime)
                    if mod_time > limite:
                        rel_path = xml.relative_to(cert_folder)
                        print(f"   ✅ OK: {rel_path} (modificado há {(agora - mod_time).seconds // 60} min)")
    
    # Análise detalhada dos arquivos problemáticos
    if arquivos_recentes:
        print(f"\n{'=' * 80}")
        print(f"ANÁLISE DETALHADA DOS {len(arquivos_recentes)} ARQUIVO(S) PROBLEMÁTICO(S)")
        print(f"{'=' * 80}\n")
        
        for xml_path, pasta_tipo, cert_nome in arquivos_recentes:
            print(f"📄 {xml_path.name}")
            print(f"   Certificado: {cert_nome}")
            print(f"   Pasta atual: {pasta_tipo}/")
            
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
                
                print(f"   Tag raiz XML: {root_tag}")
                
                # Tenta extrair chave e data
                if root_tag in ['nfeProc', 'NFe']:
                    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                    ide = root.find('.//nfe:ide', ns)
                    if ide is not None:
                        dhEmi = ide.findtext('nfe:dhEmi', None, ns)
                        dEmi = ide.findtext('nfe:dEmi', None, ns)
                        data = (dhEmi or dEmi or '').split('T')[0][:7]
                        print(f"   Data extraída: {data or 'NÃO ENCONTRADA'}")
                        if data:
                            print(f"   ✅ Deveria estar em: {cert_nome}/{data}/NFe/")
                
                elif root_tag in ['cteProc', 'CTe']:
                    ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                    ide = root.find('.//cte:ide', ns)
                    if ide is not None:
                        dhEmi = ide.findtext('cte:dhEmi', None, ns)
                        dEmi = ide.findtext('cte:dEmi', None, ns)
                        data = (dhEmi or dEmi or '').split('T')[0][:7]
                        print(f"   Data extraída: {data or 'NÃO ENCONTRADA'}")
                        if data:
                            print(f"   ✅ Deveria estar em: {cert_nome}/{data}/CTe/")
                
                elif root_tag in ['resEvento', 'procEventoNFe', 'infEvento', 'evento']:
                    # Tenta extrair chave
                    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                    chNFe = root.findtext('.//nfe:chNFe', None, ns)
                    
                    # Fallback: chave no nome do arquivo
                    if not chNFe and len(xml_path.stem) == 44:
                        chNFe = xml_path.stem
                    
                    if chNFe and len(chNFe) >= 44:
                        ano = "20" + chNFe[2:4]
                        mes = chNFe[4:6]
                        modelo = chNFe[20:22]
                        
                        if modelo == '57':
                            tipo_correto = f"{ano}-{mes}/CTe/Eventos/"
                        else:
                            tipo_correto = f"{ano}-{mes}/NFe/Eventos/"
                        
                        print(f"   Chave: {chNFe[:10]}...")
                        print(f"   Data da chave: {ano}-{mes}")
                        print(f"   Modelo: {'CTe' if modelo == '57' else 'NFe'}")
                        print(f"   ✅ Deveria estar em: {cert_nome}/{tipo_correto}")
                    else:
                        print(f"   ⚠️ Chave não encontrada no XML ou nome do arquivo")
                
                print()
                
            except Exception as e:
                print(f"   ❌ Erro ao analisar: {e}\n")
    else:
        print(f"\n✅ Nenhum arquivo problemático encontrado nas últimas 24 horas!")
    
    print("=" * 80)

if __name__ == "__main__":
    pasta = r"C:\Arquivo Walter - Empresas\Notas\NFs"
    analisar_estrutura(pasta)
