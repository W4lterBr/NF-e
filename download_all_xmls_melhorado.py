# download_all_xmls_melhorado.py
"""
Sistema melhorado para processamento de XMLs de NF-e
- Progress bar com indicadores visuais detalhados
- Processamento paralelo para melhor performance
- Tratamento robusto de erros e validação
- Logs estruturados e informativos
- Estatísticas detalhadas de processamento
- Suporte a diferentes formatos de XML (procNFe, NFe, etc.)
"""

import os
import sys
import logging
import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET
from multiprocessing import cpu_count

# Imports locais
try:
    from modules.database import DatabaseManager
    from modules.utils import (
        only_digits, format_currency, format_date, sanitize_filename,
        validate_nfe_key, extract_uf_from_key, extract_year_month_from_key
    )
except ImportError:
    # Fallback se módulos não existirem
    def only_digits(s):
        return ''.join(filter(str.isdigit, s or ''))
    
    def format_currency(v):
        return str(v)
    
    def format_date(d):
        return d
    
    def sanitize_filename(s):
        return s
    
    def validate_nfe_key(k):
        return len(only_digits(k)) == 44
    
    def extract_uf_from_key(k):
        return k[:2] if len(k) >= 2 else ''
    
    def extract_year_month_from_key(k):
        return ('', '')

# ===============================================================================
# CONFIGURAÇÃO E ESTRUTURAS DE DADOS
# ===============================================================================

@dataclass
class ProcessingStats:
    """Estatísticas do processamento de XMLs"""
    total_files: int = 0
    processed_files: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    skipped_files: int = 0
    duplicate_keys: int = 0
    invalid_xmls: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> timedelta:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return timedelta()
    
    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.successful_extractions / self.total_files) * 100
    
    @property
    def processing_speed(self) -> float:
        """Arquivos por segundo"""
        if self.duration.total_seconds() == 0:
            return 0.0
        return self.processed_files / self.duration.total_seconds()

