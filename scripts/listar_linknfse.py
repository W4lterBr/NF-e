# -*- coding: utf-8 -*-
"""
Lista campo LinkNFSe de todas as NFS-e ABRASF no banco.
Lê o XML de cada nota e extrai o campo LinkNFSe (URL do portal municipal).
"""
import sys, os, sqlite3, re
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from nfse_search import NFSeDatabase, get_data_dir
from lxml import etree

db   = NFSeDatabase()
DB   = db.db_path

# Notas ABRASF em nfse_docs têm chave no formato CNPJ_NUMERO_ZERADO
# Detecta pelo namespace no XML: 'abrasf.org.br'
with sqlite3.connect(DB) as conn:
    conn.row_factory = sqlite3.Row
    todas = conn.execute("""
        SELECT chave, n_nfse as numero, informante, dh_emi as data_emissao,
               v_serv as valor, caminho_xml, prest_cmun, prest_xnome
        FROM nfse_docs
        WHERE caminho_xml IS NOT NULL AND caminho_xml != ''
        ORDER BY informante, dh_emi DESC
    """).fetchall()

DATA_DIR = get_data_dir()

# Filtra somente as ABRASF reais pelo conteúdo do XML
notas = []
for r in todas:
    xml_path = Path(r['caminho_xml'])
    if not xml_path.exists():
        continue
    try:
        head = xml_path.read_bytes()[:400].decode('utf-8', errors='replace')
        if 'abrasf.org.br' in head:
            notas.append(r)
    except Exception:
        pass

def reconstruir_caminho(informante, data_emissao, numero):
    """Reconstrói o caminho do XML no disco a partir dos metadados."""
    aaaa = (data_emissao or '')[:4]
    mm   = (data_emissao or '')[5:7]
    cnpj = re.sub(r'\D', '', informante or '')
    if aaaa and mm and cnpj:
        # Estrutura v1.2.8: xmls/CNPJ/AAAA-MM/NFSE/
        p = DATA_DIR / 'xmls' / cnpj / f'{aaaa}-{mm}' / 'NFSE' / f'NFSe_{numero}.xml'
        if p.exists():
            return p
        # Estrutura antiga MMAAAA
        p2 = DATA_DIR / 'xmls' / cnpj / f'{mm}{aaaa}' / 'NFSE' / f'NFSe_{numero}.xml'
        if p2.exists():
            return p2
    # Busca por nome em toda a pasta do CNPJ
    base = DATA_DIR / 'xmls' / re.sub(r'\D', '', informante or '')
    if base.exists():
        for f in base.rglob(f'NFSe_{numero}.xml'):
            return f
    return None

print(f"Total NFS-e ABRASF no banco: {len(notas)}")
print()

# Namespaces ABRASF possíveis
NS_AB1 = {"ab": "http://www.abrasf.org.br/nfse.xsd"}
NS_AB2 = {"ab": "http:/www.abrasf.org.br/nfse.xsd"}   # com barra simples (DominioWeb)

def extrair_link(xml_path):
    """Retorna (link, erro)."""
    try:
        tree = etree.parse(str(xml_path))
        for ns in (NS_AB1, NS_AB2):
            el = tree.find('.//ab:LinkNFSe', ns)
            if el is not None and el.text:
                return el.text.strip(), None
        # Sem namespace
        el = tree.find('.//LinkNFSe')
        if el is not None and el.text:
            return el.text.strip(), None
        return None, 'campo ausente'
    except FileNotFoundError:
        return None, 'XML não encontrado em disco'
    except Exception as e:
        return None, str(e)[:60]

com_link    = []
sem_link    = []
sem_arquivo = []

for n in notas:
    xml_path = Path(n['caminho_xml'])
    link, erro = extrair_link(xml_path)
    if link:
        com_link.append((n, link))
    else:
        sem_link.append((n, erro))

# ─── Relatório ────────────────────────────────────────────────────────────────
print("=" * 80)
print(f"  COM LinkNFSe  : {len(com_link)}")
print(f"  Sem LinkNFSe  : {len(sem_link)}")
print(f"  Sem arquivo   : {len(sem_arquivo)}")
print("=" * 80)

if com_link:
    print()
    print("NOTAS COM LinkNFSe (podem baixar PDF do portal municipal):")
    print("-" * 80)
    ultimo_inf = None
    for nota, link in com_link:
        if nota['informante'] != ultimo_inf:
            print(f"\n  CNPJ {nota['informante']}  |  Município {nota['prest_cmun']}  |  {nota['prest_xnome']}")
            ultimo_inf = nota['informante']
        print(f"    NFS-e {nota['numero']:<10}  {(nota['data_emissao'] or '')[:10]}  R$ {nota['valor'] or '-':<12}  {link}")

if sem_link:
    print()
    print("NOTAS SEM LinkNFSe (só geração local disponível):")
    print("-" * 80)
    ultimo_inf = None
    for nota, motivo in sem_link:
        if nota['informante'] != ultimo_inf:
            print(f"\n  CNPJ {nota['informante']}  |  Município {nota['prest_cmun']}  |  {nota['prest_xnome']}")
            ultimo_inf = nota['informante']
        print(f"    NFS-e {nota['numero']:<10}  {(nota['data_emissao'] or '')[:10]}  [{motivo}]")

if sem_arquivo:
    print()
    print("NOTAS SEM ARQUIVO XML em disco:")
    print("-" * 80)
    for nota in sem_arquivo:
        print(f"  CNPJ {nota['informante']}  NFS-e {nota['numero']:<10}  xml={nota['caminho_xml'] or 'NULL'}")

print()
print("Concluído.")
