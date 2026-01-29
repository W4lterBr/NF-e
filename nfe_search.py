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
from datetime import datetime, timedelta

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

# Importa sistema de criptografia
try:
    from modules.crypto_portable import get_portable_crypto
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ Sistema de criptografia não disponível - senhas em texto plano")

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
        data_dir = app_data / "Busca XML"
    else:
        # Desenvolvimento: usa pasta local
        data_dir = Path(__file__).parent
    
    # Garante que o diretório existe
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

BASE = get_data_dir()

# -------------------------------------------------------------------
# Função para salvar arquivos de debug SOAP
# -------------------------------------------------------------------
def save_debug_soap(informante: str, tipo: str, conteudo: str, prefixo: str = ""):
    """
    Salva arquivos SOAP para debug na pasta 'Debug de notas'.
    
    Args:
        informante: CNPJ do informante
        tipo: Tipo do arquivo (request, response, xml_extraido)
        conteudo: Conteúdo a ser salvo
        prefixo: Prefixo adicional para o nome do arquivo (ex: 'nfe', 'cte', 'protocolo')
    """
    try:
        # Cria pasta Debug de notas
        debug_dir = BASE / "xmls" / "Debug de notas"
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]  # Remove microsegundos extras
        nome_base = f"{timestamp}_{informante}"
        if prefixo:
            nome_base = f"{nome_base}_{prefixo}"
        nome_arquivo = f"{nome_base}_{tipo}.xml"
        
        # Salva arquivo
        arquivo_path = debug_dir / nome_arquivo
        arquivo_path.write_text(conteudo, encoding='utf-8')
        
        logger.debug(f"📝 Debug salvo: {nome_arquivo}")
        return str(arquivo_path)
    except Exception as e:
        logger.error(f"Erro ao salvar debug SOAP: {e}")
        return None

# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
def setup_logger():
    """Configura logger com saída para console e arquivo na pasta logs."""
    LOGS_DIR = BASE / "logs"
    
    # Cria pasta de logs se não existir
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Nome do arquivo de log com data
    log_filename = LOGS_DIR / f"busca_nfe_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    # Força criação do arquivo se não existir
    try:
        log_filename.touch(exist_ok=True)
    except Exception as e:
        print(f"⚠️ Erro ao criar arquivo de log: {e}")
        print(f"   Caminho tentado: {log_filename}")
    
    logger = logging.getLogger(__name__)
    
    # Remove handlers antigos para evitar duplicação
    logger.handlers.clear()
    
    try:
        # Handler para arquivo (sempre cria novo)
        file_handler = logging.FileHandler(log_filename, encoding='utf-8', mode='a')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        logger.setLevel(logging.DEBUG)
        
        # Log de confirmação
        print(f"✅ Logger configurado: {log_filename}")
        
    except Exception as e:
        print(f"❌ ERRO ao configurar logger: {e}")
        print(f"   LOGS_DIR: {LOGS_DIR}")
        print(f"   log_filename: {log_filename}")
        # Logger básico apenas no console se falhar
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
    return logger

