# modules/download_completo.py
"""
Módulo para download de XMLs completos quando recebemos apenas resumos
Detecta resumos (resNFe, resCTe, resNFSe) e busca documentos completos (procNFe, procCTe, procNFSe) 
via consulta NSU específica
"""

import logging
import base64
import gzip
from typing import Optional, Tuple, Dict, Any
from lxml import etree
from pathlib import Path

logger = logging.getLogger(__name__)

class CompleteXMLDownloader:
    """
    Classe responsável por baixar XMLs completos quando recebemos apenas resumos
    Suporta: NFe, CTe e NFS-e do padrão nacional
    """
    
    # Mapeamento de tipos de documento para namespaces
    DOCUMENT_NAMESPACES = {
        'nfe': 'http://www.portalfiscal.inf.br/nfe',
        'cte': 'http://www.portalfiscal.inf.br/cte',
        'nfse': 'http://www.abrasf.org.br/nfse.xsd'  # Padrão nacional NFS-e
    }
    
    # Tipos de documentos suportados
    DOCUMENT_TYPES = {
        # NFe
        'resnfe': {'type': 'nfe', 'resumo': True, 'completo': 'procnfe'},
        'procnfe': {'type': 'nfe', 'resumo': False, 'completo': 'procnfe'},
        'nfe': {'type': 'nfe', 'resumo': False, 'completo': 'procnfe'},
        
        # CTe
        'rescte': {'type': 'cte', 'resumo': True, 'completo': 'proccte'},
        'proccte': {'type': 'cte', 'resumo': False, 'completo': 'proccte'},
        'cte': {'type': 'cte', 'resumo': False, 'completo': 'proccte'},
        
        # NFS-e (Padrão Nacional)
        'resnfse': {'type': 'nfse', 'resumo': True, 'completo': 'procnfse'},
        'procnfse': {'type': 'nfse', 'resumo': False, 'completo': 'procnfse'},
        'nfse': {'type': 'nfse', 'resumo': False, 'completo': 'procnfse'},
    }
    
    def __init__(self, nfe_service, xml_processor, db_manager):
        self.nfe_service = nfe_service
        self.xml_processor = xml_processor
        self.db_manager = db_manager
        
    def is_resumo(self, xml_content: str) -> bool:
        """
        Verifica se o XML é um resumo ao invés de documento completo
        Suporta: resNFe, resCTe, resNFSe
        
        Args:
            xml_content: Conteúdo do XML
            
        Returns:
            True se for resumo, False se for documento completo
        """
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'))
            root_tag = tree.tag
            
            # Remove namespace se presente
            if '}' in root_tag:
                root_tag = root_tag.split('}', 1)[1]
                
            # Normaliza para lowercase
            root_tag_lower = root_tag.lower()
            
            # Verifica se é resumo de qualquer tipo
            if root_tag_lower in ['resnfe', 'rescte', 'resnfse']:
                doc_type = self.DOCUMENT_TYPES.get(root_tag_lower, {}).get('type', 'unknown')
                logger.debug(f"Detectado resumo {doc_type.upper()} ({root_tag})")
                return True
                
            # Verifica se é documento completo
            if root_tag_lower in ['nfeproc', 'procnfe', 'nfe', 'proccte', 'cte', 'procnfse', 'nfse']:
                doc_type = self.DOCUMENT_TYPES.get(root_tag_lower, {}).get('type', 'unknown')
                logger.debug(f"Detectado documento completo {doc_type.upper()} ({root_tag})")
                return False
                
            # Para outros tipos, assume que não é resumo
            logger.debug(f"Tipo de documento não identificado: {root_tag}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar se é resumo: {e}")
            return False
    
    def get_document_type(self, xml_content: str) -> str:
        """
        Identifica o tipo de documento (nfe, cte, nfse)
        
        Args:
            xml_content: Conteúdo do XML
            
        Returns:
            Tipo do documento ('nfe', 'cte', 'nfse', 'unknown')
        """
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'))
            root_tag = tree.tag
            
            # Remove namespace se presente
            if '}' in root_tag:
                root_tag = root_tag.split('}', 1)[1]
                
            # Normaliza para lowercase
            root_tag_lower = root_tag.lower()
            
            # Retorna tipo do documento
            doc_info = self.DOCUMENT_TYPES.get(root_tag_lower, {})
            return doc_info.get('type', 'unknown')
            
        except Exception as e:
            logger.error(f"Erro ao identificar tipo de documento: {e}")
            return 'unknown'
    
    def extract_nsu_from_resumo(self, xml_content: str) -> Optional[str]:
        """
        Extrai o NSU de um resumo NFe
        
        Args:
            xml_content: Conteúdo do XML resumo
            
        Returns:
            NSU do documento ou None se não encontrado
        """
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'))
            
            # Procura NSU em diferentes locais possíveis
            # Método 1: Atributo NSU no próprio elemento
            nsu = tree.get('NSU')
            if nsu:
                return nsu.zfill(15)
                
            # Método 2: Elemento NSU
            nsu_elem = tree.find('.//{http://www.portalfiscal.inf.br/nfe}NSU')
            if nsu_elem is not None and nsu_elem.text:
                return nsu_elem.text.zfill(15)
                
            # Método 3: Procura em qualquer namespace
            for elem in tree.iter():
                if elem.tag.endswith('NSU') and elem.text:
                    return elem.text.zfill(15)
                    
            logger.warning("NSU não encontrado no resumo")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair NSU do resumo: {e}")
            return None
    
    def extract_chave_from_resumo(self, xml_content: str) -> Optional[str]:
        """
        Extrai a chave de acesso de um resumo (NFe, CTe ou NFS-e)
        
        Args:
            xml_content: Conteúdo do XML resumo
            
        Returns:
            Chave de acesso ou None se não encontrada
        """
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'))
            doc_type = self.get_document_type(xml_content)
            
            # Procura chave baseado no tipo de documento
            if doc_type == 'nfe':
                # NFe: chave tem 44 dígitos
                chave_elem = tree.find('.//{http://www.portalfiscal.inf.br/nfe}chNFe')
                if chave_elem is not None and chave_elem.text:
                    return chave_elem.text.strip()
                    
                # Procura em atributo Id
                for elem in tree.iter():
                    id_attr = elem.get('Id', '')
                    if id_attr.startswith('NFe') and len(id_attr) >= 44:
                        return id_attr[-44:]
                        
            elif doc_type == 'cte':
                # CTe: chave tem 44 dígitos
                chave_elem = tree.find('.//{http://www.portalfiscal.inf.br/cte}chCTe')
                if chave_elem is not None and chave_elem.text:
                    return chave_elem.text.strip()
                    
                # Procura em atributo Id
                for elem in tree.iter():
                    id_attr = elem.get('Id', '')
                    if id_attr.startswith('CTe') and len(id_attr) >= 44:
                        return id_attr[-44:]
                        
            elif doc_type == 'nfse':
                # NFS-e: procura número da nota ou chave específica
                numero_elem = tree.find('.//{http://www.abrasf.org.br/nfse.xsd}Numero')
                if numero_elem is not None and numero_elem.text:
                    return numero_elem.text.strip()
                    
                # Procura CodigoVerificacao (chave NFS-e)
                codigo_elem = tree.find('.//{http://www.abrasf.org.br/nfse.xsd}CodigoVerificacao')
                if codigo_elem is not None and codigo_elem.text:
                    return codigo_elem.text.strip()
                    
            # Método genérico: procura qualquer elemento que termine com chave
            for elem in tree.iter():
                if elem.tag.endswith(('chNFe', 'chCTe', 'chave', 'Numero')) and elem.text:
                    chave = elem.text.strip()
                    if len(chave) >= 8:  # Mínimo 8 caracteres para ser uma chave válida
                        return chave
                        
            logger.warning(f"Chave não encontrada no resumo {doc_type.upper()}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair chave do resumo: {e}")
            return None
    
    def download_xml_completo_by_nsu(self, nsu: str, informante: str) -> Optional[str]:
        """
        Baixa XML completo usando consulta NSU específica
        
        Args:
            nsu: NSU do documento
            informante: CNPJ/CPF do informante
            
        Returns:
            XML completo ou None se não conseguir baixar
        """
        try:
            logger.info(f"Tentando baixar XML completo para NSU {nsu}")
            
            # Monta XML de consulta NSU específica
            distInt = etree.Element("distDFeInt", 
                                  xmlns="http://www.portalfiscal.inf.br/nfe", 
                                  versao="1.01")
                                  
            etree.SubElement(distInt, "tpAmb").text = "1"  # Produção
            etree.SubElement(distInt, "cUFAutor").text = str(self.nfe_service.cuf)
            
            # CNPJ ou CPF
            if len(informante) == 14:
                etree.SubElement(distInt, "CNPJ").text = informante
            else:
                etree.SubElement(distInt, "CPF").text = informante
                
            # Consulta NSU específica
            consNSU = etree.SubElement(distInt, "consNSU")
            etree.SubElement(consNSU, "NSU").text = nsu.zfill(15)
            
            # Converte para string
            xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
            
            # Valida XML de envio
            try:
                # Importa a função de validação localmente para evitar import circular
                import sys
                from pathlib import Path
                
                # Adiciona o diretório pai ao path se necessário
                parent_dir = Path(__file__).parent.parent
                if str(parent_dir) not in sys.path:
                    sys.path.insert(0, str(parent_dir))
                
                # Importa e valida
                from nfe_search import validar_xml_auto
                validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
            except Exception as e:
                logger.warning(f"XML de consulta NSU não passou na validação: {e}")
            
            # Faz a consulta
            try:
                resp = self.nfe_service.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
                resp_xml = etree.tostring(resp, encoding='utf-8').decode()
                
                # Extrai documentos da resposta
                docs = self.xml_processor.extract_docs(resp_xml)
                
                if docs:
                    # Retorna o primeiro documento (deveria ser só um para NSU específico)
                    nsu_retornado, xml_completo = docs[0]
                    logger.info(f"XML completo baixado com sucesso para NSU {nsu}")
                    return xml_completo
                else:
                    logger.warning(f"Nenhum documento retornado para NSU {nsu}")
                    return None
                    
            except Exception as e:
                logger.error(f"Erro na consulta SEFAZ para NSU {nsu}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar XML completo por NSU {nsu}: {e}")
            return None
    
    def download_xml_completo_by_chave(self, chave: str) -> Optional[str]:
        """
        Baixa XML completo usando consulta de protocolo por chave
        
        Args:
            chave: Chave de acesso da NFe (44 dígitos)
            
        Returns:
            XML completo ou None se não conseguir baixar
        """
        try:
            logger.info(f"Tentando baixar XML completo para chave {chave}")
            
            # Usa o método existente de consulta de protocolo
            resp_xml = self.nfe_service.fetch_prot_nfe(chave)
            
            if resp_xml:
                # Verifica se a resposta contém o XML completo
                tree = etree.fromstring(resp_xml.encode('utf-8'))
                
                # Procura pelo elemento procNFe que contém o XML completo
                proc_nfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}procNFe')
                if proc_nfe is not None:
                    xml_completo = etree.tostring(proc_nfe, encoding='utf-8').decode()
                    logger.info(f"XML completo extraído da consulta de protocolo para chave {chave}")
                    return xml_completo
                    
                # Se não encontrou procNFe, verifica se tem NFe
                nfe_elem = tree.find('.//{http://www.portalfiscal.inf.br/nfe}NFe')
                if nfe_elem is not None:
                    xml_completo = etree.tostring(nfe_elem, encoding='utf-8').decode()
                    logger.info(f"XML NFe extraído da consulta de protocolo para chave {chave}")
                    return xml_completo
                    
                logger.warning(f"XML completo não encontrado na resposta para chave {chave}")
                return None
            else:
                logger.warning(f"Consulta de protocolo falhou para chave {chave}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar XML completo por chave {chave}: {e}")
            return None
    
    def process_resumo_and_download_complete(self, xml_content: str, nsu: str, informante: str) -> Optional[str]:
        """
        Processa um resumo e tenta baixar o XML completo
        Suporta: NFe, CTe e NFS-e
        
        Args:
            xml_content: Conteúdo do XML resumo
            nsu: NSU do documento resumo
            informante: CNPJ/CPF do informante
            
        Returns:
            XML completo se conseguiu baixar, None caso contrário
        """
        try:
            if not self.is_resumo(xml_content):
                # Já é documento completo, retorna como está
                logger.debug("Documento já é completo, não precisa baixar")
                return xml_content
                
            doc_type = self.get_document_type(xml_content)
            logger.info(f"Processando resumo {doc_type.upper()} NSU {nsu} - tentando baixar XML completo")
            
            # Método 1: Tenta por NSU específica (funciona para todos os tipos)
            xml_completo = self.download_xml_completo_by_nsu(nsu, informante)
            if xml_completo:
                logger.info(f"XML completo {doc_type.upper()} baixado via NSU para {nsu}")
                return xml_completo
                
            # Método 2: Tenta por chave de acesso (específico por tipo)
            chave = self.extract_chave_from_resumo(xml_content)
            if chave:
                if doc_type == 'nfe':
                    xml_completo = self.download_xml_completo_by_chave(chave)
                elif doc_type == 'cte':
                    xml_completo = self.download_cte_completo_by_chave(chave)
                elif doc_type == 'nfse':
                    xml_completo = self.download_nfse_completo_by_chave(chave)
                else:
                    xml_completo = None
                    
                if xml_completo:
                    logger.info(f"XML completo {doc_type.upper()} baixado via chave para {chave}")
                    return xml_completo
                    
            logger.warning(f"Não foi possível baixar XML completo {doc_type.upper()} para NSU {nsu}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar resumo e baixar completo para NSU {nsu}: {e}")
            return None
    
    def download_cte_completo_by_chave(self, chave: str) -> Optional[str]:
        """
        Baixa XML completo de CTe usando consulta de protocolo por chave
        
        Args:
            chave: Chave de acesso do CTe (44 dígitos)
            
        Returns:
            XML completo ou None se não conseguir baixar
        """
        try:
            logger.info(f"Tentando baixar CTe completo para chave {chave}")
            
            # Monta XML de consulta específica para CTe
            cons_sit = etree.Element("consSitCTe", 
                                   xmlns="http://www.portalfiscal.inf.br/cte", 
                                   versao="3.00")
            
            etree.SubElement(cons_sit, "tpAmb").text = "1"
            etree.SubElement(cons_sit, "xServ").text = "CONSULTAR"
            etree.SubElement(cons_sit, "chCTe").text = chave
            
            # TODO: Implementar cliente SOAP específico para CTe
            # Por enquanto, usa o método genérico via NSU
            logger.warning("Consulta direta de CTe não implementada, usando método NSU")
            return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar CTe completo por chave {chave}: {e}")
            return None
    
    def download_nfse_completo_by_chave(self, chave: str) -> Optional[str]:
        """
        Baixa XML completo de NFS-e usando consulta específica
        
        Args:
            chave: Chave/número da NFS-e
            
        Returns:
            XML completo ou None se não conseguir baixar
        """
        try:
            logger.info(f"Tentando baixar NFS-e completa para chave {chave}")
            
            # TODO: Implementar consulta específica para NFS-e
            # NFS-e tem endpoints específicos por município
            logger.warning("Consulta direta de NFS-e não implementada, usando método NSU")
            return None
                
        except Exception as e:
            logger.error(f"Erro ao baixar NFS-e completa por chave {chave}: {e}")
            return None
    
    def should_download_complete(self, xml_content: str) -> bool:
        """
        Verifica se deve tentar baixar versão completa
        
        Args:
            xml_content: Conteúdo do XML
            
        Returns:
            True se deve tentar baixar completo
        """
        # Só tenta baixar se for resumo
        if not self.is_resumo(xml_content):
            return False
            
        # Verifica se já temos o XML completo salvo
        try:
            chave = self.extract_chave_from_resumo(xml_content)
            if chave:
                # Verifica no banco se já temos dados completos desta nota
                status = self.db_manager.get_nf_status(chave)
                if status and status[0] == '100':  # Status autorizada
                    logger.debug(f"Já temos dados completos para chave {chave}")
                    return False
                    
        except Exception:
            pass
            
        return True


def create_complete_downloader(nfe_service, xml_processor, db_manager):
    """
    Factory function para criar um downloader de XMLs completos
    
    Args:
        nfe_service: Serviço NFe configurado
        xml_processor: Processador de XML
        db_manager: Gerenciador do banco de dados
        
    Returns:
        CompleteXMLDownloader configurado
    """
    return CompleteXMLDownloader(nfe_service, xml_processor, db_manager)