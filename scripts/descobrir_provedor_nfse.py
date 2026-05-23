# -*- coding: utf-8 -*-
"""
Descobre o provedor NFS-e correto através do CNPJ
"""
import requests
import re

CNPJ = "56237242000158"

print("🔍 Consultando CNPJ na Receita Federal...")
print(f"   CNPJ: {CNPJ}")
print()

# Remove formatação
cnpj_limpo = re.sub(r'\D', '', CNPJ)

# Tenta ReceitaWS (fallback)
try:
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, timeout=10, headers=headers)
    
    if response.status_code == 200:
        dados = response.json()
        
        razao_social = dados.get('nome', '')
        municipio = dados.get('municipio', '')
        uf = dados.get('uf', '')
        codigo_ibge = dados.get('codigo_municipio', '')
        
        print("✅ Dados encontrados:")
        print(f"   Razão Social: {razao_social}")
        print(f"   Município: {municipio}/{uf}")
        print(f"   Código IBGE: {codigo_ibge}")
        print()
        
        # Agora busca o provedor NFS-e deste município
        print("🔍 Buscando provedor NFS-e do município...")
        
        # Mapeamento conhecido de municípios MG
        PROVEDORES_CONHECIDOS = {
            "3106200": {  # Belo Horizonte
                "nome": "BHISS Digital",
                "url": "https://bhissdigital.pbh.gov.br/bhiss-ws/nfse",
                "provedor": "BHISS"
            },
            "3143906": {  # Poços de Caldas
                "nome": "ISSWeb",
                "url": "https://www.isswebfacil.com.br/webiss/webservices",
                "provedor": "ISSWeb"
            },
            "3118601": {  # Contagem
                "nome": "Betha",
                "url": "https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfseContagem",
                "provedor": "BETHA"
            },
            "3170206": {  # Uberlândia
                "nome": "SystemPro",
                "url": "https://issdigital.uberlandia.mg.gov.br/WsNFe2/LoteRps",
                "provedor": "SYSTEMPRO"
            }
        }
        
        if codigo_ibge in PROVEDORES_CONHECIDOS:
            config = PROVEDORES_CONHECIDOS[codigo_ibge]
            print(f"✅ Provedor encontrado: {config['nome']}")
            print(f"   URL: {config['url']}")
            print(f"   Tipo: {config['provedor']}")
        else:
            print(f"⚠️  Município {municipio} não está no mapeamento conhecido")
            print()
            print("💡 SOLUÇÕES:")
            print("   1. Acesse o site da prefeitura e veja qual sistema de NFS-e usam")
            print(f"   2. Procure por 'nota fiscal eletrônica {municipio} MG'")
            print("   3. Verifique se há portal específico de NFS-e da cidade")
            print()
            print("📋 Provedores mais comuns em MG:")
            print("   • Ginfes (Fiorilli)")
            print("   • Betha Sistemas")
            print("   • ISS.NET (Thema)")
            print("   • SystemPro (WebISS)")
            print("   • Simpliss")
            print()
            print("🌐 Links úteis:")
            print(f"   • Google: https://www.google.com/search?q=nfse+{municipio.replace(' ', '+')}+mg")
            print(f"   • Portal Transparência: https://www.{municipio.lower().replace(' ', '')}.mg.gov.br")
        
    else:
        print(f"❌ Erro ao consultar: Status {response.status_code}")
        
except Exception as e:
    print(f"❌ Erro: {e}")
