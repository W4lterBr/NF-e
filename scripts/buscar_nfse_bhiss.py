# -*- coding: utf-8 -*-
"""
Busca NFS-e via SOAP - BHISS Digital (Belo Horizonte)
"""
import sys
import os
import sqlite3
from datetime import datetime
from lxml import etree
import requests

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import requests_pkcs12
    PKCS12_AVAILABLE = True
except ImportError:
    PKCS12_AVAILABLE = False
    print("⚠️  requests-pkcs12 não disponível. Tentando com requests padrão...")

from nfe_search import logger, salvar_nfse_detalhada

# ============================================================================
# CONFIGURAÇÃO BHISS DIGITAL - BELO HORIZONTE
# ============================================================================

BHISS_CONFIG = {
    "nome": "BHISS Digital - Belo Horizonte",
    "url_producao": "https://bhissdigital.pbh.gov.br/bhiss-ws/nfse",
    "url_homologacao": "https://bhisshomologa.pbh.gov.br/bhiss-ws/nfse",
    "versao": "1.00",
    "namespace": "http://www.abrasf.org.br/nfse.xsd",
    "codigo_municipio": "3106200"
}

# ============================================================================
# FUNÇÕES SOAP
# ============================================================================

def construir_xml_consulta_bhiss(cnpj, inscricao_municipal, data_inicial, data_final):
    """
    Constrói XML de consulta no padrão BHISS (baseado em ABRASF)
    """
    namespace = BHISS_CONFIG["namespace"]
    
    # Remove formatação do CNPJ
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseEnvio xmlns="{namespace}">
    <Prestador>
        <Cnpj>{cnpj_limpo}</Cnpj>"""
    
    if inscricao_municipal:
        xml += f"""
        <InscricaoMunicipal>{inscricao_municipal}</InscricaoMunicipal>"""
    
    xml += f"""
    </Prestador>
    <Periodo>
        <DataInicial>{data_inicial}</DataInicial>
        <DataFinal>{data_final}</DataFinal>
    </Periodo>
