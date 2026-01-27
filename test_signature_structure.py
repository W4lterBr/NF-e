"""Valida se a ESTRUTURA da assinatura está conforme XSD xmldsig"""
from lxml import etree
from pathlib import Path

# XML da assinatura (do último log)
signature_xml = """<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
<ds:SignedInfo>
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
<ds:Reference URI="#ID2102005325125765049200018855001000033428111344131701">
<ds:Transforms>
<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
<ds:Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
</ds:Transforms>
<ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
<ds:DigestValue>dNWPbvjipb3d4OzC39FVwt1+0jg=</ds:DigestValue>
</ds:Reference>
</ds:SignedInfo>
<ds:SignatureValue>eQD1a0GlacH4rBiy7TiVQnbQ57F22I+dU7ShKBDEAWiEFAISWXgjXP1nUzHEMnHk
jtBwJSQ2Tv2wz4XCTrbaZb6UoQgLQIdoeA7DOQ1/BafbCK2MN8B1kNN7G2E7hTMV
ReB1f1FpHFxy4ewCXYA9N9NaT0252tkGGvNEXC9h0GE4eQZgyzvjjBNhtLig2Bxl
rkNVPLT+Q7rJEQProZviI+PnVq/J4bPE8CW92+T0Er7m80MxdQ/SyrE7J+Q8/zI0
PaAnwEnb2IfQA3+ctBZ7egRSnEWfLmFKibgXqqC+TToPE0oWeCV2giHDfK2dAhTp
LYK4p6reIAINBjtfgGh1qQ==</ds:SignatureValue>
<ds:KeyInfo>
<ds:X509Data>
<ds:X509Certificate>MIIIDzCCBfegAwIBAgIKK</ds:X509Certificate>
</ds:X509Data>
</ds:KeyInfo>
</ds:Signature>"""

print("=" * 80)
print("VALIDAÇÃO XSD DA ESTRUTURA DA ASSINATURA")
print("=" * 80)

# Parse da assinatura
sig_root = etree.fromstring(signature_xml.encode('utf-8'))
print(f"\n✅ Assinatura parseada: {sig_root.tag}")

# Carregar XSD
xsd_path = Path(__file__).parent / "Arquivo_xsd" / "xmldsig-core-schema_v1.01.xsd"
print(f"\n📋 Carregando XSD: {xsd_path.name}")

try:
    with open(xsd_path, 'rb') as f:
        schema_doc = etree.parse(f, base_url=str(xsd_path.parent) + '/')
    schema = etree.XMLSchema(schema_doc)
    print("✅ XSD carregado")
    
    # Validar estrutura
    print("\n🔍 Validando estrutura da assinatura contra XSD...")
    if schema.validate(sig_root):
        print("\n" + "=" * 80)
        print("✅✅✅ ESTRUTURA DA ASSINATURA: VÁLIDA ✅✅✅")
        print("=" * 80)
        print("\n💡 A assinatura tem ESTRUTURA correta conforme XML Signature")
        print("💡 O problema do erro 297 NÃO é estrutural")
        print("\n⚠️ Possíveis causas do erro 297:")
        print("   1. DigestValue calculado diferente (problema na canonização)")
        print("   2. SignatureValue inválida (chave privada errada)")
        print("   3. Certificado X509 não corresponde à chave privada")
        print("   4. Certificado não autorizado pelo SEFAZ")
    else:
        print("\n" + "=" * 80)
        print("❌ ESTRUTURA DA ASSINATURA: INVÁLIDA")
        print("=" * 80)
        print("\nErros encontrados:")
        for i, erro in enumerate(schema.error_log, 1):
            print(f"\n{i}. Linha {erro.line}:")
            print(f"   {erro.message}")
        print("\n💡 Isto explicaria o erro 297!")
        
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
