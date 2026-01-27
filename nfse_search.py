"""
Busca de NFS-e (Nota Fiscal de Serviço Eletrônica)

NFS-e é diferente de NF-e:
- NF-e: Centralizado na SEFAZ (produtos)
- NFS-e: Descentralizado por município (serviços)

Cada cidade tem seu próprio sistema e provedor.
Principais provedores: Ginfes, ISS.NET, eISS, Betha, WebISS, SimplISS, etc.

⚠️ IMPORTANTE - SISTEMA ADN NACIONAL (Atualizado em 2025-12-18):
═══════════════════════════════════════════════════════════════════════════════
O ADN (Ambiente de Distribuição Nacional) NFS-e possui APIs REST, MAS:

✅ APIs Disponíveis no ADN:
   • POST /adn/DFe → EMISSÃO de novas NFS-e (não consulta)
   • POST /cnc/CNC → Cadastro/atualização de contribuintes
   • GET /cnc/consulta/cad → Consulta dados cadastrais de contribuintes
   • GET /danfse/{chaveAcesso} → Visualização DANFSe (PDF da nota)

❌ NÃO Existe no ADN (testado em 2025-12-18):
   • Endpoint de CONSULTA/DISTRIBUIÇÃO de NFS-e emitidas por período
   • Equivalente ao DFe de distribuição da NF-e
   • API REST para buscar notas já emitidas

🔄 Solução Atual:
   Para CONSULTAR NFS-e existentes, é necessário usar SOAP municipal.
   Muitos municípios estão com servidores em manutenção (exemplo: Campo Grande/MS).

Este script:
1. Lista certificados cadastrados no sistema
2. Permite configurar provedores de NFS-e por município
3. Busca notas fiscais de serviço via SOAP municipal
4. Mantém código ADN REST preparado para quando endpoint de consulta for disponibilizado
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import sqlite3
import logging
import re
from pathlib import Path
from datetime import datetime
from lxml import etree
import requests
from requests.exceptions import RequestException
import json
from nuvem_fiscal_api import NuvemFiscalAPI

# Importa sistema de criptografia
sys.path.insert(0, str(Path(__file__).parent))
try:
    from modules.security import get_portable_crypto
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("Módulo de criptografia não disponível")

# -------------------------------------------------------------------
# Consulta de CNPJ
# -------------------------------------------------------------------
def consultar_cnpj(cnpj):
    """
    Consulta dados do CNPJ via API pública.
    Retorna informações do município, razão social, etc.
    """
    # Remove formatação do CNPJ
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    
    logger.info(f"🔍 Consultando CNPJ {cnpj_limpo} via BrasilAPI...")
    
    try:
        # Tenta BrasilAPI primeiro (mais rápida)
        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            
            # Extrai informações
            municipio = dados.get('municipio', '')
            uf = dados.get('uf', '')
            razao_social = dados.get('razao_social', '')
            
            # Busca código IBGE do município
            codigo_ibge = buscar_codigo_ibge(municipio, uf)
            
            logger.info(f"✅ CNPJ consultado com sucesso!")
            logger.info(f"   Razão Social: {razao_social}")
            logger.info(f"   Município: {municipio}/{uf}")
            logger.info(f"   Código IBGE: {codigo_ibge}")
            
            return {
                "sucesso": True,
                "razao_social": razao_social,
                "municipio": municipio,
                "uf": uf,
                "codigo_ibge": codigo_ibge,
                "dados_completos": dados
            }
        else:
            logger.warning(f"⚠️  BrasilAPI retornou status {response.status_code}")
            
    except Exception as e:
        logger.warning(f"⚠️  Erro ao consultar BrasilAPI: {e}")
    
    # Fallback para ReceitaWS
    try:
        logger.info("🔄 Tentando ReceitaWS como alternativa...")
        url = f"https://receitaws.com.br/v1/cnpj/{cnpj_limpo}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            dados = response.json()
            
            if dados.get('status') == 'OK':
                municipio = dados.get('municipio', '')
                uf = dados.get('uf', '')
                razao_social = dados.get('nome', '')
                
                codigo_ibge = buscar_codigo_ibge(municipio, uf)
                
                logger.info(f"✅ CNPJ consultado via ReceitaWS!")
                logger.info(f"   Razão Social: {razao_social}")
                logger.info(f"   Município: {municipio}/{uf}")
                logger.info(f"   Código IBGE: {codigo_ibge}")
                
                return {
                    "sucesso": True,
                    "razao_social": razao_social,
                    "municipio": municipio,
                    "uf": uf,
                    "codigo_ibge": codigo_ibge,
                    "dados_completos": dados
                }
    except Exception as e:
        logger.error(f"❌ Erro ao consultar ReceitaWS: {e}")
    
    logger.error("❌ Não foi possível consultar o CNPJ em nenhuma API")
    return {
        "sucesso": False,
        "mensagem": "Erro ao consultar CNPJ. Verifique a conexão ou tente manualmente."
    }

def buscar_codigo_ibge(municipio, uf):
    """
    Busca o código IBGE de um município.
    Usa API do IBGE.
    """
    try:
        logger.debug(f"🔍 Buscando código IBGE para {municipio}/{uf}")
        
        # API do IBGE - lista municípios por UF
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            municipios = response.json()
            
            # Normaliza nome do município para comparação
            municipio_normalizado = municipio.upper().strip()
            
            for mun in municipios:
                nome_mun = mun.get('nome', '').upper().strip()
                
                if nome_mun == municipio_normalizado:
                    codigo = str(mun.get('id', ''))
                    logger.debug(f"✅ Código IBGE encontrado: {codigo}")
                    return codigo
            
            # Se não encontrou exato, tenta match parcial
            for mun in municipios:
                nome_mun = mun.get('nome', '').upper().strip()
                
                if municipio_normalizado in nome_mun or nome_mun in municipio_normalizado:
                    codigo = str(mun.get('id', ''))
                    logger.warning(f"⚠️  Match parcial encontrado: {mun.get('nome')} → {codigo}")
                    return codigo
            
            logger.warning(f"⚠️  Município {municipio}/{uf} não encontrado na base do IBGE")
            return ""
            
    except Exception as e:
        logger.error(f"❌ Erro ao buscar código IBGE: {e}")
        return ""

# -------------------------------------------------------------------
# Configuração de diretórios
# -------------------------------------------------------------------
def get_data_dir():
    """Retorna o diretório de dados do aplicativo."""
    if getattr(sys, 'frozen', False):
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "Busca XML"
    else:
        data_dir = Path(__file__).parent
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

BASE_DIR = get_data_dir()
DB_PATH = BASE_DIR / "nfe_data.db"  # Banco principal do sistema

# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
def setup_logger():
    """Configura logger para NFS-e."""
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    
    log_filename = LOGS_DIR / f"busca_nfse_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    logger = logging.getLogger("nfse_search")
    logger.setLevel(logging.DEBUG)
    
    # Remove handlers existentes
    logger.handlers.clear()
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
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
    
    return logger

logger = setup_logger()

# -------------------------------------------------------------------
# Provedores de NFS-e conhecidos
# -------------------------------------------------------------------
PROVEDORES_NFSE = {
    "GINFES": {
        "nome": "Ginfes",
        "descricao": "Sistema Nacional de Nota Fiscal de Serviço Eletrônica",
        "url_base": "https://nfse.ginfes.com.br/ServiceGinfesImpl",
        "municipios": ["Várias cidades"],
    },
    "ISSNET": {
        "nome": "ISS.NET",
        "descricao": "Sistema ISS Online",
        "url_base": "https://www.issnetonline.com.br",
        "municipios": ["São Paulo", "Campinas", "Santos"],
    },
    "EISS": {
        "nome": "e-ISS",
        "descricao": "Sistema e-ISS",
        "url_base": "https://www.eiss.com.br",
        "municipios": ["Curitiba", "Londrina"],
    },
    "BETHA": {
        "nome": "Betha Sistemas",
        "descricao": "Sistema Betha",
        "url_base": "https://e-gov.betha.com.br",
        "municipios": ["Várias cidades"],
    },
    "WEBISS": {
        "nome": "WebISS",
        "descricao": "Sistema WebISS",
        "url_base": "https://www.webiss.com.br",
        "municipios": ["Rio de Janeiro", "Niterói"],
    },
}

# -------------------------------------------------------------------
# Banco de Dados
# -------------------------------------------------------------------
class NFSeDatabase:
    """Gerencia banco de dados de NFS-e."""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._criar_tabelas()
    
    def _connect(self):
        """Cria conexão com o banco."""
        return sqlite3.connect(self.db_path)
    
    def _criar_tabelas(self):
        """Cria tabelas para NFS-e se não existirem."""
        with self._connect() as conn:
            # Tabela de configuração de provedores por certificado
            conn.execute('''
                CREATE TABLE IF NOT EXISTS nfse_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cnpj_cpf TEXT NOT NULL,
                    provedor TEXT NOT NULL,
                    codigo_municipio TEXT,
                    inscricao_municipal TEXT,
                    url_customizada TEXT,
                    ativo INTEGER DEFAULT 1,
                    UNIQUE(cnpj_cpf, codigo_municipio)
                )
            ''')
            
            # Tabela de NFS-e baixadas
            conn.execute('''
                CREATE TABLE IF NOT EXISTS nfse_baixadas (
                    numero_nfse TEXT PRIMARY KEY,
                    cnpj_prestador TEXT,
                    cnpj_tomador TEXT,
                    data_emissao TEXT,
                    valor_servico REAL,
                    xml_content TEXT,
                    data_download TEXT
                )
            ''')
            
            # Tabela de RPS (Recibo Provisório de Serviço)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rps (
                    numero_rps TEXT,
                    serie_rps TEXT,
                    cnpj_prestador TEXT,
                    data_emissao TEXT,
                    status TEXT,
                    numero_nfse TEXT,
                    PRIMARY KEY (numero_rps, serie_rps, cnpj_prestador)
                )
            ''')
            
            # Tabela de controle de NSU para NFS-e
            conn.execute('''
                CREATE TABLE IF NOT EXISTS nsu_nfse (
                    informante TEXT PRIMARY KEY,
                    ult_nsu INTEGER DEFAULT 0,
                    atualizado_em TEXT
                )
            ''')
            
            conn.commit()
            logger.debug("✅ Tabelas NFS-e criadas/verificadas")
    
    def get_certificados(self):
        """Busca certificados cadastrados no banco principal com senhas descriptografadas."""
        with self._connect() as conn:
            # Tenta buscar da tabela certificados_sefaz primeiro (tabela mais recente)
            cursor = conn.execute('''
                SELECT cnpj_cpf, caminho, senha, informante, cUF_autor 
                FROM certificados_sefaz
                WHERE ativo = 1
            ''')
            rows = cursor.fetchall()
            
            # Se não encontrar, tenta tabela antiga certificados
            if not rows:
                cursor = conn.execute('''
                    SELECT cnpj_cpf, caminho, senha, informante, cUF_autor 
                    FROM certificados
                ''')
                rows = cursor.fetchall()
            
            logger.info(f"📋 Encontrados {len(rows)} certificado(s) cadastrado(s)")
            
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
                                logger.debug(f"✅ Senha descriptografada para {informante}")
                            else:
                                logger.warning(f"⚠️  Senha do certificado {informante} está em texto plano")
                        except Exception as e:
                            logger.error(f"❌ Erro ao descriptografar senha de {informante}: {e}")
                    
                    decrypted_rows.append((cnpj, caminho, senha, informante, cuf))
                
                return decrypted_rows
            
            return rows
    
    def get_config_nfse(self, cnpj):
        """Busca configuração de NFS-e para um CNPJ."""
        with self._connect() as conn:
            cursor = conn.execute('''
                SELECT provedor, codigo_municipio, inscricao_municipal, url_customizada
                FROM nfse_config
                WHERE cnpj_cpf = ? AND ativo = 1
            ''', (cnpj,))
            return cursor.fetchall()
    
    def adicionar_config_nfse(self, cnpj, provedor, cod_municipio, inscricao_municipal, url=None):
        """Adiciona configuração de provedor NFS-e."""
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO nfse_config 
                (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada)
                VALUES (?, ?, ?, ?, ?)
            ''', (cnpj, provedor, cod_municipio, inscricao_municipal, url))
            conn.commit()
            logger.info(f"✅ Configuração NFS-e salva: {cnpj} → {provedor} (município {cod_municipio})")
    
    def salvar_nfse(self, numero, cnpj_prestador, cnpj_tomador, data_emissao, valor, xml):
        """Salva NFS-e baixada."""
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO nfse_baixadas
                (numero_nfse, cnpj_prestador, cnpj_tomador, data_emissao, valor_servico, 
                 xml_content, data_download)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (numero, cnpj_prestador, cnpj_tomador, data_emissao, valor, xml, 
                  datetime.now().isoformat()))
            conn.commit()
            logger.info(f"💾 NFS-e {numero} salva no banco")
    
    def get_last_nsu_nfse(self, informante):
        """Retorna o ultimo NSU processado para NFS-e de um informante."""
        with self._connect() as conn:
            cursor = conn.execute('''
                SELECT ult_nsu FROM nsu_nfse WHERE informante = ?
            ''', (informante,))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def set_last_nsu_nfse(self, informante, nsu):
        """Atualiza o ultimo NSU processado para NFS-e de um informante."""
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO nsu_nfse (informante, ult_nsu, atualizado_em)
                VALUES (?, ?, ?)
            ''', (informante, nsu, datetime.now().isoformat()))
            conn.commit()
            logger.debug(f"✅ NSU NFS-e atualizado: {informante} -> {nsu}")

# -------------------------------------------------------------------
# Mapeamento de URLs por município
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# Mapeamento de URLs por município
# -------------------------------------------------------------------
URLS_MUNICIPIOS = {
    "5002704": {  # Campo Grande/MS
        "nome": "Campo Grande",
        "uf": "MS",
        "urls": [
            # ⚠️ Sistema ADN Nacional NÃO possui endpoint de CONSULTA de NFS-e
            # Endpoints disponíveis no ADN (conforme swaggers oficiais):
            #   - POST /adn/DFe → EMISSÃO de notas (não consulta)
            #   - POST /cnc/CNC → Cadastro de contribuintes
            #   - GET /cnc/consulta/cad → Consulta cadastral
            #   - GET /danfse/{chave} → Visualização DANFSe
            # Para CONSULTA de notas emitidas, apenas SOAP municipal está disponível.
            # 
            # SOAP Municipal (em manutenção desde 2025 - página HTML):
            "https://nfse.pmcg.ms.gov.br/ws/nfse.asmx",
            "https://nfse.pmcg.ms.gov.br/IssWeb-ejb/IssWebWS/IssWebWS",
            "https://nfse.pmcg.ms.gov.br/nfse-web/services/NfseWSService",
            # Portal SEFAZ MS
            "https://nfe.sefaz.ms.gov.br/ws/nfse.asmx",
        ],
        "versao": "2.02",
        "provedor": "NUVEMFISCAL",  # 🌐 Usar Nuvem Fiscal (agregador moderno)
        "tipo_api": "REST"  # API REST com OAuth2 - sem certificado
    },
    "3550308": {  # São Paulo/SP
        "nome": "São Paulo",
        "uf": "SP",
        "urls": [
            "https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx",
        ],
        "versao": "1.00",
        "provedor": "Proprio"
    },
    "4106902": {  # Curitiba/PR
        "nome": "Curitiba",
        "uf": "PR",
        "urls": [
            "https://nfse.curitiba.pr.gov.br/nfse/servlet/nfse",
        ],
        "versao": "2.00",
        "provedor": "Proprio"
    },
}

def tentar_descobrir_url_municipio(codigo_ibge, nome_municipio, uf):
    """
    Tenta descobrir a URL do webservice do município.
    Retorna lista de URLs para tentar.
    """
    urls_padrao = []
    
    # Normaliza nome do município (lowercase, sem acentos)
    nome_limpo = nome_municipio.lower()
    nome_limpo = nome_limpo.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
    nome_limpo = nome_limpo.replace('é', 'e').replace('ê', 'e')
    nome_limpo = nome_limpo.replace('í', 'i')
    nome_limpo = nome_limpo.replace('ó', 'o').replace('õ', 'o').replace('ô', 'o')
    nome_limpo = nome_limpo.replace('ú', 'u')
    nome_limpo = nome_limpo.replace('ç', 'c')
    nome_limpo = nome_limpo.replace(' ', '')
    
    uf_lower = uf.lower()
    
    logger.debug(f"🔍 Tentando descobrir URLs para {nome_municipio}/{uf}")
    
    # Padrões comuns de URL de NFS-e
    padroes = [
        # IPM Sistemas (muito comum)
        f"https://issdigital.{nome_limpo}.{uf_lower}.gov.br/nfse-web/services/NfseWSService",
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/IssWeb-ejb/IssWebWS/IssWebWS",
        f"https://issdigital.{nome_limpo}.{uf_lower}.gov.br/ws/nfse.asmx",
        
        # Betha Sistemas
        f"https://{nome_limpo}.{uf_lower}.gov.br/e-nota/ws/nfse.asmx",
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/e-nota/ws/nfse.asmx",
        
        # Ginfes/ABRASF
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/ServiceGinfesImpl",
        
        # Sistemas próprios comuns
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/ws/nfse.asmx",
        f"https://nfse.{nome_limpo}.{uf_lower}.gov.br/wsNFe2/LoteRps.jws",
        f"https://notaeletronica.{nome_limpo}.{uf_lower}.gov.br/nfse.svc",
    ]
    
    for url in padroes:
        urls_padrao.append(url)
    
    logger.debug(f"   Geradas {len(urls_padrao)} URLs para testar")
    return urls_padrao

# -------------------------------------------------------------------
# Serviço de NFS-e
# -------------------------------------------------------------------
class NFSeService:
    """Serviço para buscar NFS-e de diferentes provedores."""
    
    def __init__(self, certificado_path, senha, cnpj):
        self.certificado_path = certificado_path
        self.senha = senha
        self.cnpj = cnpj
        logger.debug(f"🔐 NFSeService inicializado para {cnpj}")
    
    def extrair_cstat_nsu(self, xml_resposta):
        """
        Extrai cStat, ultNSU e maxNSU da resposta NFS-e.
        
        Args:
            xml_resposta: String, bytes ou dict (JSON) com resposta da API
        
        Returns:
            Tupla (cStat, ultNSU, maxNSU)
        """
        try:
            # Se for dict (JSON), tenta extrair campos
            if isinstance(xml_resposta, dict):
                cstat = xml_resposta.get('cStat', '')
                ult_nsu = xml_resposta.get('ultNSU', '000000000000000')
                max_nsu = xml_resposta.get('maxNSU', '000000000000000')
                logger.debug(f"[NFS-e] Extraido JSON: cStat={cstat}, ultNSU={ult_nsu}, maxNSU={max_nsu}")
                return cstat, ult_nsu, max_nsu
            
            # Converte bytes para string se necessario
            if isinstance(xml_resposta, bytes):
                xml_resposta = xml_resposta.decode('utf-8')
            
            tree = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Busca com e sem namespace
            NS_NFSE = 'http://www.portalfiscal.inf.br/nfse'
            ns = {'nfse': NS_NFSE}
            
            cstat = tree.findtext('.//nfse:cStat', namespaces=ns) or tree.findtext('.//cStat') or ''
            ult_nsu = tree.findtext('.//nfse:ultNSU', namespaces=ns) or tree.findtext('.//ultNSU') or '000000000000000'
            max_nsu = tree.findtext('.//nfse:maxNSU', namespaces=ns) or tree.findtext('.//maxNSU') or '000000000000000'
            
            logger.debug(f"[NFS-e] Extraido XML: cStat={cstat}, ultNSU={ult_nsu}, maxNSU={max_nsu}")
            return cstat, ult_nsu, max_nsu
            
        except Exception as e:
            logger.error(f"❌ [NFS-e] Erro ao extrair cStat/NSU: {e}")
            return '', '000000000000000', '000000000000000'
    
    def _formatar_data(self, data_str):
        """Converte DD/MM/YYYY para YYYY-MM-DD"""
        try:
            partes = data_str.split('/')
            if len(partes) == 3:
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
            return data_str
        except:
            return data_str
    
    def buscar_nuvemfiscal(self, cpf_cnpj, data_inicial, data_final, codigo_municipio=None, ambiente="producao"):
        """
        Busca NFS-e via API Nuvem Fiscal (agregador terceirizado).
        
        ✅ VANTAGENS:
        - API REST moderna com OAuth2
        - Sem necessidade de certificado digital
        - Unifica acesso a múltiplos municípios
        - Abstrai complexidade de diferentes provedores
        
        Args:
            cpf_cnpj: CPF/CNPJ do prestador
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            codigo_municipio: Código IBGE do município (opcional)
            ambiente: producao ou homologacao
        
        Returns:
            list: Lista de NFS-e encontradas
        """
        try:
            logger.info("🌐 Buscando NFS-e via Nuvem Fiscal...")
            
            # Inicializa cliente Nuvem Fiscal
            api = NuvemFiscalAPI()
            
            # Converte datas se necessário
            data_ini = self._formatar_data(data_inicial)
            data_fim = self._formatar_data(data_final)
            
            # Consulta NFS-e
            resultado = api.consultar_nfse(
                cpf_cnpj=cpf_cnpj,
                data_inicial=data_ini,
                data_final=data_fim,
                codigo_municipio=codigo_municipio,
                ambiente=ambiente,
                top=100  # Máximo por página
            )
            
            total = resultado.get('count', 0)
            notas = resultado.get('data', [])
            
            logger.info(f"✅ Encontradas {total} NFS-e no total")
            logger.info(f"   Retornadas nesta página: {len(notas)}")
            
            # Processar notas encontradas
            nfse_list = []
            for nota in notas:
                nfse_data = {
                    'numero': nota.get('numero'),
                    'codigo_verificacao': nota.get('codigo_verificacao'),
                    'data_emissao': nota.get('data_emissao'),
                    'cpf_cnpj_prestador': cpf_cnpj,
                    'cpf_cnpj_tomador': nota.get('declaracao_prestacao_servico', {}).get('tomador', {}).get('cpf_cnpj'),
                    'razao_social_tomador': nota.get('declaracao_prestacao_servico', {}).get('tomador', {}).get('razao_social'),
                    'valor_servicos': nota.get('declaracao_prestacao_servico', {}).get('servicos', [{}])[0].get('valor_servicos', 0),
                    'codigo_municipio': codigo_municipio,
                    'status': nota.get('status')
                }
                nfse_list.append(nfse_data)
                
                logger.info(f"\n   📄 NFS-e {nfse_data['numero']}")
                logger.info(f"      Data: {nfse_data['data_emissao']}")
                logger.info(f"      Tomador: {nfse_data['razao_social_tomador']}")
                logger.info(f"      Valor: R$ {nfse_data['valor_servicos']:.2f}")
                logger.info(f"      Status: {nfse_data['status']}")
            
            return nfse_list
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar via Nuvem Fiscal: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def buscar_adn_rest(self, codigo_municipio, inscricao_municipal, data_inicial, data_final, url_base):
        """
        Busca NFS-e via API REST Nacional (ADN).
        API Documentação: https://adn.producaorestrita.nfse.gov.br/docs/index.html
        
        ⚠️ LIMITAÇÃO IDENTIFICADA (2025-12-18):
        O endpoint POST /adn/DFe é destinado à EMISSÃO de notas fiscais, não à CONSULTA.
        Por isso, retorna erro E1242: "Tipo DF-e não tratado pelo Sistema Nacional NFS-e"
        quando tentamos enviar consultas no formato ABRASF ConsultarNfseEnvio.
        
        Para CONSULTAR NFS-e existentes, seria necessário:
        - Endpoint específico de distribuição/consulta do ADN (ainda não identificado)
        - OU usar SOAP municipal (muitos em manutenção)
        - OU endpoint similar ao DFe de NF-e para distribuição
        
        Status atual: Implementação pronta, aguardando identificação do endpoint correto.
        """
        logger.info(f"🌐 Tentando API REST Nacional (ADN): {url_base}")
        
        try:
            # Converte datas
            data_ini = self._formatar_data(data_inicial)
            data_fim = self._formatar_data(data_final)
            
            logger.info(f"📅 Período: {data_ini} a {data_fim}")
            
            # Monta XML de consulta (padrão ABRASF)
            cnpj_limpo = re.sub(r'\D', '', self.cnpj)
            
            xml_consulta = f"""<?xml version="1.0" encoding="UTF-8"?>
<ConsultarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Prestador>
        <Cnpj>{cnpj_limpo}</Cnpj>
        <InscricaoMunicipal>{inscricao_municipal if inscricao_municipal else ''}</InscricaoMunicipal>
    </Prestador>
    <PeriodoEmissao>
        <DataInicial>{data_ini}</DataInicial>
        <DataFinal>{data_fim}</DataFinal>
    </PeriodoEmissao>
</ConsultarNfseEnvio>"""
            
            # Compacta XML com GZIP e codifica em Base64
            import gzip
            import base64
            
            xml_gzip = gzip.compress(xml_consulta.encode('utf-8'))
            xml_b64 = base64.b64encode(xml_gzip).decode('ascii')
            
            logger.debug(f"📦 XML compactado: {len(xml_consulta)} bytes → {len(xml_gzip)} bytes")
            logger.debug(f"📦 Base64: {len(xml_b64)} caracteres")
            
            # Monta payload JSON para API REST
            payload = {
                "LoteXmlGZipB64": [xml_b64]
            }
            
            # Faz requisição POST para /adn/DFe (endpoint correto conforme swagger.json)
            if '/adn' not in url_base:
                url_recepcao = f"{url_base}/adn/DFe"
            else:
                url_recepcao = f"{url_base}/DFe"
            
            logger.info(f"📤 POST {url_recepcao}")
            
            import requests_pkcs12
            
            response = requests_pkcs12.post(
                url_recepcao,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                pkcs12_filename=self.certificado_path,
                pkcs12_password=self.senha,
                verify=False,
                timeout=30
            )
            
            logger.info(f"📥 Resposta: HTTP {response.status_code}")
            
            if response.status_code in [200, 201]:
                # Sucesso - processa resposta JSON
                logger.info("✅ API REST respondeu com sucesso!")
                
                try:
                    resposta = response.json()
                    logger.info(f"📊 Resposta JSON recebida")
                    logger.debug(f"Resposta: {resposta}")
                    
                    # Verifica tipo de ambiente
                    tipo_ambiente = resposta.get('TipoAmbiente', 'DESCONHECIDO')
                    logger.info(f"🌍 Ambiente: {tipo_ambiente}")
                    
                    # Processa documentos do lote
                    lote = resposta.get('Lote', [])
                    
                    if not lote:
                        logger.info("ℹ️  Nenhum documento no lote")
                        return {
                            "status": "sucesso",
                            "mensagem": "Nenhuma nota encontrada no período",
                            "notas": []
                        }
                    
                    logger.info(f"📦 Processando {len(lote)} documento(s)...")
                    
                    notas_processadas = []
                    erros_encontrados = []
                    
                    for idx, doc in enumerate(lote, 1):
                        # Verifica status do processamento
                        status_proc = doc.get('StatusProcessamento', '')
                        logger.info(f"   [{idx}/{len(lote)}] Status: {status_proc}")
                        
                        # Verifica se houve erros
                        erros = doc.get('Erros', [])
                        if erros:
                            for erro in erros:
                                codigo = erro.get('Codigo', '')
                                descricao = erro.get('Descricao', '')
                                logger.warning(f"      ⚠️  Erro {codigo}: {descricao}")
                                # E1242 = Endpoint de emissão sendo usado para consulta (uso incorreto)
                                if codigo == 'E1242':
                                    logger.warning(f"      ℹ️  Este endpoint é para EMISSÃO, não CONSULTA de notas")
                                erros_encontrados.append(f"{codigo}: {descricao}")
                        
                        # Descompacta XML do documento se disponível
                        xml_doc_b64 = doc.get('XmlGZipB64', '')
                        if xml_doc_b64:
                            xml_doc_gzip = base64.b64decode(xml_doc_b64)
                            xml_doc = gzip.decompress(xml_doc_gzip).decode('utf-8')
                            
                            # Parse do XML para extrair dados
                            root = etree.fromstring(xml_doc.encode('utf-8'))
                            
                            # Extrai informações básicas
                            numero = root.xpath('//Numero/text()')
                            numero = numero[0] if numero else 'N/A'
                            
                            valor = root.xpath('//ValorServicos/text()')
                            valor = float(valor[0]) if valor else 0.0
                            
                            data_emissao = root.xpath('//DataEmissao/text()')
                            data_emissao = data_emissao[0] if data_emissao else ''
                            
                            logger.info(f"      📄 NFS-e {numero} - R$ {valor:.2f}")
                            
                            notas_processadas.append({
                                "numero": numero,
                                "data_emissao": data_emissao,
                                "valor": valor,
                                "tomador_cnpj": "",
                                "xml": xml_doc
                            })
                    
                    # Monta mensagem de retorno
                    if notas_processadas:
                        mensagem = f"{len(notas_processadas)} nota(s) encontrada(s) via API REST ADN"
                        status = "sucesso"
                    elif erros_encontrados:
                        mensagem = f"Processado com erros: {'; '.join(erros_encontrados)}"
                        status = "erro"
                    else:
                        mensagem = "Nenhuma nota encontrada via API REST ADN"
                        status = "sucesso"
                    
                    if erros_encontrados:
                        logger.warning(f"⚠️  Total de erros: {len(erros_encontrados)}")
                    
                    return {
                        "status": status,
                        "mensagem": mensagem,
                        "notas": notas_processadas,
                        "erros": erros_encontrados if erros_encontrados else []
                    }
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar resposta JSON: {e}")
                    return {
                        "status": "erro",
                        "mensagem": f"Erro ao processar resposta: {str(e)}"
                    }
            
            elif response.status_code == 400:
                logger.warning("⚠️  Requisição inválida (400)")
                try:
                    erro = response.json()
                    logger.warning(f"Detalhes: {erro}")
                    return {
                        "status": "erro",
                        "mensagem": f"Requisição inválida: {erro}"
                    }
                except:
                    return {
                        "status": "erro",
                        "mensagem": f"Requisição inválida (400)"
                    }
            
            else:
                logger.warning(f"⚠️  HTTP {response.status_code}")
                return {
                    "status": "erro",
                    "mensagem": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            logger.error(f"❌ Erro na API REST: {e}")
            return {
                "status": "erro",
                "mensagem": f"Erro API REST: {str(e)[:100]}"
            }
    
    def buscar_ginfes(self, codigo_municipio, inscricao_municipal, data_inicial, data_final):
        """Busca NFS-e no provedor Ginfes/ABRASF ou API REST Nacional."""
        logger.info(f"🔍 Buscando NFS-e para município {codigo_municipio}")
        
        try:
            # Busca informações do município
            info_municipio = URLS_MUNICIPIOS.get(codigo_municipio)
            
            # Verifica se deve usar Nuvem Fiscal
            if info_municipio and info_municipio.get('provedor') == 'NUVEMFISCAL':
                logger.info(f"🌐 Usando Nuvem Fiscal para {info_municipio['nome']}/{info_municipio['uf']}")
                return self.buscar_nuvemfiscal(
                    cpf_cnpj=self.cnpj,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    codigo_municipio=codigo_municipio,
                    ambiente="producao"
                )
            
            urls_tentar = []
            tipo_api = "SOAP"  # Padrão
            
            if info_municipio:
                # Usa URLs configuradas
                urls_tentar = info_municipio.get('urls', [info_municipio.get('url')])
                tipo_api = info_municipio.get('tipo_api', 'SOAP')
                logger.info(f"✅ {info_municipio['nome']}/{info_municipio['uf']} - Tipo: {tipo_api}")
            else:
                logger.warning(f"⚠️  Município {codigo_municipio} não tem URL configurada")
                logger.info("🔍 Tentando descobrir URLs automaticamente...")
                
                # Tenta buscar dados do município via API IBGE
                try:
                    url_ibge = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{codigo_municipio}"
                    resp_ibge = requests.get(url_ibge, timeout=5)
                    
                    if resp_ibge.status_code == 200:
                        dados_mun = resp_ibge.json()
                        nome_mun = dados_mun.get('nome', '')
                        uf_mun = dados_mun['microrregiao']['mesorregiao']['UF']['sigla']
                        
                        logger.info(f"📍 Município identificado: {nome_mun}/{uf_mun}")
                        
                        # Gera URLs padrão
                        urls_tentar = tentar_descobrir_url_municipio(codigo_municipio, nome_mun, uf_mun)
                    else:
                        logger.warning("⚠️  Não foi possível consultar dados do município via IBGE")
                        urls_tentar = []
                        
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao consultar IBGE: {e}")
                    urls_tentar = []
            
            if not urls_tentar:
                logger.error("❌ Nenhuma URL disponível para tentar")
                return {
                    "status": "erro",
                    "mensagem": "Município sem URL configurada. Configure manualmente ou entre em contato com a prefeitura."
                }
            
            # Converte datas
            data_ini_formatada = self._formatar_data(data_inicial)
            data_fim_formatada = self._formatar_data(data_final)
            
            logger.info(f"📅 Período: {data_ini_formatada} a {data_fim_formatada}")
            
            # Monta XML de consulta (padrão ABRASF 2.02)
            cnpj_limpo = re.sub(r'\D', '', self.cnpj)
            
            # XML payload (conteúdo da consulta)
            xml_payload = f"""<ConsultarNfseEnvio xmlns="http://www.abrasf.org.br/nfse.xsd">
    <Prestador>
        <Cnpj>{cnpj_limpo}</Cnpj>
        <InscricaoMunicipal>{inscricao_municipal if inscricao_municipal else ''}</InscricaoMunicipal>
    </Prestador>
    <PeriodoEmissao>
        <DataInicial>{data_ini_formatada}</DataInicial>
        <DataFinal>{data_fim_formatada}</DataFinal>
    </PeriodoEmissao>