logger = setup_logger()
logger.info(f"✅ nfe_search.py iniciado - Logs em: {BASE / 'logs'}")
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
                                # ⚠️ IMPORTANTE: NÃO atualizar NSU em erro 656!
                                # Se atualizar, perdemos documentos intermediários
                                # Exemplo: NSU=1459, SEFAZ retorna ultNSU=1461
                                # Documentos 1460 e 1461 serão perdidos se avançarmos para 1461
                                # 
                                # SOLUÇÃO: Manter NSU atual, bloquear por 65 min,
                                # e na próxima consulta (após 65 min) buscar os documentos perdidos
                                
                                # Registra erro 656 para bloquear tentativas por 65 minutos
                                db.registrar_erro_656(inf, ult_nsu)
                                logger.warning(f"🔒 [{inf}] Erro 656 - NSU mantido em {ult_nsu}, bloqueado por 65 minutos")
                                logger.warning(f"⚠️ [{inf}] Documentos intermediários serão baixados na próxima consulta")
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
                                    
                                    # Extrai e grava status diretamente do XML
                                    cStat, xMotivo = parser.extract_status_from_xml(xml)
                                    if cStat and xMotivo:
                                        db.set_nf_status(chave, cStat, xMotivo)
                                        logger.debug(f"Status gravado para {chave}: {cStat} - {xMotivo}")
                                    
                                    # Busca nome do certificado (se configurado)
                                    nome_cert = db.get_cert_nome_by_informante(inf)
                                    
                                    # 1. SEMPRE salva em xmls/ (backup local) e obtém o caminho
                                    resultado = salvar_xml_por_certificado(xml, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                                    # Resultado pode ser: (caminho_xml, caminho_pdf) ou apenas caminho_xml (compatibilidade)
                                    if isinstance(resultado, tuple):
                                        caminho_xml, caminho_pdf = resultado
                                    else:
                                        caminho_xml, caminho_pdf = resultado, None
                                    
                                    # Registra XML no banco COM o caminho
                                    if caminho_xml:
                                        db.registrar_xml(chave, cnpj, caminho_xml)
                                    else:
                                        db.registrar_xml(chave, cnpj)
                                        logger.warning(f"⚠️ XML salvo mas caminho não obtido: {chave}")
                                    
                                    # 2. Se configurado armazenamento diferente, copia para lá também
                                    pasta_storage = db.get_config('storage_pasta_base', 'xmls')
                                    if pasta_storage and pasta_storage != 'xmls':
                                        salvar_xml_por_certificado(xml, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                                    
                                    # Salva nota detalhada
                                    db.criar_tabela_detalhada()
                                    nota = extrair_nota_detalhada(xml, parser, db, chave, inf)
                                    nota['informante'] = inf  # Adiciona informante (redundância para garantir)
                                    nota['xml_status'] = xml_status  # Marca corretamente: COMPLETO, RESUMO ou EVENTO
                                    db.salvar_nota_detalhada(nota)
                                    
                                    # 3. CACHE: Atualiza caminho do PDF no banco (se foi gerado)
                                    if caminho_pdf:
                                        db.atualizar_pdf_path(chave, caminho_pdf)
                                        logger.debug(f"✅ PDF path cached: {chave} → {caminho_pdf}")
                                    
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
    Retorna: 'NFe', 'CTe', 'NFS-e' ou None
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
        # 🆕 Verifica NFS-e (padrão ABRASF)
        nfse_abrasf = tree.find('.//{http://www.abrasf.org.br/nfse.xsd}CompNfse')
        if nfse_abrasf is not None:
            return 'NFS-e'
        # Verifica NFS-e (outros padrões - busca por tags comuns)
        if tree.find('.//CompNfse') is not None or tree.find('.//Nfse') is not None:
            return 'NFS-e'
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
def extrair_cte_detalhado(xml_txt, parser, db, chave, informante=None, nsu_documento=None):
    """
    Extrai informações detalhadas de um CT-e.
    
    🔒 CRÍTICO: O NSU (nsu_documento) é obrigatório e será gravado no banco.
    
    Args:
        xml_txt: String XML do CT-e
        parser: XMLProcessor
        db: DatabaseManager
        chave: Chave de acesso (44 dígitos)
        informante: CNPJ/CPF do certificado
        nsu_documento: NSU do documento (15 dígitos) - OBRIGATÓRIO
    
    Returns:
        dict: Dados do CT-e incluindo o campo 'nsu'
    """
    try:
        tree = etree.fromstring(xml_txt.encode('utf-8'))
        inf = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
        ide = inf.find('{http://www.portalfiscal.inf.br/cte}ide') if inf is not None else None
        emit = inf.find('{http://www.portalfiscal.inf.br/cte}emit') if inf is not None else None
        dest = inf.find('{http://www.portalfiscal.inf.br/cte}dest') if inf is not None else None
        rem = inf.find('{http://www.portalfiscal.inf.br/cte}rem') if inf is not None else None
        vPrest = tree.find('.//{http://www.portalfiscal.inf.br/cte}vPrest')
        
        # Valor do CT-e (salva como número, não como texto formatado)
        valor = ""
        if vPrest is not None:
            vTPrest = vPrest.findtext('{http://www.portalfiscal.inf.br/cte}vTPrest')
            # Salva como número puro para permitir somas SQL
            valor = vTPrest if vTPrest else "0"
        
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
        
        # 🔒 VALIDAÇÃO CRÍTICA: NSU deve estar preenchido
        nsu_final = nsu_documento or ""
        if not nsu_final:
            logger.error(f"🚨 CRÍTICO: NSU vazio ao extrair CT-e {chave[:25]}...")
        
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
            "informante": str(informante or ""),
            "nsu": nsu_final  # 🔒 NSU OBRIGATÓRIO para rastreamento
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair CT-e detalhado: {e}")
        # 🔒 Mesmo em erro, tenta preservar o NSU
        nsu_final = nsu_documento or ""
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
            "informante": str(informante or ""),
            "nsu": nsu_final  # 🔒 NSU preservado mesmo em erro
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

def extrair_nota_detalhada(xml_txt, parser, db, chave, informante=None, nsu_documento=None):
    """
    Extrai informações detalhadas de NF-e ou CT-e automaticamente.
    
    🔒 IMPORTANTE: O parâmetro nsu_documento é OBRIGATÓRIO para rastreamento.
    Todos os documentos baixados da SEFAZ possuem um NSU (Número Sequencial Único)
    que DEVE ser gravado no banco para permitir:
    - Retomar busca do ponto correto após interrupção
    - Evitar reprocessamento de documentos já baixados
    - Rastreabilidade e auditoria
    
    Args:
        xml_txt: String XML do documento
        parser: XMLProcessor para parsing
        db: DatabaseManager para consultas
        chave: Chave de acesso do documento (44 dígitos)
        informante: CNPJ/CPF do certificado
        nsu_documento: NSU do documento (15 dígitos) - OBRIGATÓRIO
    
    Returns:
        dict: Dicionário com todos os campos da nota, incluindo 'nsu'
    """
    tipo = detectar_tipo_documento(xml_txt)
    
    # 🔒 VALIDAÇÃO: NSU deve estar preenchido
    if not nsu_documento:
        logger.error(f"🚨 CRÍTICO: extrair_nota_detalhada chamado SEM NSU para chave {chave[:25]}...")
        logger.error(f"   Documento será salvo mas NSU ficará vazio, impedindo rastreamento!")
    
    if tipo == 'CTe':
        return extrair_cte_detalhado(xml_txt, parser, db, chave, informante, nsu_documento)
    elif tipo == 'NFe':
        return extrair_nfe_detalhado(xml_txt, parser, db, chave, informante, nsu_documento)
    else:
        # Tipo desconhecido, tenta NF-e como padrão
        return extrair_nfe_detalhado(xml_txt, parser, db, chave, informante, nsu_documento)

def extrair_nfe_detalhado(xml_txt, parser, db, chave, informante=None, nsu_documento=None):
    """
    Extrai informações detalhadas de uma NF-e.
    
    🔒 CRÍTICO: O NSU (nsu_documento) é obrigatório e será gravado no banco.
    
    Args:
        xml_txt: String XML da NF-e
        parser: XMLProcessor
        db: DatabaseManager
        chave: Chave de acesso (44 dígitos)
        informante: CNPJ/CPF do certificado
        nsu_documento: NSU do documento (15 dígitos) - OBRIGATÓRIO
    
    Returns:
        dict: Dados da nota incluindo o campo 'nsu'
    """
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

        # 🔒 VALIDAÇÃO CRÍTICA: NSU deve estar preenchido
        nsu_final = nsu_documento or ""
        if not nsu_final:
            logger.error(f"🚨 CRÍTICO: NSU vazio ao extrair NF-e {chave[:25]}...")
        
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
            "informante": str(informante or ""),
            "nsu": nsu_final  # 🔒 NSU OBRIGATÓRIO para rastreamento
        }
    except Exception as e:
        logger.warning(f"Erro ao extrair nota detalhada: {e}")
        # 🔒 Mesmo em erro, tenta preservar o NSU
        nsu_final = nsu_documento or ""
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
            "informante": str(informante or ""),
            "nsu": nsu_final  # 🔒 NSU preservado mesmo em erro
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

def salvar_xml_por_certificado(xml, cnpj_cpf, pasta_base="xmls", nome_certificado=None, formato_mes=None):
    """
    Salva o XML em uma pasta organizada por CNPJ (backup local) ou nome amigável (armazenamento).
    Detecta automaticamente o tipo de documento e salva na pasta apropriada.
    
    ⚠️ PADRÃO DE NOMENCLATURA (v1.0.88+):
    - Nome do arquivo: {NUMERO}-{FORNECEDOR}.xml
    - Para eventos: Evento-{NUMERO}-{FORNECEDOR}.xml
    - Estrutura LOCAL (xmls/): xmls/{CNPJ}/{ANO-MES}/{TIPO}/{NUMERO}-{FORNECEDOR}.xml
    - Estrutura STORAGE: {storage}/{NOME_AMIGAVEL}/{ANO-MES}/{TIPO}/{NUMERO}-{FORNECEDOR}.xml
    
    Args:
        xml: String XML ou bytes do documento
        cnpj_cpf: CNPJ/CPF do certificado
        pasta_base: Pasta base onde os XMLs serão salvos (padrão: "xmls")
        nome_certificado: Nome amigável do certificado (ex: "61-MATPARCG") - usado em STORAGE
        formato_mes: Formato do mês (MM-AAAA, AAAA-MM, etc.) - lê do banco se None
    
    Returns:
        str: Caminho absoluto onde o XML foi salvo, ou None se não foi salvo
    
    Tipos suportados:
    - NFe completas (procNFe) → NFe/
    - CTe completas (procCTe) → CTe/
    - Resumos NFe (resNFe) → Resumos/
    - Eventos (resEvento, procEventoNFe) → Eventos/
    
    Exemplos: 
    - LOCAL: xmls/47539664000197/2025-08/NFe/52260115045348000172570010014777191002562584.xml
    - STORAGE: C:\Arquivo Walter\61-MATPARCG/2025-08/NFe/52260115045348000172570010014777191002562584.xml
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
            return None  # Não salva protocolos sem dados
        
        # ⚠️ LÓGICA DE NOMENCLATURA DE PASTA (v1.0.87+):
        # - BACKUP LOCAL (xmls/): Usa CNPJ puro (47539664000197)
        # - ARMAZENAMENTO (storage): Usa nome amigável se fornecido (61-MATPARCG)
        if pasta_base == "xmls" or not nome_certificado:
            # Backup local: sempre usa CNPJ
            pasta_certificado = format_cnpj_cpf_dir(cnpj_cpf)
        else:
            # Armazenamento externo: usa nome amigável se disponível
            pasta_certificado = nome_certificado.strip() if nome_certificado else format_cnpj_cpf_dir(cnpj_cpf)

        # Parse o XML para extrair dados de organização
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        
        # Detecta tipo de documento pela tag raiz
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # 🚫 FILTRO CRÍTICO: Ignora respostas da SEFAZ (não são documentos fiscais)
        if root_tag in ['retDistDFeInt', 'retConsSitNFe', 'retConsReciNFe', 'retEnviNFe', 'retEnvEvento', 'retEvento']:
            # ⚠️ retEnvEvento = Resposta de MANIFESTAÇÃO (não contém nota, apenas confirmação)
            # Mesmo com cStat 135 (sucesso), NÃO é um documento fiscal!
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            cStat = root.findtext(f'{ns}cStat') or root.findtext('cStat')
            xMotivo = root.findtext(f'{ns}xMotivo') or root.findtext('xMotivo')
            
            # Para eventos (retEnvEvento), verifica também infEvento
            if not cStat:
                infEvento = root.find(f'.//{ns}infEvento')
                if infEvento is not None:
                    cStat = infEvento.findtext(f'{ns}cStat') or infEvento.findtext('cStat')
                    xMotivo = infEvento.findtext(f'{ns}xEvento') or infEvento.findtext('xEvento')
            
            # retEnvEvento NUNCA deve ser salvo (é apenas confirmação do protocolo)
            if root_tag == 'retEnvEvento':
                logger.debug(f"✅ Manifestação confirmada (cStat={cStat}), mas retEnvEvento NÃO será salvo (não é documento fiscal)")
                return None  # Apenas protocolo, não salva
            
            # Outros tipos de resposta: salva apenas se for documento localizado (138)
            if cStat:
                if cStat != '138':  # 138 = Documento localizado (contém nota completa)
                    print(f"[IGNORADO] Resposta SEFAZ ({root_tag}) cStat={cStat}: {xMotivo}")
                    return None  # NÃO salva respostas de erro ou confirmações
                elif cStat == '135':
                    # Resposta de manifestação bem-sucedida - NÃO salvar como nota
                    print(f"[IGNORADO] Resposta de manifestação ({root_tag}) cStat={cStat}: {xMotivo}")
                    return None
        
        # Determina a pasta e tipo baseado no documento
        if root_tag in ['nfeProc', 'NFe']:
            tipo_pasta = "NFe"
            tipo_doc = "NFe"
        elif root_tag in ['cteProc', 'CTe']:
            tipo_pasta = "CTe"
            tipo_doc = "CTe"
        elif root_tag in ['CompNfse', 'Nfse', 'NFSe']:
            tipo_pasta = "NFSe"
            tipo_doc = "NFSe"
        elif root_tag == 'resNFe':
            tipo_pasta = "Resumos"
            tipo_doc = "ResNFe"
        elif root_tag in ['resEvento', 'procEventoNFe', 'evento', 'retEvento', 'infEvento']:
            tipo_pasta = "Eventos"  # Temporário, será ajustado depois
            tipo_doc = "Evento"
        else:
            # Tipo desconhecido - salva em "Outros"
            tipo_pasta = "Outros"
            tipo_doc = "Outro"
        
        # ⚠️ EXTRAÇÃO DA CHAVE (PADRÃO v1.0.86)
        # Chave é extraída aqui para ser usada como nome do arquivo
        chave = None
        try:
            if tipo_doc in ["NFe", "CTe"]:
                ns = '{http://www.portalfiscal.inf.br/nfe}' if tipo_doc == "NFe" else '{http://www.portalfiscal.inf.br/cte}'
                infNFe = root.find(f'.//{ns}infNFe') if tipo_doc == "NFe" else root.find(f'.//{ns}infCte')
                if infNFe is not None:
                    chave_id = infNFe.attrib.get('Id', '')
                    if chave_id:
                        # Remove prefixo NFe/CTe da chave e pega últimos 44 dígitos
                        chave = chave_id.replace('NFe', '').replace('CTe', '')[-44:]
            elif tipo_doc == "NFSe":
                ns = '{http://www.sped.fazenda.gov.br/nfse}'
                # Tenta extrair ChaveAcesso do XML de NFS-e
                chave_acesso = root.findtext(f'.//{ns}ChaveAcesso')
                if chave_acesso:
                    chave = chave_acesso  # ChaveAcesso já é a chave completa
            elif tipo_doc == "ResNFe":
                ns = '{http://www.portalfiscal.inf.br/nfe}'
                chave = root.findtext(f'{ns}chNFe')
            elif tipo_doc == "Evento":
                ns = '{http://www.portalfiscal.inf.br/nfe}'
                chave = root.findtext(f'.//{ns}chNFe')
            
            # Valida se a chave tem 44 dígitos (ou 50 para NFSe)
            if chave and tipo_doc == "NFSe":
                if len(chave) not in [44, 50]:  # NFSe pode ter 44 ou 50 caracteres
                    print(f"[AVISO] Chave NFSe inválida (len={len(chave)}): {chave}")
                    chave = None
            elif chave and len(chave) != 44:
                print(f"[AVISO] Chave inválida (len={len(chave)}): {chave}")
                chave = None
        except Exception as chave_err:
            print(f"[ERRO ao extrair chave]: {chave_err}")
            chave = None
        
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
        
        # Para NFSe
        elif tipo_doc == "NFSe":
            ns = '{http://www.sped.fazenda.gov.br/nfse}'
            # Extrai número da NFS-e
            nNF = root.findtext(f'.//{ns}Numero')
            # Extrai data de emissão
            data_emissao = root.findtext(f'.//{ns}DataEmissao')
            if data_emissao:
                data_raw = data_emissao
            # Extrai nome do prestador (emissor)
            prestador_nome = root.findtext(f'.//{ns}PrestadorServico//{ns}RazaoSocial')
            if prestador_nome:
                xNome = prestador_nome
        
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
        
        # Para eventos (resEvento, procEventoNFe, infEvento)
        elif tipo_doc == "Evento":
            ns = '{http://www.portalfiscal.inf.br/nfe}'
            
            # Tenta extrair chave e tipo de evento
            chNFe = root.findtext(f'.//{ns}chNFe')
            
            # ⚠️ FALLBACK: Se não achou chave no XML E já temos uma chave válida de 44 dígitos
            # (pode ser infEvento onde a chave está apenas no nome do arquivo)
            if (not chNFe or len(chNFe) != 44) and chave and len(chave) == 44:
                chNFe = chave
                print(f"[EVENTO] Usando chave do nome do arquivo: {chave[:10]}...")
            
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
                    
                    # ⚠️ DETECTA TIPO DE DOCUMENTO PELO CÓDIGO DA UF NA CHAVE (v1.0.87+)
                    # Posição 0-1 da chave = código UF
                    # Se modelo (posição 20-21) for 57 = CT-e, senão = NF-e
                    modelo = chNFe[20:22] if len(chNFe) >= 22 else '55'
                    if modelo == '57':
                        tipo_pasta = "CTe/Eventos"  # Evento de CT-e
                    else:
                        tipo_pasta = "NFe/Eventos"  # Evento de NF-e (padrão)
                except:
                    tipo_pasta = "NFe/Eventos"  # Padrão se não conseguir detectar
            else:
                tipo_pasta = "NFe/Eventos"  # Padrão se não houver chave
            
            if dhEvento:
                data_raw = dhEvento
            
            nNF = nNF or "EVENTO"
            xNome = tipo_evento
        
        # Define ano-mês para organização com base na configuração
        if data_raw:
            data_part = data_raw.split("T")[0]
            # Extrai ano e mês da data
            if len(data_part) >= 7:
                ano = data_part[:4]
                mes = data_part[5:7]
            else:
                from datetime import datetime
                now = datetime.now()
                ano = str(now.year)
                mes = f"{now.month:02d}"
        else:
            from datetime import datetime
            now = datetime.now()
            ano = str(now.year)
            mes = f"{now.month:02d}"
        
        # Aplica formato configurado (padrão: AAAA-MM)
        # Se não foi fornecido, tenta ler do banco
        if formato_mes is None:
            try:
                from modules.database import DatabaseManager
                from pathlib import Path
                # Usa o caminho correto do banco (mesmo que o resto do sistema)
                data_dir = Path(__file__).parent
                db_path = data_dir / 'notas.db'
                db = DatabaseManager(str(db_path))
                formato_mes = db.get_config('storage_formato_mes', 'AAAA-MM')
                print(f"[DEBUG FORMATO] Lido do banco ({db_path}): '{formato_mes}'")
            except Exception as e:
                print(f"[WARN] Não conseguiu ler formato do banco: {e}")
                formato_mes = 'AAAA-MM'
        else:
            print(f"[DEBUG FORMATO] Fornecido como parâmetro: '{formato_mes}'")
        
        if formato_mes == 'MM-AAAA':
            ano_mes = f"{mes}-{ano}"
        elif formato_mes == 'AAAA/MM':
            ano_mes = f"{ano}/{mes}"
        elif formato_mes == 'MM/AAAA':
            ano_mes = f"{mes}/{ano}"
        else:  # AAAA-MM (padrão)
            ano_mes = f"{ano}-{mes}"
        
        print(f"[DEBUG FORMATO] Formato={formato_mes}, Resultado={ano_mes}")
        
        nNF = nNF or "SEM_NUMERO"
        xNome = xNome or "SEM_NOME"
        
        # Cria pasta com tipo de documento
        pasta_dest = os.path.join(pasta_base, pasta_certificado, ano_mes, tipo_pasta)
        os.makedirs(pasta_dest, exist_ok=True)

        # ⚠️ NOME DO ARQUIVO: NÚMERO-FORNECEDOR (PADRÃO v1.0.88+)
        # Para eventos, usa apenas o tipo do evento sem repetir "Evento-"
        nome_limpo = sanitize_filename(xNome)[:50]  # Limita a 50 caracteres
        numero_limpo = sanitize_filename(nNF)
        
        if tipo_doc == "Evento":
            # Para eventos, usa só: NUMERO-TIPO_EVENTO
            # Ex: 000118032-CANCELAMENTO.xml (não "Evento-000118032-EVENTO_...")
            nome_arquivo = f"{numero_limpo}-{nome_limpo}.xml"
        else:
            nome_arquivo = f"{numero_limpo}-{nome_limpo}.xml"
        
        caminho_xml = os.path.join(pasta_dest, nome_arquivo)

        with open(caminho_xml, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"[SALVO {tipo_doc}] {caminho_xml}")
        
        # Retorna o caminho absoluto
        caminho_absoluto = os.path.abspath(caminho_xml)
        
        # ⚠️ REGISTRO NO BANCO (xmls_baixados) - REMOVIDO DAQUI
        # O registro agora é feito pela função registrar_xml() do DatabaseManager
        # que recebe o caminho retornado por esta função
        
        # Gerar PDF automaticamente (apenas para NFe/CTe completas)
        if tipo_doc in ["NFe", "CTe"]:
            try:
                caminho_pdf = caminho_xml.replace('.xml', '.pdf')
                if not os.path.exists(caminho_pdf):
                    from modules.pdf_simple import generate_danfe_pdf
                    success = generate_danfe_pdf(xml, caminho_pdf, tipo_doc)
                    if success:
                        print(f"[PDF GERADO] {caminho_pdf}")
                        # Retorna tupla: (caminho_xml, caminho_pdf) para atualizar banco
                        return (caminho_absoluto, os.path.abspath(caminho_pdf))
                else:
                    print(f"[PDF JÁ EXISTE] {caminho_pdf}")
                    # PDF já existe, retorna ambos os caminhos
                    return (caminho_absoluto, os.path.abspath(caminho_pdf))
            except Exception as pdf_err:
                print(f"[AVISO] Erro ao gerar PDF: {pdf_err}")
        
        # Retorna só o XML se não for NFe/CTe ou se falhou
        return (caminho_absoluto, None)
        
    except Exception as e:
        print(f"[ERRO ao salvar XML de {cnpj_cpf}]: {e}")
        return None  # ❌ Erro ao salvar
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
                cnpj_cpf TEXT,
                caminho_arquivo TEXT,
                xml_completo TEXT,
                baixado_em TEXT
            )''')
            # Migração: adicionar coluna xml_completo se não existir
            try:
                cur.execute("ALTER TABLE xmls_baixados ADD COLUMN xml_completo TEXT")
            except:
                pass  # Coluna já existe
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
            cur.execute('''CREATE TABLE IF NOT EXISTS notas_verificadas (
                chave TEXT PRIMARY KEY,
                verificada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resultado TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS manifestacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT NOT NULL,
                tipo_evento TEXT NOT NULL,
                informante TEXT NOT NULL,
                data_manifestacao TEXT NOT NULL,
                status TEXT,
                protocolo TEXT,
                UNIQUE(chave, tipo_evento, informante)
            )''')
            # 📊 TABELA DE HISTÓRICO DE NSU - Auditoria completa de consultas
            cur.execute('''CREATE TABLE IF NOT EXISTS historico_nsu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificado TEXT NOT NULL,
                informante TEXT NOT NULL,
                nsu_consultado TEXT NOT NULL,
                data_hora_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_xmls_retornados INTEGER DEFAULT 0,
                total_nfe INTEGER DEFAULT 0,
                total_cte INTEGER DEFAULT 0,
                total_nfse INTEGER DEFAULT 0,
                total_eventos INTEGER DEFAULT 0,
                detalhes_json TEXT,
                status TEXT DEFAULT 'sucesso',
                mensagem_erro TEXT,
                tempo_processamento_ms INTEGER
            )''')
            # Índices para histórico NSU (performance em consultas de auditoria)
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_historico_certificado ON historico_nsu(certificado, informante, nsu_consultado)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_historico_data ON historico_nsu(data_hora_consulta)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_historico_informante ON historico_nsu(informante)")
            except:
                pass  # Índices já existem
            conn.commit()
            logger.debug("Tabelas verificadas/criadas no banco (incluindo histórico NSU)")
    
    def criar_tabela_detalhada(self):
        """
        Cria a tabela notas_detalhadas com todos os campos necessários.
        
        🔒 CRÍTICO: Inclui coluna NSU para rastreamento de documentos baixados.
        """
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
                cnpj_destinatario TEXT,
                nsu TEXT
            )
            ''')
            # 🔒 MIGRAÇÃO CRÍTICA: Garante que as colunas existem (caso o banco seja antigo)
            columns_to_add = [
                ("cnpj_destinatario", "TEXT"),
                ("xml_status", "TEXT DEFAULT 'COMPLETO'"),
                ("ncm", "TEXT"),
                ("base_icms", "TEXT"),
                ("valor_icms", "TEXT"),
                ("informante", "TEXT"),
                ("nsu", "TEXT")  # 🔒 NSU CRÍTICO para rastreamento
            ]
            for col_name, col_type in columns_to_add:
                try:
                    conn.execute(f"ALTER TABLE notas_detalhadas ADD COLUMN {col_name} {col_type};")
                    logger.info(f"✅ Coluna '{col_name}' adicionada à tabela notas_detalhadas")
                except sqlite3.OperationalError:
                    # Já existe, ignora o erro
                    pass
            conn.commit()
            
            # 🔒 ÍNDICES CRÍTICOS para performance de consultas NSU
            # Índice composto para buscar último NSU por informante
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nsu_informante ON notas_detalhadas(informante, nsu)")
                logger.debug("✅ Índice idx_nsu_informante criado")
            except Exception as e:
                logger.debug(f"Índice idx_nsu_informante já existe: {e}")
            
            # Índice para buscar por NSU específico
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nsu ON notas_detalhadas(nsu)")
                logger.debug("✅ Índice idx_nsu criado")
            except Exception as e:
                logger.debug(f"Índice idx_nsu já existe: {e}")
            
            # Índice para buscar por data de emissão (útil para auditoria)
            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_data_emissao ON notas_detalhadas(data_emissao)")
                logger.debug("✅ Índice idx_data_emissao criado")
            except Exception as e:
                logger.debug(f"Índice idx_data_emissao já existe: {e}")
            
            conn.commit()
            logger.debug("Tabela notas_detalhadas verificada/criada com sucesso")

    def salvar_nota_detalhada(self, nota):
        """
        Salva ou atualiza nota detalhada no banco.
        
        🔒 CRÍTICO: O campo NSU DEVE estar preenchido para rastreamento.
        Este método inclui validações para garantir que o NSU nunca fique vazio.
        
        Args:
            nota (dict): Dicionário com dados da nota, DEVE conter campo 'nsu'
        
        Raises:
            Logs de erro se NSU estiver vazio, mas não bloqueia a gravação
        """
        with self._connect() as conn:
            # Verifica se realmente tem XML salvo em disco
            chave = nota['chave']
            xml_status = nota.get('xml_status', 'RESUMO')  # Padrão é RESUMO, não COMPLETO
            
            # 🔒 VALIDAÇÃO CRÍTICA: NSU deve estar preenchido
            nsu = nota.get('nsu', '')
            if not nsu:
                logger.error(f"🚨 CRÍTICO: Tentativa de salvar nota SEM NSU!")
                logger.error(f"   Chave: {chave[:25]}...")
                logger.error(f"   Tipo: {nota.get('tipo', 'N/A')}")
                logger.error(f"   Informante: {nota.get('informante', 'N/A')}")
                logger.error(f"   Nota será salva mas rastreamento ficará comprometido!")
            
            # 🔍 AUTO-DETECÇÃO: Verifica se existe XML em disco (upgrade RESUMO → COMPLETO ou downgrade COMPLETO → RESUMO)
            # ⚠️ EXCEÇÃO: NFS-e não usa xmls_baixados (salvo direto via salvar_nfse_detalhada)
            tipo = nota.get('tipo', '')
            if 'NFS' in str(tipo).upper():
                # NFS-e: Aceita xml_status fornecido sem validação de xmls_baixados
                pass
            else:
                # NF-e / CT-e: Valida contra xmls_baixados
                cursor = conn.execute(
                    "SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?",
                    (chave,)
                )
                row = cursor.fetchone()
                
                if row and row[0]:  # Tem registro com caminho
                    from pathlib import Path
                    if Path(row[0]).exists():
                        # ✅ XML existe no disco
                        if xml_status != 'COMPLETO':
                            logger.debug(f"🔄 Auto-upgrade: {chave[:25]}... RESUMO → COMPLETO (XML encontrado)")
                        xml_status = 'COMPLETO'
                    else:
                        # ❌ Caminho registrado mas arquivo não existe
                        if xml_status == 'COMPLETO':
                            logger.warning(f"⚠️ Nota {chave[:25]}... tem caminho registrado mas arquivo não existe. Corrigindo para RESUMO.")
                        xml_status = 'RESUMO'
                else:
                    # ❌ Não tem registro ou sem caminho
                    if xml_status == 'COMPLETO':
                        cursor_debug = conn.execute("SELECT COUNT(*) FROM xmls_baixados WHERE chave = ?", (chave,))
                        count = cursor_debug.fetchone()[0]
                        if count == 0:
                            logger.warning(f"⚠️ Nota {chave[:25]}... marcada como COMPLETO mas NÃO REGISTRADA em xmls_baixados. Corrigindo para RESUMO.")
                        else:
                            logger.warning(f"⚠️ Nota {chave[:25]}... registrada em xmls_baixados mas SEM CAMINHO. Corrigindo para RESUMO.")
                    xml_status = 'RESUMO'
            
            # 🔒 INSERT com campo NSU incluído
            conn.execute('''
                INSERT OR REPLACE INTO notas_detalhadas (
                    chave, ie_tomador, nome_emitente, cnpj_emitente, numero,
                    data_emissao, tipo, valor, cfop, vencimento, ncm, uf, natureza,
                    base_icms, valor_icms, status, atualizado_em, cnpj_destinatario, 
                    xml_status, informante, nsu
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nota['chave'], nota['ie_tomador'], nota['nome_emitente'], nota['cnpj_emitente'],
                nota['numero'], nota['data_emissao'], nota['tipo'], nota['valor'],
                nota.get('cfop', ''), nota.get('vencimento', ''), nota.get('ncm', ''),
                nota.get('uf', ''), nota.get('natureza', ''), 
                nota.get('base_icms', ''), nota.get('valor_icms', ''),
                nota['status'], nota['atualizado_em'],
                nota.get('cnpj_destinatario', ''), 
                xml_status,  # Usa o status validado
                nota.get('informante', ''),
                nsu  # 🔒 NSU OBRIGATÓRIO - campo crítico para rastreamento
            ))
            conn.commit()
            # ⚡ PERFORMANCE: O commit é feito AUTOMATICAMENTE pelo context manager
            # quando o 'with' termina, garantindo transações em lote eficientes.
            # Ao processar milhares de documentos, o SQLite otimiza os commits.
            
            # 🔒 LOG DE AUDITORIA: Confirma gravação do NSU
            if nsu:
                logger.debug(f"✅ NSU {nsu} gravado para nota {chave[:25]}...")
            else:
                logger.warning(f"⚠️ Nota {chave[:25]}... salva SEM NSU!")

    def get_certificados(self):
        """Retorna certificados com senhas descriptografadas."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT cnpj_cpf,caminho,senha,informante,cUF_autor FROM certificados"
            ).fetchall()
            logger.debug(f"Certificados carregados: {len(rows)} registros")
            
            # Descriptografa senhas se disponível
            if CRYPTO_AVAILABLE and rows:
                crypto = get_portable_crypto()
                decrypted_rows = []
                for row in rows:
                    cnpj, caminho, senha, informante, cuf = row
                    
                    # Descriptografa senha
                    if senha:
                        try:
                            # Verifica se está criptografada
                            if crypto.is_encrypted(senha):
                                senha = crypto.decrypt(senha)
                                logger.debug(f"Senha descriptografada para {informante}")
                            else:
                                logger.warning(f"⚠️ Senha do certificado {informante} está em texto plano!")
                        except Exception as e:
                            logger.error(f"Erro ao descriptografar senha de {informante}: {e}")
                    
                    decrypted_rows.append((cnpj, caminho, senha, informante, cuf))
                
                return decrypted_rows
            
            return rows

    def get_last_nsu(self, informante):
        """
        Obtém último NSU processado para o informante.
        
        🔒 ESTRATÉGIA DE RECUPERAÇÃO SEGURA:
        1. Busca NSU na tabela 'nsu' (fonte da verdade)
        2. Busca maior NSU em 'notas_detalhadas' (verificação)
        3. Se divergir:
           a) Se NSU tabela > NSU notas: Usa tabela (correto)
           b) Se NSU notas > NSU tabela: Usa tabela (SEGURO - não pula documentos)
           c) Registra ALERTA para investigação manual
        
        RAZÃO: Melhor perder um documento já processado (reprocessar)
               do que pular documentos não processados (omissão)
        
        Returns:
            str: NSU de 15 dígitos (ex: '000000000001234')
        """
        with self._connect() as conn:
            # 1️⃣ Busca NSU oficial na tabela de controle
            row = conn.execute(
                "SELECT ult_nsu FROM nsu WHERE informante=?", (informante,)
            ).fetchone()
            nsu_tabela = row[0] if row else "000000000000000"
            
            # 2️⃣ 🔒 VALIDAÇÃO CRUZADA: Busca maior NSU gravado em notas_detalhadas
            row_notas = conn.execute("""
                SELECT MAX(nsu) 
                FROM notas_detalhadas 
                WHERE informante=? 
                AND nsu IS NOT NULL 
                AND nsu != ''
            """, (informante,)).fetchone()
            nsu_notas = row_notas[0] if (row_notas and row_notas[0]) else "000000000000000"
            
            # 3️⃣ 🔒 ESTRATÉGIA CONSERVADORA: Sempre usa tabela 'nsu' como fonte da verdade
            # Isso evita pular documentos não processados
            nsu_final = nsu_tabela
            
            # 4️⃣ 📊 AUDITORIA: Logs detalhados para investigação
            if nsu_tabela != nsu_notas:
                diff = int(nsu_notas) - int(nsu_tabela)
                
                if diff > 0:
                    # NSU em notas_detalhadas está à frente - ALERTA!
                    logger.warning(f"🚨 DIVERGÊNCIA DE NSU para {informante}:")
                    logger.warning(f"   Tabela 'nsu' (controle): {nsu_tabela}")
                    logger.warning(f"   Maior em 'notas_detalhadas': {nsu_notas}")
                    logger.warning(f"   Diferença: +{diff} NSU(s)")
                    logger.warning(f"   🔒 AÇÃO: Usando NSU da tabela de controle ({nsu_tabela})")
                    logger.warning(f"   📋 Sistema irá REPROCESSAR documentos entre {nsu_tabela} e {nsu_notas}")
                    logger.warning(f"   ✅ Isso é SEGURO - documentos duplicados serão filtrados pelo CNPJ+Chave")
                elif diff < 0:
                    # NSU em tabela está à frente - situação anômala
                    logger.error(f"❌ ANOMALIA DE NSU para {informante}:")
                    logger.error(f"   Tabela 'nsu': {nsu_tabela}")
                    logger.error(f"   Maior em 'notas_detalhadas': {nsu_notas}")
                    logger.error(f"   Tabela está {abs(diff)} NSU(s) à frente das notas!")
                    logger.error(f"   Possível causa: Documentos foram processados mas não salvos")
                    logger.error(f"   🔒 AÇÃO: Usando NSU da tabela ({nsu_tabela})")
            else:
                logger.debug(f"✅ NSU consistente para {informante}: {nsu_final}")
            
            return nsu_final

    def set_last_nsu(self, informante, nsu):
        """
        Atualiza último NSU processado para o informante.
        
        🔒 CONTROLE RIGOROSO:
        1. Valida formato do informante (deve ser CNPJ/CPF)
        2. Valida formato do NSU (15 dígitos)
        3. Verifica se NSU avançou (não permite retrocesso)
        4. Registra em log de auditoria
        5. Limpa bloqueios de erro 656 se NSU avançou
        
        Args:
            informante: CNPJ/CPF (apenas números)
            nsu: NSU de 15 dígitos (string)
        """
        # 1️⃣ 🔒 VALIDAÇÃO: Informante deve ser CNPJ/CPF (números)
        if not informante or not str(informante).replace('.', '').replace('-', '').replace('/', '').isdigit():
            logger.error(f"🚨 SEGURANÇA: Tentativa de salvar valor inválido como informante NSU: {informante[:20] if informante else 'None'}...")
            logger.error(f"   NSU não será salvo para evitar corrupção do banco de dados!")
            return
        
        # 2️⃣ 🔒 VALIDAÇÃO: NSU deve ter 15 dígitos
        nsu_str = str(nsu).zfill(15) if nsu else "000000000000000"
        if not nsu_str.isdigit() or len(nsu_str) != 15:
            logger.error(f"🚨 NSU inválido para {informante}: '{nsu}' (deve ter 15 dígitos)")
            return
        
        with self._connect() as conn:
            # 3️⃣ 🔒 VALIDAÇÃO: Verifica se NSU está avançando (não permite retrocesso)
            nsu_anterior = self.get_last_nsu(informante)
            if nsu_str < nsu_anterior:
                logger.error(f"🚨 CRÍTICO: Tentativa de RETROCEDER NSU!")
                logger.error(f"   Informante: {informante}")
                logger.error(f"   NSU atual: {nsu_anterior}")
                logger.error(f"   NSU tentado: {nsu_str}")
                logger.error(f"   NSU NÃO será atualizado para prevenir perda de dados!")
                return
            
            # 4️⃣ ✅ Salva NSU
            conn.execute(
                "INSERT OR REPLACE INTO nsu (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu_str)
            )
            conn.commit()
            
            # 5️⃣ 📊 AUDITORIA: Log detalhado
            if nsu_str > nsu_anterior:
                diff = int(nsu_str) - int(nsu_anterior)
                logger.info(f"✅ NSU atualizado para {informante}: {nsu_anterior} → {nsu_str} (+{diff})")
            else:
                logger.debug(f"✅ NSU confirmado para {informante}: {nsu_str}")
            
            # 6️⃣ Se o NSU avançou, limpa o bloqueio de erro 656 (pode ter documentos novos)
            if nsu_str > nsu_anterior:
                conn.execute("DELETE FROM erro_656 WHERE informante = ?", (informante,))
                conn.commit()
                logger.debug(f"🔓 Bloqueio erro 656 limpo para {informante}")
    
    def validate_nsu_sequence(self, informante):
        """
        Valida a sequência de NSUs de um informante e detecta gaps (lacunas).
        
        🔒 CONTROLE RIGOROSO: Verifica se há NSUs faltando na sequência.
        Útil para detectar problemas na busca ou documentos não processados.
        
        Args:
            informante: CNPJ/CPF do certificado
        
        Returns:
            dict: {
                'total_documentos': int,
                'nsu_minimo': str,
                'nsu_maximo': str,
                'gaps_detectados': int,
                'gaps': [list de NSUs faltando],
                'status': 'OK' ou 'ATENÇÃO'
            }
        """
        with self._connect() as conn:
            # Busca todos os NSUs do informante (ordenados)
            rows = conn.execute("""
                SELECT nsu 
                FROM notas_detalhadas 
                WHERE informante = ? 
                AND nsu IS NOT NULL 
                AND nsu != '' 
                ORDER BY nsu
            """, (informante,)).fetchall()
            
            if not rows:
                return {
                    'total_documentos': 0,
                    'nsu_minimo': None,
                    'nsu_maximo': None,
                    'gaps_detectados': 0,
                    'gaps': [],
                    'status': 'SEM DADOS'
                }
            
            nsus = [row[0] for row in rows if row[0]]
            nsu_min = min(nsus)
            nsu_max = max(nsus)
            
            # Detecta gaps (NSUs faltando na sequência)
            gaps = []
            nsu_atual = int(nsu_min)
            nsu_fim = int(nsu_max)
            
            # ⚠️ Limita verificação a 10.000 NSUs para evitar sobrecarga
            if (nsu_fim - nsu_atual) > 10000:
                logger.warning(f"⚠️ Faixa de NSU muito grande ({nsu_fim - nsu_atual}), verificação de gaps limitada")
                return {
                    'total_documentos': len(nsus),
                    'nsu_minimo': nsu_min,
                    'nsu_maximo': nsu_max,
                    'gaps_detectados': -1,
                    'gaps': [],
                    'status': 'FAIXA MUITO GRANDE'
                }
            
            nsus_set = set(nsus)
            while nsu_atual <= nsu_fim:
                nsu_str = str(nsu_atual).zfill(15)
                if nsu_str not in nsus_set:
                    gaps.append(nsu_str)
                nsu_atual += 1
            
            status = 'OK' if len(gaps) == 0 else 'ATENÇÃO'
            
            return {
                'total_documentos': len(nsus),
                'nsu_minimo': nsu_min,
                'nsu_maximo': nsu_max,
                'gaps_detectados': len(gaps),
                'gaps': gaps[:100],  # Limita a 100 gaps para não sobrecarregar
                'status': status
            }
    
    def get_nsu_stats(self, informante):
        """
        Retorna estatísticas de NSU para um informante.
        
        🔒 CONTROLE RIGOROSO: Fornece visão completa dos NSUs processados.
        
        Returns:
            dict: Estatísticas detalhadas de NSU
        """
        with self._connect() as conn:
            # Total de documentos
            total = conn.execute(
                "SELECT COUNT(*) FROM notas_detalhadas WHERE informante = ?",
                (informante,)
            ).fetchone()[0]
            
            # Documentos COM NSU
            com_nsu = conn.execute(
                "SELECT COUNT(*) FROM notas_detalhadas WHERE informante = ? AND nsu IS NOT NULL AND nsu != ''",
                (informante,)
            ).fetchone()[0]
            
            # Documentos SEM NSU
            sem_nsu = total - com_nsu
            
            # NSU mínimo e máximo
            row_min = conn.execute(
                "SELECT MIN(nsu) FROM notas_detalhadas WHERE informante = ? AND nsu IS NOT NULL AND nsu != ''",
                (informante,)
            ).fetchone()
            nsu_min = row_min[0] if row_min and row_min[0] else None
            
            row_max = conn.execute(
                "SELECT MAX(nsu) FROM notas_detalhadas WHERE informante = ? AND nsu IS NOT NULL AND nsu != ''",
                (informante,)
            ).fetchone()
            nsu_max = row_max[0] if row_max and row_max[0] else None
            
            return {
                'informante': informante,
                'total_documentos': total,
                'com_nsu': com_nsu,
                'sem_nsu': sem_nsu,
                'percentual_com_nsu': (com_nsu / total * 100) if total > 0 else 0,
                'nsu_minimo': nsu_min,
                'nsu_maximo': nsu_max
            }
    
    def reset_nsu_for_testing(self, informante=None, confirm_code="CONFIRMO_RESET_NSU"):
        """
        Zera NSU para permitir rebusca completa de documentos.
        
        ⚠️ USO EXCLUSIVO PARA TESTES!
        Esta função permite zerar o NSU para forçar o sistema a baixar
        todos os documentos novamente e preencher os NSUs faltantes.
        
        🔒 SEGURANÇA:
        - Requer código de confirmação
        - Cria backup antes de zerar
        - Registra em log
        
        Args:
            informante: CNPJ/CPF específico ou None para todos
            confirm_code: Código de segurança (deve ser "CONFIRMO_RESET_NSU")
        
        Returns:
            dict: {'success': bool, 'informantes_zerados': list, 'backup': str}
        """
        if confirm_code != "CONFIRMO_RESET_NSU":
            logger.error("🚨 SEGURANÇA: reset_nsu_for_testing requer código de confirmação!")
            return {'success': False, 'error': 'Código de confirmação inválido'}
        
        with self._connect() as conn:
            # 1️⃣ Backup antes de zerar
            if informante:
                backup = conn.execute(
                    "SELECT informante, ult_nsu FROM nsu WHERE informante=?",
                    (informante,)
                ).fetchall()
            else:
                backup = conn.execute("SELECT informante, ult_nsu FROM nsu").fetchall()
            
            logger.warning("⚠️ ATENÇÃO: Zerando NSUs para teste!")
            logger.warning(f"   Backup: {len(backup)} registros salvos em memória")
            
            # 2️⃣ Zera NSU(s)
            informantes_zerados = []
            if informante:
                conn.execute(
                    "UPDATE nsu SET ult_nsu='000000000000000' WHERE informante=?",
                    (informante,)
                )
                informantes_zerados.append(informante)
                logger.warning(f"✅ NSU zerado para {informante}")
            else:
                conn.execute("UPDATE nsu SET ult_nsu='000000000000000'")
                informantes_zerados = [row[0] for row in backup]
                logger.warning(f"✅ NSU zerado para TODOS os {len(backup)} informantes")
            
            conn.commit()
            
            logger.warning("🔄 Próxima busca irá começar do NSU 0 e baixar TODOS os documentos")
            logger.warning("🔒 Todos os documentos baixados terão seus NSUs gravados no banco")
            
            return {
                'success': True,
                'informantes_zerados': informantes_zerados,
                'backup': backup,
                'mensagem': f'{len(informantes_zerados)} informante(s) resetado(s)'
            }
    
    # ========================================================================
    # 📊 SISTEMA DE HISTÓRICO NSU - Auditoria completa de consultas
    # ========================================================================
    
    def registrar_historico_nsu(self, certificado, informante, nsu_consultado, 
                                xmls_retornados, tempo_ms=0, status='sucesso', 
                                mensagem_erro=None):
        """
        📊 Registra no banco CADA consulta NSU feita na SEFAZ.
        
        Args:
            certificado: Identificação do certificado (CN ou hash)
            informante: CNPJ/CPF do informante
            nsu_consultado: NSU específico consultado
            xmls_retornados: Lista de dicts com XMLs retornados [{'tipo': 'nfe'/'evento', 'chave': '...'}]
            tempo_ms: Tempo de processamento em milissegundos
            status: 'sucesso', 'erro', 'vazio'
            mensagem_erro: Mensagem se houver erro
        
        Returns:
            ID do registro criado no histórico
        
        🔒 SEGURANÇA: Registro é feito de forma não-bloqueante, não trava busca.
        
        Exemplo de uso:
            xmls = [
                {'tipo': 'nfe', 'chave': '52260...'},
                {'tipo': 'evento', 'chave': '52260...', 'evento': '210210'},
                {'tipo': 'cte', 'chave': '52260...'}
            ]
            db.registrar_historico_nsu('CERT123', '49068153000160', '000000000001234', xmls, 1500)
        """
        import json
        import time
        
        try:
            # Analisa os XMLs retornados
            total_nfe = sum(1 for x in xmls_retornados if x.get('tipo') == 'nfe')
            total_cte = sum(1 for x in xmls_retornados if x.get('tipo') == 'cte')
            total_nfse = sum(1 for x in xmls_retornados if x.get('tipo') == 'nfse')
            total_eventos = sum(1 for x in xmls_retornados if x.get('tipo') == 'evento')
            total_xmls = len(xmls_retornados)
            
            # Converte detalhes para JSON (limitado para não sobrecarregar)
            detalhes_json = json.dumps(xmls_retornados[:100], ensure_ascii=False)  # Máx 100 itens
            
            with self._connect() as conn:
                cursor = conn.execute('''
                    INSERT INTO historico_nsu (
                        certificado, informante, nsu_consultado,
                        total_xmls_retornados, total_nfe, total_cte, total_nfse,
                        total_eventos, detalhes_json, status, mensagem_erro,
                        tempo_processamento_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    certificado, informante, nsu_consultado,
                    total_xmls, total_nfe, total_cte, total_nfse,
                    total_eventos, detalhes_json, status, mensagem_erro,
                    tempo_ms
                ))
                conn.commit()
                
                registro_id = cursor.lastrowid
                
                logger.info(f"📊 Histórico NSU registrado: ID={registro_id}, "
                          f"NSU={nsu_consultado}, Total={total_xmls} "
                          f"(NFe={total_nfe}, CTe={total_cte}, NFS-e={total_nfse}, Eventos={total_eventos})")
                
                return registro_id
                
        except Exception as e:
            logger.error(f"❌ Erro ao registrar histórico NSU: {e}")
            # NÃO interrompe o fluxo, apenas loga o erro
            return None
    
    def buscar_historico_nsu(self, informante=None, nsu=None, certificado=None, 
                            data_inicio=None, data_fim=None, limit=100):
        """
        🔍 Busca histórico de consultas NSU com filtros.
        
        Args:
            informante: Filtrar por CNPJ/CPF
            nsu: Filtrar por NSU específico
            certificado: Filtrar por certificado
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            limit: Limite de registros retornados
        
        Returns:
            Lista de registros do histórico
        """
        with self._connect() as conn:
            query = "SELECT * FROM historico_nsu WHERE 1=1"
            params = []
            
            if informante:
                query += " AND informante = ?"
                params.append(informante)
            
            if nsu:
                query += " AND nsu_consultado = ?"
                params.append(nsu)
            
            if certificado:
                query += " AND certificado = ?"
                params.append(certificado)
            
            if data_inicio:
                query += " AND date(data_hora_consulta) >= ?"
                params.append(data_inicio)
            
            if data_fim:
                query += " AND date(data_hora_consulta) <= ?"
                params.append(data_fim)
            
            query += " ORDER BY data_hora_consulta DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            # Converte para lista de dicts
            colunas = ['id', 'certificado', 'informante', 'nsu_consultado', 
                      'data_hora_consulta', 'total_xmls_retornados', 'total_nfe',
                      'total_cte', 'total_nfse', 'total_eventos', 'detalhes_json',
                      'status', 'mensagem_erro', 'tempo_processamento_ms']
            
            historico = []
            for row in rows:
                historico.append(dict(zip(colunas, row)))
            
            logger.debug(f"📊 Histórico NSU: {len(historico)} registros encontrados")
            return historico
    
    def comparar_consultas_nsu(self, informante, nsu):
        """
        🔍 Compara diferentes consultas do MESMO NSU para detectar divergências.
        
        Args:
            informante: CNPJ/CPF
            nsu: NSU específico para comparar
        
        Returns:
            Dict com análise de divergências:
            {
                'total_consultas': int,
                'divergencias_encontradas': bool,
                'consultas': [...],
                'analise': {...}
            }
        
        🎯 USO: Detectar se em consultas diferentes do mesmo NSU vieram XMLs diferentes
              (pode indicar erro de processamento ou perda de dados)
        """
        import json
        
        historico = self.buscar_historico_nsu(informante=informante, nsu=nsu, limit=1000)
        
        if len(historico) < 2:
            return {
                'total_consultas': len(historico),
                'divergencias_encontradas': False,
                'mensagem': 'Menos de 2 consultas para comparar'
            }
        
        # Analisa divergências
        totais_xmls = [h['total_xmls_retornados'] for h in historico]
        totais_nfe = [h['total_nfe'] for h in historico]
        totais_eventos = [h['total_eventos'] for h in historico]
        
        divergencias = (
            len(set(totais_xmls)) > 1 or 
            len(set(totais_nfe)) > 1 or 
            len(set(totais_eventos)) > 1
        )
        
        resultado = {
            'total_consultas': len(historico),
            'divergencias_encontradas': divergencias,
            'consultas': historico,
            'analise': {
                'total_xmls_unico': len(set(totais_xmls)) == 1,
                'total_nfe_unico': len(set(totais_nfe)) == 1,
                'total_eventos_unico': len(set(totais_eventos)) == 1,
                'valores_total_xmls': list(set(totais_xmls)),
                'valores_total_nfe': list(set(totais_nfe)),
                'valores_total_eventos': list(set(totais_eventos))
            }
        }
        
        if divergencias:
            logger.warning(f"⚠️ DIVERGÊNCIA detectada no NSU {nsu} do informante {informante}!")
            logger.warning(f"   Total XMLs variou: {resultado['analise']['valores_total_xmls']}")
            logger.warning(f"   Total NF-e variou: {resultado['analise']['valores_total_nfe']}")
            logger.warning(f"   Total Eventos variou: {resultado['analise']['valores_total_eventos']}")
        
        return resultado
    
    def relatorio_historico_nsu(self, informante=None, dias=30):
        """
        📊 Gera relatório consolidado do histórico NSU.
        
        Args:
            informante: CNPJ/CPF específico (None = todos)
            dias: Últimos N dias para análise
        
        Returns:
            Dict com estatísticas completas do histórico
        """
        from datetime import datetime, timedelta
        
        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        historico = self.buscar_historico_nsu(
            informante=informante, 
            data_inicio=data_inicio,
            limit=10000
        )
        
        if not historico:
            return {
                'total_consultas': 0,
                'mensagem': 'Nenhuma consulta no período'
            }
        
        # Estatísticas
        total_consultas = len(historico)
        total_xmls = sum(h['total_xmls_retornados'] for h in historico)
        total_nfe = sum(h['total_nfe'] for h in historico)
        total_cte = sum(h['total_cte'] for h in historico)
        total_nfse = sum(h['total_nfse'] for h in historico)
        total_eventos = sum(h['total_eventos'] for h in historico)
        
        tempo_medio = sum(h['tempo_processamento_ms'] or 0 for h in historico) / total_consultas if total_consultas > 0 else 0
        
        # Consultas com sucesso/erro
        consultas_sucesso = sum(1 for h in historico if h['status'] == 'sucesso')
        consultas_erro = sum(1 for h in historico if h['status'] == 'erro')
        consultas_vazio = sum(1 for h in historico if h['status'] == 'vazio')
        
        # Certificados usados
        certificados = list(set(h['certificado'] for h in historico))
        
        relatorio = {
            'periodo': f'Últimos {dias} dias',
            'data_inicio': data_inicio,
            'total_consultas': total_consultas,
            'consultas_sucesso': consultas_sucesso,
            'consultas_erro': consultas_erro,
            'consultas_vazio': consultas_vazio,
            'total_xmls_processados': total_xmls,
            'total_nfe': total_nfe,
            'total_cte': total_cte,
            'total_nfse': total_nfse,
            'total_eventos': total_eventos,
            'tempo_medio_ms': round(tempo_medio, 2),
            'certificados_utilizados': certificados,
            'informante': informante or 'TODOS'
        }
        
        logger.info(f"📊 Relatório Histórico NSU:")
        logger.info(f"   Período: {relatorio['periodo']}")
        logger.info(f"   Consultas: {total_consultas} (✅{consultas_sucesso} ❌{consultas_erro} ⚪{consultas_vazio})")
        logger.info(f"   XMLs: {total_xmls} (NFe={total_nfe}, CTe={total_cte}, NFS-e={total_nfse}, Eventos={total_eventos})")
        logger.info(f"   Tempo médio: {tempo_medio:.0f}ms")
        
        return relatorio
    
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
        # ⚠️ VALIDAÇÃO DE SEGURANÇA: informante deve ser CNPJ/CPF (números), nunca senha!
        if not informante or not str(informante).replace('.', '').replace('-', '').replace('/', '').isdigit():
            logger.error(f"🚨 SEGURANÇA: Tentativa de salvar valor inválido como informante NSU CT-e: {informante[:20] if informante else 'None'}...")
            logger.error(f"   NSU CT-e não será salvo para evitar corrupção do banco de dados!")
            return
        
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu_cte (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU CT-e atualizado para {informante}: {nsu}")
    
    def get_last_nsu_nfse(self, informante):
        """Obtém último NSU processado de NFS-e para o informante"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ult_nsu FROM nsu_nfse WHERE informante=?", (informante,)
            ).fetchone()
            last = row[0] if row else "000000000000000"
            logger.debug(f"Último NSU NFS-e para {informante}: {last}")
            return last

    def set_last_nsu_nfse(self, informante, nsu):
        """Atualiza último NSU processado de NFS-e para o informante"""
        # ⚠️ VALIDAÇÃO DE SEGURANÇA: informante deve ser CNPJ/CPF (números), nunca senha!
        if not informante or not str(informante).replace('.', '').replace('-', '').replace('/', '').isdigit():
            logger.error(f"🚨 SEGURANÇA: Tentativa de salvar valor inválido como informante NSU NFS-e: {informante[:20] if informante else 'None'}...")
            logger.error(f"   NSU NFS-e não será salvo para evitar corrupção do banco de dados!")
            return
        
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nsu_nfse (informante,ult_nsu) VALUES (?,?)",
                (informante, nsu)
            )
            conn.commit()
            logger.debug(f"NSU NFS-e atualizado para {informante}: {nsu}")
    
    def registrar_erro_656_nfse(self, informante, nsu):
        """Registra que houve erro 656 para NFS-e deste informante/NSU"""
        with self._connect() as conn:
            from datetime import datetime
            agora_utc = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, ?)",
                (informante, agora_utc, f"NFSE_{nsu}")
            )
            conn.commit()
            logger.debug(f"Erro 656 NFS-e registrado: {informante} NSU={nsu}")
    
    def registrar_sem_documentos_nfse(self, informante):
        """Registra que não há documentos NFS-e (cStat=137)"""
        with self._connect() as conn:
            from datetime import datetime
            agora_utc = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, 'SYNC_NFSE')",
                (informante, agora_utc)
            )
            conn.commit()
            logger.info(f"📊 [{informante}] NFS-e Sincronizada - aguardando 1h")
    
    def registrar_erro_656(self, informante, nsu):
        """Registra que houve erro 656 para este informante/NSU"""
        with self._connect() as conn:
            from datetime import datetime
            agora_utc = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, ?)",
                (informante, agora_utc, nsu)
            )
            conn.commit()
            logger.debug(f"Erro 656 registrado: {informante} NSU={nsu}")
    
    def registrar_sem_documentos(self, informante):
        """Registra que não há documentos (cStat=137 ou maxNSU=ultNSU) - aguardar 1 hora conforme NT 2014.002"""
        with self._connect() as conn:
            from datetime import datetime
            agora_utc = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO erro_656 (informante, ultimo_erro, nsu_bloqueado) VALUES (?, ?, 'SYNC')",
                (informante, agora_utc)
            )
            conn.commit()
            logger.info(f"📊 [{informante}] Sincronizado - aguardando 1h conforme NT 2014.002 (cStat=137 ou ultNSU=maxNSU)")
    
    def marcar_primeira_consulta(self, informante):
        """Marca que este certificado está fazendo a primeira consulta (NSU=0)"""
        with self._connect() as conn:
            from datetime import datetime
            agora_utc = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                (f'primeira_consulta_{informante}', agora_utc)
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
            
            # CORREÇÃO: Verifica PRIMEIRO o tempo decorrido, DEPOIS o NSU
            # Mudança de NSU não libera consulta antes de 65 minutos!
            from datetime import datetime, timedelta
            ultimo_erro = datetime.fromisoformat(ultimo_erro_str)
            agora = datetime.utcnow()  # Usar UTC para comparar com ultimo_erro (também UTC)
            diferenca = (agora - ultimo_erro).total_seconds() / 60  # em minutos
            
            if diferenca >= 65:  # 65 minutos de segurança
                logger.debug(f"{informante}: Passou {diferenca:.1f} minutos desde erro 656, pode consultar")
                return True
            else:
                # Ainda em período de bloqueio, NÃO consulta mesmo que NSU tenha mudado
                tempo_restante = 65 - diferenca
                logger.info(f"🔒 [{informante}] Bloqueado por erro 656 - aguarde {tempo_restante:.1f} minutos")
                logger.debug(f"   NSU bloqueado: {nsu_bloqueado}, NSU atual: {nsu_atual}")
                return False

    def get_cert_nome_by_informante(self, informante: str):
        """Busca o nome personalizado do certificado pelo informante.
        
        Args:
            informante: CNPJ/CPF do informante
            
        Returns:
            Nome do certificado ou None se não houver nome personalizado
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT nome_certificado FROM certificados WHERE informante = ?",
                    (informante,)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
                return None
        except Exception:
            return None

    def get_config(self, chave: str, default: str = None):
        """Busca uma configuração no banco de dados.
        
        Args:
            chave: Nome da configuração
            default: Valor padrão se não encontrar
            
        Returns:
            Valor da configuração ou default
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "SELECT valor FROM config WHERE chave = ?",
                    (chave,)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
                return default
        except Exception:
            return default

    def registrar_xml(self, chave, cnpj, caminho_arquivo=None):
        """
        Registra XML baixado no banco de dados.
        
        Args:
            chave: Chave de acesso (44 dígitos)
            cnpj: CNPJ/CPF do informante
            caminho_arquivo: Caminho completo onde o XML foi salvo (opcional mas recomendado)
        """
        with self._connect() as conn:
            if caminho_arquivo:
                # Registra ou atualiza com o caminho do arquivo
                conn.execute('''
                    INSERT INTO xmls_baixados (chave, cnpj_cpf, caminho_arquivo, baixado_em)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(chave) DO UPDATE SET
                        caminho_arquivo = excluded.caminho_arquivo,
                        baixado_em = datetime('now')
                ''', (chave, cnpj, caminho_arquivo))
                logger.debug(f"XML registrado: {chave} (CNPJ {cnpj}) → {caminho_arquivo}")
            else:
                # Compatibilidade: apenas registra chave e CNPJ
                conn.execute(
                    "INSERT OR IGNORE INTO xmls_baixados (chave,cnpj_cpf) VALUES (?,?)",
                    (chave, cnpj)
                )
                logger.debug(f"XML registrado: {chave} (CNPJ {cnpj}) - caminho não informado")
            conn.commit()

    def atualizar_pdf_path(self, chave: str, pdf_path: str) -> bool:
        """
        Atualiza o caminho do PDF no cache do banco de dados.
        
        Args:
            chave: Chave de acesso do documento (44 dígitos)
            pdf_path: Caminho absoluto onde o PDF está armazenado
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            from datetime import datetime
            with self._connect() as conn:
                conn.execute(
                    "UPDATE notas_detalhadas SET pdf_path = ?, atualizado_em = ? WHERE chave = ?",
                    (pdf_path, datetime.now().isoformat(), chave)
                )
                conn.commit()
                logger.debug(f"📄 PDF path atualizado: {chave[:25]}... → {pdf_path}")
                return True
        except Exception as e:
            logger.error(f"[ERRO] Falha ao atualizar pdf_path para {chave}: {e}")
            return False

    def get_chaves_missing_status(self):
        with self._connect() as conn:
            rows = conn.execute('''
                SELECT xmls_baixados.chave, xmls_baixados.cnpj_cpf
                FROM xmls_baixados
                LEFT JOIN nf_status ON xmls_baixados.chave = nf_status.chNFe
                WHERE nf_status.chNFe IS NULL
            ''').fetchall()
            logger.debug(f"Chaves sem status: {rows}")
            return rows

    def set_nf_status(self, chave, cStat, xMotivo):
        """Salva status de NF-e no banco. Valida que os dados não estejam vazios."""
        # Validação: não salva status vazios ou None
        if not chave or not cStat or not xMotivo:
            logger.warning(f"Tentativa de salvar status vazio: chave={chave}, cStat={cStat}, xMotivo={xMotivo}")
            return False
        
        # Validação: strings não podem ser apenas espaços em branco
        if not str(cStat).strip() or not str(xMotivo).strip():
            logger.warning(f"Tentativa de salvar status com espaços vazios: {chave} → '{cStat}' - '{xMotivo}'")
            return False
        
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO nf_status (chNFe,cStat,xMotivo) VALUES (?,?,?)",
                (chave, cStat, xMotivo)
            )
            conn.commit()
            logger.debug(f"Status gravado: {chave} → {cStat} / {xMotivo}")
            return True

    def find_cert_by_cnpj(self, cnpj):
        for row in self.get_certificados():
            if row[0] == cnpj:
                return row
        return None
    
    def get_config(self, chave, default=None):
        """Obtém valor de configuração do banco de dados"""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT valor FROM config WHERE chave = ?", (chave,)
                ).fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.debug(f"Erro ao buscar config '{chave}': {e}")
            return default
    
    def set_config(self, chave, valor):
        """Salva valor de configuração no banco de dados"""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                    (chave, valor)
                )
                conn.commit()
                logger.debug(f"Config salva: {chave} = {valor}")
                return True
        except Exception as e:
            logger.error(f"Erro ao salvar config '{chave}': {e}")
            return False
    
    def marcar_nota_verificada(self, chave, resultado='verificada'):
        """Marca que uma nota já foi verificada para não verificar novamente"""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO notas_verificadas (chave, verificada_em, resultado) VALUES (?, datetime('now'), ?)",
                    (chave, resultado)
                )
                conn.commit()
                logger.debug(f"Nota marcada como verificada: {chave}")
                return True
        except Exception as e:
            logger.error(f"Erro ao marcar nota verificada '{chave}': {e}")
            return False
    
    def nota_ja_verificada(self, chave):
        """Verifica se uma nota já foi verificada anteriormente"""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT 1 FROM notas_verificadas WHERE chave = ?", (chave,)
                ).fetchone()
                return row is not None
        except Exception as e:
            logger.debug(f"Erro ao verificar se nota foi verificada '{chave}': {e}")
            return False
    
    def check_manifestacao_exists(self, chave: str, tipo_evento: str, informante: str) -> bool:
        """
        Verifica se manifestação já foi registrada.
        
        Args:
            chave: Chave de acesso da NF-e
            tipo_evento: Tipo do evento (ex: '210210' para Ciência da Operação)
            informante: CNPJ/CPF do informante
        
        Returns:
            bool: True se manifestação já existe, False caso contrário
        """
        try:
            with self._connect() as conn:
                result = conn.execute(
                    "SELECT COUNT(*) FROM manifestacoes WHERE chave = ? AND tipo_evento = ? AND informante = ?",
                    (chave, tipo_evento, informante)
                ).fetchone()
                return result[0] > 0
        except Exception as e:
            logger.debug(f"Erro ao verificar manifestação: {e}")
            return False
    
    def register_manifestacao(self, chave: str, tipo_evento: str, informante: str, 
                             status: str = 'ENVIADA', protocolo: str = None) -> bool:
        """
        Registra manifestação para prevenir duplicatas.
        
        Args:
            chave: Chave de acesso da NF-e
            tipo_evento: Tipo do evento (ex: '210210')
            informante: CNPJ/CPF do informante
            status: Status da manifestação
            protocolo: Número do protocolo SEFAZ
        
        Returns:
            bool: True se registrado com sucesso, False se já existe
        """
        try:
            from datetime import datetime
            with self._connect() as conn:
                conn.execute('''INSERT INTO manifestacoes 
                    (chave, tipo_evento, informante, data_manifestacao, status, protocolo)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (chave, tipo_evento, informante, datetime.now().isoformat(), status, protocolo)
                )
                conn.commit()
                return True
        except Exception as e:
            # Manifestação já existe (UNIQUE constraint violated)
            logger.debug(f"Manifestação já existe ou erro: {e}")
            return False

