#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualizar status do CT-e processando evento existente ou indicando necessidade de busca
"""

import sqlite3
from pathlib import Path
from lxml import etree

CHAVE_CTE = '50251203232675000154570010056290311009581385'
INFORMANTE_CNPJ = '01773924000193'

def main():
    print("="*80)
    print("ATUALIZAR STATUS DO CT-e")
    print("="*80)
    print(f"Chave CT-e: {CHAVE_CTE}")
    print(f"Informante: {INFORMANTE_CNPJ}\n")
    
    # Verificar status atual
    conn = sqlite3.connect('notas.db')
    cursor = conn.execute(
        "SELECT numero, status FROM notas_detalhadas WHERE chave = ?",
        (CHAVE_CTE,)
    )
    row = cursor.fetchone()
    
    if row:
        print(f"📋 Status ATUAL no banco:")
        print(f"   Número: {row[0]}")
        print(f"   Status: {row[1]}\n")
    else:
        print("❌ CT-e não encontrado no banco\n")
        conn.close()
        return
    
    # Procurar XML do evento
    print("🔍 Procurando XML do evento de cancelamento...\n")
    
    xmls_dir = Path('xmls')
    xmls_found = []
    
    # Procurar em toda estrutura
    for xml_file in xmls_dir.rglob(f"*{CHAVE_CTE}*.xml"):
        # Pular debug
        if 'Debug' in str(xml_file):
            continue
        xmls_found.append(xml_file)
    
    print(f"📦 XMLs encontrados: {len(xmls_found)}\n")
    
    evento_encontrado = False
    
    for xml_file in xmls_found:
        try:
            # Ler XML
            xml_content = xml_file.read_bytes()
            root = etree.fromstring(xml_content)
            
            # Tag
            tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
            
            print(f"   📄 {xml_file.name}")
            print(f"      Tipo: {tag}")
            
            # Se for evento
            if tag in ['procEventoCTe', 'eventoCTe']:
                ns = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                
                ch_cte = root.findtext('.//cte:chCTe', namespaces=ns)
                tp_evento = root.findtext('.//cte:tpEvento', namespaces=ns)
                c_stat = root.findtext('.//cte:cStat', namespaces=ns)
                x_evento = root.findtext('.//cte:xEvento', namespaces=ns)
                
                print(f"      🎯 EVENTO DE CT-e!")
                print(f"         Tipo Evento: {tp_evento}")
                print(f"         Status: {c_stat}")
                print(f"         Descrição: {x_evento}")
                
                if ch_cte == CHAVE_CTE and tp_evento == '110111' and c_stat == '135':
                    print(f"\n      🚫 CANCELAMENTO DETECTADO!")
                    evento_encontrado = True
                    
                    # Atualizar banco
                    novo_status = "Cancelamento de CT-e homologado"
                    cursor = conn.execute(
                        "UPDATE notas_detalhadas SET status = ? WHERE chave = ?",
                        (novo_status, CHAVE_CTE)
                    )
                    conn.commit()
                    
                    print(f"      ✅ Status atualizado para: {novo_status}")
                    break
            
        except Exception as e:
            print(f"      ⚠️ Erro ao processar: {e}")
    
    print(f"\n{'='*80}")
    
    if evento_encontrado:
        # Verificar status final
        cursor = conn.execute(
            "SELECT status FROM notas_detalhadas WHERE chave = ?",
            (CHAVE_CTE,)
        )
        row = cursor.fetchone()
        
        if row:
            print(f"\n✅ SUCESSO!")
            print(f"   Status FINAL no banco: {row[0]}")
    else:
        print(f"\n❌ EVENTO DE CANCELAMENTO NÃO ENCONTRADO")
        print(f"\n📝 AÇÕES NECESSÁRIAS:")
        print(f"   1. Execute uma busca na SEFAZ pelo informante {INFORMANTE_CNPJ}")
        print(f"   2. O sistema irá baixar o evento de cancelamento via distribuição")
        print(f"   3. Com o código corrigido (linhas 2095-2115), o evento será")
        print(f"      processado automaticamente e o status será atualizado")
        print(f"\n   Alternativamente, você pode:")
        print(f"   - Usar a interface do sistema")
        print(f"   - Clicar em 'Buscar na SEFAZ'")
        print(f"   - Selecionar o certificado do informante {INFORMANTE_CNPJ}")
    
    print("="*80)
    conn.close()

if __name__ == "__main__":
    main()
