# -*- coding: utf-8 -*-
"""
Analise detalhada do XML enviado para SEFAZ
Compara com especificacao oficial
"""
from lxml import etree
from datetime import datetime
import hashlib
import base64

# Chave do usuario
chave = "53251257650492000188550010000334281113441317"
cnpj = "49068153000160"

# 1. CONSTRUIR XML EXATAMENTE COMO ESPECIFICACAO
print("=" * 80)
print("ANALISE DO XML DE MANIFESTACAO")
print("=" * 80)

# Criar evento conforme especificacao
ns = "http://www.portalfiscal.inf.br/nfe"
id_evento = f"ID210200{chave}01"

# infEvento
inf_evento = etree.Element(f"{{{ns}}}infEvento", attrib={"Id": id_evento})
etree.SubElement(inf_evento, f"{{{ns}}}cOrgao").text = "53"
etree.SubElement(inf_evento, f"{{{ns}}}tpAmb").text = "1"
etree.SubElement(inf_evento, f"{{{ns}}}CNPJ").text = cnpj
etree.SubElement(inf_evento, f"{{{ns}}}chNFe").text = chave
etree.SubElement(inf_evento, f"{{{ns}}}dhEvento").text = "2026-01-13T11:37:29-03:00"
etree.SubElement(inf_evento, f"{{{ns}}}tpEvento").text = "210200"
etree.SubElement(inf_evento, f"{{{ns}}}nSeqEvento").text = "1"
etree.SubElement(inf_evento, f"{{{ns}}}verEvento").text = "1.00"

# detEvento
det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", attrib={"versao": "1.00"})
etree.SubElement(det_evento, f"{{{ns}}}descEvento").text = "Ciencia da Operacao"

# evento
evento = etree.Element(f"{{{ns}}}evento", attrib={"versao": "1.00"})
evento.append(inf_evento)

print("\n1. ESTRUTURA DO XML:")
print(f"   Namespace: {ns}")
print(f"   ID do evento: {id_evento}")
print(f"   UF (cOrgao): 53 (DF)")
print(f"   Tipo evento: 210200 (Ciencia)")

# 2. CANONICALIZACAO
print("\n2. CANONICALIZACAO (C14N):")
c14n_bytes = etree.tostring(inf_evento, method='c14n', exclusive=False, with_comments=False)
print(f"   Tamanho: {len(c14n_bytes)} bytes")
print(f"   Primeiros 200 chars:")
print(f"   {c14n_bytes[:200].decode()}")

# 3. DIGEST VALUE
digest = base64.b64encode(hashlib.sha1(c14n_bytes).digest()).decode()
print(f"\n3. DIGESTVALUE (SHA1):")
print(f"   {digest}")

# 4. VERIFICAR ATRIBUTOS
print(f"\n4. ATRIBUTOS DO infEvento:")
print(f"   Id: {inf_evento.get('Id')}")
print(f"   Namespace: {inf_evento.tag}")

# 5. VERIFICAR ESPACOS EM BRANCO
print(f"\n5. ESPACOS EM BRANCO:")
xml_str = etree.tostring(evento, encoding='unicode', pretty_print=False)
tem_espacos = any(c in xml_str for c in ['\n', '\r', '\t'])
print(f"   Tem quebras de linha/tabs: {tem_espacos}")
if tem_espacos:
    print(f"   PROBLEMA: XML tem espacos em branco!")

# 6. VERIFICAR ORDEM DOS ELEMENTOS
print(f"\n6. ORDEM DOS ELEMENTOS EM infEvento:")
for i, child in enumerate(inf_evento):
    tag_name = child.tag.replace(f"{{{ns}}}", "")
    print(f"   {i+1}. {tag_name}: {child.text if child.text and len(child.text) < 50 else f'{child.text[:50] if child.text else ''}...'}")

# 7. COMPARAR COM ESPECIFICACAO
print(f"\n7. CONFORMIDADE COM ESPECIFICACAO:")
ordem_esperada = ["cOrgao", "tpAmb", "CNPJ", "chNFe", "dhEvento", "tpEvento", "nSeqEvento", "verEvento", "detEvento"]
ordem_atual = [c.tag.replace(f"{{{ns}}}", "") for c in inf_evento]

if ordem_atual == ordem_esperada:
    print(f"   OK - Ordem dos elementos correta")
else:
    print(f"   ERRO - Ordem dos elementos incorreta!")
    print(f"   Esperado: {ordem_esperada}")
    print(f"   Atual: {ordem_atual}")

# 8. VERIFICAR NAMESPACE NO detEvento
print(f"\n8. detEvento:")
det_evento_elem = inf_evento.find(f"{{{ns}}}detEvento")
print(f"   versao: {det_evento_elem.get('versao')}")
print(f"   descEvento: {det_evento_elem.findtext(f'{{{ns}}}descEvento')}")

# 9. XML COMPLETO (sem assinatura)
print(f"\n9. XML COMPLETO (sem assinatura):")
xml_final = etree.tostring(evento, encoding='unicode', pretty_print=False)
print(xml_final[:500] + "...")

print("\n" + "=" * 80)
print("DIAGNOSTICO:")
print("=" * 80)
print("Se DigestValue correto mas erro 297 persiste:")
print("  -> Problema NAO e no infEvento (hash correto)")
print("  -> Problema e na ASSINATURA DIGITAL (SignatureValue)")
print("  -> Certificado/chave privada incompativel com SEFAZ")
print("  -> Algoritmo de assinatura incorreto")
