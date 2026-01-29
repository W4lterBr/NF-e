"""
Estratégias Alternativas de Assinatura Baseadas no XSD
Testa diferentes formas de carregar certificado e gerar assinatura
"""

import sys
from pathlib import Path
from lxml import etree
import xmlsec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def criar_evento_basico():
    """Cria evento mínimo para teste."""
    ns = "http://www.portalfiscal.inf.br/nfe"
    chave = "53251257650492000188550010000334281113441317"
    id_evento = f"ID210200{chave}01"
    
    evento = etree.Element(f"{{{ns}}}evento", versao="1.00", nsmap={None: ns})
    inf_evento = etree.SubElement(evento, f"{{{ns}}}infEvento", Id=id_evento)
    
    etree.SubElement(inf_evento, f"{{{ns}}}cOrgao").text = "53"
    etree.SubElement(inf_evento, f"{{{ns}}}tpAmb").text = "1"
    etree.SubElement(inf_evento, f"{{{ns}}}CNPJ").text = "49068153000160"
    etree.SubElement(inf_evento, f"{{{ns}}}chNFe").text = chave
    etree.SubElement(inf_evento, f"{{{ns}}}dhEvento").text = "2025-01-27T10:00:00-03:00"
    etree.SubElement(inf_evento, f"{{{ns}}}tpEvento").text = "210200"
    etree.SubElement(inf_evento, f"{{{ns}}}nSeqEvento").text = "1"
    etree.SubElement(inf_evento, f"{{{ns}}}verEvento").text = "1.00"
    
    det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", versao="1.00")
    etree.SubElement(det_evento, f"{{{ns}}}descEvento").text = "Ciencia da Operacao"
    
    return evento, id_evento

def estrategia_1_der(evento, id_evento, cert_path, cert_password):
    """Estratégia 1: Certificado DER (binário)."""
    print("\n" + "=" * 80)
    print("ESTRATÉGIA 1: Certificado em formato DER (binário)")
    print("=" * 80)
    
    try:
        # Limpa XML
        for elem in evento.iter("*"):
            if elem.text and not elem.text.strip():
                elem.text = None
            if elem.tail and not elem.tail.strip():
                elem.tail = None
        
        # Registra Id
        xmlsec.tree.add_ids(evento, ["Id"])
        
        # Template
        sig = xmlsec.template.create(evento, xmlsec.Transform.C14N, xmlsec.Transform.RSA_SHA1, ns="ds")
        evento.append(sig)
        
        ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA1, uri=f"#{id_evento}")
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)
        
        key_info = xmlsec.template.ensure_key_info(sig)
        xmlsec.template.add_x509_data(key_info)
        
        # Carrega certificado
        with open(cert_path, 'rb') as f:
            pfx_data = f.read()
        
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            pfx_data, cert_password.encode(), default_backend()
        )
        
        # Chave em PEM
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Certificado em DER
        cert_der = certificate.public_bytes(serialization.Encoding.DER)
        
        # Assina
        ctx = xmlsec.SignatureContext()
        ctx.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
        ctx.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
        
        ctx.sign(sig)
        
        # Verifica localmente
        ctx_verify = xmlsec.SignatureContext()
        ctx_verify.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
        ctx_verify.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
        
        result = ctx_verify.verify(sig)
        
        if result is None:
            print("✅ Estratégia 1: Assinatura válida localmente")
            return True, evento
        else:
            print(f"❌ Estratégia 1: Falhou verificação local: {result}")
            return False, None
            
    except Exception as e:
        print(f"❌ Estratégia 1: Exceção: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def estrategia_2_pem(evento, id_evento, cert_path, cert_password):
    """Estratégia 2: Certificado PEM (texto)."""
    print("\n" + "=" * 80)
    print("ESTRATÉGIA 2: Certificado em formato PEM (texto)")
    print("=" * 80)
    
    try:
        # Limpa XML
        for elem in evento.iter("*"):
            if elem.text and not elem.text.strip():
                elem.text = None
            if elem.tail and not elem.tail.strip():
                elem.tail = None
        
        xmlsec.tree.add_ids(evento, ["Id"])
        
        sig = xmlsec.template.create(evento, xmlsec.Transform.C14N, xmlsec.Transform.RSA_SHA1, ns="ds")
        evento.append(sig)
        
        ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA1, uri=f"#{id_evento}")
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)
        
        key_info = xmlsec.template.ensure_key_info(sig)
        xmlsec.template.add_x509_data(key_info)
        
        with open(cert_path, 'rb') as f:
            pfx_data = f.read()
        
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            pfx_data, cert_password.encode(), default_backend()
        )
        
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Certificado em PEM
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
        
        ctx = xmlsec.SignatureContext()
        ctx.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
        ctx.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)
        
        ctx.sign(sig)
        
        # Verifica
        ctx_verify = xmlsec.SignatureContext()
        ctx_verify.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
        ctx_verify.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)
        
        result = ctx_verify.verify(sig)
        
        if result is None:
            print("✅ Estratégia 2: Assinatura válida localmente")
            return True, evento
        else:
            print(f"❌ Estratégia 2: Falhou verificação local: {result}")
            return False, None
            
    except Exception as e:
        print(f"❌ Estratégia 2: Exceção: {e}")
        return False, None

