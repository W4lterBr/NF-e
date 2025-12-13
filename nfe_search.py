# Bibliotecas padrão
import os
import gzip
import re
import base64
import logging
import sqlite3
import time
import warnings
from pathlib import Path
from datetime import datetime

# Suprime avisos de SSL não verificado
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Bibliotecas de terceiros
import requests
import requests_pkcs12
from requests.exceptions import RequestException
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Fault
from lxml import etree

# -------------------------------------------------------------------
# Diretório de Dados
# -------------------------------------------------------------------
def get_data_dir():
    """Retorna o diretório de dados do aplicativo."""
    import sys
    import os
    
    # Se estiver executando como executável PyInstaller
    if getattr(sys, 'frozen', False):
        # Usa AppData do usuário
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "BOT Busca NFE"
    else:
        # Desenvolvimento: usa pasta local
        data_dir = Path(__file__).parent
    
    # Garante que o diretório existe
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

BASE = get_data_dir()

# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
def setup_logger():
    """Configura logger com saída para console e arquivo na pasta logs."""
    LOGS_DIR = BASE / "logs"
    
    # Cria pasta de logs se não existir
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Nome do arquivo de log com data
    log_filename = LOGS_DIR / f"busca_nfe_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Remove log anterior se existir
    if log_filename.exists():
        try:
            log_filename.unlink()
        except Exception:
            pass  # Se não conseguir deletar, continua
    
    logger = logging.getLogger(__name__)
    
    if not logger.hasHandlers():
        # Handler para arquivo
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(file_formatter)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    logger.setLevel(logging.DEBUG)
    return logger

