"""
Serviço de consulta e download de CT-e via SEFAZ
Implementa o WS CTeDistribuicaoDFe conforme documentação oficial
"""

import logging
from pathlib import Path
import requests
import requests_pkcs12
from lxml import etree
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Fault
import base64
import gzip
from datetime import datetime

logger = logging.getLogger(__name__)

# Endpoints oficiais CT-e (Ambiente Nacional - Receita Federal)
# Fonte: https://www.cte.fazenda.gov.br/portal/webServices.aspx
URL_CTE_DISTRIBUICAO_PROD = "https://www1.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"
URL_CTE_DISTRIBUICAO_HOM = "https://hom.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"

# Namespace CTe
NS_CTE = "http://www.portalfiscal.inf.br/cte"


def get_data_dir():
    """Retorna o diretório de dados do aplicativo."""
    import sys
    import os
    
    if getattr(sys, 'frozen', False):
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "Busca XML"
    else:
        data_dir = Path(__file__).parent.parent
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def save_debug_soap_cte(informante: str, tipo: str, conteudo: str, prefixo: str = ""):
    """Salva arquivos SOAP CT-e para debug."""
    try:
        debug_dir = get_data_dir() / "xmls" / "Debug de notas"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        nome_base = f"{timestamp}_{informante}"
        if prefixo:
            nome_base = f"{nome_base}_{prefixo}"
        nome_arquivo = f"{nome_base}_{tipo}.xml"
        
        arquivo_path = debug_dir / nome_arquivo
        arquivo_path.write_text(conteudo, encoding='utf-8')
        
        logger.debug(f"📝 Debug CTe salvo: {nome_arquivo}")
        return str(arquivo_path)
    except Exception as e:
        logger.error(f"Erro ao salvar debug SOAP CTe: {e}")
        return None


