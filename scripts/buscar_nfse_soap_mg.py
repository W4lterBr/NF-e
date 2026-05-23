# -*- coding: utf-8 -*-
"""
Implementação de busca SOAP Municipal para NFS-e
Permite consultar notas por período em provedores municipais

Provedor detectado: Minas Gerais
CNPJ: 56237242000158 (COOPSERVIÇOS)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from lxml import etree
import requests
from requests.exceptions import RequestException

# Adiciona o módulo nfe_search ao path
sys.path.insert(0, str(Path(__file__).parent))
from nfe_search import DatabaseManager, logger

# ==============================================================================
# CONFIGURAÇÕES DE PROVEDORES POR ESTADO
# ==============================================================================

PROVEDORES_MG = {
    # Minas Gerais - Sistema estadual unificado
    "BETHA": {
        "nome": "Betha Sistemas (MG)",
        "url_producao": "https://e-gov.betha.com.br/e-nota-contribuinte-ws/nfseWS",
        "url_homologacao": "https://e-gov.betha.com.br/e-nota-contribuinte-test-ws/nfseWS",
        "versao": "2.02",
        "namespace": "http://www.betha.com.br/e-nota-contribuinte-ws"
    },
    "GINFES_MG": {
        "nome": "Ginfes (Padrão MG)",
        "url_producao": "https://producao.ginfes.com.br/ServiceGinfesImpl",
        "url_homologacao": "https://homologacao.ginfes.com.br/ServiceGinfesImpl",
        "versao": "3.0",
        "namespace": "http://www.ginfes.com.br/servico_consultar_nfse_envio"
    },
    "SISTEMA_MG": {
        "nome": "Sistema Municipal MG",
        "url_producao": "https://nfse.sistemamunicipal.net.br/ws/nfse.asmx",
        "url_homologacao": "https://nfse-hom.sistemamunicipal.net.br/ws/nfse.asmx",
        "versao": "2.00",
        "namespace": "http://www.abrasf.org.br/nfse.xsd"
    }
}


def detectar_provedor_mg(cnpj, db):
    """
    Detecta o provedor NFS-e do município baseado no CNPJ
    
    Args:
        cnpj: CNPJ da empresa
        db: DatabaseManager
    
    Returns:
        dict: Configuração do provedor
    """
    # Verifica se há configuração cadastrada
    try:
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='nfse_config'
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    SELECT provedor, url 
                    FROM nfse_config 
                    WHERE cnpj = ?
                """, (cnpj,))
                config = cursor.fetchone()
                
                if config:
                    provedor_nome, url_custom = config
                    
                    # Retorna configuração customizada
                    if provedor_nome.upper() in PROVEDORES_MG:
                        provedor = PROVEDORES_MG[provedor_nome.upper()].copy()
                        if url_custom:
                            provedor['url_producao'] = url_custom
                        return provedor
    except Exception as e:
        logger.warning(f"Erro ao buscar provedor cadastrado: {e}")
    
    # Padrão: Tenta Betha (mais comum em MG)
    logger.info("⚠️ Usando provedor padrão: Betha Sistemas (MG)")
    logger.info("💡 Para melhor precisão, cadastre o provedor específico do município")
    return PROVEDORES_MG["BETHA"]


def construir_xml_consulta_periodo(cnpj, inscricao_municipal, data_inicial, data_final, provedor):
    """
    Constrói XML de consulta por período conforme padrão ABRASF
    
    Args:
        cnpj: CNPJ do prestador
        inscricao_municipal: Inscrição municipal
        data_inicial: Data inicial (YYYY-MM-DD)
        data_final: Data final (YYYY-MM-DD)
        provedor: Configuração do provedor
    
    Returns:
        str: XML da requisição SOAP
    """
    ns = provedor['namespace']
    versao = provedor['versao']
    
    # XML ABRASF padrão
    root = etree.Element(f"{{{ns}}}ConsultarNfseEnvio", nsmap={'ns': ns})
    
    # Identificação do Prestador
    prestador = etree.SubElement(root, "Prestador")
    etree.SubElement(prestador, "Cnpj").text = cnpj
    if inscricao_municipal:
        etree.SubElement(prestador, "InscricaoMunicipal").text = inscricao_municipal
    
    # Período de emissão
    periodo = etree.SubElement(root, "PeriodoEmissao")
    etree.SubElement(periodo, "DataInicial").text = data_inicial
    etree.SubElement(periodo, "DataFinal").text = data_final
    
    # Converte para string
    xml_str = etree.tostring(root, encoding='unicode', pretty_print=True)
    
    return xml_str


