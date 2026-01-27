"""
Teste de geração de assinatura conforme XSD da SEFAZ
Gera assinatura real e valida contra xmldsig-core-schema_v1.01.xsd
"""

import sys
from pathlib import Path
from lxml import etree
import xmlsec
from cryptography.hazmat.primitives import serialization

# Adiciona módulos ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def criar_evento_teste():
    """Cria um evento de manifestação de teste."""
    
    ns = "http://www.portalfiscal.inf.br/nfe"
    chave = "53251257650492000188550010000334281113441317"
    id_evento = f"ID210200{chave}01"
    
    # Cria evento
    evento = etree.Element(f"{{{ns}}}evento", versao="1.00", nsmap={None: ns})
    inf_evento = etree.SubElement(evento, f"{{{ns}}}infEvento", Id=id_evento)
    
    # Preenche infEvento
    c_orgao = etree.SubElement(inf_evento, f"{{{ns}}}cOrgao")
    c_orgao.text = "53"
    
    tp_amb = etree.SubElement(inf_evento, f"{{{ns}}}tpAmb")
    tp_amb.text = "1"
    
    cnpj = etree.SubElement(inf_evento, f"{{{ns}}}CNPJ")
    cnpj.text = "49068153000160"
    
    chave_elem = etree.SubElement(inf_evento, f"{{{ns}}}chNFe")
    chave_elem.text = chave
    
    dh_evento = etree.SubElement(inf_evento, f"{{{ns}}}dhEvento")
    dh_evento.text = "2025-01-27T10:00:00-03:00"
    
    tp_evento = etree.SubElement(inf_evento, f"{{{ns}}}tpEvento")
    tp_evento.text = "210200"
    
    n_seq_evento = etree.SubElement(inf_evento, f"{{{ns}}}nSeqEvento")
    n_seq_evento.text = "1"
    
    ver_evento = etree.SubElement(inf_evento, f"{{{ns}}}verEvento")
    ver_evento.text = "1.00"
    
    # detEvento
    det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", versao="1.00")
    desc_evento = etree.SubElement(det_evento, f"{{{ns}}}descEvento")
    desc_evento.text = "Ciencia da Operacao"
    
    return evento, id_evento

def assinar_com_xmlsec(evento, id_evento, cert_path, cert_password):
    """Assina o evento usando xmlsec."""
    
    print("=" * 80)
    print("ASSINANDO EVENTO COM XMLSEC")
    print("=" * 80)
    
    ns = "http://www.portalfiscal.inf.br/nfe"
    
    # Limpa espaços em branco
    print("\n1️⃣ Limpando espaços em branco...")
    for element in evento.iter("*"):
        if element.text is not None and not element.text.strip():
            element.text = None
        if element.tail is not None and not element.tail.strip():
            element.tail = None
    print("   ✅ Espaços limpos")
    
    # Registra Id
    print("\n2️⃣ Registrando atributo Id...")
    xmlsec.tree.add_ids(evento, ["Id"])
    print("   ✅ Id registrado")
    
    # Cria template de assinatura
    print("\n3️⃣ Criando template de assinatura...")
    print(f"   - CanonicalizationMethod: xmlsec.Transform.C14N")
    print(f"   - SignatureMethod: xmlsec.Transform.RSA_SHA1")
    signature_node = xmlsec.template.create(
        evento,
        xmlsec.Transform.C14N,
        xmlsec.Transform.RSA_SHA1,
        ns="ds"
    )
    evento.append(signature_node)
    print("   ✅ Template criado")
    
    # Adiciona Reference
    print("\n4️⃣ Adicionando Reference...")
    print(f"   - URI: #{id_evento}")
    print(f"   - DigestMethod: xmlsec.Transform.SHA1")
    ref = xmlsec.template.add_reference(
        signature_node,
        xmlsec.Transform.SHA1,
        uri=f"#{id_evento}"
    )
    
    print("   - Transforms:")
    print("     1. xmlsec.Transform.ENVELOPED")
    xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
    print("     2. xmlsec.Transform.C14N")
    xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)
    print("   ✅ Reference adicionada")
    
    # Adiciona KeyInfo
    print("\n5️⃣ Adicionando KeyInfo...")
    key_info = xmlsec.template.ensure_key_info(signature_node)
    xmlsec.template.add_x509_data(key_info)
    print("   ✅ KeyInfo adicionada")
    
    # Carrega certificado
    print("\n6️⃣ Carregando certificado...")
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    
    with open(cert_path, 'rb') as f:
        pfx_data = f.read()
    
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data, cert_password.encode(), default_backend()
    )
    
    print(f"   - Subject: {certificate.subject}")
    print(f"   - Issuer: {certificate.issuer}")
    
    # Prepara chave em PEM
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    cert_der = certificate.public_bytes(serialization.Encoding.DER)
    print("   ✅ Certificado carregado")
    
    # Assina
    print("\n7️⃣ Assinando...")
    ctx = xmlsec.SignatureContext()
    ctx.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
    ctx.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
    
    ctx.sign(signature_node)
    print("   ✅ Assinatura gerada!")
    
    return evento

