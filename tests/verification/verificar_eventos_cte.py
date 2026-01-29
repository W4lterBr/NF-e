#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar eventos de CT-e nos XMLs baixados
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Chave do CT-e que estamos procurando
CHAVE_CTE = "50251203232675000154570010056290311009581385"

# Diretório base
BASE_DIR = Path(__file__).parent / "xmls" / "01773924000193"

print(f"🔍 Procurando eventos relacionados ao CT-e: {CHAVE_CTE}\n")

# Contador de eventos
eventos_encontrados = []
eventos_cte_total = 0
eventos_cte_cancelamento = 0

# Percorrer todas as pastas de eventos
for eventos_dir in BASE_DIR.rglob("Eventos"):
    if not eventos_dir.is_dir():
        continue
    
    print(f"📁 Analisando: {eventos_dir.relative_to(BASE_DIR)}")
    
    for xml_file in eventos_dir.glob("*.xml"):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Procurar por eventos de CT-e
            # Namespaces possíveis
            namespaces = {
                'ns': 'http://www.portalfiscal.inf.br/cte',
                'ns2': 'http://www.portalfiscal.inf.br/nfe'
            }
            
            # Tentar encontrar chave de CT-e
            ch_cte = None
            for ns_prefix in ['ns:', 'ns2:', '']:
                ch_cte = root.findtext(f'.//{ns_prefix}chCTe', namespaces=namespaces if ns_prefix else None)
                if ch_cte:
                    break
            
            if ch_cte:
                eventos_cte_total += 1
                
                # Encontrar tipo de evento
                tp_evento = None
                for ns_prefix in ['ns:', 'ns2:', '']:
                    tp_evento = root.findtext(f'.//{ns_prefix}tpEvento', namespaces=namespaces if ns_prefix else None)
                    if tp_evento:
                        break
                
                # Verificar se é cancelamento (110111)
                if tp_evento == '110111':
                    eventos_cte_cancelamento += 1
                
                # Se for o CT-e que procuramos
                if ch_cte == CHAVE_CTE:
                    eventos_encontrados.append({
                        'arquivo': xml_file.name,
                        'pasta': eventos_dir.relative_to(BASE_DIR),
                        'tp_evento': tp_evento or 'N/A',
                        'caminho_completo': xml_file
                    })
        
        except Exception as e:
            continue

print(f"\n📊 ESTATÍSTICAS:")
print(f"   Total de eventos de CT-e encontrados: {eventos_cte_total}")
print(f"   Eventos de cancelamento de CT-e (110111): {eventos_cte_cancelamento}")
print(f"\n{'='*80}")

if eventos_encontrados:
    print(f"\n✅ ENCONTRADOS {len(eventos_encontrados)} EVENTOS para o CT-e {CHAVE_CTE}:\n")
    
    for evento in eventos_encontrados:
        print(f"📄 {evento['arquivo']}")
        print(f"   📂 Pasta: {evento['pasta']}")
        print(f"   🏷️  Tipo: {evento['tp_evento']}")
        
        # Ler e mostrar detalhes
        try:
            with open(evento['caminho_completo'], 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ET.parse(evento['caminho_completo'])
            root = tree.getroot()
            
            # Extrair informações do evento
            c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
            x_motivo = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
            dh_evento = root.findtext('.//{http://www.portalfiscal.inf.br/cte}dhEvento')
            n_prot = root.findtext('.//{http://www.portalfiscal.inf.br/cte}nProt')
            
            if c_stat:
                print(f"   📋 Status: {c_stat} - {x_motivo or 'N/A'}")
            if dh_evento:
                print(f"   📅 Data: {dh_evento}")
            if n_prot:
                print(f"   🔢 Protocolo: {n_prot}")
            
            # Verificar se é cancelamento
            if evento['tp_evento'] == '110111':
                if c_stat == '135':
                    print(f"   ✅ CANCELAMENTO HOMOLOGADO!")
                else:
                    print(f"   ⚠️  Cancelamento com status diferente")
            
        except Exception as e:
            print(f"   ⚠️  Erro ao ler detalhes: {e}")
        
        print()
else:
    print(f"\n❌ NENHUM EVENTO encontrado para o CT-e {CHAVE_CTE}")
    print(f"\n🔍 Isso significa que:")
    print(f"   1. O evento de cancelamento nunca foi baixado via NSU")
    print(f"   2. Ou o CT-e não teve nenhum evento registrado na SEFAZ")
    print(f"\n💡 SOLUÇÃO:")
    print(f"   - Fazer nova busca NSU para baixar eventos pendentes")
    print(f"   - Verificar se o CT-e realmente foi cancelado")
    print(f"   - Consultar diretamente na SEFAZ")

print(f"\n{'='*80}")
