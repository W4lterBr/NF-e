from lxml import etree

xml_path = r'C:\Users\Nasci\OneDrive\Documents\Programas VS Code\BOT - Busca NFE\xmls\33251845000109\01-2026\NFSe\NFSe_NSU_2.xml'

with open(xml_path, 'rb') as f:
    tree = etree.parse(f)

ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}

print('Testando extração com namespace:')
print(f"nNFSe: {tree.findtext('.//nfse:nNFSe', namespaces=ns)}")
print(f"dhEmi: {tree.findtext('.//nfse:dhEmi', namespaces=ns)}")
print(f"vServ: {tree.findtext('.//nfse:vServ', namespaces=ns)}")
print(f"CNPJ Tomador: {tree.findtext('.//nfse:toma//nfse:CNPJ', namespaces=ns)}")

print('\nTestando sem namespace:')
print(f"nNFSe: {tree.findtext('.//nNFSe')}")
print(f"dhEmi: {tree.findtext('.//dhEmi')}")
print(f"vServ: {tree.findtext('.//vServ')}")
print(f"CNPJ Tomador: {tree.findtext('.//toma//CNPJ')}")
