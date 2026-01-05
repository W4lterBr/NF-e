#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para procurar eventos de CT-e nas pastas de eventos das NF-es vinculadas
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Chaves
CHAVE_CTE = "50251203232675000154570010056290311009581385"
NFE_KEYS = [
    "50251201773924000193550010000172491401236837",
    "50251201773924000193550010000172511797679216"
]

print(f"🔍 Procurando eventos relacionados ao CT-e nas NF-es...\n")
print(f"CT-e: {CHAVE_CTE}")
print(f"NF-e 1: {NFE_KEYS[0]}")
print(f"NF-e 2: {NFE_KEYS[1]}")
print(f"\n{'='*80}\n")

# Diretório base
base_dir = Path("xmls/01773924000193")

# Procurar em TODOS os arquivos de eventos
eventos_total = 0
eventos_cte_relacionados = []

for eventos_dir in base_dir.rglob("Eventos"):
    for xml_file in eventos_dir.glob("*.xml"):
        eventos_total += 1
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Converter XML para string para busca rápida
            xml_str = ET.tostring(root, encoding='unicode')
            
            # Verificar se menciona o CT-e ou alguma das NF-es
            menciona_cte = CHAVE_CTE in xml_str
            menciona_nfe1 = NFE_KEYS[0] in xml_str
            menciona_nfe2 = NFE_KEYS[1] in xml_str
            
            if menciona_cte or menciona_nfe1 or menciona_nfe2:
                # Extrair informações do evento
                tp_evento = None
                c_stat = None
                x_motivo = None
                ch_nfe = None
                ch_cte_evt = None
                
                # Tentar múltiplos namespaces
                for ns_uri in ['http://www.portalfiscal.inf.br/cte', 
                               'http://www.portalfiscal.inf.br/nfe',
                               '']:
                    ns = {f'ns': ns_uri} if ns_uri else {}
                    prefix = 'ns:' if ns_uri else ''
                    
                    if not tp_evento:
                        tp_evento = root.findtext(f'.//{{{ns_uri}}}tpEvento' if ns_uri else './/tpEvento')
                    if not c_stat:
                        c_stat = root.findtext(f'.//{{{ns_uri}}}cStat' if ns_uri else './/cStat')
                    if not x_motivo:
                        x_motivo = root.findtext(f'.//{{{ns_uri}}}xMotivo' if ns_uri else './/xMotivo')
                    if not ch_nfe:
                        ch_nfe = root.findtext(f'.//{{{ns_uri}}}chNFe' if ns_uri else './/chNFe')
                    if not ch_cte_evt:
                        ch_cte_evt = root.findtext(f'.//{{{ns_uri}}}chCTe' if ns_uri else './/chCTe')
                
                eventos_cte_relacionados.append({
                    'arquivo': xml_file.name,
                    'caminho': xml_file,
                    'pasta': eventos_dir.relative_to(base_dir),
                    'tp_evento': tp_evento or 'N/A',
                    'c_stat': c_stat or 'N/A',
                    'x_motivo': x_motivo or 'N/A',
                    'ch_nfe': ch_nfe or 'N/A',
                    'ch_cte': ch_cte_evt or 'N/A',
                    'menciona_cte': menciona_cte,
                    'menciona_nfe1': menciona_nfe1,
                    'menciona_nfe2': menciona_nfe2
                })
        
        except Exception as e:
            continue

print(f"📊 Total de eventos analisados: {eventos_total}")
print(f"📊 Eventos relacionados encontrados: {len(eventos_cte_relacionados)}\n")
print(f"{'='*80}\n")

if eventos_cte_relacionados:
    print(f"✅ ENCONTRADOS {len(eventos_cte_relacionados)} EVENTOS RELACIONADOS:\n")
    
    for evt in eventos_cte_relacionados:
        print(f"📄 {evt['arquivo']}")
        print(f"   📂 Pasta: {evt['pasta']}")
        print(f"   🏷️  Tipo: {evt['tp_evento']}")
        print(f"   📋 Status: {evt['c_stat']} - {evt['x_motivo']}")
        
        if evt['ch_nfe'] != 'N/A':
            print(f"   📦 NF-e: {evt['ch_nfe']}")
        if evt['ch_cte'] != 'N/A':
            print(f"   🚛 CT-e: {evt['ch_cte']}")
        
        if evt['menciona_cte']:
            print(f"   🎯 ⚠️  MENCIONA O CT-e DIRETAMENTE!")
        if evt['menciona_nfe1']:
            print(f"   🎯 Menciona NF-e 1 (vinculada)")
        if evt['menciona_nfe2']:
            print(f"   🎯 Menciona NF-e 2 (vinculada)")
        
        # Verificar se é cancelamento de CT-e
        if evt['tp_evento'] == '110111':
            if evt['c_stat'] == '135':
                print(f"   🔥🔥🔥 ESTE É O CANCELAMENTO DO CT-e HOMOLOGADO! 🔥🔥🔥")
            else:
                print(f"   ⚠️  Evento de cancelamento de CT-e com status {evt['c_stat']}")
        
        print()
else:
    print(f"❌ NENHUM evento relacionado encontrado")
    print(f"\n💡 Isso confirma que:")
    print(f"   1. O evento de cancelamento do CT-e NÃO foi baixado")
    print(f"   2. Nem como evento do CT-e, nem das NF-es vinculadas")
    print(f"   3. É necessário fazer nova busca NSU para baixar eventos pendentes")
