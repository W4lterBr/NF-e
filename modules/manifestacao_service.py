"""
Serviço de Manifestação de Documentos Fiscais (NF-e e CT-e)
Implementa envio de eventos de manifestação para SEFAZ usando PyNFe
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from lxml import etree

# Biblioteca PyNFe para manifestação
from pynfe.processamento.comunicacao import ComunicacaoSefaz
from pynfe.processamento.assinatura import AssinaturaA1
from pynfe.processamento.serializacao import SerializacaoXML
from pynfe.entidades.evento import EventoManifestacaoDest

logger = logging.getLogger('nfe_search')


class ManifestacaoService:
    """Serviço para envio de eventos de manifestação para SEFAZ usando PyNFe."""
    
    def __init__(self, certificado_path: str, certificado_senha: str):
        """
        Inicializa o serviço de manifestação.
        
        Args:
            certificado_path: Caminho do certificado .pfx/.p12
            certificado_senha: Senha do certificado
        """
        self.certificado_path = certificado_path
        self.certificado_senha = certificado_senha
        
        # Verificar se certificado existe
        if not Path(certificado_path).exists():
            raise FileNotFoundError(f"Certificado não encontrado: {certificado_path}")
        
        logger.info(f"[MANIFESTAÇÃO PyNFe] Serviço inicializado")
    
    def enviar_manifestacao(
        self,
        chave: str,
        tipo_evento: str,
        cnpj_destinatario: str,
        justificativa: Optional[str] = None
    ) -> Tuple[bool, str, str, str]:
        """
        Envia evento de manifestação para SEFAZ usando PyNFe.
        
        Args:
            chave: Chave de acesso da NF-e (44 dígitos)
            tipo_evento: Código do evento (210200, 210210, 210220, 210240)
            cnpj_destinatario: CNPJ do destinatário manifestante
            justificativa: Justificativa (obrigatória para tipo 210240)
            
        Returns:
            Tupla (sucesso, protocolo, mensagem, xml_resposta)
        """
        try:
            logger.info("=" * 80)
            logger.info("MANIFESTAÇÃO COM PyNFe")
            logger.info("=" * 80)
            logger.info(f"Chave: {chave}")
            logger.info(f"Tipo evento: {tipo_evento}")
            
            # Mapear tipo de evento para código PyNFe
            # 1=Confirmação, 2=Ciência, 3=Desconhecimento, 4=Operação não Realizada
            mapa_eventos = {
                '210200': 1,  # Confirmação da Operação
                '210210': 2,  # Ciência da Operação
                '210220': 3,  # Desconhecimento da Operação
                '210240': 4   # Operação não Realizada
            }
            
            if tipo_evento not in mapa_eventos:
                return (False, "", f"Tipo de evento inválido: {tipo_evento}", "")
            
            operacao = mapa_eventos[tipo_evento]
            
            # Extrair UF da chave (primeiros 2 dígitos)
            uf_codigo = chave[0:2]
            
            # Criar evento de manifestação
            # IMPORTANTE: usar uf='AN' para forçar cOrgao=91 (Ambiente Nacional)
            evento = EventoManifestacaoDest(
                cnpj=cnpj_destinatario,
                chave=chave,
                data_emissao=datetime.now(),
                operacao=operacao,
                uf='AN',      # Ambiente Nacional para manifestação
                orgao='91',   # 91 = Ambiente Nacional
            )
            
            # Adicionar justificativa se necessário
            if justificativa and operacao == 4:  # Operação não Realizada
                evento.justificativa = justificativa
            
            logger.info(f"Evento criado: {evento.descricao}")
            logger.info(f"ID: {evento.identificador}")
            
            # Serializar evento para XML
            logger.info("Serializando evento...")
            serializador = SerializacaoXML(None, homologacao=False)
            xml_evento = serializador.serializar_evento(evento, retorna_string=False)
            
            # Assinar evento
            logger.info("Assinando evento com PyNFe...")
            assinatura = AssinaturaA1(self.certificado_path, self.certificado_senha)
            xml_assinado = assinatura.assinar(xml_evento)
            
            xml_str = etree.tostring(xml_assinado, encoding='unicode')
            logger.info(f"Evento assinado ({len(xml_str)} bytes)")
            
            # Enviar para SEFAZ
            logger.info("Enviando para SEFAZ via Ambiente Nacional...")
            comunicacao = ComunicacaoSefaz(
                uf=uf_codigo,  # UF da chave (usado apenas para roteamento)
                certificado=self.certificado_path,
                certificado_senha=self.certificado_senha,
                homologacao=False
            )
            
            # Enviar evento (modelo='55' para NF-e)
            resposta = comunicacao.evento(modelo='55', evento=xml_assinado)
            
            logger.info(f"Status HTTP: {resposta.status_code}")
            
            # Parsear resposta XML
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            root = etree.fromstring(resposta.content)
            ret_env_evento = root.find('.//nfe:retEnvEvento', namespaces=ns)
            
            if ret_env_evento is None:
                logger.error("Resposta SEFAZ sem retEnvEvento")
                return (False, "", "Resposta SEFAZ inválida", resposta.text)
            
            # Status do lote
            c_stat_lote = ret_env_evento.findtext('.//nfe:cStat', namespaces=ns)
            x_motivo_lote = ret_env_evento.findtext('.//nfe:xMotivo', namespaces=ns)
            
            logger.info(f"cStat Lote: {c_stat_lote} - {x_motivo_lote}")
            
            # Verificar retEvento
            ret_evento = ret_env_evento.find('.//nfe:retEvento', namespaces=ns)
            if ret_evento is not None:
                inf_evento = ret_evento.find('.//nfe:infEvento', namespaces=ns)
                if inf_evento is not None:
                    c_stat = inf_evento.findtext('.//nfe:cStat', namespaces=ns)
                    x_motivo = inf_evento.findtext('.//nfe:xMotivo', namespaces=ns)
                    n_prot = inf_evento.findtext('.//nfe:nProt', namespaces=ns)
                    
                    logger.info(f"cStat Evento: {c_stat} - {x_motivo}")
                    if n_prot:
                        logger.info(f"Protocolo: {n_prot}")
                    
                    # Verificar sucesso (135 = Evento registrado e vinculado)
                    if c_stat == '135':
                        logger.info("MANIFESTAÇÃO REGISTRADA COM SUCESSO!")
                        return (True, n_prot or "", x_motivo, resposta.text)
                    elif c_stat == '573':
                        # Duplicidade - consideramos sucesso pois evento já foi registrado
                        logger.info("Evento já registrado anteriormente (duplicidade)")
                        return (True, n_prot or "", f"Duplicidade: {x_motivo}", resposta.text)
                    else:
                        logger.warning(f"Evento rejeitado: {c_stat} - {x_motivo}")
                        return (False, "", f"Rejeicao {c_stat}: {x_motivo}", resposta.text)
            
            # Se chegou aqui, não encontrou retEvento
            return (False, "", f"Lote processado mas sem retEvento: {x_motivo_lote}", resposta.text)
            
        except Exception as e:
            logger.error(f"Erro ao enviar manifestacao: {e}", exc_info=True)
            return (False, "", f"Erro: {str(e)}", "")
