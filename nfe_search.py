#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nfe_search.py -- Busca distribuições de NF-e e consulta de protocolo para status.
Com validação de XML por XSD (NF-e 4.00) antes de enviar ou processar.
"""
import os
import gzip
import base64
import logging
import sqlite3
from pathlib import Path
from datetime import datetime

import requests
import requests_pkcs12
import time
from datetime import datetime
from requests.exceptions import RequestException
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Fault
from lxml import etree
# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
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
logger.debug("Iniciando nfe_search.py")

BASE = Path(__file__).parent
# -------------------------------------------------------------------
# Fluxo NSU
# -------------------------------------------------------------------
def ciclo_nsu(db, parser, intervalo=3600):
    """
    Executa o ciclo de busca de NSU para todos os certificados cadastrados.
    Repetidamente a cada intervalo (segundos).
    """
    while True:
        logger.info(f"Iniciando busca periódica de NSU em {datetime.now().isoformat()}")
        for cnpj, path, senha, inf, cuf in db.get_certificados():
            svc = NFeService(path, senha, cnpj, cuf)
            ult_nsu = db.get_last_nsu(inf)
            logger.debug(f"Buscando notas a partir do NSU {ult_nsu} para {inf}")

            while True:
                resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", ult_nsu)
                if not resp:
                    logger.warning(f"Falha ao buscar NSU para {inf}")
                    break  # Próximo certificado

                cStat = parser.extract_cStat(resp)
                if cStat == '656':  # Consumo indevido, bloqueio temporário
                    logger.warning(f"Consumo indevido, aguardando desbloqueio para {inf}")
                    break

                docs = parser.extract_docs(resp)
                if not docs:
                    logger.info(f"Nenhum novo docZip para {inf}")
                    break

                for nsu, xml in docs:
                    try:
                        validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                        tree = etree.fromstring(xml.encode('utf-8'))
                        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                        if infnfe is None:
                            continue
                        chave = infnfe.attrib.get('Id','')[-44:]
                        db.registrar_xml(chave, cnpj)
                    except Exception:
                        logger.exception("Erro ao processar docZip")

                ult = parser.extract_last_nsu(resp)
                if ult and ult != ult_nsu:
                    db.set_last_nsu(inf, ult)
                    ult_nsu = ult
                else:
                    break  # Não há mais novos, encerra o loop para este certificado

        logger.info(f"Busca de NSU finalizada. Dormindo por {intervalo/60:.0f} minutos...")
        time.sleep(intervalo)
# -------------------------------------------------------------------
# Validação de XML com XSD
# -------------------------------------------------------------------
def find_xsd(xsd_name, base_dir=None):
    """
    Busca recursiva pelo XSD pelo nome em base_dir e subpastas.
    Retorna o Path ou None.
    """
    if base_dir is None:
        base_dir = Path(__file__).parent
    base_dir = Path(base_dir)
    for p in base_dir.rglob(xsd_name):
        if p.exists():
            logging.debug(f"XSD encontrado: {p}")
            return p
    logging.debug(f"XSD não encontrado: {xsd_name} em {base_dir}")
    return None

def validar_xml_auto(xml_string, prefer_xsd=None):
    """
    Valida um XML string usando o XSD mais adequado:
      - tenta prefer_xsd se informado,
      - senão tenta pelo nome do elemento raiz (usando mapeamento padrão),
      - busca o XSD no diretório do script e em subpastas,
      - registra todas tentativas e erros.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    doc = etree.fromstring(xml_string.encode("utf-8"), parser)
    root = doc.tag.split("}")[-1]  # Remove namespace, pega só o nome

    # Mapeamento padrão de elemento raiz para XSD
    root2xsd = {
        "consSitNFe": "consSitNFe_v4.00.xsd",
        "retConsSitNFe": "retConsSitNFe_v4.00.xsd",
        "NFe": "leiauteNFe_v4.00.xsd",
        "enviNFe": "leiauteNFe_v4.00.xsd",
        "procNFe": "leiauteNFe_v4.00.xsd",
        "distDFeInt": "distDFeInt_v1.01.xsd",
        "retDistDFeInt": "retDistDFeInt_v1.01.xsd",
    }


    tried = []
    # 1) Tentar prefer_xsd se informado
    if prefer_xsd:
        path = find_xsd(prefer_xsd)
        tried.append(str(path) if path else prefer_xsd)
        if path and path.exists():
            try:
                with open(path, "rb") as f:
                    schema_doc = etree.parse(f, parser)
                schema = etree.XMLSchema(schema_doc)
                schema.assertValid(doc)
                logging.debug(f"XML validado com sucesso contra {prefer_xsd} ({path})")
                return True
            except Exception as e:
                logging.error(f"Erro ao validar XML com XSD {prefer_xsd}: {e}")

    # 2) Tentar pelo elemento raiz
    xsd_name = root2xsd.get(root)
    if xsd_name:
        path = find_xsd(xsd_name)
        tried.append(str(path) if path else xsd_name)
        if path and path.exists():
            try:
                with open(path, "rb") as f:
                    schema_doc = etree.parse(f, parser)
                schema = etree.XMLSchema(schema_doc)
                schema.assertValid(doc)
                logging.debug(f"XML validado com sucesso contra {xsd_name} ({path})")
                return True
            except Exception as e:
                logging.error(f"Erro ao validar XML com XSD {xsd_name}: {e}")

    # 3) Debug extra: registrar tentativas e o root do XML
    logging.debug(f"Tentativas de XSD para root '{root}': {tried}")
    raise Exception(f"Não foi possível validar o XML. Elemento raiz: {root}. XSDs tentados: {tried}")
