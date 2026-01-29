#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testa TODAS as URLs oficiais de consulta de CT-e
"""

import sys
import os
from pathlib import Path
import requests
import urllib3
from lxml import etree

# Desabilitar warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from modules.database import DatabaseManager

# Chave do CT-e
CHAVE_CTE = "50251203232675000154570010056290311009581385"

# URLs oficiais de consulta CT-e por estado/autorizador
URLS_OFICIAIS = {
    'MT - Mato Grosso': 'https://cte.sefaz.mt.gov.br/ctews2/services/CTeConsultaV4',
    'MS - Mato Grosso do Sul': 'https://producao.cte.ms.gov.br/ws/CTeConsultaV4',
    'MG - Minas Gerais': 'https://cte.fazenda.mg.gov.br/cte/services/CTeConsultaV4',
    'PR - Paraná': 'https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4',
    'RS - Rio Grande do Sul': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',
    'SP - São Paulo': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx',
    'SVRS - Sefaz Virtual RS': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',
    'SVSP - Sefaz Virtual SP': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx',
}

print(f"🔍 Testando TODAS as URLs oficiais de CT-e")
print(f"📦 Chave: {CHAVE_CTE}")
print(f"📍 UF: 50 (MS - Mato Grosso do Sul)")
print(f"\n{'='*100}\n")

# Pegar primeiro certificado
db = DatabaseManager('notas.db')
certificados = db.load_certificates()

if not certificados:
    print("❌ Nenhum certificado encontrado")
    sys.exit(1)

cert = certificados[0]
cert_path = cert['caminho']
cert_senha = cert['senha']
cert_cnpj = cert['cnpj_cpf']

print(f"🔑 Usando certificado: {cert['informante']} ({cert_cnpj})\n")
print(f"{'='*100}\n")

# Criar XML de consulta
xml_consulta = f'''<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00">
    <tpAmb>1</tpAmb>
    <xServ>CONSULTAR</xServ>
    <chCTe>{CHAVE_CTE}</chCTe>
</consSitCTe>'''

# Testar cada URL
resultados = []

for estado, url in URLS_OFICIAIS.items():
    print(f"🌐 {estado}")
    print(f"   📌 URL: {url}")
    
    try:
        # Criar envelope SOAP 1.2
        soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Body>
        <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteConsultaV4">{xml_consulta}</cteDadosMsg>
    </soap12:Body>
</soap12:Envelope>'''
        
        # Importar requests_pkcs12 para usar certificado
        import requests_pkcs12
        
        # Fazer requisição
        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8'
        }
        
        response = requests_pkcs12.post(
            url,
            data=soap_envelope.encode('utf-8'),
            headers=headers,
            pkcs12_filename=cert_path,
            pkcs12_password=cert_senha,
            verify=False,
            timeout=10
        )
        
        print(f"   📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ SUCESSO! Resposta recebida ({len(response.content)} bytes)")
            
            # Tentar parsear resposta
            try:
                root = etree.fromstring(response.content)
                
                # Procurar por informações importantes
                c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                x_motivo = root.findtext('.//{http://www.portalfiscal.inf.br/cte}xMotivo')
                
                if c_stat:
                    print(f"   📋 cStat: {c_stat}")
                    print(f"   💬 xMotivo: {x_motivo}")
                    
                    resultados.append({
                        'estado': estado,
                        'url': url,
                        'sucesso': True,
                        'c_stat': c_stat,
                        'x_motivo': x_motivo,
                        'resposta': response.content
                    })
                else:
                    print(f"   ⚠️  Resposta sem cStat")
                    resultados.append({
                        'estado': estado,
                        'url': url,
                        'sucesso': True,
                        'c_stat': None,
                        'x_motivo': None,
                        'resposta': response.content
                    })
            except Exception as e:
                print(f"   ⚠️  Erro ao parsear: {str(e)[:100]}")
                resultados.append({
                    'estado': estado,
                    'url': url,
                    'sucesso': True,
                    'erro_parse': str(e),
                    'resposta': response.content
                })
        
        elif response.status_code == 500:
            print(f"   ⚠️  Erro 500 - Verificando mensagem...")
            # 500 pode ser erro SOAP com mensagem útil
            try:
                root = etree.fromstring(response.content)
                fault_string = root.findtext('.//{http://www.w3.org/2003/05/soap-envelope}Reason//{http://www.w3.org/2003/05/soap-envelope}Text')
                if not fault_string:
                    fault_string = root.findtext('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
                
                if fault_string:
                    print(f"   💬 Mensagem: {fault_string}")
                    resultados.append({
                        'estado': estado,
                        'url': url,
                        'sucesso': False,
                        'erro': fault_string
                    })
                else:
                    print(f"   ❌ Erro 500 sem mensagem clara")
                    resultados.append({
                        'estado': estado,
                        'url': url,
                        'sucesso': False,
                        'erro': 'HTTP 500'
                    })
            except:
                print(f"   ❌ Erro 500 - não foi possível parsear")
                resultados.append({
                    'estado': estado,
                    'url': url,
                    'sucesso': False,
                    'erro': 'HTTP 500 - não parseável'
                })
        
        else:
            print(f"   ❌ Erro HTTP {response.status_code}")
            resultados.append({
                'estado': estado,
                'url': url,
                'sucesso': False,
                'erro': f'HTTP {response.status_code}'
            })
    
    except requests.exceptions.Timeout:
        print(f"   ⏱️  Timeout")
        resultados.append({
            'estado': estado,
            'url': url,
            'sucesso': False,
            'erro': 'Timeout'
        })
    except Exception as e:
        print(f"   ❌ Exceção: {str(e)[:100]}")
        resultados.append({
            'estado': estado,
            'url': url,
            'sucesso': False,
            'erro': str(e)[:100]
        })
    
    print()

# Resumo dos resultados
print(f"\n{'='*100}")
print(f"📊 RESUMO DOS TESTES\n")
print(f"{'='*100}\n")

sucessos = [r for r in resultados if r.get('sucesso')]
falhas = [r for r in resultados if not r.get('sucesso')]

print(f"✅ Sucessos: {len(sucessos)}")
print(f"❌ Falhas: {len(falhas)}\n")

if sucessos:
    print(f"🎯 URLs QUE FUNCIONARAM:\n")
    for r in sucessos:
        print(f"   ✅ {r['estado']}")
        print(f"      {r['url']}")
        if r.get('c_stat'):
            print(f"      Status: {r['c_stat']} - {r['x_motivo']}")
        print()
    
    # Salvar resposta completa do primeiro sucesso
    if sucessos[0].get('resposta'):
        print(f"\n{'='*100}")
        print(f"📄 RESPOSTA COMPLETA DO PRIMEIRO SUCESSO:\n")
        print(f"{'='*100}\n")
        
        try:
            root = etree.fromstring(sucessos[0]['resposta'])
            print(etree.tostring(root, pretty_print=True, encoding='unicode'))
        except:
            print(sucessos[0]['resposta'].decode('utf-8', errors='ignore'))

if falhas:
    print(f"\n❌ URLs QUE FALHARAM:\n")
    for r in falhas:
        print(f"   ❌ {r['estado']}: {r.get('erro', 'Erro desconhecido')}")

print(f"\n{'='*100}\n")
