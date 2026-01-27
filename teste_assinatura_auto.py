"""Teste de assinatura com senha do banco de dados"""
import sqlite3
import sys
import os
from lxml import etree
import xmlsec
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime

# Adicionar módulos
sys.path.insert(0, str(Path(__file__).parent / "modules"))
from database import DatabaseManager

print("="*80)
print("TESTE DE ASSINATURA - DIAGNÓSTICO COMPLETO")
print("="*80)

# Descobrir DATA_DIR exatamente como o aplicativo principal faz
def get_data_dir():
    if getattr(sys, 'frozen', False):
        data_dir = Path(sys.executable).parent / "data"
    else:
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "BuscaXML"
    return data_dir

DATA_DIR = get_data_dir()
db_path_appdata = DATA_DIR / "notas.db"
db_path_local = Path(__file__).parent / "notas.db"

print(f"DATA_DIR: {DATA_DIR}")
print(f"DB_PATH (AppData): {db_path_appdata}")
print(f"DB_PATH (Local): {db_path_local}")
print()

# Tentar local primeiro (desenvolvimento)
if db_path_local.exists():
    db_path = db_path_local
    print(f"OK - Usando banco LOCAL: {db_path}")
elif db_path_appdata.exists():
    db_path = db_path_appdata
    print(f"OK - Usando banco APPDATA: {db_path}")
else:
    print(f"ERRO - Nenhum banco de dados encontrado!")
    exit(1)

print()

# 1. Carregar certificados usando DatabaseManager (descriptografa automaticamente)
db = DatabaseManager(db_path)
certs = db.load_certificates()

# Encontrar certificado do CNPJ
cert = next((c for c in certs if c['cnpj_cpf'] == '49068153000160'), None)
if not cert:
    print("ERRO - Certificado 49068153000160 nao encontrado")
    exit(1)

cert_path = cert['caminho']
senha = cert['senha']  # Já descriptografada pelo load_certificates()
print(f"OK - Certificado: {cert_path}")
print(f"OK - Senha carregada e descriptografada: {'*' * len(senha)}")

# 2. Carregar certificado
cert_file = Path(cert_path)
if not cert_file.exists():
    print(f"ERRO - Certificado nao encontrado: {cert_file}")
    exit(1)

with open(cert_file, 'rb') as f:
    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        f.read(), senha.encode(), default_backend()
    )

print(f"OK - Certificado carregado: {certificate.subject}")

# 3. Criar evento EXATAMENTE como no código real
ns = "http://www.portalfiscal.inf.br/nfe"
evento = etree.Element(f"{{{ns}}}evento", versao="1.00", nsmap={None: ns})
inf = etree.SubElement(evento, f"{{{ns}}}infEvento", Id="ID2102005325125765049200018855001000033428111344131701")

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

print("✅ Evento criado")

# 4. Limpar espaços
for elem in evento.iter():
    if elem.text and not elem.text.strip():
        elem.text = None
    if elem.tail and not elem.tail.strip():
        elem.tail = None

# 5. Registrar IDs
xmlsec.tree.add_ids(evento, ["Id"])

# 6. Template
sig = xmlsec.template.create(evento, xmlsec.Transform.C14N, xmlsec.Transform.RSA_SHA1, ns="ds")
evento.append(sig)

ref = xmlsec.template.add_reference(sig, xmlsec.Transform.SHA1, uri="#ID2102005325125765049200018855001000033428111344131701")
xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)

ki = xmlsec.template.ensure_key_info(sig)
xmlsec.template.add_x509_data(ki)

print("✅ Template criado")

# 7. Preparar chave/cert
key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
cert_der = certificate.public_bytes(serialization.Encoding.DER)

# 8. ASSINAR (testando DER como no código real)
print("\n" + "="*80)
print("ASSINANDO COM CERTIFICADO DER")
print("="*80)

ctx = xmlsec.SignatureContext()
ctx.key = xmlsec.Key.from_memory(key_pem, xmlsec.KeyFormat.PEM, None)

try:
    ctx.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
    print("✅ Certificado DER carregado")
except:
    ctx.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)
    print("✅ Certificado PEM carregado (fallback)")

sig_node = evento.find('.//{http://www.w3.org/2000/09/xmldsig#}Signature')
ctx.sign(sig_node)
print("✅ Assinado")

# 9. Verificar certificado X509 foi incluído
x509_cert = sig_node.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
if x509_cert is not None and x509_cert.text:
    print(f"✅ Certificado X509 incluído: {len(x509_cert.text)} caracteres")
else:
    print("❌ Certificado X509 NÃO incluído")

# 10. VERIFICAR
print("\n🔍 Verificando assinatura...")
try:
    xmlsec.tree.add_ids(evento, ["Id"])
    ctx_verify = xmlsec.SignatureContext()
    ctx_verify.verify(sig_node)
    
    print("\n" + "="*80)
    print("✅✅✅ ASSINATURA VÁLIDA! ✅✅✅")
    print("="*80)
    print("\n💡 A assinatura está CORRETA")
    print("💡 O problema do erro 297 está na SERIALIZAÇÃO ou ENVELOPE SOAP")
    
except xmlsec.Error as e:
    print("\n" + "="*80)
    print("❌❌❌ ASSINATURA INVÁLIDA ❌❌❌")
    print("="*80)
    print(f"\n💥 Erro: {e}")
    print("\n💡 Problema FUNDAMENTAL na criação da assinatura")
    print("Possíveis causas:")
    print("  1. xmlsec não consegue validar com certificado embutido")
    print("  2. Transforms incorretos (C14N vs C14N Exclusive)")
    print("  3. Problema na versão do xmlsec")

# 11. Mostrar XML
print("\n" + "="*80)
print("XML ASSINADO (primeiros 2000 chars):")
print("="*80)
xml_str = etree.tostring(evento, encoding='unicode', pretty_print=True)
print(xml_str[:2000])

print("\n" + "="*80)
