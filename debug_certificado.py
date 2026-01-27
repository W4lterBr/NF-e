"""
Verifica detalhes do certificado e testa com URL do SVRS
"""

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import requests_pkcs12
from lxml import etree
import urllib3
urllib3.disable_warnings()

# Caminho do certificado
cert_path = input("Caminho do certificado .pfx: ").strip().strip('"')
cert_password = input("Senha: ").strip()

print("\n" + "="*80)
print("ANÁLISE DO CERTIFICADO")
print("="*80)

# Carrega certificado
with open(cert_path, 'rb') as f:
    pfx_data = f.read()

private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
    pfx_data, cert_password.encode(), default_backend()
)

print(f"\n✓ Certificado carregado com sucesso!")
print(f"\nSubject: {certificate.subject}")
print(f"Issuer: {certificate.issuer}")
print(f"Válido de: {certificate.not_valid_before_utc}")
print(f"Válido até: {certificate.not_valid_after_utc}")

# Extrai CNPJ
cnpj = None
for attr in certificate.subject:
    if attr.oid.dotted_string == '2.5.4.3':  # CN
        cn = attr.value
        if ':' in cn:
            cnpj = cn.split(':')[-1]
            print(f"\nCNPJ extraído: {cnpj}")

print(f"\nCertificados adicionais na cadeia: {len(additional_certs if additional_certs else [])}")

# Teste simples
print("\n" + "="*80)
print("TESTE DE CONEXÃO COM SVRS")
print("="*80)

url = 'https://cte.svrs.rs.gov.br/ws/CteRecepcaoEvento/CteRecepcaoEvento.asmx'
print(f"\nURL: {url}")

# XML mínimo
evento_xml = """<evento xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
<infEvento>
<cOrgao>51</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>{}</CNPJ>
<chCTe>51251259126255000148570010000734411000948563</chCTe>
<dhEvento>2026-01-05T20:00:00-03:00</dhEvento>
<tpEvento>610110</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Prestacao do Servico em Desacordo</descEvento>
<xJust>TESTE DE CONEXAO COM CERTIFICADO</xJust>
</detEvento>
</infEvento>
</evento>""".format(cnpj or '00000000000000')

soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
<soap12:Body>
<cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento">{evento_xml}</cteDadosMsg>
</soap12:Body>
</soap12:Envelope>"""

headers = {
    'Content-Type': 'application/soap+xml; charset=utf-8',
    'SOAPAction': '"http://www.portalfiscal.inf.br/cte/wsdl/CteRecepcaoEvento/cteRecepcaoEvento"',
}

print("\nEnviando requisição COM certificado...")
print(f"CNPJ no XML: {cnpj or '00000000000000'}")

try:
    response = requests_pkcs12.post(
        url,
        data=soap_envelope.encode('utf-8'),
        headers=headers,
        pkcs12_filename=cert_path,
        pkcs12_password=cert_password,
        verify=False,
        timeout=30
    )
    
    print(f"\n✓ Status HTTP: {response.status_code}")
    print(f"✓ Tamanho da resposta: {len(response.content)} bytes")
    
    if response.status_code == 200:
        print("\n✓ SUCESSO! Resposta:")
        print(response.content.decode('utf-8', errors='ignore')[:500])
    elif response.status_code == 403:
        print("\n⚠️  HTTP 403 - Certificado não autorizado para esta operação")
    elif response.status_code == 404:
        print("\n✗ HTTP 404 - Recurso não encontrado")
        print("\nResposta:")
        print(response.content.decode('utf-8', errors='ignore'))
    elif response.status_code == 500:
        print("\n⚠️  HTTP 500 - Erro no servidor")
        print("\nResposta:")
        print(response.content.decode('utf-8', errors='ignore')[:1000])
    
except Exception as e:
    print(f"\n✗ Erro: {e}")

print("\n" + "="*80)
print("TESTE CONCLUÍDO")
print("="*80)
