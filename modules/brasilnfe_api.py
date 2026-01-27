# -*- coding: utf-8 -*-
"""
API BrasilNFe - Manifestação do Destinatário
https://brasilnfe.com.br/api/eventos

Vantagens:
- Assinatura feita nos servidores BrasilNFe (sem problemas de xmlsec)
- Já testado e compatível com SEFAZ
- Suporte técnico disponível
- Elimina erro 297 de assinatura
"""
import requests
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class BrasilNFeAPI:
    """Cliente para API BrasilNFe - Manifestação de NF-e"""
    
    BASE_URL = "https://api.brasilnfe.com.br/services/fiscal"
    
    # Tipos de manifestação
    TIPO_CONFIRMACAO = 1
    TIPO_CIENCIA = 2
    TIPO_DESCONHECIMENTO = 3
    TIPO_NAO_REALIZADA = 4
    
    def __init__(self, api_token: str):
        """
        Inicializa cliente da API BrasilNFe
        
        Args:
            api_token: Token de autenticação da API
        """
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_token}'
        })
    
    def manifestar_nota_fiscal(
        self,
        chave: str,
        tipo_manifestacao: int,
        tipo_ambiente: int = 1,
        numero_sequencial: int = 1
    ) -> Tuple[bool, Optional[str], str, Optional[str]]:
        """
        Envia manifestação do destinatário via API BrasilNFe
        
        Args:
            chave: Chave de acesso da NF-e (44 dígitos)
            tipo_manifestacao: 1=Confirmação, 2=Ciência, 3=Desconhecimento, 4=Não Realizada
            tipo_ambiente: 1=Produção, 2=Homologação
            numero_sequencial: Número sequencial do evento (padrão 1)
        
        Returns:
            Tupla (sucesso, protocolo, mensagem, xml_resposta)
        """
        url = f"{self.BASE_URL}/ManifestarNotaFiscal"
        
        payload = {
            "TipoAmbiente": tipo_ambiente,
            "TipoManifestacao": tipo_manifestacao,
            "Chave": chave,
            "NumeroSequencial": numero_sequencial
        }
        
        logger.info(f"[BrasilNFe] Enviando manifestação para chave {chave}")
        logger.info(f"[BrasilNFe] Tipo: {tipo_manifestacao}, Ambiente: {tipo_ambiente}")
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            
            logger.info(f"[BrasilNFe] Status HTTP: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Erro HTTP {response.status_code}: {response.text}"
                logger.error(f"[BrasilNFe] {error_msg}")
                return False, None, error_msg, None
            
            data = response.json()
            
            # Extrair informações da resposta
            status = data.get('Status')
            ds_motivo = data.get('DsMotivo', '')
            ds_evento = data.get('DsEvento', '')
            nu_protocolo = data.get('NuProtocolo')
            cod_status_sefaz = data.get('CodStatusRespostaSefaz')
            error = data.get('Error', '')
            
            logger.info(f"[BrasilNFe] Status: {status}")
            logger.info(f"[BrasilNFe] Motivo: {ds_motivo}")
            logger.info(f"[BrasilNFe] Protocolo: {nu_protocolo}")
            logger.info(f"[BrasilNFe] Código SEFAZ: {cod_status_sefaz}")
            
            if status == 1:
                # Evento processado com sucesso
                sucesso = True
                mensagem = f"{ds_evento}: {ds_motivo}"
            elif status == 2:
                # Aguardando processamento
                sucesso = False
                mensagem = f"Aguardando processamento: {ds_motivo}"
            elif status == 3:
                # Erro ao processar
                sucesso = False
                mensagem = f"Erro: {error or ds_motivo}"
            else:
                sucesso = False
                mensagem = f"Status desconhecido ({status}): {ds_motivo}"
            
            # Tentar gerar XML de resposta simulado (para compatibilidade)
            xml_resposta = self._gerar_xml_resposta_simulado(data)
            
            return sucesso, nu_protocolo, mensagem, xml_resposta
            
        except requests.RequestException as e:
            error_msg = f"Erro de conexão com API BrasilNFe: {str(e)}"
            logger.error(f"[BrasilNFe] {error_msg}")
            return False, None, error_msg, None
        except Exception as e:
            error_msg = f"Erro inesperado: {str(e)}"
            logger.error(f"[BrasilNFe] {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None, error_msg, None
    
    def _gerar_xml_resposta_simulado(self, data: Dict) -> Optional[str]:
        """
        Gera XML de resposta simulado para compatibilidade com o sistema
        
        Args:
            data: Dados JSON da resposta da API
        
        Returns:
            XML simulado ou None
        """
        try:
            # XML básico para registrar a resposta
            xml = f'''<?xml version="1.0" encoding="utf-8"?>
<retEnvEvento xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00">
    <idLote>1</idLote>
    <tpAmb>{data.get('TipoAmbiente', 1)}</tpAmb>
    <verAplic>BrasilNFe API</verAplic>
    <cStat>{data.get('CodStatusRespostaSefaz', 0)}</cStat>
    <xMotivo>{data.get('DsMotivo', '')}</xMotivo>
    <retEvento versao="1.00">
        <infEvento>
            <tpAmb>{data.get('TipoAmbiente', 1)}</tpAmb>
            <verAplic>BrasilNFe API</verAplic>
            <cStat>{data.get('CodStatusRespostaSefaz', 0)}</cStat>
            <xMotivo>{data.get('DsMotivo', '')}</xMotivo>
            <nProt>{data.get('NuProtocolo', '')}</nProt>
        </infEvento>
    </retEvento>
</retEnvEvento>'''
            return xml
        except:
            return None
    
    def cancelar_nota_fiscal(
        self,
        chave: str,
        justificativa: str,
        numero_protocolo: Optional[str] = None,
        numero_sequencial: int = 1
    ) -> Tuple[bool, Optional[str], str, Optional[str]]:
        """
        Cancela uma NF-e via API BrasilNFe
        
        Args:
            chave: Chave de acesso da NF-e
            justificativa: Justificativa do cancelamento (min 15 caracteres)
            numero_protocolo: Protocolo de autorização (opcional)
            numero_sequencial: Número sequencial do evento
        
        Returns:
            Tupla (sucesso, protocolo, mensagem, xml_resposta)
        """
        url = f"{self.BASE_URL}/CancelarNotaFiscal"
        
        payload = {
            "ChaveNF": chave,
            "Justificativa": justificativa,
            "NumeroSequencial": numero_sequencial
        }
        
        if numero_protocolo:
            payload["NumeroProtocolo"] = numero_protocolo
        
        logger.info(f"[BrasilNFe] Enviando cancelamento para chave {chave}")
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                return False, None, f"Erro HTTP {response.status_code}", None
            
            data = response.json()
            
            sucesso = data.get('Status') == 1
            protocolo = data.get('NuProtocolo')
            mensagem = f"{data.get('DsEvento', '')}: {data.get('DsMotivo', '')}"
            xml_resposta = self._gerar_xml_resposta_simulado(data)
            
            return sucesso, protocolo, mensagem, xml_resposta
            
        except Exception as e:
            logger.error(f"[BrasilNFe] Erro ao cancelar: {e}")
            return False, None, str(e), None
    
    def carta_correcao(
        self,
        chave: str,
        correcao: str,
        tipo_ambiente: int = 1,
        numero_sequencial: int = 1
    ) -> Tuple[bool, Optional[str], str, Optional[str]]:
        """
        Envia Carta de Correção Eletrônica (CC-e) via API BrasilNFe
        
        Args:
            chave: Chave de acesso da NF-e
            correcao: Descrição da correção (min 15, max 1000 caracteres)
            tipo_ambiente: 1=Produção, 2=Homologação
            numero_sequencial: Número sequencial do evento
        
        Returns:
            Tupla (sucesso, protocolo, mensagem, xml_resposta)
        """
        url = f"{self.BASE_URL}/EnviarCartaCorrecao"
        
        payload = {
            "TipoAmbiente": tipo_ambiente,
            "ChaveNF": chave,
            "Correcao": correcao,
            "NumeroSequencial": numero_sequencial
        }
        
        logger.info(f"[BrasilNFe] Enviando carta de correção para chave {chave}")
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                return False, None, f"Erro HTTP {response.status_code}", None
            
            data = response.json()
            
            sucesso = data.get('Status') == 1
            protocolo = data.get('NuProtocolo')
            mensagem = f"{data.get('DsEvento', '')}: {data.get('DsMotivo', '')}"
            xml_resposta = self._gerar_xml_resposta_simulado(data)
            
            return sucesso, protocolo, mensagem, xml_resposta
            
        except Exception as e:
            logger.error(f"[BrasilNFe] Erro ao enviar CC-e: {e}")
            return False, None, str(e), None
