"""
Script para testar validação de XML de manifestação contra XSD.
"""

from lxml import etree
import os

def validar_xml_manifestacao(xml_string):
    """Valida XML de manifestação contra o XSD oficial."""
    
    # Caminho base dos XSDs
    xsd_dir = os.path.join(os.path.dirname(__file__), "Arquivo_xsd")
    
    # Carrega o XSD do evento
    xsd_path = os.path.join(xsd_dir, "leiauteEvento_v1.00.xsd")
    
    try:
        # Parse do XSD
        with open(xsd_path, 'r', encoding='utf-8') as f:
            xsd_doc = etree.parse(f)
        xsd_schema = etree.XMLSchema(xsd_doc)
        
        # Parse do XML
        xml_doc = etree.fromstring(xml_string.encode('utf-8'))
        
        # Valida
        is_valid = xsd_schema.validate(xml_doc)
        
        if is_valid:
            print("✅ XML VÁLIDO conforme XSD!")
            return True
        else:
            print("❌ XML INVÁLIDO conforme XSD!")
            print("\n📋 Erros encontrados:")
            for i, error in enumerate(xsd_schema.error_log, 1):
                print(f"\n  {i}. Linha {error.line}, Coluna {error.column}")
                print(f"     {error.message}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao validar: {e}")
        return False

def extrair_envevento_de_soap(soap_xml):
    """Extrai apenas o envEvento do envelope SOAP para validação."""
    try:
        # Parse SOAP
        soap_doc = etree.fromstring(soap_xml.encode('utf-8'))
        
        # Namespace SOAP
        namespaces = {
            'soap12': 'http://www.w3.org/2003/05/soap-envelope',
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
        
        # Busca envEvento dentro do SOAP Body
        env_evento = soap_doc.xpath('//nfe:envEvento', namespaces=namespaces)[0]
        
        # Converte de volta para string
        xml_str = etree.tostring(env_evento, encoding='utf-8', xml_declaration=True).decode('utf-8')
        
        print("📄 XML extraído do SOAP:")
        print(xml_str)
        print("\n" + "="*80 + "\n")
        
        return xml_str
        
    except Exception as e:
        print(f"❌ Erro ao extrair envEvento: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    # Exemplo de uso com o último log
    print("🔍 Testando validação XSD de manifestação...\n")
    
    # XML de teste (copie do log)
    xml_test = """<?xml version="1.0" encoding="utf-8"?>
<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
<idLote>1</idLote>
<evento versao="1.00">
<infEvento Id="ID21021035260172381189001001550010083154761637954119001">
<cOrgao>35</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>01773924000193</CNPJ>
<chNFe>35260172381189001001550010083154761637954119</chNFe>
<dhEvento>2026-01-07T11:12:48-03:00</dhEvento>
<tpEvento>210210</tpEvento>
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
<Reference URI="#ID21021035260172381189001001550010083154761637954119001">
<Transforms>
<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
</Transforms>
<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
<DigestValue>e5xtQtoqyr7rg4ke0+j2NgdahqY=</DigestValue>
</Reference>
</SignedInfo>
<SignatureValue>test</SignatureValue>
<KeyInfo>
<X509Data>
<X509Certificate>test</X509Certificate>
</X509Data>
</KeyInfo>
</Signature>
</evento>
</envEvento>"""
    
    # Se passar SOAP como argumento, extrai
    if len(sys.argv) > 1 and sys.argv[1] == '--from-soap':
        # Implementar extração de SOAP dos logs
        pass
    
    # Valida
    validar_xml_manifestacao(xml_test)
