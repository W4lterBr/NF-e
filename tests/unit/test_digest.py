"""Analisa a assinatura do evento e verifica o DigestValue"""
from lxml import etree
from hashlib import sha1
import base64

# XML do infEvento (antes de assinar)
info_evento = """<infEvento xmlns="http://www.portalfiscal.inf.br/nfe" Id="ID2102005325125765049200018855001000033428111344131701">
<cOrgao>53</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>49068153000160</CNPJ>
<chNFe>53251257650492000188550010000334281113441317</chNFe>
<dhEvento>2026-01-13T10:34:10-03:00</dhEvento>
<tpEvento>210200</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Ciencia da Operacao</descEvento>
</detEvento>
</infEvento>"""

print("=" * 80)
print("ANÁLISE DA ASSINATURA - DigestValue")
print("=" * 80)

# Parse do XML
root = etree.fromstring(info_evento.encode('utf-8'))
print(f"\n✅ XML parseado: {root.tag}")

# Canonicalizar (C14N) - mesmo algoritmo usado na assinatura
c14n_bytes = etree.tostring(root, method='c14n', exclusive=False)
print(f"\n📝 XML Canonicalizado (C14N):")
print(c14n_bytes.decode('utf-8')[:500] + '...')
print(f"\n📏 Tamanho: {len(c14n_bytes)} bytes")

# Calcular hash SHA1
digest = sha1(c14n_bytes).digest()
digest_b64 = base64.b64encode(digest).decode('ascii')

print(f"\n🔐 DigestValue calculado: {digest_b64}")
print(f"   (do log): B80jgAHiQZpwE63bdiPFZV0gLdI=")

if digest_b64 == "B80jgAHiQZpwE63bdiPFZV0gLdI=":
    print("\n✅ MATCH! DigestValue está correto")
else:
    print("\n❌ DIFERENTE! Problema na canonicalização")
    print("\nDiferenças possíveis:")
    print("- Namespace declarations diferentes")
    print("- Espaços em branco não removidos")
    print("- Atributos em ordem diferente")
    
print("\n" + "=" * 80)
