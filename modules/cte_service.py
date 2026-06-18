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

# Usa o logger raiz para herdar configurações do módulo principal
logger = logging.getLogger('nfe_search')  # Mesmo logger do nfe_search.py

# Desabilita logs verbosos do zeep para evitar "I/O operation on closed file"
logging.getLogger('zeep').setLevel(logging.WARNING)
logging.getLogger('zeep.wsdl').setLevel(logging.WARNING)
logging.getLogger('zeep.xsd').setLevel(logging.WARNING)
logging.getLogger('zeep.transports').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

# Endpoints oficiais CT-e (Ambiente Nacional - Receita Federal)
# Fonte: https://www.cte.fazenda.gov.br/portal/webServices.aspx
# NOTA: CTeDistribuicaoDFe é **exclusivo** do Ambiente Nacional (AN – Receita Federal).
# O SVRS (cte.svrs.rs.gov.br) NÃO oferece este serviço — apenas autorização (v4.00).
URL_CTE_DISTRIBUICAO_PROD = "https://www1.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"
URL_CTE_DISTRIBUICAO_PROD_SVRS = None  # SVRS não possui CTeDistribuicaoDFe
URL_CTE_DISTRIBUICAO_HOM = "https://hom.cte.fazenda.gov.br/CTeDistribuicaoDFe/CTeDistribuicaoDFe.asmx?wsdl"
URL_CTE_DISTRIBUICAO_HOM_SVRS = None  # SVRS não possui CTeDistribuicaoDFe

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

        # Seleciona endpoints (principal e alternativo)
        if ambiente == 'producao':
            url_principal = URL_CTE_DISTRIBUICAO_PROD
            url_alternativa = URL_CTE_DISTRIBUICAO_PROD_SVRS
        else:
            url_principal = URL_CTE_DISTRIBUICAO_HOM
            url_alternativa = URL_CTE_DISTRIBUICAO_HOM_SVRS

        # 🔒 Verificação do certificado do servidor habilitada por padrão (protege
        # contra MITM); só desabilita — e registra em logs/certificado_seguranca.log —
        # para hosts com cadeia de certificado mal configurada.
        from modules.certificate_manager import determinar_verify_para_host
        verificar_servidor = determinar_verify_para_host(url_principal, cert_path, senha)

        # Configura sessão HTTP com certificado
        sess = requests.Session()
        sess.verify = verificar_servidor
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        
        # Configuração de transporte com timeout maior (60s) para CT-e
        trans = Transport(session=sess, timeout=60, operation_timeout=60)

        # Monta lista de URLs a tentar (filtra entradas None)
        urls_tentativas = [(nome, url) for nome, url in [
            ("Nacional", url_principal),
            ("SVRS",     url_alternativa),
        ] if url]

        # Tenta conectar nas URLs disponíveis
        self.dist_client = None
        url_usada = None

        for nome_url, url_dist in urls_tentativas:
            try:
                logger.debug(f"Tentando conectar CT-e via {nome_url}: {url_dist}")
                self.dist_client = Client(wsdl=url_dist, transport=trans)
                url_usada = url_dist
                logger.info(f"✅ Cliente CTe inicializado via {nome_url}: {url_dist}")
                break  # Conectou com sucesso
            except Exception as e:
                logger.warning(f"⚠️ Falha ao conectar CT-e via {nome_url}: {str(e)[:100]}")
                if nome_url == urls_tentativas[-1][0]:  # Era a última tentativa
                    logger.error(f"❌ Falha ao inicializar cliente CTe em TODAS as URLs")
                    raise
                # Continua para próxima URL
        
        # Salva configurações
        self.url_atual = url_usada  # URL que funcionou
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
        logger.info(f"🌐 [{self.informante}] HTTP REQUEST CT-e Distribuição:")
        logger.info(f"   📍 URL: {self.url_atual}")
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

    def fetch_by_nsu(self, nsu):
        """
        Busca CT-e específico por NSU via CTeDistribuicaoDFe (consNSU).
        Nota: CTeDistribuicaoDFe NÃO suporta consChCTe (query por chave) — apenas
        distNSU (sequencial) e consNSU (NSU específico). Para query por chave de acesso
        use NFeService.fetch_prot_cte() que chama CTeConsultaV4.

        Args:
            nsu: NSU de 15 dígitos do documento CT-e

        Returns:
            XML da resposta ou None em caso de erro
        """
        logger.info(f"🔑 [CTe] Consultando via Distribuição DFe por NSU: {nsu}")

        distInt = etree.Element("distDFeInt", xmlns=NS_CTE, versao="1.00")
        etree.SubElement(distInt, "tpAmb").text = self.ambiente
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, "CNPJ").text = self.informante
        sub = etree.SubElement(distInt, "consNSU")
        etree.SubElement(sub, "NSU").text = str(nsu).zfill(15)

        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        save_debug_soap_cte(self.informante, "request", xml_envio, prefixo="cte_dist_nsu")

        logger.info(f"🌐 [{self.informante}] HTTP REQUEST CT-e Por NSU:")
        logger.info(f"   📍 URL: {self.url_atual}")
        logger.info(f"   📋 Payload: distDFeInt (consNSU={nsu}, cUF={self.cuf})")
        logger.info(f"   📏 Tamanho XML: {len(xml_envio)} bytes")

        try:
            resp = self.dist_client.service.cteDistDFeInteresse(cteDadosMsg=distInt)
            xml_str = etree.tostring(resp, encoding='utf-8').decode()
            logger.info(f"📥 [{self.informante}] Resposta CT-e Por NSU: {len(xml_str)} bytes")
            save_debug_soap_cte(self.informante, "response", xml_str, prefixo="cte_dist_nsu")
            return xml_str
        except Fault as fault:
            logger.error(f"SOAP Fault CTe Por NSU: {fault}")
            save_debug_soap_cte(self.informante, "fault", str(fault), prefixo="cte_dist_nsu")
            return None
        except Exception as e:
            logger.error(f"❌ [{self.informante}] Erro ao buscar CT-e por NSU: {e}")
            return None

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
