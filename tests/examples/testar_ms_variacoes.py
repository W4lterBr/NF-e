#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa diferentes variações de SOAP para MS (Mato Grosso do Sul)
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
URL_MS = "https://producao.cte.ms.gov.br/ws/CTeConsultaV4"

# Pegar certificado
db = DatabaseManager('notas.db')
cert = db.load_certificates()[0]

print(f"🔍 Testando MS (Mato Grosso do Sul) com diferentes variações\n")
print(f"📦 Chave: {CHAVE_CTE}")
print(f"🌐 URL: {URL_MS}\n")
print(f"{'='*100}\n")

# XML de consulta base
xml_consulta = f'<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chCTe>{CHAVE_CTE}</chCTe></consSitCTe>'

# Variações a testar
variacoes = []

# Variação 1: SOAP 1.2 com namespace padrão
variacoes.append({
    'nome': 'SOAP 1.2 - Namespace padrão CteConsultaV4',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg>
    </soap12:Body>
</soap12:Envelope>''',
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Variação 2: SOAP 1.2 sem wrapper cteDadosMsg
variacoes.append({
    'nome': 'SOAP 1.2 - Sem wrapper cteDadosMsg',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        {xml_consulta}
    </soap12:Body>
</soap12:Envelope>''',
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Variação 3: SOAP 1.2 com namespace diferente
variacoes.append({
    'nome': 'SOAP 1.2 - Namespace CTeConsultaV4 (maiúscula)',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CTeConsultaV4">{xml_consulta}</cteDadosMsg>
    </soap12:Body>
</soap12:Envelope>''',
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Variação 4: SOAP 1.1
variacoes.append({
    'nome': 'SOAP 1.1 - Tentativa',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg>
    </soap:Body>
</soap:Envelope>''',
    'headers': {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4/cteConsultaCT'
    }
})

# Variação 5: SOAP 1.2 compacto (sem quebras de linha)
envelope_compacto = f'<?xml version="1.0" encoding="utf-8"?><soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body><cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg></soap12:Body></soap12:Envelope>'
variacoes.append({
    'nome': 'SOAP 1.2 - Compacto (sem espaços)',
    'envelope': envelope_compacto,
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Variação 6: Com namespace CteConsulta (sem o V4)
variacoes.append({
    'nome': 'SOAP 1.2 - Namespace CteConsulta (sem V4)',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsulta">{xml_consulta}</cteDadosMsg>
    </soap12:Body>
</soap12:Envelope>''',
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Variação 7: Com cteConsultaCT ao invés de cteDadosMsg
variacoes.append({
    'nome': 'SOAP 1.2 - Usando cteConsultaCT',
    'envelope': f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        <cteConsultaCT xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteConsultaCT>
    </soap12:Body>
</soap12:Envelope>''',
    'headers': {'Content-Type': 'application/soap+xml; charset=utf-8'}
})

# Testar cada variação
for idx, var in enumerate(variacoes, 1):
    print(f"🧪 Teste {idx}/{len(variacoes)}: {var['nome']}")
    print(f"   📏 Tamanho: {len(var['envelope'])} bytes")
    
    try:
        response = requests_pkcs12.post(
            URL_MS,
            data=var['envelope'].encode('utf-8'),
            headers=var['headers'],
            pkcs12_filename=cert['caminho'],
            pkcs12_password=cert['senha'],
            verify=False,
            timeout=10
        )
        
        print(f"   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCESSO!\n")
            
            root = etree.fromstring(response.content)
            c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
            x_motivo = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
            
            print(f"   📋 cStat: {c_stat}")
            print(f"   💬 xMotivo: {x_motivo}\n")
            
            if c_stat and c_stat not in ['217', '218', '599']:
                print(f"\n{'='*100}")
                print(f"🎯 RESPOSTA COMPLETA (cStat {c_stat}):\n")
                print(etree.tostring(root, pretty_print=True, encoding='unicode')[:3000])
                print(f"{'='*100}\n")
                
                # Procurar eventos
                eventos = root.findall('.//{http://www.portalfiscal.inf.br/cte}procEventoCTe')
                if eventos:
                    print(f"\n✅ {len(eventos)} eventos encontrados!")
                    for evt in eventos:
                        tp = evt.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
                        if tp == '110111':
                            print(f"   🔥 CANCELAMENTO!")
                
                # Sucesso - parar de testar
                print(f"\n🎉 ENCONTRAMOS A CONFIGURAÇÃO CORRETA!")
                break
        
        elif response.status_code == 500:
            # Tentar extrair mensagem de erro
            try:
                root = etree.fromstring(response.content)
                fault = root.findtext('.//{http://www.w3.org/2003/05/soap-envelope}Reason//{http://www.w3.org/2003/05/soap-envelope}Text')
                if not fault:
                    fault = root.findtext('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
                if not fault:
                    # Procurar qualquer texto de erro
                    fault_elem = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Fault')
                    if fault_elem is not None:
                        fault = etree.tostring(fault_elem, encoding='unicode', method='text')[:200]
                
                print(f"   ❌ Erro 500: {fault or 'Erro desconhecido'}")
                
                # Mostrar primeiros 500 caracteres da resposta para debug
                if not fault or fault == 'java.lang.NullPointerException':
                    print(f"   🔍 Resposta bruta:")
                    print(f"   {response.text[:500]}")
            except:
                print(f"   ❌ Erro 500 não parseável")
                print(f"   🔍 Início da resposta: {response.text[:300]}")
        else:
            print(f"   ❌ HTTP {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Exceção: {str(e)[:200]}")
    
    print()

print(f"\n{'='*100}\n")
print(f"📊 RESUMO: Testadas {len(variacoes)} variações para MS")