</ConsultarNfseEnvio>"""
    
    return xml


def enviar_soap_bhiss(xml_corpo, cert_path, senha):
    """
    Envia requisição SOAP para BHISS Digital
    """
    url = BHISS_CONFIG["url_producao"]
    
    # Monta envelope SOAP 1.1
    soap_env = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        {xml_corpo}
    </soap:Body>
</soap:Envelope>"""
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '""',  # BHISS usa SOAPAction vazio
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    logger.info(f"📤 Enviando requisição SOAP para BHISS...")
    logger.info(f"   URL: {url}")
    
    try:
        if PKCS12_AVAILABLE and cert_path and senha:
            response = requests_pkcs12.post(
                url,
                data=soap_env.encode('utf-8'),
                headers=headers,
                pkcs12_filename=cert_path,
                pkcs12_password=senha,
                timeout=60
            )
        else:
            # Fallback sem certificado (pode não funcionar)
            response = requests.post(
                url,
                data=soap_env.encode('utf-8'),
                headers=headers,
                timeout=60,
                verify=True
            )
        
        logger.info(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Resposta recebida com sucesso")
            return response.text
        else:
            logger.error(f"❌ Erro na requisição: {response.status_code}")
            logger.error(f"   Resposta: {response.text[:500]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar SOAP: {e}")
        return None


def processar_resposta_bhiss(xml_resposta, db, informante):
    """
    Processa resposta XML do BHISS e extrai NFS-e
    """
    if not xml_resposta:
        return 0
    
    try:
        # Remove namespaces para facilitar parsing
        xml_limpo = xml_resposta
        for ns in ['soap:', 'ns1:', 'ns2:', 'nfse:', 'tipos:']:
            xml_limpo = xml_limpo.replace(ns, '')
        
        root = etree.fromstring(xml_limpo.encode('utf-8'))
        
        # Busca CompNfse (cada nota completa)
        notas_encontradas = []
        
        # Diferentes padrões de resposta
        patterns = [
            './/CompNfse',
            './/Nfse',
            './/NFSe',
            './/ListaNfse/CompNfse',
        ]
        
        for pattern in patterns:
            notas = root.xpath(pattern)
            if notas:
                notas_encontradas.extend(notas)
                break
        
        if not notas_encontradas:
            logger.warning("⚠️  Nenhuma NFS-e encontrada na resposta")
            
            # Verifica se há mensagem de erro
            erros = root.xpath('.//MensagemRetorno') or root.xpath('.//Erro')
            if erros:
                for erro in erros:
                    codigo = erro.findtext('.//Codigo', '')
                    mensagem = erro.findtext('.//Mensagem', '')
                    logger.error(f"   Erro {codigo}: {mensagem}")
            
            return 0
        
        logger.info(f"📋 Encontradas {len(notas_encontradas)} NFS-e na resposta")
        
        total_salvas = 0
        for nota_elem in notas_encontradas:
            try:
                # Converte elemento de volta para XML string
                xml_nota = etree.tostring(nota_elem, encoding='unicode')
                
                # Salva usando a função existente do nfe_search
                if salvar_nfse_detalhada(xml_nota, db, informante):
                    total_salvas += 1
                    
            except Exception as e_nota:
                logger.error(f"   ❌ Erro ao processar nota individual: {e_nota}")
                continue
        
        logger.info(f"✅ Total salvas: {total_salvas}/{len(notas_encontradas)}")
        return total_salvas
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar resposta: {e}")
        logger.error(f"   XML recebido: {xml_resposta[:1000]}")
        return 0


def buscar_nfse_bhiss_periodo(cnpj, inscricao_municipal, data_inicial, data_final, cert_path, senha, db):
    """
    Função principal - busca NFS-e via BHISS por período
    """
    logger.info("="*80)
    logger.info("🔍 BUSCA NFS-e VIA SOAP - BHISS DIGITAL (BELO HORIZONTE)")
    logger.info("="*80)
    logger.info(f"📅 Período: {data_inicial} → {data_final}")
    logger.info(f"🏢 CNPJ: {cnpj}")
    logger.info(f"📋 Inscrição Municipal: {inscricao_municipal if inscricao_municipal else '(não informada)'}")
    logger.info(f"🔌 Sistema: {BHISS_CONFIG['nome']}")
    logger.info(f"🌐 URL: {BHISS_CONFIG['url_producao']}")
    logger.info("")
    
    # 1. Constrói XML
    xml_consulta = construir_xml_consulta_bhiss(cnpj, inscricao_municipal, data_inicial, data_final)
    
    # 2. Envia SOAP
    xml_resposta = enviar_soap_bhiss(xml_consulta, cert_path, senha)
    
    if not xml_resposta:
        logger.error("❌ Falha na consulta SOAP")
        return 0
    
    # 3. Processa resposta
    total = processar_resposta_bhiss(xml_resposta, db, cnpj)
    
    return total


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🔍 BUSCA NFS-e - BHISS DIGITAL (BELO HORIZONTE)")
    print("="*80)
    print()
    
    # Parâmetros fixos
    CNPJ = "56237242000158"
    INSCRICAO_MUNICIPAL = ""  # Deixar vazio se não souber
    DATA_INICIAL = "2025-01-01"
    DATA_FINAL = "2026-02-18"
    
    # Busca certificado no banco
    from nfe_search import DatabaseManager
    
    db_path = os.path.join(os.path.dirname(__file__), 'notas.db')
    db = DatabaseManager(db_path)
    
    # Busca todos certificados e filtra pelo CNPJ
    certificados = db.get_certificados()
    cert_data = None
    
    for cnpj, caminho, senha, informante, cuf in certificados:
        if informante == CNPJ:
            cert_data = (caminho, senha)
            break
    
    if not cert_data:
        print(f"❌ Certificado não encontrado para CNPJ {CNPJ}")
        sys.exit(1)
    
    cert_path, senha = cert_data
    
    print(f"📜 Certificado encontrado: {cert_path}")
    print(f"🔐 CNPJ: {CNPJ}")
    print()
    
    # Exibe resumo
    print("📋 RESUMO DA BUSCA:")
    print(f"   Sistema: {BHISS_CONFIG['nome']}")
    print(f"   URL: {BHISS_CONFIG['url_producao']}")
    print(f"   Período: {DATA_INICIAL} a {DATA_FINAL}")
    print(f"   CNPJ: {CNPJ}")
    print(f"   Inscrição: {INSCRICAO_MUNICIPAL if INSCRICAO_MUNICIPAL else '(não informada)'}")
    print()
    
    confirmacao = input("⚠️  Deseja continuar? (S/N): ").strip().upper()
    if confirmacao != 'S':
        print("❌ Operação cancelada")
        sys.exit(0)
    
    print()
    print("🚀 Iniciando busca...")
    print()
    
    # Executa busca
    total_baixadas = buscar_nfse_bhiss_periodo(
        cnpj=CNPJ,
        inscricao_municipal=INSCRICAO_MUNICIPAL,
        data_inicial=DATA_INICIAL,
        data_final=DATA_FINAL,
        cert_path=cert_path,
        senha=senha,
        db=db
    )
    
    print()
    print("="*80)
    print(f"✅ Processo concluído: {total_baixadas} NFS-e baixadas")
    print("="*80)