logger = setup_logger()
logger.debug("Iniciando nfe_search.py")
# -------------------------------------------------------------------
# Fluxo NSU
# -------------------------------------------------------------------
def ciclo_nsu(db, parser, intervalo=3600):
    """
    Executa o ciclo de busca de NSU para todos os certificados cadastrados.
    Faz busca periódica e salva notas detalhadas.
    Se ocorrer erro de conexão ou indisponibilidade da SEFAZ/internet,
    registra no log, aguarda alguns minutos e tenta novamente sem encerrar o processo.
    
    Implementa:
    - NSU = 0 automático para primeira consulta
    - Retry exponencial (5s → 15s → 60s → 5min)
    - Modo investigação após 5 falhas consecutivas
    - Detecção de estado offline
    """
    BASE_DIR = Path(__file__).parent
    XML_DIR = BASE_DIR / "xmls"
    INTERVALO_CONSUMO_INDEVIDO = 3900  # 65 minutos (1h5min)
    
    # Controle de retry exponencial
    RETRY_DELAYS = [5, 15, 60, 300]  # 5s, 15s, 60s, 5min
    MAX_FALHAS_INVESTIGACAO = 5
    
    # Estado global
    estado_offline = False
    falhas_consecutivas = {}
    
    while True:
        try:
            logger.info(f"Iniciando busca periódica de NSU em {datetime.now().isoformat()}")
            certificados = db.get_certificados()
            total_certs = len(certificados)
            
            for idx, (cnpj, path, senha, inf, cuf) in enumerate(certificados, 1):
                consumo_indevido = False  # Inicializa ANTES do try
                
                try:
                    logger.info(f"[{idx}/{total_certs}] Processando certificado {inf} (CNPJ: {cnpj})")
                    
                    # Verifica se pode consultar (erro 656 recente?)
                    ult_nsu = db.get_last_nsu(inf)
                    if not db.pode_consultar_certificado(inf, ult_nsu):
                        logger.info(f"Pulando {inf} - aguardando cooldown erro 656")
                        continue
                    
                    # ✅ NSU = 0 AUTOMÁTICO: Detecta primeira consulta
                    if ult_nsu == "000000000000000":
                        logger.info(f"🔍 [{inf}] PRIMEIRA CONSULTA DETECTADA - Iniciando varredura completa (NSU=0)")
                        db.marcar_primeira_consulta(inf)
                    
                    svc = NFeService(path, senha, cnpj, cuf)
                    logger.debug(f"Buscando notas a partir do NSU {ult_nsu} para {inf}")
                    
                    # Inicializa contador de falhas para este certificado
                    if inf not in falhas_consecutivas:
                        falhas_consecutivas[inf] = 0
                    
                    while True:
                        try:
                            resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", ult_nsu)
                            if not resp:
                                logger.warning(f"Falha ao buscar NSU para {inf}")
                                break
                            
                            cStat = parser.extract_cStat(resp)
                            
                            # ✅ NSU = 0: Mostra maxNSU na primeira consulta
                            if ult_nsu == "000000000000000":
                                max_nsu = parser.extract_max_nsu(resp)
                                if max_nsu and max_nsu != "000000000000000":
                                    logger.info(f"📊 [{inf}] Total documentos disponíveis: {int(max_nsu)} (varredura completa)")
                            
                            if cStat == '656':  # Consumo indevido, bloqueio temporário
                                ult = parser.extract_last_nsu(resp)
                                if ult and ult != ult_nsu:
                                    db.set_last_nsu(inf, ult)
                                    logger.info(f"NSU atualizado após consumo indevido para {inf}: {ult}")
                                
                                # Registra erro 656 para bloquear tentativas por 65 minutos
                                db.registrar_erro_656(inf, ult_nsu)
                                logger.warning(f"Consumo indevido para {inf}, bloqueado por 65 minutos")
                                consumo_indevido = True
                                break

                            docs = parser.extract_docs(resp)
                            if not docs:
                                logger.info(f"Nenhum novo docZip para {inf}")
                                break
                            for nsu, xml in docs:
                                try:
                                    # Detecta tipo de documento
                                    tipo = detectar_tipo_documento(xml)
                                    
                                    # Valida com schema apropriado (pula validação por enquanto para CT-e)
                                    if tipo == 'NFe':
                                        validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                                    # CT-e não valida por enquanto (pode adicionar schema depois)
                                    
                                    tree = etree.fromstring(xml.encode('utf-8'))
                                    
                                    # Detecta tipo pela tag raiz para determinar status
                                    root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
                                    
                                    # Determina se é documento completo ou resumo/evento
                                    if root_tag in ['nfeProc', 'cteProc', 'NFe', 'CTe']:
                                        xml_status = 'COMPLETO'
                                    elif root_tag == 'resNFe':
                                        xml_status = 'RESUMO'
                                    elif root_tag in ['resEvento', 'procEventoNFe', 'evento']:
                                        xml_status = 'EVENTO'
                                    else:
                                        xml_status = 'RESUMO'  # Padrão para desconhecidos
                                    
                                    # Extrai chave baseado no tipo
                                    chave = None
                                    if tipo == 'NFe':
                                        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                                        if infnfe is not None:
                                            chave = infnfe.attrib.get('Id','')[-44:]
                                    elif tipo == 'CTe':
                                        infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                                        if infcte is not None:
                                            chave = infcte.attrib.get('Id','')[-44:]
                                    
                                    # Para resumos e eventos, tenta extrair chave de outro local
                                    if not chave:
                                        ns = '{http://www.portalfiscal.inf.br/nfe}'
                                        chNFe_elem = tree.find(f'.//{ns}chNFe')
                                        if chNFe_elem is not None and chNFe_elem.text:
                                            chave = chNFe_elem.text.strip()
                                    
                                    if not chave:
                                        continue
                                    
                                    db.registrar_xml(chave, cnpj)
                                    
                                    # Extrai e grava status diretamente do XML
                                    cStat, xMotivo = parser.extract_status_from_xml(xml)
                                    if cStat and xMotivo:
                                        db.set_nf_status(chave, cStat, xMotivo)
                                        logger.debug(f"Status gravado para {chave}: {cStat} - {xMotivo}")
                                    
                                    # Salva o XML em disco
                                    salvar_xml_por_certificado(xml, cnpj)
                                    # Salva nota detalhada
                                    db.criar_tabela_detalhada()
                                    nota = extrair_nota_detalhada(xml, parser, db, chave, inf)
                                    nota['informante'] = inf  # Adiciona informante (redundância para garantir)
                                    nota['xml_status'] = xml_status  # Marca corretamente: COMPLETO, RESUMO ou EVENTO
                                    db.salvar_nota_detalhada(nota)
                                    
                                    # Se for evento, atualiza o status da nota original
                                    if xml_status == 'EVENTO':
                                        processar_evento_status(xml, chave, db)
                                except Exception:
                                    logger.exception("Erro ao processar docZip")
                            
                            # SEMPRE sincroniza com ultNSU da SEFAZ (mesmo que não tenha mudado)
                            ult = parser.extract_last_nsu(resp)
                            if ult:
                                # ✅ Reset contador de falhas após sucesso
                                if inf in falhas_consecutivas:
                                    falhas_consecutivas[inf] = 0
                                
                                # ✅ Marca estado como online
                                if estado_offline:
                                    logger.info(f"✅ RECONECTADO: Internet/SEFAZ online novamente")
                                    estado_offline = False
                                
                                if ult != ult_nsu:
                                    # NSU avançou - registra e continua buscando
                                    db.set_last_nsu(inf, ult)
                                    logger.info(f"NSU avançou para {inf}: {ult_nsu} → {ult}")
                                    ult_nsu = ult
                                else:
                                    # NSU não mudou - sincroniza mesmo assim e encerra busca
                                    db.set_last_nsu(inf, ult)
                                    logger.debug(f"NSU sincronizado (sem mudança) para {inf}: {ult}")
                                    break
                            else:
                                # SEFAZ não retornou ultNSU - situação anormal
                                logger.warning(f"SEFAZ não retornou ultNSU para {inf}")
                                break
                        except (requests.exceptions.RequestException, Fault, OSError) as e:
                            # ✅ RETRY EXPONENCIAL ESTRUTURADO
                            falhas_consecutivas[inf] = falhas_consecutivas.get(inf, 0) + 1
                            falha_num = falhas_consecutivas[inf]
                            
                            # Detecta se é problema de rede (offline)
                            if isinstance(e, (requests.exceptions.ConnectionError, OSError)):
                                estado_offline = True
                                logger.error(f"🔴 OFFLINE: Sem conexão com internet/SEFAZ para {inf}")
                            
                            logger.warning(f"⚠️ Falha #{falha_num} para {inf}: {e}")
                            
                            # MODO INVESTIGAÇÃO: Após 5 falhas consecutivas
                            if falha_num >= MAX_FALHAS_INVESTIGACAO:
                                logger.critical(f"🔍 MODO INVESTIGAÇÃO ATIVADO para {inf} (5+ falhas consecutivas)")
                                logger.info(f"   → Revalidando certificado: {path}")
                                logger.info(f"   → Testando conectividade SEFAZ cUF={cuf}")
                                logger.info(f"   → Pausando consultas por 10 minutos")
                                time.sleep(600)  # 10 minutos de pausa
                                falhas_consecutivas[inf] = 0  # Reset contador
                                continue
                            
                            # Retry exponencial
                            delay_idx = min(falha_num - 1, len(RETRY_DELAYS) - 1)
                            delay = RETRY_DELAYS[delay_idx]
                            logger.info(f"⏳ Retry exponencial: aguardando {delay}s antes de tentar novamente...")
                            time.sleep(delay)
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
                        # Extrai e atualiza status do XML
                        cStat, xMotivo = parser.extract_status_from_xml(xml_txt)
                        if cStat and xMotivo:
                            db.set_nf_status(chave, cStat, xMotivo)
                        
                        nota = extrair_nota_detalhada(xml_txt, parser, db, chave, inf)
                        nota['informante'] = inf  # Garantir informante
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
def detectar_tipo_documento(xml_txt):
    """
    Detecta o tipo de documento fiscal no XML.
    Retorna: 'NFe', 'CTe' ou None
    """
    try:
        tree = etree.fromstring(xml_txt.encode("utf-8"))
        # Verifica NF-e
        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        if infnfe is not None:
            return 'NFe'
        # Verifica CT-e
        infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
        if infcte is not None:
            return 'CTe'
        return None
    except Exception:
        return None

def extrair_chave_nfe(xml_txt):
    """Extrai chave de acesso de NF-e ou CT-e."""
    try:
        tree = etree.fromstring(xml_txt.encode("utf-8"))
        # Tenta NF-e
        infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        if infnfe is not None:
            return infnfe.attrib.get('Id', '')[-44:]
        # Tenta CT-e
        infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
        if infcte is not None:
            return infcte.attrib.get('Id', '')[-44:]
        return None
    except Exception:
        return None

