# Bibliotecas padrão
import os
import gzip
import re
import base64
import logging
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Bibliotecas de terceiros
import requests
import requests_pkcs12
from requests.exceptions import RequestException
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.exceptions import Fault
from zeep.wsdl.utils import etree_to_string
from zeep.plugins import Plugin
from lxml import etree

# Módulos locais
try:
    from modules.download_completo import create_complete_downloader
except ImportError:
    create_complete_downloader = None
# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
def setup_logger():
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger

logger = setup_logger()
logger.debug("Iniciando nfe_search.py")

BASE = Path(__file__).parent
# -------------------------------------------------------------------
# Fluxo NSU
# -------------------------------------------------------------------
def ciclo_nsu(db, parser, intervalo=3600):
    """
    Executa o ciclo de busca de NSU para todos os certificados cadastrados.
    Faz busca periódica e salva notas detalhadas.
    Se ocorrer erro de conexão ou indisponibilidade da SEFAZ/internet,
    registra no log, aguarda alguns minutos e tenta novamente sem encerrar o processo.
    
    NOVA FUNCIONALIDADE: Detecta resumos (resNFe) e baixa automaticamente XMLs completos
    """
    XML_DIR = Path("xmls")
    while True:
        try:
            logger.info(f"Iniciando busca periódica de NSU em {datetime.now().isoformat()}")
            for cnpj, path, senha, inf, cuf in db.get_certificados():
                try:
                    svc = NFeService(path, senha, cnpj, cuf)
                    ult_nsu = db.get_last_nsu(inf)
                    logger.debug(f"Buscando notas a partir do NSU {ult_nsu} para {inf}")
                    
                    # Cria downloader de XMLs completos se disponível
                    complete_downloader = None
                    if create_complete_downloader:
                        complete_downloader = create_complete_downloader(svc, parser, db)
                    
                    while True:
                        try:
                            resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", ult_nsu)
                            if not resp:
                                logger.warning(f"Falha ao buscar NSU para {inf}")
                                break
                            cStat = parser.extract_cStat(resp)
                            if cStat == '656':  # Consumo indevido, bloqueio temporário
                                ult = parser.extract_last_nsu(resp)
                                if ult and ult != ult_nsu:
                                    db.set_last_nsu(inf, ult)
                                    logger.info(f"NSU atualizado após consumo indevido para {inf}: {ult}")
                                logger.warning(f"Consumo indevido, aguardando desbloqueio para {inf}")
                                break

                            docs = parser.extract_docs(resp)
                            if not docs:
                                logger.info(f"Nenhum novo docZip para {inf}")
                                break
                            for nsu, xml in docs:
                                try:
                                    # ========================================
                                    # NOVA FUNCIONALIDADE: Download XML Completo
                                    # Suporta: NFe, CTe e NFS-e
                                    # ========================================
                                    xml_final = xml  # Por padrão usa o XML original
                                    
                                    if complete_downloader and complete_downloader.should_download_complete(xml):
                                        doc_type = complete_downloader.get_document_type(xml)
                                        logger.info(f"Detectado resumo {doc_type.upper()} no NSU {nsu} - tentando baixar XML completo")
                                        xml_completo = complete_downloader.process_resumo_and_download_complete(xml, nsu, inf)
                                        if xml_completo:
                                            xml_final = xml_completo
                                            logger.info(f"✅ XML completo {doc_type.upper()} baixado com sucesso para NSU {nsu}")
                                        else:
                                            logger.warning(f"⚠️  Não foi possível baixar XML completo {doc_type.upper()} para NSU {nsu}, usando resumo")
                                    
                                    # Processa baseado no tipo de documento
                                    detected = None
                                    if complete_downloader:
                                        try:
                                            detected = complete_downloader.get_document_type(xml_final)
                                        except Exception:
                                            detected = None
                                    doc_type = detected or (parser.detect_doc_type(xml_final) if parser else 'nfe')
                                    doc_type_norm = (doc_type or '').lower()
                                    
                                    if doc_type_norm == 'nfe':
                                        # Processa NFe
                                        validar_xml_auto(xml_final, 'leiauteNFe_v4.00.xsd')
                                        tree = etree.fromstring(xml_final.encode('utf-8'))
                                        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                                        if infnfe is None:
                                            continue
                                        chave = infnfe.attrib.get('Id','')[-44:]
                                        db.registrar_xml(chave, cnpj)
                                    
                                    elif doc_type_norm == 'cte':
                                        # Processa CTe (validação tolerante, pois XSD pode não estar disponível)
                                        try:
                                            validar_xml_auto(xml_final, 'leiauteCTe_v3.00.xsd')
                                        except Exception:
                                            logger.debug("CT-e não validou no XSD; prosseguindo")
                                        tree = etree.fromstring(xml_final.encode('utf-8'))
                                        infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                                        if infcte is None:
                                            continue
                                        chave = infcte.attrib.get('Id','')[-44:]
                                        db.registrar_xml(chave, cnpj)
                                        
                                    elif doc_type_norm == 'nfse':
                                        # Processa NFS-e (tolerante)
                                        try:
                                            validar_xml_auto(xml_final, 'leiauteNFSe_v1.00.xsd')
                                        except Exception:
                                            logger.debug("NFS-e não validou no XSD; prosseguindo")
                                        tree = etree.fromstring(xml_final.encode('utf-8'))
                                        numero_elem = tree.find('.//{http://www.abrasf.org.br/nfse.xsd}Numero')
                                        numero = numero_elem.text if numero_elem is not None else ''
                                        chave = f"NFSE_{numero}" if numero else f"NFSE_{nsu}"
                                        db.registrar_xml(chave, cnpj)
                                        # Salva detalhamento mínimo para NFS-e
                                        db.criar_tabela_detalhada()
                                        nota_nfse = extrair_detalhe_nfse(xml_final, nsu)
                                        if nota_nfse:
                                            nota_nfse['xml_status'] = 'COMPLETO'
                                            nota_nfse['informante'] = inf
                                            nota_nfse['nsu'] = nsu
                                            db.salvar_nota_detalhada(nota_nfse)
                                    
                                    else:
                                        # Documento tipo desconhecido, tenta processar como NFe
                                        validar_xml_auto(xml_final, 'leiauteNFe_v4.00.xsd')
                                        tree = etree.fromstring(xml_final.encode('utf-8'))
                                        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                                        if infnfe is None:
                                            continue
                                        chave = infnfe.attrib.get('Id','')[-44:]
                                        db.registrar_xml(chave, cnpj)
                                    
                                    # Salva o XML final em disco (completo se conseguiu baixar)
                                    salvar_xml_por_certificado(xml_final, cnpj)
                                    # Salva nota detalhada (NFe e CTe)
                                    if doc_type_norm == 'nfe':
                                        db.criar_tabela_detalhada()
                                        nota = extrair_nota_detalhada(xml_final, parser, db, chave)
                                        db.salvar_nota_detalhada(nota)
                                    elif doc_type_norm == 'cte':
                                        db.criar_tabela_detalhada()
                                        nota_cte = extrair_detalhe_cte(xml_final, chave)
                                        db.salvar_nota_detalhada(nota_cte)
                                except Exception:
                                    logger.exception("Erro ao processar docZip")
                            ult = parser.extract_last_nsu(resp)
                            if ult and ult != ult_nsu:
                                db.set_last_nsu(inf, ult)
                                ult_nsu = ult
                            else:
                                break
                        except (requests.exceptions.RequestException, Fault, OSError) as e:
                            logger.warning(f"Erro de rede/SEFAZ para {inf}: {e}")
                            logger.info("Aguardando 3 minutos antes de tentar novamente este certificado...")
                            time.sleep(180)  # aguarda 3 minutos e tenta de novo o mesmo certificado
                            continue  # volta para o while interno
                except Exception as e:
                    logger.exception(f"Erro inesperado ao processar certificado {inf}: {e}")
                    continue  # vai para o próximo certificado

            # Após o ciclo, garante atualização das notas detalhadas a partir dos XMLs já salvos
            db.criar_tabela_detalhada()
            for xml_file in XML_DIR.rglob("*.xml"):
                try:
                    xml_txt = xml_file.read_text(encoding="utf-8")
                    chave = extrair_chave_nfe(xml_txt)
                    if chave:
                        nota = extrair_nota_detalhada(xml_txt, parser, db, chave)
                        db.salvar_nota_detalhada(nota)
                except Exception as e:
                    logger.warning(f"Falha ao extrair/atualizar nota detalhada de {xml_file}: {e}")

            logger.info(f"Busca de NSU finalizada. Dormindo por {intervalo/60:.0f} minutos...")

            time.sleep(intervalo)

        except Exception as e:
            logger.error(f"Erro geral no ciclo NSU: {e}")
            logger.info("Aguardando 5 minutos para reiniciar o ciclo...")
            time.sleep(300)  # espera 5 minutos antes de recomeçar o ciclo externo