def validar_assinatura_xsd(evento_assinado):
    """Valida a assinatura contra o XSD."""
    
    print("\n" + "=" * 80)
    print("VALIDANDO ASSINATURA CONTRA XSD")
    print("=" * 80)
    
    # Extrai apenas a assinatura
    ns_ds = "http://www.w3.org/2000/09/xmldsig#"
    signature = evento_assinado.find(f'.//{{{ns_ds}}}Signature')
    
    if signature is None:
        print("❌ Assinatura não encontrada no XML!")
        return False
    
    print("\n✅ Assinatura encontrada")
    
    # Valida contra XSD
    xsd_path = BASE_DIR / 'Arquivo_xsd' / 'xmldsig-core-schema_v1.01.xsd'
    with open(xsd_path, 'rb') as f:
        xsd_doc = etree.parse(f)
    
    schema = etree.XMLSchema(xsd_doc)
    
    print("\n📋 Estrutura da assinatura gerada:")
    print(etree.tostring(signature, pretty_print=True, encoding='unicode')[:1000] + "...")
    
    # Valida
    print("\n🔍 Validando contra xmldsig-core-schema_v1.01.xsd...")
    is_valid = schema.validate(signature)
    
    if is_valid:
        print("✅ ASSINATURA VÁLIDA CONFORME XSD!")
        return True
    else:
        print("❌ ASSINATURA INVÁLIDA!")
        print("\nErros:")
        for error in schema.error_log:
            print(f"  - Linha {error.line}: {error.message}")
        return False