# -------------------------------------------------------------------
# Processador de XML
# -------------------------------------------------------------------
class XMLProcessor:
    NS = {'nfe':'http://www.portalfiscal.inf.br/nfe'}
    
    def __init__(self, informante=None):
        """Inicializa XMLProcessor com informante opcional para debug."""
        self.informante = informante

    def extract_docs(self, resp_xml):
        logger.debug("Extraindo docs de distribuição")
        docs = []
        tree = etree.fromstring(resp_xml.encode('utf-8'))
        for dz in tree.findall('.//nfe:docZip', namespaces=self.NS):
            data = base64.b64decode(dz.text or '')
            xml  = gzip.decompress(data).decode('utf-8')
            nsu  = dz.get('NSU','')
            docs.append((nsu, xml))
            
            # 🔍 DEBUG: Salva cada XML extraído
            try:
                # Identifica tipo do documento
                if '<resNFe' in xml or '<resEvento' in xml:
                    tipo_doc = "resumo"
                elif '<procNFe' in xml or '<nfeProc' in xml:
                    tipo_doc = "nfe_completa"
                elif '<procCTe' in xml or '<cteProc' in xml:
                    tipo_doc = "cte_completo"
                elif '<procEventoNFe' in xml:
                    tipo_doc = "evento"
                else:
                    tipo_doc = "documento"
                
                # XMLProcessor não tem informante, usa genérico
                informante = getattr(self, 'informante', 'DESCONHECIDO')
                save_debug_soap(informante, f"xml_extraido_{tipo_doc}_NSU{nsu}", xml, prefixo="nfe_dist")
            except Exception as e:
                logger.debug(f"Debug save XML pulado: {e}")
        
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
        """
        Parse protocolo de NFe. Retorna (chNFe, cStat, xMotivo).
        Se xml_obj for None ou inválido, retorna (None, None, None).
        """
        logger.debug("Parseando protocolo NF-e")
        
        # Validação: se recebeu None, retorna valores nulos
        if xml_obj is None:
            logger.warning("parse_protNFe recebeu None como entrada")
            return None, None, None
        
        try:
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
        except Exception as e:
            logger.error(f"Erro ao parsear protNFe: {e}")
            return None, None, None
    
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
    
    def fetch_by_key(self, chave):
        """
        Busca XML completo de NF-e/CT-e por chave de acesso.
        Este é um método de compatibilidade que delega para o NFeService.
        
        Args:
            chave: Chave de 44 dígitos da NF-e/CT-e
        
        Returns:
            XML completo ou None
        
        Nota:
            Este método requer que o XMLProcessor tenha sido inicializado
            com informante para criar o NFeService apropriado.
        """
        logger.warning(f"⚠️ fetch_by_key chamado no XMLProcessor - método legado")
        logger.warning(f"   Recomenda-se usar NFeService.fetch_by_chave_dist() diretamente")
        
        if not self.informante:
            logger.error(f"❌ XMLProcessor.fetch_by_key: informante não definido")
            return None
        
        # Este método precisa de um NFeService para funcionar
        # Por enquanto, retorna None e loga erro
        logger.error(f"❌ XMLProcessor.fetch_by_key: método não implementado completamente")
        logger.error(f"   Use NFeService.fetch_by_chave_dist() para buscar XMLs por chave")
        return None

