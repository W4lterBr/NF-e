# -*- coding: utf-8 -*-
"""
Modulo para integracao com Sistema Nacional de NFS-e via API REST.
Implementa padroes tecnicos do Ambiente Nacional (Padrao Nacional).

URLs OFICIAIS:
- Producao: https://adn.nfse.gov.br
- Homologacao: https://adn.producaorestrita.nfse.gov.br

ENDPOINTS PRINCIPAIS:
- GET /contribuintes/DFe/{NSU} - Consulta incremental por NSU
- GET /danfse/{chave} - Download de DANFSe (PDF)
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from lxml import etree
import requests
from requests.exceptions import RequestException
import logging

# Configuracao de logging
logger = logging.getLogger('nfe_search')


class NFSeService:
    """
    Servico de consulta ao Sistema Nacional de NFS-e via API REST.
    
    Endpoints:
    - GET /contribuintes/DFe/{NSU} (consulta incremental)
    - GET /danfse/{chave} (download PDF)
    """
    
    def __init__(self, cert_path, senha, informante, cuf, ambiente='producao'):
        """
        Inicializa o servico NFS-e REST.
        
        Args:
            cert_path: Caminho do certificado .pfx (ICP-Brasil)
            senha: Senha do certificado
            informante: CNPJ do informante
            cuf: Codigo da UF
            ambiente: 'producao' ou 'homologacao'
        """
        self.cert_path = cert_path
        self.senha = senha
        self.informante = informante
        self.cuf = cuf
        self.ambiente = ambiente
        
        # URLs oficiais do Ambiente Nacional
        if ambiente == 'producao':
            self.url_base = "https://adn.nfse.gov.br"
        else:
            self.url_base = "https://adn.producaorestrita.nfse.gov.br"
        
        # Inicializa sessao com certificado mTLS
        try:
            import requests_pkcs12
            
            # Carrega certificado para autenticacao mTLS
            with open(cert_path, 'rb') as f:
                pkcs12_data = f.read()
            
            # Cria sessao com adaptador PKCS12
            self.session = requests.Session()
            self.session.mount('https://', requests_pkcs12.Pkcs12Adapter(
                pkcs12_data=pkcs12_data,
                pkcs12_password=senha
            ))
            
            # Headers padrao para API REST
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
            
            logger.info(f"✅ Cliente NFS-e REST inicializado: {self.url_base}")
            logger.info(f"   CNPJ: {informante}")
            logger.info(f"   Autenticacao: mTLS (certificado digital)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente NFS-e: {e}")
            raise
    
    def consultar_nsu(self, nsu, tipo_nsu=None):
        """
        Consulta documento por NSU.
        
        Endpoint: GET /contribuintes/DFe/{NSU}
        
        Args:
            nsu: Numero Sequencial Unico
            tipo_nsu: Tipo de NSU (opcional)
                - "RECEPCAO": NSU de recepção (emissão)
                - "DISTRIBUICAO": NSU de distribuição
                - "GERAL": Todos os NSUs (recomendado!)
                - "MEI": Específico para MEI
                - None: Usa padrão (DISTRIBUICAO)
        
        Returns:
            dict ou bytes: Resposta da API
        """
        endpoint = f"{self.url_base}/contribuintes/DFe/{nsu}"
        
        # Adiciona parâmetros query
        params = {}
        if tipo_nsu:
            params['tipoNSU'] = tipo_nsu
        
        try:
            logger.debug(f"📡 Consultando NSU: {nsu}" + (f" (tipoNSU={tipo_nsu})" if tipo_nsu else ""))
            
            response = self.session.get(endpoint, params=params, timeout=12)
            response.raise_for_status()
            
            # Verifica se conteudo esta vazio
            if not response.content or len(response.content) == 0:
                logger.debug(f"📭 NSU {nsu}: resposta vazia (sem documentos)")
                return None
            
            # Tenta parsear como JSON
            try:
                resultado = response.json()
                logger.info(f"✅ NSU {nsu}: JSON recebido")
                return resultado
            except:
                # Se nao for JSON, retorna conteudo bruto
                logger.info(f"✅ NSU {nsu}: XML recebido ({len(response.content)} bytes)")
                return response.content
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"📭 NSU {nsu} nao encontrado")
                return None
            elif e.response.status_code == 429:
                logger.warning(f"⚠️  Rate limit atingido no NSU {nsu}, aguardando 2s...")
                time.sleep(2)
                return None
            logger.error(f"❌ Erro HTTP ao consultar NSU: {e}")
            logger.error(f"   Status: {e.response.status_code}")
            logger.error(f"   Resposta: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao consultar NSU: {e}")
            raise
    
    def consultar_danfse(self, chave, retry=3):
        """
        Consulta DANFSe (PDF oficial da NFS-e) por chave de acesso.
        
        Este é o PDF OFICIAL gerado pelo Ambiente Nacional de NFS-e,
        equivalente ao DANFE da NF-e. Contém layout padronizado com:
        - Cabeçalho com brasão e dados fiscais
        - QR Code para consulta
        - Informações completas de prestador/tomador
        - Discriminação dos serviços
        - Valores e tributos
        
        Endpoint: GET /danfse/{chave}
        
        Args:
            chave: Chave de acesso da NFS-e (50 dígitos)
            retry: Número de tentativas em caso de erro do servidor
        
        Returns:
            bytes: Conteúdo do PDF oficial (DANFSe)
            
        Raises:
            HTTPError: Se API retornar erro persistente
            Exception: Outros erros de rede/timeout
        """
        endpoint = f"{self.url_base}/danfse/{chave}"
        
        for tentativa in range(1, retry + 1):
            try:
                if tentativa > 1:
                    logger.info(f"   🔄 Tentativa {tentativa}/{retry}...")
                    time.sleep(2)  # Aguarda 2s entre tentativas
                
                response = self.session.get(endpoint, timeout=(5, 10))
                
                # Verifica se retornou PDF
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Valida se é realmente um PDF
                    if 'application/pdf' in content_type or response.content.startswith(b'%PDF'):
                        logger.info(f"✅ DANFSe oficial obtido ({len(response.content):,} bytes)")
                        return response.content
                    else:
                        logger.warning(f"⚠️  Resposta não é PDF (Content-Type: {content_type})")
                        continue
                
                # Erros temporários do servidor - tenta novamente
                if response.status_code in [502, 503, 504]:
                    logger.warning(f"⚠️  Servidor temporariamente indisponível ({response.status_code})")
                    if tentativa < retry:
                        continue
                
                # Outros erros HTTP
                response.raise_for_status()
                
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️  Timeout na consulta DANFSe (tentativa {tentativa}/{retry})")
                if tentativa < retry:
                    continue
                raise
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [502, 503, 504] and tentativa < retry:
                    continue
                logger.error(f"❌ Erro HTTP ao consultar DANFSe: {e}")
                logger.error(f"   Status: {e.response.status_code}")
                raise
                
            except Exception as e:
                logger.error(f"❌ Erro ao consultar DANFSe: {e}")
                if tentativa < retry:
                    continue
                raise
        
        # Se chegou aqui, todas as tentativas falharam
        raise Exception(f"Falha ao obter DANFSe após {retry} tentativas")
    
    def validar_xml(self, xml_content):
        """
        Valida estrutura basica do XML da NFS-e.
        
        Args:
            xml_content: Conteudo XML (string)
        
        Returns:
            bool: True se valido, False caso contrario
        """
        try:
            tree = etree.fromstring(xml_content.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"❌ XML invalido: {e}")
            return False
    
    def extrair_cstat_nsu(self, xml_resposta):
        """
        Extrai cStat, ultNSU e maxNSU da resposta.
        
        Args:
            xml_resposta: String, bytes ou dict (JSON) com resposta da API
        
        Returns:
            Tupla (cStat, ultNSU, maxNSU)
        """
        try:
            # Se for dict (JSON), tenta extrair campos
            if isinstance(xml_resposta, dict):
                cstat = xml_resposta.get('cStat', '')
                ult_nsu = xml_resposta.get('ultNSU', '000000000000000')
                max_nsu = xml_resposta.get('maxNSU', '000000000000000')
                logger.debug(f"[NFS-e] Extraido JSON: cStat={cstat}, ultNSU={ult_nsu}, maxNSU={max_nsu}")
                return cstat, ult_nsu, max_nsu
            
            # Converte bytes para string se necessario
            if isinstance(xml_resposta, bytes):
                xml_resposta = xml_resposta.decode('utf-8')
            
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Busca com e sem namespace
            NS_NFSE = 'http://www.portalfiscal.inf.br/nfse'
            ns = {'nfse': NS_NFSE}
            
            cstat = tree.findtext('.//nfse:cStat', namespaces=ns) or tree.findtext('.//cStat') or ''
            ult_nsu = tree.findtext('.//nfse:ultNSU', namespaces=ns) or tree.findtext('.//ultNSU') or '000000000000000'
            max_nsu = tree.findtext('.//nfse:maxNSU', namespaces=ns) or tree.findtext('.//maxNSU') or '000000000000000'
            
            logger.debug(f"[NFS-e] Extraido XML: cStat={cstat}, ultNSU={ult_nsu}, maxNSU={max_nsu}")
            return cstat, ult_nsu, max_nsu
            
        except Exception as e:
            logger.error(f"❌ [NFS-e] Erro ao extrair cStat/NSU: {e}")
            return '', '000000000000000', '000000000000000'
    
    def extrair_documentos(self, resultado):
        """
        Extrai documentos do resultado da consulta NSU.
        
        Args:
            resultado: dict (JSON) ou bytes (XML) retornado por consultar_nsu()
        
        Yields:
            Tupla (nsu, xml_content, tipo_documento)
        """
        import base64
        import gzip
        
        if not resultado:
            return
        
        try:
            # Processa resultado JSON (formato API REST)
            if isinstance(resultado, dict):
                lote_dfe = resultado.get('LoteDFe', [])
                
                if not lote_dfe:
                    logger.debug(f"📭 Resposta sem documentos no lote")
                    return
                
                # Processa cada documento do lote
                for doc in lote_dfe:
                    try:
                        doc_nsu = str(doc.get('NSU', '')).zfill(15)  # Padroniza para 15 dígitos
                        xml_base64 = doc.get('ArquivoXml', '')
                        
                        if not xml_base64:
                            logger.warning(f"⚠️  NSU {doc_nsu}: sem ArquivoXml")
                            continue
                        
                        # Decodifica Base64 e descomprime gzip
                        xml_comprimido = base64.b64decode(xml_base64)
                        xml = gzip.decompress(xml_comprimido).decode('utf-8')
                        
                        # Determina tipo de documento
                        if '<Nfse' in xml or '<NFSe' in xml or '<nfse' in xml or '<CompNfse' in xml:
                            tipo = 'NFS-e'
                        elif '<eventoCancelamento' in xml:
                            tipo = 'Cancelamento'
                        elif '<eventoSubstituicao' in xml:
                            tipo = 'Substituicao'
                        else:
                            tipo = 'Desconhecido'
                        
                        yield (doc_nsu, xml, tipo)
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Erro ao processar documento do lote: {e}")
                        continue
            
            # Processa resultado XML direto (formato legado)
            elif isinstance(resultado, bytes):
                try:
                    xml = resultado.decode('utf-8')
                    
                    # Determina tipo de documento
                    if '<Nfse' in xml or '<NFSe' in xml or '<nfse' in xml or '<CompNfse' in xml:
                        tipo = 'NFS-e'
                    elif '<eventoCancelamento' in xml:
                        tipo = 'Cancelamento'
                    elif '<eventoSubstituicao' in xml:
                        tipo = 'Substituicao'
                    else:
                        tipo = 'Desconhecido'
                    
                    # NSU não vem na resposta XML direta
                    yield ('000000000000000', xml, tipo)
                    
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao processar XML direto: {e}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair documentos: {e}")


def consultar_nfse_incremental(db, cert_path, senha, informante, cuf, ambiente='producao', busca_completa=False):
    """
    Realiza consulta incremental de NFS-e via NSU.
    
    Estrategia:
    1. Recupera ultimo NSU processado do banco (ou NSU=0 se busca_completa=True)
    2. Consulta documentos novos desde o ultimo NSU
    3. Processa cada documento (valida, extrai dados)
    4. Atualiza ultimo NSU no banco
    5. Para quando receber 404 (fim dos documentos)
    
    Args:
        db: Instancia do banco de dados
        cert_path: Caminho do certificado
        senha: Senha do certificado
        informante: CNPJ do informante
        cuf: Codigo da UF
        ambiente: 'producao' ou 'homologacao'
        busca_completa: Se True, inicia do NSU=0 (busca todos documentos)
    
    Returns:
        list: Lista de tuplas (nsu, xml_content, tipo_documento)
    """
    try:
        # Inicializa servico
        servico = NFSeService(cert_path, senha, informante, cuf, ambiente)
        
        # Recupera ultimo NSU processado
        if busca_completa:
            ultimo_nsu = 0
            logger.info(f"🔄 BUSCA COMPLETA: Iniciando do NSU=0 (todos os documentos)")
        else:
            # int() garante que o valor do banco (string "000000000000000") seja numérico
            ultimo_nsu = int(db.get_last_nsu_nfse(informante) or 0)
            logger.info(f"📍 BUSCA INCREMENTAL: Ultimo NSU processado: {ultimo_nsu:015d}")
        
        documentos_encontrados = []
        nsu_atual = max(ultimo_nsu + 1, 1)  # Comeca do proximo (minimo 1)
        max_tentativas_404 = 5  # Para apos 5 NSUs seguidos sem retorno
        tentativas_404 = 0
        max_documentos = 50  # Limite de documentos por execucao
        
        logger.info(f"🔍 Iniciando busca a partir do NSU {nsu_atual}")
        
        while tentativas_404 < max_tentativas_404 and len(documentos_encontrados) < max_documentos:
            # Delay para respeitar rate limit (1 req/segundo)
            if nsu_atual > ultimo_nsu + 1:
                time.sleep(1)
            
            # Consulta NSU atual (GET /contribuintes/DFe/{NSU})
            resultado = servico.consultar_nsu(nsu_atual)
            
            if resultado is None:
                # 404 ou 429 - NSU nao encontrado ou rate limit
                tentativas_404 += 1
                nsu_atual += 1
                continue
            
            # Resetou contador de 404
            tentativas_404 = 0
            
            # Processa resultado
            if isinstance(resultado, dict):
                # JSON estruturado da API
                # Formato: {"StatusProcessamento": "...", "LoteDFe": [{NSU, ChaveAcesso, ArquivoXml, ...}], ...}
                lote_dfe = resultado.get('LoteDFe', [])
                
                if not lote_dfe:
                    logger.debug(f"📭 NSU {nsu_atual}: sem documentos no lote")
                    tentativas_404 += 1
                    nsu_atual += 1
                    continue
                
                # Processa cada documento do lote
                import base64
                import gzip
                
                for doc in lote_dfe:
                    doc_nsu = doc.get('NSU', nsu_atual)
                    xml_base64 = doc.get('ArquivoXml', '')
                    
                    if not xml_base64:
                        logger.warning(f"⚠️  NSU {doc_nsu}: sem ArquivoXml, pulando")
                        continue
                    
                    try:
                        # Decodifica Base64 e descomprime gzip
                        xml_comprimido = base64.b64decode(xml_base64)
                        xml = gzip.decompress(xml_comprimido).decode('utf-8')
                        
                        # Determina tipo de documento
                        if '<Nfse' in xml or '<NFSe' in xml or '<nfse' in xml:
                            tipo = 'NFS-e'
                        elif '<eventoCancelamento' in xml:
                            tipo = 'Cancelamento'
                        else:
                            tipo = 'Outros'
                        
                        # Adiciona documento encontrado
                        documentos_encontrados.append((doc_nsu, xml, tipo))
                        logger.info(f"✅ NSU {doc_nsu}: {tipo} processado")
                        
                    except Exception as e:
                        logger.warning(f"⚠️  NSU {doc_nsu}: erro ao processar: {e}")
                        continue
                
                # Reseta contador de 404 se achou documentos
                if lote_dfe:
                    tentativas_404 = 0
                
            elif isinstance(resultado, bytes):
                # Conteudo binario (legado - possivelmente XML direto)
                try:
                    xml = resultado.decode('utf-8')
                    
                    # Determina tipo de documento
                    if '<Nfse' in xml or '<NFSe' in xml or '<nfse' in xml:
                        tipo = 'NFS-e'
                    elif '<eventoCancelamento' in xml:
                        tipo = 'Cancelamento'
                    elif '<eventoSubstituicao' in xml:
                        tipo = 'Substituicao'
                    else:
                        tipo = 'Desconhecido'
                    
                    documentos_encontrados.append((nsu_atual, xml, tipo))
                    logger.info(f"✅ NSU {nsu_atual}: {tipo} processado")
                    
                except Exception as e:
                    logger.warning(f"⚠️  NSU {nsu_atual}: erro ao processar bytes: {e}")
            
            nsu_atual += 1
        
        # Salva ultimo NSU processado no banco
        if documentos_encontrados:
            # Pega o maior NSU processado
            maior_nsu = max(doc[0] for doc in documentos_encontrados)
            db.set_last_nsu_nfse(informante, maior_nsu)
            logger.info(f"💾 Ultimo NSU atualizado: {maior_nsu}")
        
        return documentos_encontrados
        
    except Exception as e:
        logger.error(f"❌ Erro na consulta incremental: {e}")
        import traceback
        traceback.print_exc()
        return []
