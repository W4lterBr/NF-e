from lxml import etree
from pathlib import Path

# Pega primeiro XML para testar
xml_path = list(Path("xmls").rglob("NFSe/*.xml"))[0]
print(f"Testando: {xml_path}")

with open(xml_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

tree = etree.fromstring(xml_content.encode('utf-8'))
ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}

print("\nTestando extrações:")
print(f"nNFSe: {tree.findtext('.//nfse:nNFSe', namespaces=ns)}")
print(f"nDFSe: {tree.findtext('.//nfse:nDFSe', namespaces=ns)}")
print(f"dhEmi: {tree.findtext('.//nfse:dhEmi', namespaces=ns)}")
print(f"dhProc: {tree.findtext('.//nfse:dhProc', namespaces=ns)}")
print(f"CNPJ emit: {tree.findtext('.//nfse:emit/nfse:CNPJ', namespaces=ns)}")
print(f"xNome emit: {tree.findtext('.//nfse:emit/nfse:xNome', namespaces=ns)}")
print(f"CNPJ toma: {tree.findtext('.//nfse:toma/nfse:CNPJ', namespaces=ns)}")
print(f"vServ: {tree.findtext('.//nfse:vServ', namespaces=ns)}")
print(f"vLiq: {tree.findtext('.//nfse:vLiq', namespaces=ns)}")
print(f"vISSQN: {tree.findtext('.//nfse:vISSQN', namespaces=ns)}")
print(f"vBC: {tree.findtext('.//nfse:vBC', namespaces=ns)}")
print(f"UF: {tree.findtext('.//nfse:emit/nfse:enderNac/nfse:UF', namespaces=ns)}")
print(f"xDescServ: {tree.findtext('.//nfse:xDescServ', namespaces=ns)}")