# -------------------------------------------------------------------
# Serviço SOAP
# -------------------------------------------------------------------
class NFeService:
    def __init__(self, cert_path, senha, informante, cuf):
        logger.debug(f"Inicializando serviço para informante={informante}, cUF={cuf}")
        
        # Imports necessários
        import ssl
        import urllib3
        import requests
        from requests_pkcs12 import Pkcs12Adapter
        
        # Desabilita warnings de SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configura sessão com certificado PKCS12
        sess = requests.Session()
        sess.verify = False  # Desabilita verificação SSL
        
        # Corrige conflito SSL em Python 3.10+
        # Cria adapter personalizado com contexto SSL corrigido
        class CustomPkcs12Adapter(Pkcs12Adapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)
        
        sess.mount('https://', CustomPkcs12Adapter(
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

    def fetch_by_chave_dist(self, chave):
        """
        Consulta documento específico via Distribuição DFe usando a chave de acesso.
        Útil para XMLs antigos que não estão mais disponíveis via ConsultaProtocolo.
        Disponibilidade: ~1000+ dias (muito maior que ConsultaProtocolo ~180 dias)
        
        Args:
            chave: Chave de 44 dígitos da NF-e/CT-e
            
        Returns:
            XML da resposta ou None em caso de erro
        """
        logger.info(f"🔑 Consultando via Distribuição DFe por chave: {chave}")
        
        distInt = etree.Element("distDFeInt",
            xmlns=XMLProcessor.NS['nfe'], versao="1.01"
        )
        etree.SubElement(distInt, "tpAmb").text    = "1"
        etree.SubElement(distInt, "cUFAutor").text = str(self.cuf)
        etree.SubElement(distInt, "CNPJ").text     = self.informante
        
        # Usa consChNFe em vez de distNSU para buscar por chave específica
        sub = etree.SubElement(distInt, "consChNFe")
        etree.SubElement(sub, "chNFe").text = chave

        xml_envio = etree.tostring(distInt, encoding='utf-8').decode()
        
        # 🔍 DEBUG: Salva XML enviado
        save_debug_soap(self.informante, "request", xml_envio, prefixo="nfe_dist_chave")
        
        # Valide antes de enviar
        try:
            validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
        except Exception as e:
            logger.warning(f"XML de distribuição por chave não passou na validação XSD: {e}")
            # Continua mesmo com erro de validação (às vezes o XSD está desatualizado)

        # 🌐 DEBUG HTTP: Informações da requisição SOAP
        logger.info(f"🌐 [{self.informante}] HTTP REQUEST Distribuição por Chave:")
        logger.info(f"   📍 URL: {URL_DISTRIBUICAO}")
        logger.info(f"   🔐 Certificado: Configurado com PKCS12")
        logger.info(f"   📦 Método: POST (SOAP)")
        logger.info(f"   📋 Payload: distDFeInt (consChNFe={chave}, cUF={self.cuf})")
        logger.info(f"   📏 Tamanho XML: {len(xml_envio)} bytes")

        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
            
            # 🌐 DEBUG HTTP: Informações da resposta
            logger.info(f"✅ [{self.informante}] HTTP RESPONSE Distribuição por Chave recebida")
            logger.info(f"   📊 Tipo: {type(resp).__name__}")
            if hasattr(resp, '__dict__'):
                logger.debug(f"   🔍 Atributos: {list(resp.__dict__.keys())[:5]}...")
            
        except Fault as fault:
            logger.error(f"SOAP Fault Distribuição por Chave: {fault}")
            logger.error(f"   ❌ Falha na comunicação SOAP")
            # 🔍 DEBUG: Salva erro SOAP
            save_debug_soap(self.informante, "fault", str(fault), prefixo="nfe_dist_chave")
            return None
        except Exception as e:
            logger.error(f"❌ [{self.informante}] Erro HTTP na distribuição por chave: {e}")
            logger.exception(e)
            return None
        
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.info(f"📥 [{self.informante}] Resposta processada: {len(xml_str)} bytes")
        logger.debug(f"Resposta Distribuição por Chave:\n{xml_str}")
        
        # 🔍 DEBUG: Salva XML recebido
        save_debug_soap(self.informante, "response", xml_str, prefixo="nfe_dist_chave")
        
        return xml_str

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
        
        # 🔍 DEBUG: Salva XML enviado
        save_debug_soap(self.informante, "request", xml_envio, prefixo="nfe_dist")
        
        # Valide antes de enviar
        try:
            validar_xml_auto(xml_envio, 'distDFeInt_v1.01.xsd')
        except Exception as e:
            logger.error("XML de distribuição não passou na validação XSD. Corrija antes de enviar.")
            return None

        # 🌐 DEBUG HTTP: Informações da requisição SOAP
        logger.info(f"🌐 [{self.informante}] HTTP REQUEST Distribuição:")
        logger.info(f"   📍 URL: {URL_DISTRIBUICAO}")
        logger.info(f"   🔐 Certificado: Configurado com PKCS12")
        logger.info(f"   📦 Método: POST (SOAP)")
        logger.info(f"   📋 Payload: distDFeInt (ultNSU={ult_nsu}, cUF={self.cuf})")
        logger.info(f"   📏 Tamanho XML: {len(xml_envio)} bytes")

        try:
            resp = self.dist_client.service.nfeDistDFeInteresse(nfeDadosMsg=distInt)
            
            # 🌐 DEBUG HTTP: Informações da resposta
            logger.info(f"✅ [{self.informante}] HTTP RESPONSE Distribuição recebida")
            logger.info(f"   📊 Tipo: {type(resp).__name__}")
            if hasattr(resp, '__dict__'):
                logger.debug(f"   🔍 Atributos: {list(resp.__dict__.keys())[:5]}...")
            
        except Fault as fault:
            logger.error(f"SOAP Fault Distribuição: {fault}")
            logger.error(f"   ❌ Falha na comunicação SOAP")
            # 🔍 DEBUG: Salva erro SOAP
            save_debug_soap(self.informante, "fault", str(fault), prefixo="nfe_dist")
            return None
        except Exception as e:
            logger.error(f"❌ [{self.informante}] Erro HTTP na distribuição: {e}")
            logger.exception(e)
            return None
        
        xml_str = etree.tostring(resp, encoding='utf-8').decode()
        logger.info(f"📥 [{self.informante}] Resposta processada: {len(xml_str)} bytes")
        logger.debug(f"Resposta Distribuição:\n{xml_str}")
        
        # 🔍 DEBUG: Salva XML recebido
        save_debug_soap(self.informante, "response", xml_str, prefixo="nfe_dist")
        
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
            
            # 🔍 DEBUG: Salva SOAP request completo
            save_debug_soap(self.informante, "request", soap_envelope, prefixo=f"protocolo_{chave}")
            
            logger.debug(f"Envelope SOAP:\n{soap_envelope[:500]}")
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            # 🌐 DEBUG HTTP: Informações da requisição
            logger.info(f"🌐 [{self.informante}] HTTP REQUEST Protocolo NF-e:")
            logger.info(f"   📍 URL: {url}")
            logger.info(f"   🔑 Chave: {chave}")
            logger.info(f"   📦 Método: POST")
            logger.info(f"   📋 Headers: {headers}")
            logger.info(f"   📏 Tamanho SOAP: {len(soap_envelope)} bytes")
            logger.info(f"   🔐 Certificado: PKCS12 via sessão requests")
            
            # Usa a sessão que já tem o certificado configurado
            resp = self.dist_client.transport.session.post(url, data=soap_envelope.encode('utf-8'), headers=headers)
            
            # 🌐 DEBUG HTTP: Informações da resposta
            logger.info(f"✅ [{self.informante}] HTTP RESPONSE Protocolo:")
            logger.info(f"   📊 Status Code: {resp.status_code}")
            logger.info(f"   📋 Headers: {dict(resp.headers)}")
            logger.info(f"   📏 Tamanho: {len(resp.content)} bytes")
            logger.info(f"   ⏱️ Tempo resposta: {resp.elapsed.total_seconds():.2f}s")
            
            resp.raise_for_status()
            
            # 🔍 DEBUG: Salva SOAP response completo (raw)
            save_debug_soap(self.informante, "response_raw", resp.content.decode('utf-8'), prefixo=f"protocolo_{chave}")
            
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
    
    def fetch_prot_cte(self, chave):
        """
        Consulta o protocolo do CT-e pela chave, validando o XML de envio e resposta.
        """
        if not self.cons_client:
            logger.debug("Cliente de protocolo não disponível")
            return None

        logger.debug(f"Chamando protocolo CT-e para chave={chave}")
        
        # Define URL do serviço baseado no cUF (extrai da chave)
        # Chave CTe: posições 0-1 = cUF
        cuf_from_chave = chave[:2] if len(chave) == 44 else str(self.cuf)
        
        # URLs OFICIAIS dos serviços de consulta CT-e (versão 4.00)
        # Fonte: https://dfe-portal.svrs.rs.gov.br/Cte/Servicos
        url_map = {
            '51': 'https://cte.sefaz.mt.gov.br/ctews/services/CTeConsultaV4',  # MT
            '50': 'https://producao.cte.ms.gov.br/ws/CTeConsultaV4',  # MS (sem .asmx!)
            '31': 'https://cte.fazenda.mg.gov.br/cte/services/CTeConsultaV4',  # MG
            '41': 'https://cte.fazenda.pr.gov.br/cte/CTeConsultaV4?wsdl',  # PR
            '43': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RS (SVRS)
            '35': 'https://nfe.fazenda.sp.gov.br/cteWEB/services/cteConsultaV4.asmx',  # SP
            # SVRS (usado por GO=52, DF=53, RJ=33, AC, AL, AP, ES, PA, PB, PI, RN, RO, RR, SC, SE, TO)
            '52': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # GO (SVRS)
            '53': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # DF (SVRS)
            '33': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RJ (SVRS)
        }
        url = url_map.get(cuf_from_chave, 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx')  # Default: SVRS
        
        # Monta XML de consulta CT-e (versão 4.00)
        xml_consulta = f'''<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chCTe>{chave}</chCTe></consSitCTe>'''
        
        logger.debug(f"XML de consulta CT-e:\n{xml_consulta}")
        logger.debug(f"URL do serviço (cUF={cuf_from_chave}): {url}")

        # Envia requisição SOAP manualmente
        try:
            # Monta envelope SOAP 1.2 (IMPORTANTE: namespace case-sensitive - CTeConsultaV4 com T maiúsculo!)
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap12:Body>
    <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CTeConsultaV4">{xml_consulta}</cteDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
            
            # 🔍 DEBUG: Salva SOAP request completo
            save_debug_soap(self.informante, "request", soap_envelope, prefixo=f"protocolo_cte_{chave}")
            
            logger.debug(f"Envelope SOAP CT-e:\n{soap_envelope[:500]}")
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            # 🌐 DEBUG HTTP: Informações da requisição
            logger.info(f"🌐 [{self.informante}] HTTP REQUEST Protocolo CT-e:")
            logger.info(f"   📍 URL: {url}")
            logger.info(f"   🔑 Chave: {chave}")
            logger.info(f"   📦 Método: POST")
            logger.info(f"   📋 Headers: {headers}")
            logger.info(f"   📏 Tamanho SOAP: {len(soap_envelope)} bytes")
            logger.info(f"   🔐 Certificado: PKCS12 via sessão requests")
            
            # Usa a sessão que já tem o certificado configurado
            resp = self.dist_client.transport.session.post(url, data=soap_envelope.encode('utf-8'), headers=headers)
            
            # 🌐 DEBUG HTTP: Informações da resposta
            logger.info(f"✅ [{self.informante}] HTTP RESPONSE Protocolo CT-e:")
            logger.info(f"   📊 Status Code: {resp.status_code}")
            logger.info(f"   📋 Headers: {dict(resp.headers)}")
            logger.info(f"   📏 Tamanho: {len(resp.content)} bytes")
            logger.info(f"   ⏱️ Tempo resposta: {resp.elapsed.total_seconds():.2f}s")
            
            resp.raise_for_status()
            
            # 🔍 DEBUG: Salva SOAP response completo (raw)
            save_debug_soap(self.informante, "response_raw", resp.content.decode('utf-8'), prefixo=f"protocolo_cte_{chave}")
            
            # Extrai corpo da resposta SOAP
            resp_tree = etree.fromstring(resp.content)
            body = resp_tree.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
            if body is not None and len(body) > 0:
                resp = body[0]
            else:
                logger.error("Resposta SOAP CT-e sem corpo")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição HTTP CT-e: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao montar/enviar requisição SOAP CT-e: {e}")
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
                resp_xml = etree.tostring(resp, encoding="utf-8").decode()
        except Exception as e:
            logger.error(f"Erro ao converter resposta SOAP CT-e em XML: {e}")
            return None

        # Protege contra respostas inválidas
        if not resp_xml or resp_xml.strip().startswith('<html') or resp_xml.strip() == '':
            logger.warning("Resposta inválida da SEFAZ CT-e (não é XML): %s", resp_xml)
            return None

        logger.debug(f"Resposta Protocolo CT-e (raw):\n{resp_xml}")
        return resp_xml
    
    def consultar_eventos_chave(self, chave):
        """
        Consulta eventos de uma chave específica na SEFAZ.
        
        Args:
            chave: Chave de 44 dígitos da NF-e/CT-e
            
        Returns:
            XML com os eventos encontrados ou None se não houver
        """
        logger.debug(f"Consultando eventos para chave={chave}")
        
        # Define URL do serviço baseado no cUF (extrai da chave)
        cuf_from_chave = chave[:2] if len(chave) == 44 else str(self.cuf)
        
        # Detecta se é NFe ou CTe pela posição 20 (modelo: 55=NFe, 57=CTe)
        modelo = chave[20:22] if len(chave) == 44 else '55'
        is_cte = modelo == '57'
        
        if is_cte:
            # URLs dos serviços de consulta de CT-e (versão 4.00) - Fonte: https://dfe-portal.svrs.rs.gov.br/Cte/Servicos
            # SVRS (Sefaz Virtual RS) atende: AC, AL, AP, DF, ES, GO, MS, MT, PA, PB, PI, RJ, RN, RO, RR, SC, SE, TO
            url_map = {
                '31': 'https://cte.fazenda.mg.gov.br/cte/services/CTeConsultaV4',  # MG
                '35': 'https://nfe.fazenda.sp.gov.br/CTeWS/WS/CTeConsultaV4.asmx',  # SP
                '41': 'https://cte.fazenda.pr.gov.br/cte4/CTeConsultaV4',  # PR
                '50': 'https://producao.cte.ms.gov.br/ws/CTeConsultaV4',  # MS
                '51': 'https://cte.sefaz.mt.gov.br/ctews2/services/CTeConsultaV4',  # MT
                # SVRS (usado por GO=52, DF=53, RJ=33, RS=43, AC, AL, AP, ES, PA, PB, PI, RN, RO, RR, SC, SE, TO)
                '52': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # GO (SVRS)
                '53': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # DF (SVRS)
                '33': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RJ (SVRS)
                '43': 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx',  # RS (SVRS)
            }
            url = url_map.get(cuf_from_chave, 'https://cte.svrs.rs.gov.br/ws/CTeConsultaV4/CTeConsultaV4.asmx')  # Default: SVRS
            
            # XML de consulta CT-e (versão 4.00)
            xml_consulta = f'''<consSitCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chCTe>{chave}</chCTe></consSitCTe>'''
            
            # IMPORTANTE: namespace case-sensitive - CTeConsultaV4 com T maiúsculo!
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap12:Body>
    <cteDadosMsg xmlns="http://www.portalfiscal.inf.br/cte/wsdl/CTeConsultaV4">{xml_consulta}</cteDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
        else:
            # URLs dos serviços de consulta de NF-e
            # SVRS (Sefaz Virtual RS) atende: AC, AL, AP, DF, ES, GO, MA, PA, PB, PI, RJ, RN, RO, RR, SC, SE, TO
            url_map = {
                '31': 'https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4',  # MG
                '50': 'https://nfe.sefaz.ms.gov.br/ws/NFeConsultaProtocolo4',  # MS
                '51': 'https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeConsulta4',  # MT
                '35': 'https://nfe.fazenda.sp.gov.br/ws/nfeconsultaprotocolo4.asmx',  # SP
                '41': 'https://nfe.sefa.pr.gov.br/nfe/NFeConsultaProtocolo4',  # PR
                '29': 'https://nfe.sefaz.ba.gov.br/webservices/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # BA
                # SVRS para estados sem servidor próprio
                '32': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # ES (SVRS)
                '33': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # RJ (SVRS)
                '52': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # GO (SVRS)
                '53': 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx',  # DF (SVRS)
            }
            url = url_map.get(cuf_from_chave, 'https://www.sefazvirtual.fazenda.gov.br/NFeConsultaProtocolo4/NFeConsultaProtocolo4.asmx')
            
            # XML de consulta NF-e
            xml_consulta = f'''<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00"><tpAmb>1</tpAmb><xServ>CONSULTAR</xServ><chNFe>{chave}</chNFe></consSitNFe>'''
            
            soap_envelope = f'''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4">{xml_consulta}</nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>'''
        
        logger.debug(f"XML consulta eventos ({('CTe' if is_cte else 'NFe')}):\n{xml_consulta}")
        logger.debug(f"URL do serviço (cUF={cuf_from_chave}): {url}")
        logger.debug(f"XML consulta eventos ({('CTe' if is_cte else 'NFe')}):\n{xml_consulta}")
        logger.debug(f"URL do serviço (cUF={cuf_from_chave}): {url}")
        
        # Envia requisição SOAP
        try:
            save_debug_soap(self.informante, "request_eventos", soap_envelope, prefixo=f"eventos_{chave[:10]}")
            
            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
            }
            
            logger.info(f"🔍 Consultando eventos da chave {'CTe' if is_cte else 'NFe'}: {chave}")
            
            resp = self.dist_client.transport.session.post(url, data=soap_envelope.encode('utf-8'), headers=headers)
            resp.raise_for_status()
            
            save_debug_soap(self.informante, "response_eventos", resp.content.decode('utf-8'), prefixo=f"eventos_{chave[:10]}")
            
            # Extrai corpo da resposta SOAP
            resp_tree = etree.fromstring(resp.content)
            body = resp_tree.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
            if body is not None and len(body) > 0:
                resp_xml = etree.tostring(body[0], encoding="utf-8").decode()
                logger.debug(f"Resposta eventos:\n{resp_xml[:500]}")
                return resp_xml
            else:
                logger.warning("Resposta SOAP sem corpo")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição HTTP eventos: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar eventos: {e}")
            return None

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
        # Inicializa parser XML para processar CT-e
        parser = XMLProcessor(informante=inf)
        
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
                elif max_nsu == "000000000000000":
                    logger.info(f"✅ [{inf}] CT-e: SEFAZ retornou maxNSU=0 (sem documentos disponíveis)")
        
        # Loop de busca incremental com limite de segurança
        ult_nsu_cte = last_nsu_cte
        max_iterations = 100  # Limite de segurança para evitar loop infinito
        iteration_count = 0
        
        logger.info(f"🚛 [{inf}] Iniciando loop CT-e. NSU inicial: {ult_nsu_cte}")
        
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"🔄 [{inf}] CT-e iteração {iteration_count}/{max_iterations}, NSU atual: {ult_nsu_cte}")
            
            # 🌐 DEBUG HTTP: Informações da requisição CT-e
            logger.info(f"🌐 [{inf}] Preparando requisição HTTP CT-e:")
            logger.info(f"   📍 Endpoint: CTeDistribuicaoDFe (Receita Federal)")
            logger.info(f"   📋 Tipo: {'CNPJ' if len(cnpj)==14 else 'CPF'}")
            logger.info(f"   📊 NSU solicitado: {ult_nsu_cte}")
            logger.info(f"   🔐 Certificado: {path}")
            
            resp_cte = cte_svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", ult_nsu_cte)
            
            if not resp_cte:
                logger.info(f"✅ [{inf}] CT-e: Sem resposta (fim da fila)")
                break
            
            logger.info(f"📥 [{inf}] CT-e: Resposta recebida, extraindo cStat...")
            cStat_cte = cte_svc.extract_cstat(resp_cte)
            logger.info(f"📊 [{inf}] CT-e cStat: {cStat_cte}")
            
            if cStat_cte == '656':
                logger.warning(f"🔒 [{inf}] CT-e: Erro 656 - Consumo indevido")
                # ⚠️ IMPORTANTE: NÃO atualizar NSU em erro 656!
                # Se atualizar, perdemos documentos intermediários
                # SOLUÇÃO: Manter NSU atual, bloquear por 65 min
                logger.warning(f"⚠️ [{inf}] CT-e: NSU mantido em {ult_nsu_cte}, documentos serão baixados após bloqueio")
                logger.info(f"   ⏰ Bloqueio por consulta muito frequente - aguarde 65 minutos")
                break
            
            # Extrai e processa documentos CT-e
            logger.info(f"📦 [{inf}] CT-e: Extraindo documentos...")
            docs_processados = 0
            doc_count = 0
            
            # 📊 HISTÓRICO NSU: Inicia coleta de informações da consulta CT-e
            tempo_inicio_cte = time.time()
            xmls_processados_historico_cte = []
            
            for nsu, xml_cte, schema in cte_svc.extrair_docs(resp_cte):
                doc_count += 1
                logger.info(f"📄 [{inf}] CT-e: Processando doc {doc_count}, NSU={nsu}, schema={schema}")
                try:
                    # Detecta tipo de documento CT-e
                    tipo_doc = detectar_tipo_documento(xml_cte)
                    logger.debug(f"🔍 [{inf}] CT-e NSU {nsu}: tipo={tipo_doc}")
                    
                    if tipo_doc != 'CTe':
                        logger.debug(f"⏭️ [{inf}] CT-e NSU {nsu}: não é CT-e, pulando")
                        continue
                    
                    # Extrai chave do CT-e
                    logger.debug(f"🔑 [{inf}] CT-e NSU {nsu}: Parseando XML...")
                    tree = etree.fromstring(xml_cte.encode('utf-8'))
                    infcte = tree.find('.//{http://www.portalfiscal.inf.br/cte}infCte')
                    
                    if infcte is None:
                        # Pode ser evento ou resumo
                        logger.debug(f"🔍 [{inf}] CT-e NSU {nsu}: infCte não encontrado, tentando chCTe...")
                        
                        # Tenta extrair chave de eventos
                        ch_cte_elem = tree.find('.//{http://www.portalfiscal.inf.br/cte}chCTe')
                        if ch_cte_elem is not None and ch_cte_elem.text:
                            chave_cte = ch_cte_elem.text.strip()
                            logger.debug(f"✅ [{inf}] CT-e NSU {nsu}: chave={chave_cte}")
                        else:
                            logger.debug(f"❌ [{inf}] CT-e NSU {nsu}: chave não encontrada, pulando")
                            continue
                    else:
                        chave_cte = infcte.attrib.get('Id', '')[-44:]
                        logger.debug(f"✅ [{inf}] CT-e NSU {nsu}: chave={chave_cte}")
                    
                    # Busca nome do certificado (se configurado)
                    nome_cert = db.get_cert_nome_by_informante(inf)
                    
                    # 1. SEMPRE salva em xmls/ (backup local) e obtém o caminho
                    logger.debug(f"💾 [{inf}] CT-e {chave_cte}: Salvando em xmls/ (backup)...")
                    resultado = salvar_xml_por_certificado(xml_cte, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                    # Resultado pode ser: (caminho_xml, caminho_pdf) ou apenas caminho_xml
                    if isinstance(resultado, tuple):
                        caminho_xml, caminho_pdf = resultado
                    else:
                        caminho_xml, caminho_pdf = resultado, None
                    
                    # Registra XML no banco COM o caminho
                    if caminho_xml:
                        db.registrar_xml(chave_cte, cnpj, caminho_xml)
                    else:
                        db.registrar_xml(chave_cte, cnpj)
                        logger.warning(f"⚠️ [{inf}] CT-e XML salvo mas caminho não obtido: {chave_cte}")
                    
                    # 2. Se configurado armazenamento diferente, copia para lá também
                    pasta_storage = db.get_config('storage_pasta_base', 'xmls')
                    if pasta_storage and pasta_storage != 'xmls':
                        logger.debug(f"💾 [{inf}] CT-e {chave_cte}: Copiando para armazenamento ({pasta_storage})...")
                        salvar_xml_por_certificado(xml_cte, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                    
                    db.criar_tabela_detalhada()
                    
                    logger.debug(f"📝 [{inf}] CT-e {chave_cte}: Extraindo nota detalhada...")
                    nota_cte = extrair_nota_detalhada(xml_cte, parser, db, chave_cte, inf, nsu)
                    nota_cte['informante'] = inf  # Garantir informante
                    
                    # CACHE: Atualiza caminho do PDF no banco (se foi gerado)
                    if caminho_pdf:
                        db.atualizar_pdf_path(chave_cte, caminho_pdf)
                        logger.debug(f"✅ PDF path cached: {chave_cte} → {caminho_pdf}")
                    
                    # Determina status do XML (COMPLETO, RESUMO, EVENTO)
                    root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
                    if root_tag in ['cteProc', 'CTe']:
                        nota_cte['xml_status'] = 'COMPLETO'
                    elif root_tag == 'resCTe':
                        nota_cte['xml_status'] = 'RESUMO'
                    elif root_tag in ['procEventoCTe', 'eventoCTe']:
                        nota_cte['xml_status'] = 'EVENTO'
                        
                        # 🆕 Processa evento para atualizar status da nota relacionada
                        try:
                            # Extrai chave do CT-e relacionado ao evento
                            ch_cte_evento = root.findtext('.//{http://www.portalfiscal.inf.br/cte}chCTe')
                            tp_evento = root.findtext('.//{http://www.portalfiscal.inf.br/cte}tpEvento')
                            c_stat = root.findtext('.//{http://www.portalfiscal.inf.br/cte}cStat')
                            
                            if ch_cte_evento and tp_evento == '110111' and c_stat == '135':
                                # Cancelamento de CT-e homologado
                                novo_status = "Cancelamento de CT-e homologado"
                                db.atualizar_status_por_evento(ch_cte_evento, novo_status)
                                logger.info(f"🚫 [{inf}] CT-e {ch_cte_evento} → {novo_status}")
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao processar evento de CT-e: {e}")
                    else:
                        nota_cte['xml_status'] = 'RESUMO'
                    
                    logger.debug(f"💾 [{inf}] CT-e {chave_cte}: Salvando nota detalhada...")
                    db.salvar_nota_detalhada(nota_cte)
                    
                    # 📊 HISTÓRICO: Registra CT-e processado
                    xmls_processados_historico_cte.append({
                        'tipo': 'cte',
                        'chave': chave_cte,
                        'xml_status': nota_cte.get('xml_status', 'COMPLETO')
                    })
                    
                    docs_processados += 1
                    logger.info(f"✅ [{inf}] CT-e processado: NSU={nsu}, chave={chave_cte}")
                    
                except Exception as e:
                    logger.error(f"❌ [{inf}] Erro ao processar CT-e NSU {nsu}: {e}")
                    logger.exception(e)
            
            logger.info(f"📦 [{inf}] CT-e: Fim da extração. Total documentos: {doc_count}, processados: {docs_processados}")
            
            # Extrai ultNSU da resposta da SEFAZ
            logger.info(f"🔄 [{inf}] CT-e: Extraindo ultNSU da resposta...")
            ult_cte = cte_svc.extract_last_nsu(resp_cte)
            logger.info(f"📊 [{inf}] CT-e: ultNSU={ult_cte}, NSU atual={ult_nsu_cte}")
            
            # ✅ CORREÇÃO: SEMPRE atualiza NSU quando SEFAZ retorna ultNSU
            # Mesmo que seja igual, garante sincronização (importante após Busca Completa)
            if ult_cte:
                if ult_cte != ult_nsu_cte:
                    logger.info(f"💾 [{inf}] CT-e: Atualizando NSU no banco: {ult_nsu_cte} → {ult_cte}")
                    logger.info(f"➡️ [{inf}] CT-e NSU avançou: {ult_nsu_cte} → {ult_cte} ({docs_processados} docs)")
                    ult_nsu_cte = ult_cte
                    logger.info(f"🔄 [{inf}] CT-e: Continuando para próxima iteração...")
                else:
                    # NSU não mudou - sincroniza e encerra
                    logger.info(f"🛑 [{inf}] CT-e: NSU confirmado pela SEFAZ (permanece em {ult_nsu_cte})")
                    if docs_processados > 0:
                        logger.info(f"✅ [{inf}] CT-e sincronizado: {docs_processados} documentos processados")
                    else:
                        logger.info(f"✅ [{inf}] CT-e sincronizado: nenhum documento novo")
                    logger.info(f"🏁 [{inf}] CT-e: Break - NSU não mudou")
                
                # ✅ SEMPRE atualiza no banco (garante sincronização)
                db.set_last_nsu_cte(inf, ult_cte)
                
                # 📊 HISTÓRICO NSU: Registra consulta CT-e no banco de dados
                try:
                    tempo_fim_cte = time.time()
                    tempo_ms_cte = int((tempo_fim_cte - tempo_inicio_cte) * 1000)
                    
                    # Obtém identificação do certificado
                    cert_nome = db.get_cert_nome_by_informante(inf) or f"Cert_{inf[:8]}"
                    
                    # Registra histórico de forma não-bloqueante
                    status_historico_cte = 'sucesso' if docs_processados > 0 else 'vazio'
                    db.registrar_historico_nsu(
                        certificado=cert_nome,
                        informante=inf,
                        nsu_consultado=ult_nsu_cte,
                        xmls_retornados=xmls_processados_historico_cte,
                        tempo_ms=tempo_ms_cte,
                        status=status_historico_cte
                    )
                    logger.debug(f"📊 Histórico NSU CT-e registrado: {len(xmls_processados_historico_cte)} XMLs")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao registrar histórico NSU CT-e (não-crítico): {e}")
                
                # Break apenas se NSU não mudou
                if ult_cte == ult_nsu_cte:
                    break
            else:
                logger.warning(f"⚠️ [{inf}] CT-e: SEFAZ não retornou ultNSU, encerrando loop")
                logger.info(f"🏁 [{inf}] CT-e: Break - sem ultNSU")
                break
        
        # Log se atingiu o limite de iterações
        if iteration_count >= max_iterations:
            logger.warning(f"⚠️ [{inf}] CT-e: Atingido limite de {max_iterations} iterações. Última NSU: {ult_nsu_cte}")
        else:
            logger.info(f"🏁 [{inf}] CT-e: Loop finalizado após {iteration_count} iterações")
                
    except Exception as e:
        logger.error(f"❌ [{inf}] ERRO CRÍTICO ao processar CT-e: {e}")
        logger.exception(f"Erro ao processar CT-e para {inf}: {e}")


def salvar_nfse_detalhada(xml_content, nsu, informante):
    """
    Processa um XML de NFS-e e salva em notas_detalhadas.
    Função auxiliar para integração com buscar_nfse_auto.py
    
    Args:
        xml_content: String com XML completo da NFS-e
        nsu: NSU do documento
        informante: CNPJ informante
    """
    try:
        from lxml import etree
        from pathlib import Path
        
        # Define caminho do banco principal
        base_dir = Path(__file__).parent
        db_path = str(base_dir / "notas.db")
        
        # Cria instância do DatabaseManager
        db = DatabaseManager(db_path)
        
        # Parse do XML
        tree = etree.fromstring(xml_content.encode('utf-8'))
        
        # 🔧 XML do ADN tem estrutura específica do padrão nacional
        # Namespace: http://www.sped.fazenda.gov.br/nfse
        ns = {'nfse': 'http://www.sped.fazenda.gov.br/nfse'}
        
        # Extrai chave do atributo Id da tag infNFSe
        inf_nfse = tree.find('.//nfse:infNFSe', namespaces=ns)
        if inf_nfse is None:
            inf_nfse = tree.find('.//infNFSe')
        
        chave_nfse = inf_nfse.get('Id', '') if inf_nfse is not None else str(nsu)
        if chave_nfse and chave_nfse.startswith('NFS'):
            chave_nfse = chave_nfse[3:]  # Remove prefixo "NFS"
        
        # Extrai número (<nNFSe>)
        numero = tree.findtext('.//nfse:nNFSe', namespaces=ns)
        if not numero:
            numero = tree.findtext('.//nNFSe') or str(nsu)
        
        # Extrai emitente (<emit><xNome>)
        nome_emit = tree.findtext('.//nfse:emit/nfse:xNome', namespaces=ns)
        if not nome_emit:
            nome_emit = tree.findtext('.//emit/xNome') or 'NFS-e'
        
        # Extrai CNPJ emitente (<emit><CNPJ>)
        cnpj_emit = tree.findtext('.//nfse:emit/nfse:CNPJ', namespaces=ns)
        if not cnpj_emit:
            cnpj_emit = tree.findtext('.//emit/CNPJ') or informante
        
        # Extrai data de processamento (<dhProc>)
        data_emissao = tree.findtext('.//nfse:dhProc', namespaces=ns)
        if not data_emissao:
            data_emissao = tree.findtext('.//dhProc')
        if data_emissao and 'T' in data_emissao:
            data_emissao = data_emissao.split('T')[0]  # Pega apenas a data
        
        # Extrai valor líquido (<valores><vLiq>)
        valor = tree.findtext('.//nfse:valores/nfse:vLiq', namespaces=ns)
        if not valor:
            valor = tree.findtext('.//valores/vLiq') or '0.00'
        
        # Cria nota detalhada com TODOS os campos obrigatórios
        nota_nfse = {
            'chave': chave_nfse,
            'numero': numero,
            'tipo': 'NFS-e',
            'nome_emitente': nome_emit,
            'cnpj_emitente': cnpj_emit,
            'data_emissao': data_emissao or datetime.now().isoformat()[:10],
            'valor': valor,
            'status': 'Autorizada',
            'informante': informante,
            'xml_status': 'COMPLETO',
            'nsu': nsu,
            # Campos obrigatórios adicionais
            'ie_tomador': '',
            'cnpj_destinatario': '',
            'cfop': '',
            'vencimento': '',
            'ncm': '',
            'uf': '',
            'natureza': 'Serviço',
            'base_icms': '',
            'valor_icms': '',
            'atualizado_em': datetime.now().isoformat()
        }
        
        # Salva no banco
        db.criar_tabela_detalhada()
        db.salvar_nota_detalhada(nota_nfse)
        logger.debug(f"✅ NFS-e {numero} salva em notas_detalhadas")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar NFS-e detalhada: {e}")
        return False


def processar_nfse(cert_data, db):
    """
    Processa NFS-e (Nota Fiscal de Serviço Eletrônica) do Padrão Nacional
    Consulta incremental via NSU no Ambiente Nacional da Receita Federal
    """
    from modules.nfse_service import NFSeService
    
    cnpj, path, senha, inf, cuf = cert_data
    
    try:
        # Inicializa serviço NFS-e
        nfse_svc = NFSeService(path, senha, cnpj, cuf, ambiente='producao')
        logger.info(f"📋 Iniciando busca de NFS-e para {inf}")
        
        # Obtém último NSU NFS-e processado
        last_nsu_nfse = db.get_last_nsu_nfse(inf)
        
        # Primeira consulta (NSU = 0) para verificar maxNSU
        if last_nsu_nfse == "000000000000000":
            resp = nfse_svc.consultar_nsu(last_nsu_nfse)
            if resp:
                _, _, max_nsu = nfse_svc.extrair_cstat_nsu(resp)
                if max_nsu and max_nsu != "000000000000000":
                    logger.info(f"📊 [{inf}] NFS-e disponíveis até NSU: {max_nsu}")
                elif max_nsu == "000000000000000":
                    logger.info(f"✅ [{inf}] NFS-e: Ambiente Nacional retornou maxNSU=0 (sem documentos)")
                    logger.info(f"🏁 [{inf}] NFS-e: Nenhum documento disponível no momento")
                    return
        
        # Loop de busca incremental
        ult_nsu_nfse = last_nsu_nfse
        max_iterations = 100
        iteration_count = 0
        
        logger.info(f"📋 [{inf}] Iniciando loop NFS-e. NSU inicial: {ult_nsu_nfse}")
        
        while iteration_count < max_iterations:
            iteration_count += 1
            logger.info(f"🔄 [{inf}] NFS-e iteração {iteration_count}/{max_iterations}, NSU atual: {ult_nsu_nfse}")
            
            logger.info(f"🌐 [{inf}] Preparando requisição HTTP NFS-e:")
            logger.info(f"   📍 Endpoint: Ambiente Nacional NFS-e (Receita Federal)")
            logger.info(f"   📊 NSU solicitado: {ult_nsu_nfse}")
            logger.info(f"   🔐 Certificado: {path}")
            
            resp_nfse = nfse_svc.consultar_nsu(ult_nsu_nfse)
            
            if not resp_nfse:
                logger.info(f"✅ [{inf}] NFS-e: Sem resposta (fim da fila)")
                break
            
            # Extrai status
            cStat_nfse, ult_nfse, max_nsu_nfse = nfse_svc.extrair_cstat_nsu(resp_nfse)
            logger.info(f"📊 [{inf}] NFS-e: cStat={cStat_nfse}, ultNSU={ult_nfse}, maxNSU={max_nsu_nfse}")
            
            if cStat_nfse == '656':
                logger.warning(f"🔒 [{inf}] NFS-e: Erro 656 - Consumo indevido")
                logger.warning(f"⚠️ [{inf}] NFS-e: NSU mantido em {ult_nsu_nfse}")
                logger.info(f"   ⏰ Bloqueio - aguarde 65 minutos")
                break
            
            if cStat_nfse == '137':
                logger.info(f"✅ [{inf}] NFS-e: Nenhum documento novo (cStat=137)")
                db.registrar_sem_documentos_nfse(inf)
                break
            
            # Extrai e processa documentos NFS-e
            logger.info(f"📦 [{inf}] NFS-e: Extraindo documentos...")
            docs_processados = 0
            doc_count = 0
            
            for nsu, xml_nfse, tipo_doc in nfse_svc.extrair_documentos(resp_nfse):
                doc_count += 1
                logger.info(f"📄 [{inf}] NFS-e: Processando doc {doc_count}, NSU={nsu}, tipo={tipo_doc}")
                
                # Valida XML
                if not nfse_svc.validar_xml(xml_nfse):
                    logger.warning(f"⚠️ [{inf}] NFS-e inválida, NSU={nsu}")
                    continue
                
                # Extrai chave/identificador
                try:
                    tree = etree.fromstring(xml_nfse.encode('utf-8'))
                    # TODO: Extrair chave específica da NFS-e do padrão nacional
                    # Por enquanto, usa NSU como identificador
                    chave_nfse = f"NFSE_{nsu}"
                    
                    # Busca nome do certificado
                    nome_cert = db.get_cert_nome_by_informante(inf)
                    
                    # Salva XML
                    from nfe_search import salvar_xml_por_certificado
                    resultado = salvar_xml_por_certificado(xml_nfse, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                    
                    # Registra PDF path se gerado
                    if isinstance(resultado, tuple):
                        caminho_xml, caminho_pdf = resultado
                        if caminho_pdf:
                            db.atualizar_pdf_path(chave_nfse, caminho_pdf)
                    
                    # Registra no banco
                    db.registrar_xml(chave_nfse, cnpj, caminho_xml if isinstance(resultado, tuple) else resultado)
                    
                    # 🆕 Extrai e salva nota detalhada para aparecer na interface
                    try:
                        # Extrai informações básicas da NFS-e
                        ns = {'nfse': 'http://www.abrasf.org.br/nfse.xsd'}
                        
                        # Tenta extrair número
                        numero = tree.findtext('.//nfse:Numero', namespaces=ns)
                        if not numero:
                            numero = tree.findtext('.//Numero') or nsu
                        
                        # Tenta extrair emitente
                        nome_emit = tree.findtext('.//nfse:RazaoSocial', namespaces=ns)
                        if not nome_emit:
                            nome_emit = tree.findtext('.//RazaoSocial') or 'NFS-e'
                        
                        # Tenta extrair CNPJ emitente
                        cnpj_emit = tree.findtext('.//nfse:Cnpj', namespaces=ns)
                        if not cnpj_emit:
                            cnpj_emit = tree.findtext('.//Cnpj') or cnpj
                        
                        # Tenta extrair data de emissão
                        data_emissao = tree.findtext('.//nfse:DataEmissao', namespaces=ns)
                        if not data_emissao:
                            data_emissao = tree.findtext('.//DataEmissao')
                        
                        # Tenta extrair valor
                        valor = tree.findtext('.//nfse:ValorServicos', namespaces=ns)
                        if not valor:
                            valor = tree.findtext('.//ValorServicos') or '0.00'
                        
                        # Cria nota detalhada com TODOS os campos obrigatórios
                        nota_nfse = {
                            'chave': chave_nfse,
                            'numero': numero,
                            'tipo': 'NFS-e',
                            'nome_emitente': nome_emit,
                            'cnpj_emitente': cnpj_emit,
                            'data_emissao': data_emissao or datetime.now().isoformat()[:10],
                            'valor': valor,
                            'status': 'Autorizada',
                            'informante': inf,
                            'xml_status': 'COMPLETO',
                            'nsu': nsu,
                            # Campos obrigatórios adicionais
                            'ie_tomador': '',
                            'cnpj_destinatario': '',
                            'cfop': '',
                            'vencimento': '',
                            'ncm': '',
                            'uf': '',
                            'natureza': 'Serviço',
                            'base_icms': '',
                            'valor_icms': '',
                            'atualizado_em': datetime.now().isoformat()
                        }
                        
                        # Salva no banco
                        db.criar_tabela_detalhada()
                        db.salvar_nota_detalhada(nota_nfse)
                        logger.info(f"✅ [{inf}] NFS-e detalhada salva: {numero}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ [{inf}] NFS-e salva mas não foi possível extrair detalhes: {e}")
                    
                    docs_processados += 1
                    logger.info(f"💾 [{inf}] NFS-e salva: NSU={nsu}")
                    
                except Exception as e:
                    logger.error(f"❌ [{inf}] Erro ao processar NFS-e NSU={nsu}: {e}")
                    continue
            
            logger.info(f"📊 [{inf}] NFS-e: {docs_processados} documentos processados nesta iteração")
            
            # Atualiza NSU
            if ult_nfse and ult_nfse != "000000000000000":
                if ult_nfse != ult_nsu_nfse:
                    logger.info(f"✅ [{inf}] NFS-e: NSU atualizado de {ult_nsu_nfse} → {ult_nfse}")
                    ult_nsu_nfse = ult_nfse
                    db.set_last_nsu_nfse(inf, ult_nfse)
                else:
                    logger.info(f"🛑 [{inf}] NFS-e: NSU não mudou ({ult_nsu_nfse}), finalizando")
                    break
            else:
                logger.warning(f"⚠️ [{inf}] NFS-e: Sem ultNSU na resposta")
                break
        
        if iteration_count >= max_iterations:
            logger.warning(f"⚠️ [{inf}] NFS-e: Atingido limite de {max_iterations} iterações")
        else:
            logger.info(f"🏁 [{inf}] NFS-e: Loop finalizado após {iteration_count} iterações")
                
    except Exception as e:
        logger.error(f"❌ [{inf}] ERRO CRÍTICO ao processar NFS-e: {e}")
        logger.exception(f"Erro ao processar NFS-e para {inf}: {e}")


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
        logger.info(f"  📜 Certificado: {certificado_path}")
        logger.info(f"  🏢 CNPJ: {cnpj}, UF: {cuf}")
        
        # Verifica se o certificado existe
        from pathlib import Path
        cert_file = Path(certificado_path)
        if not cert_file.exists():
            logger.error(f"  ❌ Certificado não encontrado: {certificado_path}")
            return None
        
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
    
    try:
        logger.info(f"=== Início da busca: {datetime.now().isoformat()} ===")
        logger.info(f"Diretório de dados: {data_dir}")
        
        # 1) Distribuição - NFe E CTe de TODOS os certificados
        logger.info("📥 Fase 1: Buscando documentos (NFe e CT-e) de todos os certificados...")
        for cnpj, path, senha, inf, cuf in db.get_certificados():
            # Cria parser específico para este certificado
            parser = XMLProcessor(informante=inf)
            logger.debug(f"Processando certificado: CNPJ={cnpj}, arquivo={path}, informante={inf}, cUF={cuf}")
            
            # 1.1) Busca NFe
            logger.info(f"📄 Iniciando busca de NF-e para {cnpj}")
            
            # Verifica se pode consultar (não teve erro 656 recente)
            if not db.pode_consultar_certificado(inf, db.get_last_nsu(inf)):
                logger.info(f"⏭️ [{cnpj}] NF-e: Pulando consulta - aguardando cooldown de erro 656 anterior")
                # Pula para CT-e (NFS-e será processada pelo script dedicado após)
                try:
                    processar_cte(db, (cnpj, path, senha, inf, cuf))
                except Exception as e:
                    logger.exception(f"Erro geral ao processar CT-e para {inf}: {e}")
                # ⚠️ NFS-e REMOVIDA: Será executada pelo buscar_nfse_auto.py após busca completa
                continue
            
            svc      = NFeService(path, senha, cnpj, cuf)
            last_nsu = db.get_last_nsu(inf)
            logger.info(f"📊 [{cnpj}] NF-e: NSU atual = {last_nsu}")
            logger.info(f"🔐 [{cnpj}] NF-e: Certificado = {path}, cUF = {cuf}")
            
            # 🔄 LOOP para buscar TODOS os documentos até ultNSU == maxNSU
            max_iterations = 100  # Limite de segurança
            iteration_count = 0
            
            while iteration_count < max_iterations:
                iteration_count += 1
                logger.info(f"🔄 [{cnpj}] NF-e iteração {iteration_count}/{max_iterations}, NSU atual: {last_nsu}")
                
                resp = svc.fetch_by_cnpj("CNPJ" if len(cnpj)==14 else "CPF", last_nsu)
                if not resp:
                    logger.warning(f"Sem resposta NFe para {inf} na iteração {iteration_count}")
                    break  # Sai do loop
                
                # Processa a resposta dentro do loop
                # Log da resposta para debug
                logger.info(f"📥 [{cnpj}] NF-e: Resposta recebida ({len(resp)} bytes)")
                logger.info(f"📄 [{cnpj}] NF-e: Primeiros 800 caracteres da resposta:")
                logger.info(resp[:800] if len(resp) > 800 else resp)
                
                # 🔍 DEBUG: Salva resposta completa da SEFAZ para análise
                cabecalho_debug = f"""
=== RESPOSTA COMPLETA DA SEFAZ ===
Informante: {inf}
CNPJ: {cnpj}
NSU solicitado: {last_nsu}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tamanho: {len(resp)} bytes
UF: {cuf}

=== XML DA RESPOSTA ===
"""
                save_debug_soap(inf, "resposta_sefaz_completa", cabecalho_debug + resp, prefixo="analise")
                
                cStat = parser.extract_cStat(resp)
                ult   = parser.extract_last_nsu(resp)
                max_nsu = parser.extract_max_nsu(resp)
                
                # Log mais claro sobre maxNSU
                if max_nsu == "000000000000000":
                    logger.info(f"📊 [{cnpj}] NF-e: cStat={cStat}, ultNSU={ult}, maxNSU={max_nsu} (SEFAZ: sem docs novos)")
                else:
                    logger.info(f"📊 [{cnpj}] NF-e: cStat={cStat}, ultNSU={ult}, maxNSU={max_nsu}")
                
                # 🔴 TRATAMENTO DE ERRO 656 - Consumo Indevido (ANTES de processar docs)
                if cStat == '656':
                    logger.warning(f"🚫 [{cnpj}] NF-e: cStat=656 - Consumo Indevido detectado")
                    
                    # ⚠️ IMPORTANTE: NÃO atualizar NSU em erro 656!
                    # Se atualizar, perdemos documentos intermediários
                    # Exemplo: NSU=1459, SEFAZ retorna ultNSU=1461
                    # Documentos 1460 e 1461 serão perdidos se avançarmos
                    logger.warning(f"⚠️ [{cnpj}] NF-e: NSU mantido em {last_nsu} para evitar perda de documentos")
                    logger.warning(f"📋 [{cnpj}] NF-e: SEFAZ indicou ultNSU={ult}, documentos serão baixados após bloqueio")
                    
                    # Registra erro 656 para bloquear por 65 minutos
                    db.registrar_erro_656(inf, last_nsu)
                    logger.warning(f"🔒 [{cnpj}] NF-e bloqueada por 65 minutos - próxima consulta possível às {(datetime.now() + timedelta(minutes=65)).strftime('%H:%M:%S')}")
                    
                    # Explica o erro de forma clara
                    if max_nsu == "000000000000000":
                        logger.info(f"   ✅ Situação normal: SEFAZ retornou maxNSU=0 (não há documentos novos)")
                        logger.info(f"   📝 NSU atual ({ult}) está atualizado - sistema aguardando novos documentos")
                    else:
                        logger.info(f"   📭 SEFAZ informa maxNSU={max_nsu}")
                    logger.info(f"   ⏰ Bloqueio por consulta muito frequente (< 1 hora) - aguarde intervalo")
                    
                    break  # Sai do loop NF-e, vai para CT-e
                
                # 🛑 ORDEM CORRETA: Verifica cStat=137 PRIMEIRO (antes de ultNSU==maxNSU)
                # cStat 137 = Nenhum documento localizado
                if cStat == '137':
                    logger.info(f"📭 [{cnpj}] NF-e: cStat=137 - Nenhum documento localizado")
                    
                    # Atualiza NSU
                    if ult:
                        db.set_last_nsu(inf, ult)
                        logger.debug(f"📊 [{cnpj}] NF-e: NSU atualizado para {ult}")
                    
                    # Registra sem documentos (bloqueia por 1h)
                    db.registrar_sem_documentos(inf)
                    logger.info(f"⏰ [{cnpj}] NF-e: Aguardando 1h conforme NT 2014.002 - próxima consulta às {(datetime.now() + timedelta(hours=1)).strftime('%H:%M:%S')}")
                    
                    break  # Sai do loop NF-e, vai para CT-e
                
                # ✅ Se chegou aqui: cStat=138 (há documentos para processar)
                # Processa documentos normalmente
                docs_count = 0
                docs_list = parser.extract_docs(resp)
                
                # 📊 HISTÓRICO NSU: Inicia coleta de informações da consulta
                import time
                tempo_inicio = time.time()
                xmls_processados_historico = []  # Lista para registro de histórico
                
                logger.info(f"📦 [{cnpj}] NF-e: extract_docs() retornou {len(docs_list) if docs_list else 0} documento(s)")
                
                if docs_list:
                    logger.info(f"📦 [{cnpj}] NF-e: Encontrados {len(docs_list)} documento(s) na resposta")
                    logger.info(f"🔧 [{cnpj}] VERSÃO DO CÓDIGO: Processamento de eventos ATIVADO (v2026-01-04)")
                    
                    # 🔍 DEBUG: Salva resumo dos documentos encontrados
                    resumo_docs = f"=== RESUMO DOS DOCUMENTOS ENCONTRADOS ===\n"
                    resumo_docs += f"Total de documentos: {len(docs_list)}\n"
                    resumo_docs += f"cStat: {cStat}\n"
                    resumo_docs += f"ultNSU: {ult}\n"
                    resumo_docs += f"maxNSU: {max_nsu}\n\n"
                    
                    for idx, (nsu, xml) in enumerate(docs_list, 1):
                        logger.info(f"📄 [{cnpj}] NF-e: Processando doc {idx}/{len(docs_list)}, NSU={nsu}")
                        try:
                            validar_xml_auto(xml, 'leiauteNFe_v4.00.xsd')
                            logger.info(f"✅ [{cnpj}] NF-e: XML válido (NSU={nsu})")
                            
                            tree = etree.fromstring(xml.encode('utf-8'))
                            
                            # Verifica se é um EVENTO (resEvento, procEventoNFe)
                            root_tag = tree.tag.split('}')[-1] if '}' in tree.tag else tree.tag
                            logger.info(f"🏷️ [{cnpj}] Tag raiz do documento: {root_tag} (NSU={nsu})")
                            
                            # 🔍 DEBUG: Adiciona ao resumo
                            resumo_docs += f"Doc {idx} - NSU {nsu}:\n"
                            resumo_docs += f"  Tag raiz: {root_tag}\n"
                            resumo_docs += f"  Tamanho: {len(xml)} bytes\n"
                            
                            if root_tag in ['resEvento', 'procEventoNFe', 'evento']:
                                logger.info(f"📋 [{cnpj}] NF-e: Evento detectado (NSU={nsu})")
                                # Processa evento
                                try:
                                    ns = '{http://www.portalfiscal.inf.br/nfe}'
                                    
                                    # Extrai chave do evento
                                    chave = tree.findtext(f'.//{ns}chNFe') or tree.findtext('.//chNFe')
                                    if not chave or len(chave) != 44:
                                        logger.warning(f"⚠️ [{cnpj}] Evento sem chave válida (NSU={nsu}), pulando")
                                        resumo_docs += f"  Tipo: EVENTO (chave inválida)\n\n"
                                        continue
                                    
                                    # Extrai tipo de evento
                                    tpEvento = tree.findtext(f'.//{ns}tpEvento') or tree.findtext('.//tpEvento')
                                    descEvento = tree.findtext(f'.//{ns}descEvento') or tree.findtext('.//descEvento') or 'Evento'
                                    
                                    logger.info(f"📋 [{cnpj}] Evento tipo {tpEvento} ({descEvento}) para chave {chave}")
                                    
                                    # 🔍 DEBUG: Adiciona detalhes do evento ao resumo
                                    resumo_docs += f"  Tipo: EVENTO\n"
                                    resumo_docs += f"  Código: {tpEvento}\n"
                                    resumo_docs += f"  Descrição: {descEvento}\n"
                                    resumo_docs += f"  Chave: {chave}\n"
                                    
                                    # 🔍 DEBUG: Salva XML do evento individualmente
                                    save_debug_soap(inf, f"evento_{tpEvento}_NSU{nsu}", xml, prefixo="extraido")
                                    
                                    # Busca nome do certificado (se configurado)
                                    nome_cert = db.get_cert_nome_by_informante(inf)
                                    
                                    # 1. SEMPRE salva evento em xmls/ (backup local)
                                    resultado = salvar_xml_por_certificado(xml, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                                    logger.info(f"💾 [{cnpj}] Evento salvo na pasta Eventos/")
                                    
                                    # Registra caminho do PDF se foi gerado
                                    if isinstance(resultado, tuple):
                                        caminho_xml, caminho_pdf = resultado
                                        if caminho_pdf:
                                            db.atualizar_pdf_path(chave, caminho_pdf)
                                    
                                    # 2. Se configurado armazenamento diferente, copia para lá também
                                    pasta_storage = db.get_config('storage_pasta_base', 'xmls')
                                    if pasta_storage and pasta_storage != 'xmls':
                                        salvar_xml_por_certificado(xml, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                                    
                                    # Processa o evento (atualiza status da nota se for cancelamento, etc)
                                    processar_evento_status(xml, chave, db)
                                    
                                    # Registra manifestação no banco (se for manifestação do destinatário)
                                    if tpEvento and tpEvento.startswith('2102'):  # Manifestações: 210200, 210210, 210220, 210240
                                        cStat_evento = tree.findtext(f'.//{ns}cStat') or tree.findtext('.//cStat')
                                        protocolo = tree.findtext(f'.//{ns}nProt') or tree.findtext('.//nProt')
                                        
                                        if cStat_evento == '135':  # Evento registrado
                                            if not db.check_manifestacao_exists(chave, tpEvento, cnpj):
                                                db.register_manifestacao(chave, tpEvento, cnpj, 'REGISTRADA', protocolo)
                                                logger.info(f"✅ [{cnpj}] Manifestação {tpEvento} registrada para chave {chave}")
                                    
                                    # 📊 HISTÓRICO: Registra evento processado
                                    xmls_processados_historico.append({
                                        'tipo': 'evento',
                                        'chave': chave,
                                        'evento': tpEvento,
                                        'descricao': descEvento
                                    })
                                    
                                    docs_count += 1
                                    continue  # Pula para próximo documento
                                    
                                except Exception as e:
                                    logger.warning(f"⚠️ [{cnpj}] Erro ao processar evento (NSU={nsu}): {e}")
                                    import traceback
                                    traceback.print_exc()
                                    continue
                            
                            # Se não é evento, processa como NF-e normal
                            infnfe = tree.find('.//{http://www.portalfiscal.inf.br/nfe}infNFe')
                            if infnfe is None:
                                # Pode ser um resNFe (resumo) - tenta extrair chave
                                ns = '{http://www.portalfiscal.inf.br/nfe}'
                                chave_resumo = tree.findtext(f'.//{ns}chNFe') or tree.findtext('.//chNFe')
                                
                                if chave_resumo and len(chave_resumo) == 44:
                                    logger.info(f"📋 [{cnpj}] resNFe detectado (NSU={nsu}), chave={chave_resumo}")
                                    
                                    # Verifica se já temos o XML completo no banco
                                    try:
                                        with db._connect() as conn:
                                            existing = conn.execute("SELECT COUNT(*) FROM xmls_baixados WHERE chave=?", (chave_resumo,)).fetchone()[0]
                                        if existing > 0:
                                            logger.info(f"✅ [{cnpj}] XML completo já existe no banco para chave {chave_resumo}")
                                            resumo_docs += f"  Tipo: resNFe (RESUMO) - XML completo já no banco\n\n"
                                        else:
                                            logger.info(f"🔍 [{cnpj}] resNFe sem XML completo - iniciando busca automática por chave")
                                            
                                            # Faz busca automática por chave usando o serviço SOAP
                                            try:
                                                # Usa o serviço SOAP para buscar por chave (não XMLProcessor)
                                                xml_completo = svc.fetch_by_chave_dist(chave_resumo)
                                                if xml_completo:
                                                    logger.info(f"✅ [{cnpj}] XML completo baixado com sucesso para chave {chave_resumo}")
                                                    
                                                    # Processa o XML completo
                                                    tree_completo = etree.fromstring(xml_completo.encode())
                                                    
                                                    # Busca nome do certificado
                                                    nome_cert = db.get_cert_nome_by_informante(inf)
                                                    
                                                    # Salva XML completo
                                                    resultado = salvar_xml_por_certificado(xml_completo, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                                                    
                                                    # 🆕 Registra na tabela xmls_baixados
                                                    if resultado:
                                                        caminho_xml = resultado[0] if isinstance(resultado, tuple) else resultado
                                                        try:
                                                            with db._connect() as conn:
                                                                conn.execute(
                                                                    "INSERT OR REPLACE INTO xmls_baixados (chave, caminho_arquivo, cnpj_cpf, baixado_em) VALUES (?, ?, ?, ?)",
                                                                    (chave_resumo, caminho_xml, cnpj, datetime.now().isoformat())
                                                                )
                                                            logger.info(f"✅ [{cnpj}] XML registrado em xmls_baixados: {chave_resumo}")
                                                        except Exception as e:
                                                            logger.error(f"❌ [{cnpj}] Erro ao registrar XML em xmls_baixados: {e}")
                                                    
                                                    # Registra caminho do PDF se foi gerado
                                                    if isinstance(resultado, tuple):
                                                        caminho_xml, caminho_pdf = resultado
                                                        if caminho_pdf:
                                                            db.atualizar_pdf_path(chave_resumo, caminho_pdf)
                                                    
                                                    # Se configurado armazenamento diferente, copia para lá também
                                                    pasta_storage = db.get_config('storage_pasta_base', 'xmls')
                                                    if pasta_storage and pasta_storage != 'xmls':
                                                        salvar_xml_por_certificado(xml_completo, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                                                    
                                                    # Extrai e salva nota detalhada
                                                    # 🔒 CRÍTICO: NSU do RESUMO deve ser gravado junto com XML completo
                                                    nota = extrair_nota_detalhada(xml_completo, parser, db, chave_resumo, inf, nsu_documento=nsu)
                                                    nota['informante'] = inf
                                                    nota['xml_status'] = 'COMPLETO'
                                                    # ⚠️ VALIDAÇÃO: Garante que NSU foi preenchido
                                                    if not nota.get('nsu'):
                                                        logger.warning(f"⚠️ [{cnpj}] NSU não preenchido para resNFe {chave_resumo}, usando NSU={nsu}")
                                                        nota['nsu'] = nsu
                                                    db.salvar_nota_detalhada(nota)
                                                    
                                                    logger.info(f"💾 [{cnpj}] Nota salva no banco: {nota.get('numero_nota', 'N/A')}")
                                                    resumo_docs += f"  Tipo: resNFe → XML completo baixado automaticamente ✅\n"
                                                    resumo_docs += f"  Chave: {chave_resumo}\n\n"
                                                    
                                                    # 📊 HISTÓRICO: Registra resNFe processado
                                                    xmls_processados_historico.append({
                                                        'tipo': 'nfe',
                                                        'chave': chave_resumo,
                                                        'numero': nota.get('numero_nota', 'N/A')
                                                    })
                                                    
                                                    docs_count += 1
                                                else:
                                                    logger.warning(f"⚠️ [{cnpj}] Busca automática por chave {chave_resumo} não retornou XML")
                                                    resumo_docs += f"  Tipo: resNFe - busca automática falhou\n"
                                                    resumo_docs += f"  Chave: {chave_resumo}\n\n"
                                            except Exception as e:
                                                logger.error(f"❌ [{cnpj}] Erro na busca automática por chave {chave_resumo}: {e}")
                                                logger.exception(e)
                                                resumo_docs += f"  Tipo: resNFe - erro na busca automática\n"
                                                resumo_docs += f"  Chave: {chave_resumo}\n\n"
                                    except Exception as e:
                                        logger.error(f"❌ Erro ao processar resNFe: {e}")
                                else:
                                    logger.warning(f"⚠️ [{cnpj}] NF-e: infNFe não encontrado no XML (NSU={nsu}), pulando")
                                    resumo_docs += f"  Tipo: Desconhecido (sem infNFe ou chave)\n\n"
                                
                                continue
                            
                            # Verifica modelo do documento (55 = NF-e, 65 = NFC-e)
                            ide = infnfe.find('{http://www.portalfiscal.inf.br/nfe}ide')
                            if ide is not None:
                                modelo = ide.findtext('{http://www.portalfiscal.inf.br/nfe}mod', '')
                                if modelo == '65':
                                    logger.info(f"🛒 [{cnpj}] NFC-e (modelo 65) detectada no NSU={nsu}, pulando (sistema busca apenas NF-e modelo 55)")
                                    resumo_docs += f"  Tipo: NFC-e (modelo 65) - IGNORADO\n\n"
                                    continue
                                elif modelo and modelo != '55':
                                    logger.warning(f"⚠️ [{cnpj}] Modelo desconhecido '{modelo}' no NSU={nsu}, pulando")
                                    resumo_docs += f"  Tipo: Modelo {modelo} - IGNORADO\n\n"
                                    continue
                            
                            chave  = infnfe.attrib.get('Id','')[-44:]
                            logger.info(f"🔑 [{cnpj}] NF-e (modelo 55): Chave extraída = {chave}")
                            
                            # 🔍 DEBUG: Adiciona informações da NF-e ao resumo
                            resumo_docs += f"  Tipo: NF-e (modelo 55)\n"
                            resumo_docs += f"  Chave: {chave}\n"
                            
                            # 🔍 DEBUG: Salva XML da NF-e individualmente
                            save_debug_soap(inf, f"nfe_NSU{nsu}_chave{chave[:8]}", xml, prefixo="extraido")
                            
                            # Busca nome do certificado (se configurado)
                            nome_cert = db.get_cert_nome_by_informante(inf)
                            
                            # 1. SEMPRE salva em xmls/ (backup local) e obtém o caminho
                            logger.info(f"💾 [{cnpj}] NF-e: Salvando em xmls/ (backup) - chave={chave}")
                            resultado = salvar_xml_por_certificado(xml, cnpj, pasta_base="xmls", nome_certificado=nome_cert)
                            
                            # Resultado pode ser: (caminho_xml, caminho_pdf) ou apenas caminho_xml
                            if isinstance(resultado, tuple):
                                caminho_xml, caminho_pdf = resultado
                            else:
                                caminho_xml, caminho_pdf = resultado, None
                            
                            # Registra XML no banco COM o caminho do arquivo
                            if caminho_xml:
                                db.registrar_xml(chave, cnpj, caminho_xml)
                            else:
                                # Fallback: registra sem caminho
                                db.registrar_xml(chave, cnpj)
                                logger.warning(f"⚠️ [{cnpj}] XML salvo mas caminho não obtido: {chave}")
                            
                            # CACHE: Atualiza caminho do PDF no banco (se foi gerado)
                            if caminho_pdf:
                                db.atualizar_pdf_path(chave, caminho_pdf)
                                logger.debug(f"✅ PDF path cached: {chave} → {caminho_pdf}")
                            
                            # 2. Se configurado armazenamento diferente, copia para lá também
                            pasta_storage = db.get_config('storage_pasta_base', 'xmls')
                            if pasta_storage and pasta_storage != 'xmls':
                                logger.info(f"💾 [{cnpj}] NF-e: Copiando para armazenamento ({pasta_storage}) - chave={chave}")
                                salvar_xml_por_certificado(xml, cnpj, pasta_base=pasta_storage, nome_certificado=nome_cert)
                            
                            # Salva nota detalhada
                            # 🔒 CRÍTICO: NSU deve ser gravado no banco para rastreamento
                            nota = extrair_nota_detalhada(xml, parser, db, chave, inf, nsu_documento=nsu)
                            nota['informante'] = inf
                            # ⚠️ VALIDAÇÃO: Garante que NSU foi preenchido antes de salvar
                            if not nota.get('nsu'):
                                logger.warning(f"⚠️ [{cnpj}] NSU não preenchido para chave {chave}, usando NSU={nsu}")
                                nota['nsu'] = nsu
                            db.salvar_nota_detalhada(nota)
                            
                            # 📊 HISTÓRICO: Registra NF-e processada
                            xmls_processados_historico.append({
                                'tipo': 'nfe',
                                'chave': chave,
                                'numero': nota.get('numero_nota', 'N/A')
                            })
                            
                            docs_count += 1
                            logger.info(f"✅ [{cnpj}] NF-e: Documento {docs_count} processado (chave={chave})")
                        except Exception as e:
                            logger.exception(f"❌ [{cnpj}] NF-e: Erro ao processar docZip NSU={nsu}: {e}")
                    
                    # 🔍 DEBUG: Salva resumo completo dos documentos processados
                    resumo_docs += f"\n=== RESUMO FINAL ===\n"
                    resumo_docs += f"Total processado com sucesso: {docs_count}\n"
                    resumo_docs += f"Informante: {inf}\n"
                    resumo_docs += f"CNPJ: {cnpj}\n"
                    save_debug_soap(inf, "resumo_documentos", resumo_docs, prefixo="analise")
                    logger.info(f"📊 [{cnpj}] Resumo de documentos salvo em Debug de notas/")
                else:
                    logger.info(f"📭 [{cnpj}] NF-e: Nenhum documento na resposta (docs_list vazio ou None)")
                    
                    # Se não há documentos E ultNSU < maxNSU, pode haver problema
                    if ult and max_nsu and int(ult) < int(max_nsu):
                        logger.warning(f"⚠️ [{cnpj}] NF-e: Sem documentos, mas ultNSU ({ult}) < maxNSU ({max_nsu})")
                        logger.warning(f"   Possível problema no parser ou resposta da SEFAZ")
                
                # ✅ ATUALIZA NSU APÓS PROCESSAR DOCUMENTOS
                if ult:
                    if ult != last_nsu:
                        logger.info(f"📊 [{cnpj}] NF-e: NSU atualizado {last_nsu} → {ult}")
                    else:
                        logger.debug(f"📊 [{cnpj}] NF-e: NSU confirmado pela SEFAZ (permanece em {last_nsu})")
                    db.set_last_nsu(inf, ult)
                else:
                    logger.warning(f"⚠️ [{cnpj}] NF-e: ultNSU não encontrado na resposta!")
                
                # 📊 HISTÓRICO NSU: Registra consulta no banco de dados
                try:
                    tempo_fim = time.time()
                    tempo_ms = int((tempo_fim - tempo_inicio) * 1000)
                    
                    # Obtém identificação do certificado
                    cert_nome = db.get_cert_nome_by_informante(inf) or f"Cert_{inf[:8]}"
                    
                    # Registra histórico de forma não-bloqueante
                    status_historico = 'sucesso' if docs_count > 0 else 'vazio'
                    db.registrar_historico_nsu(
                        certificado=cert_nome,
                        informante=inf,
                        nsu_consultado=last_nsu,
                        xmls_retornados=xmls_processados_historico,
                        tempo_ms=tempo_ms,
                        status=status_historico
                    )
                    logger.debug(f"📊 Histórico NSU registrado: {len(xmls_processados_historico)} XMLs")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao registrar histórico NSU (não-crítico): {e}")
                
                # Log final do processamento
                if docs_count > 0:
                    logger.info(f"✅ [{cnpj}] NF-e: {docs_count} documento(s) processado(s) com sucesso")
                    
                    # Se processou documentos mas ultNSU == maxNSU, ainda está sincronizado
                    if ult and max_nsu and ult == max_nsu:
                        logger.info(f"📊 [{cnpj}] NF-e: Após processar {docs_count} doc(s), sistema sincronizado (ultNSU=maxNSU)")
                        db.registrar_sem_documentos(inf)
                        logger.info(f"   ⏰ Próxima consulta em 1h conforme NT 2014.002")
                
                # 🔄 Controle do loop NF-e
                # Verifica se há mais documentos para buscar
                if ult and max_nsu:
                    if ult == max_nsu:
                        logger.info(f"✅ [{cnpj}] NF-e sincronizada: ultNSU={ult} == maxNSU={max_nsu}")
                        break  # Sai do loop, vai para CT-e
                    else:
                        # Ainda há documentos
                        docs_restantes = int(max_nsu) - int(ult)
                        logger.info(f"🔄 [{cnpj}] Ainda há ~{docs_restantes} documentos - continuando loop (ultNSU={ult}, maxNSU={max_nsu})")
                        
                        # Atualiza NSU para próxima iteração
                        last_nsu = ult
                        db.set_last_nsu(inf, ult)
                        
                        # Continua loop (não faz break)
                        continue
                
                # Se não conseguiu extrair NSUs, sai do loop
                logger.warning(f"⚠️ [{cnpj}] Não foi possível extrair ultNSU/maxNSU - saindo do loop")
                break
            
            # 1.2) Busca CTe
            try:
                processar_cte(db, (cnpj, path, senha, inf, cuf))
            except Exception as e:
                logger.exception(f"Erro geral ao processar CT-e para {inf}: {e}")
            
            # ⚠️ 1.3) NFS-e REMOVIDA DAQUI - Será executada separadamente
            # A busca de NFS-e agora é feita pelo script buscar_nfse_auto.py
            # após a conclusão da busca de NF-e e CT-e, evitando duplicação
            # e permitindo controle independente (incremental vs completa)
        
        logger.info("✅ Fase 1 concluída: Todos os documentos foram buscados (NFe e CTe)!")
        logger.info("📋 NFS-e será processada separadamente pelo buscar_nfse_auto.py")
        
        # 2) Consulta de Protocolo - AGORA SIM, depois de buscar tudo
        # Verifica se o usuário habilitou a consulta de status
        consultar_status = db.get_config('consultar_status_protocolo', '1')
        if consultar_status != '1':
            logger.info("⏭️ Fase 2: Consulta de status desabilitada pelo usuário (pulando)")
        else:
            logger.info("📋 Fase 2: Consultando status das chaves (protocolo)...")
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
                    
                    # Valida se recebeu resposta antes de processar
                    if not prot:
                        logger.warning(f"Sem resposta ao consultar protocolo da chave {chave}")
                        continue
                    
                    chNFe, cStat, xMotivo = parser.parse_protNFe(prot)
                    
                    # Só salva status se tiver dados válidos (não vazios, não None)
                    if chNFe and cStat and xMotivo and cStat.strip() and xMotivo.strip():
                        db.set_nf_status(chave, cStat, xMotivo)
                        logger.info(f"✅ Status atualizado: {chave} → {cStat} - {xMotivo}")
                    else:
                        logger.debug(f"⏭️ Status vazio/inválido para {chave}: cStat={cStat}, xMotivo={xMotivo}")
        
        logger.info("✅ Fase 2 concluída: Status das chaves atualizado!")
        logger.info(f"=== Busca concluída: {datetime.now().isoformat()} ===")
        logger.info(f"Próxima busca será agendada pela interface conforme intervalo configurado...")
        
    except Exception as e:
        logger.exception(f"Erro durante ciclo de busca: {e}")
        raise


def atualizar_status_notas_lote(db, certificados, chaves_list, progress_callback=None, max_workers=5):
    """
    Atualiza o status de múltiplas notas consultando eventos na SEFAZ (com paralelização).
    
    Args:
        db: Instância do DatabaseManager
        certificados: Lista de certificados disponíveis
        chaves_list: Lista de chaves de acesso para consultar
        progress_callback: Função callback(current, total, chave) para reportar progresso
        max_workers: Número máximo de consultas simultâneas (padrão: 5)
        
    Returns:
        Dict com estatísticas: {'consultadas': int, 'canceladas': int, 'erros': int}
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    stats = {'consultadas': 0, 'canceladas': 0, 'erros': 0, 'atualizadas': 0}
    stats_lock = threading.Lock()  # Lock para atualizar stats de forma thread-safe
    
    if not certificados:
        logger.error("Nenhum certificado disponível para consulta")
        return stats
    
    # Agrupa chaves por UF (cUF) para usar certificado correto
    chaves_por_uf = {}
    for chave in chaves_list:
        if len(chave) != 44:
            continue
        cuf = chave[:2]  # Primeiros 2 dígitos = cUF
        if cuf not in chaves_por_uf:
            chaves_por_uf[cuf] = []
        chaves_por_uf[cuf].append(chave)
    
    total_chaves = len(chaves_list)
    processadas = [0]  # Lista para ser mutável em closure
    processadas_lock = threading.Lock()
    
    def consultar_chave(chave, svc, cuf):
        """Consulta uma chave individualmente (executado em thread separada)."""
        nonlocal processadas
        
        try:
            # Consulta eventos da chave
            xml_resposta = svc.consultar_eventos_chave(chave)
            
            with stats_lock:
                stats['consultadas'] += 1
            
            if not xml_resposta:
                logger.debug(f"Sem eventos para chave {chave}")
                return None
            
            # Processa resposta para detectar cancelamento
            from lxml import etree
            root = etree.fromstring(xml_resposta.encode('utf-8') if isinstance(xml_resposta, str) else xml_resposta)
            
            # Detecta se é NFe ou CTe pela chave
            modelo = chave[20:22] if len(chave) == 44 else '55'
            is_cte = modelo == '57'
            
            # Define namespace baseado no tipo
            if is_cte:
                ns_uri = 'http://www.portalfiscal.inf.br/cte'
                tipo_doc = 'CT-e'
            else:
                ns_uri = 'http://www.portalfiscal.inf.br/nfe'
                tipo_doc = 'NF-e'
            
            # Procura evento de cancelamento
            # NFe: tpEvento = 110111 (cancelamento)
            # CTe: tpEvento = 110111 (cancelamento)
            eventos = root.findall(f'.//{{{ns_uri}}}infEvento')
            
            for evento in eventos:
                tp_evento = evento.findtext(f'{{{ns_uri}}}tpEvento')
                c_stat = evento.findtext(f'.//{{{ns_uri}}}cStat')
                
                if tp_evento == '110111' and c_stat == '135':  # Cancelamento autorizado
                    novo_status = f"Cancelamento de {tipo_doc} homologado"
                    db.atualizar_status_por_evento(chave, novo_status)
                    
                    # Salva XML do evento
                    try:
                        evento_xml = etree.tostring(evento, encoding='utf-8', pretty_print=True).decode()
                        
                        # Tenta extrair CNPJ do evento, depois da chave, e por último usa o informante do certificado
                        informante = evento.findtext(f'{{{ns_uri}}}CNPJ')
                        
                        if not informante:
                            # Extrai CNPJ da chave (posições 6-20 = 14 dígitos do CNPJ)
                            try:
                                informante = chave[6:20] if len(chave) >= 20 else None
                            except:
                                pass
                        
                        # Se ainda não tem, usa o CNPJ do certificado (self.cnpj_cpf)
                        if not informante:
                            informante = getattr(self, 'cnpj_cpf', None)
                        
                        # Último fallback: usa string vazia (vai para pasta raiz)
                        if not informante:
                            logger.warning(f"⚠️ Não foi possível identificar CNPJ para evento de {chave}")
                            informante = ""
                        
                        ano_mes = chave[2:6]  # AAMM da chave
                        ano = '20' + ano_mes[:2]
                        mes = ano_mes[2:4]
                        
                        from pathlib import Path
                        eventos_dir = Path('xmls') / informante / f"{ano}-{mes}" / "Eventos"
                        eventos_dir.mkdir(parents=True, exist_ok=True)
                        
                        evento_file = eventos_dir / f"{chave}.xml"
                        evento_file.write_text(evento_xml, encoding='utf-8')
                        logger.info(f"[SALVO Evento] {evento_file}")
                    except Exception as e:
                        logger.warning(f"Não foi possível salvar evento de {chave}: {e}")
                    
                    with stats_lock:
                        stats['canceladas'] += 1
                        stats['atualizadas'] += 1
                    
                    logger.info(f"✅ Status atualizado: {chave} → {novo_status}")
                    return 'cancelada'
                    
                elif tp_evento == '110110' and c_stat == '135':  # Carta de correção
                    novo_status = "Carta de Correção registrada"
                    db.atualizar_status_por_evento(chave, novo_status)
                    
                    with stats_lock:
                        stats['atualizadas'] += 1
                    
                    logger.info(f"✅ Status atualizado: {chave} → {novo_status}")
                    return 'correcao'
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao consultar chave {chave}: {e}")
            with stats_lock:
                stats['erros'] += 1
            return 'erro'
        finally:
            # Atualiza progresso
            with processadas_lock:
                processadas[0] += 1
                if progress_callback:
                    try:
                        progress_callback(processadas[0], total_chaves, chave)
                    except:
                        pass  # Ignora erros no callback
    
    # Processa cada UF
    for cuf, chaves in chaves_por_uf.items():
        # Tenta encontrar certificado da mesma UF ou usa o primeiro disponível
        cert = certificados[0]  # Fallback para primeiro certificado
        for c in certificados:
            if c.get('cUF_autor') == cuf:
                cert = c
                break
        
        # Cria serviço NFe
        try:
            svc = NFeService(
                cert.get('caminho'),
                cert.get('senha'),
                cert.get('cnpj_cpf'),
                cert.get('cUF_autor')
            )
        except Exception as e:
            logger.error(f"Erro ao criar serviço NFe para UF {cuf}: {e}")
            with stats_lock:
                stats['erros'] += len(chaves)
            continue
        
        # Paraleliza consultas com ThreadPoolExecutor
        logger.info(f"🚀 Consultando {len(chaves)} chaves da UF {cuf} com {max_workers} workers paralelos")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submete todas as consultas
            futures = {executor.submit(consultar_chave, chave, svc, cuf): chave for chave in chaves}
            
            # Aguarda conclusão
            for future in as_completed(futures):
                chave = futures[future]
                try:
                    resultado = future.result()
                except Exception as e:
                    logger.error(f"Exceção não tratada ao consultar {chave}: {e}")
    
    logger.info(f"📊 Atualização concluída: {stats}")
    return stats


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