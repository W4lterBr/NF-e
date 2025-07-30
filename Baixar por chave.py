import os
import sys
import logging
import sqlite3
import gzip
import base64
from pathlib import Path
import pandas as pd
from lxml import etree
import tkinter as tk
from tkinter import filedialog, messagebox
from zeep import Client
from zeep.transports import Transport
import requests
import requests_pkcs12
import time

# --- Configuração de logs ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("BaixarNFE")

# --- Constantes ---
DB_PATH = Path(__file__).parent / "notas.db"
PASTA_XMLS = Path(__file__).parent / "xmls"
PASTA_XMLS.mkdir(exist_ok=True)

URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl"
)

# --- Tabela de endpoints dos webservices de evento por UF (produção) ---
ENDPOINTS_EVENTO = {
    12: "https://nfe.sefaz.ac.gov.br/ws/recepcaoevento4.asmx?wsdl",   # AC
    27: "https://nfe.sefaz.al.gov.br/ws/recepcaoevento4.asmx?wsdl",   # AL
    13: "https://nfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4?wsdl", # AM
    16: "https://nfe.sefaz.ap.gov.br/ws/recepcaoevento4.asmx?wsdl",   # AP
    29: "https://nfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl", # BA
    23: "https://nfe.sefaz.ce.gov.br/ws/recepcaoevento4.asmx?wsdl",   # CE
    53: "https://nfe.fazenda.df.gov.br/ws/recepcaoevento4.asmx?wsdl", # DF
    32: "https://nfe.sefaz.es.gov.br/ws/recepcaoevento4.asmx?wsdl",   # ES
    52: "https://nfe.sefaz.go.gov.br/ws/recepcaoevento4.asmx?wsdl",   # GO
    21: "https://sistemas.sefaz.ma.gov.br/ws/recepcaoevento4/RecepcaoEvento4?wsdl", # MA
    31: "https://nfe.fazenda.mg.gov.br/ws/recepcaoevento4.asmx?wsdl", # MG
    50: "https://nfe.sefaz.ms.gov.br/ws/recepcaoevento4.asmx?wsdl",   # MS
    51: "https://nfe.sefaz.mt.gov.br/ws/recepcaoevento4.asmx?wsdl",   # MT
    15: "https://nfe.sefa.pa.gov.br/ws/recepcaoevento4.asmx?wsdl",    # PA
    25: "https://nfe.sefaz.pb.gov.br/ws/recepcaoevento4.asmx?wsdl",   # PB
    26: "https://nfe.sefaz.pe.gov.br/nfe-service/services/NfeRecepcaoEvento4?wsdl", # PE
    22: "https://nfe.sefaz.pi.gov.br/ws/recepcaoevento4.asmx?wsdl",   # PI
    41: "https://nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4?wsdl",     # PR
    33: "https://nfe.fazenda.rj.gov.br/ws/recepcaoevento4.asmx?wsdl", # RJ
    24: "https://nfe.set.rn.gov.br/ws/recepcaoevento4.asmx?wsdl",     # RN
    43: "https://nfe.sefaz.rs.gov.br/ws/recepcaoevento4/recepcaoevento4.asmx?wsdl", # RS
    11: "https://nfe.sefin.ro.gov.br/ws/recepcaoevento4.asmx?wsdl",   # RO
    14: "https://nfe.sefaz.rr.gov.br/ws/recepcaoevento4.asmx?wsdl",   # RR
    42: "https://nfe.sef.sc.gov.br/ws/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx?wsdl", # SC
    28: "https://nfe.sefaz.se.gov.br/ws/recepcaoevento4.asmx?wsdl",   # SE
    35: "https://nfe.fazenda.sp.gov.br/ws/nfeevento4.asmx?wsdl",      # SP
    17: "https://nfe.sefaz.to.gov.br/ws/recepcaoevento4.asmx?wsdl",   # TO
}

NAMESPACE_NFE = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

def get_endpoint_evento(cuf):
    url = ENDPOINTS_EVENTO.get(int(cuf))
    if not url:
        raise Exception(f"UF {cuf} não possui endpoint configurado. Informe para suporte.")
    return url

