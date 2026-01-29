import xml.etree.ElementTree as ET

# Ler o XML de debug
with open('debug_manifestacao.xml', 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Parsear e formatar
try:
    root = ET.fromstring(xml_content)
    ET.indent(root, space="  ")
    formatted = ET.tostring(root, encoding='unicode')
    
    # Salvar formatado
    with open('debug_manifestacao_formatado.xml', 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(formatted)
    
    print("XML formatado salvo com sucesso!")
    
    # Verificar alguns detalhes
    print(f"\nTamanho original: {len(xml_content)} bytes")
    print(f"Tamanho formatado: {len(formatted)} bytes")
    
except Exception as e:
    print(f"Erro: {e}")
