#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testa endpoints ADN diretamente
"""
import requests_pkcs12
import sqlite3
import json
import gzip
import base64

# Buscar certificado
conn = sqlite3.connect('nfe_data.db')
row = conn.execute("SELECT caminho, senha FROM certificados_sefaz WHERE cnpj_cpf = '33251845000109'").fetchone()
cert_path, senha = row

print(f"✅ Certificado: {cert_path}\n")

# XML de teste (ABRASF ConsultarNfseEnvio)
xml_consulta = """<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Prestador>
        <Cnpj>33251845000109</Cnpj>
        <InscricaoMunicipal></InscricaoMunicipal>
    </Prestador>
    <PeriodoEmissao>
        <DataInicial>2025-05-01</DataInicial>
        <DataFinal>2025-12-17</DataFinal>
    </PeriodoEmissao>
</ConsultarNfseEnvio>"""

# Compress e encode
xml_gzip = gzip.compress(xml_consulta.encode('utf-8'))
xml_b64 = base64.b64encode(xml_gzip).decode('ascii')
payload = {"LoteXmlGZipB64": [xml_b64]}

# Endpoints a testar
endpoints_post = [
    ("ADN /DFe", "https://adn.producaorestrita.nfse.gov.br/adn/DFe"),
    ("Contribuintes", "https://adn.producaorestrita.nfse.gov.br/contribuintes"),
    ("Contribuintes/DFe", "https://adn.producaorestrita.nfse.gov.br/contribuintes/DFe"),
    ("Contribuintes/Consulta", "https://adn.producaorestrita.nfse.gov.br/contribuintes/Consulta"),
    ("Contribuintes/ConsultarNfse", "https://adn.producaorestrita.nfse.gov.br/contribuintes/ConsultarNfse"),
    ("Municipios", "https://adn.producaorestrita.nfse.gov.br/municipios"),
    ("Municipios/DFe", "https://adn.producaorestrita.nfse.gov.br/municipios/DFe"),
]

for nome, url in endpoints_post:
    print("=" * 80)
    print(f"📍 {nome}")
    print(f"🔗 POST {url}")
    print("=" * 80)
    
    try:
        response = requests_pkcs12.post(
            url,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            pkcs12_filename=cert_path,
            pkcs12_password=senha,
            verify=False,
            timeout=15
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code in [200, 201]:
            print("✅ SUCESSO!")
            try:
                data = response.json()
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            except:
                print(response.text[:500])
        elif response.status_code == 404:
            print("❌ Endpoint não existe")
        elif response.status_code == 400:
            print("⚠️ Bad Request")
            print(response.text[:500])
        else:
            print(f"⚠️ Resposta: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}: {e}")
    
    print()

print("\n" + "=" * 80)
print("Testando endpoints GET")
print("=" * 80 + "\n")

# Testar GET também
endpoints_get = [
    ("Contribuintes/Nfse", "https://adn.producaorestrita.nfse.gov.br/contribuintes/nfse"),
    ("Municipios/Nfse", "https://adn.producaorestrita.nfse.gov.br/municipios/nfse"),
]

for nome, url in endpoints_get:
    print(f"🔗 GET {nome}: {url}")
    try:
        response = requests_pkcs12.get(
            url,
            params={
                "cnpj": "33251845000109",
                "dataInicial": "2025-05-01",
                "dataFinal": "2025-12-17"
            },
            pkcs12_filename=cert_path,
            pkcs12_password=senha,
            verify=False,
            timeout=15
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")
    print()
