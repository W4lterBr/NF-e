# -*- coding: utf-8 -*-
"""
Tenta descobrir endpoint de notas emitidas baseado no padrão conhecido
Endpoint base confirmado: /contribuintes/
"""
import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))

from nfe_search import DatabaseManager

CNPJ = "56237242000158"

print("="*80)
print("🔍 DESCOBRINDO ENDPOINT DE NOTAS EMITIDAS")
print("="*80)
print()

# Busca certificado
db_path = os.path.join(os.path.dirname(__file__), 'notas.db')
db = DatabaseManager(db_path)

certificados = db.get_certificados()
cert_data = None

for cnpj, caminho, senha, informante, cuf in certificados:
    if informante == CNPJ:
        cert_data = (cnpj, caminho, senha, informante, cuf)
        break

if not cert_data:
    print(f"❌ Certificado não encontrado")
    sys.exit(1)

cnpj, path, senha, inf, cuf = cert_data

# Inicializa cliente
import requests_pkcs12

with open(path, 'rb') as f:
    pkcs12_data = f.read()

session = requests.Session()
session.mount('https://', requests_pkcs12.Pkcs12Adapter(
    pkcs12_data=pkcs12_data,
    pkcs12_password=senha
))

session.headers.update({
    'Accept': 'application/json',
})

url_base = "https://adn.nfse.gov.br"

# Endpoints para testar (baseados no padrão /contribuintes/)
# Confirmado que funciona: /contribuintes/DFe/{NSU}
# Confirmado que existe: /contribuintes/nfse/emitidas (mas 429)

endpoints_testar = [
    # Variações de DFe
    "/contribuintes/DFe",
    "/contribuintes/dfe",
    
    # Variações de NFS-e
    "/contribuintes/nfse",
    "/contribuintes/NFSe",
    "/contribuintes/nfs-e",
    
    # Emitidas (já sabemos que existe)
    "/contribuintes/nfse/emitidas",
    "/contribuintes/NFSe/emitidas",
    
    # Consultas
    "/contribuintes/consulta/nfse",
    "/contribuintes/consulta/emitidas",
    
    # Período
    "/contribuintes/nfse/periodo",
    "/contribuintes/periodo",
    
    # Lista
    "/contribuintes/nfse/lista",
    "/contribuintes/lista",
    
    # Documentos
    "/contribuintes/documentos",
    "/contribuintes/documentos/emitidos",
]

print(f"📋 Testando {len(endpoints_testar)} endpoints...")
print(f"   CNPJ: {cnpj}")
print()

endpoints_validos = []

for i, endpoint in enumerate(endpoints_testar, 1):
    url = f"{url_base}{endpoint}"
    
    print(f"{i:2d}. {endpoint:45s} ", end='', flush=True)
    
    try:
        # HEAD request para não consumir dados
        response = session.head(url, timeout=5, allow_redirects=False)
        status = response.status_code
        
        if status == 200:
            print(f"✅ 200 OK")
            endpoints_validos.append((endpoint, status, "Funcionando"))
        elif status == 204:
            print(f"✅ 204 No Content")
            endpoints_validos.append((endpoint, status, "Vazio mas válido"))
        elif status == 401:
            print(f"🔐 401 Unauthorized")
            endpoints_validos.append((endpoint, status, "Existe mas precisa auth"))
        elif status == 403:
            print(f"🚫 403 Forbidden")
            endpoints_validos.append((endpoint, status, "Existe mas bloqueado"))
        elif status == 405:
            print(f"⚠️  405 Method Not Allowed (HEAD)")
            # Tenta GET
            response_get = session.get(url, timeout=5)
            if response_get.status_code == 200:
                print(f"      → GET: ✅ 200 OK")
                endpoints_validos.append((endpoint, 200, "GET funciona"))
            elif response_get.status_code == 429:
                print(f"      → GET: ⏱️  429 Rate Limit")
                endpoints_validos.append((endpoint, 429, "Existe mas rate limit"))
        elif status == 429:
            print(f"⏱️  429 Rate Limit")
            endpoints_validos.append((endpoint, status, "Existe mas rate limit"))
        elif status == 404:
            print(f"❌ 404")
        elif status == 301 or status == 302:
            print(f"🔀 {status} Redirect → {response.headers.get('Location', '?')}")
            endpoints_validos.append((endpoint, status, f"Redireciona"))
        else:
            print(f"⁉️  {status}")
            endpoints_validos.append((endpoint, status, "Status desconhecido"))
        
        # Delay para evitar rate limit
        time.sleep(0.5)
        
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error")
    except Exception as e:
        print(f"❌ {type(e).__name__}")

print()
print("="*80)

if endpoints_validos:
    print("✅ ENDPOINTS VÁLIDOS ENCONTRADOS:")
    print("="*80)
    for endpoint, status, descricao in endpoints_validos:
        print(f"   {status} - {endpoint}")
        print(f"      {descricao}")
        print()
    
    # Salva em arquivo
    with open('endpoints_validos_adn.txt', 'w', encoding='utf-8') as f:
        f.write("ENDPOINTS VÁLIDOS ADN NACIONAL\n")
        f.write("="*80 + "\n\n")
        for endpoint, status, descricao in endpoints_validos:
            f.write(f"{status} - {url_base}{endpoint}\n")
            f.write(f"   {descricao}\n\n")
    
    print("💾 Lista salva em: endpoints_validos_adn.txt")
else:
    print("❌ NENHUM ENDPOINT VÁLIDO ENCONTRADO")

print("="*80)