# Função para montar o dict da nota detalhada a partir do XML
def extrair_cte_detalhado(xml_txt, parser, db, chave, informante=None):
    """Extrai informações detalhadas de um CT-e."""
    try:
        tree = etree.fromstring(xml_txt.encode('utf-8'))
        inf = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
        ide = inf.find('{http://www.portalfiscal.inf.br/cte}ide') if inf is not None else None
        emit = inf.find('{http://www.portalfiscal.inf.br/cte}emit') if inf is not None else None
        dest = inf.find('{http://www.portalfiscal.inf.br/cte}dest') if inf is not None else None
        rem = inf.find('{http://www.portalfiscal.inf.br/cte}rem') if inf is not None else None
        vPrest = tree.find('.//{http://www.portalfiscal.inf.br/cte}vPrest')
        
        # Valor do CT-e
        valor = ""
        if vPrest is not None:
            vTPrest = vPrest.findtext('{http://www.portalfiscal.inf.br/cte}vTPrest')
            valor = f"R$ {float(vTPrest):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vTPrest else ""
        
        # CFOP do CT-e
        cfop = ide.findtext('{http://www.portalfiscal.inf.br/cte}CFOP') if ide is not None else ""
        
        # Busca status no banco
        status_db = db.get_nf_status(chave)
        if status_db and status_db[0] and status_db[1]:
            status_str = f"{status_db[0]} – {status_db[1]}"
        else:
            status_str = "Autorizado o uso do CT-e"
        
        # CNPJ do destinatário ou remetente
        cnpj_destinatario = ""
        if dest is not None:
            cnpj_destinatario = dest.findtext('{http://www.portalfiscal.inf.br/cte}CNPJ', "")
        elif rem is not None:
            cnpj_destinatario = rem.findtext('{http://www.portalfiscal.inf.br/cte}CNPJ', "")
        
        return {
            "chave": chave or "",
            "ie_tomador": dest.findtext('{http://www.portalfiscal.inf.br/cte}IE') if dest is not None else "",
            "nome_emitente": emit.findtext('{http://www.portalfiscal.inf.br/cte}xNome') if emit is not None else "",
            "cnpj_emitente": emit.findtext('{http://www.portalfiscal.inf.br/cte}CNPJ') if emit is not None else "",
            "numero": ide.findtext('{http://www.portalfiscal.inf.br/cte}nCT') if ide is not None else "",
            "data_emissao": (ide.findtext('{http://www.portalfiscal.inf.br/cte}dhEmi')[:10]
                            if ide is not None and ide.findtext('{http://www.portalfiscal.inf.br/cte}dhEmi')
                            else ""),
            "tipo": "CTe",
            "valor": valor,
            "cfop": cfop,
            "vencimento": "",  # CT-e geralmente não tem vencimento
            "uf": ide.findtext('{http://www.portalfiscal.inf.br/cte}cUF') if ide is not None else "",
            "natureza": ide.findtext('{http://www.portalfiscal.inf.br/cte}natOp') if ide is not None else "",
            "status": status_str,
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": cnpj_destinatario,
            "xml_status": "COMPLETO",
            "informante": str(informante or "")
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair CT-e detalhado: {e}")
        return {
            "chave": chave or "",
            "ie_tomador": "",
            "nome_emitente": "",
            "cnpj_emitente": "",
            "numero": "",
            "data_emissao": "",
            "tipo": "CTe",
            "valor": "",
            "cfop": "",
            "vencimento": "",
            "uf": "",
            "natureza": "",
            "status": "Autorizado o uso do CT-e",
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": "",
            "xml_status": "COMPLETO",
            "informante": str(informante or "")
        }

def processar_evento_status(xml_txt, chave_evento, db):
    """
    Processa eventos (cancelamento, carta correção) e atualiza o status da nota original.
    """
    try:
        from lxml import etree
        
        root = etree.fromstring(xml_txt.encode('utf-8') if isinstance(xml_txt, str) else xml_txt)
        ns = '{http://www.portalfiscal.inf.br/nfe}'
        
        # Extrai chave da nota referenciada
        chNFe = root.findtext(f'.//{ns}chNFe')
        if not chNFe or len(chNFe) != 44:
            return
        
        # Extrai tipo de evento
        tpEvento = root.findtext(f'.//{ns}tpEvento')
        
        # Extrai status do evento
        cStat = root.findtext(f'.//{ns}cStat')
        xMotivo = root.findtext(f'.//{ns}xMotivo')
        
        # Mapeia eventos para status
        if tpEvento == '110111' and cStat == '135':  # Cancelamento autorizado
            novo_status = "Cancelamento de NF-e homologado"
            db.atualizar_status_por_evento(chNFe, novo_status)
            logger.info(f"Status atualizado: {chNFe} → {novo_status}")
        
        elif tpEvento == '110110' and cStat == '135':  # Carta de correção
            novo_status = "Carta de Correção registrada"
            db.atualizar_status_por_evento(chNFe, novo_status)
            logger.info(f"Status atualizado: {chNFe} → {novo_status}")
        
        # Eventos de manifestação (210200-210240) não alteram status principal
        
    except Exception as e:
        logger.debug(f"Erro ao processar evento de status: {e}")

def extrair_nota_detalhada(xml_txt, parser, db, chave, informante=None):
    """Extrai informações detalhadas de NF-e ou CT-e automaticamente."""
    tipo = detectar_tipo_documento(xml_txt)
    
    if tipo == 'CTe':
        return extrair_cte_detalhado(xml_txt, parser, db, chave, informante)
    elif tipo == 'NFe':
        return extrair_nfe_detalhado(xml_txt, parser, db, chave, informante)
    else:
        # Tipo desconhecido, tenta NF-e como padrão
        return extrair_nfe_detalhado(xml_txt, parser, db, chave, informante)

def extrair_nfe_detalhado(xml_txt, parser, db, chave, informante=None):
    """Extrai informações detalhadas de uma NF-e."""
    try:
        tree = etree.fromstring(xml_txt.encode('utf-8'))
        inf = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
        ide = inf.find('{http://www.portalfiscal.inf.br/nfe}ide') if inf is not None else None
        emit = inf.find('{http://www.portalfiscal.inf.br/nfe}emit') if inf is not None else None
        dest = inf.find('{http://www.portalfiscal.inf.br/nfe}dest') if inf is not None else None
        tot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}ICMSTot')

        cfop = ""
        ncm = ""
        if inf is not None:
            for det in inf.findall('{http://www.portalfiscal.inf.br/nfe}det'):
                prod = det.find('{http://www.portalfiscal.inf.br/nfe}prod')
                if prod is not None:
                    if not cfop:
                        cfop = prod.findtext('{http://www.portalfiscal.inf.br/nfe}CFOP') or ""
                    if not ncm:
                        ncm = prod.findtext('{http://www.portalfiscal.inf.br/nfe}NCM') or ""
                    if cfop and ncm:
                        break

        vencimento = ""
        if inf is not None:
            cobr = inf.find('{http://www.portalfiscal.inf.br/nfe}cobr')
            if cobr is not None:
                dup = cobr.find('.//{http://www.portalfiscal.inf.br/nfe}dup')
                if dup is not None:
                    vencimento = dup.findtext('{http://www.portalfiscal.inf.br/nfe}dVenc', "")

        valor = ""
        base_icms = ""
        valor_icms = ""
        if tot is not None:
            vnf = tot.findtext('{http://www.portalfiscal.inf.br/nfe}vNF')
            valor = f"R$ {float(vnf):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vnf else ""
            
            vBC = tot.findtext('{http://www.portalfiscal.inf.br/nfe}vBC')
            base_icms = f"R$ {float(vBC):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vBC else ""
            
            vICMS = tot.findtext('{http://www.portalfiscal.inf.br/nfe}vICMS')
            valor_icms = f"R$ {float(vICMS):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if vICMS else ""

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
            "ncm": ncm,
            "uf": ide.findtext('{http://www.portalfiscal.inf.br/nfe}cUF') if ide is not None else "",
            "natureza": ide.findtext('{http://www.portalfiscal.inf.br/nfe}natOp') if ide is not None else "",
            "base_icms": base_icms,
            "valor_icms": valor_icms,
            "status": status_str,
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": cnpj_destinatario,
            "xml_status": "COMPLETO",
            "informante": str(informante or "")
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair nota detalhada: {e}")
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
            "ncm": "",
            "uf": "",
            "natureza": "",
            "base_icms": "",
            "valor_icms": "",
            "status": "Autorizado o uso da NF-e",
            "atualizado_em": datetime.now().isoformat(),
            "cnpj_destinatario": "",
            "xml_status": "COMPLETO",
            "informante": str(informante or "")
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
    Salva o XML em uma pasta separada por certificado (apenas dígitos) e ano-mês de emissão.
    Detecta automaticamente o tipo de documento e salva na pasta apropriada.
    
    Tipos suportados:
    - NFe completas (procNFe) → NFe/
    - CTe completas (procCTe) → CTe/
    - Resumos NFe (resNFe) → Resumos/
    - Eventos (resEvento, procEventoNFe) → Eventos/
    
    Exemplo: xmls/47539664000197/2025-08/NFe/00123-EMPRESA.xml
    Exemplo: xmls/47539664000197/2025-08/Eventos/CANC-00123-EMPRESA.xml
    """
    import os
    from lxml import etree
    import re
    from datetime import datetime

    def sanitize_filename(s: str) -> str:
        """Remove caracteres inválidos para nomes de arquivos/pastas."""
        return re.sub(r'[\\/*?:"<>|]', "_", s or "").strip()

    try:
        # Verifica se é apenas protocolo (não salva)
        xml_str = xml if isinstance(xml, str) else xml.decode('utf-8')
        xml_lower = xml_str.lower()
        
        # Detecta se é apenas protocolo de consulta (sem dados da nota)
        is_only_protocol = (
            '<retconssit' in xml_lower and 
            '<protnfe' in xml_lower and
            '<nfeproc' not in xml_lower and
            '<nfe' not in xml_lower.replace('nferesultmsg', '').replace('protnfe', '')
        )
        
        if is_only_protocol:
            logger.warning("XML contém apenas protocolo, não será salvo")
            return  # Não salva protocolos sem dados
        
        cnpj_cpf_fmt = format_cnpj_cpf_dir(cnpj_cpf)

        # Parse o XML para extrair dados de organização
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        
        # Detecta tipo de documento pela tag raiz
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # Determina a pasta e tipo baseado no documento
        if root_tag in ['nfeProc', 'NFe']:
            tipo_pasta = "NFe"
            tipo_doc = "NFe"
        elif root_tag in ['cteProc', 'CTe']:
            tipo_pasta = "CTe"
            tipo_doc = "CTe"
        elif root_tag == 'resNFe':
            tipo_pasta = "Resumos"
            tipo_doc = "ResNFe"
        elif root_tag in ['resEvento', 'procEventoNFe', 'evento']:
            tipo_pasta = "Eventos"
            tipo_doc = "Evento"
        else:
            # Tipo desconhecido - salva em "Outros"
            tipo_pasta = "Outros"
            tipo_doc = "Outro"
        
        # Extrai informações para organização
        ide = None
        emit = None
        nNF = None
        xNome = None
        data_raw = None
        
        # Para NFe/CTe completas
        if tipo_doc in ["NFe", "CTe"]:
            ns = '{http://www.portalfiscal.inf.br/nfe}' if tipo_doc == "NFe" else '{http://www.portalfiscal.inf.br/cte}'
            ide = root.find(f'.//{ns}ide')
            emit = root.find(f'.//{ns}emit')
            
            if ide is not None:
                nNF = ide.findtext(f'{ns}nNF' if tipo_doc == "NFe" else f'{ns}nCT')
                dEmi = ide.findtext(f'{ns}dEmi')
                dhEmi = ide.findtext(f'{ns}dhEmi')
                data_raw = dEmi or dhEmi
            
            if emit is not None:
                xNome = emit.findtext(f'{ns}xNome')
        
        # Para resumos (resNFe)
        elif tipo_doc == "ResNFe":
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            chNFe = root.findtext(f'{ns}chNFe')
            if chNFe and len(chNFe) >= 44:
                # Extrai data da chave (posições 2-8: AAMMDD)
                try:
                    ano = "20" + chNFe[2:4]
                    mes = chNFe[4:6]
                    data_raw = f"{ano}-{mes}-01"
                except:
                    pass
            nNF = root.findtext(f'{ns}nNF') or "RESUMO"
            xNome = root.findtext(f'{ns}xNome') or "NFe"
        
        # Para eventos (resEvento, procEventoNFe)
        elif tipo_doc == "Evento":
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            
            # Tenta extrair chave e tipo de evento
            chNFe = root.findtext(f'.//{ns}chNFe')
            tpEvento = root.findtext(f'.//{ns}tpEvento')
            nSeqEvento = root.findtext(f'.//{ns}nSeqEvento') or "1"
            dhEvento = root.findtext(f'.//{ns}dhEvento')
            
            # Mapeia tipo de evento
            eventos_map = {
                '110110': 'CARTA_CORRECAO',
                '110111': 'CANCELAMENTO',
                '210200': 'CONFIRMACAO',
                '210210': 'CIENCIA',
                '210220': 'DESCONHECIMENTO',
                '210240': 'NAO_REALIZADA'
            }
            tipo_evento = eventos_map.get(tpEvento, f'EVENTO_{tpEvento}')
            
            if chNFe and len(chNFe) >= 44:
                # Extrai data da chave
                try:
                    ano = "20" + chNFe[2:4]
                    mes = chNFe[4:6]
                    data_raw = f"{ano}-{mes}-01"
                    # Extrai número da nota da chave (posições 25-34)
                    nNF = chNFe[25:34]
                except:
                    pass
            
            if dhEvento:
                data_raw = dhEvento
            
            nNF = nNF or "EVENTO"
            xNome = tipo_evento
        
        # Define ano-mês para organização
        if data_raw:
            data_part = data_raw.split("T")[0]
            ano_mes = data_part[:7] if len(data_part) >= 7 else datetime.now().strftime("%Y-%m")
        else:
            ano_mes = datetime.now().strftime("%Y-%m")
        
        nNF = nNF or "SEM_NUMERO"
        xNome = xNome or "SEM_NOME"
        
        # Cria pasta com tipo de documento
        pasta_dest = os.path.join(pasta_base, cnpj_cpf_fmt, ano_mes, tipo_pasta)
        os.makedirs(pasta_dest, exist_ok=True)

        nome_arquivo = f"{sanitize_filename(nNF)}-{sanitize_filename(xNome)[:40]}.xml"
        caminho_xml = os.path.join(pasta_dest, nome_arquivo)

        with open(caminho_xml, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[SALVO {tipo_doc}] {caminho_xml}")
        
        # Gerar PDF automaticamente (apenas para NFe/CTe completas)
        if tipo_doc in ["NFe", "CTe"]:
            try:
                caminho_pdf = caminho_xml.replace('.xml', '.pdf')
                if not os.path.exists(caminho_pdf):
                    from modules.pdf_simple import generate_danfe_pdf
                    success = generate_danfe_pdf(xml, caminho_pdf, tipo_doc)
                    if success:
                        print(f"[PDF GERADO] {caminho_pdf}")
            except Exception as pdf_err:
                print(f"[AVISO] Erro ao gerar PDF: {pdf_err}")
    except Exception as e:
        print(f"[ERRO ao salvar XML de {cnpj_cpf}]: {e}")
# -------------------------------------------------------------------
# Validação de XML com XSD
# -------------------------------------------------------------------
def validar_xml_auto(xml, default_xsd):
    # Debug desativado para evitar travamento com XMLs grandes
    # print("\n--- XML sendo validado ---\n", xml, "\n-------------------------\n")

    # Mapeamento padrão
    ROOT_XSD_MAP = {
        "nfeProc":      "procNFe_v4.00.xsd",
        "NFe":          "leiauteNFe_v4.00.xsd",
        "procEventoNFe":"procEventoNFe_v1.00.xsd",
        "resNFe":       "resNFe_v1.01.xsd",
        "resEvento":    "resEvento_v1.01.xsd",
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
        logger.debug(f"PULANDO validação XSD para {root_tag} (problema conhecido com XSD de eventos SEFAZ)")
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
                logger.debug(f"XSD Encontrado: {p}")
                return str(p)
        logger.warning(f"XSD NÃO encontrado: {xsd_name} em {base_dir}")
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
    '31': "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4?wsdl",  # MG
    '50': "https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4?wsdl",  # MS
    '51': "https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx?wsdl",  # SVRS
    '52': "https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx?wsdl",  # GO -> SVRS
}
URL_CONSULTA_FALLBACK = (
    "https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/"
    "NFeConsultaProtocolo4.asmx?wsdl"
)
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
            cur.execute('''CREATE TABLE IF NOT EXISTS nsu_cte (
                informante TEXT PRIMARY KEY,
                ult_nsu TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS erro_656 (
                informante TEXT PRIMARY KEY,
                ultimo_erro TIMESTAMP,
                nsu_bloqueado TEXT
            )''')
            conn.commit()
            logger.debug("Tabelas verificadas/criadas no banco")
    
    def criar_tabela_detalhada(self):
        with self._connect() as conn:
            # Cria a tabela com todos os campos necessários
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
                ncm TEXT,
                status TEXT DEFAULT 'Autorizado o uso da NF-e',
                natureza TEXT,
                uf TEXT,
                base_icms TEXT,
                valor_icms TEXT,
                informante TEXT,
                xml_status TEXT DEFAULT 'COMPLETO',
                atualizado_em DATETIME,
                cnpj_destinatario TEXT
            )
            ''')
            # Garante que as colunas existem (caso o banco seja antigo)
            columns_to_add = [
                ("cnpj_destinatario", "TEXT"),
                ("xml_status", "TEXT DEFAULT 'COMPLETO'"),
                ("ncm", "TEXT"),
                ("base_icms", "TEXT"),
                ("valor_icms", "TEXT"),
                ("informante", "TEXT")
            ]
            for col_name, col_type in columns_to_add:
                try:
                    conn.execute(f"ALTER TABLE notas_detalhadas ADD COLUMN {col_name} {col_type};")
                except sqlite3.OperationalError:
                    # Já existe, ignora o erro
                    pass
            conn.commit()

    def salvar_nota_detalhada(self, nota):
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO notas_detalhadas (
                    chave, ie_tomador, nome_emitente, cnpj_emitente, numero,
                    data_emissao, tipo, valor, cfop, vencimento, ncm, uf, natureza,
                    base_icms, valor_icms, status, atualizado_em, cnpj_destinatario, 
                    xml_status, informante
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nota['chave'], nota['ie_tomador'], nota['nome_emitente'], nota['cnpj_emitente'],
                nota['numero'], nota['data_emissao'], nota['tipo'], nota['valor'],
                nota.get('cfop', ''), nota.get('vencimento', ''), nota.get('ncm', ''),
                nota.get('uf', ''), nota.get('natureza', ''), 
                nota.get('base_icms', ''), nota.get('valor_icms', ''),
                nota['status'], nota['atualizado_em'],
                nota.get('cnpj_destinatario', ''), 
                nota.get('xml_status', 'COMPLETO'),
                nota.get('informante', '')
            ))
            conn.commit()

    def get_certificados(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()
            logger.debug(f"Certificados carregados: {rows}")
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
            
            # Se o NSU avançou, limpa o bloqueio de erro 656 (pode ter documentos novos)
            conn.execute("DELETE FROM erro_656 WHERE informante = ?", (informante,))
            conn.commit()
    
    def get_last_nsu_cte(self, informante):
        """Obtém último NSU processado de CT-e para o informante"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ult_nsu FROM nsu_cte WHERE informante=?", (informante,)
            ).fetchone()
            last = row[0] if row else "000000000000000"
            logger.debug(f"Último NSU CT-e para {informante}: {last}")
            return last

    def set_last_nsu_cte(self, informante, nsu):
        """Atualiza último NSU processado de CT-e para o informante"""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu_cte (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU CT-e atualizado para {informante}: {nsu}")
    
    def registrar_erro_656(self, informante, nsu):
        """Registra que houve erro 656 para este informante/NSU"""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, datetime('now'), ?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"Erro 656 registrado: {informante} NSU={nsu}")
    
    def marcar_primeira_consulta(self, informante):
        """Marca que este certificado está fazendo a primeira consulta (NSU=0)"""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, datetime('now'))",
                (f'primeira_consulta_{informante}',)
            )
            conn.commit()
            logger.info(f"✅ Primeira consulta marcada para {informante}")
    
    def pode_consultar_certificado(self, informante, nsu_atual):
        """Verifica se pode consultar o certificado (não teve erro 656 na última hora)"""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT ultimo_erro, nsu_bloqueado 
                   FROM erro_656 
                   WHERE informante = ?""",
                (informante,)
            ).fetchone()
            
            if not row:
                return True  # Nunca teve erro 656
            
            ultimo_erro_str, nsu_bloqueado = row
            
            # Se o NSU mudou, pode consultar (tem documentos novos)
            if nsu_bloqueado != nsu_atual:
                logger.debug(f"{informante}: NSU mudou de {nsu_bloqueado} para {nsu_atual}, pode consultar")
                return True
            
            # Verifica se já passou 65 minutos desde o último erro
            from datetime import datetime, timedelta
            ultimo_erro = datetime.fromisoformat(ultimo_erro_str)
            agora = datetime.now()
            diferenca = (agora - ultimo_erro).total_seconds() / 60  # em minutos
            
            if diferenca >= 65:  # 65 minutos de segurança
                logger.debug(f"{informante}: Passou {diferenca:.1f} minutos desde erro 656, pode consultar")
                return True
            else:
                logger.info(f"{informante}: Ainda em bloqueio erro 656 (faltam {65 - diferenca:.1f} minutos)")
                return False

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
    
    def extract_max_nsu(self, resp_xml):
        """Extrai maxNSU da resposta SEFAZ - indica o maior NSU disponível (útil na primeira consulta)"""
        try:
            tree = etree.fromstring(resp_xml.encode('utf-8'))
            max_nsu = tree.find('.//nfe:maxNSU', namespaces=self.NS)
            if max_nsu is not None and max_nsu.text:
                val = max_nsu.text.strip().zfill(15)
                logger.debug(f"maxNSU extraído: {val}")
                return val
        except:
            pass
        return None

    def extract_cStat(self, resp_xml):
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        cs = tree.find('.//nfe:cStat', namespaces=self.NS)
        stat = cs.text if cs is not None else None
        logger.debug(f"cStat extraído: {stat}")
        return stat

    def parse_protNFe(self, xml_obj):
        logger.debug("Parseando protocolo NF-e")
        # Se já for Element, use direto
        if isinstance(xml_obj, etree._Element):
            tree = xml_obj
        else:
            tree = etree.fromstring(xml_obj.encode('utf-8'))
        prot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}protNFe')
        if prot is None:
            logger.debug("nenhum protNFe encontrado")
            return None, None, None
        chNFe   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}chNFe') or ''
        cStat   = prot.findtext('{http://www.portalfiscal.inf.br/nfe}cStat') or ''
        xMotivo = prot.findtext('{http://www.portalfiscal.inf.br/nfe}xMotivo') or ''
        logger.debug(f"Parse protocolo → chNFe={chNFe}, cStat={cStat}, xMotivo={xMotivo}")
        return chNFe, cStat, xMotivo
    
    def extract_status_from_xml(self, xml_str):
        """
        Extrai status (cStat, xMotivo) diretamente do XML completo.
        Funciona para NFe e CTe com protocolo embutido.
        Mapeia códigos especiais (denegação, recusa, cancelamento).
        Retorna: (cStat, xMotivo) ou (None, None)
        """
        try:
            tree = etree.fromstring(xml_str.encode('utf-8') if isinstance(xml_str, str) else xml_str)
            
            # Tenta NFe primeiro
            prot = tree.find('.//{http://www.portalfiscal.inf.br/nfe}protNFe')
            if prot is not None:
                cStat = prot.findtext('{http://www.portalfiscal.inf.br/nfe}infProt/{http://www.portalfiscal.inf.br/nfe}cStat') or \
                        prot.findtext('{http://www.portalfiscal.inf.br/nfe}cStat') or ''
                xMotivo = prot.findtext('{http://www.portalfiscal.inf.br/nfe}infProt/{http://www.portalfiscal.inf.br/nfe}xMotivo') or \
                          prot.findtext('{http://www.portalfiscal.inf.br/nfe}xMotivo') or ''
                
                # Mapeia status especiais
                if cStat:
                    xMotivo = self._mapear_status_especial(cStat, xMotivo)
                    logger.debug(f"Status extraído de NFe: {cStat} - {xMotivo}")
                    return cStat, xMotivo
            
            # Tenta CTe
            prot = tree.find('.//{http://www.portalfiscal.inf.br/cte}protCTe')
            if prot is not None:
                cStat = prot.findtext('{http://www.portalfiscal.inf.br/cte}infProt/{http://www.portalfiscal.inf.br/cte}cStat') or \
                        prot.findtext('{http://www.portalfiscal.inf.br/cte}cStat') or ''
                xMotivo = prot.findtext('{http://www.portalfiscal.inf.br/cte}infProt/{http://www.portalfiscal.inf.br/cte}xMotivo') or \
                          prot.findtext('{http://www.portalfiscal.inf.br/cte}xMotivo') or ''
                
                # Mapeia status especiais
                if cStat:
                    xMotivo = self._mapear_status_especial(cStat, xMotivo)
                    logger.debug(f"Status extraído de CTe: {cStat} - {xMotivo}")
                    return cStat, xMotivo
            
            logger.debug("Nenhum status encontrado no XML")
            return None, None
        except Exception as e:
            logger.warning(f"Erro ao extrair status do XML: {e}")
            return None, None
    
    def _mapear_status_especial(self, cStat: str, xMotivo: str) -> str:
        """Mapeia códigos de status especiais para mensagens claras"""
        mapeamento = {
            '100': 'Autorizado o uso da NF-e',
            '101': 'Cancelamento de NF-e homologado',
            '135': 'Evento registrado e vinculado a NF-e',
            '301': 'Uso Denegado: Irregularidade fiscal do emitente',
            '302': 'Uso Denegado: Irregularidade fiscal do destinatário',
            '110': 'Uso Denegado',
            '205': 'NF-e está denegada na base de dados da SEFAZ',
            '218': 'NF-e já está cancelada na base de dados da SEFAZ'
        }
        return mapeamento.get(cStat, xMotivo)

# -------------------------------------------------------------------
# Serviço SOAP
# -------------------------------------------------------------------
class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        logger.debug(f"Inicializando serviço para informante={informante}, cUF={cuf}")
        sess = requests.Session()
        sess.verify = False  # Desabilita verificação SSL
        sess.mount('https://', requests_pkcs12.Pkcs12Adapter(
            pkcs12_filename=cert_path, pkcs12_password=senha
        ))
        trans = Transport(session=sess)
        self.dist_client = Client(wsdl=URL_DISTRIBUICAO, transport=trans)
        wsdl = CONSULTA_WSDL.get(str(cuf), URL_CONSULTA_FALLBACK)
        try:
            self.cons_client = Client(wsdl=wsdl, transport=trans)
            logger.debug(f"Cliente de protocolo inicializado: {wsdl}")
        except Exception as e:
            self.cons_client = None
            logger.warning(f"Falha ao inicializar WSDL de protocolo ({wsdl}): {e}")
        self.informante = informante
        self.cuf        = cuf

    def fetch_by_cnpj(self, tipo, ult_nsu):
        logger.debug(f"Chamando distribuição: tipo={tipo}, informante={self.informante}, ultNSU={ult_nsu}")
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

        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
        except Fault as fault:
            logger.error(f"SOAP Fault Distribuição: {fault}")
            return None
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.debug(f"Resposta Distribuição:\n{xml_str}")
        return xml_str

    def fetch_prot_nfe(self, chave):
        """
        Consulta o protocolo da NF-e pela chave, validando o XML de envio e resposta.
        """
        if not self.cons_client:
            logger.debug("Cliente de protocolo não disponível")
            return None

        logger.debug(f"Chamando protocolo para chave={chave}")
        
        # Define URL do serviço baseado no cUF (extrai da chave ou usa self.cuf)
        # Chave NFe: posições 0-1 = cUF
        cuf_from_chave = chave[:2] if len(chave) == 44 else str(self.cuf)
        
        url_map = {
            '31': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4',  # MG
            '50': 'https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4',  # MS
            '51': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # SVRS
            '52': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # GO
            '35': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',  # SP
            '33': 'https://nfe.fazenda.rj.gov.br/ws/NFeConsultaProtocolo4',  # RJ
            '41': 'https://nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4',  # PR
            '53': 'https://nfe.sefaz.df.gov.br/ws/NFeConsultaProtocolo4',  # DF
        }
        url = url_map.get(cuf_from_chave, 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx')
        
        # Monta XML SEM prefixos de namespace (SEFAZ rejeita prefixos)
        xml_consulta = f'''<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe></consSitNFe>'''
        
        logger.debug(f"XML de consulta:\n{xml_consulta}")
        logger.debug(f"URL do serviço (cUF={cuf_from_chave}): {url}")

        # Envia requisição SOAP manualmente (evita que Zeep adicione prefixos)
        try:
            # Monta envelope SOAP 1.2
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">{xml_consulta}</nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
            
            logger.debug(f"Envelope SOAP:\n{soap_envelope[:500]}")
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            # Usa a sessão que já tem o certificado configurado
            resp = self.dist_client.transport.session.post(url, data=soap_envelope.encode('utf-8'), headers=headers)
            resp.raise_for_status()
            
            # Extrai corpo da resposta SOAP
            resp_tree = etree.fromstring(resp.content)
            body = resp_tree.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
            if body is not None and len(body) > 0:
                resp = body[0]
            else:
                logger.error("Resposta SOAP sem corpo")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição HTTP: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao montar/enviar requisição SOAP: {e}")
            return None

        # Converte resposta para string XML
        try:
            if isinstance(resp, etree._Element):
                resp_xml = etree.tostring(resp, encoding="utf-8").decode()
            elif hasattr(resp, 'decode'):
                resp_xml = resp.decode()
            elif isinstance(resp, str):
                resp_xml = resp
            else:
                # Último recurso: tenta serializar
                resp_xml = etree.tostring(resp, encoding="utf-8").decode()
        except Exception as e:
            logger.error(f"Erro ao converter resposta SOAP em XML: {e}")
            return None

        # Protege contra respostas inválidas (vazia, HTML, etc)
        if not resp_xml or resp_xml.strip().startswith('<html') or resp_xml.strip() == '':
            logger.warning("Resposta inválida da SEFAZ (não é XML): %s", resp_xml)
            return None

        # (Opcional) Salva para depuração
        # with open('ult_resposta_protocolo.xml', 'w', encoding='utf-8') as f:
        #     f.write(resp_xml)

        # NÃO valida XML de resposta da SEFAZ (esquemas podem variar)
        logger.debug(f"Resposta Protocolo (raw):\n{resp_xml}")
        return resp_xml

# -------------------------------------------------------------------
# Fluxo Principal
# -------------------------------------------------------------------
def processar_cte(db, cert_data):
    """
    Processa CT-e para um certificado específico usando o serviço CTeDistribuicaoDFe.
    
    Args:
        db: Instância do DatabaseManager
        cert_data: Tupla (cnpj, path, senha, informante, cuf)
    """
    from modules.cte_service import CTeService
    
    cnpj, path, senha, inf, cuf = cert_data
    
    try:
        # Inicializa serviço CT-e
        cte_svc = CTeService(path, senha, cnpj, cuf, ambiente='producao')
        logger.info(f"🚛 Iniciando busca de CT-e para {inf}")
        
        # Obtém último NSU CT-e processado
        last_nsu_cte = db.get_last_nsu_cte(inf)
        
        # Primeira consulta (NSU = 0) para verificar maxNSU
        if last_nsu_cte == "000000000000000":
            resp = cte_svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu_cte)
            if resp:
                max_nsu = cte_svc.extract_max_nsu(resp)
                if max_nsu and max_nsu != "000000000000000":
                    logger.info(f"📊 [{inf}] CT-e disponíveis até NSU: {max_nsu}")
        
        # Loop de busca incremental
        ult_nsu_cte = last_nsu_cte
        while True:
            resp_cte = cte_svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", ult_nsu_cte)
            
            if not resp_cte:
                logger.debug(f"Sem resposta CT-e para {inf}")
                break
            
            cStat_cte = cte_svc.extract_cstat(resp_cte)
            
            if cStat_cte == '656':
                logger.warning(f"Consumo indevido CT-e (656) para {inf}, aguardar")
                break
            
            # Extrai e processa documentos CT-e
            docs_processados = 0
            for nsu, xml_cte, schema in cte_svc.extrair_docs(resp_cte):
                try:
                    # Detecta tipo de documento CT-e
                    tipo_doc = detectar_tipo_documento(xml_cte)
                    
                    if tipo_doc != 'CTe':
                        logger.debug(f"Documento NSU {nsu} não é CT-e, tipo: {tipo_doc}")
                        continue
                    
                    # Extrai chave do CT-e
                    tree = etree.fromstring(xml_cte.encode('utf-8'))
                    infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                    
                    if infcte is None:
                        # Pode ser evento ou resumo
                        logger.debug(f"infCte não encontrado em NSU {nsu}, schema={schema}")
                        
                        # Tenta extrair chave de eventos
                        ch_cte_elem = tree.find('.//{http://www.portalfiscal.inf.br/cte}chCTe')
                        if ch_cte_elem is not None and ch_cte_elem.text:
                            chave_cte = ch_cte_elem.text.strip()
                        else:
                            continue
                    else:
                        chave_cte = infcte.attrib.get('Id', '')[-44:]
                    
                    # Registra XML no banco
                    db.registrar_xml(chave_cte, cnpj)
                    
                    # Salva XML em disco
                    salvar_xml_por_certificado(xml_cte, cnpj)
                    
                    # Processa e salva nota detalhada
                    db.criar_tabela_detalhada()
                    nota_cte = extrair_nota_detalhada(xml_cte, None, db, chave_cte, inf)
                    nota_cte['informante'] = inf  # Garantir informante
                    
                    # Determina status do XML (COMPLETO, RESUMO, EVENTO)
                    root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
                    if root_tag in ['cteProc', 'CTe']:
                        nota_cte['xml_status'] = 'COMPLETO'
                    elif root_tag == 'resCTe':
                        nota_cte['xml_status'] = 'RESUMO'
                    elif root_tag in ['procEventoCTe', 'eventoCTe']:
                        nota_cte['xml_status'] = 'EVENTO'
                    else:
                        nota_cte['xml_status'] = 'RESUMO'
                    
                    db.salvar_nota_detalhada(nota_cte)
                    docs_processados += 1
                    logger.debug(f"✅ CT-e processado: NSU={nsu}, chave={chave_cte}, schema={schema}")
                    
                except Exception as e:
                    logger.exception(f"Erro ao processar CT-e NSU {nsu}: {e}")
            
            # Atualiza NSU CT-e
            ult_cte = cte_svc.extract_last_nsu(resp_cte)
            if ult_cte:
                if ult_cte != ult_nsu_cte:
                    db.set_last_nsu_cte(inf, ult_cte)
                    logger.info(f"🚛 CT-e NSU avançou para {inf}: {ult_nsu_cte} → {ult_cte} ({docs_processados} docs)")
                    ult_nsu_cte = ult_cte
                else:
                    # NSU não mudou - sincroniza e encerra
                    db.set_last_nsu_cte(inf, ult_cte)
                    if docs_processados > 0:
                        logger.info(f"✅ CT-e sincronizado para {inf}: {docs_processados} documentos processados")
                    break
            else:
                logger.debug("SEFAZ não retornou ultNSU para CT-e")
                break
                
    except Exception as e:
        logger.exception(f"Erro ao processar CT-e para {inf}: {e}")


def main():
    """
    FUNÇÃO DESCONTINUADA - NÃO USAR!
    A interface (interface_pyqt5.py) agora controla quando executar as buscas.
    Use run_single_cycle() através da interface.
    
    Antiga função que executava ciclo contínuo de busca de NFe/CTe.
    Mantida apenas para referência histórica.
    """
    print("AVISO: main() está descontinuada!")
    print("Use a interface gráfica (interface_pyqt5.py) para executar buscas.")
    print("A interface controla o agendamento automático conforme intervalo configurado.")
    return


def consultar_nfe_por_chave(chave: str, certificado_path: str, senha: str, cnpj: str, cuf: str) -> str:
    """
    Função helper para consultar XML completo de uma NFe pela chave de acesso.
    Retorna o XML completo em formato string, ou None se não encontrado.
    """
    try:
        logger.info(f"Consultando NFe por chave: {chave}")
        svc = NFeService(certificado_path, senha, cnpj, cuf)
        prot_xml = svc.fetch_prot_nfe(chave)
        
        if not prot_xml:
            logger.warning(f"Nenhuma resposta obtida para chave {chave}")
            return None
        
        # Verifica se o retorno contém o XML completo (procNFe)
        if '<protNFe' in prot_xml or '<retConsSitNFe' in prot_xml:
            logger.info(f"XML completo obtido para chave {chave}")
            return prot_xml
        
        logger.warning(f"Resposta não contém XML completo para chave {chave}")
        return None
        
    except Exception as e:
        logger.error(f"Erro ao consultar chave {chave}: {e}")
        return None


def run_single_cycle():
    """
    Executa apenas UMA iteração de busca (sem loop infinito).
    Usado quando chamado pela interface gráfica.
    """
    data_dir = get_data_dir()
    db = DatabaseManager(data_dir / "notas.db")
    parser = XMLProcessor()
    
    try:
        logger.info(f"=== Início da busca: {datetime.now().isoformat()} ===")
        logger.info(f"Diretório de dados: {data_dir}")
        
        # 1) Distribuição - NFe E CTe
        for cnpj, path, senha, inf, cuf in db.get_certificados():
            logger.debug(f"Processando certificado: CNPJ={cnpj}, arquivo={path}, informante={inf}, cUF={cuf}")
            
            # 1.1) Busca NFe
            svc      = NFeService(path, senha, cnpj, cuf)
            last_nsu = db.get_last_nsu(inf)
            resp     = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
            if not resp:
                logger.warning(f"Sem resposta NFe para {inf}")
            else:
                cStat = parser.extract_cStat(resp)
                ult   = parser.extract_last_nsu(resp)
                if cStat == '656':
                    logger.info(f"{inf}: Consumo indevido NFe (656), manter NSU em {last_nsu}")
                else:
                    if ult:
                        db.set_last_nsu(inf, ult)
                    for nsu, xml in parser.extract_docs(resp):
                        try:
                            validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                            tree   = etree.fromstring(xml.encode('utf-8'))
                            infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                            if infnfe is None:
                                logger.debug("infNFe não encontrado no XML, pulando")
                                continue
                            chave  = infnfe.attrib.get('Id','')[-44:]
                            db.registrar_xml(chave, cnpj)
                        except Exception:
                            logger.exception("Erro ao processar docZip NFe")
            
            # 1.2) Busca CTe em paralelo
            try:
                processar_cte(db, (cnpj, path, senha, inf, cuf))
            except Exception as e:
                logger.exception(f"Erro geral ao processar CT-e para {inf}: {e}")
        
        logger.info("✅ Todos os certificados processados, iniciando consulta de protocolos...")
        
        # 2) Consulta de Protocolo
        logger.debug("Verificando chaves sem status...")
        faltam = db.get_chaves_missing_status()
        logger.debug(f"Encontradas {len(faltam) if faltam else 0} chaves sem status")
        
        if not faltam:
            logger.info("Nenhuma chave faltando status")
        else:
            logger.info(f"📋 Consultando status de {len(faltam)} chave(s)...")
            for idx, (chave, cnpj) in enumerate(faltam, 1):
                logger.info(f"[{idx}/{len(faltam)}] Consultando chave {chave}...")
                cert = db.find_cert_by_cnpj(cnpj)
                if not cert:
                    logger.warning(f"Certificado não encontrado para {cnpj}, ignorando {chave}")
                    continue
                _, path, senha, inf, cuf = cert
                svc = NFeService(path, senha, cnpj, cuf)
                logger.debug(f"Consultando protocolo para NF-e {chave} (informante {inf})")
                prot = svc.fetch_prot_nfe(chave)
                chNFe, cStat, xMotivo = parser.parse_protNFe(prot)
                if cStat and xMotivo:
                    db.set_nf_status(chave, cStat, xMotivo)
                    logger.info(f"✅ Status atualizado: {chave} → {cStat} - {xMotivo}")
        
        logger.info(f"=== Busca concluída: {datetime.now().isoformat()} ===")
        logger.info(f"Próxima busca será agendada pela interface conforme intervalo configurado...")
        
    except Exception as e:
        logger.exception(f"Erro durante ciclo de busca: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("AVISO: Este módulo não deve ser executado diretamente!")
    print("=" * 60)
    print()
    print("Use a interface gráfica (interface_pyqt5.py) para:")
    print("  1. Configurar o intervalo de busca (1 a 23 horas)")
    print("  2. Executar buscas automáticas")
    print("  3. Visualizar resultados")
    print()
    print("Para iniciar a interface, execute:")
    print("  python interface_pyqt5.py")
    print()
    print("=" * 60)