def estrategia_3_pkcs12_direto(evento, id_evento, cert_path, cert_password):
    """Estratégia 3: Carregar PKCS12 diretamente (sem converter)."""
    print("\n" + "=" * 80)
    print("ESTRATÉGIA 3: Carregar PKCS12 diretamente pelo xmlsec")
    print("=" * 80)
    
    try:
        # Limpa XML
        for elem in evento.iter("*"):
            if elem.text and not elem.text.strip():
                elem.text = None
            if elem.tail and not elem.tail.strip():
                elem.tail = None
        
        xmlsec.tree.add_ids(evento, ["Id"])
        
        sig = xmlsec.template.create(evento, xmlsec.Transform.C14N, xmlsec.Transform.RSA_SHA1, ns="ds")
        evento.append(sig)
        
        ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA1, uri=f"#{id_evento}")
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)
        
        key_info = xmlsec.template.ensure_key_info(sig)
        xmlsec.template.add_x509_data(key_info)
        
        # Tenta carregar PKCS12 diretamente
        ctx = xmlsec.SignatureContext()
        
        try:
            # Algumas versões do xmlsec suportam PKCS12
            ctx.key = xmlsec.Key.from_file(cert_path, xmlsec.KeyFormat.PKCS12, cert_password)
            print("   ✅ Carregou PKCS12 diretamente")
        except:
            print("   ⚠️ xmlsec não suporta PKCS12 direto, usando conversão")
            # Fallback: converter
            with open(cert_path, 'rb') as f:
                pfx_data = f.read()
            
            private_key, certificate, _ = pkcs12.load_key_and_certificates(
                pfx_data, cert_password.encode(), default_backend()
            )
            
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            cert_der = certificate.public_bytes(serialization.Encoding.DER)
            
            ctx.key = xmlsec.Key.from_memory(private_key_pem, xmlsec.KeyFormat.PEM, None)
            ctx.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
        
        ctx.sign(sig)
        
        # Verifica
        result = ctx.verify(sig)
        
        if result is None:
            print("✅ Estratégia 3: Assinatura válida localmente")
            return True, evento
        else:
            print(f"❌ Estratégia 3: Falhou verificação local: {result}")
            return False, None
            
    except Exception as e:
        print(f"❌ Estratégia 3: Exceção: {e}")
        return False, None

def main():
    """Testa todas as estratégias."""
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " TESTE DE ESTRATÉGIAS DE ASSINATURA ".center(78) + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Busca certificado
    from modules.database import DatabaseManager
    db = DatabaseManager("notas.db")
    
    certs = db.load_certificates()
    if not certs:
        print("\n❌ Nenhum certificado encontrado")
        return 1
    
    cert = certs[0]
    cert_path = cert['caminho']
    cert_password = cert['senha']
    informante = cert['informante']
    
    print(f"\n📜 Certificado: {informante}")
    print(f"   Caminho: {cert_path}")
    
    resultados = []
    
    # Testa cada estratégia
    estrategias = [
        ("DER (binário)", estrategia_1_der),
        ("PEM (texto)", estrategia_2_pem),
        ("PKCS12 direto", estrategia_3_pkcs12_direto),
    ]
    
    for nome, funcao in estrategias:
        evento, id_evento = criar_evento_basico()
        sucesso, evento_assinado = funcao(evento, id_evento, cert_path, cert_password)
        resultados.append((nome, sucesso, evento_assinado))
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DAS ESTRATÉGIAS")
    print("=" * 80)
    
    for nome, sucesso, evento in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{nome:20s} {status}")
    
    # Se alguma passou, salva XML
    for nome, sucesso, evento in resultados:
        if sucesso and evento is not None:
            filename = f"evento_assinado_{nome.replace(' ', '_').lower()}.xml"
            with open(filename, 'wb') as f:
                f.write(etree.tostring(evento, pretty_print=True, xml_declaration=True, encoding='UTF-8'))
            print(f"\n💾 XML salvo: {filename}")
            print(f"   Teste este XML manualmente na SEFAZ para ver se é aceito!")
    
    print("\n" + "=" * 80)
    print("CONCLUSÃO")
    print("=" * 80)
    
    if any(sucesso for _, sucesso, _ in resultados):
        print("✅ Pelo menos uma estratégia funcionou localmente")
        print("\nPRÓXIMO PASSO:")
        print("1. Teste o XML gerado na SEFAZ manualmente")
        print("2. Se ainda der erro 297, o problema é incompatibilidade do certificado")
        print("3. Considere usar API BrasilNFe para garantir compatibilidade")
        return 0
    else:
        print("❌ NENHUMA estratégia funcionou")
        print("\nO problema pode ser:")
        print("- Certificado corrompido")
        print("- Senha incorreta")
        print("- Biblioteca xmlsec com problema")
        return 1

if __name__ == '__main__':
    sys.exit(main())
