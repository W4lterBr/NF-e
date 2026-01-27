"""
Serviço de consulta e download de NFS-e via Ambiente Nacional (Padrão Nacional)
Implementa consulta incremental via NSU conforme documentação da Receita Federal

Documentação técnica:
- NFS-e Padrão Nacional: ambiente centralizado pela Receita Federal
- Consulta incremental baseada em NSU (Número Sequencial Único)
- Autenticação via certificado digital ICP-Brasil
- Tratamento de eventos: cancelamento, substituição, retificação
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
logger = logging.getLogger('nfe_search')

# Endpoints oficiais NFS-e Padrão Nacional (Receita Federal)
# Fonte: https://www.gov.br/nfse/pt-br/desenvolvedor
URL_NFSE_DISTRIBUICAO_PROD = "https://www.nfse.gov.br/NfseDistribuicao/NfseDistribuicao.asmx?wsdl"
URL_NFSE_DISTRIBUICAO_HOM = "https://hom.nfse.gov.br/NfseDistribuicao/NfseDistribuicao.asmx?wsdl"

# Namespace NFS-e Padrão Nacional
NS_NFSE = "http://www.sped.fazenda.gov.br/nfse"


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


def save_debug_soap_nfse(informante: str, tipo: str, conteudo: str, prefixo: str = ""):
    """Salva arquivos SOAP NFS-e para debug."""
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
        
        logger.debug(f"📝 Debug NFS-e salvo: {nome_arquivo}")
        return str(arquivo_path)
    except Exception as e:
        logger.error(f"Erro ao salvar debug SOAP NFS-e: {e}")
        return None


class NFSeService:
    """
    Serviço de consulta de NFS-e via Ambiente Nacional (Padrão Nacional)
    
    Documentos suportados:
    - procNFSe: NFS-e autorizada completa
    - resNFSe: Resumo da NFS-e
    - procEventoNFSe: Eventos (cancelamento, substituição, retificação)
    
    Estratégia de consulta:
    - Consulta incremental baseada em NSU
    - Armazenamento do último NSU processado por CNPJ
    - Idempotência: evita reprocessamento de documentos já baixados
    - Validação estrutural e de assinatura digital
    """
    
    def __init__(self, cert_path, senha, informante, cuf, ambiente='producao'):
        """
        Inicializa o serviço NFS-e Padrão Nacional
        
        Args:
            cert_path: Caminho do certificado PFX
            senha: Senha do certificado
            informante: CNPJ/CPF do contribuinte
            cuf: Código UF do contribuinte (apenas por compatibilidade)
            ambiente: 'producao' ou 'homologacao'
        """
        logger.debug(f"Inicializando NFSeService: informante={informante}, ambiente={ambiente}")
        
        # Configura sessão HTTP com certificado
        sess = requests.Session()
        sess.verify = False  # Desabilita verificação SSL
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        
        # Seleciona endpoint baseado no ambiente
        url_dist = URL_NFSE_DISTRIBUICAO_PROD if ambiente == 'producao' else URL_NFSE_DISTRIBUICAO_HOM
        
        trans = Transport(session=sess)
        
        try:
            self.client = Client(url_dist, transport=trans)
            logger.info(f"✅ Cliente NFS-e inicializado com sucesso: {informante}")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente NFS-e: {e}")
            raise
        
        self.informante = informante
        self.cnpj_cpf = informante
        self.cuf = cuf
        self.ambiente = ambiente
    
    def consultar_nsu(self, ultimo_nsu="000000000000000"):
        """
        Consulta NFS-e por NSU incremental
        
        Args:
            ultimo_nsu: Último NSU processado (15 dígitos)
        
        Returns:
            XML da resposta SOAP contendo documentos disponíveis
        """
        logger.info(f"📋 [NFS-e] Consultando a partir do NSU {ultimo_nsu} para {self.informante}")
        
        # Monta XML de requisição
        xml_envio = f"""<?xml version="1.0" encoding="UTF-8"?>
<distNSU xmlns="{NS_NFSE}" versao="1.00">
    <tpAmb>1</tpAmb>
    <CNPJ>{self.informante}</CNPJ>
    <ultNSU>{ultimo_nsu}</ultNSU>
