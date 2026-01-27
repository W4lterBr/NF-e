"""Debug completo da assinatura - identifica o problema exato"""
from lxml import etree
from pathlib import Path
import xmlsec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12

print("=" * 80)
print("DEBUG COMPLETO DA ASSINATURA XMLSEC")
print("=" * 80)

# 1. Carregar certificado
cert_path = Path("certificados/LUZ COMERCIO ALIMENTICIO LTDA_49068153000160.pfx")
password = input("\nSenha do certificado: ").encode()

with open(cert_path, 'rb') as f:
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        f.read(), password, default_backend()
    )

print(f"\n✅ Certificado carregado: {certificate.subject}")

# 2. Criar XML de evento simples (dhEvento FIXO para reproduzibilidade)
evento_xml = etree.Element(
    "{http://www.portalfiscal.inf.br/nfe}evento",
    versao="1.00",
    nsmap={None: 'http://www.portalfiscal.inf.br/nfe'}
)

inf_evento = etree.SubElement(
    evento_xml,
    "{http://www.portalfiscal.inf.br/nfe}infEvento",
    Id="ID2102005325125765049200018855001000033428111344131701"
)

# Campos do infEvento
for tag, text in [
    ("cOrgao", "53"),
    ("tpAmb", "1"),
    ("CNPJ", "49068153000160"),
    ("chNFe", "53251257650492000188550010000334281113441317"),
    ("dhEvento", "2026-01-13T12:00:00-03:00"),  # FIXO
    ("tpEvento", "210200"),
    ("nSeqEvento", "1"),
    ("verEvento", "1.00"),
]:
    elem = etree.SubElement(inf_evento, f"{{http://www.portalfiscal.inf.br/nfe}}{tag}")
    elem.text = text

det_evento = etree.SubElement(
    inf_evento,
    "{http://www.portalfiscal.inf.br/nfe}detEvento",
    versao="1.00"
)
desc = etree.SubElement(det_evento, "{http://www.portalfiscal.inf.br/nfe}descEvento")
desc.text = "Ciencia da Operacao"

print("\n✅ XML criado")
print(etree.tostring(evento_xml, encoding='unicode', pretty_print=True)[:500])

# 3. Limpar espaços
for element in evento_xml.iter("*"):
    if element.text is not None and not element.text.strip():
        element.text = None
    if element.tail is not None and not element.tail.strip():
        element.tail = None

# 4. Registrar IDs
xmlsec.tree.add_ids(evento_xml, ["Id"])
print("✅ IDs registrados")

# 5. Criar template de assinatura
signature_node = xmlsec.template.create(
    evento_xml,
    xmlsec.Transform.C14N,
    xmlsec.Transform.RSA_SHA1,
    ns="ds"
)
evento_xml.append(signature_node)

# 6. Adicionar Reference
ref = xmlsec.template.add_reference(
    signature_node,
    xmlsec.Transform.SHA1,
    uri="#ID2102005325125765049200018855001000033428111344131701"
)
xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)

# 7. Adicionar KeyInfo
key_info = xmlsec.template.ensure_key_info(signature_node)
xmlsec.template.add_x509_data(key_info)

print("✅ Template criado")

# 8. Preparar chave/certificado
private_key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
cert_pem = certificate.public_bytes(serialization.Encoding.PEM)

# 9. ASSINAR - Método 1: PEM
print("\n" + "=" * 80)
print("TESTE 1: Assinatura com certificado PEM")
print("=" * 80)
try:
    ctx1 = xmlsec.SignatureContext()
    ctx1.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
    ctx1.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)
    
    # Copiar XML para não modificar original
    xml_copy1 = etree.fromstring(etree.tostring(evento_xml))
    sig_node1 = xml_copy1.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    
    ctx1.sign(sig_node1)
    print("✅ Assinatura criada")
    
    # Tentar verificar
    xmlsec.tree.add_ids(xml_copy1, ["Id"])
    ctx1_verify = xmlsec.SignatureContext()
    ctx1_verify.verify(sig_node1)
    print("✅ VERIFICAÇÃO: VÁLIDA (PEM)")
    
except xmlsec.Error as e:
    print(f"❌ VERIFICAÇÃO: INVÁLIDA (PEM) - {e}")
except Exception as e:
    print(f"❌ ERRO: {e}")

# 10. ASSINAR - Método 2: DER
print("\n" + "=" * 80)
print("TESTE 2: Assinatura com certificado DER")
print("=" * 80)
try:
    cert_der = certificate.public_bytes(serialization.Encoding.DER)
    
    ctx2 = xmlsec.SignatureContext()
    ctx2.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
    ctx2.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
    
    # Copiar XML
    xml_copy2 = etree.fromstring(etree.tostring(evento_xml))
    sig_node2 = xml_copy2.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
    
    ctx2.sign(sig_node2)
    print("✅ Assinatura criada")
    
    # Tentar verificar
    xmlsec.tree.add_ids(xml_copy2, ["Id"])
    ctx2_verify = xmlsec.SignatureContext()
    ctx2_verify.verify(sig_node2)
    print("✅ VERIFICAÇÃO: VÁLIDA (DER)")
    
except xmlsec.Error as e:
    print(f"❌ VERIFICAÇÃO: INVÁLIDA (DER) - {e}")
except Exception as e:
    print(f"❌ ERRO: {e}")

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("Se ambos falharam: problema na configuração xmlsec ou certificado")
print("Se um passou: usar o método que funcionou")
print("=" * 80)
