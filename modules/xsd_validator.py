"""
Validador XSD para XMLs de CT-e e NF-e
"""
import os
from lxml import etree
import logging

logger = logging.getLogger('BuscaNFe')

# Mapa de eventos para XSDs específicos
XSD_MAP_CTE = {
    '610110': 'evPrestDesacordo_v4.00.xsd',  # Prestação em desacordo
    '610112': 'evCancPrestDesacordo_v4.00.xsd',  # Cancelamento prestação em desacordo
    '610140': 'evGTV_v4.00.xsd',  # GTV
    '610150': 'evCECTe_v4.00.xsd',  # Comprovante de Entrega
    '610110': 'evPrestDesacordo_v4.00.xsd',
    '610111': 'evCancCECTe_v4.00.xsd',
    '110111': 'evCancCTe_v4.00.xsd',
    '110115': 'evCCeCTe_v4.00.xsd',
}

XSD_MAP_NFE = {
    '210200': 'eventoCancNFe_v1.00.xsd',
    '210210': 'eventoCancNFe_v1.00.xsd',
    '210220': 'eventoCancNFe_v1.00.xsd',
    '210240': 'eventoCancNFe_v1.00.xsd',
}


def validar_xml_evento(xml_string, tipo_evento, is_cte=True):
    """
    Valida XML do evento contra schema XSD apropriado.
    
    Args:
        xml_string: String com XML do evento (sem assinatura)
        tipo_evento: Código do tipo de evento (ex: '610110')
        is_cte: True para CT-e, False para NF-e
        
    Returns:
        Tupla (valido: bool, erros: list)
    """
    try:
        # Determina pasta de XSDs
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        xsd_dir = os.path.join(base_dir, 'Arquivo_xsd')
        
        if not os.path.exists(xsd_dir):
            logger.warning(f"[XSD] Pasta de XSDs não encontrada: {xsd_dir}")
            return True, []  # Não bloqueia se pasta não existe
        
        # Usa XSD geral para validação do envelope completo
        # (XSDs específicos validam apenas detEvento, não o envelope)
        xsd_filename = 'eventoCTe_v4.00.xsd' if is_cte else 'eventoNFe_v1.00.xsd'
        xsd_path = os.path.join(xsd_dir, xsd_filename)
        
        if not os.path.exists(xsd_path):
            logger.warning(f"[XSD] Arquivo XSD não encontrado: {xsd_path}")
            return True, []  # Não bloqueia se XSD não existe
        
        logger.info(f"[XSD] Validando contra: {xsd_filename}")
        
        # Carrega XSD
        try:
            with open(xsd_path, 'rb') as f:
                schema_doc = etree.parse(f)
            schema = etree.XMLSchema(schema_doc)
        except Exception as e:
            logger.error(f"[XSD] Erro ao carregar schema: {e}")
            return True, []  # Não bloqueia se falhar ao carregar
        
        # Parse XML
        try:
            xml_doc = etree.fromstring(xml_string.encode('utf-8'))
        except Exception as e:
            logger.error(f"[XSD] Erro ao fazer parse do XML: {e}")
            return False, [f"Erro ao fazer parse do XML: {e}"]
        
        # Valida
        valido = schema.validate(xml_doc)
        
        if valido:
            logger.info("[XSD] ✓ XML válido!")
            return True, []
        else:
            erros = []
            for erro in schema.error_log:
                erro_str = str(erro)
                # Ignora erro de Signature faltando (será adicionada depois)
                if "Signature" in erro_str and "Missing child element" in erro_str:
                    continue
                erros.append(erro_str)
            
            if not erros:  # Se só tinha erro de Signature, considera válido
                logger.info("[XSD] ✓ XML válido (ignorando Signature pendente)!")
                return True, []
            
            logger.error(f"[XSD] ✗ XML inválido: {len(erros)} erros")
            for erro in erros[:5]:  # Mostra no máximo 5 erros
                logger.error(f"[XSD]   - {erro}")
            return False, erros
            
    except Exception as e:
        logger.error(f"[XSD] Erro inesperado na validação: {e}")
        return True, []  # Não bloqueia em caso de erro inesperado


def extrair_erros_principais(erros):
    """
    Extrai mensagens de erro principais para exibir ao usuário.
    
    Args:
        erros: Lista de erros do validador
        
    Returns:
        String com resumo dos erros
    """
    if not erros:
        return ""
    
    mensagens = []
    for erro in erros[:3]:  # Primeiros 3 erros
        # Tenta extrair parte relevante
        if "Element" in erro and "expected" in erro:
            mensagens.append(erro.split(":", 1)[-1].strip())
        else:
            mensagens.append(erro)
    
    if len(erros) > 3:
        mensagens.append(f"... e mais {len(erros) - 3} erros")
    
    return "\n".join(mensagens)