def enviar_soap_consulta(url, xml_corpo, provedor, cert_path, senha):
    """
    Envia requisição SOAP para consultar NFS-e
    
    Args:
        url: URL do webservice
        xml_corpo: Corpo da mensagem SOAP (XML interno)
        provedor: Configuração do provedor
        cert_path: Caminho do certificado .pfx
        senha: Senha do certificado
    
    Returns:
        str: XML de resposta ou None
    """
    # Envelope SOAP 1.1
    soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ns="{provedor['namespace']}">
    <soap:Header/>
    <soap:Body>
        {xml_corpo}
    </soap:Body>
</soap:Envelope>"""
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': f'"{provedor["namespace"]}/ConsultarNfse"'
    }
    
    try:
        # Tenta com requests-pkcs12 (certificado digital)
        try:
            import requests_pkcs12
            
            with open(cert_path, 'rb') as f:
                pkcs12_data = f.read()
            
            response = requests_pkcs12.post(
                url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                pkcs12_data=pkcs12_data,
                pkcs12_password=senha,
                timeout=60
            )
        except ImportError:
            # Fallback: requests normal (sem certificado)
            logger.warning("⚠️ requests_pkcs12 não disponível, tentando sem certificado")
            response = requests.post(
                url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=60
            )
        
        response.raise_for_status()
        
        logger.info(f"✅ Resposta SOAP recebida ({len(response.content)} bytes)")
        return response.text
        
    except RequestException as e:
        logger.error(f"❌ Erro na requisição SOAP: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"   Resposta: {e.response.text[:500]}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao enviar SOAP: {e}")
        return None


def processar_resposta_nfse(xml_resposta, db, informante):
    """
    Processa XML de resposta e extrai NFS-e
    
    Args:
        xml_resposta: XML de resposta SOAP
        db: DatabaseManager
        informante: CNPJ do informante
    
    Returns:
        int: Quantidade de notas processadas
    """
    try:
        # Parse do XML
        tree = etree.fromstring(xml_resposta.encode('utf-8'))
        
        # Remove namespace para facilitar busca
        for elem in tree.iter():
            if '}' in str(elem.tag):
                elem.tag = elem.tag.split('}', 1)[1]
        
        # Busca por tags de NFS-e (múltiplos padrões)
        notas = tree.findall('.//CompNfse') or tree.findall('.//Nfse') or tree.findall('.//NFSe')
        
        if not notas:
            logger.warning("⚠️ Nenhuma NFS-e encontrada na resposta")
            logger.debug(f"XML: {xml_resposta[:500]}")
            return 0
        
        logger.info(f"📦 Encontradas {len(notas)} NFS-e na resposta")
        
        # Processa cada nota
        from nfe_search import salvar_nfse_detalhada
        
        processadas = 0
        for i, nota_elem in enumerate(notas, 1):
            try:
                # Converte elemento para string
                xml_nota = etree.tostring(nota_elem, encoding='unicode')
                
                # Salva usando função especializada
                salvar_nfse_detalhada(xml_nota, nsu=f"SOAP_{i:06d}", informante=informante)
                processadas += 1
                logger.info(f"✅ NFS-e {i}/{len(notas)} processada")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar NFS-e {i}: {e}")
                continue
        
        return processadas
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar resposta: {e}")
        return 0


def buscar_nfse_soap_periodo(cnpj, inscricao_municipal, data_inicial, data_final, cert_path, senha, db):
    """
    Busca NFS-e via SOAP por período
    
    Args:
        cnpj: CNPJ do prestador
        inscricao_municipal: Inscrição municipal (opcional)
        data_inicial: Data inicial (YYYY-MM-DD)
        data_final: Data final (YYYY-MM-DD)
        cert_path: Caminho do certificado
        senha: Senha do certificado
        db: DatabaseManager
    
    Returns:
        int: Quantidade de notas baixadas
    """
    logger.info("="*80)
    logger.info("🔍 BUSCA NFS-e VIA SOAP MUNICIPAL")
    logger.info("="*80)
    logger.info(f"📅 Período: {data_inicial} → {data_final}")
    logger.info(f"🏢 CNPJ: {cnpj}")
    logger.info(f"📋 Inscrição: {inscricao_municipal or '(não informada)'}")
    
    # Detecta provedor
    provedor = detectar_provedor_mg(cnpj, db)
    logger.info(f"🔌 Provedor: {provedor['nome']}")
    logger.info(f"🌐 URL: {provedor['url_producao']}")
    
    # Constrói XML de consulta
    xml_consulta = construir_xml_consulta_periodo(
        cnpj, inscricao_municipal, data_inicial, data_final, provedor
    )
    
    logger.debug(f"📝 XML Consulta:\n{xml_consulta}")
    
    # Envia requisição SOAP
    xml_resposta = enviar_soap_consulta(
        provedor['url_producao'], xml_consulta, provedor, cert_path, senha
    )
    
    if not xml_resposta:
        logger.error("❌ Falha na consulta SOAP")
        return 0
    
    # Processa resposta
    qtd_processadas = processar_resposta_nfse(xml_resposta, db, cnpj)
    
    logger.info("="*80)
    logger.info(f"✅ BUSCA CONCLUÍDA: {qtd_processadas} NFS-e baixadas")
    logger.info("="*80)
    
    return qtd_processadas


# ==============================================================================
# MAIN - Exemplo de uso
# ==============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("NFS-e SOAP - Busca por Período (Minas Gerais)")
    print("="*80 + "\n")
    
    # Configurações
    CNPJ = "56237242000158"  # COOPSERVIÇOS
    INSCRICAO_MUNICIPAL = ""  # Deixe vazio se não souber
    DATA_INICIAL = "2025-01-01"
    DATA_FINAL = "2026-02-18"  # Hoje
    
    # Carrega certificado do banco
    db = DatabaseManager(Path(__file__).parent / "notas.db")
    
    # Busca certificado
    certs = db.get_certificados()
    cert_coopservicos = None
    
    for cert in certs:
        if CNPJ in cert[0]:  # cert[0] = cnpj_cpf
            cert_coopservicos = cert
            break
    
    if not cert_coopservicos:
        print(f"❌ Certificado COOPSERVIÇOS ({CNPJ}) não encontrado!")
        exit(1)
    
    cnpj, cert_path, senha, informante, cuf = cert_coopservicos
    
    print(f"📜 Certificado encontrado: {cert_path}")
    print(f"🔐 CNPJ: {cnpj}")
    print()
    
    # Confirma com usuário
    print("⚠️  Esta busca pode demorar dependendo da quantidade de notas.")
    print(f"📅 Buscando de {DATA_INICIAL} até {DATA_FINAL}")
    print()
    
    resposta = input("Deseja continuar? (S/N): ").strip().upper()
    
    if resposta != 'S':
        print("❌ Busca cancelada pelo usuário")
        exit(0)
    
    print()
    
    # Executa busca
    try:
        qtd = buscar_nfse_soap_periodo(
            cnpj=cnpj,
            inscricao_municipal=INSCRICAO_MUNICIPAL,
            data_inicial=DATA_INICIAL,
            data_final=DATA_FINAL,
            cert_path=cert_path,
            senha=senha,
            db=db
        )
        
        print(f"\n✅ Processo concluído: {qtd} NFS-e baixadas")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Busca interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro na busca: {e}")
        import traceback
        traceback.print_exc()
