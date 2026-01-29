# -*- coding: utf-8 -*-
"""
Teste de conectividade SSL/TLS com SEFAZ
Verifica quais protocolos funcionam
"""
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    """Adaptador que força TLS 1.1+ para compatibilidade com SEFAZ"""
    
    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TLSAdapter, self).__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context(ssl_version=ssl.PROTOCOL_TLS)
        # Habilita TLS 1.0, 1.1 e 1.2
        ctx.options |= ssl.OP_NO_SSLv2
        ctx.options |= ssl.OP_NO_SSLv3
        # Desabilita verificacao de hostname (para usar com verify=False)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Não desabilita TLS 1.0 ou 1.1 (alguns servidores SEFAZ ainda usam)
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

# URL da SEFAZ
url = "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx"

print("=" * 80)
print("TESTE DE CONECTIVIDADE SSL/TLS - SEFAZ")
print("=" * 80)
print(f"\nURL: {url}")

# Teste 1: Conexao padrao (sem adapter customizado)
print("\n1. TESTE COM CONFIGURACAO PADRAO:")
try:
    session = requests.Session()
    response = session.get(url, timeout=10, verify=False)
    print(f"   Status: {response.status_code}")
    print(f"   Protocolo: {response.raw.version}")
    print(f"   OK - Conectou com sucesso")
except Exception as e:
    print(f"   ERRO: {e}")

# Teste 2: Com TLSAdapter (forçando TLS 1.1+)
print("\n2. TESTE COM TLSAdapter (TLS 1.1+):")
try:
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    response = session.get(url, timeout=10, verify=False)
    print(f"   Status: {response.status_code}")
    print(f"   Protocolo: {response.raw.version}")
    print(f"   OK - Conectou com TLSAdapter")
except Exception as e:
    print(f"   ERRO: {e}")

# Teste 3: Verificar se WSDL está acessível
print("\n3. TESTE DE WSDL:")
try:
    wsdl_url = url + "?wsdl"
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    response = session.get(wsdl_url, timeout=10, verify=False)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Tamanho WSDL: {len(response.content)} bytes")
        print(f"   OK - WSDL acessivel")
    else:
        print(f"   ERRO - Status {response.status_code}")
except Exception as e:
    print(f"   ERRO: {e}")

# Teste 4: Testar POST com SOAP minimo
print("\n4. TESTE DE POST SOAP:")
try:
    # SOAP minimo para testar conectividade
    soap_test = """<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">
      <envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
        <idLote>1</idLote>
      </envEvento>
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""
    
    session = requests.Session()
    session.mount('https://', TLSAdapter())
    
    headers = {
        'Content-Type': 'application/soap+xml; charset=utf-8',
        'SOAPAction': '"http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento"'
    }
    
    response = session.post(url, data=soap_test.encode('utf-8'), headers=headers, timeout=10, verify=False)
    print(f"   Status: {response.status_code}")
    print(f"   Resposta: {response.text[:200]}...")
    
    # Esperamos erro de validacao, nao erro de conexao
    if response.status_code == 200 or 'soap' in response.text.lower():
        print(f"   OK - Servidor SOAP respondeu (validacao esperada)")
    else:
        print(f"   AVISO - Resposta inesperada")
except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "=" * 80)
print("CONCLUSAO:")
print("=" * 80)
print("Se todos os testes OK -> problema nao e SSL/TLS")
print("Se teste 2 OK mas teste 1 ERRO -> precisa TLSAdapter")
print("Se teste 4 tem resposta SOAP -> conectividade OK")
