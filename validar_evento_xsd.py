"""Script para validar XML de evento contra XSD"""
import sys
from lxml import etree
from pathlib import Path

# Define paths
xsd_path = Path(__file__).parent / "Arquivo_xsd" / "leiauteEvento_v1.00.xsd"

# XML de teste (evento assinado conforme gerado pelo sistema)
xml_test = """<?xml version="1.0" encoding="utf-8"?>
<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <infEvento Id="ID2102005325125765049200018855001000033428111344131701">
    <cOrgao>53</cOrgao>
    <tpAmb>1</tpAmb>
    <CNPJ>49068153000160</CNPJ>
    <chNFe>53251257650492000188550010000334281113441317</chNFe>
    <dhEvento>2026-01-13T13:03:32-03:00</dhEvento>
    <tpEvento>210200</tpEvento>
    <nSeqEvento>1</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Ciencia da Operacao</descEvento>
    </detEvento>
  </infEvento>
  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
    <SignedInfo>
      <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
      <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
      <Reference URI="#ID2102005325125765049200018855001000033428111344131701">
        <Transforms>
          <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
          <Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
        </Transforms>
        <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
        <DigestValue>TEST</DigestValue>
      </Reference>
    </SignedInfo>
    <SignatureValue>TEST</SignatureValue>
    <KeyInfo>
      <X509Data>
        <X509Certificate>TEST</X509Certificate>
      </X509Data>
    </KeyInfo>
  </Signature>
</evento>"""

try:
    print("=" * 80)
    print("VALIDAÇÃO XSD DE EVENTO NF-e")
    print("=" * 80)
    
    # Carrega XSD
    print(f"\n1. Carregando XSD: {xsd_path}")
    if not xsd_path.exists():
        print(f"❌ ERRO: XSD não encontrado em {xsd_path}")
        sys.exit(1)
    
    xmlschema_doc = etree.parse(str(xsd_path))
    xmlschema = etree.XMLSchema(xmlschema_doc)
    print("✅ XSD carregado com sucesso")
    
    # Parse XML
    print("\n2. Parseando XML de teste")
    xml_doc = etree.fromstring(xml_test.encode('utf-8'))
    print("✅ XML parseado com sucesso")
    
    # Valida
    print("\n3. Validando XML contra XSD")
    is_valid = xmlschema.validate(xml_doc)
    
    if is_valid:
        print("✅ XML VÁLIDO CONFORME XSD!")
    else:
        print("❌ XML INVÁLIDO!")
        print("\nErros encontrados:")
        for error in xmlschema.error_log:
            print(f"  - Linha {error.line}: {error.message}")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n❌ ERRO na validação: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
