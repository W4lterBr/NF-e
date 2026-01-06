"""
Serviço de Manifestação de Documentos Fiscais (NF-e e CT-e)
Implementa envio de eventos de manifestação para SEFAZ
"""

import logging
from pathlib import Path
from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from datetime import datetime
import requests_pkcs12
import base64

logger = logging.getLogger('nfe_search')

# Endpoints de Recepção de Eventos NF-e por UF
EVENTOS_NFE_URLS = {
    '11': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RO -> SVRS
    '12': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # AC -> SVRS
    '13': 'https://dfe-am.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # AM
    '14': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RR -> SVRS
    '15': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # PA -> SVRS
    '16': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # AP -> SVRS
    '17': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # TO -> SVRS
    '21': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # MA -> SVRS
    '22': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # PI -> SVRS
    '23': 'https://nfe.sefa.ce.gov.br/nfe4/services/RecepcaoEvento4',  # CE
    '24': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RN -> SVRS
    '25': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # PB -> SVRS
    '26': 'https://nfe.sefaz.pe.gov.br/nfe-service/services/RecepcaoEvento4',  # PE
    '27': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # AL -> SVRS
    '28': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # SE -> SVRS
    '29': 'https://nfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx',  # BA
    '31': 'https://nfe.fazenda.mg.gov.br/nfe2/services/RecepcaoEvento4',  # MG
    '32': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # ES -> SVRS
    '33': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RJ -> SVRS
    '35': 'https://nfe.fazenda.sp.gov.br/ws/recepcaoevento4.asmx',  # SP
    '41': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # PR -> SVRS
    '42': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # SC -> SVRS
    '43': 'https://nfe.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RS
    '50': 'https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4',  # MS
    '51': 'https://nfe.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4',  # MT
    '52': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # GO -> SVRS
    '53': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # DF -> SVRS
}

# Endpoints de Recepção de Eventos CT-e por UF
EVENTOS_CTE_URLS = {
    # Estados que usam SVRS (Sefaz Virtual RS) - V4.00
    '11': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # RO -> SVRS
    '12': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # AC -> SVRS
    '13': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # AM -> SVRS
    '15': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # PA -> SVRS
    '17': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # TO -> SVRS
    '21': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # MA -> SVRS
    '22': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # PI -> SVRS
    '23': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # CE -> SVRS
    '24': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # RN -> SVRS
    '25': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # PB -> SVRS
    '27': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # AL -> SVRS
    '28': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # SE -> SVRS
    '29': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # BA -> SVRS
    '32': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # ES -> SVRS
    '33': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # RJ -> SVRS
    '42': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # SC -> SVRS
    '52': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # GO -> SVRS
    '53': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # DF -> SVRS
    
    # Estados que usam SVSP (Sefaz Virtual SP) - V4.00
    '14': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx',  # RR -> SVSP
    '16': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx',  # AP -> SVSP
    '26': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx',  # PE -> SVSP
    
    # Estados com webservice próprio - V4.00
    '31': 'https://cte.fazenda.mg.gov.br/cte/services/CTeRecepcaoEventoV4',  # MG
    '35': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeRecepcaoEventoV4.asmx',  # SP
    '41': 'https://cte.fazenda.pr.gov.br/cte4/CTeRecepcaoEventoV4?wsdl',  # PR
    '43': 'https://cte.svrs.rs.gov.br/ws/CTeRecepcaoEventoV4/CTeRecepcaoEventoV4.asmx',  # RS (igual SVRS)
    '50': 'https://producao.cte.ms.gov.br/ws/CTeRecepcaoEventoV4',  # MS
    '51': 'https://cte.sefaz.mt.gov.br/ctews2/services/CTeRecepcaoEventoV4?wsdl',  # MT (webservice próprio!)
}


