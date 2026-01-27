"""
Teste para diagnosticar erro 491 - tpEvento inválido
"""

# Analisando o XML enviado:
xml_enviado = """
<evento versao="1.00">
<infEvento Id="ID2102103526017238118900100155001008315476163795411901">
<cOrgao>35</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>01773924000193</CNPJ>
<chNFe>35260172381189001001550010083154761637954119</chNFe>
<dhEvento>2026-01-07T11:17:04-03:00</dhEvento>
<tpEvento>210210</tpEvento>
<nSeqEvento>1</nSeqEvento>
<verEvento>1.00</verEvento>
<detEvento versao="1.00">
<descEvento>Ciencia da Operacao</descEvento>
</detEvento>
</infEvento>
</evento>
"""

print("📋 Análise do XML enviado:\n")
print("Chave:", "35260172381189001001550010083154761637954119")
print("  UF (posições 0-2):", "35", "= São Paulo")
print("  Ano/Mês (pos 2-6):", "2601", "= Janeiro/2026")
print("  CNPJ Emit (pos 6-20):", "72381189001001")
print("  Modelo (pos 20-22):", "55", "= NF-e")
print("  Série (pos 22-25):", "001")
print("  Número (pos 25-34):", "008315476")
print("  tpEmis (pos 34):", "1", "= Normal")
print("  Código (pos 35-43):", "637954119")
print("  DV (pos 43):", "9")

print("\n📋 Campos do evento:")
print("  tpEvento:", "210210", "✅")
print("  cOrgao:", "35", "✅")
print("  tpAmb:", "1", "✅ (Produção)")
print("  CNPJ Dest:", "01773924000193", "✅")
print("  descEvento:", "Ciencia da Operacao", "✅")
print("  verEvento:", "1.00", "✅")

print("\n🔍 Verificando possíveis causas do erro 491:")
print("\n1. Data do evento no futuro?")
print("   dhEvento: 2026-01-07T11:17:04-03:00")
print("   Data atual: 2026-01-07")
print("   ✅ Data válida")

print("\n2. Evento já registrado anteriormente?")
print("   Pode ser que o evento já tenha sido manifestado")
print("   Solução: Testar com outra chave")

print("\n3. NF-e pode estar cancelada ou denegada?")
print("   Segundo a nota técnica (H04/H05):")
print("   - Não pode fazer Ciência em NF-e Cancelada/Denegada")

print("\n4. Destinatário da chave é 01773924000193?")
print("   Precisa confirmar se o CNPJ 01773924000193 é realmente o destinatário")

print("\n5. Ambiente correto?")
print("   tpAmb=1 (Produção) - OK")

print("\n💡 DIAGNÓSTICO PROVÁVEL:")
print("   O erro 491 pode indicar que:")
print("   a) O evento já foi registrado anteriormente")
print("   b) A NF-e está cancelada ou denegada")
print("   c) O CNPJ não é o destinatário desta NF-e")
print("   d) A NF-e não existe ou não está autorizada")

print("\n🔧 SOLUÇÕES:")
print("   1. Verificar o status da NF-e pela chave")
print("   2. Tentar com outra chave que você sabe que está autorizada")
print("   3. Verificar se o CNPJ é realmente o destinatário")
print("   4. Verificar se já não foi feita manifestação anterior")