def verificar_algoritmos(evento_assinado):
    """Verifica se os algoritmos usados estão corretos."""
    
    print("\n" + "=" * 80)
    print("VERIFICANDO ALGORITMOS USADOS")
    print("=" * 80)
    
    ns_ds = "http://www.w3.org/2000/09/xmldsig#"
    
    checks = []
    
    # CanonicalizationMethod
    canon = evento_assinado.find(f'.//{{{ns_ds}}}CanonicalizationMethod')
    if canon is not None:
        alg = canon.get('Algorithm')
        print(f"\n1️⃣ CanonicalizationMethod: {alg}")
        expected = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        if alg == expected:
            print("   ✅ CORRETO")
            checks.append(True)
        else:
            print(f"   ❌ ESPERADO: {expected}")
            checks.append(False)
    else:
        print("\n1️⃣ CanonicalizationMethod: ❌ NÃO ENCONTRADO")
        checks.append(False)
    
    # SignatureMethod
    sig_method = evento_assinado.find(f'.//{{{ns_ds}}}SignatureMethod')
    if sig_method is not None:
        alg = sig_method.get('Algorithm')
        print(f"\n2️⃣ SignatureMethod: {alg}")
        expected = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
        if alg == expected:
            print("   ✅ CORRETO")
            checks.append(True)
        else:
            print(f"   ❌ ESPERADO: {expected}")
            checks.append(False)
    else:
        print("\n2️⃣ SignatureMethod: ❌ NÃO ENCONTRADO")
        checks.append(False)
    
    # DigestMethod
    digest_method = evento_assinado.find(f'.//{{{ns_ds}}}DigestMethod')
    if digest_method is not None:
        alg = digest_method.get('Algorithm')
        print(f"\n3️⃣ DigestMethod: {alg}")
        expected = "http://www.w3.org/2000/09/xmldsig#sha1"
        if alg == expected:
            print("   ✅ CORRETO")
            checks.append(True)
        else:
            print(f"   ❌ ESPERADO: {expected}")
            checks.append(False)
    else:
        print("\n3️⃣ DigestMethod: ❌ NÃO ENCONTRADO")
        checks.append(False)
    
    # Transforms
    transforms = evento_assinado.findall(f'.//{{{ns_ds}}}Transform')
    print(f"\n4️⃣ Transforms: {len(transforms)} encontrados")
    if len(transforms) == 2:
        alg1 = transforms[0].get('Algorithm')
        alg2 = transforms[1].get('Algorithm')
        print(f"   1º: {alg1}")
        print(f"   2º: {alg2}")
        
        expected1 = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
        expected2 = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
        
        if alg1 == expected1 and alg2 == expected2:
            print("   ✅ CORRETO (enveloped + c14n)")
            checks.append(True)
        else:
            print(f"   ❌ ESPERADO: {expected1}")
            print(f"   ❌ ESPERADO: {expected2}")
            checks.append(False)
    else:
        print("   ❌ ESPERADO: exatamente 2 transforms")
        checks.append(False)
    
    return all(checks)

def main():
    """Executa o teste completo."""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " TESTE DE ASSINATURA CONFORME XSD DA SEFAZ ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Busca certificado
    from modules.database import DatabaseManager
    db = DatabaseManager("notas.db")
    
    certs = db.load_certificates()
    if not certs:
        print("\n❌ Nenhum certificado encontrado no banco de dados")
        print("   Configure um certificado antes de executar este teste")
        return 1
    
    # Usa primeiro certificado
    cert = certs[0]
    cert_path = cert['caminho']  # Campo correto é 'caminho'
    cert_password = cert['senha']
    informante = cert['informante']
    
    print(f"\n📜 Usando certificado: {informante}")
    print(f"   Caminho: {cert_path}")
    
    # Cria evento
    print("\n" + "=" * 80)
    print("CRIANDO EVENTO DE TESTE")
    print("=" * 80)
    evento, id_evento = criar_evento_teste()
    print(f"✅ Evento criado com ID: {id_evento}")
    
    # Assina
    try:
        evento_assinado = assinar_com_xmlsec(evento, id_evento, cert_path, cert_password)
    except Exception as e:
        print(f"\n❌ ERRO ao assinar: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Valida XSD
    xsd_valido = validar_assinatura_xsd(evento_assinado)
    
    # Verifica algoritmos
    algoritmos_corretos = verificar_algoritmos(evento_assinado)
    
    # Conclusão
    print("\n" + "=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    
    if xsd_valido and algoritmos_corretos:
        print("✅ ASSINATURA 100% CONFORME XSD DA SEFAZ!")
        print()
        print("A assinatura gerada pelo xmlsec está correta segundo o XSD.")
        print("Se ainda houver erro 297, o problema pode ser:")
        print("  1. Certificado incompatível com SEFAZ")
        print("  2. Problema de rede/conectividade")
        print("  3. Ambiente de homologação vs produção")
        return 0
    else:
        print("❌ ASSINATURA NÃO CONFORME!")
        print()
        print("A assinatura não está de acordo com o XSD da SEFAZ.")
        print("Revise o código de assinatura em manifestacao_service.py")
        return 1

if __name__ == '__main__':
    sys.exit(main())
