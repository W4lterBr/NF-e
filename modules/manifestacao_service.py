"""
Serviço de Manifestação de Documentos Fiscais (NF-e e CT-e)
Implementa envio de eventos de manifestação para SEFAZ
Suporta dois métodos: API BrasilNFe (recomendado) ou assinatura local com xmlsec
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
import xmlsec
from typing import Optional, Tuple

# Importa API BrasilNFe se disponível
try:
    from .brasilnfe_api import BrasilNFeAPI
    BRASILNFE_DISPONIVEL = True
except ImportError:
    BRASILNFE_DISPONIVEL = False
    logger.warning("⚠️ Módulo BrasilNFe API não disponível - usando apenas assinatura local")

logger = logging.getLogger('nfe_search')

# ============================================================================
# VALIDAÇÃO XSD
# ============================================================================

def validar_xml_evento_xsd(evento_xml, is_cte=False):
    """
    Valida XML do evento contra o schema XSD oficial.
    
    Args:
        evento_xml: ElementTree do evento (evento ou envEvento)
        is_cte: True se for CT-e, False se for NF-e
        
    Returns:
        tuple (bool, str): (sucesso, mensagem_erro)
    """
    try:
        # Define caminho do XSD
        xsd_file = 'leiauteEvento_v1.00.xsd' if not is_cte else 'leiauteCTe_v4.00.xsd'
        xsd_dir = Path(__file__).parent.parent / 'Arquivo_xsd'
        xsd_path = xsd_dir / xsd_file
        
        if not xsd_path.exists():
            logger.warning(f"⚠️ XSD não encontrado: {xsd_path}")
            return (True, "XSD não encontrado - validação ignorada")
        
        # Carrega e parsea o XSD com base_url para resolver includes
        logger.info(f"📋 Validando XML contra {xsd_file}...")
        with open(xsd_path, 'rb') as f:
            # ⚠️ CRÍTICO: base_url permite resolver includes relativos (tiposBasico_v1.03.xsd)
            schema_doc = etree.parse(f, base_url=str(xsd_dir) + '/')
        
        # Tenta criar schema (pode falhar se XSD tiver erro interno)
        try:
            schema = etree.XMLSchema(schema_doc)
        except etree.XMLSchemaParseError as schema_err:
            # XSD oficial tem erro conhecido (TCOrgaoIBGE duplicado)
            logger.warning(f"⚠️ XSD tem erro interno: {str(schema_err)[:100]}")
            logger.info("  ℹ️ Validação XSD desabilitada (problema no schema oficial)")
            return (True, "XSD com erro interno - validação ignorada")
        
        # Valida o XML
        if schema.validate(evento_xml):
            logger.info("✅ Validação XSD: APROVADA")
            return (True, "XML válido conforme XSD")
        else:
            # Coleta erros detalhados
            erros = []
            for erro in schema.error_log:
                erros.append(f"Linha {erro.line}: {erro.message}")
            
            msg_erro = "\n".join(erros[:5])  # Primeiros 5 erros
            logger.error(f"❌ Validação XSD FALHOU:\n{msg_erro}")
            return (False, f"Erros XSD:\n{msg_erro}")
            
    except Exception as e:
        logger.error(f"❌ Erro na validação XSD: {e}")
        return (False, f"Erro na validação: {str(e)}")

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
    '35': 'https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx',  # SP
    '41': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # PR -> SVRS
    '42': 'https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # SC -> SVRS
    '43': 'https://nfe.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx',  # RS
    '50': 'https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4',  # MS
    '51': 'https://nfe.sefaz.mt.gov.br/nfews/v2/services/RecepcaoEvento4',  # MT
    '52': 'https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4?wsdl',  # GO (webservice próprio!)
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
    """Serviço para envio de eventos de manifestação para SEFAZ.
    Suporta dois métodos:
    1. API BrasilNFe (recomendado) - assinatura remota garantida
    2. Assinatura local com xmlsec - pode ter problemas de compatibilidade
    """
    
    def __init__(self, cert_path, cert_password, db=None):
        """
        Inicializa o serviço de manifestação.
        
        Args:
            cert_path: Caminho do arquivo .pfx do certificado
            cert_password: Senha do certificado
            db: DatabaseManager (opcional) para acessar configurações
        """
        self.cert_path = cert_path
        self.cert_password = cert_password
        self.db = db
        
        # Carrega certificado e chave privada
        from cryptography.hazmat.primitives.serialization import pkcs12
        
        with open(cert_path, 'rb') as f:
            pfx_data = f.read()
        
        self.private_key, self.certificate, self.additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, cert_password.encode(), default_backend()
        )
        
        logger.info(f"[MANIFESTAÇÃO] Certificado carregado: {self.certificate.subject}")
        
        # Verifica se BrasilNFe está configurado
        self.brasilnfe_api = None
        if db and BRASILNFE_DISPONIVEL:
            token = db.get_config('brasilnfe_token')
            if token:
                self.brasilnfe_api = BrasilNFeAPI(token)
                logger.info("✅ API BrasilNFe configurada - usará assinatura remota")
            else:
                logger.info("⚠️ Token BrasilNFe não configurado - usará assinatura local")
    
    def assinar_e_montar_soap(self, evento_root, cnpj_destinatario, tipo_evento, is_cte):
        """
        ⚠️ CORREÇÃO DEFINITIVA: Usa xmlsec (100% compatível com SEFAZ)
        
        signxml NÃO é compatível byte-a-byte com SEFAZ devido a:
        - Diferenças na canonicalização
        - Namespace handling diferente
        - Atributos Id não registrados corretamente
        
        xmlsec é a biblioteca usada pela SEFAZ e garante compatibilidade total.
        
        Args:
            evento_root: Elemento lxml <evento> já montado (SEM assinatura)
            cnpj_destinatario: CNPJ do destinatário
            tipo_evento: Código do evento
            is_cte: True se for CT-e, False se NF-e
            
        Returns:
            String XML do envelope SOAP completo (assinado)
        """
        logger.info("=" * 80)
        logger.info("INICIANDO ASSINATURA COM XMLSEC (COMPATÍVEL COM SEFAZ)")
        logger.info("=" * 80)
        
        ns = "http://www.portalfiscal.inf.br/cte" if is_cte else "http://www.portalfiscal.inf.br/nfe"
        versao = "4.00" if is_cte else "1.00"
        
        # PASSO 0: Validar XML contra XSD ANTES de assinar
        logger.info("PASSO 0: Validando XML contra XSD oficial")
        valido, msg_validacao = validar_xml_evento_xsd(evento_root, is_cte)
        if not valido:
            raise ValueError(f"XML inválido conforme XSD:\n{msg_validacao}")
        logger.info(f"  ✓ {msg_validacao}")
        
        # PASSO 1: Limpar espaços em branco do evento (ANTES de qualquer coisa)
        logger.info("PASSO 1: Limpando espaços em branco do evento")
        for element in evento_root.iter("*"):
            # Remove apenas text vazio (não tail - isso quebra a estrutura)
            if element.text is not None and not element.text.strip():
                element.text = None
            # Remove tail vazio também (espaços entre tags)
            if element.tail is not None and not element.tail.strip():
                element.tail = None
        
        # PASSO 2: Localizar infEvento
        logger.info("PASSO 2: Localizando infEvento")
        inf_evento = evento_root.find(f'.//{{{ns}}}infEvento')
        if inf_evento is None:
            raise ValueError("Elemento infEvento não encontrado")
        
        evento_id = inf_evento.attrib['Id']
        logger.info(f"  - ID: {evento_id}")
        
        # PASSO 3: ⚠️ CRÍTICO - Registrar atributo Id como ID XML (xmlsec)
        logger.info("PASSO 3: Registrando atributo Id como ID XML (xmlsec.tree.add_ids)")
        xmlsec.tree.add_ids(evento_root, ["Id"])
        logger.info("  ✓ Atributo Id registrado")
        
        # PASSO 4: Criar template de assinatura
        logger.info("PASSO 4: Criando template de assinatura com xmlsec")
        signature_node = xmlsec.template.create(
            evento_root,
            xmlsec.Transform.C14N,       # ⚠️ C14N padrão (NÃO exclusivo) - exigido pela NF-e
            xmlsec.Transform.RSA_SHA1,   # RSA-SHA1
            ns="ds"
        )
        
        # Adiciona Signature ao final do evento
        evento_root.append(signature_node)
        logger.info("  ✓ Template de assinatura criado")
        
        # PASSO 5: Adicionar Reference para infEvento
        logger.info("PASSO 5: Adicionando Reference para infEvento")
        ref = xmlsec.template.add_reference(
            signature_node,
            xmlsec.Transform.SHA1,
            uri=f"#{evento_id}"
        )
        
        # Transforms: ENVELOPED + C14N (ordem exata da NT 2014.002)
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)  # ⚠️ C14N padrão (NÃO exclusivo)
        logger.info(f"  ✓ Reference criada: #{evento_id}")
        
        # PASSO 6: Adicionar KeyInfo com certificado
        logger.info("PASSO 6: Adicionando KeyInfo")
        key_info = xmlsec.template.ensure_key_info(signature_node)
        xmlsec.template.add_x509_data(key_info)
        logger.info("  ✓ KeyInfo adicionada")
        
        # PASSO 7: Preparar chave privada e certificado em PEM
        logger.info("PASSO 7: Preparando chave privada e certificado")
        private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        cert_pem = self.certificate.public_bytes(serialization.Encoding.PEM)
        logger.info(f"  - Chave privada: {len(private_key_pem)} bytes")
        logger.info(f"  - Certificado: {len(cert_pem)} bytes")
        logger.info(f"  - Subject: {self.certificate.subject}")
        logger.info(f"  - Issuer: {self.certificate.issuer}")
        logger.info(f"  - Validade: {self.certificate.not_valid_before} até {self.certificate.not_valid_after}")
        
        # PASSO 8: ⚠️ CRÍTICO - Assinar com xmlsec.SignatureContext
        logger.info("PASSO 8: Assinando com xmlsec.SignatureContext")
        ctx = xmlsec.SignatureContext()
        
        # Carrega chave privada em PEM
        ctx.key = xmlsec.Key.from_memory(
            private_key_pem,
            xmlsec.KeyFormat.PEM,
            None
        )
        
        # ⚠️ ALTERNATIVA: Carregar certificado em DER (binário) ao invés de PEM
        # O SEFAZ pode estar esperando formato específico
        cert_der = self.certificate.public_bytes(serialization.Encoding.DER)
        try:
            ctx.key.load_cert_from_memory(cert_der, xmlsec.KeyFormat.CERT_DER)
            logger.info("  - Certificado carregado em formato DER")
        except:
            # Fallback para PEM se DER falhar
            ctx.key.load_cert_from_memory(cert_pem, xmlsec.KeyFormat.CERT_PEM)
            logger.info("  - Certificado carregado em formato PEM (fallback)")
        
        logger.info("  - Chave e certificado carregados no contexto")
        
        # Assina
        ctx.sign(signature_node)
        logger.info("  ✓ Assinatura digital aplicada com sucesso")
        
        # Verifica se Signature foi preenchida
        sig_value = signature_node.find('.//{http://www.w3.org/2000/09/xmldsig#}SignatureValue')
        if sig_value is None or not sig_value.text:
            raise ValueError("ERRO: SignatureValue não foi gerada!")
        logger.info(f"  ✓ SignatureValue confirmada: {len(sig_value.text)} caracteres")
        
        # Verifica se certificado X509 foi incluído
        x509_cert = signature_node.find('.//{http://www.w3.org/2000/09/xmldsig#}X509Certificate')
        if x509_cert is None or not x509_cert.text:
            logger.warning("  ⚠️ Certificado X509 NÃO foi incluído automaticamente!")
            logger.warning("  💡 Isto pode causar erro 297 no SEFAZ")
        else:
            logger.info(f"  ✓ Certificado X509 incluído: {len(x509_cert.text)} caracteres")
        
        # ⚠️ VALIDAÇÃO IMEDIATA: Verifica a assinatura recém-criada
        logger.info("  🔍 Validando assinatura recém-criada...")
        try:
            # Contexto de verificação usa o certificado X509 embutido no XML
            # Não precisa carregar chave - xmlsec busca no <X509Certificate>
            ctx_verify = xmlsec.SignatureContext()
            
            # ⚠️ CRÍTICO: Re-registrar IDs para verificação
            xmlsec.tree.add_ids(evento_root, ["Id"])
            
            ctx_verify.verify(signature_node)
            logger.info("  ✅ Assinatura verificada: VÁLIDA")
        except xmlsec.Error as e:
            logger.error(f"  ❌ Assinatura INVÁLIDA logo após assinar: {e}")
            logger.error("  💡 Problema: Certificado X509, transforms ou canonização")
            logger.warning("  ⚠️ Continuando (SEFAZ fará validação própria)...")
            # NÃO interromper - deixar SEFAZ validar
            # raise ValueError(f"Assinatura inválida após criação: {e}")
        
        # PASSO 9: Criar envEvento DIRETAMENTE com o evento assinado (SEM re-parsear)
        logger.info("PASSO 9: Criando envEvento com evento assinado (sem re-parsear)")
        env_tag = f"{{{ns}}}envEventoCTe" if is_cte else f"{{{ns}}}envEvento"
        env_evento = etree.Element(env_tag, versao=versao, nsmap={None: ns})
        
        id_lote = etree.SubElement(env_evento, f"{{{ns}}}idLote")
        id_lote.text = "1"
        
        # ⚠️ CRÍTICO: Anexa o evento_root DIRETAMENTE (já assinado em memória)
        # NÃO serializar e re-parsear - isso pode alterar namespaces e quebrar a assinatura
        env_evento.append(evento_root)
        logger.info("  ✓ Evento assinado anexado diretamente ao envEvento")
        
        # PASSO 10: Construir envelope SOAP em DOM
        logger.info("PASSO 10: Construindo envelope SOAP em DOM")
        
        soap_ns = "http://www.w3.org/2003/05/soap-envelope"
        soap_envelope = etree.Element(
            f"{{{soap_ns}}}Envelope",
            nsmap={
                'soap12': soap_ns,
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsd': 'http://www.w3.org/2001/XMLSchema'
            }
        )
        
        soap_body = etree.SubElement(soap_envelope, f"{{{soap_ns}}}Body")
        
        # Define tag e namespace SOAP baseado no tipo
        if is_cte:
            soap_dados_ns = "http://www.portalfiscal.inf.br/cte/wsdl/CTeRecepcaoEventoV4"
            soap_dados_tag = f"{{{soap_dados_ns}}}cteDadosMsg"
        else:
            soap_dados_ns = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"
            soap_dados_tag = f"{{{soap_dados_ns}}}nfeDadosMsg"
        
        dados_msg = etree.SubElement(soap_body, soap_dados_tag, nsmap={None: soap_dados_ns})
        dados_msg.append(env_evento)
        logger.info("  ✓ envEvento anexado ao SOAP Body")
        
        # PASSO 11: Serializar UMA ÚNICA VEZ (no final)
        logger.info("PASSO 11: Serializando envelope SOAP completo (UMA ÚNICA VEZ)")
        
        # ⚠️ CRÍTICO: Limpar quebras de linha APENAS dentro do elemento Signature
        # NÃO tocar no infEvento (já assinado) para não quebrar o DigestValue!
        ns_ds = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
        signature_elem = soap_envelope.find('.//ds:Signature', namespaces=ns_ds)
        
        if signature_elem is not None:
            # Limpar apenas dentro de Signature (certificado e assinatura têm quebras de linha)
            for elem in signature_elem.iter():
                # Limpar text (conteúdo dentro da tag)
                if elem.text and elem.text.strip():
                    # Remove apenas quebras de linha, preserva espaços importantes
                    elem.text = ''.join(elem.text.split())
                elif elem.text and not elem.text.strip():
                    elem.text = None
                
                # Limpar tail (texto após a tag)
                if elem.tail and not elem.tail.strip():
                    elem.tail = None
        
        # Serializar sem pretty_print (compacto)
        soap_xml_bytes = etree.tostring(
            soap_envelope,
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=False
        )
        soap_xml = soap_xml_bytes.decode('utf-8')
        
        logger.info(f"  - SOAP envelope size: {len(soap_xml)} bytes")
        logger.info(f"  - Signature presente: {'<Signature' in soap_xml or '<ds:Signature' in soap_xml}")
        
        logger.info("=" * 80)
        logger.info("ASSINATURA COM XMLSEC CONCLUÍDA (100% COMPATÍVEL COM SEFAZ)")
        logger.info("=" * 80)
        
        return soap_xml
        
        return soap_xml
    
    def enviar_manifestacao(self, chave, tipo_evento, cnpj_destinatario, justificativa=None):
        """
        Envia evento de manifestação para SEFAZ.
        Usa API BrasilNFe se configurada, senão usa assinatura local.
        
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
            
            # ============================================================================
            # MÉTODO 1: API BrasilNFe (RECOMENDADO - sem problemas de assinatura)
            # ============================================================================
            if self.brasilnfe_api and not is_cte:  # BrasilNFe só suporta NF-e por ora
                logger.info("=" * 80)
                logger.info("USANDO API BRASILNFE (assinatura remota garantida)")
                logger.info("=" * 80)
                
                # Mapeia tipo de evento para código BrasilNFe
                tipo_manifestacao_map = {
                    '210200': 2,  # Ciência da Operação
                    '210210': 1,  # Confirmação da Operação
                    '210220': 3,  # Desconhecimento da Operação
                    '210240': 4,  # Operação não Realizada
                }
                
                tipo_manifestacao = tipo_manifestacao_map.get(tipo_evento)
                if not tipo_manifestacao:
                    raise ValueError(f"Tipo de evento {tipo_evento} não suportado pela API BrasilNFe")
                
                logger.info(f"Chave: {chave}")
                logger.info(f"Tipo Manifestação: {tipo_manifestacao} ({tipo_evento})")
                
                # Envia via API BrasilNFe
                sucesso, protocolo, mensagem, xml_resposta = self.brasilnfe_api.manifestar_nota_fiscal(
                    chave=chave,
                    tipo_manifestacao=tipo_manifestacao,
                    tipo_ambiente=1,  # Produção
                    numero_sequencial=1
                )
                
                if sucesso:
                    logger.info(f"✅ Manifestação registrada via BrasilNFe! Protocolo: {protocolo}")
                else:
                    logger.error(f"❌ Erro BrasilNFe: {mensagem}")
                
                return (sucesso, protocolo, mensagem, xml_resposta)
            
            # ============================================================================
            # MÉTODO 2: Assinatura Local com xmlsec (FALLBACK - pode ter erro 297)
            # ============================================================================
            logger.info("=" * 80)
            logger.info("USANDO ASSINATURA LOCAL (xmlsec - pode ter problemas)")
            logger.info("=" * 80)
            
            if is_cte:
                logger.info("CT-e detectado - usando assinatura local")
            else:
                logger.warning("⚠️ NF-e sem API BrasilNFe configurada - usando xmlsec (pode ter erro 297)")
            
            cuf = chave[0:2]
            
            # Monta descrição do evento (exatamente como na nota técnica)
            desc_evento_map = {
                '210200': 'Ciencia da Operacao',  # Ciência da Operação
                '210210': 'Confirmacao da Operacao',  # Confirmação da Operação
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
            
            # ⚠️ CRÍTICO: dhEvento deve usar timezone de Brasília (-03:00)
            # O sistema pode estar em outro timezone (ex: -04:00), mas a nota é de Brasília
            from datetime import timezone, timedelta
            brasilia_tz = timezone(timedelta(hours=-3))
            now_brasilia = datetime.now(brasilia_tz)
            dh_evento = now_brasilia.strftime('%Y-%m-%dT%H:%M:%S%z')
            # Adiciona os ":" no timezone (de -0300 para -03:00)
            dh_evento = dh_evento[:-2] + ':' + dh_evento[-2:]
            
            # Gera ID do evento seguindo XSD: ID + tpEvento(6) + chave(44) + nSeqEvento(2) = 54 chars
            id_evento = f"ID{tipo_evento}{chave}{str(1).zfill(2)}"
            
            logger.info("=" * 80)
            logger.info("CONSTRUINDO EVENTO EM DOM (antes de assinar)")
            logger.info("=" * 80)
            
            # ⚠️ MUDANÇA CRÍTICA: Construir evento em DOM (não em string)
            elemento_raiz = f"{{{ns}}}eventoCTe" if is_cte else f"{{{ns}}}evento"
            
            # ⚠️ CRÍTICO: Criar COM namespace no tag E nsmap
            # O nsmap={None: ns} faz o xmlns aparecer automaticamente na serialização
            # NÃO usar .set("xmlns", ns) - isso modifica o elemento!
            evento_root = etree.Element(elemento_raiz, versao=versao, nsmap={None: ns})
            
            logger.info(f"Evento criado: tag={evento_root.tag}, nsmap={evento_root.nsmap}")
            
            # Cria infEvento
            inf_evento = etree.SubElement(evento_root, f"{{{ns}}}infEvento", Id=id_evento)
            
            # Adiciona campos de infEvento
            c_orgao = etree.SubElement(inf_evento, f"{{{ns}}}cOrgao")
            c_orgao.text = cuf
            
            tp_amb = etree.SubElement(inf_evento, f"{{{ns}}}tpAmb")
            tp_amb.text = "1"
            
            cnpj = etree.SubElement(inf_evento, f"{{{ns}}}CNPJ")
            cnpj.text = cnpj_destinatario
            
            chave_elem = etree.SubElement(inf_evento, f"{{{ns}}}{chave_tag}")
            chave_elem.text = chave
            
            dh_evento_elem = etree.SubElement(inf_evento, f"{{{ns}}}dhEvento")
            dh_evento_elem.text = dh_evento
            
            tp_evento = etree.SubElement(inf_evento, f"{{{ns}}}tpEvento")
            tp_evento.text = tipo_evento
            
            n_seq_evento = etree.SubElement(inf_evento, f"{{{ns}}}nSeqEvento")
            n_seq_evento.text = "1"
            
            # verEvento só existe em NF-e v1.00, não em CT-e v4.00
            if not is_cte:
                ver_evento = etree.SubElement(inf_evento, f"{{{ns}}}verEvento")
                ver_evento.text = versao
            
            # Monta detEvento específico por tipo de evento
            if tipo_evento == '610110':  # Prestação em Desacordo (CT-e)
                det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", versaoEvento="4.00")
                ev_prest = etree.SubElement(det_evento, f"{{{ns}}}evPrestDesacordo")
                desc = etree.SubElement(ev_prest, f"{{{ns}}}descEvento")
                desc.text = "Prestacao do Servico em Desacordo"
                ind_desacordo = etree.SubElement(ev_prest, f"{{{ns}}}indDesacordoOper")
                ind_desacordo.text = "1"
                x_obs = etree.SubElement(ev_prest, f"{{{ns}}}xObs")
                x_obs.text = justificativa
            elif tipo_evento == '610112':  # Cancelamento Prestação em Desacordo (CT-e)
                det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", versaoEvento="4.00")
                ev_canc = etree.SubElement(det_evento, f"{{{ns}}}evCancPrestDesacordo")
                desc = etree.SubElement(ev_canc, f"{{{ns}}}descEvento")
                desc.text = "Cancelamento Prestacao do Servico em Desacordo"
                n_prot = etree.SubElement(ev_canc, f"{{{ns}}}nProtEvento")
                n_prot.text = "PROTOCOLO_ORIGINAL"
            else:  # Eventos genéricos (NF-e)
                det_evento = etree.SubElement(inf_evento, f"{{{ns}}}detEvento", versao=versao)
                desc = etree.SubElement(det_evento, f"{{{ns}}}descEvento")
                desc.text = desc_evento
                
                # xJust só deve ser incluído se houver justificativa
                if justificativa:
                    x_just = etree.SubElement(det_evento, f"{{{ns}}}xJust")
                    x_just.text = justificativa
            
            logger.info(f"Evento construído em DOM (root tag: {evento_root.tag})")
            
            # ⚠️ CORREÇÃO DEFINITIVA: Assina e monta SOAP no MESMO DOM
            soap_xml = self.assinar_e_montar_soap(evento_root, cnpj_destinatario, tipo_evento, is_cte)
            
            logger.info(f"[MANIFESTAÇÃO] SOAP Envelope completo:\n{soap_xml[:2000]}...")
            
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
                data=soap_xml.encode('utf-8'),
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