# Função utilitária para extrair chave (44 dígitos) do XML
def extrair_chave_nfe(xml_txt):
    try:
        tree = etree.fromstring(xml_txt.encode("utf-8"))
        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        if infnfe is not None:
            return infnfe.attrib.get('Id', '')[-44:]
        return None
    except Exception:
        return None

# Função para montar o dict da nota detalhada a partir do XML
def extrair_nota_detalhada(xml_txt, parser, db, chave):
    try:
        tree = etree.fromstring(xml_txt.encode('utf-8'))
        inf = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        ide = inf.find('{http://www.portalfiscal.inf.br/nfe}ide') if inf is not None else None
        emit = inf.find('{http://www.portalfiscal.inf.br/nfe}emit') if inf is not None else None
        dest = inf.find('{http://www.portalfiscal.inf.br/nfe}dest') if inf is not None else None
        tot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}ICMSTot')

        cfop = ""
        if inf is not None:
            for det in inf.findall('{http://www.portalfiscal.inf.br/nfe}det'):
                prod = det.find('{http://www.portalfiscal.inf.br/nfe}prod')
                if prod is not None:
                    cfop = prod.findtext('{http://www.portalfiscal.inf.br/nfe}CFOP') or ""
                    if cfop:
                        break

        vencimento = ""
        if inf is not None:
            cobr = inf.find('{http://www.portalfiscal.inf.br/nfe}cobr')
            if cobr is not None:
                dup = cobr.find('.//{http://www.portalfiscal.inf.br/nfe}dup')
                if dup is not None:
                    vencimento = dup.findtext('{http://www.portalfiscal.inf.br/nfe}dVenc', "")

        valor = ""
        if tot is not None:
            vnf = tot.findtext('{http://www.portalfiscal.inf.br/nfe}vNF')
            valor = f"R$ {float(vnf):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vnf else ""

        # Busca status no banco (pode ser None)
        status_db = db.get_nf_status(chave)
        if status_db and status_db[0] and status_db[1]:
            status_str = f"{status_db[0]} – {status_db[1]}"
        else:
            status_str = "Autorizado o uso da NF-e"

        # CNPJ do destinatário
        cnpj_destinatario = dest.findtext('{http://www.portalfiscal.inf.br/nfe}CNPJ', "") if dest is not None else ""

        return {
            "chave": chave or "",
            "ie_tomador": dest.findtext('{http://www.portalfiscal.inf.br/nfe}IE') if dest is not None else "",
            "nome_emitente": emit.findtext('{http://www.portalfiscal.inf.br/nfe}xNome') if emit is not None else "",
            "cnpj_emitente": emit.findtext('{http://www.portalfiscal.inf.br/nfe}CNPJ') if emit is not None else "",
            "numero": ide.findtext('{http://www.portalfiscal.inf.br/nfe}nNF') if ide is not None else "",
            "data_emissao": (ide.findtext('{http://www.portalfiscal.inf.br/nfe}dhEmi')[:10]
                            if ide is not None and ide.findtext('{http://www.portalfiscal.inf.br/nfe}dhEmi')
                            else ""),
            "tipo": "NFe",
            "valor": valor,
            "cfop": cfop,
            "vencimento": vencimento,
            "uf": ide.findtext('{http://www.portalfiscal.inf.br/nfe}cUF') if ide is not None else "",
            "natureza": ide.findtext('{http://www.portalfiscal.inf.br/nfe}natOp') if ide is not None else "",
            "status": status_str,
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": cnpj_destinatario
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair dados da NF-e: {e}")
        return {
            "chave": chave or "",
            "ie_tomador": "",
            "nome_emitente": "",
            "cnpj_emitente": "",
            "numero": "",
            "data_emissao": "",
            "tipo": "NFe",
            "valor": "",
            "cfop": "",
            "vencimento": "",
            "uf": "",
            "natureza": "",
            "status": "Autorizado o uso da NF-e",
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": ""
        }
# -------------------------------------------------------------------
def extrair_detalhe_nfse(xml_txt, nsu: str | None = None):
    """Extrai campos principais da NFS-e (padrão ABRASF) para a tabela 'notas_detalhadas'.
    Usa namespace http://www.abrasf.org.br/nfse.xsd. Chave gerada como 'NFSE_<Numero>'.
    """
    try:
        ns = '{http://www.abrasf.org.br/nfse.xsd}'
        tree = etree.fromstring(xml_txt.encode('utf-8')) if isinstance(xml_txt, str) else xml_txt

        numero = tree.findtext(f'.//{ns}Numero') or ''
        data_emissao = tree.findtext(f'.//{ns}DataEmissao') or ''
        razao = tree.findtext(f'.//{ns}RazaoSocial') or ''
        # Alguns layouts usam PrestadorServico/IdentificacaoPrestador
        if not razao:
            razao = tree.findtext(f'.//{ns}PrestadorServico//{ns}RazaoSocial') or ''

        cnpj_emit = tree.findtext(f'.//{ns}Cnpj') or ''
        if not cnpj_emit:
            cnpj_emit = tree.findtext(f'.//{ns}Prestador//{ns}Cnpj') or ''

        valor_serv = tree.findtext(f'.//{ns}ValorServicos') or ''
        valor = f"R$ {float(valor_serv):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if valor_serv else ''

        chave = f"NFSE_{numero}" if numero else (f"NFSE_{nsu}" if nsu else "NFSE")

        return {
            'chave': chave,
            'ie_tomador': '',
            'nome_emitente': razao,
            'cnpj_emitente': cnpj_emit,
            'numero': numero,
            'data_emissao': data_emissao[:10] if data_emissao else '',
            'tipo': 'NFS-e',
            'valor': valor,
            'cfop': '',
            'vencimento': '',
            'uf': '',
            'natureza': '',
            'status': 'Autorizado',
            'atualizado_em': datetime.now().isoformat(),
            'cnpj_destinatario': ''
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair dados da NFS-e: {e}")
        return None
# Função para montar o dict do CT-e a partir do XML (mínimo viável)
def extrair_detalhe_cte(xml_txt, chave: str):
    """Extrai campos principais do CT-e para a tabela 'notas_detalhadas'.
    Campos considerados: chave, numero (nCT), data_emissao (dhEmi), emitente (CNPJ/xNome),
    valor (vTPrest), tipo='CTe', uf (cUF), status padrão, atualizado_em.
    """
    try:
        ns = '{http://www.portalfiscal.inf.br/cte}'
        tree = etree.fromstring(xml_txt.encode('utf-8')) if isinstance(xml_txt, str) else xml_txt

        # Aceita root em CTe ou procCTe
        ide = tree.find(f'.//{ns}ide')
        emit = tree.find(f'.//{ns}emit')
        vprest = tree.find(f'.//{ns}vPrest')

        numero = ide.findtext(f'{ns}nCT') if ide is not None else ''
        dhEmi = ide.findtext(f'{ns}dhEmi') if ide is not None else ''
        cUF = ide.findtext(f'{ns}cUF') if ide is not None else ''
        xNome = emit.findtext(f'{ns}xNome') if emit is not None else ''
        cnpj_emit = emit.findtext(f'{ns}CNPJ') if emit is not None else ''

        # Valor total: vTPrest
        vTPrest = ''
        if vprest is not None:
            vTPrest = vprest.findtext(f'{ns}vTPrest') or ''
        valor = f"R$ {float(vTPrest):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vTPrest else ''

        return {
            'chave': chave or '',
            'ie_tomador': '',
            'nome_emitente': xNome,
            'cnpj_emitente': cnpj_emit,
            'numero': numero,
            'data_emissao': dhEmi[:10] if dhEmi else '',
            'tipo': 'CTe',
            'valor': valor,
            'cfop': '',
            'vencimento': '',
            'uf': cUF or '',
            'natureza': '',
            'status': 'Autorizado',
            'atualizado_em': datetime.now().isoformat(),
            'cnpj_destinatario': ''
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair dados do CT-e: {e}")
        return {
            'chave': chave or '',
            'ie_tomador': '',
            'nome_emitente': '',
            'cnpj_emitente': '',
            'numero': '',
            'data_emissao': '',
            'tipo': 'CTe',
            'valor': '',
            'cfop': '',
            'vencimento': '',
            'uf': '',
            'natureza': '',
            'status': 'Autorizado',
            'atualizado_em': datetime.now().isoformat(),
            'cnpj_destinatario': ''
        }
    
# -------------------------------------------------------------------
# Salvar XML na pasta
# -------------------------------------------------------------------
def sanitize_filename(s: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos/pastas."""
    return re.sub(r'[\\/*?:"<>|]', "_", s).strip()

def format_cnpj_cpf_dir(doc: str) -> str:
    """
    Retorna apenas os dígitos do CNPJ ou CPF para uso seguro em nomes de pastas.
    Exemplo:
        '47.539.664/0001-97'  --> '47539664000197'
        '123.456.789-01'      --> '12345678901'
        '47539664000197'      --> '47539664000197'
    """
    return ''.join(filter(str.isdigit, doc or ""))

def salvar_xml_por_certificado(xml, cnpj_cpf, pasta_base="xmls"):
    """
    Salva o XML em uma pasta separada por certificado, tipo de documento e ano-mês de emissão.
    Exemplos: 
    - xmls/47539664000197/NFe/2025-08/00123-EMPRESA.xml
    - xmls/47539664000197/CTe/2025-08/00456-TRANSPORTADORA.xml
    - xmls/47539664000197/NFS-e/2025-08/00789-PRESTADOR.xml
    """
    import os
    from lxml import etree
    import re

    def sanitize_filename(s: str) -> str:
        """Remove caracteres inválidos para nomes de arquivos/pastas."""
        return re.sub(r'[\\/*?:"<>|]', "_", s or "").strip()

    def detect_document_type(xml_root):
        """Detecta o tipo de documento fiscal baseado na tag raiz e namespaces"""
        root_tag = xml_root.tag
        
        # Remove namespace se presente
        if '}' in root_tag:
            namespace, tag_name = root_tag.split('}', 1)
            namespace = namespace[1:]  # Remove o '{'
        else:
            tag_name = root_tag
            namespace = ""
        
        # Normaliza tag para lowercase
        tag_lower = tag_name.lower()
        
        # Detecta tipo baseado na tag raiz
        if any(x in tag_lower for x in ['nfe', 'resnfe', 'procnfe']):
            return 'NFe'
        elif any(x in tag_lower for x in ['cte', 'rescte', 'proccte']):
            return 'CTe'  
        elif any(x in tag_lower for x in ['nfse', 'resnfse', 'procnfse']):
            return 'NFS-e'
        
        # Detecta por namespace se tag não foi conclusiva
        if 'nfe' in namespace:
            return 'NFe'
        elif 'cte' in namespace:
            return 'CTe'
        elif 'nfse' in namespace or 'abrasf' in namespace:
            return 'NFS-e'
            
        # Default para NFe se não conseguir detectar
        return 'NFe'

    def extract_document_data(xml_root, doc_type):
        """Extrai dados específicos baseado no tipo de documento"""
        if doc_type == 'NFe':
            # NFe - busca em namespace NFe
            ide = xml_root.find('.//{http://www.portalfiscal.inf.br/nfe}ide')
            if ide is not None:
                dEmi = ide.findtext('{http://www.portalfiscal.inf.br/nfe}dEmi')
                dhEmi = ide.findtext('{http://www.portalfiscal.inf.br/nfe}dhEmi')
                nNF = ide.findtext('{http://www.portalfiscal.inf.br/nfe}nNF') or "SEM_NUMERO"
                
                emit = xml_root.find('.//{http://www.portalfiscal.inf.br/nfe}emit')
                xNome = emit.findtext('{http://www.portalfiscal.inf.br/nfe}xNome') if emit is not None else "SEM_NOME"
                
                return dEmi or dhEmi, nNF, xNome
                
        elif doc_type == 'CTe':
            # CTe - busca em namespace CTe
            ide = xml_root.find('.//{http://www.portalfiscal.inf.br/cte}ide')
            if ide is not None:
                dhEmi = ide.findtext('{http://www.portalfiscal.inf.br/cte}dhEmi')
                nCT = ide.findtext('{http://www.portalfiscal.inf.br/cte}nCT') or "SEM_NUMERO"
                
                emit = xml_root.find('.//{http://www.portalfiscal.inf.br/cte}emit')
                xNome = emit.findtext('{http://www.portalfiscal.inf.br/cte}xNome') if emit is not None else "SEM_NOME"
                
                return dhEmi, f"CTE-{nCT}", xNome
                
        elif doc_type == 'NFS-e':
            # NFS-e - busca em namespace NFS-e (padrão nacional)
            # Tenta diferentes estruturas de NFS-e
            numero_elem = xml_root.find('.//{http://www.abrasf.org.br/nfse.xsd}Numero')
            data_elem = xml_root.find('.//{http://www.abrasf.org.br/nfse.xsd}DataEmissao')
            prestador_elem = xml_root.find('.//{http://www.abrasf.org.br/nfse.xsd}RazaoSocial')
            
            numero = numero_elem.text if numero_elem is not None else "SEM_NUMERO"
            data_emissao = data_elem.text if data_elem is not None else None
            nome_prestador = prestador_elem.text if prestador_elem is not None else "SEM_NOME"
            
            return data_emissao, f"NFSE-{numero}", nome_prestador
            
        # Fallback genérico
        return None, "SEM_NUMERO", "SEM_NOME"

    try:
        cnpj_cpf_fmt = format_cnpj_cpf_dir(cnpj_cpf)

        # Parse o XML para extrair dados
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        
        # Detecta tipo de documento
        doc_type = detect_document_type(root)
        
        # Extrai dados específicos do tipo
        data_raw, numero, nome = extract_document_data(root, doc_type)
        
        # Processa data de emissão
        if data_raw:
            data_part = data_raw.split("T")[0]
            ano_mes = data_part[:7] if len(data_part) >= 7 else "SEM_DATA"
        else:
            ano_mes = "SEM_DATA"

        # Monta estrutura de pastas: pasta_base/CNPJ/TIPO/ANO-MES/
        pasta_dest = os.path.join(pasta_base, cnpj_cpf_fmt, doc_type, ano_mes)
        os.makedirs(pasta_dest, exist_ok=True)

        # Nome do arquivo com prefixo do tipo
        nome_arquivo = f"{sanitize_filename(numero)}-{sanitize_filename(nome)[:40]}.xml"
        caminho_xml = os.path.join(pasta_dest, nome_arquivo)

        with open(caminho_xml, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[SALVO {doc_type}] {caminho_xml}")
        return caminho_xml
        
    except Exception as e:
        print(f"[ERRO ao salvar XML de {cnpj_cpf}]: {e}")
        return None
# -------------------------------------------------------------------
# Validação de XML com XSD
# -------------------------------------------------------------------
def validar_xml_auto(xml, default_xsd):
    # Mostra XML para debug
    print("\n--- XML sendo validado ---\n", xml, "\n-------------------------\n")

    # Mapeamento padrão
    ROOT_XSD_MAP = {
        # NFe
        "nfeProc":      "procNFe_v4.00.xsd",
        "NFe":          "leiauteNFe_v4.00.xsd",
        "procEventoNFe":"procEventoNFe_v1.00.xsd",
        "resNFe":       "resNFe_v1.01.xsd",
        "resEvento":    "resEvento_v1.01.xsd",
        # CTe
        "procCTe":      "procCTe_v3.00.xsd",
        "CTe":          "leiauteCTe_v3.00.xsd",
        "resCTe":       "resCTe_v1.04.xsd",
        # NFS-e
        "procNFSe":     "procNFSe_v1.00.xsd",
        "NFSe":         "leiauteNFSe_v1.00.xsd",
        "resNFSe":      "resNFSe_v1.00.xsd",
        # Outros
        "retConsReciNFe":"retConsReciNFe_v4.00.xsd",
        "enviNFe":      "enviNFe_v4.00.xsd",
        "distDFeInt":   "distDFeInt_v1.01.xsd",
        "inutNFe":      "inutNFe_v4.00.xsd",
        "procInutNFe":  "procInutNFe_v4.00.xsd",
        # Outros se necessário
    }
    # Descobre tag raiz
    try:
        tree = etree.fromstring(xml.encode('utf-8') if isinstance(xml, str) else xml)
        root_tag = tree.tag
        if '}' in root_tag:
            root_tag = root_tag.split('}', 1)[1]
    except Exception as e:
        raise Exception(f"Erro ao fazer parse do XML: {e}")

    # ATENÇÃO: Pule validação de eventos (resEvento, procEventoNFe etc)
    if root_tag.lower() in {"proceventonfe", "resevento", "receventonfe"}:
        print(f"[DEBUG] PULANDO validação XSD para {root_tag} (problema conhecido com XSD de eventos SEFAZ)")
        return True

    # Descobre nome do XSD correto
    xsd_file = ROOT_XSD_MAP.get(root_tag, default_xsd)

    # Busca o XSD no projeto (recursivo)
    def find_xsd(xsd_name, base_dir=None):
        from pathlib import Path
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = Path(base_dir)
        for p in base_dir.rglob(xsd_name):
            if p.exists():
                print(f"[XSD] Encontrado: {p}")
                return str(p)
        print(f"[XSD] NÃO encontrado: {xsd_name} em {base_dir}")
        return None

    xsd_path = find_xsd(xsd_file)
    if not xsd_path:
        raise FileNotFoundError(f"Arquivo XSD não encontrado: {xsd_file} (procure inclusive em subpastas)")

    # PREVENÇÃO: Muda para pasta do XSD antes de validar (corrige problemas de includes)
    xsd_dir = os.path.dirname(xsd_path)
    cwd = os.getcwd()
    try:
        os.chdir(xsd_dir)
        # Usa só o nome do arquivo pois está na pasta
        with open(os.path.basename(xsd_path), 'rb') as f:
            schema_root = etree.XML(f.read())
        schema = etree.XMLSchema(schema_root)
        if not schema.validate(tree):
            errors = "\n".join([str(e) for e in schema.error_log])
            raise Exception(f"Erro ao validar XML com XSD {xsd_file}:\n{errors}")
    except etree.XMLSchemaParseError as e:
        raise Exception(f"[DEBUG] Falha ao validar XML (parse XSD): {e}")
    except etree.XMLSyntaxError as e:
        raise Exception(f"[DEBUG] Falha ao validar XML (syntax XSD): {e}")
    except Exception as e:
        raise Exception(f"[DEBUG] Falha ao validar XML: {e}")
    finally:
        os.chdir(cwd)
    return True
# -------------------------------------------------------------------
# URLs dos serviços
# -------------------------------------------------------------------
URL_DISTRIBUICAO = (
    "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/"
    "NFeDistribuicaoDFe.asmx?wsdl"
)
CONSULTA_WSDL = {
    '50': "https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4?wsdl",  # MS
    # ... os demais já estavam no seu dicionário, mas só MS interessa aqui.
}
URL_CONSULTA_FALLBACK = (
    "https://www1.nfe.fazenda.gov.br/NFeConsultaProtocolo/"
    "NFeConsultaProtocolo.asmx?wsdl"
)

# -------------------------------------------------------------------
# Rate Limiting para SEFAZ
# -------------------------------------------------------------------
class SEFAZRateLimiter:
    """
    Gerencia limites de taxa da SEFAZ para evitar bloqueios.
    
    Limites conhecidos:
    - Consulta de Protocolo: ~60-120 por minuto por certificado
    - Distribuição NSU: ~300-500 por hora
    """
    
    def __init__(self):
        # Rastreia consultas por certificado
        self.protocol_queries = defaultdict(list)  # {cnpj: [timestamps]}
        self.nsu_queries = defaultdict(list)       # {cnpj: [timestamps]}
        
        # Limites configuráveis
        self.PROTOCOL_LIMIT_PER_MINUTE = 50  # Conservador para evitar bloqueio
        self.NSU_LIMIT_PER_HOUR = 400
        self.PROTOCOL_COOLDOWN = 1.2  # Segundos entre consultas de protocolo
        self.NSU_COOLDOWN = 8.0       # Segundos entre consultas NSU
        
        logger.info(f"Rate Limiter iniciado - Protocolo: {self.PROTOCOL_LIMIT_PER_MINUTE}/min, NSU: {self.NSU_LIMIT_PER_HOUR}/hora")
    
    def can_query_protocol(self, cnpj: str) -> bool:
        """Verifica se pode fazer consulta de protocolo."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Remove consultas antigas
        self.protocol_queries[cnpj] = [
            ts for ts in self.protocol_queries[cnpj] if ts > minute_ago
        ]
        
        # Verifica limite
        can_query = len(self.protocol_queries[cnpj]) < self.PROTOCOL_LIMIT_PER_MINUTE
        if not can_query:
            logger.warning(f"Rate limit atingido para protocolo CNPJ {cnpj}: {len(self.protocol_queries[cnpj])}/{self.PROTOCOL_LIMIT_PER_MINUTE}")
        
        return can_query
    
    def can_query_nsu(self, cnpj: str) -> bool:
        """Verifica se pode fazer consulta NSU."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Remove consultas antigas
        self.nsu_queries[cnpj] = [
            ts for ts in self.nsu_queries[cnpj] if ts > hour_ago
        ]
        
        # Verifica limite
        can_query = len(self.nsu_queries[cnpj]) < self.NSU_LIMIT_PER_HOUR
        if not can_query:
            logger.warning(f"Rate limit atingido para NSU CNPJ {cnpj}: {len(self.nsu_queries[cnpj])}/{self.NSU_LIMIT_PER_HOUR}")
        
        return can_query
    
    def record_protocol_query(self, cnpj: str):
        """Registra uma consulta de protocolo."""
        self.protocol_queries[cnpj].append(datetime.now())
        time.sleep(self.PROTOCOL_COOLDOWN)  # Cooldown entre consultas
    
    def record_nsu_query(self, cnpj: str):
        """Registra uma consulta NSU."""
        self.nsu_queries[cnpj].append(datetime.now())
        time.sleep(self.NSU_COOLDOWN)  # Cooldown entre consultas
    
    def wait_if_needed(self, cnpj: str, query_type: str = "protocol") -> bool:
        """
        Espera se necessário para respeitar rate limits.
        Retorna False se deve pular este certificado temporariamente.
        """
        if query_type == "protocol":
            if not self.can_query_protocol(cnpj):
                logger.info(f"Aguardando rate limit para protocolo CNPJ {cnpj}...")
                time.sleep(60)  # Espera 1 minuto
                return self.can_query_protocol(cnpj)
        else:  # NSU
            if not self.can_query_nsu(cnpj):
                logger.info(f"Aguardando rate limit para NSU CNPJ {cnpj}...")
                time.sleep(600)  # Espera 10 minutos
                return self.can_query_nsu(cnpj)
        
        return True
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de uso."""
        now = datetime.now()
        stats = {}
        
        for cnpj in set(list(self.protocol_queries.keys()) + list(self.nsu_queries.keys())):
            # Consultas de protocolo na última hora
            hour_ago = now - timedelta(hours=1)
            protocol_last_hour = len([
                ts for ts in self.protocol_queries[cnpj] if ts > hour_ago
            ])
            
            # Consultas NSU na última hora
            nsu_last_hour = len([
                ts for ts in self.nsu_queries[cnpj] if ts > hour_ago
            ])
            
            stats[cnpj] = {
                'protocol_last_hour': protocol_last_hour,
                'nsu_last_hour': nsu_last_hour,
                'total_protocol': len(self.protocol_queries[cnpj]),
                'total_nsu': len(self.nsu_queries[cnpj])
            }
        
        return stats

# -------------------------------------------------------------------
# Banco de Dados
# -------------------------------------------------------------------
class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._initialize()
        logger.debug(f"Banco inicializado em {db_path}")

    def get_nf_status(self, chave):
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT cStat, xMotivo FROM nf_status WHERE chNFe = ?", (chave,)
            )
            return cur.fetchone()

    def extrair_dados_nfe(xml_str, db):
        """
        Extrai dados relevantes do XML da NF-e para a tabela detalhada.
        """
        try:
            tree = etree.fromstring(xml_str.encode("utf-8") if isinstance(xml_str, str) else xml_str)
            inf = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
            if inf is None:
                return None
            ide  = inf.find('{http://www.portalfiscal.inf.br/nfe}ide')
            emit = inf.find('{http://www.portalfiscal.inf.br/nfe}emit')
            dest = inf.find('{http://www.portalfiscal.inf.br/nfe}dest')
            tot  = inf.find('.//{http://www.portalfiscal.inf.br/nfe}ICMSTot')
            valor = tot.findtext('{http://www.portalfiscal.inf.br/nfe}vNF') if tot is not None else ''

            chave = inf.attrib.get('Id','')[-44:]
            ie_tomador = dest.findtext('{http://www.portalfiscal.inf.br/nfe}IE') if dest is not None else ''
            nome_emitente = emit.findtext('{http://www.portalfiscal.inf.br/nfe}xNome') if emit is not None else ''
            cnpj_emitente = emit.findtext('{http://www.portalfiscal.inf.br/nfe}CNPJ') if emit is not None else ''
            numero = ide.findtext('{http://www.portalfiscal.inf.br/nfe}nNF') if ide is not None else ''
            data_emissao = ide.findtext('{http://www.portalfiscal.inf.br/nfe}dhEmi') or \
                ide.findtext('{http://www.portalfiscal.inf.br/nfe}dEmi') if ide is not None else ''
            tipo = 'NFe'
            uf = ide.findtext('{http://www.portalfiscal.inf.br/nfe}cUF') if ide is not None else ''
            natureza = ide.findtext('{http://www.portalfiscal.inf.br/nfe}natOp') if ide is not None else ''
            # Busca status se existir no banco
            stat = db.get_nf_status(chave)
            status = f"{stat[0]} – {stat[1]}" if stat else "—"

            return {
                "chave": chave,
                "ie_tomador": ie_tomador,
                "nome_emitente": nome_emitente,
                "cnpj_emitente": cnpj_emitente,
                "numero": numero,
                "data_emissao": data_emissao,
                "tipo": tipo,
                "valor": valor,
                "uf": uf,
                "natureza": natureza,
                "status": status,
                "atualizado_em": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERRO extrair_dados_nfe] {e}")
            return None

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS certificados (
                id INTEGER PRIMARY KEY,
                cnpj_cpf TEXT,
                caminho TEXT,
                senha TEXT,
                informante TEXT,
                cUF_autor TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS xmls_baixados (
                chave TEXT PRIMARY KEY,
                cnpj_cpf TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nf_status (
                chNFe TEXT PRIMARY KEY,
                cStat TEXT,
                xMotivo TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS nsu (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            conn.commit()
            logger.debug("Tabelas verificadas/criadas no banco")
    
    def criar_tabela_detalhada(self):
        with self._connect() as conn:
            # Cria a tabela com o campo cnpj_destinatario, se ainda não existir
            conn.execute('''
            CREATE TABLE IF NOT EXISTS notas_detalhadas (
                chave TEXT PRIMARY KEY,
                ie_tomador TEXT,
                nome_emitente TEXT,
                cnpj_emitente TEXT,
                numero TEXT,
                data_emissao TEXT,
                tipo TEXT,
                valor TEXT,
                cfop TEXT,
                vencimento TEXT,
                uf TEXT,
                natureza TEXT,
                status TEXT DEFAULT 'Autorizado o uso da NF-e',
                xml_status TEXT DEFAULT 'RESUMO', -- RESUMO | COMPLETO
                informante TEXT,
                nsu TEXT,
                atualizado_em DATETIME,
                cnpj_destinatario TEXT
            )
            ''')
            # Garante que a coluna cnpj_destinatario existe (caso o banco seja antigo)
            try:
                conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN cnpj_destinatario TEXT;")
            except sqlite3.OperationalError:
                # Já existe, ignora o erro
                pass
            # Migrações leves para novas colunas
            try:
                conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN xml_status TEXT DEFAULT 'RESUMO';")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN informante TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE notas_detalhadas ADD COLUMN nsu TEXT;")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    def salvar_nota_detalhada(self, nota):
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO notas_detalhadas (
                    chave, ie_tomador, nome_emitente, cnpj_emitente, numero,
                    data_emissao, tipo, valor, cfop, vencimento, uf, natureza,
                    status, xml_status, informante, nsu, atualizado_em, cnpj_destinatario
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nota['chave'], nota['ie_tomador'], nota['nome_emitente'], nota['cnpj_emitente'],
                nota['numero'], nota['data_emissao'], nota['tipo'], nota['valor'],
                nota.get('cfop', ''), nota.get('vencimento', ''), nota.get('uf', ''),
                nota.get('natureza', ''), nota['status'], nota.get('xml_status','RESUMO'),
                nota.get('informante',''), nota.get('nsu',''), nota['atualizado_em'],
                nota.get('cnpj_destinatario', '')
            ))
            conn.commit()

    def get_certificados(self):
        # TEMPORÁRIO: Forçar uso da tabela legada para carregar todos os certificados
        logger.debug("Forçando uso da tabela legada para carregar todos os certificados")
        
        with self._connect() as conn:
            # Usa diretamente a tabela antiga para garantir que todos os certificados sejam carregados
            rows = conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()
            logger.debug(f"Certificados carregados da tabela legada: {len(rows)} certificados")
            
            # Log detalhado dos certificados carregados
            for i, cert in enumerate(rows, 1):
                cnpj, caminho, senha, inf, cuf = cert
                logger.debug(f"Certificado {i}: CNPJ={cnpj}, Informante={inf}, UF={cuf}, Caminho={caminho}")
            
            return rows

    def get_last_nsu(self, informante):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)
            ).fetchone()
            last = row[0] if row else "000000000000000"
            logger.debug(f"Último NSU para {informante}: {last}")
            return last

    def set_last_nsu(self, informante, nsu):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU atualizado para {informante}: {nsu}")

    def registrar_xml(self, chave, cnpj):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
                (chave, cnpj)
            )
            conn.commit()
            logger.debug(f"XML registrado: {chave} (CNPJ {cnpj})")

    def get_chaves_missing_status(self):
        with self._connect() as conn:
            rows = conn.execute('''
                SELECT x.chave, x.cnpj_cpf
                FROM xmls_baixados x
                LEFT JOIN nf_status n
                ON x.chave = n.chNFe
                WHERE n.chNFe IS NULL
            ''').fetchall()
            logger.debug(f"Chaves sem status: {rows}")
            return rows

    def set_nf_status(self, chave, cStat, xMotivo):
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nf_status (chNFe,cStat,xMotivo) VALUES (?,?,?)",
                (chave, cStat, xMotivo)
            )
            conn.commit()
            logger.debug(f"Status gravado: {chave} → {cStat} / {xMotivo}")

    def marcar_para_download(self, chave, cnpj):
        """Marca um documento para download posterior na busca normal"""
        with self._connect() as conn:
            # Cria tabela se não existir
            conn.execute('''
                CREATE TABLE IF NOT EXISTS download_pendente (
                    chave TEXT PRIMARY KEY,
                    cnpj TEXT,
                    data_marcacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processado INTEGER DEFAULT 0
                )
            ''')
            
            # Insere ou atualiza a marcação
            conn.execute(
                "INSERT OR REPLACE INTO download_pendente (chave, cnpj, processado) VALUES (?, ?, 0)",
                (chave, cnpj)
            )
            conn.commit()
            logger.debug(f"Documento marcado para download: {chave} (CNPJ: {cnpj})")

    def get_pendentes_download(self, cnpj=None):
        """Retorna documentos marcados para download"""
        with self._connect() as conn:
            if cnpj:
                cursor = conn.execute(
                    "SELECT chave, cnpj FROM download_pendente WHERE cnpj = ? AND processado = 0",
                    (cnpj,)
                )
            else:
                cursor = conn.execute(
                    "SELECT chave, cnpj FROM download_pendente WHERE processado = 0"
                )
            return cursor.fetchall()

    def marcar_como_processado(self, chave):
        """Marca um documento como processado"""
        with self._connect() as conn:
            conn.execute(
                "UPDATE download_pendente SET processado = 1 WHERE chave = ?",
                (chave,)
            )
            conn.commit()

    def find_cert_by_cnpj(self, cnpj):
        for row in self.get_certificados():
            if row[0] == cnpj:
                return row
        return None

# -------------------------------------------------------------------
# Processador de XML
# -------------------------------------------------------------------
class XMLProcessor:
    NS = {'nfe':'http://www.portalfiscal.inf.br/nfe'}

    def extract_docs(self, resp_xml):
        logger.debug("Extraindo docs de distribuição")
        docs = []
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        for dz in tree.findall('.//nfe:docZip', namespaces=self.NS):
            data = base64.b64decode(dz.text or '')
            xml  = gzip.decompress(data).decode('utf-8')
            nsu  = dz.get('NSU','')
            docs.append((nsu, xml))
        logger.debug(f"{len(docs)} documentos extraídos")
        return docs

    def extract_last_nsu(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        ult = tree.find('.//nfe:ultNSU', namespaces=self.NS)
        last = ult.text.zfill(15) if ult is not None and ult.text else None
        logger.debug(f"último NSU extraído: {last}")
        return last

    def extract_cStat(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        cs = tree.find('.//nfe:cStat', namespaces=self.NS)
        stat = cs.text if cs is not None else None
        logger.debug(f"cStat extraído: {stat}")
        return stat

    def parse_protNFe(self, xml_obj):
        logger.debug("Parseando protocolo NF-e")
        
        # Verifica se é a mensagem especial de erro 404
        if isinstance(xml_obj, str) and '<erro_404>' in xml_obj:
            logger.debug("Detectado erro 404 especial na resposta")
            return '', '404', 'Erro 404: Uso de prefixo de namespace nao permitido'
        
        # Se já for Element, use direto
        if isinstance(xml_obj, etree._Element):
            tree = xml_obj
        else:
            tree = etree.fromstring(xml_obj.encode('utf-8'))
            
        # Primeiro verifica se há erro na própria consulta (retConsSitNFe)
        # Pode estar como root ou como filho
        ret_cons = tree.find('.//{http://www.portalfiscal.inf.br/nfe}retConsSitNFe')
        
        # Se não encontrou como filho, verifica se o próprio root é retConsSitNFe
        if ret_cons is None and tree.tag.endswith('retConsSitNFe'):
            ret_cons = tree
            
        if ret_cons is not None:
            cStat = ret_cons.findtext('.//{http://www.portalfiscal.inf.br/nfe}cStat') or ''
            xMotivo = ret_cons.findtext('.//{http://www.portalfiscal.inf.br/nfe}xMotivo') or ''
            
            # Se erro 404 (namespace), trata como erro de consulta
            if cStat == '404':
                logger.warning(f"Erro 404 na consulta: {xMotivo}")
                # Retorna dados com erro 404 para ser tratado especificamente
                return '', '404', xMotivo
                
        prot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}protNFe')
        if prot is None:
            logger.debug("nenhum protNFe encontrado")
            return None, None, None
        chNFe   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}chNFe') or ''
        cStat   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}cStat') or ''
        xMotivo = prot.findtext('{http://www.portalfiscal.inf.br/nfe}xMotivo') or ''
        logger.debug(f"Parse protocolo → chNFe={chNFe}, cStat={cStat}, xMotivo={xMotivo}")
        return chNFe, cStat, xMotivo

    def detect_doc_type(self, xml_str: str) -> str:
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
            tag = etree.QName(root).localname.lower()
            # NFe tipos
            if 'resnfe' in tag:
                return 'resNFe'
            if 'procnfe' in tag or 'nfeproc' in tag:
                return 'nfeProc'
            if tag == 'nfe':
                return 'NFe'
            # CTe tipos
            if 'rescte' in tag:
                return 'resCTe'
            if 'proccte' in tag:
                return 'procCTe'
            if tag == 'cte':
                return 'CTe'
            # NFSe tipos (ABRASF)
            if 'procnfse' in tag:
                return 'procNFSe'
            if 'resnfse' in tag:
                return 'resNFSe'
            if 'nfse' in tag and tag != 'nfe':
                return 'NFSe'
            return tag
        except Exception:
            return 'unknown'

    def extrair_dados_resnfe(self, xml_str: str):
        """Extrai dados básicos de um resNFe para popular tabela"""
        try:
            tree = etree.fromstring(xml_str.encode('utf-8'))
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            chave = tree.findtext(f'.//{ns}chNFe') or ''
            cnpj_emit = tree.findtext(f'.//{ns}CNPJ') or ''
            xNome = tree.findtext(f'.//{ns}xNome') or ''
            dEmi = tree.findtext(f'.//{ns}dEmi') or ''
            vNF = tree.findtext(f'.//{ns}vNF') or ''
            cUF = tree.findtext(f'.//{ns}cUF') or ''
            return {
                'chave': chave,
                'ie_tomador': '',
                'nome_emitente': xNome,
                'cnpj_emitente': cnpj_emit,
                'numero': '',
                'data_emissao': dEmi,
                'tipo': 'NFe',
                'valor': vNF,
                'uf': cUF,
                'natureza': '',
                'status': 'Resumo',
                'atualizado_em': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro ao extrair resNFe: {e}")
            return None

# -------------------------------------------------------------------
# Serviço SOAP
# -------------------------------------------------------------------
class NFeService:
    # Rate limiter compartilhado entre todas as instâncias
    _rate_limiter = None
    
    def __init__(self, cert_path, senha, informante, cuf):
        logger.debug(f"Inicializando serviço para informante={informante}, cUF={cuf}")
        
        # Inicializa rate limiter se necessário
        if NFeService._rate_limiter is None:
            NFeService._rate_limiter = SEFAZRateLimiter()
        
        # Configurar sessão com certificado e SSL
        sess = requests.Session()
        
        # Desabilitar verificação SSL para contornar problemas com certificados SEFAZ
        sess.verify = False
        
        # Configurar timeouts mais agressivos
        sess.timeout = (30, 60)  # (connect timeout, read timeout)
        
        # Configurar certificado
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        
        # Desabilitar avisos de SSL não verificado
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configurar transport com timeouts personalizados
        trans = Transport(session=sess, timeout=30, operation_timeout=60)
        self._session = sess
        
        # Configurar Settings do zeep para evitar prefixos de namespace
        # strict=False permite mais flexibilidade
        # xsd_ignore_sequence_order=True para ordem flexível de elementos
        zeep_settings = Settings(
            strict=False,
            xml_huge_tree=True,
            xsd_ignore_sequence_order=True
        )
        
        # Inicializar cliente de distribuição com tratamento de exceções
        try:
            self.dist_client = Client(
                wsdl=URL_DISTRIBUICAO, 
                transport=trans,
                settings=zeep_settings
            )
            logger.debug(f"Cliente de distribuição inicializado: {URL_DISTRIBUICAO}")
        except Exception as e:
            logger.error(f"Falha crítica ao inicializar cliente de distribuição: {e}")
            self.dist_client = None
        
        # Inicializar cliente de consulta (protocolo) com tratamento de exceções
        wsdl = CONSULTA_WSDL.get(str(cuf), URL_CONSULTA_FALLBACK)
        try:
            self.cons_client = Client(
                wsdl=wsdl, 
                transport=trans,
                settings=zeep_settings
            )
            logger.debug(f"Cliente de protocolo inicializado: {wsdl}")
        except Exception as e:
            self.cons_client = None
            logger.warning(f"Falha ao inicializar WSDL de protocolo ({wsdl}): {e}")
            
        self.informante = informante
        self.cuf        = cuf
        # Endpoint real do serviço de protocolo (sem ?wsdl)
        try:
            self.cons_endpoint = wsdl.split('?')[0]
        except Exception:
            self.cons_endpoint = wsdl

    def fetch_by_cnpj(self, tipo, ult_nsu):
        logger.debug(f"Chamando distribuição: tipo={tipo}, informante={self.informante}, ultNSU={ult_nsu}")
        
        # Verificar se cliente de distribuição está disponível
        if not self.dist_client:
            logger.error("Cliente de distribuição não disponível")
            return None
        
        # Aplicar rate limiting para NSU
        if not self._rate_limiter.wait_if_needed(self.informante, "nsu"):
            logger.warning(f"Rate limit NSU excedido para {self.informante}, pulando consulta")
            return None
        
        distInt = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(distInt, "tpAmb").text    = "1"
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, tipo).text       = self.informante
        sub = etree.SubElement(distInt, "distNSU")
        etree.SubElement(sub, "ultNSU").text       = ult_nsu

        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        
        # Valide antes de enviar
        try:
            validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
        except Exception as e:
            logger.error("XML de distribuição não passou na validação XSD. Corrija antes de enviar.")
            return None

        # Tentar conexão com tratamento robusto de exceções
        try:
            logger.debug("Enviando requisição para SEFAZ...")
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
            xml_str = etree.tostring(resp, encoding='utf-8').decode()
            logger.debug(f"Resposta Distribuição:\n{xml_str}")
            
            # Registrar consulta NSU bem-sucedida
            self._rate_limiter.record_nsu_query(self.informante)
            
            return xml_str
            
        except Fault as fault:
            logger.error(f"SOAP Fault Distribuição: {fault}")
            return None
            
        except (requests.exceptions.ConnectTimeout, 
                requests.exceptions.ReadTimeout,
                requests.exceptions.Timeout) as timeout_error:
            logger.error(f"Timeout na conexão com SEFAZ: {timeout_error}")
            logger.warning("Tentativa de distribuição cancelada devido a timeout")
            return None
            
        except requests.exceptions.ConnectionError as conn_error:
            logger.error(f"Erro de conexão com SEFAZ: {conn_error}")
            logger.warning("Verificar conectividade com internet")
            return None
            
        except Exception as e:
            logger.error(f"Erro inesperado na distribuição: {e}")
            logger.exception("Detalhes completos do erro:")
            return None

    def fetch_prot_nfe(self, chave):
        """
        Consulta o protocolo da NF-e pela chave, validando o XML de envio e resposta.
        """
        if not self.cons_client:
            logger.debug("Cliente de protocolo não disponível")
            return None

        # Aplicar rate limiting para consulta de protocolo
        if not self._rate_limiter.wait_if_needed(self.informante, "protocol"):
            logger.warning(f"Rate limit protocolo excedido para {self.informante}, pulando consulta da chave {chave}")
            return None

        logger.debug(f"Chamando protocolo para chave={chave}")
        
        # Cria elemento XML SEM prefixos de namespace
        # O erro 404 "prefixo de namespace não permitido" acontece quando há prefixos como nfe: ou soap:
        NS = "http://www.portalfiscal.inf.br/nfe"
        
        # Cria elemento raiz com namespace padrão (sem prefixo)
        consSitNFe = etree.Element(
            "{%s}consSitNFe" % NS,
            versao="4.00",
            nsmap={None: NS}  # None = namespace padrão (sem prefixo)
        )
        
        # Adiciona elementos filhos (herdam o namespace automaticamente)
        etree.SubElement(consSitNFe, "{%s}tpAmb" % NS).text = "1"
        etree.SubElement(consSitNFe, "{%s}xServ" % NS).text = "CONSULTAR"
        etree.SubElement(consSitNFe, "{%s}chNFe" % NS).text = chave
        
        # Converte para string para validação
        xml_envio_str = etree.tostring(consSitNFe, encoding='unicode', pretty_print=False)
        
        # Valida o XML de consulta
        try:
            validar_xml_auto(xml_envio_str, 'consSitNFe_v4.00.xsd')
        except Exception as e:
            logger.error(f"XML de consulta protocolo não passou na validação XSD: {e}")
            return None

        # 1) Tenta requisição SOAP crua para controlar totalmente namespaces
        try:
            logger.debug("Consultando protocolo na SEFAZ (modo SOAP raw)...")
            logger.debug(f"XML enviado (sem prefixos):\n{xml_envio_str}")
            soap_env = self._build_protocolo_envelope(xml_envio_str)
            ws_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4/nfeConsultaNF"
            headers = {
                'Content-Type': f'application/soap+xml; charset=utf-8; action="{ws_action}"',
            }
            resp = self._session.post(self.cons_endpoint, data=soap_env.encode('utf-8'), headers=headers, timeout=60)
            resp.raise_for_status()
            xml_str = resp.text
            logger.debug(f"Resposta Protocolo (raw):\n{xml_str}")
            self._rate_limiter.record_protocol_query(self.informante)
            return xml_str
        except Exception as raw_err:
            logger.warning(f"Falha no modo SOAP raw: {raw_err}. Tentando via cliente SOAP...")
            # 2) Fallback para cliente SOAP (zeep)
            try:
                resp = self.cons_client.service.nfeConsultaNF(consSitNFe)
                xml_str = etree.tostring(resp, encoding='utf-8').decode()
                logger.debug(f"Resposta Protocolo (zeep):\n{xml_str}")
                self._rate_limiter.record_protocol_query(self.informante)
                return xml_str
            except Fault as fault:
                logger.error(f"SOAP Fault Protocolo: {fault}")
                return None
            except (requests.exceptions.ConnectTimeout, 
                    requests.exceptions.ReadTimeout,
                    requests.exceptions.Timeout) as timeout_error:
                logger.error(f"Timeout na consulta de protocolo: {timeout_error}")
                logger.warning(f"Consulta de protocolo cancelada para chave: {chave}")
                return None
            except requests.exceptions.ConnectionError as conn_error:
                logger.error(f"Erro de conexão na consulta de protocolo: {conn_error}")
                return None
            except Exception as e:
                error_str = str(e)
                if "404" in error_str and ("namespace" in error_str.lower() or "prefixo" in error_str.lower()):
                    logger.warning(f"Erro 404 detectado na consulta de protocolo para chave {chave}")
                    return '<erro_404>Erro 404: Uso de prefixo de namespace nao permitido</erro_404>'
                logger.error(f"Erro inesperado na consulta de protocolo: {e}")
                return None

        # Zeep pode retornar lxml.Element, string, ou objeto
        if hasattr(resp, 'decode'):
            resp_xml = resp.decode()
        elif hasattr(resp, '__str__'):
            resp_xml = str(resp)
        else:
            resp_xml = etree.tostring(resp, encoding="utf-8").decode()

        # Protege contra respostas inválidas (vazia, HTML, etc)
        if not resp_xml or resp_xml.strip().startswith('<html') or resp_xml.strip() == '':
            logger.warning("Resposta inválida da SEFAZ (não é XML): %s", resp_xml)
            return None

        # (Opcional) Salva para depuração
        # with open('ult_resposta_protocolo.xml', 'w', encoding='utf-8') as f:
        #     f.write(resp_xml)

        # Valida o XML da resposta (padrão é leiauteNFe_v4.00.xsd, mas pode mudar conforme SEFAZ)
        try:
            validar_xml_auto(resp_xml, 'leiauteNFe_v4.00.xsd')
        except Exception:
            logger.warning("Resposta da SEFAZ não passou na validação XSD.")
            return None

        logger.debug(f"Resposta Protocolo (raw):\n{resp_xml}")
        return resp_xml

    def _build_protocolo_envelope(self, xml_envio_str: str) -> str:
        """Monta um envelope SOAP 1.2 com o payload já sem prefixos.
        Mantém o consSitNFe com namespace padrão e sem prefixos.
        """
        wsdl_ns = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4"
        # Construímos com o namespace do SOAP apenas no envelope, sem interferir no payload
        envelope = (
            f"<Envelope xmlns=\"http://www.w3.org/2003/05/soap-envelope\">"
            f"<Body>"
            f"<nfeConsultaNF xmlns=\"{wsdl_ns}\">"
            f"<nfeDadosMsg>"
            f"{xml_envio_str}"
            f"</nfeDadosMsg>"
            f"</nfeConsultaNF>"
            f"</Body>"
            f"</Envelope>"
        )
        return envelope

    def fetch_by_chave(self, chave: str):
        """Consulta distribuição por chave específica (consChNFe)."""
        logger.debug(f"Distribuição por chave: {chave}")
        if not self.dist_client:
            logger.error("Cliente de distribuição não disponível")
            return None

        if not self._rate_limiter.wait_if_needed(self.informante, "nsu"):
            logger.warning(f"Rate limit NSU excedido para {self.informante}, pulando consChNFe")
            return None

        ns = XMLProcessor.NS['nfe']
        distInt = etree.Element("distDFeInt", xmlns=ns, versao="1.01")
        etree.SubElement(distInt, "tpAmb").text = "1"
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        cons = etree.SubElement(distInt, "consChNFe")
        etree.SubElement(cons, "chNFe").text = chave

        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        try:
            validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
        except Exception:
            logger.warning("XML consChNFe não validou contra XSD; prosseguindo mesmo assim")

        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
            xml_str = etree.tostring(resp, encoding='utf-8').decode()
            self._rate_limiter.record_nsu_query(self.informante)
            return xml_str
        except Exception as e:
            logger.error(f"Erro na consChNFe: {e}")
            return None

