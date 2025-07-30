#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_emitidas_db.py -- Baixa XMLs emitidos pelo CNPJ/CPF via distribuição DF-e, 24x7.
Salva apenas NF-e emitidas (não apenas resumos/eventos).
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime
from lxml import etree
import sqlite3
import requests
import requests_pkcs12
from zeep import Client
from zeep.transports import Transport

# ----------------------- CONFIGURAÇÕES ------------------------
BASE = Path(__file__).parent
DB_PATH = BASE / "notas.db"
DIR_EMITIDAS = BASE / "emitidas"
UPDATE_INTERVAL = 3600  # segundos = 1 hora

URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"
    "NFeDistribuicaoDFe.asmx?wsdl"
)

# ------------------------- LOGGER -----------------------------
def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger

logger = setup_logger()

# ------------------- BANCO DE DADOS --------------------------
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY,
                cnpj_cpf TEXT,
                caminho TEXT,
                senha TEXT,
                informante TEXT,
                cUF_autor TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            conn.commit()
            logger.debug("Tabelas verificadas/criadas no banco")
        logger.debug(f"Banco inicializado em {self.db_path}")

    def get_certificados(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()
            logger.debug(f"Certificados carregados: {rows}")
            return rows

    def get_last_nsu(self, informante):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)
            ).fetchone()
            return row[0] if row else "000000000000000"

    def set_last_nsu(self, informante, nsu):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU atualizado para {informante}: {nsu}")

# --------------- SERVIÇO DE DISTRIBUIÇÃO ----------------------
class XMLProcessor:
    NS = {'nfe':'http://www.portalfiscal.inf.br/nfe'}

    def extract_docs(self, resp_xml):
        docs = []
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        for dz in tree.findall('.//nfe:docZip', namespaces=self.NS):
            import gzip, base64
            data = base64.b64decode(dz.text or '')
            xml  = gzip.decompress(data).decode('utf-8')
            nsu  = dz.get('NSU','')
            schema = dz.get('schema','')
            docs.append((nsu, xml, schema))
        logger.debug(f"{len(docs)} documentos extraídos")
        return docs

    def extract_last_nsu(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        ult = tree.find('.//nfe:ultNSU', namespaces=self.NS)
        return ult.text.zfill(15) if ult is not None and ult.text else None

    def extract_cStat(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        cs = tree.find('.//nfe:cStat', namespaces=self.NS)
        return cs.text if cs is not None else None

def is_emitida_por(xml_str, cnpj):
    """Retorna True se a nota foi emitida pelo CNPJ (emitente)"""
    try:
        tree = etree.fromstring(xml_str.encode('utf-8'))
        emit_cnpj = tree.find('.//{http://www.portalfiscal.inf.br/nfe}emit/{http://www.portalfiscal.inf.br/nfe}CNPJ')
        emit_cpf = tree.find('.//{http://www.portalfiscal.inf.br/nfe}emit/{http://www.portalfiscal.inf.br/nfe}CPF')
        doc_emit = (emit_cnpj.text if emit_cnpj is not None else (emit_cpf.text if emit_cpf is not None else ""))
        return doc_emit and doc_emit.zfill(14) == cnpj.zfill(14)
    except Exception as e:
        logger.warning(f"Erro ao identificar emitente do XML: {e}")
        return False

class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        logger.debug(f"Inicializando serviço para informante={informante}, cUF={cuf}")
        sess = requests.Session()
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        trans = Transport(session=sess)
        self.dist_client = Client(wsdl=URL_DISTRIBUICAO, transport=trans)
        self.informante = informante
        self.cuf        = cuf

    def fetch_by_cnpj(self, tipo, ult_nsu):
        logger.debug(f"Chamando distribuição: tipo={tipo}, informante={self.informante}, ultNSU={ult_nsu}")
        from lxml import etree
        distInt = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(distInt, "tpAmb").text    = "1"
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, tipo).text       = self.informante
        sub = etree.SubElement(distInt, "distNSU")
        etree.SubElement(sub, "ultNSU").text       = ult_nsu
        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
        except Exception as fault:
            logger.error(f"SOAP Fault Distribuição: {fault}")
            return None
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.debug(f"Resposta Distribuição:\n{xml_str[:500]}...")  # Mostra só o início para logs longos
        return xml_str

def save_emitidas_from_dfe(cnpj, parser, resp, dir_out):
    os.makedirs(dir_out, exist_ok=True)
    count = 0
    for nsu, xml, schema in parser.extract_docs(resp):
        try:
            tree = etree.fromstring(xml.encode('utf-8'))
            root_tag = tree.tag
            logger.debug(f"NSU {nsu} - Root tag: {root_tag}, schema={schema}")
            # Salve TODO nfeProc só para inspecionar
            if root_tag.endswith('nfeProc'):
                chave = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe').attrib.get('Id','')[-44:]
                path_out = Path(dir_out) / f"{chave}.xml"
                with open(path_out, "w", encoding="utf-8") as f:
                    f.write(xml)
                logger.info(f"NF-e salva: {path_out}")
                count += 1
        except Exception as e:
            logger.warning(f"Falha ao parsear XML do NSU {nsu}: {e}")
    return count

# --------------------- LOOP PRINCIPAL ------------------------
def main():
    logger.info("=== Início da busca de emitidas ===")
    db = DatabaseManager(DB_PATH)
    parser = XMLProcessor()

    while True:
        for cnpj, path, senha, inf, cuf in db.get_certificados():
            logger.info(f"Processando emitente {inf} (CNPJ {cnpj})")
            svc = NFeService(path, senha, inf, cuf)
            last_nsu = db.get_last_nsu(inf)
            resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
            if not resp:
                logger.info(f"Nenhuma resposta do serviço para {inf}")
                continue
            cStat = parser.extract_cStat(resp)
            ult   = parser.extract_last_nsu(resp)
            logger.debug(f"cStat extraído: {cStat}")
            logger.debug(f"último NSU extraído: {ult}")
            if cStat == '656':
                logger.info(f"{inf}: Consumo indevido (656), manter NSU em {last_nsu}")
            elif cStat == '138':  # Documentos localizados
                baixadas = save_emitidas_from_dfe(cnpj, parser, resp, DIR_EMITIDAS)
                logger.info(f"{baixadas} emitidas baixadas neste lote.")
                if ult:
                    db.set_last_nsu(inf, ult)
            else:
                logger.info(f"{inf}: cStat={cStat}, xMotivo desconhecido ou sem docs.")
                if ult:
                    db.set_last_nsu(inf, ult)
        logger.info("=== Busca concluída. Próxima tentativa em 1 hora ===")
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