@dataclass
class ValidationResult:
    """Resultado da validação de um XML"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    nfe_data: Optional[Dict[str, Any]] = None

# ===============================================================================
# SISTEMA DE LOGGING AVANÇADO
# ===============================================================================

class ColoredFormatter(logging.Formatter):
    """Formatter com cores para diferentes níveis de log"""
    
    # Códigos de cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',    # Ciano
        'INFO': '\033[32m',     # Verde
        'WARNING': '\033[33m',  # Amarelo
        'ERROR': '\033[31m',    # Vermelho
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Adiciona cor baseada no nível
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)

def setup_logger(name: str, log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """Configura sistema de logging avançado"""
    logger = logging.getLogger(name)
    
    # Remove handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Nível de log
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Formato detalhado
    detailed_format = (
        '%(asctime)s | %(name)s | %(levelname)s | '
        '%(funcName)s:%(lineno)d | %(message)s'
    )
    
    # Console handler com cores
    console_handler = logging.StreamHandler()
    if os.name != 'nt':  # Unix/Linux
        console_formatter = ColoredFormatter(detailed_format)
    else:  # Windows
        console_formatter = logging.Formatter(detailed_format)
    
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # File handler (se especificado)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            detailed_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)  # Log completo em arquivo
        logger.addHandler(file_handler)
    
    return logger\n\n# ===============================================================================\n# PROGRESS BAR AVANÇADO\n# ===============================================================================\n\nclass AdvancedProgressBar:\n    \"\"\"Barra de progresso avançada com estatísticas em tempo real\"\"\"\n    \n    def __init__(self, total: int, description: str = \"Processando\", width: int = 50):\n        self.total = total\n        self.current = 0\n        self.description = description\n        self.width = width\n        self.start_time = datetime.now()\n        self.last_update = self.start_time\n        self.update_interval = 0.1  # Atualiza no máximo a cada 100ms\n    \n    def update(self, increment: int = 1, status: str = \"\"):\n        \"\"\"Atualiza progresso\"\"\"\n        self.current += increment\n        \n        # Throttle de atualizações para não sobrecarregar o terminal\n        now = datetime.now()\n        if (now - self.last_update).total_seconds() < self.update_interval and self.current < self.total:\n            return\n        \n        self.last_update = now\n        self._render(status)\n    \n    def _render(self, status: str = \"\"):\n        \"\"\"Renderiza a barra de progresso\"\"\"\n        # Calcula porcentagem\n        percentage = min(100.0, (self.current / self.total) * 100) if self.total > 0 else 0\n        \n        # Barra visual\n        filled = int(self.width * percentage / 100)\n        bar = '█' * filled + '░' * (self.width - filled)\n        \n        # Estatísticas de tempo\n        elapsed = datetime.now() - self.start_time\n        if self.current > 0:\n            avg_time = elapsed.total_seconds() / self.current\n            remaining = avg_time * (self.total - self.current)\n            eta = timedelta(seconds=int(remaining))\n            speed = self.current / elapsed.total_seconds()\n        else:\n            eta = timedelta()\n            speed = 0\n        \n        # Formata linha de status\n        status_line = (\n            f\"\\r{self.description}: [{bar}] \"\n            f\"{percentage:5.1f}% ({self.current:,}/{self.total:,}) | \"\n            f\"Velocidade: {speed:.1f}/s | \"\n            f\"ETA: {eta} | \"\n            f\"{status}\"\n        )\n        \n        # Limita tamanho da linha\n        terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80\n        if len(status_line) > terminal_width:\n            status_line = status_line[:terminal_width-3] + \"...\"\n        \n        print(status_line, end='', flush=True)\n    \n    def finish(self, message: str = \"Concluído\"):\n        \"\"\"Finaliza a barra de progresso\"\"\"\n        self.current = self.total\n        self._render(message)\n        print()  # Nova linha\n\n# ===============================================================================\n# PROCESSADOR DE XML AVANÇADO\n# ===============================================================================\n\nclass AdvancedXMLProcessor:\n    \"\"\"Processador avançado de XMLs com validação e extração robusta\"\"\"\n    \n    # Namespaces conhecidos\n    NAMESPACES = {\n        'nfe': 'http://www.portalfiscal.inf.br/nfe',\n        'nfce': 'http://www.portalfiscal.inf.br/nfe',  # NFCe usa mesmo namespace\n    }\n    \n    # Mapeamento de elementos raiz para tipos de documento\n    ROOT_ELEMENTS = {\n        'nfeProc': 'procNFe',\n        'NFe': 'NFe',\n        'procEventoNFe': 'Evento',\n        'resNFe': 'Resumo NFe',\n        'resEvento': 'Resumo Evento',\n    }\n    \n    def __init__(self, logger: logging.Logger):\n        self.logger = logger\n        self.processed_keys: Set[str] = set()\n    \n    def validate_xml_file(self, file_path: Path) -> ValidationResult:\n        \"\"\"Valida arquivo XML e extrai dados básicos\"\"\"\n        errors = []\n        warnings = []\n        \n        try:\n            # Verifica se arquivo existe e não está vazio\n            if not file_path.exists():\n                return ValidationResult(False, [\"Arquivo não encontrado\"], [])\n            \n            if file_path.stat().st_size == 0:\n                return ValidationResult(False, [\"Arquivo vazio\"], [])\n            \n            # Tenta fazer parse do XML\n            try:\n                tree = ET.parse(file_path)\n                root = tree.getroot()\n            except ET.ParseError as e:\n                return ValidationResult(False, [f\"XML mal formado: {e}\"], [])\n            \n            # Identifica tipo de documento\n            root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag\n            doc_type = self.ROOT_ELEMENTS.get(root_tag, \"Desconhecido\")\n            \n            if doc_type == \"Desconhecido\":\n                warnings.append(f\"Tipo de documento não reconhecido: {root_tag}\")\n            \n            # Extrai dados específicos do tipo\n            if doc_type in ['procNFe', 'NFe']:\n                nfe_data = self._extract_nfe_data(root)\n                if nfe_data:\n                    # Verifica chave duplicada\n                    chave = nfe_data.get('chave', '')\n                    if chave in self.processed_keys:\n                        warnings.append(f\"Chave duplicada: {chave}\")\n                    else:\n                        self.processed_keys.add(chave)\n                    \n                    return ValidationResult(True, errors, warnings, nfe_data)\n                else:\n                    errors.append(\"Não foi possível extrair dados da NF-e\")\n            else:\n                # Para outros tipos, apenas valida estrutura básica\n                warnings.append(f\"Tipo {doc_type} não suportado para extração de dados\")\n                return ValidationResult(True, errors, warnings)\n            \n            return ValidationResult(False, errors, warnings)\n            \n        except Exception as e:\n            self.logger.error(f\"Erro inesperado ao validar {file_path}: {e}\")\n            return ValidationResult(False, [f\"Erro inesperado: {e}\"], [])\n    \n    def _extract_nfe_data(self, root: ET.Element) -> Optional[Dict[str, Any]]:\n        \"\"\"Extrai dados estruturados de uma NF-e\"\"\"\n        try:\n            # Procura elemento NFe (pode estar dentro de nfeProc)\n            nfe_elem = self._find_element(root, './/nfe:NFe', self.NAMESPACES)\n            if nfe_elem is None:\n                nfe_elem = root if root.tag.endswith('NFe') else None\n            \n            if nfe_elem is None:\n                return None\n            \n            # Elemento infNFe\n            inf_nfe = self._find_element(nfe_elem, './/nfe:infNFe', self.NAMESPACES)\n            if inf_nfe is None:\n                return None\n            \n            # Extrai chave\n            chave = inf_nfe.get('Id', '').replace('NFe', '')[-44:]\n            if not validate_nfe_key(chave):\n                return None\n            \n            # Elementos principais\n            ide = self._find_element(inf_nfe, 'nfe:ide', self.NAMESPACES)\n            emit = self._find_element(inf_nfe, 'nfe:emit', self.NAMESPACES)\n            dest = self._find_element(inf_nfe, 'nfe:dest', self.NAMESPACES)\n            total = self._find_element(inf_nfe, './/nfe:ICMSTot', self.NAMESPACES)\n            \n            # Dados básicos\n            data = {\n                'chave': chave,\n                'numero': self._get_text(ide, 'nfe:nNF'),\n                'data_emissao': self._format_date_field(\n                    self._get_text(ide, 'nfe:dhEmi') or self._get_text(ide, 'nfe:dEmi')\n                ),\n                'cnpj_emitente': only_digits(self._get_text(emit, 'nfe:CNPJ') or self._get_text(emit, 'nfe:CPF')),\n                'nome_emitente': self._get_text(emit, 'nfe:xNome'),\n                'cnpj_destinatario': only_digits(self._get_text(dest, 'nfe:CNPJ') or self._get_text(dest, 'nfe:CPF')) if dest is not None else '',\n                'nome_destinatario': self._get_text(dest, 'nfe:xNome') if dest is not None else '',\n                'valor': self._get_text(total, 'nfe:vNF') if total is not None else '',\n                'tipo': 'NFCe' if self._get_text(ide, 'nfe:mod') == '65' else 'NFe',\n                'uf': self._get_text(ide, 'nfe:cUF'),\n                'natureza': self._get_text(ide, 'nfe:natOp'),\n                'ie_tomador': self._get_text(dest, 'nfe:IE') if dest is not None else '',\n                'atualizado_em': datetime.now().isoformat(),\n            }\n            \n            # Campos adicionais\n            data['cfop'] = self._get_text(inf_nfe, './/nfe:CFOP')\n            data['vencimento'] = self._format_date_field(self._get_text(inf_nfe, './/nfe:dVenc'))\n            \n            # Status do protocolo (se presente)\n            prot = self._find_element(root, './/nfe:protNFe/nfe:infProt', self.NAMESPACES)\n            if prot is not None:\n                cstat = self._get_text(prot, 'nfe:cStat')\n                xmotivo = self._get_text(prot, 'nfe:xMotivo')\n                if cstat and xmotivo:\n                    data['status'] = f\"{xmotivo} ({cstat})\"\n                else:\n                    data['status'] = 'Autorizado o uso da NF-e'\n            else:\n                data['status'] = 'Autorizado o uso da NF-e'\n            \n            return data\n            \n        except Exception as e:\n            self.logger.warning(f\"Erro ao extrair dados da NF-e: {e}\")\n            return None\n    \n    def _find_element(self, parent: ET.Element, path: str, namespaces: Dict[str, str] = None) -> Optional[ET.Element]:\n        \"\"\"Busca elemento com fallback para xpath sem namespace\"\"\"\n        try:\n            # Tenta com namespace\n            if namespaces:\n                elem = parent.find(path, namespaces)\n                if elem is not None:\n                    return elem\n            \n            # Fallback sem namespace\n            simple_path = path.replace('nfe:', '')\n            return parent.find(simple_path)\n            \n        except Exception:\n            return None\n    \n    def _get_text(self, parent: Optional[ET.Element], path: str) -> str:\n        \"\"\"Obtém texto de um elemento filho\"\"\"\n        if parent is None:\n            return ''\n        \n        elem = self._find_element(parent, path, self.NAMESPACES)\n        return elem.text.strip() if elem is not None and elem.text else ''\n    \n    def _format_date_field(self, date_str: str) -> str:\n        \"\"\"Formata campo de data\"\"\"\n        if not date_str:\n            return ''\n        \n        try:\n            # Remove parte de tempo\n            if 'T' in date_str:\n                date_str = date_str.split('T')[0]\n            \n            # Se já está em formato brasileiro, retorna\n            if '/' in date_str:\n                return date_str\n            \n            # Converte de ISO para brasileiro\n            dt = datetime.fromisoformat(date_str)\n            return dt.strftime('%d/%m/%Y')\n            \n        except Exception:\n            return date_str\n\n# ===============================================================================\n# SISTEMA DE CACHE E PERFORMANCE\n# ===============================================================================\n\nclass ProcessingCache:\n    \"\"\"Cache para otimizar processamento repetido\"\"\"\n    \n    def __init__(self, cache_file: Optional[Path] = None):\n        self.cache_file = cache_file\n        self.cache: Dict[str, Dict[str, Any]] = {}\n        self.load_cache()\n    \n    def load_cache(self):\n        \"\"\"Carrega cache do arquivo\"\"\"\n        if self.cache_file and self.cache_file.exists():\n            try:\n                with open(self.cache_file, 'r', encoding='utf-8') as f:\n                    self.cache = json.load(f)\n            except Exception as e:\n                logging.warning(f\"Erro ao carregar cache: {e}\")\n                self.cache = {}\n    \n    def save_cache(self):\n        \"\"\"Salva cache no arquivo\"\"\"\n        if self.cache_file:\n            try:\n                self.cache_file.parent.mkdir(parents=True, exist_ok=True)\n                with open(self.cache_file, 'w', encoding='utf-8') as f:\n                    json.dump(self.cache, f, indent=2, ensure_ascii=False)\n            except Exception as e:\n                logging.warning(f\"Erro ao salvar cache: {e}\")\n    \n    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:\n        \"\"\"Obtém informações em cache de um arquivo\"\"\"\n        key = str(file_path)\n        file_stat = file_path.stat()\n        \n        if key in self.cache:\n            cached_info = self.cache[key]\n            # Verifica se arquivo foi modificado\n            if cached_info.get('mtime') == file_stat.st_mtime and cached_info.get('size') == file_stat.st_size:\n                return cached_info.get('data')\n        \n        return None\n    \n    def set_file_info(self, file_path: Path, data: Dict[str, Any]):\n        \"\"\"Define informações em cache de um arquivo\"\"\"\n        key = str(file_path)\n        file_stat = file_path.stat()\n        \n        self.cache[key] = {\n            'mtime': file_stat.st_mtime,\n            'size': file_stat.st_size,\n            'data': data,\n            'cached_at': datetime.now().isoformat()\n        }\n\n# ===============================================================================\n# PROCESSADOR PRINCIPAL\n# ===============================================================================\n\ndef process_single_file(args: Tuple[Path, bool, Optional[Path]]) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:\n    \"\"\"Processa um único arquivo XML (função para processamento paralelo)\"\"\"\n    file_path, use_cache, cache_file = args\n    \n    try:\n        # Configura logger para o worker\n        logger = logging.getLogger(f\"worker_{os.getpid()}\")\n        \n        # Cache\n        cache = ProcessingCache(cache_file) if use_cache else None\n        \n        # Verifica cache primeiro\n        if cache:\n            cached_data = cache.get_file_info(file_path)\n            if cached_data:\n                return True, cached_data, []\n        \n        # Processa arquivo\n        processor = AdvancedXMLProcessor(logger)\n        result = processor.validate_xml_file(file_path)\n        \n        if result.is_valid and result.nfe_data:\n            # Salva no cache\n            if cache:\n                cache.set_file_info(file_path, result.nfe_data)\n                cache.save_cache()\n            \n            return True, result.nfe_data, result.warnings\n        else:\n            return False, None, result.errors + result.warnings\n            \n    except Exception as e:\n        return False, None, [f\"Erro inesperado: {str(e)}\"]\n\nclass XMLBatchProcessor:\n    \"\"\"Processador em lote de XMLs com paralelização\"\"\"\n    \n    def __init__(self, config: Dict[str, Any]):\n        self.config = config\n        self.logger = setup_logger(__name__, config.get('log_level', 'INFO'), config.get('log_file'))\n        self.stats = ProcessingStats()\n        \n        # Configurações\n        self.xml_root = Path(config.get('xml_dir', 'xmls'))\n        self.db_path = Path(config.get('db_path', 'notas.db'))\n        self.max_workers = config.get('max_workers', min(cpu_count(), 8))\n        self.use_cache = config.get('use_cache', True)\n        self.cache_file = Path(config.get('cache_file', 'processing_cache.json')) if self.use_cache else None\n        self.batch_size = config.get('batch_size', 1000)\n        \n        # Database manager\n        try:\n            self.db_manager = DatabaseManager(self.db_path)\n        except Exception:\n            # Fallback para SQLite simples\n            self.db_manager = None\n    \n    def find_xml_files(self) -> List[Path]:\n        \"\"\"Encontra todos os arquivos XML na estrutura de diretórios\"\"\"\n        xml_files = []\n        \n        if not self.xml_root.exists():\n            self.logger.warning(f\"Diretório de XMLs não encontrado: {self.xml_root}\")\n            return []\n        \n        # Busca recursiva por arquivos .xml\n        for xml_file in self.xml_root.rglob(\"*.xml\"):\n            if xml_file.is_file() and xml_file.stat().st_size > 0:\n                xml_files.append(xml_file)\n        \n        self.logger.info(f\"Encontrados {len(xml_files)} arquivos XML\")\n        return sorted(xml_files)\n    \n    def process_files_parallel(self, xml_files: List[Path]) -> ProcessingStats:\n        \"\"\"Processa arquivos em paralelo\"\"\"\n        self.stats.start_time = datetime.now()\n        self.stats.total_files = len(xml_files)\n        \n        # Progress bar\n        progress = AdvancedProgressBar(\n            total=len(xml_files),\n            description=\"Processando XMLs\"\n        )\n        \n        # Prepara argumentos para workers\n        worker_args = [(f, self.use_cache, self.cache_file) for f in xml_files]\n        \n        # Processa em lotes para não sobrecarregar memória\n        notes_to_save = []\n        \n        try:\n            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:\n                # Submete trabalhos em lotes\n                for i in range(0, len(worker_args), self.batch_size):\n                    batch = worker_args[i:i + self.batch_size]\n                    \n                    # Submete lote\n                    future_to_file = {executor.submit(process_single_file, args): args[0] for args in batch}\n                    \n                    # Coleta resultados do lote\n                    for future in as_completed(future_to_file):\n                        file_path = future_to_file[future]\n                        \n                        try:\n                            success, nfe_data, messages = future.result()\n                            \n                            self.stats.processed_files += 1\n                            \n                            if success and nfe_data:\n                                notes_to_save.append(nfe_data)\n                                self.stats.successful_extractions += 1\n                                \n                                # Log de warnings se houver\n                                if messages:\n                                    for msg in messages:\n                                        self.logger.warning(f\"{file_path.name}: {msg}\")\n                            else:\n                                self.stats.failed_extractions += 1\n                                \n                                # Log de erros\n                                if messages:\n                                    for msg in messages:\n                                        self.logger.error(f\"{file_path.name}: {msg}\")\n                            \n                            # Atualiza progress\n                            progress.update(1, f\"✓ {self.stats.successful_extractions} | ✗ {self.stats.failed_extractions}\")\n                            \n                        except Exception as e:\n                            self.logger.error(f\"Erro ao processar {file_path}: {e}\")\n                            self.stats.failed_extractions += 1\n                            progress.update(1, f\"Erro: {file_path.name}\")\n                    \n                    # Salva lote no banco\n                    if notes_to_save:\n                        self._save_notes_batch(notes_to_save)\n                        notes_to_save.clear()\n        \n        except KeyboardInterrupt:\n            self.logger.info(\"Processamento interrompido pelo usuário\")\n            progress.finish(\"Interrompido\")\n        except Exception as e:\n            self.logger.error(f\"Erro durante processamento paralelo: {e}\")\n            progress.finish(\"Erro\")\n        else:\n            progress.finish(\"Concluído\")\n        \n        # Salva notas restantes\n        if notes_to_save:\n            self._save_notes_batch(notes_to_save)\n        \n        self.stats.end_time = datetime.now()\n        return self.stats\n    \n    def _save_notes_batch(self, notes: List[Dict[str, Any]]):\n        \"\"\"Salva lote de notas no banco de dados\"\"\"\n        if not notes:\n            return\n        \n        try:\n            if self.db_manager:\n                # Usa DatabaseManager moderno\n                for note in notes:\n                    self.db_manager.save_note(note)\n            else:\n                # Fallback para SQLite direto\n                self._save_notes_sqlite(notes)\n                \n            self.logger.debug(f\"Salvo lote de {len(notes)} notas no banco\")\n            \n        except Exception as e:\n            self.logger.error(f\"Erro ao salvar lote no banco: {e}\")\n    \n    def _save_notes_sqlite(self, notes: List[Dict[str, Any]]):\n        \"\"\"Fallback para salvar notas usando SQLite direto\"\"\"\n        # Garante que tabela existe\n        self._ensure_table_exists()\n        \n        with sqlite3.connect(self.db_path) as conn:\n            for note in notes:\n                # INSERT OR REPLACE\n                columns = list(note.keys())\n                placeholders = ['?' for _ in columns]\n                \n                sql = f\"INSERT OR REPLACE INTO notas_detalhadas ({','.join(columns)}) VALUES ({','.join(placeholders)})\"\n                conn.execute(sql, list(note.values()))\n            \n            conn.commit()\n    \n    def _ensure_table_exists(self):\n        \"\"\"Garante que a tabela de notas detalhadas existe\"\"\"\n        with sqlite3.connect(self.db_path) as conn:\n            conn.execute('''\n                CREATE TABLE IF NOT EXISTS notas_detalhadas (\n                    chave TEXT PRIMARY KEY,\n                    numero TEXT,\n                    data_emissao TEXT,\n                    cnpj_emitente TEXT,\n                    nome_emitente TEXT,\n                    cnpj_destinatario TEXT,\n                    nome_destinatario TEXT,\n                    valor TEXT,\n                    cfop TEXT,\n                    tipo TEXT DEFAULT 'NFe',\n                    vencimento TEXT,\n                    status TEXT DEFAULT 'Autorizado o uso da NF-e',\n                    natureza TEXT,\n                    ie_tomador TEXT,\n                    uf TEXT,\n                    atualizado_em TEXT\n                )\n            ''')\n            conn.commit()\n    \n    def print_summary(self):\n        \"\"\"Imprime resumo detalhado do processamento\"\"\"\n        print(\"\\n\" + \"=\"*80)\n        print(\"RESUMO DO PROCESSAMENTO DE XMLs\")\n        print(\"=\"*80)\n        \n        # Estatísticas principais\n        print(f\"Arquivos encontrados: {self.stats.total_files:,}\")\n        print(f\"Arquivos processados: {self.stats.processed_files:,}\")\n        print(f\"Extrações bem-sucedidas: {self.stats.successful_extractions:,}\")\n        print(f\"Extrações falhadas: {self.stats.failed_extractions:,}\")\n        print(f\"Taxa de sucesso: {self.stats.success_rate:.1f}%\")\n        \n        # Performance\n        print(f\"\\nPerformance:\")\n        print(f\"Duração total: {self.stats.duration}\")\n        print(f\"Velocidade: {self.stats.processing_speed:.1f} arquivos/segundo\")\n        print(f\"Workers utilizados: {self.max_workers}\")\n        \n        # Configurações\n        print(f\"\\nConfiguração:\")\n        print(f\"Diretório XML: {self.xml_root}\")\n        print(f\"Banco de dados: {self.db_path}\")\n        print(f\"Cache habilitado: {self.use_cache}\")\n        print(f\"Tamanho do lote: {self.batch_size}\")\n        \n        print(\"=\"*80)\n\n# ===============================================================================\n# FUNÇÃO PRINCIPAL\n# ===============================================================================\n\ndef main():\n    \"\"\"Função principal\"\"\"\n    parser = argparse.ArgumentParser(\n        description='Sistema melhorado de processamento de XMLs de NF-e',\n        formatter_class=argparse.RawDescriptionHelpFormatter,\n        epilog=\"\"\"\nExemplos de uso:\n  %(prog)s --xml-dir xmls --workers 4\n  %(prog)s --config config.json --verbose\n  %(prog)s --no-cache --log-level DEBUG\n        \"\"\"\n    )\n    \n    # Argumentos de configuração\n    parser.add_argument('--config', type=Path, help='Arquivo de configuração JSON')\n    parser.add_argument('--xml-dir', type=Path, default='xmls', help='Diretório dos XMLs')\n    parser.add_argument('--db-path', type=Path, default='notas.db', help='Caminho do banco de dados')\n    parser.add_argument('--workers', type=int, help='Número de workers paralelos')\n    parser.add_argument('--batch-size', type=int, default=1000, help='Tamanho do lote para processamento')\n    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')\n    parser.add_argument('--log-file', type=Path, help='Arquivo de log')\n    parser.add_argument('--no-cache', action='store_true', help='Desabilita cache')\n    parser.add_argument('--cache-file', type=Path, default='processing_cache.json', help='Arquivo de cache')\n    parser.add_argument('--verbose', action='store_true', help='Saída detalhada')\n    \n    args = parser.parse_args()\n    \n    # Configuração padrão\n    config = {\n        'xml_dir': str(args.xml_dir),\n        'db_path': str(args.db_path),\n        'max_workers': args.workers or min(cpu_count(), 8),\n        'batch_size': args.batch_size,\n        'log_level': args.log_level,\n        'log_file': args.log_file,\n        'use_cache': not args.no_cache,\n        'cache_file': str(args.cache_file),\n        'verbose': args.verbose\n    }\n    \n    # Carrega configuração de arquivo se especificado\n    if args.config and args.config.exists():\n        try:\n            with open(args.config, 'r', encoding='utf-8') as f:\n                file_config = json.load(f)\n            config.update(file_config)\n            print(f\"Configuração carregada de: {args.config}\")\n        except Exception as e:\n            print(f\"Erro ao carregar configuração: {e}\")\n            return 1\n    \n    # Cria processador\n    processor = XMLBatchProcessor(config)\n    \n    try:\n        # Encontra arquivos XML\n        xml_files = processor.find_xml_files()\n        if not xml_files:\n            print(\"Nenhum arquivo XML encontrado para processar.\")\n            return 0\n        \n        print(f\"Iniciando processamento de {len(xml_files)} arquivos com {config['max_workers']} workers...\")\n        \n        # Processa arquivos\n        stats = processor.process_files_parallel(xml_files)\n        \n        # Mostra resumo\n        processor.print_summary()\n        \n        # Código de saída baseado na taxa de sucesso\n        if stats.success_rate >= 95.0:\n            return 0  # Sucesso\n        elif stats.success_rate >= 80.0:\n            return 1  # Sucesso parcial\n        else:\n            return 2  # Muitas falhas\n            \n    except KeyboardInterrupt:\n        print(\"\\nProcessamento interrompido pelo usuário.\")\n        return 130\n    except Exception as e:\n        print(f\"Erro fatal: {e}\")\n        return 1\n\nif __name__ == \"__main__\":\n    sys.exit(main())