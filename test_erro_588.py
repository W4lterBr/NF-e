"""Valida se há caracteres inválidos no XML (erro 588)"""
from lxml import etree
import re

# XML do SOAP (do log - com quebras de linha)
soap_xml = """<?xml version='1.0' encoding='utf-8'?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope"><soap12:Body><nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"><envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><idLote>1</idLote><evento versao="1.00"><infEvento Id="ID210200"><cOrgao>53</cOrgao></infEvento><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
<ds:SignedInfo>
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
</ds:SignedInfo>
<ds:SignatureValue>p07DX3Quvj9s5VKaqwoXqKKM+uQwmQN9qRmXmtMcCbS0NXZXUnwBCKWDKjihoRzW
Z+TzWXzAFiLbgzFctPZuyOOsOAsK7x7mBMkDKYARc4/8dtK918Qov679JLamZMhn
ppRChiSYI3oUYwPlS2DGSReDnQs/razDTjqVeaU3CdDPQ1R+LqvcLyYS0rgNSZH3</ds:SignatureValue>
<ds:KeyInfo>
<ds:X509Data>
<ds:X509Certificate>MIIIDzCCBfegAwIBAgIKK/N5xpUoYJ3jxDANBgkqhkiG9w0BAQsFADBgMQswCQYD
VQQGEwJCUjEWMBQGA1UECgwNSUNQLUJyYXNpbC1QSjEYMBYGA1UECwwPQVJTb2x1</ds:X509Certificate>
</ds:X509Data>
</ds:KeyInfo>
</ds:Signature></evento></envEvento></nfeDadosMsg></soap12:Body></soap12:Envelope>"""

print("=" * 80)
print("DETECTOR DE CARACTERES DE EDIÇÃO (ERRO 588)")
print("=" * 80)

root = etree.fromstring(soap_xml.encode('utf-8'))
print("\n✅ XML parseado")

problemas = []

# Verifica quebras de linha em elementos de texto
for elem in root.iter():
    if elem.text and ('\n' in elem.text or '\r' in elem.text or '\t' in elem.text):
        tag_clean = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        preview = elem.text[:50].replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        problemas.append(f"  • {tag_clean}: contém quebras de linha/tabs")
        print(f"⚠️ {tag_clean}: {preview}...")

if problemas:
    print("\n" + "=" * 80)
    print("❌ CARACTERES DE EDIÇÃO DETECTADOS (Causarão erro 588)")
    print("=" * 80)
    print("\nProblemas encontrados:")
    for p in problemas:
        print(p)
    print("\n💡 Solução: Remover \\n, \\r, \\t do conteúdo texto")
    print("   elem.text = ''.join(elem.text.split())")
else:
    print("\n" + "=" * 80)
    print("✅ NENHUM CARACTERE DE EDIÇÃO")
    print("=" * 80)
    print("\n💡 XML está limpo e pronto para SEFAZ")

print("\n" + "=" * 80)
