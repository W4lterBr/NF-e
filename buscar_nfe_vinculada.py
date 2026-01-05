#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para encontrar NF-e vinculada ao CT-e e procurar eventos de cancelamento
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Chave do CT-e
CHAVE_CTE = "50251203232675000154570010056290311009581385"
XML_CTE = "xmls/01773924000193/2025-12/CTe/50251203232675000154570010056290311009581385.xml"

print(f"🔍 Analisando CT-e: {CHAVE_CTE}\n")

# Parsear o XML do CT-e
try:
    tree = ET.parse(XML_CTE)
    root = tree.getroot()
    
    ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
    
    # Procurar chaves de NF-e vinculadas
    nfe_keys = []
    
    # Procurar em infDoc -> infNFe
    for inf_doc in root.findall('.//{http://www.portalfiscal.inf.br/cte}infDoc'):
        for inf_nfe in inf_doc.findall('.//{http://www.portalfiscal.inf.br/cte}infNFe'):
            chave = inf_nfe.findtext('{http://www.portalfiscal.inf.br/cte}chave')
            if chave:
                nfe_keys.append(chave)
    
    print(f"📦 NF-e(s) vinculada(s) ao CT-e:")
    if nfe_keys:
        for key in nfe_keys:
            print(f"   ✅ {key}")
    else:
        print(f"   ❌ Nenhuma chave de NF-e encontrada no CT-e")
        print(f"\n🔍 Procurando outros campos de documentos...")
        
        # Procurar em outras estruturas possíveis
        for elem in root.iter():
            if 'chave' in elem.tag.lower() or 'chnfe' in elem.tag.lower():
                if elem.text and len(elem.text) == 44:
                    print(f"      Encontrado: {elem.tag} = {elem.text}")
                    nfe_keys.append(elem.text)
    
    print(f"\n{'='*80}\n")
    
    # Para cada NF-e encontrada, procurar eventos que mencionem o CT-e
    if nfe_keys:
        for nfe_key in nfe_keys:
            print(f"🔍 Procurando eventos da NF-e {nfe_key} que mencionem o CT-e...\n")
            
            # Procurar arquivos de eventos
            base_dir = Path("xmls/01773924000193")
            eventos_encontrados = []
            
            for eventos_dir in base_dir.rglob("Eventos"):
                for xml_file in eventos_dir.glob("*.xml"):
                    try:
                        with open(xml_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Verificar se menciona a NF-e E o CT-e
                        if nfe_key in content or CHAVE_CTE in content:
                            event_tree = ET.parse(xml_file)
                            event_root = event_tree.getroot()
                            
                            # Verificar se é evento de CT-e
                            tp_evento = event_root.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
                            if not tp_evento:
                                tp_evento = event_root.findtext('.//{http://www.portalfiscal.inf.br/nfe}tpEvento')
                            
                            if tp_evento:
                                eventos_encontrados.append({
                                    'arquivo': xml_file.name,
                                    'caminho': xml_file,
                                    'tipo': tp_evento
                                })
                    
                    except Exception as e:
                        continue
            
            if eventos_encontrados:
                print(f"✅ ENCONTRADOS {len(eventos_encontrados)} EVENTOS relacionados:\n")
                for evt in eventos_encontrados:
                    print(f"📄 {evt['arquivo']}")
                    print(f"   🏷️  Tipo de evento: {evt['tipo']}")
                    
                    # Ler detalhes
                    try:
                        evt_tree = ET.parse(evt['caminho'])
                        evt_root = evt_tree.getroot()
                        
                        # Procurar detalhes do evento
                        c_stat = evt_root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                        x_motivo = evt_root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
                        ch_cte = evt_root.findtext('.//{http://www.portalfiscal.inf.br/cte}chCTe')
                        
                        if not c_stat:
                            c_stat = evt_root.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat')
                        if not x_motivo:
                            x_motivo = evt_root.findtext('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
                        
                        if c_stat:
                            print(f"   📋 Status: {c_stat} - {x_motivo or 'N/A'}")
                        if ch_cte:
                            print(f"   🚛 CT-e: {ch_cte}")
                        
                        # Verificar se é cancelamento de CT-e
                        if evt['tipo'] == '110111' and c_stat == '135':
                            print(f"   🎯 ⚠️  ESTE É O EVENTO DE CANCELAMENTO DO CT-e!")
                    
                    except Exception as e:
                        pass
                    
                    print()
            else:
                print(f"❌ Nenhum evento encontrado para esta NF-e\n")

except FileNotFoundError:
    print(f"❌ Arquivo do CT-e não encontrado: {XML_CTE}")
except Exception as e:
    print(f"❌ Erro ao processar: {e}")
    import traceback
    traceback.print_exc()