# -------------------------------------------------------------------
# URLs dos serviços
# -------------------------------------------------------------------
URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"
    "NFeDistribuicaoDFe.asmx?wsdl"
)
CONSULTA_WSDL = {
    '50': "https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4?wsdl",  # MS
    # ... os demais já estavam no seu dicionário, mas só MS interessa aqui.
}
URL_CONSULTA_FALLBACK = (
    "https://www1.nfe.fazenda.gov.br/NFeConsultaProtocolo/"
    "NFeConsultaProtocolo.asmx?wsdl"
)
# -------------------------------------------------------------------
# Banco de Dados
# -------------------------------------------------------------------
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize()
        logger.debug(f"Banco inicializado em {db_path}")

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
            cur.execute('''CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY,
                cnpj_cpf TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nf_status (
                chNFe TEXT PRIMARY KEY,
                cStat TEXT,
                xMotivo TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            conn.commit()
            logger.debug("Tabelas verificadas/criadas no banco")

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
            last = row[0] if row else "000000000000000"
            logger.debug(f"Último NSU para {informante}: {last}")
            return last

    def set_last_nsu(self, informante, nsu):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU atualizado para {informante}: {nsu}")

    def registrar_xml(self, chave, cnpj):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
                (chave, cnpj)
            )
            conn.commit()
            logger.debug(f"XML registrado: {chave} (CNPJ {cnpj})")

    def get_chaves_missing_status(self):
        with self._connect() as conn:
            rows = conn.execute('''
                SELECT x.chave, x.cnpj_cpf
                FROM xmls_baixados x
                LEFT JOIN nf_status n
                ON x.chave = n.chNFe
                WHERE n.chNFe IS NULL
            ''').fetchall()
            logger.debug(f"Chaves sem status: {rows}")
            return rows

    def set_nf_status(self, chave, cStat, xMotivo):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nf_status (chNFe,cStat,xMotivo) VALUES (?,?,?)",
                (chave, cStat, xMotivo)
            )
            conn.commit()
            logger.debug(f"Status gravado: {chave} → {cStat} / {xMotivo}")

    def find_cert_by_cnpj(self, cnpj):
        for row in self.get_certificados():
            if row[0] == cnpj:
                return row
        return None

# -------------------------------------------------------------------
# Processador de XML
# -------------------------------------------------------------------
class XMLProcessor:
    NS = {'nfe':'http://www.portalfiscal.inf.br/nfe'}

    def extract_docs(self, resp_xml):
        logger.debug("Extraindo docs de distribuição")
        docs = []
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        for dz in tree.findall('.//nfe:docZip', namespaces=self.NS):
            data = base64.b64decode(dz.text or '')
            xml  = gzip.decompress(data).decode('utf-8')
            nsu  = dz.get('NSU','')
            docs.append((nsu, xml))
        logger.debug(f"{len(docs)} documentos extraídos")
        return docs

    def extract_last_nsu(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        ult = tree.find('.//nfe:ultNSU', namespaces=self.NS)
        last = ult.text.zfill(15) if ult is not None and ult.text else None
        logger.debug(f"último NSU extraído: {last}")
        return last

    def extract_cStat(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        cs = tree.find('.//nfe:cStat', namespaces=self.NS)
        stat = cs.text if cs is not None else None
        logger.debug(f"cStat extraído: {stat}")
        return stat

    def parse_protNFe(self, xml_obj):
        logger.debug("Parseando protocolo NF-e")
        # Se já for Element, use direto
        if isinstance(xml_obj, etree._Element):
            tree = xml_obj
        else:
            tree = etree.fromstring(xml_obj.encode('utf-8'))
        prot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}protNFe')
        if prot is None:
            logger.debug("nenhum protNFe encontrado")
            return None, None, None
        chNFe   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}chNFe') or ''
        cStat   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}cStat') or ''
        xMotivo = prot.findtext('{http://www.portalfiscal.inf.br/nfe}xMotivo') or ''
        logger.debug(f"Parse protocolo → chNFe={chNFe}, cStat={cStat}, xMotivo={xMotivo}")
        return chNFe, cStat, xMotivo

# -------------------------------------------------------------------
# Serviço SOAP
# -------------------------------------------------------------------
class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        logger.debug(f"Inicializando serviço para informante={informante}, cUF={cuf}")
        sess = requests.Session()
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        trans = Transport(session=sess)
        self.dist_client = Client(wsdl=URL_DISTRIBUICAO, transport=trans)
        wsdl = CONSULTA_WSDL.get(str(cuf), URL_CONSULTA_FALLBACK)
        try:
            self.cons_client = Client(wsdl=wsdl, transport=trans)
            logger.debug(f"Cliente de protocolo inicializado: {wsdl}")
        except Exception as e:
            self.cons_client = None
            logger.warning(f"Falha ao inicializar WSDL de protocolo ({wsdl}): {e}")
        self.informante = informante
        self.cuf        = cuf

    def fetch_by_cnpj(self, tipo, ult_nsu):
        logger.debug(f"Chamando distribuição: tipo={tipo}, informante={self.informante}, ultNSU={ult_nsu}")
        distInt = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(distInt, "tpAmb").text    = "1"
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, tipo).text       = self.informante
        sub = etree.SubElement(distInt, "distNSU")
        etree.SubElement(sub, "ultNSU").text       = ult_nsu

        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        # Valide antes de enviar
        try:
            validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
        except Exception as e:
            logger.error("XML de distribuição não passou na validação XSD. Corrija antes de enviar.")
            return None

        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
        except Fault as fault:
            logger.error(f"SOAP Fault Distribuição: {fault}")
            return None
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.debug(f"Resposta Distribuição:\n{xml_str}")
        return xml_str

    def fetch_prot_nfe(self, chave):
        """
        Consulta o protocolo da NF-e pela chave, validando o XML de envio e resposta.
        """
        if not self.cons_client:
            logger.debug("Cliente de protocolo não disponível")
            return None

        logger.debug(f"Chamando protocolo para chave={chave}")
        NAMESPACE = "http://www.portalfiscal.inf.br/nfe"
        # Cria o XML da consulta (sem prefixo de namespace)
        cons = etree.Element("consSitNFe", versao="4.00", xmlns=NAMESPACE)
        etree.SubElement(cons, "tpAmb").text = "1"
        etree.SubElement(cons, "xServ").text = "CONSULTAR"
        etree.SubElement(cons, "chNFe").text = chave
        xml_envio = etree.tostring(cons, encoding='utf-8').decode()

        # Valida o XML de consulta (buscando consSitNFe_v4.00.xsd em subpastas)
        try:
            validar_xml_auto(xml_envio, 'consSitNFe_v4.00.xsd')
        except Exception as e:
            logger.error("XML de consulta protocolo não passou na validação XSD.")
            return None

        # Chama o serviço SOAP
        try:
            resp = self.cons_client.service.nfeConsultaNF(cons)
        except Fault as fault:
            logger.error(f"SOAP Fault Protocolo: {fault}")
            return None

        # Zeep pode retornar lxml.Element, string, ou objeto
        if hasattr(resp, 'decode'):
            resp_xml = resp.decode()
        elif hasattr(resp, '__str__'):
            resp_xml = str(resp)
        else:
            resp_xml = etree.tostring(resp, encoding="utf-8").decode()

        # Protege contra respostas inválidas (vazia, HTML, etc)
        if not resp_xml or resp_xml.strip().startswith('<html') or resp_xml.strip() == '':
            logger.warning("Resposta inválida da SEFAZ (não é XML): %s", resp_xml)
            return None

        # (Opcional) Salva para depuração
        # with open('ult_resposta_protocolo.xml', 'w', encoding='utf-8') as f:
        #     f.write(resp_xml)

        # Valida o XML da resposta (padrão é leiauteNFe_v4.00.xsd, mas pode mudar conforme SEFAZ)
        try:
            validar_xml_auto(resp_xml, 'leiauteNFe_v4.00.xsd')
        except Exception:
            logger.warning("Resposta da SEFAZ não passou na validação XSD.")
            return None

        logger.debug(f"Resposta Protocolo (raw):\n{resp_xml}")
        return resp_xml

# -------------------------------------------------------------------
# Fluxo Principal
# -------------------------------------------------------------------
def main():
    BASE = Path(__file__).parent
    db = DatabaseManager(BASE / "notas.db")
    parser = XMLProcessor()
    logger.info(f"=== Início da busca: {datetime.now().isoformat()} ===")
    # 1) Distribuição
    for cnpj, path, senha, inf, cuf in db.get_certificados():
        logger.debug(f"Processando certificado: CNPJ={cnpj}, arquivo={path}, informante={inf}, cUF={cuf}")
        svc      = NFeService(path, senha, cnpj, cuf)
        last_nsu = db.get_last_nsu(inf)
        resp     = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
        if not resp:
            continue
        cStat = parser.extract_cStat(resp)
        ult   = parser.extract_last_nsu(resp)
        if cStat == '656':
            logger.info(f"{inf}: Consumo indevido (656), manter NSU em {last_nsu}")
        else:
            if ult:
                db.set_last_nsu(inf, ult)
            for nsu, xml in parser.extract_docs(resp):
                try:
                    validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                    tree   = etree.fromstring(xml.encode('utf-8'))
                    infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                    if infnfe is None:
                        logger.debug("infNFe não encontrado no XML, pulando")
                        continue
                    chave  = infnfe.attrib.get('Id','')[-44:]
                    db.registrar_xml(chave, cnpj)
                except Exception:
                    logger.exception("Erro ao processar docZip")
    # 2) Consulta de Protocolo
    faltam = db.get_chaves_missing_status()
    if not faltam:
        logger.info("Nenhuma chave faltando status")
    else:
        for chave, cnpj in faltam:
            cert = db.find_cert_by_cnpj(cnpj)
            if not cert:
                logger.warning(f"Certificado não encontrado para {cnpj}, ignorando {chave}")
                continue
            _, path, senha, inf, cuf = cert
            svc = NFeService(path, senha, cnpj, cuf)
            logger.debug(f"Consultando protocolo para NF-e {chave} (informante {inf})")
            prot_xml = svc.fetch_prot_nfe(chave)
            if not prot_xml:
                continue
            ch, cStat, xMotivo = parser.parse_protNFe(prot_xml)
            if ch:
                db.set_nf_status(ch, cStat, xMotivo)
    logger.info(f"=== Busca concluída: {datetime.now().isoformat()} ===")

if __name__ == "__main__":
    BASE = Path(__file__).parent
    db = DatabaseManager(BASE / "notas.db")
    parser = XMLProcessor()
    ciclo_nsu(db, parser, intervalo=3600)  # 3600 segundos = 1h