# --- Função para ler certificados do banco ---
def ler_certificados(db_path):
    logger.info(f"Lendo certificados do banco de dados: {db_path}")
    conn = sqlite3.connect(db_path)
    certs = conn.execute("SELECT cnpj_cpf, caminho, senha, informante, cUF_autor FROM certificados").fetchall()
    conn.close()
    for c in certs:
        logger.info(f"Certificado carregado: {c}")
    return certs

# --- Função para selecionar arquivo Excel via interface gráfica ---
def selecionar_arquivo_excel():
    root = tk.Tk()
    root.withdraw()
    arquivo = filedialog.askopenfilename(
        title="Selecione o arquivo de chaves (Excel)",
        filetypes=[("Planilhas Excel", "*.xlsx *.xls")]
    )
    if not arquivo:
        messagebox.showerror("Erro", "Arquivo não selecionado!")
        sys.exit(1)
    logger.info(f"Arquivo selecionado: {arquivo}")
    return arquivo

# --- Função para importar chaves do Excel ---
def importar_chaves(excel_path):
    logger.info(f"Lendo chaves do arquivo: {excel_path}")
    df = pd.read_excel(excel_path)
    chaves = []
    for col in df.columns:
        if "chave" in col.lower():
            chaves = df[col].astype(str).str.extract(r'(\d{44})')[0].dropna().tolist()
            break
    if not chaves:
        logger.warning("Nenhuma coluna de chave encontrada ou nenhuma chave válida no Excel!")
    logger.info(f"{len(chaves)} chaves importadas do Excel")
    return chaves

# --- Função para enviar o evento Ciência da Operação ---
def enviar_ciencia_operacao(cert_path, senha, informante, cuf, chave, num_seq=1):
    url_evento = get_endpoint_evento(cuf)
    session = requests.Session()
    session.mount('https://', requests_pkcs12.Pkcs12Adapter(pkcs12_filename=cert_path, pkcs12_password=senha))
    transport = Transport(session=session)
    client = Client(wsdl=url_evento, transport=transport)

    id_evento = f"ID210210{chave}0{num_seq:02}"
    dhEvento = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    tag = 'CNPJ' if len(informante) == 14 else 'CPF'

    xml_envio = f'''<envEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
        <idLote>1</idLote>
        <evento versao="1.00">
            <infEvento Id="{id_evento}">
                <cOrgao>{cuf}</cOrgao>
                <tpAmb>1</tpAmb>
                <{tag}>{informante}</{tag}>
                <chNFe>{chave}</chNFe>
                <dhEvento>{dhEvento}</dhEvento>
                <tpEvento>210210</tpEvento>
                <nSeqEvento>{num_seq}</nSeqEvento>
                <verEvento>1.00</verEvento>
                <detEvento versao="1.00">
                    <descEvento>Ciência da Operação</descEvento>
                </detEvento>
            </infEvento>
        </evento>
    </envEvento>'''

    try:
        resposta = client.service.nfeRecepcaoEvento4(nfeDadosMsg=xml_envio)
        # Salvar a resposta para debug
        debug_evt = Path(cert_path).parent / f'debug_evento_{chave}.xml'
        debug_evt.write_text(str(resposta), encoding='utf-8')
        print(f"[DEBUG] Resposta evento da SEFAZ salva em: {debug_evt}")
        # Parse da resposta para status
        root = etree.fromstring(str(resposta).encode('utf-8'))
        cStat = root.find('.//{http://www.portalfiscal.inf.br/nfe}cStat')
        xMotivo = root.find('.//{http://www.portalfiscal.inf.br/nfe}xMotivo')
        return (int(cStat.text), xMotivo.text)
    except Exception as e:
        print(f"[ERRO] Falha ao enviar evento para chave {chave}: {e}")
        return (0, str(e))

