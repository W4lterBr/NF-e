#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa consulta CT-e com XML formatado corretamente
"""

import sys
from pathlib import Path
import requests_pkcs12
from lxml import etree
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).parent))
from modules.database import DatabaseManager

CHAVE_CTE = "50251203232675000154570010056290311009581385"

# Pegar certificado
db = DatabaseManager('notas.db')
cert = db.load_certificates()[0]

print(f"🔍 Testando consulta CT-e com XML corrigido")
print(f"📦 Chave: {CHAVE_CTE}\n")

# XML SEM espaços/tabs desnecessários
xml_consulta = f'<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chCTe>{CHAVE_CTE}</chCTe></consSitCTe>'

# Envelope SOAP 1.2 COMPACTO
soap_envelope = f'<?xml version="1.0" encoding="utf-8"?><soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body><cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg></soap12:Body></soap12:Envelope>'

# Testar URLs que tiveram melhor resultado
urls_testar = {
    'PR - Paraná': 'https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4',
    'MS - Mato Grosso do Sul': 'https://producao.cte.ms.gov.br/ws/CTeConsultaV4',
}

for estado, url in urls_testar.items():
    print(f"🌐 {estado}")
    print(f"   📌 {url}")
    
    try:
        response = requests_pkcs12.post(
            url,
            data=soap_envelope.encode('utf-8'),
            headers={'Content-Type': 'application/soap+xml; charset=utf-8'},
            pkcs12_filename=cert['caminho'],
            pkcs12_password=cert['senha'],
            verify=False,
            timeout=10
        )
        
        print(f"   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCESSO!\n")
            
            # Parsear resposta
            root = etree.fromstring(response.content)
            
            # Extrair informações
            c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
            x_motivo = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
            
            print(f"   📋 cStat: {c_stat}")
            print(f"   💬 xMotivo: {x_motivo}\n")
            
            # Se sucesso real (não erro 599), mostrar dados completos
            if c_stat and c_stat not in ['599', '217', '218']:
                print(f"{'='*100}")
                print(f"📄 RESPOSTA COMPLETA:\n")
                print(etree.tostring(root, pretty_print=True, encoding='unicode'))
                print(f"{'='*100}\n")
                
                # Procurar por eventos
                print(f"\n🔍 Procurando eventos...\n")
                eventos = root.findall('.//{http://www.portalfiscal.inf.br/cte}procEventoCTe')
                
                if eventos:
                    print(f"✅ Encontrados {len(eventos)} eventos:\n")
                    for evt in eventos:
                        tp_evento = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
                        c_stat_evt = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                        x_motivo_evt = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
                        dh_evento = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}dhEvento')
                        
                        print(f"   📌 Tipo: {tp_evento}")
                        if tp_evento == '110111':
                            print(f"      🔥 CANCELAMENTO DE CT-e!")
                        print(f"   📋 Status: {c_stat_evt} - {x_motivo_evt}")
                        print(f"   📅 Data: {dh_evento}")
                        print()
                else:
                    print(f"   ❌ Nenhum evento no retorno")
        
        elif response.status_code == 500:
            root = etree.fromstring(response.content)
            fault = root.findtext('.//{http://www.w3.org/2003/05/soap-envelope}Reason//{http://www.w3.org/2003/05/soap-envelope}Text')
            print(f"   ❌ Erro 500: {fault or 'Erro desconhecido'}")
        
        else:
            print(f"   ❌ Erro HTTP {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Exceção: {str(e)[:150]}")
    
    print()
