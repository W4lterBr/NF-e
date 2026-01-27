"""Simula o que SEFAZ faz: recebe XML assinado e recalcula DigestValue"""
from lxml import etree
from hashlib import sha1
import base64

# XML completo do evento assinado (do log)
evento_completo = """<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><infEvento Id="ID2102005325125765049200018855001000033428111344131701"><cOrgao>53</cOrgao><tpAmb>1</tpAmb><CNPJ>49068153000160</CNPJ><chNFe>53251257650492000188550010000334281113441317</chNFe><dhEvento>2026-01-13T10:34:10-03:00</dhEvento><tpEvento>210200</tpEvento><nSeqEvento>1</nSeqEvento><verEvento>1.00</verEvento><detEvento versao="1.00"><descEvento>Ciencia da Operacao</descEvento></detEvento></infEvento><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/><ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/><ds:Reference URI="#ID2102005325125765049200018855001000033428111344131701"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/><ds:DigestValue>B80jgAHiQZpwE63bdiPFZV0gLdI=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>DQIFPWIF9vsZX8S3uB74QBjhEJYE/mLXqdVz+FxR8gi3QRycS1RP3ZXujH7NeiyI
JtwoIICoH44N6pKPDRKTioI6Cs8a13q2TA26YrBlEh7BZTFl94ZaooHatHXQGB1w
7MuqKk1gS73Xs0QFNf9XN1IRQRVWNd2MsU5ZvLC6P018WFPe1/IP15/hXyGUCAi5
8kXh9CzePgVexG6/M/KhPOUZjva8uKtJ6NL63pgBbbNXgXo1JON8T/I5p0tiVp/R
Ks3/3AKD/3Ahgni9/KysQKpHErndgrOr1GE22ATeXBIVPaqFhWaXfNxAAie9SV7n
WMiAIIviOXT0t9ZOImdWvg==</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIIIDzCCBfegAwIBAgIKK</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature></evento>"""

print("=" * 80)
print("SIMULANDO VALIDAÇÃO DO SEFAZ")
print("=" * 80)

# Parse do XML recebido
root = etree.fromstring(evento_completo.encode('utf-8'))
print(f"\n✅ XML parseado: {root.tag}")

# Localiza infEvento
ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
inf_evento = root.find('.//nfe:infEvento', namespaces=ns)
print(f"✅ infEvento encontrado: Id={inf_evento.get('Id')}")

# Aplicar transformações conforme especificado na assinatura:
# 1. Enveloped Signature (remove o elemento Signature)
# 2. C14N (canonicalização)

print("\n🔧 Aplicando transforms:")
print("   1. Enveloped Signature (remover <Signature>)")
print("   2. C14N Canonicalization")

# Clonar infEvento para não modificar original
inf_evento_copy = etree.fromstring(etree.tostring(inf_evento))

# Não precisa remover Signature (ela não está dentro de infEvento)

# Canonicalizar
c14n_bytes = etree.tostring(inf_evento_copy, method='c14n', exclusive=False)
print(f"\n📝 XML Canonicalizado:")
print(c14n_bytes.decode('utf-8'))
print(f"\n📏 Tamanho: {len(c14n_bytes)} bytes")

# Calcular DigestValue
digest = sha1(c14n_bytes).digest()
digest_b64 = base64.b64encode(digest).decode('ascii')

print(f"\n🔐 DigestValue recalculado:  {digest_b64}")
print(f"   DigestValue na assinatura: B80jgAHiQZpwE63bdiPFZV0gLdI=")

if digest_b64 == "B80jgAHiQZpwE63bdiPFZV0gLdI=":
    print("\n✅ ASSINATURA VÁLIDA! SEFAZ deveria aceitar")
else:
    print("\n❌ ASSINATURA INVÁLIDA! Erro 297")
    print("\n💡 Possíveis causas:")
    print("   - infEvento foi modificado após assinatura")
    print("   - Namespace declarations diferentes")
    print("   - SEFAZ está usando algoritmo diferente")
    
print("\n" + "=" * 80)
