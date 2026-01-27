"""Teste completo de assinatura - identifica problema raiz"""
from lxml import etree
import xmlsec
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12

print("="*80)
print("TESTE COMPLETO DE ASSINATURA - DIAGNÓSTICO")
print("="*80)

# 1. Carregar certificado
cert_path = Path("certificados/LUZ COMERCIO ALIMENTICIO LTDA_49068153000160.pfx")
senha = input("\nDigite a senha do certificado: ").encode()

with open(cert_path, 'rb') as f:
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        f.read(), senha, default_backend()
    )

print(f"\n✅ Certificado: {certificate.subject}")

# 2. Criar evento simples
ns = "http://www.portalfiscal.inf.br/nfe"
evento = etree.Element(f"{{{ns}}}evento", versao="1.00", nsmap={None: ns})
inf = etree.SubElement(evento, f"{{{ns}}}infEvento", Id="ID210200TESTE123456789012345678901234567890")

for tag, text in [
    ("cOrgao", "53"),
    ("tpAmb", "1"),
    ("CNPJ", "49068153000160"),
    ("chNFe", "53251257650492000188550010000334281113441317"),
    ("dhEvento", "2026-01-13T12:00:00-03:00"),
    ("tpEvento", "210200"),
    ("nSeqEvento", "1"),
    ("verEvento", "1.00"),
]:
    e = etree.SubElement(inf, f"{{{ns}}}{tag}")
    e.text = text

det = etree.SubElement(inf, f"{{{ns}}}detEvento", versao="1.00")
desc = etree.SubElement(det, f"{{{ns}}}descEvento")
desc.text = "Ciencia da Operacao"

print("\n✅ Evento criado")

# 3. Limpar espaços (como fazemos no código real)
for elem in evento.iter():
    if elem.text and not elem.text.strip():
        elem.text = None
    if elem.tail and not elem.tail.strip():
        elem.tail = None

# 4. Registrar IDs
xmlsec.tree.add_ids(evento, ["Id"])
print("✅ IDs registrados")

# 5. Template de assinatura
sig = xmlsec.template.create(evento, xmlsec.Transform.C14N, xmlsec.Transform.RSA_SHA1, ns="ds")
evento.append(sig)

# 6. Reference
ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA1, uri="#ID210200TESTE123456789012345678901234567890")
xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)

# 7. KeyInfo
ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

print("✅ Template criado")

# 8. Preparar chave/cert
key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

# 9. TESTE 1: Assinar com PEM
print("\n" + "="*80)
print("TESTE: Assinatura com certificado PEM")
print("="*80)

ctx = xmlsec.SignatureContext()
ctx.key = xmlsec.Key.from_memory(key_pem, xmlsec.KeyFormat.PEM, None)
ctx.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)

sig_node = evento.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
ctx.sign(sig_node)
print("✅ Assinado")

# Verificar
print("\n🔍 Verificando assinatura...")
try:
    # Re-registrar IDs para verificação
    xmlsec.tree.add_ids(evento, ["Id"])
    
    ctx_verify = xmlsec.SignatureContext()
    ctx_verify.verify(sig_node)
    
    print("✅✅✅ ASSINATURA VÁLIDA! ✅✅✅")
    print("\n💡 A assinatura está correta")
    print("💡 O problema está em outro lugar (serialização, envelope, etc)")
    
except xmlsec.Error as e:
    print(f"❌ ASSINATURA INVÁLIDA: {e}")
    print("\n💡 Problema NA CRIAÇÃO da assinatura")
    print("Possíveis causas:")
    print("  1. Certificado não corresponde à chave privada")
    print("  2. Transforms incorretos")
    print("  3. IDs não registrados corretamente")
    print("  4. Problema no xmlsec (versão, compilação)")

# Mostrar XML final
print("\n" + "="*80)
print("XML ASSINADO:")
print("="*80)
xml_str = etree.tostring(evento, encoding='unicode', pretty_print=True)
print(xml_str[:1000])

print("\n" + "="*80)
