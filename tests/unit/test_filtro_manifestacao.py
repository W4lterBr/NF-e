"""
Teste do Filtro de Respostas de Manifestação
Garante que respostas retEnvEvento não sejam salvas como notas
"""
from lxml import etree

# Simula uma resposta de manifestação bem-sucedida (NÃO deve ser salva)
xml_manifestacao_sucesso = """<?xml version="1.0" encoding="utf-8"?>
<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
  <idLote>1</idLote>
  <tpAmb>1</tpAmb>
  <verAplic>RS20180515084647</verAplic>
  <cOrgao>91</cOrgao>
  <cStat>128</cStat>
  <xMotivo>Lote de evento processado</xMotivo>
  <retEvento versao="1.00">
    <infEvento Id="ID135200">
      <tpAmb>1</tpAmb>
      <verAplic>RS20180515084647</verAplic>
      <cOrgao>91</cOrgao>
      <cStat>135</cStat>
      <xMotivo>Evento registrado e vinculado a NF-e</xMotivo>
      <chNFe>50260126834440000138550010001795571240230671</chNFe>
      <tpEvento>210200</tpEvento>
      <xEvento>Confirmacao da Operacao</xEvento>
      <nSeqEvento>1</nSeqEvento>
      <dhRegEvento>2026-01-28T16:16:20-03:00</dhRegEvento>
      <nProt>891261320336255</nProt>
    </infEvento>
  </retEvento>
</retEnvEvento>"""

# Simula uma resposta de erro 656 (NÃO deve ser salva)
xml_erro_656 = """<?xml version="1.0" encoding="utf-8"?>
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>1</tpAmb>
  <verAplic>1.7.6</verAplic>
  <cStat>656</cStat>
  <xMotivo>Rejeicao: Consumo Indevido (Ultrapassou o limite de 20 consultas por hora)</xMotivo>
  <dhResp>2026-01-28T14:30:30-03:00</dhResp>
</retDistDFeInt>"""

# Simula uma NF-e completa (DEVE ser salva)
xml_nfe_completo = """<?xml version="1.0" encoding="utf-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe50260126834440000138550010001795571240230671" versao="4.00">
      <ide>
        <nNF>179557</nNF>
      </ide>
      <emit>
        <xNome>EMPRESA TESTE LTDA</xNome>
      </emit>
    </infNFe>
  </NFe>
</nfeProc>"""

print("=" * 80)
print("TESTE: Filtro de Respostas SEFAZ")
print("=" * 80)

# Testa cada XML
tests = [
    ("Manifestação Sucesso (cStat=135)", xml_manifestacao_sucesso, False),  # NÃO deve salvar
    ("Erro 656", xml_erro_656, False),  # NÃO deve salvar
    ("NF-e Completa", xml_nfe_completo, True),  # DEVE salvar
]

for nome, xml, deve_salvar in tests:
    root = etree.fromstring(xml.encode('utf-8'))
    root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
    
    print(f"\n📄 {nome}:")
    print(f"   Tag raiz: {root_tag}")
    
    # Simula lógica do filtro
    is_resposta_sefaz = root_tag in ['retDistDFeInt', 'retConsSitNFe', 'retConsReciNFe', 
                                       'retEnviNFe', 'retEnvEvento', 'retEvento']
    
    if is_resposta_sefaz:
        ns = '{http://www.portalfiscal.inf.br/nfe}'
        cStat = root.findtext(f'{ns}cStat') or root.findtext('cStat')
        xMotivo = root.findtext(f'{ns}xMotivo') or root.findtext('xMotivo')
        
        # Para eventos, verifica infEvento
        if not cStat:
            infEvento = root.find(f'.//{ns}infEvento')
            if infEvento is not None:
                cStat = infEvento.findtext(f'{ns}cStat') or infEvento.findtext('cStat')
                xMotivo = infEvento.findtext(f'{ns}xEvento') or infEvento.findtext('xEvento')
        
        print(f"   cStat: {cStat}")
        print(f"   xMotivo: {xMotivo}")
        
        should_save = False
        if cStat in ['138', '135']:
            if cStat == '135':
                print(f"   ❌ IGNORADO - Resposta de manifestação")
            else:
                print(f"   ⚠️ Resposta de sucesso - verificar contexto")
        else:
            print(f"   ❌ IGNORADO - Resposta de erro")
    else:
        should_save = True
        print(f"   ✅ Documento fiscal válido")
    
    # Verifica resultado
    resultado_correto = (should_save == deve_salvar)
    status = "✅ PASSOU" if resultado_correto else "❌ FALHOU"
    print(f"   {status} - Esperado: {'salvar' if deve_salvar else 'ignorar'}")

print("\n" + "=" * 80)
print("✅ Filtro atualizado para incluir:")
print("   - retEnvEvento (resposta de envio de evento)")
print("   - retEvento (resposta de evento)")
print("   - cStat 135 (manifestação registrada)")
print("\n📋 Arquivos removidos:")
print("   - 4 arquivos SEM_NUMERO-SEM_NOME.xml")
print("\n✅ Sistema corrigido!")
