#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta direta de CT-e pela chave
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from modules.database import DatabaseManager
from nfe_search import NFeService
import xml.etree.ElementTree as ET

# Chave do CT-e
CHAVE_CTE = "50251203232675000154570010056290311009581385"

print(f"🔍 Consultando CT-e: {CHAVE_CTE}\n")
print(f"{'='*80}\n")

# Conectar ao banco para pegar certificados
db = DatabaseManager('notas.db')

# Pegar todos os certificados
certificados = db.load_certificates()

if not certificados:
    print("❌ Nenhum certificado encontrado no banco")
    sys.exit(1)

print(f"📋 Certificados disponíveis: {len(certificados)}\n")

# UF do CT-e (posição 0-1 da chave)
uf_cte = CHAVE_CTE[0:2]
print(f"📍 UF do CT-e: {uf_cte} (MS - Mato Grosso do Sul)\n")

# Tentar com cada certificado
for idx, cert in enumerate(certificados, 1):
    cnpj = cert['cnpj_cpf']
    path = cert['caminho']
    senha = cert['senha']
    informante = cert['informante']
    cuf = cert.get('uf', uf_cte)
    
    print(f"🔑 Tentativa {idx}/{len(certificados)}: {informante} ({cnpj})")
    
    try:
        # Criar serviço NFE
        svc = NFeService(path, senha, cnpj, cuf)
        
        # Tentar consultar
        resp_xml = svc.fetch_prot_cte(CHAVE_CTE)
        
        if resp_xml:
            print(f"   ✅ Resposta recebida!\n")
            print(f"{'='*80}")
            print(f"📄 RESPOSTA XML:\n")
            
            # Parsear e exibir de forma legível
            try:
                root = ET.fromstring(resp_xml)
                
                # Função para imprimir XML de forma legível
                def print_element(elem, indent=0):
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    spaces = '  ' * indent
                    
                    if elem.text and elem.text.strip():
                        print(f"{spaces}{tag}: {elem.text.strip()}")
                    else:
                        print(f"{spaces}{tag}:")
                    
                    for child in elem:
                        print_element(child, indent + 1)
                
                print_element(root)
                
                # Tentar extrair informações importantes
                print(f"\n{'='*80}")
                print(f"📊 INFORMAÇÕES EXTRAÍDAS:\n")
                
                # Procurar por informações relevantes
                ns_cte = {'cte': 'http://www.portalfiscal.inf.br/cte'}
                
                # Status do CT-e
                c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                x_motivo = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
                
                if c_stat:
                    print(f"   📋 Status: {c_stat}")
                if x_motivo:
                    print(f"   💬 Motivo: {x_motivo}")
                
                # Procurar por protocolo
                n_prot = root.findtext('.//{http://www.portalfiscal.inf.br/cte}nProt')
                if n_prot:
                    print(f"   🔢 Protocolo: {n_prot}")
                
                # Procurar por eventos
                print(f"\n🔍 Procurando eventos no retorno...\n")
                
                eventos = root.findall('.//{http://www.portalfiscal.inf.br/cte}procEventoCTe')
                if eventos:
                    print(f"   ✅ Encontrados {len(eventos)} eventos:\n")
                    for evt in eventos:
                        tp_evento = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
                        c_stat_evt = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                        x_motivo_evt = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
                        dh_evento = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}dhEvento')
                        
                        print(f"      📌 Tipo: {tp_evento}")
                        print(f"      📋 Status: {c_stat_evt} - {x_motivo_evt}")
                        print(f"      📅 Data: {dh_evento}")
                        
                        if tp_evento == '110111':
                            print(f"      🔥 EVENTO DE CANCELAMENTO!")
                        
                        print()
                else:
                    print(f"   ❌ Nenhum evento encontrado no retorno")
                
            except Exception as e:
                print(f"\n⚠️ Erro ao parsear XML: {e}")
                print(f"\nXML bruto:\n{resp_xml[:2000]}...")
            
            # Sucesso - parar de tentar outros certificados
            break
        else:
            print(f"   ❌ Sem resposta")
    
    except Exception as e:
        print(f"   ❌ Erro: {str(e)[:100]}")
    
    print()

# Fim do script
print(f"\n{'='*80}\n")
