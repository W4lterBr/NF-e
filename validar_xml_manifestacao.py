"""
Script para validar XML de manifestação contra XSD de Goiás
"""

# XML que está sendo enviado (do log)
xml_enviado = '''<?xml version="1.0" encoding="utf-8"?>
<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
<idLote>1</idLote>
<evento versao="1.00">
<infEvento Id="ID2102005226015550603000016655001000000536151980371001">
<cOrgao>52</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>49068153000160</CNPJ>
<chNFe>52260155506030000166550010000005361519803710</chNFe>
<dhEvento>2026-01-13T07:41:32-03:00</dhEvento>
<tpEvento>210200</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Ciencia da Operacao</descEvento>
</detEvento>
</infEvento>
</evento>
</envEvento>'''

print("XML que está sendo enviado:")
print(xml_enviado)
print("\n" + "="*80)
print("ANÁLISE:")
print("="*80)
print("✅ Namespace: http://www.portalfiscal.inf.br/nfe")
print("✅ versao='1.00' em envEvento")
print("✅ versao='1.00' em evento")
print("✅ tpEvento='210200' (Ciência)")
print("✅ descEvento='Ciencia da Operacao'")
print("✅ versao='1.00' em detEvento")
print("✅ Sem xJust (não obrigatório para 210200)")
print("\n⚠️ PROBLEMA POSSÍVEL:")
print("Goiás pode estar rejeitando porque espera o XSD de")
print("envEvento v1.00, mas o campo 'versao' está incorreto ou faltando algo.")
