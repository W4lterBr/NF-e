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

logger = logging.getLogger(__name__)

# Endpoints oficiais CT-e (Ambiente Nacional - Receita Federal)
# Fonte: https://www.cte.fazenda.gov.br/portal/webServices.aspx
URL_CTE_DISTRIBUICAO_PROD = "https://www1.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"
URL_CTE_DISTRIBUICAO_HOM = "https://hom.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"

# Namespace CTe
NS_CTE = "http://www.portalfiscal.inf.br/cte"


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
        
        # Envia requisição SOAP
        try:
            resp = self.dist_client.service.cteDistDFeInteresse(cteDadosMsg=distInt)
        except Fault as fault:
            logger.error(f"SOAP Fault CTe Distribuição: {fault}")
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar CTe: {e}")
            return None
        
        # Converte resposta para XML
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.debug(f"Resposta CTe Distribuição (primeiros 500 chars):\n{xml_str[:500]}")
        
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
