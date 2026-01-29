#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Busca documentação swagger dos diferentes endpoints ADN
"""
import requests_pkcs12
import sqlite3
import json

# Buscar certificado
conn = sqlite3.connect('nfe_data.db')
row = conn.execute("SELECT caminho, senha FROM certificados_sefaz WHERE cnpj_cpf = '33251845000109'").fetchone()
cert_path, senha = row

print(f"✅ Certificado: {cert_path}\n")

# Endpoints a testar
endpoints = {
    "ADN Recepção": "https://adn.producaorestrita.nfse.gov.br/docs/swagger.json",
    "ADN Contribuintes": "https://adn.producaorestrita.nfse.gov.br/contribuintes/docs/swagger.json",
    "ADN Municípios": "https://adn.producaorestrita.nfse.gov.br/municipios/docs/swagger.json",
    "CNC": "https://adn.producaorestrita.nfse.gov.br/cnc/docs/swagger.json",
    "CNC Consulta": "https://adn.producaorestrita.nfse.gov.br/cnc/consulta/docs/swagger.json",
    "SEFIN Nacional": "https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional/docs/swagger.json",
}

for nome, url in endpoints.items():
    print("=" * 80)
    print(f"📚 {nome}")
    print(f"🔗 {url}")
    print("=" * 80)
    
    try:
        response = requests_pkcs12.get(
            url,
            pkcs12_filename=cert_path,
            pkcs12_password=senha,
            verify=False,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Swagger JSON obtido!")
                print(f"\nTítulo: {data.get('info', {}).get('title', 'N/A')}")
                print(f"Descrição: {data.get('info', {}).get('description', 'N/A')[:200]}...")
                
                # Listar endpoints
                paths = data.get('paths', {})
                if paths:
                    print(f"\n📍 Endpoints disponíveis ({len(paths)}):")
                    for path, methods in paths.items():
                        for method in methods.keys():
                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE']:
                                summary = methods[method].get('summary', 'N/A')
                                print(f"   {method.upper():6} {path}")
                                print(f"          → {summary}")
                
                # Salvar arquivo
                filename = f"swagger_{nome.replace(' ', '_').lower()}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"\n💾 Salvo em: {filename}")
                
            except json.JSONDecodeError:
                print("⚠️ Resposta não é JSON válido")
                print(response.text[:500])
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}: {e}")
    
    print()
