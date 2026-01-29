import requests_pkcs12
import requests
import sqlite3
import json
import gzip
import base64

# Buscar certificado no banco
conn = sqlite3.connect('nfe_data.db')
cursor = conn.execute("SELECT caminho, senha FROM certificados_sefaz WHERE cnpj_cpf = '33251845000109'")
row = cursor.fetchone()
if not row:
    print("❌ Certificado não encontrado")
    exit(1)

cert_path, senha = row
print(f"✅ Certificado: {cert_path}")
print(f"✅ Senha: {'*' * len(senha)}")

# XML de consulta ABRASF 2.02
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
print("\n📦 Compactando XML...")
xml_gzip = gzip.compress(xml_consulta.encode('utf-8'))
xml_b64 = base64.b64encode(xml_gzip).decode('ascii')
print(f"   XML: {len(xml_consulta)} bytes")
print(f"   GZIP: {len(xml_gzip)} bytes ({100 - len(xml_gzip)*100//len(xml_consulta):.0f}% redução)")
print(f"   Base64: {len(xml_b64)} chars")

# JSON payload
payload = {"LoteXmlGZipB64": [xml_b64]}
print(f"\n📤 Payload JSON: {len(json.dumps(payload))} bytes")

# Testar endpoints
urls = [
    "https://adn.producaorestrita.nfse.gov.br/adn",
    "https://adn.nfse.gov.br/adn"
]

for url_base in urls:
    url = f"{url_base}/DFe"
    print(f"\n{'='*80}")
    print(f"🌐 Testando: {url}")
    print('='*80)
    
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
            timeout=30
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 201:
            print("✅ SUCESSO!")
            try:
                data = response.json()
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except:
                print("Resposta não é JSON:")
                print(response.text[:1000])
        elif response.status_code == 400:
            print("⚠️  BAD REQUEST (400)")
            print(response.text[:1000])
        elif response.status_code == 404:
            print("❌ NOT FOUND (404) - Endpoint não existe")
        elif response.status_code == 496:
            print("❌ Certificado SSL necessário (496)")
        else:
            print(f"⚠️  Resposta inesperada ({response.status_code}):")
            print(response.text[:1000])
            
    except requests.exceptions.SSLError as e:
        print(f"❌ Erro SSL: {e}")
    except Exception as e:
        print(f"❌ Erro: {type(e).__name__}: {e}")

print("\n" + "="*80)
print("FIM DOS TESTES")
print("="*80)

