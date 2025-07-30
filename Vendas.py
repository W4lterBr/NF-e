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

# --- LOG ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("BaixarNFCE")

# --- CONFIG ---
DB_PATH = Path(__file__).parent / "notas.db"
PASTA_XMLS = Path(__file__).parent / "xmls_nfce"
PASTA_XMLS.mkdir(exist_ok=True)

URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl"
)
NAMESPACE_NFE = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

# --- Banco de Certificados ---
def ler_certificados(db_path):
    logger.info(f"Lendo certificados do banco de dados: {db_path}")
    conn = sqlite3.connect(db_path)
    certs = conn.execute("SELECT cnpj_cpf, caminho, senha, informante, cUF_autor FROM certificados").fetchall()
    conn.close()
    for c in certs:
        logger.info(f"Certificado carregado: {c}")
    return certs

# --- Seleção do Excel ---
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

# --- Serviço SEFAZ ---
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

# --- Consulta NFC-e por chave ---
def consultar_chave_nfce(service, chave, pasta_xmls):
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
    cstat_val = cStat.text if cStat is not None else "?"
    xmotivo_val = xMotivo.text if xMotivo is not None else "?"
    print(f"Resposta SEFAZ: cStat={cstat_val} | Motivo={xmotivo_val}")

    doczips = tree.findall('.//ns:docZip', namespaces=ns)
    baixou = False
    for dz in doczips:
        nsu = dz.get('NSU', 'S/NSU')
        content = dz.text or ''
        try:
            xml_bytes = gzip.decompress(base64.b64decode(content))
            xml_txt = xml_bytes.decode('utf-8')
            # Verifica se é NFC-e (modelo 65)
            mod = ""
            try:
                xml_tree = etree.fromstring(xml_bytes)
                mod_el = xml_tree.find('.//ns:ide/ns:mod', namespaces=ns)
                if mod_el is not None:
                    mod = mod_el.text.strip()
            except Exception:
                pass
            if mod == "65":
                xml_path = pasta_xmls / f'{chave}.xml'
                xml_path.write_text(xml_txt, encoding='utf-8')
                print(f"[SUCESSO] NFC-e salva em: {xml_path}")
                baixou = True
            else:
                print(f"[INFO] Ignorado: documento NSU={nsu} não é NFC-e (modelo retornado: '{mod}')")
        except Exception as exc:
            print(f"[ERRO] Falha ao decodificar docZip para chave {chave}: {exc}")
    if not baixou:
        print(f"[INFO] Nenhuma NFC-e (modelo 65) baixada para a chave {chave}.")
    return baixou

# --- Principal ---
def main():
    certs = ler_certificados(DB_PATH)
    if not certs:
        logger.error("Nenhum certificado cadastrado no banco.")
        sys.exit(1)

    # Usa o primeiro certificado cadastrado
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
        consultar_chave_nfce(service, chave, PASTA_XMLS)

if __name__ == "__main__":
    main()
