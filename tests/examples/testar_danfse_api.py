# -*- coding: utf-8 -*-
"""
Teste rápido de download de DANFSe oficial da API.
"""

from modules.nfse_service import NFSeService
from nfse_search import NFSeDatabase
from pathlib import Path
from lxml import etree
import sys

print("=" * 70)
print("TESTE DE DOWNLOAD DE DANFSE OFICIAL")
print("=" * 70)

# Busca credenciais
db = NFSeDatabase()
certs = db.get_certificados()
if not certs:
    print("❌ Nenhum certificado encontrado")
    sys.exit(1)

cnpj, cert_path, senha, informante, cuf = certs[0]
print(f"\n✅ Certificado: {informante}")

# Pega XML aleatório
xmls = list(Path('xmls/33251845000109').rglob('NFSe/*.xml'))
if not xmls:
    print("❌ Nenhum XML de NFS-e encontrado")
    sys.exit(1)

xml_path = xmls[0]
print(f"✅ XML selecionado: {xml_path.name}")

# Extrai chave
xml_content = xml_path.read_text(encoding='utf-8')
ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
tree = etree.fromstring(xml_content.encode('utf-8'))
inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
chave = inf_nfse.get('Id')[3:] if inf_nfse is not None else None

if not chave:
    print("❌ Chave não encontrada no XML")
    sys.exit(1)

print(f"✅ Chave extraída: {chave[:20]}...")

# Inicializa serviço
print(f"\n📡 Conectando à API...")
service = NFSeService(
    cert_path=cert_path,
    senha=senha,
    informante=informante,
    cuf=cuf,
    ambiente='producao'
)
print("✅ Serviço inicializado")

# Tenta baixar PDF
print(f"\n📥 Baixando DANFSe OFICIAL (pode demorar 30-60s)...")
try:
    pdf = service.consultar_danfse(chave, retry=3)
    
    if pdf:
        print(f"\n✅ PDF OFICIAL OBTIDO!")
        print(f"   Tamanho: {len(pdf):,} bytes")
        print(f"   Início: {pdf[:4]}")
        
        # Salva teste
        test_path = Path('teste_danfse_oficial.pdf')
        test_path.write_bytes(pdf)
        print(f"\n💾 Salvo em: {test_path}")
        print(f"\n🎉 SUCESSO! O PDF oficial da API está funcionando!")
        print(f"   Abra o arquivo para ver o layout completo do DANFSe")
    else:
        print("❌ PDF vazio retornado")
        
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print(f"\n⚠️  A API do Ambiente Nacional pode estar:")
    print(f"   - Temporariamente indisponível (erro 502/503)")
    print(f"   - Com timeout de conexão")
    print(f"   - Em manutenção")
    print(f"\n💡 Solução: PDFs genéricos foram gerados como fallback")