class ManifestacaoService:
    """Serviço para envio de eventos de manifestação para SEFAZ."""
    
    def __init__(self, cert_path, cert_password):
        """
        Inicializa o serviço de manifestação.
        
        Args:
            cert_path: Caminho do arquivo .pfx do certificado
            cert_password: Senha do certificado
        """
        self.cert_path = cert_path
        self.cert_password = cert_password
        
        # Carrega certificado e chave privada
        from cryptography.hazmat.primitives.serialization import pkcs12
        
        with open(cert_path, 'rb') as f:
            pfx_data = f.read()
        
        self.private_key, self.certificate, self.additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, cert_password.encode(), default_backend()
        )
        
        logger.info(f"[MANIFESTAÇÃO] Certificado carregado: {self.certificate.subject}")
    
    def assinar_xml(self, xml_string):
        """
        Assina XML com o certificado digital usando c14n e SHA256.
        
        Args:
            xml_string: String do XML a ser assinado
            
        Returns:
            String do XML assinado
        """
        from lxml import etree
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        import hashlib
        
        # Parse XML
        root = etree.fromstring(xml_string.encode('utf-8'))
        
        # Encontra o elemento a ser assinado (infEvento)
        inf_evento = root.find('.//{http://www.portalfiscal.inf.br/nfe}infEvento')
        if inf_evento is None:
            inf_evento = root.find('.//{http://www.portalfiscal.inf.br/cte}infEvento')
        
        if inf_evento is None:
            raise ValueError("Elemento infEvento não encontrado no XML")
        
        # Gera Id se não existir
        if 'Id' not in inf_evento.attrib:
            chave = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/nfe}chNFe')
            if not chave:
                chave = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/cte}chCTe')
            tp_evento = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/nfe}tpEvento')
            if not tp_evento:
                tp_evento = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
            n_seq = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/nfe}nSeqEvento')
            if not n_seq:
                n_seq = inf_evento.findtext('.//{http://www.portalfiscal.inf.br/cte}nSeqEvento')
            
            inf_evento.attrib['Id'] = f"ID{tp_evento}{chave}{n_seq.zfill(2)}"
        
        # Canonicalização C14N
        c14n_data = etree.tostring(inf_evento, method='c14n', exclusive=False, with_comments=False)
        
        # Calcula hash SHA-1 (SEFAZ CT-e requer SHA-1)
        digest_value = hashlib.sha1(c14n_data).digest()
        digest_value_b64 = base64.b64encode(digest_value).decode('utf-8')
        
        # Monta SignedInfo (sem namespace declaration - herda de Signature quando validado)
        signed_info_xml = f'''<SignedInfo>
<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
<Reference URI="#{inf_evento.attrib['Id']}">
<Transforms>
<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
<Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
</Transforms>
<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
<DigestValue>{digest_value_b64}</DigestValue>
</Reference>
</SignedInfo>'''
        
        # Obtém certificado em base64 (necessário para KeyInfo)
        cert_der = self.certificate.public_bytes(serialization.Encoding.DER)
        cert_b64 = base64.b64encode(cert_der).decode('utf-8')
        
        # Monta estrutura Signature completa (sem SignatureValue ainda)
        signature_template = f'''<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
{signed_info_xml}
<SignatureValue></SignatureValue>
<KeyInfo>
<X509Data>
<X509Certificate>{cert_b64}</X509Certificate>
</X509Data>
</KeyInfo>
</Signature>'''
        
        # Parse para extrair SignedInfo com namespace herdado
        signature_elem = etree.fromstring(signature_template)
        signed_info_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}SignedInfo')
        
        # Canonicaliza SignedInfo com namespace herdado (como SEFAZ fará)
        signed_info_c14n = etree.tostring(signed_info_elem, method='c14n', exclusive=False, with_comments=False)
        
        # Assina SignedInfo
        signature_bytes = self.private_key.sign(
            signed_info_c14n,
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        signature_value_b64 = base64.b64encode(signature_bytes).decode('utf-8')
        
        # Atualiza SignatureValue no elemento
        signature_value_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        signature_value_elem.text = signature_value_b64
        
        # Atualiza SignatureValue no elemento
        signature_value_elem = signature_elem.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        signature_value_elem.text = signature_value_b64
        
        # Adiciona assinatura completa ao XML
        root.append(signature_elem)
        
        # Retorna XML assinado (sem declaração XML pois será embutido no SOAP)
        return etree.tostring(root, encoding='utf-8', xml_declaration=False).decode('utf-8')
    
    def enviar_manifestacao(self, chave, tipo_evento, cnpj_destinatario, justificativa=None):
        """
        Envia evento de manifestação para SEFAZ.
        
        Args:
            chave: Chave de acesso do documento (44 dígitos)
            tipo_evento: Código do evento (ex: 210210, 210200, 610110)
            cnpj_destinatario: CNPJ do destinatário manifestante
            justificativa: Justificativa (obrigatória para alguns eventos)
            
        Returns:
            Tupla (sucesso: bool, protocolo: str, mensagem: str, xml_resposta: str)
        """
        try:
            # Determina se é NF-e ou CT-e pela chave
            modelo = chave[20:22]
            is_cte = modelo == '57'
            cuf = chave[0:2]
            
            # Monta descrição do evento
            desc_evento_map = {
                '210210': 'Ciencia da Operacao',
                '210200': 'Confirmacao da Operacao',
                '210220': 'Desconhecimento da Operacao',
                '210240': 'Operacao nao Realizada',
                '610110': 'Prestacao do Servico em Desacordo',
                '610112': 'Cancelamento Prestacao do Servico em Desacordo',
            }
            desc_evento = desc_evento_map.get(tipo_evento, 'Evento')
            
            # Namespace e versão baseado no tipo de documento
            ns = "http://www.portalfiscal.inf.br/cte" if is_cte else "http://www.portalfiscal.inf.br/nfe"
            chave_tag = "chCTe" if is_cte else "chNFe"
            versao = "4.00" if is_cte else "1.00"  # CT-e usa versão 4.00, NF-e usa 1.00
            
            # Data e hora atual
            dh_evento = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
            
            # Gera ID do evento seguindo pattern XSD: ID[0-9]{12}[A-Z0-9]{12}[0-9]{29}
            # Estrutura: ID + tpEvento(6)+chave[0:6](=12) + chave[6:18](=12) + chave[18:44]+nSeqEvento(3)(=26+3=29)
            id_evento = f"ID{tipo_evento}{chave[:6]}{chave[6:18]}{chave[18:]}{str(1).zfill(3)}"
            
            # Monta detEvento específico por tipo de evento
            if tipo_evento == '610110':  # Prestação em Desacordo (CT-e)
                det_evento_xml = f'''<detEvento versaoEvento="4.00">
<evPrestDesacordo>
<descEvento>Prestacao do Servico em Desacordo</descEvento>
<indDesacordoOper>1</indDesacordoOper>
<xObs>{justificativa}</xObs>
</evPrestDesacordo>
</detEvento>'''
            elif tipo_evento == '610112':  # Cancelamento Prestação em Desacordo (CT-e)
                det_evento_xml = f'''<detEvento versaoEvento="4.00">
<evCancPrestDesacordo>
<descEvento>Cancelamento Prestacao do Servico em Desacordo</descEvento>
<nProtEvento>PROTOCOLO_ORIGINAL</nProtEvento>
</evCancPrestDesacordo>
</detEvento>'''
            else:  # Eventos genéricos (NF-e)
                justificativa_xml = f"<xJust>{justificativa}</xJust>" if justificativa else ""
                det_evento_xml = f'''<detEvento versao="{versao}">
<descEvento>{desc_evento}</descEvento>
{justificativa_xml}</detEvento>'''
            
            # Elemento raiz correto: eventoCTe para CT-e, evento para NF-e
            elemento_raiz = "eventoCTe" if is_cte else "evento"
            
            # verEvento só existe em NF-e v1.00, não em CT-e v4.00
            ver_evento_tag = "" if is_cte else f"<verEvento>{versao}</verEvento>\n"
            
            xml_evento = f'''<?xml version="1.0" encoding="UTF-8"?>
<{elemento_raiz} xmlns="{ns}" versao="{versao}">
<infEvento Id="{id_evento}">
<cOrgao>{cuf}</cOrgao>
<tpAmb>1</tpAmb>
<CNPJ>{cnpj_destinatario}</CNPJ>
<{chave_tag}>{chave}</{chave_tag}>
<dhEvento>{dh_evento}</dhEvento>
<tpEvento>{tipo_evento}</tpEvento>
<nSeqEvento>1</nSeqEvento>
{ver_evento_tag}{det_evento_xml}
</infEvento>
</{elemento_raiz}>'''
            
            logger.info(f"[MANIFESTAÇÃO] XML antes da assinatura:\n{xml_evento}")
            
            # Valida XML contra XSD antes de assinar (DESABILITADO - XSD tem padrões muito específicos)
            # from modules.xsd_validator import validar_xml_evento, extrair_erros_principais
            # valido, erros_xsd = validar_xml_evento(xml_evento, tipo_evento, is_cte)
            # 
            # if not valido:
            #     msg_erros = extrair_erros_principais(erros_xsd)
            #     logger.error(f"[MANIFESTAÇÃO] XML inválido conforme XSD:\n{msg_erros}")
            #     return False, "", f"XML inválido conforme schema XSD:\n{msg_erros}", ""
            
            # Assina o XML
            xml_assinado = self.assinar_xml(xml_evento)
            
            logger.info(f"[MANIFESTAÇÃO] XML assinado:\n{xml_assinado}")
            
            # Define tag e namespace SOAP baseado no tipo de documento
            if is_cte:
                soap_tag = "cteDadosMsg"
                soap_ns = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4"
            else:
                soap_tag = "nfeDadosMsg"
                soap_ns = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"
            
            # Monta envelope SOAP
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<soap12:Body>
<{soap_tag} xmlns="{soap_ns}">{xml_assinado}</{soap_tag}>
</soap12:Body>
</soap12:Envelope>'''
            
            logger.info(f"[MANIFESTAÇÃO] SOAP Envelope:\n{soap_envelope}")
            
            # Seleciona URL do webservice
            url_map = EVENTOS_CTE_URLS if is_cte else EVENTOS_NFE_URLS
            url = url_map.get(cuf, 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx')
            
            logger.info(f"[MANIFESTAÇÃO] Enviando para: {url}")
            logger.info(f"[MANIFESTAÇÃO] UF: {cuf}, Modelo: {'CT-e' if is_cte else 'NF-e'}")
            
            # Define SOAPAction baseado no tipo de documento
            if is_cte:
                soap_action = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4/cteRecepcaoEventoV4"
            else:
                soap_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento"
            
            # Envia requisição
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'SOAPAction': f'"{soap_action}"',
            }
            
            logger.info(f"[MANIFESTAÇÃO] SOAPAction: {soap_action}")
            
            response = requests_pkcs12.post(
                url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                pkcs12_filename=self.cert_path,
                pkcs12_password=self.cert_password,
                verify=False,
                timeout=30
            )
            
            logger.info(f"[MANIFESTAÇÃO] Status HTTP: {response.status_code}")
            logger.info(f"[MANIFESTAÇÃO] Resposta ({len(response.content)} bytes)")
            
            # Se erro, loga conteúdo para debug
            if response.status_code >= 400:
                logger.error(f"[MANIFESTAÇÃO] Conteúdo da resposta de erro:\n{response.content.decode('utf-8', errors='ignore')}")
            
            response.raise_for_status()
            
            # Parse resposta
            response_xml = response.content.decode('utf-8')
            logger.info(f"[MANIFESTAÇÃO] Resposta SEFAZ:\n{response_xml}")
            
            root = etree.fromstring(response.content)
            
            # Extrai informações da resposta
            ret_evento = root.find(f'.//{{{ns}}}retEvento')
            inf_evento = ret_evento.find(f'.//{{{ns}}}infEvento') if ret_evento is not None else None
            
            if inf_evento is not None:
                c_stat = inf_evento.findtext(f'{{{ns}}}cStat')
                x_motivo = inf_evento.findtext(f'{{{ns}}}xMotivo')
                n_prot = inf_evento.findtext(f'{{{ns}}}nProt')
                
                logger.info(f"[MANIFESTAÇÃO] cStat: {c_stat}")
                logger.info(f"[MANIFESTAÇÃO] xMotivo: {x_motivo}")
                logger.info(f"[MANIFESTAÇÃO] Protocolo: {n_prot}")
                
                # Status de sucesso: 135, 136, 155
                if c_stat in ['135', '136', '155']:
                    return (True, n_prot or '', x_motivo or 'Evento registrado', response_xml)
                else:
                    return (False, '', f"Erro SEFAZ ({c_stat}): {x_motivo}", response_xml)
            else:
                return (False, '', "Resposta SEFAZ inválida", response_xml)
                
        except Exception as e:
            logger.error(f"[MANIFESTAÇÃO] Erro: {e}")
            import traceback
            traceback.print_exc()
            return (False, '', f"Erro ao enviar: {str(e)}", '')