# -------------------------------------------------------------------
# Fluxo Principal
# -------------------------------------------------------------------
def main():
    BASE = Path(__file__).parent
    db = DatabaseManager(BASE / "notas.db")
    db.criar_tabela_detalhada()
    parser = XMLProcessor()
    logger.info(f"=== Início da busca: {datetime.now().isoformat()} ===")
    
    certificados_processados = 0
    total_certificados = 0
    
    try:
        # 1) Distribuição com download automático de XMLs completos
        certificados = db.get_certificados()
        total_certificados = len(certificados)
        logger.info(f"Total de certificados a processar: {total_certificados}")
        
        for cnpj, path, senha, inf, cuf in certificados:
            try:
                logger.debug(f"Processando certificado: CNPJ={cnpj}, arquivo={path}, informante={inf}, cUF={cuf}")
                
                # Inicializar serviço com tratamento de exceções
                try:
                    svc = NFeService(path, senha, cnpj, cuf)
                    if not svc.dist_client:
                        logger.error(f"Não foi possível inicializar serviço para certificado {cnpj}")
                        continue
                except Exception as e:
                    logger.error(f"Erro ao inicializar serviço para certificado {cnpj}: {e}")
                    continue
                
                last_nsu = db.get_last_nsu(inf)
                resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
                
                if not resp:
                    logger.warning(f"Sem resposta da SEFAZ para certificado {cnpj}")
                    continue
                    
                cStat = parser.extract_cStat(resp)
                ult = parser.extract_last_nsu(resp)
                
                if cStat == '656':
                    logger.info(f"{inf}: Consumo indevido (656), manter NSU em {last_nsu}")
                else:
                    if ult:
                        db.set_last_nsu(inf, ult)
                    
                    # Cria downloader de XMLs completos se disponível
                    complete_downloader = None
                    if create_complete_downloader:
                        complete_downloader = create_complete_downloader(svc, parser, db)
                        
                        for nsu, xml in parser.extract_docs(resp):
                            try:
                                # Detecta o tipo de documento
                                doc_type = parser.detect_doc_type(xml)
                                if doc_type == 'resNFe':
                                    # Validar como resumo e salvar como RESUMO
                                    try:
                                        validar_xml_auto(xml, 'resNFe_v1.01.xsd')
                                    except Exception:
                                        logger.debug("resNFe não validou no XSD; prosseguindo")
                                    nota = parser.extrair_dados_resnfe(xml)
                                    if nota:
                                        nota['xml_status'] = 'RESUMO'
                                        nota['informante'] = inf
                                        nota['nsu'] = nsu
                                        db.salvar_nota_detalhada(nota)
                                elif doc_type == 'resCTe':
                                    # Resumo de CTe → criar entrada mínima como RESUMO
                                    try:
                                        validar_xml_auto(xml, 'resCTe_v1.04.xsd')
                                    except Exception:
                                        logger.debug("resCTe não validou no XSD; prosseguindo")
                                    try:
                                        tree_res = etree.fromstring(xml.encode('utf-8'))
                                        nscte = '{http://www.portalfiscal.inf.br/cte}'
                                        chave_cte = tree_res.findtext(f'.//{nscte}chCTe') or ''
                                        xNome = tree_res.findtext(f'.//{nscte}xNome') or ''
                                        dEmi = tree_res.findtext(f'.//{nscte}dEmi') or ''
                                        nota_res = {
                                            'chave': chave_cte,
                                            'ie_tomador': '',
                                            'nome_emitente': xNome,
                                            'cnpj_emitente': '',
                                            'numero': '',
                                            'data_emissao': dEmi,
                                            'tipo': 'CTe',
                                            'valor': '',
                                            'uf': '',
                                            'natureza': '',
                                            'status': 'Resumo',
                                            'xml_status': 'RESUMO',
                                            'informante': inf,
                                            'nsu': nsu,
                                            'atualizado_em': datetime.now().isoformat(),
                                            'cnpj_destinatario': ''
                                        }
                                        db.salvar_nota_detalhada(nota_res)
                                    except Exception:
                                        logger.debug("Falha ao extrair dados de resCTe; prosseguindo")
                                else:
                                    # Tenta tratar como XML completo
                                    try:
                                        validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                                    except Exception:
                                        logger.debug("XML completo não validou no XSD; prosseguindo")
                                    tree   = etree.fromstring(xml.encode('utf-8'))
                                    infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                                    infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                                    if infnfe is not None:
                                        chave  = infnfe.attrib.get('Id','')[-44:]
                                        # Extrai dados completos de NFe
                                        nota = DatabaseManager.extrair_dados_nfe(xml, db)
                                        if nota:
                                            nota['xml_status'] = 'COMPLETO'
                                            nota['informante'] = inf
                                            nota['nsu'] = nsu
                                            db.salvar_nota_detalhada(nota)
                                            db.registrar_xml(chave, cnpj)
                                    elif infcte is not None:
                                        chave  = infcte.attrib.get('Id','')[-44:]
                                        # Extrai dados completos de CTe
                                        nota_cte = extrair_detalhe_cte(xml, chave)
                                        if nota_cte:
                                            nota_cte['xml_status'] = 'COMPLETO'
                                            nota_cte['informante'] = inf
                                            nota_cte['nsu'] = nsu
                                            db.salvar_nota_detalhada(nota_cte)
                                            db.registrar_xml(chave, cnpj)
                                    else:
                                        logger.debug("Documento completo não corresponde a NFe ou CTe conhecidos; pulando")
                            except Exception as e:
                                logger.error(f"Erro ao processar docZip NSU {nsu}: {e}")
                                
                certificados_processados += 1
                logger.info(f"Certificado {cnpj} processado ({certificados_processados}/{total_certificados})")
                
            except Exception as e:
                logger.error(f"Erro ao processar certificado {cnpj}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Erro geral na busca de distribuição: {e}")
    
    # 2) Consulta de Protocolo
    try:
        logger.info("Iniciando consulta de protocolos...")
        faltam = db.get_chaves_missing_status()
        if not faltam:
            logger.info("Nenhuma chave faltando status")
        else:
            logger.info(f"Consultando protocolo para {len(faltam)} chaves")
            protocolos_consultados = 0
            
            for chave, cnpj in faltam:
                try:
                    cert = db.find_cert_by_cnpj(cnpj)
                    if not cert:
                        logger.warning(f"Certificado não encontrado para {cnpj}, ignorando {chave}")
                        continue
                        
                    _, path, senha, inf, cuf = cert
                    
                    try:
                        svc = NFeService(path, senha, cnpj, cuf)
                        if not svc.cons_client:
                            logger.warning(f"Cliente de protocolo não disponível para {cnpj}")
                            continue
                    except Exception as e:
                        logger.error(f"Erro ao inicializar serviço de protocolo para {cnpj}: {e}")
                        continue
                    
                    logger.debug(f"Consultando protocolo para NF-e {chave} (informante {inf})")
                    prot_xml = svc.fetch_prot_nfe(chave)
                    
                    if prot_xml:
                        ch, cStat, xMotivo = parser.parse_protNFe(prot_xml)
                        
                        # Trata erros específicos da SEFAZ
                        if cStat == '404':
                            logger.warning(f"Erro 404 (namespace) para chave {chave}: {xMotivo}")
                            # Marca como erro para não tentar novamente
                            db.set_nf_status(chave, '404', f"Erro SEFAZ: {xMotivo}")
                            protocolos_consultados += 1  # Conta como processado
                            continue
                            
                        if ch and ch == chave:  # Verifica se a chave confere
                            db.set_nf_status(ch, cStat, xMotivo)
                            protocolos_consultados += 1
                        elif ch:  # Chave diferente
                            logger.warning(f"Chave retornada ({ch}) diferente da solicitada ({chave})")
                            db.set_nf_status(chave, 'ERRO', "Chave divergente na resposta")
                            protocolos_consultados += 1
                        else:
                            logger.warning(f"Chave não encontrada na resposta do protocolo para {chave}")
                            # Marca como erro para não ficar tentando infinitamente
                            db.set_nf_status(chave, 'SEM_PROTOCOLO', 'Protocolo não encontrado na resposta')
                            protocolos_consultados += 1
                    else:
                        logger.warning(f"Sem resposta de protocolo para chave {chave}")
                        db.set_nf_status(chave, 'SEM_RESPOSTA', 'SEFAZ não retornou dados')
                        protocolos_consultados += 1
                            
                except Exception as e:
                    logger.error(f"Erro ao consultar protocolo para chave {chave}: {e}")
                    # Marca como erro para não tentar novamente
                    db.set_nf_status(chave, 'ERRO', f"Erro consulta: {str(e)[:100]}")
                    continue
            
            logger.info(f"Consulta de protocolos concluída: {protocolos_consultados} protocolos atualizados")
            
    except Exception as e:
        logger.error(f"Erro geral na consulta de protocolos: {e}")
    
    logger.info(f"=== Busca concluída: {datetime.now().isoformat()} ===")
    logger.info(f"Certificados processados: {certificados_processados}/{total_certificados}")

if __name__ == "__main__":
    import sys
    BASE = Path(__file__).parent
    db = DatabaseManager(BASE / "notas.db")
    parser = XMLProcessor()
    
    # Se receber argumentos da interface, executa apenas uma vez
    if len(sys.argv) > 1:
        logger.info("Executando busca única (chamada da interface)")
        main()
    else:
        # Execução normal com loop infinito
        logger.info("Executando busca periódica (modo daemon)")
        ciclo_nsu(db, parser, intervalo=3600)  # 3600 segundos = 1h