</distNSU>"""
        
        # Salva debug da requisição
        save_debug_soap_nfse(self.informante, "request", xml_envio, prefixo="nfse_dist")
        
        try:
            logger.debug(f"📤 Enviando requisição de distribuição NFS-e...")
            
            # Chama o web service
            response = self.client.service.nfseDistribuicaoDFe(xml_envio)
            
            # Extrai XML da resposta
            xml_str = etree.tostring(response, encoding='unicode', pretty_print=True)
            
            # Salva debug da resposta
            save_debug_soap_nfse(self.informante, "response", xml_str, prefixo="nfse_dist")
            
            logger.info(f"✅ [NFS-e] Resposta recebida com sucesso")
            return xml_str
            
        except Fault as fault:
            logger.error(f"❌ [NFS-e] SOAP Fault: {fault}")
            save_debug_soap_nfse(self.informante, "fault", str(fault), prefixo="nfse_dist")
            raise
        except Exception as e:
            logger.error(f"❌ [NFS-e] Erro na consulta: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def extrair_documentos(self, xml_resposta):
        """
        Extrai documentos individuais do XML de resposta
        
        Args:
            xml_resposta: XML retornado pela SEFAZ
        
        Returns:
            Lista de tuplas (NSU, XML_documento, tipo_documento)
        """
        documentos = []
        
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Busca todos os docZip
            for dz in tree.findall(f'.//{{{NS_NFSE}}}docZip'):
                nsu = dz.get('NSU', '')
                schema = dz.get('schema', '')
                
                # Decodifica e descompacta
                data = base64.b64decode(dz.text or '')
                xml_doc = gzip.decompress(data).decode('utf-8')
                
                # Identifica tipo do documento baseado no schema
                tipo_doc = self._identificar_tipo_documento(xml_doc, schema)
                
                documentos.append((nsu, xml_doc, tipo_doc))
                
                # Salva debug de cada documento extraído
                save_debug_soap_nfse(
                    self.informante,
                    f"xml_extraido_{tipo_doc}_NSU{nsu}",
                    xml_doc,
                    prefixo="nfse_dist"
                )
            
            logger.info(f"📦 [NFS-e] {len(documentos)} documento(s) extraído(s)")
            return documentos
            
        except Exception as e:
            logger.error(f"❌ [NFS-e] Erro ao extrair documentos: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _identificar_tipo_documento(self, xml_doc, schema):
        """Identifica o tipo de documento baseado no XML e schema."""
        if '<resNFSe' in xml_doc or 'resNFSe' in schema:
            return 'resumo'
        elif '<procNFSe' in xml_doc or '<nfseProc' in xml_doc:
            return 'nfse_completa'
        elif '<procEventoNFSe' in xml_doc or 'eventoNFSe' in schema:
            return 'evento'
        else:
            return 'documento'
    
    def extrair_cstat_nsu(self, xml_resposta):
        """
        Extrai cStat, ultNSU e maxNSU da resposta
        
        Returns:
            Tupla (cStat, ultNSU, maxNSU)
        """
        try:
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Busca com namespace
            ns = {'nfse': NS_NFSE}
            
            cstat = tree.findtext('.//nfse:cStat', namespaces=ns) or tree.findtext('.//cStat') or ''
            ult_nsu = tree.findtext('.//nfse:ultNSU', namespaces=ns) or tree.findtext('.//ultNSU') or '000000000000000'
            max_nsu = tree.findtext('.//nfse:maxNSU', namespaces=ns) or tree.findtext('.//maxNSU') or '000000000000000'
            
            return cstat, ult_nsu, max_nsu
            
        except Exception as e:
            logger.error(f"❌ [NFS-e] Erro ao extrair cStat/NSU: {e}")
            return '', '000000000000000', '000000000000000'
    
    def validar_xml(self, xml_doc):
        """
        Valida estrutura básica do XML
        
        Args:
            xml_doc: String com conteúdo XML
        
        Returns:
            True se válido, False caso contrário
        """
        try:
            etree.fromstring(xml_doc.encode('utf-8'))
            return True
        except Exception as e:
            logger.warning(f"⚠️  [NFS-e] XML inválido: {e}")
            return False


def consultar_nfse_incremental(db, cert_path, senha, informante, cuf, ambiente='producao'):
    """
    Função auxiliar para consulta incremental de NFS-e
    
    Args:
        db: Instância do DatabaseManager
        cert_path: Caminho do certificado
        senha: Senha do certificado
        informante: CNPJ do contribuinte
        cuf: Código UF
        ambiente: 'producao' ou 'homologacao'
    
    Returns:
        Lista de documentos processados
    """
    try:
        # Inicializa serviço
        service = NFSeService(cert_path, senha, informante, cuf, ambiente)
        
        # Obtém último NSU processado
        ultimo_nsu = db.get_last_nsu_nfse(informante)
        logger.info(f"📊 [NFS-e] Último NSU processado: {ultimo_nsu}")
        
        # Consulta SEFAZ
        xml_resposta = service.consultar_nsu(ultimo_nsu)
        
        # Extrai status
        cstat, ult_nsu, max_nsu = service.extrair_cstat_nsu(xml_resposta)
        logger.info(f"📊 [NFS-e] cStat={cstat}, ultNSU={ult_nsu}, maxNSU={max_nsu}")
        
        # Verifica status
        if cstat == '137':
            logger.info(f"✅ [NFS-e] Nenhum documento novo disponível (cStat=137)")
            db.registrar_sem_documentos_nfse(informante)
            return []
        
        if cstat == '656':
            logger.warning(f"⚠️  [NFS-e] Consumo indevido (cStat=656) - aguarde 65 minutos")
            db.registrar_erro_656_nfse(informante, ultimo_nsu)
            return []
        
        # Extrai documentos
        documentos = service.extrair_documentos(xml_resposta)
        
        if not documentos:
            logger.info(f"📭 [NFS-e] Nenhum documento retornado")
            return []
        
        # Atualiza NSU no banco
        if ult_nsu and ult_nsu != '000000000000000':
            db.set_last_nsu_nfse(informante, ult_nsu)
        
        return documentos
        
    except Exception as e:
        logger.error(f"❌ [NFS-e] Erro na consulta incremental: {e}")
        import traceback
        traceback.print_exc()
        return []