class CTeService:
    """
    Serviço de consulta de CT-e via Distribuição de Documentos Fiscais Eletrônicos (DFe)
    
    Documentos suportados:
    - procCTe: CT-e autorizado completo
    - resCTe: Resumo do CT-e
    - procEventoCTe: Eventos (cancelamento, EPEC, etc.)
    """
    
    def __init__(self, cert_path, senha, informante, cuf, ambiente='producao'):
        """
        Inicializa o serviço CT-e
        
        Args:
            cert_path: Caminho do certificado PFX
            senha: Senha do certificado
            informante: CNPJ/CPF do informante
            cuf: Código UF do informante
            ambiente: 'producao' ou 'homologacao'
        """
        logger.debug(f"Inicializando CTeService: informante={informante}, cUF={cuf}, ambiente={ambiente}")
        
        # Configura sessão HTTP com certificado
        sess = requests.Session()
        sess.verify = False  # Desabilita verificação SSL
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        
        # Seleciona endpoint baseado no ambiente
        url_dist = URL_CTE_DISTRIBUICAO_PROD if ambiente == 'producao' else URL_CTE_DISTRIBUICAO_HOM
        
        trans = Transport(session=sess)
        try:
            self.dist_client = Client(wsdl=url_dist, transport=trans)
            logger.debug(f"Cliente CTe inicializado: {url_dist}")
        except Exception as e:
            logger.error(f"Falha ao inicializar cliente CTe: {e}")
            raise
        
        self.informante = informante
        self.cuf = cuf
        self.ambiente = '1' if ambiente == 'producao' else '2'
    
    def fetch_by_cnpj(self, tipo, ult_nsu):
        """
        Busca documentos CT-e por CNPJ/CPF usando NSU
        
        Args:
            tipo: 'CNPJ' ou 'CPF'
            ult_nsu: Último NSU processado (formato: 000000000000000)
        
        Returns:
            XML da resposta ou None em caso de erro
        """
        logger.debug(f"Consultando CTe: tipo={tipo}, informante={self.informante}, ultNSU={ult_nsu}")
        
        # Monta XML de consulta conforme estrutura CTeDistribuicaoDFe
        distInt = etree.Element("distDFeInt",
            xmlns=NS_CTE, versao="1.00"
        )
        etree.SubElement(distInt, "tpAmb").text = self.ambiente
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, tipo).text = self.informante
        sub = etree.SubElement(distInt, "distNSU")
        etree.SubElement(sub, "ultNSU").text = ult_nsu
        
        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        logger.debug(f"XML de consulta CTe:\n{xml_envio}")
        
        # 🔍 DEBUG: Salva XML enviado
        save_debug_soap_cte(self.informante, "request", xml_envio, prefixo="cte_dist")
        
        # 🌐 DEBUG HTTP: Informações da requisição SOAP CT-e
        url_dist = URL_CTE_DISTRIBUICAO_PROD if self.ambiente == '1' else URL_CTE_DISTRIBUICAO_HOM
        logger.info(f"🌐 [{self.informante}] HTTP REQUEST CT-e Distribuição:")
        logger.info(f"   📍 URL: {url_dist}")
        logger.info(f"   🔐 Certificado: Configurado com PKCS12")
        logger.info(f"   📦 Método: POST (SOAP)")
        logger.info(f"   📋 Payload: distDFeInt (ultNSU={ult_nsu}, cUF={self.cuf}, tpAmb={self.ambiente})")
        logger.info(f"   📏 Tamanho XML: {len(xml_envio)} bytes")
        
        # Envia requisição SOAP
        try:
            resp = self.dist_client.service.cteDistDFeInteresse(cteDadosMsg=distInt)
            
            # 🌐 DEBUG HTTP: Informações da resposta
            logger.info(f"✅ [{self.informante}] HTTP RESPONSE CT-e Distribuição recebida")
            logger.info(f"   📊 Tipo: {type(resp).__name__}")
            if hasattr(resp, '__dict__'):
                logger.debug(f"   🔍 Atributos: {list(resp.__dict__.keys())[:5]}...")
            
        except Fault as fault:
            logger.error(f"SOAP Fault CTe Distribuição: {fault}")
            logger.error(f"   ❌ Falha na comunicação SOAP CT-e")
            # 🔍 DEBUG: Salva erro SOAP
            save_debug_soap_cte(self.informante, "fault", str(fault), prefixo="cte_dist")
            return None
        except Exception as e:
            logger.error(f"❌ [{self.informante}] Erro HTTP na distribuição CT-e: {e}")
            logger.exception(e)
            return None
        
        # Converte resposta para XML
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.info(f"📥 [{self.informante}] Resposta CT-e processada: {len(xml_str)} bytes")
        logger.debug(f"Resposta CTe Distribuição (primeiros 500 chars):\n{xml_str[:500]}")
        
        # 🔍 DEBUG: Salva XML recebido
        save_debug_soap_cte(self.informante, "response", xml_str, prefixo="cte_dist")
        
        return xml_str
    
    def extrair_docs(self, xml_resposta):
        """
        Extrai documentos compactados (docZip) da resposta SOAP
        
        Args:
            xml_resposta: XML de resposta da SEFAZ
        
        Yields:
            Tuplas (NSU, XML_descompactado)
        """
        import gzip
        import base64
        
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Busca elementos docZip
            for doc_zip in tree.findall(f'.//{{{NS_CTE}}}docZip'):
                nsu = doc_zip.attrib.get('NSU', '')
                schema = doc_zip.attrib.get('schema', '')
                
                # Decodifica e descompacta
                conteudo_b64 = doc_zip.text
                if not conteudo_b64:
                    continue
                
                conteudo_compactado = base64.b64decode(conteudo_b64)
                conteudo_xml = gzip.decompress(conteudo_compactado).decode('utf-8')
                
                logger.debug(f"Documento CTe extraído: NSU={nsu}, schema={schema}")
                
                # 🔍 DEBUG: Salva cada XML extraído
                try:
                    # Identifica tipo do documento
                    if '<resCTe' in conteudo_xml or '<resEvento' in conteudo_xml:
                        tipo_doc = "resumo"
                    elif '<procCTe' in conteudo_xml or '<cteProc' in conteudo_xml:
                        tipo_doc = "cte_completo"
                    elif '<procEventoCTe' in conteudo_xml:
                        tipo_doc = "evento"
                    else:
                        tipo_doc = "documento"
                    
                    save_debug_soap_cte(self.informante, f"xml_extraido_{tipo_doc}_NSU{nsu}", conteudo_xml, prefixo="cte_dist")
                except Exception as e:
                    logger.error(f"Erro ao salvar XML CTe extraído em debug: {e}")
                
                yield (nsu, conteudo_xml, schema)
                
        except Exception as e:
            logger.exception(f"Erro ao extrair documentos CTe: {e}")
    
    def extract_cstat(self, xml_resposta):
        """Extrai código de status da resposta"""
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            cstat_elem = tree.find(f'.//{{{NS_CTE}}}cStat')
            return cstat_elem.text if cstat_elem is not None else None
        except:
            return None
    
    def extract_last_nsu(self, xml_resposta):
        """Extrai último NSU da resposta"""
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            nsu_elem = tree.find(f'.//{{{NS_CTE}}}ultNSU')
            return nsu_elem.text if nsu_elem is not None else None
        except:
            return None
    
    def extract_max_nsu(self, xml_resposta):
        """Extrai NSU máximo disponível"""
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            max_nsu_elem = tree.find(f'.//{{{NS_CTE}}}maxNSU')
            return max_nsu_elem.text if max_nsu_elem is not None else None
        except:
            return None