</ConsultarNfseEnvio>"""
            
            # SOAP Envelope completo (similar ao Fiscal.io)
            xml_consulta = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Body>
        <ConsultarNfseEnvioRequest xmlns="http://www.ginfes.com.br">
            <nfseCabecMsg><![CDATA[<?xml version="1.0" encoding="UTF-8"?><cabecalho versao="3" xmlns="http://www.abrasf.org.br/nfse.xsd"><versaoDados>3</versaoDados></cabecalho>]]></nfseCabecMsg>
            <nfseDadosMsg><![CDATA[{xml_payload}]]></nfseDadosMsg>
        </ConsultarNfseEnvioRequest>
    </soap:Body>
</soap:Envelope>"""
            
            logger.debug(f"📤 SOAP Envelope montado ({len(xml_consulta)} bytes)")
            
            # Tenta cada URL até obter sucesso
            logger.info(f"🔄 Testando {len(urls_tentar)} URL(s) - Tipo: {tipo_api}")
            
            for idx, url in enumerate(urls_tentar, 1):
                logger.info(f"🌐 [{idx}/{len(urls_tentar)}] Tentando: {url}")
                
                # ADN REST não possui endpoint de consulta - apenas SOAP municipal disponível
                # (API REST /adn/DFe é somente para EMISSÃO de notas)
                
                # SOAP tradicional
                try:
                    # Requisição com certificado
                    import requests_pkcs12
                    
                    response = requests_pkcs12.post(
                        url,
                        data=xml_consulta.encode('utf-8'),
                        headers={
                            'Content-Type': 'text/xml; charset=utf-8',
                            'SOAPAction': ''  # Vazio, igual Fiscal.io
                        },
                        pkcs12_filename=self.certificado_path,
                        pkcs12_password=self.senha,
                        verify=False,
                        timeout=15
                    )
                    
                    logger.info(f"📥 Resposta recebida: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Servidor respondeu com sucesso!")
                        logger.info(f"📄 Primeiros 1000 caracteres da resposta:")
                        logger.info(response.text[:1000])
                        logger.info("="*80)
                        
                        # Processa resposta XML
                        resultado = self._processar_resposta_ginfes(response.text)
                        
                        # Se processou com sucesso, retorna
                        if resultado['status'] != 'erro':
                            logger.info(f"✅ URL funcionou: {url}")
                            return resultado
                        else:
                            logger.warning(f"⚠️  URL respondeu mas com erro: {resultado['mensagem']}")
                            logger.warning(f"   Tentando próxima URL...")
                            # Continua para próxima URL
                            
                    elif response.status_code == 404:
                        logger.warning(f"⚠️  URL não encontrada (404)")
                        # Continua para próxima URL
                        
                    elif response.status_code == 500:
                        logger.warning(f"⚠️  Erro interno do servidor (500)")
                        logger.debug(f"Resposta: {response.text[:300]}")
                        # Pode ser erro no XML, tenta próxima URL
                        
                    else:
                        logger.warning(f"⚠️  Código HTTP inesperado: {response.status_code}")
                        
                except requests.exceptions.SSLError as e:
                    logger.warning(f"⚠️  Erro SSL nesta URL")
                    # Continua para próxima
                    
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"⚠️  Erro de conexão nesta URL")
                    # Continua para próxima
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"⚠️  Timeout (15s) nesta URL")
                    # Continua para próxima
                    
                except Exception as e:
                    logger.warning(f"⚠️  Erro inesperado nesta URL: {e}")
                    # Continua para próxima
            
            # Se chegou aqui, nenhuma URL funcionou
            logger.error("❌ Nenhuma URL funcionou")
            return {
                "status": "erro",
                "mensagem": f"Testadas {len(urls_tentar)} URLs sem sucesso. Verifique configuração do município ou entre em contato com a prefeitura."
            }
            
        except Exception as e:
            logger.exception(f"❌ Erro ao buscar Ginfes: {e}")
            return {"status": "erro", "mensagem": str(e)}
    
    def _processar_resposta_ginfes(self, xml_resposta):
        """Processa resposta XML do Ginfes."""
        try:
            logger.info("🔄 Processando resposta XML...")
            
            # Parse do XML
            root = etree.fromstring(xml_resposta.encode('utf-8'))
            
            # Namespace ABRASF
            ns = {'nfse': 'http://www.abrasf.org.br/nfse.xsd'}
            
            # Procura por erros
            erros = root.xpath('//MensagemRetorno/Mensagem', namespaces=ns)
            if erros:
                mensagens_erro = [erro.text for erro in erros]
                logger.warning(f"⚠️  Erros retornados pela prefeitura:")
                for msg in mensagens_erro:
                    logger.warning(f"   • {msg}")
                return {
                    "status": "erro_prefeitura",
                    "mensagem": "; ".join(mensagens_erro),
                    "notas": []
                }
            
            # Procura por NFS-e
            notas = root.xpath('//CompNfse', namespaces=ns)
            
            if not notas:
                logger.info("ℹ️  Nenhuma NFS-e encontrada no período")
                return {
                    "status": "sucesso",
                    "mensagem": "Nenhuma nota encontrada no período",
                    "notas": []
                }
            
            logger.info(f"✅ {len(notas)} NFS-e encontrada(s)!")
            
            notas_processadas = []
            for idx, nota in enumerate(notas, 1):
                try:
                    # Extrai dados da nota
                    numero = nota.xpath('.//Numero/text()', namespaces=ns)
                    numero = numero[0] if numero else f"nota_{idx}"
                    
                    data_emissao = nota.xpath('.//DataEmissao/text()', namespaces=ns)
                    data_emissao = data_emissao[0] if data_emissao else ""
                    
                    valor = nota.xpath('.//ValorServicos/text()', namespaces=ns)
                    valor = float(valor[0]) if valor else 0.0
                    
                    tomador_cnpj = nota.xpath('.//TomadorServico//Cnpj/text()', namespaces=ns)
                    tomador_cnpj = tomador_cnpj[0] if tomador_cnpj else ""
                    
                    logger.info(f"   📄 NFS-e {numero} - R$ {valor:.2f} - {data_emissao}")
                    
                    notas_processadas.append({
                        "numero": numero,
                        "data_emissao": data_emissao,
                        "valor": valor,
                        "tomador_cnpj": tomador_cnpj,
                        "xml": etree.tostring(nota, encoding='unicode')
                    })
                    
                except Exception as e:
                    logger.warning(f"⚠️  Erro ao processar nota {idx}: {e}")
            
            return {
                "status": "sucesso",
                "mensagem": f"{len(notas_processadas)} nota(s) encontrada(s)",
                "notas": notas_processadas
            }
            
        except etree.XMLSyntaxError as e:
            logger.error(f"❌ Erro ao fazer parse do XML: {e}")
            
            # Salva resposta em arquivo para análise
            try:
                debug_file = BASE / "logs" / f"nfse_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                debug_file.write_text(xml_resposta, encoding='utf-8')
                logger.info(f"💾 Resposta salva em: {debug_file}")
            except:
                pass
            
            logger.debug(f"XML recebido (primeiros 2000 chars): {xml_resposta[:2000]}")
            return {
                "status": "erro",
                "mensagem": f"Resposta inválida do servidor (XML malformado)",
                "notas": []
            }
        except Exception as e:
            logger.exception(f"❌ Erro ao processar resposta: {e}")
            return {
                "status": "erro",
                "mensagem": str(e),
                "notas": []
            }
    
    def buscar_issnet(self, codigo_municipio, inscricao_municipal, data_inicial, data_final):
        """Busca NFS-e no provedor ISS.NET."""
        logger.info(f"🔍 Buscando NFS-e no ISS.NET para município {codigo_municipio}")
        
        try:
            # ISS.NET usa REST em algumas cidades
            logger.debug(f"📤 Configurando busca ISS.NET")
            
            return {
                "status": "info",
                "mensagem": "Busca ISS.NET configurada (requer credenciais específicas do município)"
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar ISS.NET: {e}")
            return {"status": "erro", "mensagem": str(e)}

# -------------------------------------------------------------------
# Interface de Linha de Comando
# -------------------------------------------------------------------
def listar_certificados(db):
    """Lista todos os certificados cadastrados."""
    print("\n" + "="*80)
    print("📋 CERTIFICADOS CADASTRADOS NO SISTEMA")
    print("="*80)
    
    certificados = db.get_certificados()
    
    if not certificados:
        print("❌ Nenhum certificado encontrado!")
        print("   Configure certificados primeiro na interface principal.")
        return []
    
    for idx, (cnpj, caminho, senha, informante, cuf) in enumerate(certificados, 1):
        print(f"\n[{idx}] CNPJ/CPF: {cnpj}")
        print(f"    Informante: {informante}")
        print(f"    UF: {cuf}")
        print(f"    Certificado: {Path(caminho).name}")
        
        # Verifica se tem configuração NFS-e
        configs = db.get_config_nfse(cnpj)
        if configs:
            print(f"    ✅ NFS-e configurada: {len(configs)} município(s)")
            for provedor, cod_mun, insc_mun, url in configs:
                print(f"       → {provedor} (município {cod_mun})")
        else:
            print(f"    ⚠️  Sem configuração NFS-e")
    
    print("\n" + "="*80)
    return certificados

def listar_provedores():
    """Lista provedores de NFS-e disponíveis."""
    print("\n" + "="*80)
    print("🏢 PROVEDORES DE NFS-e DISPONÍVEIS")
    print("="*80)
    
    for codigo, info in PROVEDORES_NFSE.items():
        print(f"\n[{codigo}] {info['nome']}")
        print(f"    Descrição: {info['descricao']}")
        print(f"    URL Base: {info['url_base']}")
        print(f"    Municípios: {', '.join(info['municipios'][:3])}")
        if len(info['municipios']) > 3:
            print(f"                e outros...")
    
    print("\n" + "="*80)

def configurar_nfse(db, certificados):
    """Wizard para configurar NFS-e de um certificado."""
    print("\n" + "="*80)
    print("⚙️  CONFIGURAR NFS-e PARA CERTIFICADO")
    print("="*80)
    
    # Escolhe certificado
    print("\nEscolha o certificado:")
    for idx, (cnpj, *_) in enumerate(certificados, 1):
        print(f"[{idx}] {cnpj}")
    
    try:
        escolha = int(input("\nNúmero do certificado: "))
        if escolha < 1 or escolha > len(certificados):
            print("❌ Opção inválida!")
            return
        
        cnpj = certificados[escolha - 1][0]
        print(f"\n✅ Certificado selecionado: {cnpj}")
        
        # Consulta dados do CNPJ automaticamente
        print(f"\n🔍 Consultando dados do CNPJ na Receita Federal...")
        print("   (Isso pode levar alguns segundos...)")
        
        dados_cnpj = consultar_cnpj(cnpj)
        
        if dados_cnpj.get("sucesso"):
            print(f"\n✅ Dados encontrados!")
            print(f"   Razão Social: {dados_cnpj['razao_social']}")
            print(f"   Município: {dados_cnpj['municipio']}/{dados_cnpj['uf']}")
            print(f"   Código IBGE: {dados_cnpj['codigo_ibge']}")
            
            cod_municipio = dados_cnpj['codigo_ibge']
            
            # Permite editar se não encontrou ou usuário quer alterar
            if not cod_municipio:
                print("\n⚠️  Código IBGE não encontrado automaticamente.")
                cod_municipio = input("Digite o código do município (IBGE - 7 dígitos): ")
            else:
                confirma = input(f"\nUsar código {cod_municipio}? (S/n): ").strip().lower()
                if confirma == 'n':
                    cod_municipio = input("Digite o código do município (IBGE - 7 dígitos): ")
        else:
            print(f"\n⚠️  {dados_cnpj.get('mensagem', 'Erro ao consultar CNPJ')}")
            print("   Você precisará informar os dados manualmente.")
            cod_municipio = input("\nCódigo do município (IBGE - 7 dígitos): ")
        
        # Escolhe provedor
        print("\n" + "-"*80)
        print("Escolha o provedor de NFS-e:")
        provedores_lista = list(PROVEDORES_NFSE.keys())
        for idx, codigo in enumerate(provedores_lista, 1):
            print(f"[{idx}] {PROVEDORES_NFSE[codigo]['nome']} - {PROVEDORES_NFSE[codigo]['descricao']}")
        
        provedor_num = int(input("\nNúmero do provedor: "))
        if provedor_num < 1 or provedor_num > len(provedores_lista):
            print("❌ Opção inválida!")
            return
        
        provedor = provedores_lista[provedor_num - 1]
        print(f"✅ Provedor: {PROVEDORES_NFSE[provedor]['nome']}")
        
        # Solicita inscrição municipal
        print("\n" + "-"*80)
        inscricao_municipal = input("Inscrição Municipal (deixe vazio se não souber): ").strip()
        
        # Confirma antes de salvar
        print("\n" + "="*80)
        print("📋 CONFIRME OS DADOS:")
        print("="*80)
        print(f"CNPJ: {cnpj}")
        if dados_cnpj.get("sucesso"):
            print(f"Razão Social: {dados_cnpj['razao_social']}")
            print(f"Município: {dados_cnpj['municipio']}/{dados_cnpj['uf']}")
        print(f"Código IBGE: {cod_municipio}")
        print(f"Provedor: {PROVEDORES_NFSE[provedor]['nome']}")
        print(f"Inscrição Municipal: {inscricao_municipal if inscricao_municipal else '(não informada)'}")
        print("="*80)
        
        confirma = input("\nSalvar configuração? (S/n): ").strip().lower()
        if confirma == 'n':
            print("❌ Configuração cancelada!")
            return
        
        # Salva configuração
        db.adicionar_config_nfse(cnpj, provedor, cod_municipio, inscricao_municipal)
        
        print("\n✅ Configuração NFS-e salva com sucesso!")
        print(f"   CNPJ: {cnpj}")
        print(f"   Provedor: {provedor}")
        print(f"   Município: {cod_municipio}")
        print(f"   Inscrição: {inscricao_municipal if inscricao_municipal else '(vazio)'}")
        
    except ValueError:
        print("❌ Entrada inválida!")
    except Exception as e:
        logger.exception(f"Erro ao configurar NFS-e: {e}")
        print(f"❌ Erro: {e}")

def buscar_nfse_agora(db, certificados):
    """Executa busca de NFS-e."""
    print("\n" + "="*80)
    print("🔍 BUSCAR NFS-e")
    print("="*80)
    
    # Lista certificados com configuração
    certs_configurados = []
    for idx, (cnpj, caminho, senha, informante, cuf) in enumerate(certificados, 1):
        configs = db.get_config_nfse(cnpj)
        if configs:
            certs_configurados.append((idx, cnpj, caminho, senha, configs))
            print(f"\n[{idx}] {cnpj} - {len(configs)} município(s) configurado(s)")
            for provedor, cod_mun, insc_mun, url in configs:
                mun_info = URLS_MUNICIPIOS.get(cod_mun, {})
                mun_nome = mun_info.get('nome', cod_mun)
                print(f"    → {provedor} (município {mun_nome})")
    
    if not certs_configurados:
        print("\n❌ Nenhum certificado com NFS-e configurada!")
        print("   Use a opção 2 para configurar.")
        return
    
    try:
        escolha = int(input("\nEscolha o certificado para buscar: "))
        
        cert_escolhido = None
        for idx, cnpj, caminho, senha, configs in certs_configurados:
            if idx == escolha:
                cert_escolhido = (cnpj, caminho, senha, configs)
                break
        
        if not cert_escolhido:
            print("❌ Opção inválida!")
            return
        
        cnpj, caminho, senha, configs = cert_escolhido
        
        # Verifica se certificado existe
        if not Path(caminho).exists():
            print(f"\n❌ ERRO: Certificado não encontrado em:")
            print(f"   {caminho}")
            print("\n⚠️  Verifique se o arquivo existe ou reconfigure o certificado.")
            return
        
        # Solicita período
        print("\nPeríodo de busca:")
        data_inicial = input("Data inicial (DD/MM/YYYY): ")
        data_final = input("Data final (DD/MM/YYYY): ")
        
        # Validação básica de datas
        if not re.match(r'\d{2}/\d{2}/\d{4}', data_inicial) or not re.match(r'\d{2}/\d{2}/\d{4}', data_final):
            print("❌ Formato de data inválido! Use DD/MM/YYYY")
            return
        
        # Executa busca
        print(f"\n🚀 Iniciando busca de NFS-e para {cnpj}...")
        print("="*80)
        
        service = NFSeService(caminho, senha, cnpj)
        
        total_notas = 0
        
        for provedor, cod_mun, insc_mun, url in configs:
            mun_info = URLS_MUNICIPIOS.get(cod_mun, {})
            mun_nome = mun_info.get('nome', cod_mun)
            
            print(f"\n📡 Consultando {provedor} - {mun_nome}...")
            print("-"*80)
            
            if provedor == "GINFES":
                resultado = service.buscar_ginfes(cod_mun, insc_mun, data_inicial, data_final)
            elif provedor == "ISSNET":
                resultado = service.buscar_issnet(cod_mun, insc_mun, data_inicial, data_final)
            else:
                print(f"⚠️  Provedor {provedor} ainda não implementado")
                continue
            
            print(f"\n📊 Status: {resultado['status']}")
            print(f"📝 Mensagem: {resultado['mensagem']}")
            
            # Processa notas encontradas
            if resultado.get('notas'):
                notas = resultado['notas']
                print(f"\n✅ {len(notas)} nota(s) fiscal(is) encontrada(s):")
                print("="*80)
                
                for nota in notas:
                    print(f"\n📄 NFS-e Nº {nota['numero']}")
                    print(f"   Data: {nota['data_emissao']}")
                    print(f"   Valor: R$ {nota['valor']:.2f}")
                    print(f"   Tomador CNPJ: {nota['tomador_cnpj']}")
                    
                    # Salva no banco
                    try:
                        db.salvar_nfse(
                            nota['numero'],
                            cnpj,
                            nota['tomador_cnpj'],
                            nota['data_emissao'],
                            nota['valor'],
                            nota['xml']
                        )
                        print(f"   💾 Salva no banco de dados")
                    except Exception as e:
                        logger.error(f"Erro ao salvar nota {nota['numero']}: {e}")
                        print(f"   ⚠️  Erro ao salvar: {e}")
                
                total_notas += len(notas)
                print("-"*80)
        
        print("\n" + "="*80)
        if total_notas > 0:
            print(f"✅ Busca concluída! Total: {total_notas} nota(s) encontrada(s)")
        else:
            print(f"✅ Busca concluída! Nenhuma nota encontrada no período.")
        print("="*80)
        
    except ValueError:
        print("❌ Entrada inválida!")
    except Exception as e:
        logger.exception(f"❌ Erro ao buscar NFS-e: {e}")
        print(f"❌ Erro: {e}")

# -------------------------------------------------------------------
# Menu Principal
# -------------------------------------------------------------------
def menu_principal():
    """Menu interativo para NFS-e."""
    db = NFSeDatabase()
    
    print("\n" + "="*80)
    print("🏢 SISTEMA DE BUSCA DE NFS-e (Nota Fiscal de Serviço Eletrônica)")
    print("="*80)
    print("\nINFORMAÇÕES IMPORTANTES:")
    print("• NFS-e é diferente de NF-e (produtos)")
    print("• Cada município tem seu próprio sistema")
    print("• É necessário configurar o provedor do município")
    print("• Requer inscrição municipal do prestador")
    
    certificados = listar_certificados(db)
    
    while True:
        print("\n" + "-"*80)
        print("MENU:")
        print("[1] Listar provedores disponíveis")
        print("[2] Configurar NFS-e para um certificado")
        print("[3] Buscar NFS-e")
        print("[4] Listar certificados novamente")
        print("[0] Sair")
        print("-"*80)
        
        try:
            opcao = input("\nEscolha uma opção: ").strip()
            
            if opcao == "0":
                print("\n👋 Encerrando...")
                break
            elif opcao == "1":
                listar_provedores()
            elif opcao == "2":
                if not certificados:
                    print("❌ Nenhum certificado cadastrado!")
                else:
                    configurar_nfse(db, certificados)
            elif opcao == "3":
                if not certificados:
                    print("❌ Nenhum certificado cadastrado!")
                else:
                    buscar_nfse_agora(db, certificados)
            elif opcao == "4":
                certificados = listar_certificados(db)
            else:
                print("❌ Opção inválida!")
        
        except KeyboardInterrupt:
            print("\n\n👋 Encerrando...")
            break
        except Exception as e:
            logger.exception(f"Erro no menu: {e}")
            print(f"❌ Erro: {e}")

# -------------------------------------------------------------------
# Execução
# -------------------------------------------------------------------
if __name__ == "__main__":
    try:
        logger.info("="*80)
        logger.info("🚀 Iniciando Sistema de Busca de NFS-e")
        logger.info("="*80)
        
        menu_principal()
        
        logger.info("="*80)
        logger.info("✅ Sistema encerrado")
        logger.info("="*80)
        
    except Exception as e:
        logger.exception(f"❌ Erro fatal: {e}")
        print(f"\n❌ ERRO FATAL: {e}")
        input("\nPressione Enter para sair...")
