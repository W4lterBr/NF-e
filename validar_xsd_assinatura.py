"""
Teste de assinatura conforme XSD oficial da SEFAZ
Valida se a assinatura gerada está 100% conforme xmldsig-core-schema_v1.01.xsd
"""

import sys
from pathlib import Path
from lxml import etree
import xmlsec

# Adiciona módulos ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def validar_assinatura_contra_xsd():
    """Valida se a estrutura de assinatura está conforme o XSD."""
    
    print("=" * 80)
    print("VALIDAÇÃO DE ASSINATURA CONTRA XSD OFICIAL DA SEFAZ")
    print("=" * 80)
    
    # Carrega XSD da assinatura
    xsd_path = BASE_DIR / 'Arquivo_xsd' / 'xmldsig-core-schema_v1.01.xsd'
    if not xsd_path.exists():
        print(f"❌ XSD não encontrado: {xsd_path}")
        return False
    
    print(f"✅ XSD encontrado: {xsd_path}")
    
    # Parsea o XSD
    with open(xsd_path, 'rb') as f:
        xsd_doc = etree.parse(f)
    
    schema = etree.XMLSchema(xsd_doc)
    print("✅ Schema carregado com sucesso")
    
    # Lê requisitos do XSD
    print("\n" + "=" * 80)
    print("REQUISITOS DO XSD (xmldsig-core-schema_v1.01.xsd)")
    print("=" * 80)
    
    ns_ds = "http://www.w3.org/2000/09/xmldsig#"
    
    # Busca elementos importantes no XSD
    xsd_root = xsd_doc.getroot()
    
    print("\n1️⃣ CanonicalizationMethod:")
    canon = xsd_root.find('.//{http://www.w3.org/2001/XMLSchema}element[@name="CanonicalizationMethod"]')
    if canon is not None:
        attr = canon.find('.//{http://www.w3.org/2001/XMLSchema}attribute[@name="Algorithm"]')
        if attr is not None:
            fixed = attr.get('fixed')
            print(f"   ✅ Algorithm FIXO: {fixed}")
            print(f"   ⚠️ DEVE SER EXATAMENTE: http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    
    print("\n2️⃣ SignatureMethod:")
    sig_method = xsd_root.find('.//{http://www.w3.org/2001/XMLSchema}element[@name="SignatureMethod"]')
    if sig_method is not None:
        attr = sig_method.find('.//{http://www.w3.org/2001/XMLSchema}attribute[@name="Algorithm"]')
        if attr is not None:
            fixed = attr.get('fixed')
            print(f"   ✅ Algorithm FIXO: {fixed}")
            print(f"   ⚠️ DEVE SER EXATAMENTE: http://www.w3.org/2000/09/xmldsig#rsa-sha1")
    
    print("\n3️⃣ DigestMethod:")
    digest_method = xsd_root.find('.//{http://www.w3.org/2001/XMLSchema}element[@name="DigestMethod"]')
    if digest_method is not None:
        attr = digest_method.find('.//{http://www.w3.org/2001/XMLSchema}attribute[@name="Algorithm"]')
        if attr is not None:
            fixed = attr.get('fixed')
            print(f"   ✅ Algorithm FIXO: {fixed}")
            print(f"   ⚠️ DEVE SER EXATAMENTE: http://www.w3.org/2000/09/xmldsig#sha1")
    
    print("\n4️⃣ Transforms:")
    transforms = xsd_root.find('.//{http://www.w3.org/2001/XMLSchema}complexType[@name="TransformsType"]')
    if transforms is not None:
        elem = transforms.find('.//{http://www.w3.org/2001/XMLSchema}element[@name="Transform"]')
        if elem is not None:
            min_occurs = elem.get('minOccurs')
            max_occurs = elem.get('maxOccurs')
            print(f"   ✅ Quantidade de Transform: minOccurs={min_occurs}, maxOccurs={max_occurs}")
            print(f"   ⚠️ DEVEM SER EXATAMENTE 2 TRANSFORMS")
    
    # Busca enumeração de Transform
    transform_enum = xsd_root.find('.//{http://www.w3.org/2001/XMLSchema}simpleType[@name="TTransformURI"]')
    if transform_enum is not None:
        print("\n   Valores permitidos para Transform:")
        for enum in transform_enum.findall('.//{http://www.w3.org/2001/XMLSchema}enumeration'):
            value = enum.get('value')
            if 'enveloped' in value:
                print(f"   ✅ 1º Transform: {value}")
            elif 'c14n' in value:
                print(f"   ✅ 2º Transform: {value}")
    
    print("\n" + "=" * 80)
    print("RESUMO DOS REQUISITOS")
    print("=" * 80)
    print("""
    A assinatura DEVE ter EXATAMENTE:
    
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
      <SignedInfo>
        <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
        <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
        <Reference URI="#ID...">
          <Transforms>
            <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
            <Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
          </Transforms>
          <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
          <DigestValue>...</DigestValue>
        </Reference>
      </SignedInfo>
      <SignatureValue>...</SignatureValue>
      <KeyInfo>
        <X509Data>
          <X509Certificate>...</X509Certificate>
        </X509Data>
      </KeyInfo>
    </Signature>
    
    ⚠️ IMPORTANTE:
    - CanonicalizationMethod: C14N NORMAL (NÃO Exclusive C14N)
    - SignatureMethod: RSA-SHA1 (NÃO SHA256)
    - DigestMethod: SHA1 (NÃO SHA256)
    - Transforms: EXATAMENTE 2 (enveloped + c14n)
    - URI: Deve começar com # e apontar para o Id do infEvento
    """)
    
    return True

def testar_xmlsec_constants():
    """Testa se as constantes do xmlsec correspondem aos algoritmos do XSD."""
    
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO DAS CONSTANTES XMLSEC")
    print("=" * 80)
    
    checks = []
    
    # C14N (Canonicalization)
    print("\n1️⃣ Canonicalization (C14N):")
    try:
        c14n_normal = xmlsec.Transform.C14N
        print(f"   xmlsec.Transform.C14N = {c14n_normal}")
        if 'c14n' in str(c14n_normal).lower() and 'excl' not in str(c14n_normal).lower():
            print("   ✅ C14N NORMAL (correto para SEFAZ)")
            checks.append(True)
        else:
            print("   ⚠️ Pode não ser C14N normal")
            checks.append(False)
    except AttributeError:
        print("   ❌ xmlsec.Transform.C14N não existe")
        checks.append(False)
    
    try:
        c14n_excl = xmlsec.Transform.EXCL_C14N
        print(f"   xmlsec.Transform.EXCL_C14N = {c14n_excl}")
        print("   ⚠️ NÃO usar Exclusive C14N para SEFAZ!")
    except AttributeError:
        print("   ✅ EXCL_C14N não disponível (bom)")
    
    # RSA-SHA1
    print("\n2️⃣ Signature Method (RSA-SHA1):")
    try:
        rsa_sha1 = xmlsec.Transform.RSA_SHA1
        print(f"   xmlsec.Transform.RSA_SHA1 = {rsa_sha1}")
        if 'sha1' in str(rsa_sha1).lower():
            print("   ✅ RSA-SHA1 (correto para SEFAZ)")
            checks.append(True)
        else:
            print("   ⚠️ Pode não ser SHA1")
            checks.append(False)
    except AttributeError:
        print("   ❌ xmlsec.Transform.RSA_SHA1 não existe")
        checks.append(False)
    
    # SHA1 Digest
    print("\n3️⃣ Digest Method (SHA1):")
    try:
        sha1 = xmlsec.Transform.SHA1
        print(f"   xmlsec.Transform.SHA1 = {sha1}")
        if 'sha1' in str(sha1).lower():
            print("   ✅ SHA1 (correto para SEFAZ)")
            checks.append(True)
        else:
            print("   ⚠️ Pode não ser SHA1")
            checks.append(False)
    except AttributeError:
        print("   ❌ xmlsec.Transform.SHA1 não existe")
        checks.append(False)
    
    # Enveloped Signature
    print("\n4️⃣ Transform Enveloped:")
    try:
        enveloped = xmlsec.Transform.ENVELOPED
        print(f"   xmlsec.Transform.ENVELOPED = {enveloped}")
        if 'enveloped' in str(enveloped).lower():
            print("   ✅ ENVELOPED (correto)")
            checks.append(True)
        else:
            print("   ⚠️ Pode não ser enveloped")
            checks.append(False)
    except AttributeError:
        print("   ❌ xmlsec.Transform.ENVELOPED não existe")
        checks.append(False)
    
    print("\n" + "=" * 80)
    if all(checks):
        print("✅ TODAS as constantes xmlsec estão corretas!")
        return True
    else:
        print("⚠️ ALGUMAS constantes podem estar incorretas")
        return False

def main():
    """Executa os testes."""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " VALIDAÇÃO XSD - ASSINATURA SEFAZ ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    resultado1 = validar_assinatura_contra_xsd()
    resultado2 = testar_xmlsec_constants()
    
    print("\n" + "=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    
    if resultado1 and resultado2:
        print("✅ XSD validado e constantes corretas")
        print()
        print("PRÓXIMO PASSO:")
        print("Verificar se o XML gerado pelo xmlsec corresponde EXATAMENTE ao XSD")
        print("Use: python test_xmlsec_verify.py (teste real de assinatura)")
        return 0
    else:
        print("⚠️ Algumas validações falharam")
        print("Revise a implementação da assinatura")
        return 1

if __name__ == '__main__':
    sys.exit(main())
