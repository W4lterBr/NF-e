"""Verifica se chave privada e certificado correspondem"""
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from hashlib import sha256

# Carregar certificado
cert_path = Path(__file__).parent / "certificados" / "LUZ COMERCIO ALIMENTICIO LTDA_49068153000160.pfx"
password = b"SENHA_AQUI"  # Você precisará fornecer a senha

try:
    with open(cert_path, 'rb') as f:
        pfx_data = f.read()
    
    from cryptography.hazmat.primitives.serialization import pkcs12
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        pfx_data,
        password,
        backend=default_backend()
    )
    
    print("=" * 80)
    print("VERIFICAÇÃO DE CORRESPONDÊNCIA CHAVE-CERTIFICADO")
    print("=" * 80)
    
    print(f"\n✅ Certificado carregado:")
    print(f"   Subject: {certificate.subject}")
    print(f"   Issuer: {certificate.issuer}")
    
    # Testar assinatura/verificação
    test_data = b"teste de assinatura"
    
    # Assinar com chave privada
    from cryptography.hazmat.primitives.asymmetric import padding
    signature = private_key.sign(
        test_data,
        padding.PKCS1v15(),
        hashes.SHA1()
    )
    print(f"\n✅ Assinatura criada: {len(signature)} bytes")
    
    # Verificar com chave pública do certificado
    public_key = certificate.public_key()
    try:
        public_key.verify(
            signature,
            test_data,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        print("✅ CHAVE PRIVADA E CERTIFICADO CORRESPONDEM!")
        print("\n💡 O problema do erro 297 NÃO é incompatibilidade de chaves")
    except Exception as e:
        print(f"❌ CHAVES NÃO CORRESPONDEM: {e}")
        print("\n💡 Este é o problema! Certificado e chave privada não são do mesmo par")
        
except FileNotFoundError:
    print(f"❌ Certificado não encontrado: {cert_path}")
    print("💡 Coloque o arquivo .pfx na pasta certificados/")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
