# -*- coding: utf-8 -*-
"""
Teste de canonicalizacao: C14N vs C14N Exclusive
"""
from lxml import etree
from datetime import datetime

# XML de teste (infEvento)
chave = "53251257650492000188550010000334281113441317"
cnpj = "49068153000160"
id_evento = f"ID210200{chave}01"

xml_str = f'''<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
<infEvento Id="{id_evento}">
<cOrgao>53</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>{cnpj}</CNPJ>
<chNFe>{chave}</chNFe>
<dhEvento>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')}</dhEvento>
<tpEvento>210200</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Ciencia da Operacao</descEvento>
</detEvento>
</infEvento>
</evento>'''

root = etree.fromstring(xml_str.encode())
inf_evento = root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento')

print("=" * 80)
print("TESTE DE CANONICALIZACAO")
print("=" * 80)

# C14N não-exclusivo (atual)
c14n_non_exclusive = etree.tostring(
    inf_evento,
    method='c14n',
    exclusive=False,
    with_comments=False
)

# C14N exclusivo
c14n_exclusive = etree.tostring(
    inf_evento,
    method='c14n',
    exclusive=True,
    with_comments=False
)

print("\n1. C14N NAO-EXCLUSIVO (atual):")
print(f"   Tamanho: {len(c14n_non_exclusive)} bytes")
print(f"   Primeiros 100 chars: {c14n_non_exclusive[:100]}")

print("\n2. C14N EXCLUSIVO:")
print(f"   Tamanho: {len(c14n_exclusive)} bytes")
print(f"   Primeiros 100 chars: {c14n_exclusive[:100]}")

print("\n3. DIFERENCA:")
if c14n_non_exclusive == c14n_exclusive:
    print("   Identicos!")
else:
    print("   DIFERENTES!")
    print(f"   Diferenca de tamanho: {len(c14n_non_exclusive) - len(c14n_exclusive)} bytes")

# DigestValue com ambos
import hashlib
import base64

digest_non_exc = base64.b64encode(hashlib.sha1(c14n_non_exclusive).digest()).decode()
digest_exc = base64.b64encode(hashlib.sha1(c14n_exclusive).digest()).decode()

print("\n4. DigestValue (SHA1):")
print(f"   C14N nao-exclusivo: {digest_non_exc}")
print(f"   C14N exclusivo: {digest_exc}")

if digest_non_exc != digest_exc:
    print("\n   *** CRITICO: DigestValue diferente! ***")
    print("   O algoritmo de canonicalizacao pode estar errado!")
