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

DEPENDÊNCIAS:
- lxml: Parse de XML (pip install lxml)
- requests: HTTP requests (pip install requests)
- requests_pkcs12: Autenticação com certificado (pip install requests-pkcs12)
- sqlite3: Banco de dados (built-in Python)
- pathlib: Manipulação de caminhos (built-in Python)

ESTRUTURA DE CLASSES:
- NFSeDatabase: Gerencia banco de dados SQLite com tabelas de NFS-e
- NFSeService: Comunica com APIs municipais (SOAP e REST)

TABELAS DO BANCO:
- nfse_config: Configuração de provedores por certificado/município
- nfse_baixadas: NFS-e já baixadas
- rps: Recibos Provisórios de Serviço (RPS)
- nsu_nfse: Controle de NSU (Número Sequencial Único) para distribuição

Para migrar para web:
1. Substituir sqlite3 por PostgreSQL/MySQL
2. Implementar autenticação OAuth2 para APIs REST
3. Usar certificados armazenados em HSM ou AWS KMS
4. Implementar fila de processamento (Celery/RabbitMQ)
5. Cache com Redis para consultas frequentes
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

# Importar nuvem_fiscal_api se disponível (agregador terceirizado)
try:
    from nuvem_fiscal_api import NuvemFiscalAPI
    NUVEM_FISCAL_AVAILABLE = True
except ImportError:
    NUVEM_FISCAL_AVAILABLE = False
    logging.warning("nuvem_fiscal_api não disponível - algumas funcionalidades limitadas")

# Importa sistema de criptografia (se disponível)
try:
    from modules.security import get_portable_crypto
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("Módulo de criptografia não disponível")

