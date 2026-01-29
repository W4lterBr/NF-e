# -*- coding: utf-8 -*-
"""
Teste de assinatura usando signxml (alternativa ao xmlsec)
signxml é mais moderno e pode ter melhor compatibilidade com SEFAZ
"""
import sys
from pathlib import Path
from lxml import etree
from datetime import datetime
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend

# Adicionar módulos
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from modules.manifestacao_service import ManifestacaoService
from modules.database import DatabaseManager

print("=" * 80)
print("TESTE DE ASSINATURA COM SIGNXML")
print("=" * 80)

# 1. Carregar certificado
db = DatabaseManager(BASE_DIR / "notas.db")
certs = db.load_certificates()
cert = next((c for c in certs if c['cnpj_cpf'] == '49068153000160'), None)

if not cert:
    print("ERRO: Certificado nao encontrado")
    exit(1)

cert_path = cert['caminho']
senha = cert['senha']

print(f"\n1. Carregando certificado...")
print(f"   Caminho: {cert_path}")

with open(cert_path, 'rb') as f:
    pfx_data = f.read()

private_key, certificate, _ = pkcs12.load_key_and_certificates(
    pfx_data, senha.encode(), default_backend()
)

print(f"   OK - Certificado carregado")

# 2. Criar evento XML
chave = "53251257650492000188550010000334281113441317"
cnpj = "49068153000160"

print(f"\n2. Criando XML do evento...")

ns = "http://www.portalfiscal.inf.br/nfe"
id_evento = f"ID210200{chave}01"

# infEvento
inf_evento = etree.Element(f"{{{ns}}}infEvento", attrib={"Id": id_evento})
etree.SubElement(inf_evento, f"{{{ns}}}cOrgao").text = "53"
etree.SubElement(inf_evento, f"{{{ns}}}tpAmb").text = "1"
etree.SubElement(inf_evento, f"{{{ns}}}CNPJ").text = cnpj
etree.SubElement(inf_evento, f"{{{ns}}}chNFe").text = chave
etree.SubElement(inf_evento, f"{{{ns}}}dhEvento").text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
etree.SubElement(inf_evento, f"{{{ns}}}tpEvento").text = "210200"
etree.SubElement(inf_evento, f"{{{ns}}}nSeqEvento").text = "1"
etree.SubElement(inf_evento, f"{{{ns}}}verEvento").text = "1.00"

det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", attrib={"versao": "1.00"})
etree.SubElement(det_evento, f"{{{ns}}}descEvento").text = "Ciencia da Operacao"

# evento
evento = etree.Element(f"{{{ns}}}evento", attrib={"versao": "1.00"})
evento.append(inf_evento)

print(f"   OK - XML criado (ID: {id_evento})")

# 3. Assinar com signxml
print(f"\n3. Assinando com signxml...")

try:
    # signxml usa SHA256 por padrao (mais seguro que SHA1)
    # Vamos testar se SEFAZ aceita SHA256
    signer = XMLSigner(
        method=methods.enveloped,
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    )
    
    signed_root = signer.sign(
        evento,
        key=private_key,
        cert=[certificate],  # Lista de certificados
        reference_uri=f"#{id_evento}"
    )
    
    print(f"   OK - XML assinado com signxml")
    
    # Verificar assinatura
    from signxml import XMLVerifier
    verifier = XMLVerifier()
    try:
        verified_data = verifier.verify(signed_root, x509_cert=certificate)
        print(f"   OK - Assinatura VALIDA (verificacao local)")
    except Exception as e:
        print(f"   ERRO - Assinatura INVALIDA: {e}")
    
    # Mostrar XML assinado
    print(f"\n4. XML ASSINADO:")
    xml_assinado = etree.tostring(signed_root, encoding='unicode', pretty_print=False)
    print(xml_assinado[:1000] + "...")
    
    # Verificar estrutura da assinatura
    ns_ds = "http://www.w3.org/2000/09/xmldsig#"
    signature = signed_root.find(f".//{{{ns_ds}}}Signature")
    if signature is not None:
        print(f"\n5. ESTRUTURA DA ASSINATURA:")
        
        # DigestValue
        digest = signature.findtext(f".//{{{ns_ds}}}DigestValue")
        print(f"   DigestValue: {digest[:50]}...")
        
        # SignatureValue
        sig_value = signature.findtext(f".//{{{ns_ds}}}SignatureValue")
        print(f"   SignatureValue: {sig_value[:50] if sig_value else 'NAO ENCONTRADO'}...")
        
        # Certificado X509
        x509_cert = signature.findtext(f".//{{{ns_ds}}}X509Certificate")
        if x509_cert:
            print(f"   X509Certificate: {len(x509_cert)} caracteres")
        else:
            print(f"   X509Certificate: NAO ENCONTRADO")
    
    print(f"\n{'=' * 80}")
    print("CONCLUSAO:")
    print(f"{'=' * 80}")
    print("Se signxml validou localmente mas xmlsec nao:")
    print("  -> Problema pode ser incompatibilidade entre bibliotecas")
    print("  -> Testar envio para SEFAZ com assinatura signxml")
    print("  -> Se SEFAZ aceitar -> usar signxml em producao")
    
except Exception as e:
    print(f"   ERRO ao assinar: {e}")
    import traceback
    traceback.print_exc()
