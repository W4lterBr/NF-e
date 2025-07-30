# parser.py
import os
import gzip
import base64
import re
from datetime import datetime
from lxml import etree
from db import obter_pasta_armazenamento, registrar_xml_baixado

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_XMLS = os.path.join(SCRIPT_DIR, "xmls")

# Colunas usadas na Treeview
COLUMNS = [
    "IE Tomador", "Filial", "Nome", "CNPJ/CPF", "Num", "DtEmi",
    "Tipo", "Valor", "Status", "UF", "Chave", "Natureza"
]

def extrair_ult_nsu_resposta(xml_resposta):
    try:
        tree = etree.fromstring(xml_resposta.encode('utf-8'))
        ult = tree.find('.//{http://www.portalfiscal.inf.br/nfe}ultNSU')
        if ult is not None and ult.text.isdigit():
            return ult.text.zfill(15)
    except Exception:
        pass
    return None

def extrair_status(xml_resposta):
    """
    Retorna (cStat, xMotivo) do retDistDFeInt.
    """
    try:
        tree = etree.fromstring(xml_resposta.encode('utf-8'))
        # namespace padrão
        ns = {'ret': 'http://www.portalfiscal.inf.br/nfe'}
        cstat = tree.find('.//ret:cStat', namespaces=ns)
        xmot  = tree.find('.//ret:xMotivo', namespaces=ns)
        return (cstat.text if cstat is not None else None,
                xmot.text  if xmot  is not None else None)
    except Exception:
        return (None, None)

def extrair_xmls_e_chaves(xml_resposta):
    resultados = []
    tree = etree.fromstring(xml_resposta.encode('utf-8'))
    for doc in tree.findall('.//{http://www.portalfiscal.inf.br/nfe}docZip'):
        nsu = doc.get('NSU', '')
        try:
            bin_data = base64.b64decode(doc.text)
            xml_nf = gzip.decompress(bin_data).decode('utf-8')
            resultados.append((nsu, xml_nf))
        except Exception:
            continue
    return resultados

def formatar_brl(valor):
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return valor or ''

def ler_dados_detalhados_nfe(xml_str):
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    tree = etree.fromstring(xml_str.encode('utf-8'))
    infnfe = tree.find('.//nfe:infNFe', namespaces=ns)
    if infnfe is None:
        return {}
    ide = infnfe.find('nfe:ide', namespaces=ns)
    emit = infnfe.find('nfe:emit', namespaces=ns)
    dest = infnfe.find('nfe:dest', namespaces=ns)
    total = infnfe.find('nfe:total/nfe:ICMSTot', namespaces=ns)
    motivo = next((e.text for e in tree.iter() if e.tag.endswith('xMotivo')), '')
    vnf = total.findtext('nfe:vNF', namespaces=ns) if total is not None else ''
    dados = {
        'IE Tomador': dest.findtext('nfe:IE', namespaces=ns) or '',
        'Filial': dest.findtext('nfe:IE', namespaces=ns) or '',
        'Nome': emit.findtext('nfe:xNome', namespaces=ns) or '',
        'CNPJ/CPF': (emit.findtext('nfe:CNPJ', namespaces=ns)
                     or emit.findtext('nfe:CPF', namespaces=ns)) or '',
        'Num': ide.findtext('nfe:nNF', namespaces=ns) or '',
        'DtEmi': ide.findtext('nfe:dhEmi', namespaces=ns)[:10] or '',
        'Tipo': 'NFe',
        'Valor': formatar_brl(vnf),
        'Status': motivo,
        'UF': '',
        'Chave': infnfe.attrib.get('Id','')[-44:],
        'Natureza': ide.findtext('nfe:natOp', namespaces=ns) or ''
    }
    return dados

def listar_todos_xmls_detalhados_multiplos(*pastas):
    resultado = []
    for base in pastas:
        for raiz, _, arquivos in os.walk(base):
            for arq in arquivos:
                if not arq.lower().endswith('.xml'):
                    continue
                caminho = os.path.join(raiz, arq)
                try:
                    with open(caminho, encoding='utf-8') as f:
                        xml = f.read()
                    dados = ler_dados_detalhados_nfe(xml)
                    if dados.get('Chave'):
                        resultado.append(dados)
                except Exception:
                    continue
    return resultado

def salvar_xml_organizado(xml_nf, dados, informante):
    pasta_base = obter_pasta_armazenamento(informante)
    agora = datetime.now()
    numero = dados.get('Num','')
    emissor = re.sub(r'[^a-zA-Z0-9 _-]', '', dados.get('Nome',''))
    nome_arquivo = f"NF {numero or ''} {emissor or 'FORNECEDOR'}.xml"
    if pasta_base:
        ano, mes, dia = agora.strftime('%Y'), agora.strftime('%m'), agora.strftime('%d')
        dest_dir = os.path.join(pasta_base, informante, ano, mes, dia)
    else:
        dest_dir = PASTA_XMLS
    os.makedirs(dest_dir, exist_ok=True)
    destino = os.path.join(dest_dir, nome_arquivo)
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(xml_nf)
    registrar_xml_baixado(dados['Chave'], dados['CNPJ/CPF'])