# -------------------------------------------------------------------
# Consulta de CNPJ via APIs públicas
# -------------------------------------------------------------------
def consultar_cnpj(cnpj):
    """
    Consulta dados do CNPJ via API pública.
    Retorna informações do município, razão social, etc.
    
    Tenta primeiro BrasilAPI (mais rápida), depois ReceitaWS como fallback.
    
    Args:
        cnpj (str): CNPJ com ou sem formatação
    
    Returns:
        dict: {
            "sucesso": bool,
            "razao_social": str,
            "municipio": str,
            "uf": str,
            "codigo_ibge": str,
            "dados_completos": dict
        }
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
    Usa API oficial do IBGE.
    
    Args:
        municipio (str): Nome do município
        uf (str): Sigla da UF (ex: MS, SP)
    
    Returns:
        str: Código IBGE de 7 dígitos ou vazio se não encontrado
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
    """
    Retorna o diretório de dados do aplicativo.
    
    Se executado como .exe (frozen), usa %APPDATA%/Busca XML
    Se executado como .py, usa diretório do script
    """
    if getattr(sys, 'frozen', False):
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "Busca XML"
    else:
        data_dir = Path(__file__).parent
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

BASE_DIR = get_data_dir()
DB_PATH = BASE_DIR / "notas.db"  # ⚠️ Banco principal do sistema

# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
def setup_logger():
    """Configura logger para NFS-e com arquivo diário."""
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    
    log_filename = LOGS_DIR / f"busca_nfse_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    logger = logging.getLogger("nfse_search")
    logger.setLevel(logging.DEBUG)
    
    # Remove handlers existentes para evitar duplicação
    logger.handlers.clear()
    
    # Handler para arquivo (DEBUG level)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Handler para console (INFO level)
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
        "versao": "2.02"
    },
    "ISSNET": {
        "nome": "ISS.NET",
        "descricao": "Sistema ISS Online",
        "url_base": "https://www.issnetonline.com.br",
        "municipios": ["São Paulo", "Campinas", "Santos"],
        "versao": "1.00"
    },
    "EISS": {
        "nome": "e-ISS",
        "descricao": "Sistema e-ISS",
        "url_base": "https://www.eiss.com.br",
        "municipios": ["Curitiba", "Londrina"],
        "versao": "2.00"
    },
    "BETHA": {
        "nome": "Betha Sistemas",
        "descricao": "Sistema Betha",
        "url_base": "https://e-gov.betha.com.br",
        "municipios": ["Várias cidades"],
        "versao": "2.02"
    },
    "WEBISS": {
        "nome": "WebISS",
        "descricao": "Sistema WebISS",
        "url_base": "https://www.webiss.com.br",
        "municipios": ["Rio de Janeiro", "Niterói"],
        "versao": "1.00"
    },
    "NUVEMFISCAL": {
        "nome": "Nuvem Fiscal",
        "descricao": "Agregador terceirizado com API REST moderna",
        "url_base": "https://api.nuvemfiscal.com.br",
        "municipios": ["Todos os municípios com integração"],
        "versao": "REST",
        "tipo_api": "REST",  # Diferente dos outros (SOAP)
        "requer_certificado": False,  # Usa OAuth2
    },
}

# -------------------------------------------------------------------
# Mapeamento de URLs por município (códigos IBGE)
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
    Tenta descobrir a URL do webservice do município automaticamente.
    Gera URLs padrão baseadas em convenções comuns.
    
    Args:
        codigo_ibge (str): Código IBGE de 7 dígitos
        nome_municipio (str): Nome do município
        uf (str): Sigla da UF
    
    Returns:
        list: Lista de URLs para testar (padrões comuns)
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
# Banco de Dados
# -------------------------------------------------------------------
class NFSeDatabase:
    """
    Gerencia banco de dados de NFS-e.
    
    Tabelas:
    - nfse_config: Configuração de provedores por CNPJ/município
    - nfse_baixadas: NFS-e já baixadas (histórico)
    - rps: Recibos Provisórios de Serviço
    - nsu_nfse: Controle de NSU para distribuição
    
    Importante: Esta classe usa o banco principal 'notas.db' do sistema.
    Para migração web, considerar PostgreSQL ou MySQL.
    """
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        logger.debug(f"🗄️  NFSeDatabase inicializado: {db_path}")
        self._criar_tabelas()
    
    def _connect(self):
        """Cria conexão com o banco SQLite."""
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
        """
        Busca certificados cadastrados no banco principal.
        
        ⚠️ ATENÇÃO: Este método depende da tabela 'certificados' do sistema principal.
        Para migração web, substituir por consulta à tabela de usuários/empresas.
        
        Returns:
            list: Lista de tuplas (cnpj, caminho, senha, informante, cuf)
        """
        with self._connect() as conn:
            try:
                cursor = conn.execute('''
                    SELECT cnpj_cpf, caminho, senha, informante, cuf
                    FROM certificados
                    WHERE ativo = 1
                ''')
                return cursor.fetchall()
            except sqlite3.OperationalError:
                logger.warning("⚠️  Tabela 'certificados' não encontrada no banco")
                return []
    
    def get_config_nfse(self, cnpj):
        """
        Busca configuração de NFS-e para um CNPJ.
        
        Args:
            cnpj (str): CNPJ do prestador
        
        Returns:
            list: Lista de tuplas (provedor, codigo_municipio, inscricao_municipal, url_customizada)
        """
        with self._connect() as conn:
            cursor = conn.execute('''
                SELECT provedor, codigo_municipio, inscricao_municipal, url_customizada
                FROM nfse_config
                WHERE cnpj_cpf = ? AND ativo = 1
            ''', (cnpj,))
            return cursor.fetchall()
    
    def adicionar_config_nfse(self, cnpj, provedor, cod_municipio, inscricao_municipal, url=None):
        """
        Adiciona ou atualiza configuração de provedor NFS-e.
        
        Args:
            cnpj (str): CNPJ do prestador
            provedor (str): Nome do provedor (ex: GINFES, ISSNET)
            cod_municipio (str): Código IBGE do município
            inscricao_municipal (str): Inscrição municipal
            url (str, optional): URL customizada do webservice
        """
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO nfse_config 
                (cnpj_cpf, provedor, codigo_municipio, inscricao_municipal, url_customizada)
                VALUES (?, ?, ?, ?, ?)
            ''', (cnpj, provedor, cod_municipio, inscricao_municipal, url))
            conn.commit()
            logger.info(f"✅ Configuração NFS-e salva: {cnpj} → {provedor} (município {cod_municipio})")
    
    def salvar_nfse(self, numero, cnpj_prestador, cnpj_tomador, data_emissao, valor, xml):
        """
        Salva NFS-e baixada no banco.
        
        Args:
            numero (str): Número da NFS-e
            cnpj_prestador (str): CNPJ do prestador
            cnpj_tomador (str): CNPJ do tomador
            data_emissao (str): Data de emissão (formato ISO)
            valor (float): Valor do serviço
            xml (str): Conteúdo XML completo da NFS-e
        """
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
        """
        Retorna o ultimo NSU processado para NFS-e de um informante.
        
        Args:
            informante (str): CNPJ do informante
        
        Returns:
            int: Último NSU processado (0 se nunca processou)
        """
        with self._connect() as conn:
            cursor = conn.execute('''
                SELECT ult_nsu FROM nsu_nfse WHERE informante = ?
            ''', (informante,))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def set_last_nsu_nfse(self, informante, nsu):
        """
        Atualiza o ultimo NSU processado para NFS-e de um informante.
        
        Args:
            informante (str): CNPJ do informante
            nsu (int): Novo NSU
        """
        with self._connect() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO nsu_nfse (informante, ult_nsu, atualizado_em)
                VALUES (?, ?, ?)
            ''', (informante, nsu, datetime.now().isoformat()))
            conn.commit()
            logger.debug(f"✅ NSU NFS-e atualizado: {informante} -> {nsu}")

# -------------------------------------------------------------------
# Serviço de NFS-e - Comunicação com APIs
# -------------------------------------------------------------------
class NFSeService:
    """
    Serviço para buscar NFS-e de diferentes provedores.
    
    Suporta:
    - SOAP municipal (padrão ABRASF)
    - REST ADN Nacional (limitado a emissão)
    - REST Nuvem Fiscal (agregador terceirizado)
    
    Autenticação:
    - Certificado digital A1 (.pfx) para SOAP e ADN
    - OAuth2 para Nuvem Fiscal
    
    Para migração web:
    - Armazenar certificados em HSM ou serviço cloud (AWS KMS, Azure Key Vault)
    - Implementar pool de conexões
    - Cache de consultas com Redis
    - Fila de processamento assíncrono (Celery)
    """
    
    def __init__(self, certificado_path, senha, cnpj):
        """
        Inicializa o serviço de NFS-e.
        
        Args:
            certificado_path (str): Caminho para arquivo .pfx do certificado
            senha (str): Senha do certificado
            cnpj (str): CNPJ do prestador
        """
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
            tuple: (cStat, ultNSU, maxNSU)
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
        """
        Converte DD/MM/YYYY para YYYY-MM-DD.
        
        Args:
            data_str (str): Data no formato DD/MM/YYYY
        
        Returns:
            str: Data no formato YYYY-MM-DD
        """
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
        - Documentação completa e suporte técnico
        
        ⚠️ DESVANTAGENS:
        - Serviço pago (custo por consulta/emissão)
        - Depende de disponibilidade de terceiro
        - Nem todos municípios disponíveis
        
        Args:
            cpf_cnpj (str): CPF/CNPJ do prestador
            data_inicial (str): Data inicial (YYYY-MM-DD ou DD/MM/YYYY)
            data_final (str): Data final (YYYY-MM-DD ou DD/MM/YYYY)
            codigo_municipio (str, optional): Código IBGE do município
            ambiente (str): 'producao' ou 'homologacao'
        
        Returns:
            list: Lista de NFS-e encontradas
        """
        if not NUVEM_FISCAL_AVAILABLE:
            logger.error("❌ nuvem_fiscal_api não está instalado")
            return []
        
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
    
    def buscar_ginfes(self, codigo_municipio, inscricao_municipal, data_inicial, data_final):
        """
        Busca NFS-e no provedor Ginfes/ABRASF ou API REST Nacional.
        
        Sequência de tentativa:
        1. Verifica se município tem Nuvem Fiscal configurado
        2. Tenta URLs SOAP configuradas para o município
        3. Tenta descobrir URLs automaticamente via padrões comuns
        
        Args:
            codigo_municipio (str): Código IBGE do município
            inscricao_municipal (str): Inscrição municipal do prestador
            data_inicial (str): Data inicial (DD/MM/YYYY)
            data_final (str): Data final (DD/MM/YYYY)
        
        Returns:
            dict: {
                "status": "sucesso" | "erro" | "erro_prefeitura",
                "mensagem": str,
                "notas": list
            }
        """
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
            
            # SOAP Envelope completo
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
                
                try:
                    # Requisição com certificado
                    import requests_pkcs12
                    
                    response = requests_pkcs12.post(
                        url,
                        data=xml_consulta.encode('utf-8'),
                        headers={
                            'Content-Type': 'text/xml; charset=utf-8',
                            'SOAPAction': ''
                        },
                        pkcs12_filename=self.certificado_path,
                        pkcs12_password=self.senha,
                        verify=False,
                        timeout=15
                    )
                    
                    logger.info(f"📥 Resposta recebida: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Servidor respondeu com sucesso!")
                        
                        # Processa resposta XML
                        resultado = self._processar_resposta_ginfes(response.text)
                        
                        # Se processou com sucesso, retorna
                        if resultado['status'] != 'erro':
                            logger.info(f"✅ URL funcionou: {url}")
                            return resultado
                        else:
                            logger.warning(f"⚠️  URL respondeu mas com erro: {resultado['mensagem']}")
                            logger.warning(f"   Tentando próxima URL...")
                            
                    elif response.status_code == 404:
                        logger.warning(f"⚠️  URL não encontrada (404)")
                        
                    elif response.status_code == 500:
                        logger.warning(f"⚠️  Erro interno do servidor (500)")
                        logger.debug(f"Resposta: {response.text[:300]}")
                        
                    else:
                        logger.warning(f"⚠️  Código HTTP inesperado: {response.status_code}")
                        
                except requests.exceptions.SSLError as e:
                    logger.warning(f"⚠️  Erro SSL nesta URL")
                    
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"⚠️  Erro de conexão nesta URL")
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"⚠️  Timeout (15s) nesta URL")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Erro inesperado nesta URL: {e}")
            
            # Se chegou aqui, nenhuma URL funcionou
            logger.error("❌ Nenhuma URL funcionou")
            return {
                "status": "erro",
                "mensagem": f"Testadas {len(urls_tentar)} URLs sem sucesso. Verifique configuração do município."
            }
            
        except Exception as e:
            logger.exception(f"❌ Erro ao buscar Ginfes: {e}")
            return {"status": "erro", "mensagem": str(e)}
    
    def _processar_resposta_ginfes(self, xml_resposta):
        """
        Processa resposta XML do Ginfes/ABRASF.
        
        Args:
            xml_resposta (str): XML de resposta do webservice
        
        Returns:
            dict: {
                "status": "sucesso" | "erro" | "erro_prefeitura",
                "mensagem": str,
                "notas": list of dict
            }
        """
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
                LOGS_DIR = BASE_DIR / "logs"
                LOGS_DIR.mkdir(exist_ok=True)
                debug_file = LOGS_DIR / f"nfse_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                debug_file.write_text(xml_resposta, encoding='utf-8')
                logger.info(f"💾 Resposta salva em: {debug_file}")
            except:
                pass
            
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

# -------------------------------------------------------------------
# Interface de Linha de Comando (CLI)
# -------------------------------------------------------------------
def listar_certificados(db):
    """Lista todos os certificados cadastrados no sistema."""
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
                # Implementar listagem de provedores
                pass
            elif opcao == "2":
                # Implementar configuração
                pass
            elif opcao == " 3":
#                 # Implementar busca
                pass
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
# Execução Principal
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