# --- Classe para consumir o Webservice ---
class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        session = requests.Session()
        session.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        transport = Transport(session=session)
        self.client = Client(wsdl=URL_DISTRIBUICAO, transport=transport)
        self.informante = informante
        self.cuf = cuf

    def fetch_by_chave(self, chave):
        root = etree.Element("distDFeInt",
            xmlns=NAMESPACE_NFE['ns'], versao="1.01"
        )
        etree.SubElement(root, "tpAmb").text    = "1"
        etree.SubElement(root, "cUFAutor").text = str(self.cuf)
        tag = "CNPJ" if len(self.informante) == 14 else "CPF"
        etree.SubElement(root, tag).text        = self.informante
        cons = etree.SubElement(root, "consChNFe")
        etree.SubElement(cons, "chNFe").text    = chave

        try:
            resposta = self.client.service.nfeDistDFeInteresse(nfeDadosMsg=root)
            resp_xml = etree.tostring(resposta, encoding='utf-8').decode()
            return resp_xml
        except Exception as e:
            logger.error(f"Erro ao consultar chave {chave}: {e}")
            return None

# --- Função para consultar e salvar XMLs ---
def consultar_chave_nfe(service, chave, pasta_xmls):
    print(f"\nConsultando chave: {chave}")
    resp_xml = service.fetch_by_chave(chave)
    if not resp_xml:
        print(f"[ERRO] Resposta vazia da SEFAZ para chave {chave}")
        return False

    debug_path = pasta_xmls / f'debug_resp_{chave}.xml'
    debug_path.write_text(resp_xml, encoding='utf-8')
    print(f"[DEBUG] Resposta da SEFAZ salva em: {debug_path}")

    tree = etree.fromstring(resp_xml.encode('utf-8'))
    ns = NAMESPACE_NFE
    cStat = tree.find('.//ns:cStat', namespaces=ns)
    xMotivo = tree.find('.//ns:xMotivo', namespaces=ns)
    print(f"Resposta SEFAZ: cStat={cStat.text if cStat is not None else '?'} | Motivo={xMotivo.text if xMotivo is not None else '?'}")

    doczips = tree.findall('.//ns:docZip', namespaces=ns)
    if not doczips:
        print(f"[ATENÇÃO] Nenhum docZip retornado para chave {chave} (provavelmente NF-e não está disponível para este certificado neste momento).")
        return False

    for dz in doczips:
        nsu = dz.get('NSU', 'S/NSU')
        content = dz.text or ''
        try:
            xml_bytes = gzip.decompress(base64.b64decode(content))
            xml_path = pasta_xmls / f'{chave}.xml'
            xml_path.write_bytes(xml_bytes)
            print(f"NF-e salva em: {xml_path}")
            return True
        except Exception as exc:
            print(f"[ERRO] Falha ao decodificar docZip para chave {chave}: {exc}")
            continue
    return False

# --- Função principal ---
def main():
    certs = ler_certificados(DB_PATH)
    if not certs:
        logger.error("Nenhum certificado cadastrado no banco.")
        sys.exit(1)

    cnpj_cpf, caminho, senha, informante, cuf = certs[0]
    if not os.path.exists(caminho):
        logger.error(f"Arquivo PFX não encontrado: {caminho}")
        sys.exit(1)

    excel_path = selecionar_arquivo_excel()
    chaves = importar_chaves(excel_path)
    if not chaves:
        logger.error("Nenhuma chave encontrada.")
        sys.exit(1)

    service = NFeService(caminho, senha, informante, cuf)

    for chave in chaves:
        # 1. Enviar manifestação Ciência da Operação
        print(f"\nEnviando evento Ciência da Operação para chave: {chave}")
        status, motivo = enviar_ciencia_operacao(caminho, senha, informante, cuf, chave)
        print(f"Retorno evento: cStat={status} | Motivo={motivo}")
        if status != 135:
            print(f"[ATENÇÃO] Evento não autorizado para chave {chave}. Pular download.")
            continue
        # 2. Se autorizado, tentar baixar o XML
        consultar_chave_nfe(service, chave, PASTA_XMLS)
        # --- Descomente abaixo se quiser respeitar o limite SEFAZ (20/hora) ---
        # time.sleep(200)

if __name__ == "__main__":
    main()
