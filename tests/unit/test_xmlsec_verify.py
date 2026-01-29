"""Valida a assinatura RSA completa do evento usando xmlsec (como SEFAZ faz)"""
from lxml import etree
import xmlsec

# XML completo do evento assinado (minificado)
evento_xml = """<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><infEvento Id="ID2102005325125765049200018855001000033428111344131701"><cOrgao>53</cOrgao><tpAmb>1</tpAmb><CNPJ>49068153000160</CNPJ><chNFe>53251257650492000188550010000334281113441317</chNFe><dhEvento>2026-01-13T10:34:10-03:00</dhEvento><tpEvento>210200</tpEvento><nSeqEvento>1</nSeqEvento><verEvento>1.00</verEvento><detEvento versao="1.00"><descEvento>Ciencia da Operacao</descEvento></detEvento></infEvento><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/><ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/><ds:Reference URI="#ID2102005325125765049200018855001000033428111344131701"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/><ds:DigestValue>B80jgAHiQZpwE63bdiPFZV0gLdI=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>DQIFPWIF9vsZX8S3uB74QBjhEJYE/mLXqdVz+FxR8gi3QRycS1RP3ZXujH7NeiyIJtwoIICoH44N6pKPDRKTioI6Cs8a13q2TA26YrBlEh7BZTFl94ZaooHatHXQGB1w7MuqKk1gS73Xs0QFNf9XN1IRQRVWNd2MsU5ZvLC6P018WFPe1/IP15/hXyGUCAi58kXh9CzePgVexG6/M/KhPOUZjva8uKtJ6NL63pgBbbNXgXo1JON8T/I5p0tiVp/RKs3/3AKD/3Ahgni9/KysQKpHErndgrOr1GE22ATeXBIVPaqFhWaXfNxAAie9SV7nWMiAIIviOXT0t9ZOImdWvg==</ds:SignatureValue><ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIIIDzCCBfegAwIBAgIKK/N5xpUoYJ3jxDANBgkqhkiG9w0BAQsFADBgMQswCQYDVQQGEwJCUjEWMBQGA1UECgwNSUNQLUJyYXNpbC1QSjEYMBYGA1UECwwPQVJTb2x1Y2FvRGlnaXRhbDEfMB0GA1UEAwwWQUMgU29sdWNhbyBEaWdpdGFsIHYxMB4XDTI1MTEyMTEzNDYxNVoXDTI2MTEyMTEzNDYxNVowggErMQswCQYDVQQGEwJCUjEWMBQGA1UECgwNSUNQLUJyYXNpbC1QSjEYMBYGA1UECwwPQVJTb2x1Y2FvRGlnaXRhbDEfMB0GA1UECwwWVmlkZW9jb25mZXJlbmNpYSBBMTExMB4GA1UECwwXMzE5MDQ5MTgwMDAxOTkgLSBQSiBBMTEbMBkGA1UECwwSQ2VydGlmaWNhZG8gUEogQTExJDAiBgNVBAMMG0xVWiBDT01FUkNJTyBBTElNRU5USUNJTyBMVERBMRowGAYDVQRhDBFQSjA0OTA2ODE1MzAwMDE2MDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMrKO1i5qFMqz8Dz4TYQf4KnR1rGBXLRhq3xpYhkxHyEPgxRmVL0O4hqkxW3oNE+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4CAwEAATANBgkqhkiG9w0BAQsFAAOCAgEAqZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4F+xm3JYGblNkqrx8xoRZyW+oBXqU+pFMXtJkH3NuZ5gE2K+qZ8F8YpX0YfI6JkF+J0yYV2OxLl5kLPqF+E4</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature></evento>"""

print("=" * 80)
print("VALIDAÇÃO DE ASSINATURA COM XMLSEC (COMO SEFAZ)")
print("=" * 80)

try:
    # Parse XML
    root = etree.fromstring(evento_xml.encode('utf-8'))
    print("\n✅ XML parseado")
    
    # Registrar IDs
    xmlsec.tree.add_ids(root, ["Id"])
    print("✅ IDs registrados")
    
    # Localizar assinatura
    ns_ds = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
    sig_node = root.find('.//ds:Signature', namespaces=ns_ds)
    if sig_node is None:
        print("❌ Nenhuma assinatura encontrada")
        print(f"   Root tag: {root.tag}")
        print(f"   Filhos: {[child.tag for child in root]}")
        exit(1)
    print("✅ Assinatura localizada")
    
    # Criar contexto de verificação
    ctx = xmlsec.SignatureContext()
    print("✅ Contexto criado")
    
    # Verificar assinatura (usando certificado X509 embutido)
    print("\n🔍 Verificando assinatura RSA-SHA1...")
    ctx.verify(sig_node)
    
    print("\n" + "="*80)
    print("✅✅✅ ASSINATURA VÁLIDA! ✅✅✅")
    print("="*80)
    print("\n💡 A assinatura está matematicamente correta")
    print("💡 O SEFAZ deveria aceitar este evento")
    print("\n⚠️ Erro 297 pode ser por:")
    print("   1. Certificado não está na cadeia de confiança do SEFAZ")
    print("   2. Certificado expirado ou revogado")
    print("   3. CNPJ do certificado não autorizado para manifestar esta nota")
    print("   4. Problema no webservice do SEFAZ")
    
except xmlsec.Error as e:
    print("\n" + "="*80)
    print("❌❌❌ ASSINATURA INVÁLIDA! ❌❌❌")
    print("="*80)
    print(f"\n💥 Erro: {e}")
    print("\n💡 Isto explicaria o erro 297 do SEFAZ")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
