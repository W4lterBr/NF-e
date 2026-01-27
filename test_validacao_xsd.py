"""Testa validação XSD do evento de manifestação"""
from pathlib import Path
from lxml import etree

# XML do evento que foi enviado (do log)
evento_xml = """<?xml version='1.0' encoding='utf-8'?>
<evento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
    <infEvento Id="ID2102005325125765049200018855001000033428111344131701">
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
    </infEvento>
</evento>
"""

print("=" * 80)
print("TESTE DE VALIDAÇÃO XSD DO EVENTO")
print("=" * 80)

# Parsear XML
evento_root = etree.fromstring(evento_xml.encode('utf-8'))
print(f"\n✅ XML parseado: {evento_root.tag}")

# Carregar XSD
xsd_dir = Path(__file__).parent / "Arquivo_xsd"
xsd_path = xsd_dir / "leiauteEvento_v1.00.xsd"
print(f"\n📋 Carregando XSD: {xsd_path.name}")

try:
    # Carregar com resolução de includes usando base_url
    with open(xsd_path, 'rb') as f:
        schema_doc = etree.parse(f, base_url=str(xsd_dir) + '/')
    schema = etree.XMLSchema(schema_doc)
    
    print(f"✅ XSD carregado com sucesso")
    
    # Validar
    print(f"\n🔍 Validando evento contra XSD...")
    if schema.validate(evento_root):
        print("✅ VALIDAÇÃO PASSOU! XML está correto conforme XSD")
    else:
        print("❌ VALIDAÇÃO FALHOU!")
        print("\nErros encontrados:")
        for i, erro in enumerate(schema.error_log, 1):
            print(f"\n{i}. Linha {erro.line}, Coluna {erro.column}")
            print(f"   {erro.message}")
            print(f"   Tipo: {erro.type_name}")
            
except etree.XMLSchemaParseError as e:
    print(f"\n❌ ERRO ao parsear XSD:")
    print(f"   {e}")
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
