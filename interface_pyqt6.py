# interface_pyqt6.py
"""
Interface principal do sistema NFe usando PyQt6
Design responsivo com Material Design 3 e configurações ajustáveis
"""

import sys
import logging
import subprocess
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuração de encoding para Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QDateEdit, QStatusBar, QMenuBar, QMenu,
    QHeaderView, QAbstractItemView, QMessageBox, QSplitter,
    QToolBar, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate, QSettings
from PyQt6.QtGui import QFont, QIcon, QAction, QKeySequence

# Configuração de caminhos
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR))

# Imports dos módulos
try:
    from modules.database import DatabaseManager
    from modules.utils import format_currency, format_date, only_digits
    from modules.qt_components import (
        AppTheme, ModernCard, ModernButton, StatusChip,
        SearchField, ModernTable, StatsCard, FilterPanel,
        ModernMessageBox, ProgressDialog, apply_modern_style,
        create_icon_from_text, show_notification
    )
    from modules.deps_checker import ensure_pdf_deps, has_any_pdf_backend
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Certifique-se de que os módulos estão no diretório 'modules'")
    sys.exit(1)

# Configurações
DB_PATH = SCRIPT_DIR / "notas.db"
SETTINGS_ORG = "NFE_System"
SETTINGS_APP = "BOT_NFE"

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURAÇÕES DA APLICAÇÃO
# ===============================================================================

class AppConfig:
    """Gerenciador de configurações da aplicação"""
    
    def __init__(self):
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self.load_defaults()
    
    def load_defaults(self):
        """Carrega configurações padrão"""
        if not self.settings.value("window/geometry"):
            self.settings.setValue("window/geometry", "100,100,1400,900")
        if not self.settings.value("window/maximized"):
            self.settings.setValue("window/maximized", False)
        if not self.settings.value("table/auto_resize"):
            self.settings.setValue("table/auto_resize", True)
        if not self.settings.value("filters/remember"):
            self.settings.setValue("filters/remember", True)
    
    def save_window_state(self, window):
        """Salva estado da janela"""
        if window.isMaximized():
            self.settings.setValue("window/maximized", True)
        else:
            self.settings.setValue("window/maximized", False)
            geometry = window.geometry()
            self.settings.setValue("window/geometry", 
                f"{geometry.x()},{geometry.y()},{geometry.width()},{geometry.height()}")
    
    def restore_window_state(self, window):
        """Restaura estado da janela"""
        if self.settings.value("window/maximized", type=bool):
            window.showMaximized()
        else:
            geometry_str = self.settings.value("window/geometry", "100,100,1400,900")
            x, y, w, h = map(int, geometry_str.split(','))
            window.setGeometry(x, y, w, h)

# ===============================================================================
# WORKERS PARA OPERAÇÕES EM BACKGROUND
# ===============================================================================

class DataLoaderWorker(QThread):
    """Worker para carregar dados em background"""
    
    data_loaded = pyqtSignal(list)
    progress_updated = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
    
    def run(self):
        try:
            self.progress_updated.emit(20, "Conectando ao banco...")
            notes = self.db_manager.load_notes()
            
            self.progress_updated.emit(60, "Processando dados...")
            
            # Converte para formato da interface
            table_data = []
            total = len(notes)
            
            for i, note in enumerate(notes):
                progress = 60 + int((i / total) * 30) if total else 100
                self.progress_updated.emit(progress, f"Processando nota {i+1}/{total}" if total else "Processando dados...")
                
                table_data.append({
                    'chave': note.get('chave', ''),
                    'status': note.get('status', ''),
                    'xml_status': note.get('xml_status', 'RESUMO'),
                    'numero': note.get('numero', ''),
                    'data_emissao': note.get('data_emissao', ''),
                    'nome_emitente': note.get('nome_emitente', ''),
                    'cnpj_emitente': note.get('cnpj_emitente', ''),
                    'valor': note.get('valor', ''),
                    'tipo': note.get('tipo', ''),
                    'uf': note.get('uf', ''),
                    'informante': note.get('informante', ''),
                })
            
            self.progress_updated.emit(100, "Concluído!")
            self.data_loaded.emit(table_data)
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            self.error_occurred.emit(str(e))

class NFESearchWorker(QThread):
    """Worker para busca de NF-e em background"""
    
    search_completed = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, script_path: Path):
        super().__init__()
        self.script_path = script_path
    
    def run(self):
        try:
            self.progress_updated.emit(10, "Iniciando busca...")
            
            # Detecta executável Python correto
            python_exe = sys.executable
            
            # Log detalhado do início
            logger.info("=== INICIANDO BUSCA DE NF-E ===")
            logger.info(f"Script path: {self.script_path}")
            logger.info(f"Python executable: {python_exe}")
            logger.info(f"Timeout configurado: 300 segundos (5 minutos)")
            
            # Configurações de ambiente para Windows
            import os
            import time
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            logger.info(f"Ambiente configurado: PYTHONIOENCODING=utf-8, PYTHONUTF8=1")
            logger.info(f"Working directory: {self.script_path.parent}")
            
            start_time = time.time()
            
            # Usa Popen para captura em tempo real
            try:
                logger.info("Iniciando processo subprocess...")
                process = subprocess.Popen(
                    [python_exe, str(self.script_path), "interface_mode"],  # Adiciona argumento para execução única
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Redireciona stderr para stdout
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    cwd=str(self.script_path.parent),
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
                
                timeout = 300
                output_lines = []
                
                # Lê saída linha por linha em tempo real
                while True:
                    # Verifica se processo terminou
                    if process.poll() is not None:
                        break
                    
                    # Verifica timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        logger.error(f"❌ TIMEOUT: Processo excedeu {timeout} segundos")
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        self.search_completed.emit(False, "Timeout - busca demorou mais de 5 minutos")
                        return
                    
                    # Lê uma linha da saída
                    try:
                        line = process.stdout.readline()
                        if line:
                            line = line.strip()
                            if line:  # Só loga linhas não vazias
                                logger.info(f"📄 SCRIPT: {line}")
                                output_lines.append(line)
                                
                                # Atualiza progresso baseado no conteúdo da linha
                                if "Iniciando busca" in line or "Processando certificado" in line:
                                    self.progress_updated.emit(20, "Processando certificados...")
                                elif "Buscando notas" in line or "NSU" in line:
                                    self.progress_updated.emit(40, "Buscando documentos...")
                                elif "XML completo baixado" in line or "registrar_xml" in line:
                                    self.progress_updated.emit(60, "Processando XMLs...")
                                elif "Consultando protocolo" in line:
                                    self.progress_updated.emit(80, "Consultando protocolos...")
                                elif "Busca concluída" in line:
                                    self.progress_updated.emit(95, "Finalizando...")
                    except:
                        # Se não conseguir ler mais linhas, sai do loop
                        break
                
                # Aguarda processo terminar
                process.wait()
                total_time = time.time() - start_time
                
                logger.info(f"✅ Processo finalizado em {total_time:.1f} segundos")
                logger.info(f"Return code: {process.returncode}")
                
                # Log do resumo da saída
                if output_lines:
                    logger.info(f"📊 Total de linhas de saída: {len(output_lines)}")
                    # Mostra últimas linhas importantes
                    for line in output_lines[-5:]:
                        if line and not line.startswith("DEBUG"):
                            logger.info(f"📄 FINAL: {line}")
                
                self.progress_updated.emit(100, "Concluído!")
                
                if process.returncode == 0:
                    logger.info("=== ✅ BUSCA CONCLUÍDA COM SUCESSO ===")
                    self.search_completed.emit(True, "Busca concluída com sucesso!")
                else:
                    logger.error(f"=== ❌ ERRO NO SCRIPT === Return code: {process.returncode}")
                    error_summary = "\n".join(output_lines[-10:]) if output_lines else "Sem saída capturada"
                    logger.error(f"Últimas linhas: {error_summary}")
                    self.search_completed.emit(False, f"Erro na busca (código {process.returncode})")
                    
            except Exception as subprocess_error:
                total_time = time.time() - start_time
                logger.error(f"❌ Exceção no subprocess após {total_time:.1f} segundos: {subprocess_error}")
                self.search_completed.emit(False, f"Erro no subprocess: {str(subprocess_error)}")
                
        except Exception as e:
            logger.error(f"❌ ERRO GERAL NO WORKER: {e}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.search_completed.emit(False, f"Erro inesperado: {str(e)}")
    
    def get_python_executable(self) -> str:
        """Detecta o executável Python correto"""
        # Tenta venv primeiro
        venv_python = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        
        # Fallback para python do sistema
        return sys.executable

# ===============================================================================
# WORKER PARA GERAR PDF (DANFE/DACTE)
# ===============================================================================

class PDFWorker(QThread):
    """Busca XML completo (se necessário) e gera DANFE/DACTE em background."""
    finished_ok = pyqtSignal(str)  # caminho do PDF gerado
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, item: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item = item

    def run(self):
        try:
            from nfe_search import NFeService, DatabaseManager as CoreDB, XMLProcessor
            from modules.pdf_generator import generate_pdf_from_xml
            import os, tempfile, sqlite3
            from pathlib import Path

            self.progress_updated.emit(10, "Preparando...")

            chave = self.item.get('chave')
            tipo = (self.item.get('tipo') or 'NFe').strip()
            if tipo.upper().startswith('NFS'):
                raise Exception("Geração de PDF para NFS-e ainda não é suportada nesta versão.")
            informante = (self.item.get('informante') or '').strip()
            xml_status = (self.item.get('xml_status') or 'RESUMO').upper()

            xml_final = None

            # 1) Tenta caminho salvo em xmls_baixados (se existir caminho_arquivo)
            try:
                base = Path(__file__).parent
                db_path = base / 'notas.db'
                with sqlite3.connect(str(db_path)) as conn:
                    row = conn.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,)).fetchone()
                    if row and row[0] and os.path.exists(row[0]):
                        with open(row[0], 'r', encoding='utf-8') as f:
                            xml_final = f.read()
            except Exception:
                pass

            # 2) Se ainda não tem XML, faz um scan local em xmls/<CNPJ>/** para localizar por chave
            found_path = None
            found_cnpj_dir = None
            if not xml_final:
                try:
                    base = Path(__file__).parent
                    xml_root = base / 'xmls'
                    only_digits = ''.join(filter(str.isdigit, informante or ''))
                    candidate_dirs = []
                    if only_digits:
                        candidate_dirs.append(xml_root / only_digits)
                    # Também considera todas pastas de CNPJ se a específica não existir
                    if not candidate_dirs or not candidate_dirs[0].exists():
                        candidate_dirs.extend([p for p in xml_root.iterdir() if p.is_dir()])

                    # Varre arquivos e procura a chave no conteúdo como filtro rápido
                    for cdir in candidate_dirs:
                        try:
                            for fpath in cdir.rglob('*.xml'):
                                try:
                                    txt = fpath.read_text(encoding='utf-8', errors='ignore')
                                    if chave and chave in txt:
                                        xml_final = txt
                                        found_path = str(fpath)
                                        found_cnpj_dir = cdir.name
                                        raise StopIteration
                                except Exception:
                                    continue
                        except StopIteration:
                            break
                except Exception:
                    pass

            # 3) Se ainda não tem XML, consulta consChNFe tentando todos os certificados ativos
            if not xml_final:
                self.progress_updated.emit(30, "Buscando XML completo na SEFAZ...")
                core_db = CoreDB((Path(__file__).parent) / 'notas.db')
                proc = XMLProcessor()
                prefer_map = {'NFe': ('nfeProc', 'NFe'), 'CTe': ('procCTe', 'CTe')}
                prefer = prefer_map.get(tipo, ('nfeProc', 'NFe'))

                certs = core_db.get_certificados()
                if not certs:
                    raise Exception("Nenhum certificado configurado para baixar o XML completo.")

                # Ordena: primeiro o que casa com informante (se houver), depois os demais
                def _key(c):
                    cnpj, path, senha, inf, cuf = c
                    return 0 if (informante and (inf or '').strip() == informante) else 1
                certs = sorted(certs, key=_key)

                last_docs_count = 0
                used_cnpj = None
                for cnpj, path, senha, inf, cuf in certs:
                    try:
                        svc = NFeService(path, senha, cnpj, cuf)
                        resp = svc.fetch_by_chave(chave)
                        if not resp:
                            continue
                        docs = proc.extract_docs(resp)
                        last_docs_count = max(last_docs_count, len(docs))
                        found = None
                        for _nsu, xml_doc in docs:
                            kind = proc.detect_doc_type(xml_doc)
                            if kind in prefer:
                                found = xml_doc
                                break
                        if found:
                            xml_final = found
                            used_cnpj = cnpj
                            break
                    except Exception:
                        continue

                if not xml_final:
                    if last_docs_count > 0:
                        raise Exception("A SEFAZ retornou apenas resumo para esta chave. Tente novamente mais tarde ou verifique se o certificado correto está sendo usado.")
                    raise Exception("Falha ao consultar distribuição para a chave selecionada (sem documentos retornados).")

                # Persistir XML obtido via SEFAZ em disco e registrar no banco UI
                try:
                    from nfe_search import salvar_xml_por_certificado
                    saved = salvar_xml_por_certificado(xml_final, used_cnpj or (informante or ''))
                    if saved:
                        try:
                            from modules.database import DatabaseManager as UIData
                            ui_db = UIData(str((Path(__file__).parent) / 'notas.db'))
                            ui_db.register_xml_download(chave, used_cnpj or (informante or ''), saved)
                            ui_db.update_xml_status(chave, 'COMPLETO')
                        except Exception:
                            pass
                except Exception:
                    pass

            # Se encontrou por scan local, registra caminho no banco UI
            if xml_final and found_path:
                try:
                    from modules.database import DatabaseManager as UIData
                    ui_db = UIData(str((Path(__file__).parent) / 'notas.db'))
                    ui_db.register_xml_download(chave, found_cnpj_dir or (informante or ''), found_path)
                    ui_db.update_xml_status(chave, 'COMPLETO')
                except Exception:
                    pass

            self.progress_updated.emit(70, "Gerando PDF...")
            out_dir = tempfile.gettempdir()
            pdf_name = f"{tipo}-{chave}.pdf"
            out_path = os.path.join(out_dir, pdf_name)
            pdf_path = generate_pdf_from_xml(xml_final, tipo=tipo, out_path=out_path)

            self.progress_updated.emit(100, "Concluído")
            self.finished_ok.emit(pdf_path)

        except Exception as e:
            self.error_occurred.emit(str(e))

# ===============================================================================
# INTERFACE PRINCIPAL
# ===============================================================================

class NFETableWidget(ModernTable):
    """Tabela especializada para NF-e"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Dados
        self.original_data: List[Dict[str, Any]] = []
        self.filtered_data: List[Dict[str, Any]] = []
        
        # Configuração das colunas
        self.columns = [
            ("Status", 120),
            ("XML", 90),
            ("Número", 100),
            ("Data", 100),
            ("Emitente", 250),
            ("CNPJ", 150),
            ("Valor", 120),
            ("Tipo", 80),
            ("UF", 60),
        ]
        
        self.setup_table()
    
    def setup_table(self):
        """Configura a estrutura da tabela"""
        # Define colunas
        self.setColumnCount(len(self.columns))
        headers = [col[0] for col in self.columns]
        self.setHorizontalHeaderLabels(headers)
        
        # Define larguras
        for i, (_, width) in enumerate(self.columns):
            self.setColumnWidth(i, width)
        
        # Configurações
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        # Somente leitura: não permitir edição de células
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Seleção por linha inteira, sem edição
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Header stretch
        header = self.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Emitente (índice deslocado por nova coluna)
    
    def set_data(self, data: List[Dict[str, Any]]):
        """Define os dados da tabela"""
        self.original_data = data
        self.filtered_data = data.copy()
        self.update_display()
    
    def filter_data(self, filters: Dict[str, str]):
        """Filtra os dados baseado nos critérios"""
        filtered = self.original_data.copy()
        
        # Aplica filtros
        if filters.get("search"):
            search_term = filters["search"].lower()
            filtered = [
                item for item in filtered
                if search_term in item.get("nome_emitente", "").lower()
                or search_term in item.get("numero", "").lower()
                or search_term in item.get("cnpj_emitente", "").lower()
            ]
        
        if filters.get("numero"):
            numero = filters["numero"]
            filtered = [item for item in filtered if numero in item.get("numero", "")]
        
        if filters.get("cnpj"):
            cnpj = filters["cnpj"]
            filtered = [item for item in filtered if cnpj in item.get("cnpj_emitente", "")]
        
        if filters.get("status") and filters["status"] != "Todos":
            status = filters["status"].lower()
            filtered = [item for item in filtered if status in item.get("status", "").lower()]
        
        self.filtered_data = filtered
        self.update_display()
    
    def update_display(self):
        """Atualiza a exibição da tabela"""
        self.setRowCount(len(self.filtered_data))
        
        for row, item in enumerate(self.filtered_data):
            # Status com cor
            status = item.get("status", "")
            status_widget = self.create_status_widget(status)
            self.setCellWidget(row, 0, status_widget)

            # XML: Resumo/Completo
            xml_status = (item.get("xml_status", "RESUMO") or "RESUMO").upper()
            xml_widget = self.create_xml_widget(xml_status)
            self.setCellWidget(row, 1, xml_widget)
            
            # Outros campos
            self.setItem(row, 2, QTableWidgetItem(item.get("numero", "")))
            # Formata data como DD/MM/AAAA
            data_raw = item.get("data_emissao", "")
            data_fmt = format_date(data_raw, input_format="auto", output_format="%d/%m/%Y")
            self.setItem(row, 3, QTableWidgetItem(data_fmt))
            
            # Nome do emitente (truncado)
            nome = item.get("nome_emitente", "")
            if len(nome) > 35:
                nome = nome[:32] + "..."
            self.setItem(row, 4, QTableWidgetItem(nome))
            
            self.setItem(row, 5, QTableWidgetItem(item.get("cnpj_emitente", "")))
            self.setItem(row, 6, QTableWidgetItem(item.get("valor", "")))
            
            # Tipo com cor
            tipo = item.get("tipo", "NFe")
            tipo_widget = self.create_tipo_widget(tipo)
            self.setCellWidget(row, 7, tipo_widget)
            
            self.setItem(row, 8, QTableWidgetItem(item.get("uf", "")))
    
    def create_status_widget(self, status: str) -> QWidget:
        """Cria widget colorido para status"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Determina cor baseada no status
        if "autorizado" in status.lower():
            color = AppTheme.SUCCESS
        elif "cancelad" in status.lower():
            color = AppTheme.ERROR
        elif "denegad" in status.lower():
            color = AppTheme.WARNING
        else:
            color = AppTheme.INFO
        
        # Trunca status se muito longo
        display_status = status[:15] + "..." if len(status) > 15 else status
        
        chip = StatusChip(display_status, color)
        layout.addWidget(chip)
        
        return widget
    
    def create_tipo_widget(self, tipo: str) -> QWidget:
        """Cria widget colorido para tipo"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        
        color = AppTheme.SECONDARY if tipo == "NFe" else AppTheme.WARNING
        chip = StatusChip(tipo, color)
        layout.addWidget(chip)
        
        return widget

    def create_xml_widget(self, xml_status: str) -> QWidget:
        """Cria widget de chip para XML (Resumo/Completo)"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        if xml_status == "COMPLETO":
            color = AppTheme.SUCCESS
            label = "Completo"
        else:
            color = AppTheme.WARNING
            label = "Resumo"

        chip = StatusChip(label, color)
        layout.addWidget(chip)
        return widget

class StatsPanel(QWidget):
    """Painel de estatísticas do dashboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(AppTheme.SPACING_MD)
        
        # Cards de estatística
        self.total_card = StatsCard(
            "Total de NF-e", "0",
            create_icon_from_text("T"), AppTheme.PRIMARY
        )
        
        self.authorized_card = StatsCard(
            "Autorizadas", "0",
            create_icon_from_text("✓"), AppTheme.SUCCESS
        )
        
        self.cancelled_card = StatsCard(
            "Canceladas", "0",
            create_icon_from_text("✗"), AppTheme.ERROR
        )
        
        self.value_card = StatsCard(
            "Valor Total", "R$ 0,00",
            create_icon_from_text("$"), AppTheme.INFO
        )
        
        layout.addWidget(self.total_card)
        layout.addWidget(self.authorized_card)
        layout.addWidget(self.cancelled_card)
        layout.addWidget(self.value_card)
    
    def update_stats(self, stats: Dict[str, Any]):
        """Atualiza as estatísticas"""
        self.total_card.update_value(f"{stats.get('total', 0):,}")
        self.authorized_card.update_value(f"{stats.get('authorized', 0):,}")
        self.cancelled_card.update_value(f"{stats.get('cancelled', 0):,}")
        self.value_card.update_value(format_currency(stats.get('total_value', 0)))

class ModernFilterPanel(ModernCard):
    """Painel de filtros moderno e colapsável"""
    
    # Signal para mudança de filtros
    filters_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Estado do painel (expandido/colapsado)
        self.is_expanded = False
        
        # Header com botão de toggle
        header_layout = QHBoxLayout()
        
        # Campo de busca principal (sempre visível)
        self.search_field = SearchField("Buscar por emitente, número ou CNPJ...")
        self.search_field.textChanged.connect(self._on_filter_change)
        
        # Botão para expandir/colapsar filtros avançados
        self.toggle_btn = ModernButton("📋 Filtros Avançados", variant="outline")
        self.toggle_btn.setMaximumWidth(180)
        self.toggle_btn.clicked.connect(self._toggle_filters)
        
        header_layout.addWidget(self.search_field)
        header_layout.addWidget(self.toggle_btn)
        
        # Widget de filtros avançados (inicialmente escondido)
        self.advanced_widget = QWidget()
        self.advanced_widget.setVisible(False)
        
        # Linha de filtros específicos
        filter_layout = QHBoxLayout(self.advanced_widget)
        filter_layout.setContentsMargins(0, 10, 0, 0)
        
        # Número
        self.numero_field = QLineEdit()
        self.numero_field.setPlaceholderText("Número")
        self.numero_field.setMaximumWidth(120)
        self.numero_field.textChanged.connect(self._on_filter_change)
        
        # CNPJ
        self.cnpj_field = QLineEdit()
        self.cnpj_field.setPlaceholderText("CNPJ")
        self.cnpj_field.setMaximumWidth(160)
        self.cnpj_field.textChanged.connect(self._on_filter_change)
        
        # Datas
        self.data_inicio = QDateEdit()
        self.data_inicio.setCalendarPopup(True)
        self.data_inicio.setDate(QDate.currentDate().addDays(-30))
        self.data_inicio.setMaximumWidth(120)
        self.data_inicio.dateChanged.connect(self._on_filter_change)
        
        self.data_fim = QDateEdit()
        self.data_fim.setCalendarPopup(True)
        self.data_fim.setDate(QDate.currentDate())
        self.data_fim.setMaximumWidth(120)
        self.data_fim.dateChanged.connect(self._on_filter_change)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Todos", "Autorizado", "Cancelado", "Denegado"])
        self.status_combo.setMaximumWidth(120)
        self.status_combo.currentTextChanged.connect(self._on_filter_change)
        
        # Tipo de documento
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["Todos", "NFe", "CTe", "NFS-e"])
        self.tipo_combo.setMaximumWidth(100)
        self.tipo_combo.currentTextChanged.connect(self._on_filter_change)
        
        # Botões
        self.clear_btn = ModernButton("Limpar", variant="outline")
        self.clear_btn.clicked.connect(self._clear_filters)
        
        # Layout dos filtros avançados
        filter_layout.addWidget(QLabel("Número:"))
        filter_layout.addWidget(self.numero_field)
        filter_layout.addWidget(QLabel("CNPJ:"))
        filter_layout.addWidget(self.cnpj_field)
        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.data_inicio)
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.data_fim)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_combo)
        filter_layout.addWidget(QLabel("Tipo:"))
        filter_layout.addWidget(self.tipo_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(self.clear_btn)
        
        # Layout principal do card
        self.card_layout.addLayout(header_layout)
        self.card_layout.addWidget(self.advanced_widget)
    
    def _toggle_filters(self):
        """Alterna entre expandido/colapsado"""
        self.is_expanded = not self.is_expanded
        self.advanced_widget.setVisible(self.is_expanded)
        
        # Atualiza texto do botão
        if self.is_expanded:
            self.toggle_btn.setText("🔼 Filtros Avançados")
        else:
            self.toggle_btn.setText("📋 Filtros Avançados")
    
    def _on_filter_change(self):
        """Emite sinal quando filtros mudam"""
        filters = {
            'search': self.search_field.text(),
            'numero': self.numero_field.text(),
            'cnpj': self.cnpj_field.text(),
            'data_inicio': self.data_inicio.date().toString('dd/MM/yyyy'),
            'data_fim': self.data_fim.date().toString('dd/MM/yyyy'),
            'status': self.status_combo.currentText(),
            'tipo': self.tipo_combo.currentText()
        }
        self.filters_changed.emit(filters)
    
    def _clear_filters(self):
        """Limpa todos os filtros"""
        self.search_field.clear()
        self.numero_field.clear()
        self.cnpj_field.clear()
        self.data_inicio.setDate(QDate.currentDate().addDays(-30))
        self.data_fim.setDate(QDate.currentDate())
        self.status_combo.setCurrentIndex(0)
        self.tipo_combo.setCurrentIndex(0)

class StatsPanel(QWidget):
    """Painel de estatísticas expandido para NFe, CTe e NFS-e"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(AppTheme.SPACING_MD)
        
        # Cards de estatística por tipo
        self.nfe_card = StatsCard(
            "📄 NFe", "0",
            create_icon_from_text("NFe"), AppTheme.PRIMARY
        )
        
        self.cte_card = StatsCard(
            "🚛 CTe", "0", 
            create_icon_from_text("CTe"), AppTheme.WARNING
        )
        
        self.nfse_card = StatsCard(
            "🏢 NFS-e", "0",
            create_icon_from_text("NFS"), AppTheme.INFO
        )
        
        # Cards de status
        self.authorized_card = StatsCard(
            "Autorizadas", "0",
            create_icon_from_text("✓"), AppTheme.SUCCESS
        )
        
        self.cancelled_card = StatsCard(
            "Canceladas", "0",
            create_icon_from_text("✗"), AppTheme.ERROR
        )
        
        self.value_card = StatsCard(
            "Valor Total", "R$ 0,00",
            create_icon_from_text("$"), AppTheme.SUCCESS
        )
        
        layout.addWidget(self.nfe_card)
        layout.addWidget(self.cte_card)
        layout.addWidget(self.nfse_card)
        layout.addWidget(self.authorized_card)
        layout.addWidget(self.cancelled_card)
        layout.addWidget(self.value_card)
    
    def update_stats(self, stats: Dict[str, Any]):
        """Atualiza as estatísticas expandidas"""
        self.nfe_card.update_value(f"{stats.get('nfe_count', 0):,}")
        self.cte_card.update_value(f"{stats.get('cte_count', 0):,}")
        self.nfse_card.update_value(f"{stats.get('nfse_count', 0):,}")
        self.authorized_card.update_value(f"{stats.get('authorized', 0):,}")
        self.cancelled_card.update_value(f"{stats.get('cancelled', 0):,}")
        self.value_card.update_value(format_currency(stats.get('total_value', 0)))

class MainWindow(QMainWindow):
    """Janela principal da aplicação"""
    
    def __init__(self):
        super().__init__()
        
        # Configurações
        self.config = AppConfig()
        
        # Configurações básicas
        self.setWindowTitle("BOT NFe - Sistema de Gerenciamento v2.0")
        self.setMinimumSize(1000, 600)
        
        # Database manager
        self.db_manager = DatabaseManager(DB_PATH)
        self.current_data: List[Dict[str, Any]] = []

        # Verifica e tenta instalar dependências de PDF no início
        try:
            pre = has_any_pdf_backend()
            ok = ensure_pdf_deps(auto_install=True)
            post = has_any_pdf_backend()
            if not ok or not post:
                logger.warning("Dependências de PDF não puderam ser garantidas automaticamente. PDFs podem não abrir.")
            elif not pre and post:
                # Notifica que instalamos automaticamente
                try:
                    show_notification(self, "Dependências instaladas", "Bibliotecas de PDF foram instaladas automaticamente. Agora você pode abrir DANFE/DACTE.")
                except Exception:
                    logger.info("Dependências de PDF instaladas automaticamente.")
        except Exception as e:
            logger.warning(f"Falha ao garantir dependências de PDF: {e}")
        
        # Configuração da interface
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_status_bar()
        
        # Restaura estado da janela
        self.config.restore_window_state(self)
        
        # Controle de cooldown de busca (60 minutos)
        self.COOLDOWN_MINUTES = 60
        self.last_search_dt = self._get_last_search_dt()
        
        # Timer para próxima execução automática
        self.next_run_timer = QTimer(self)
        self.next_run_timer.setSingleShot(True)
        self.next_run_timer.timeout.connect(self._auto_run_search)
        
        # Agendar próxima execução automática se houver last_search_dt
        self._schedule_next_auto_run()
        
        # Carregamento inicial
        QTimer.singleShot(100, self.load_data)
    
    def setup_ui(self):
        """Configura a interface principal"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(AppTheme.SPACING_MD)
        main_layout.setContentsMargins(AppTheme.SPACING_MD, AppTheme.SPACING_MD, 
                                     AppTheme.SPACING_MD, AppTheme.SPACING_MD)
        
        # Barra de ações
        self.setup_action_bar(main_layout)
        
        # Painel de estatísticas
        self.stats_panel = StatsPanel()
        main_layout.addWidget(self.stats_panel)
        
        # Painel de filtros
        self.filter_panel = ModernFilterPanel()
        self.filter_panel.filters_changed.connect(self.on_filters_changed)
        main_layout.addWidget(self.filter_panel)
        
        # Tabela principal
        self.nfe_table = NFETableWidget()
        # Abrir DANFE/DACTE ao dar 2 cliques na linha
        try:
            self.nfe_table.cellDoubleClicked.connect(self.on_table_double_clicked)
        except Exception:
            pass
        main_layout.addWidget(self.nfe_table, 1)  # Expansível
    
    def setup_action_bar(self, parent_layout: QVBoxLayout):
        """Configura barra de ações principal"""
        action_layout = QHBoxLayout()
        
        # Título e informações
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        
        title_label = QLabel("BOT NFe - Sistema Multi-Documento")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_HEADLINE}px;
                font-weight: bold;
                color: {AppTheme.PRIMARY};
                margin: 0;
            }}
        """)
        
        # Label para última consulta
        self.last_query_label = QLabel("Última consulta: Carregando...")
        self.last_query_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_SMALL}px;
                color: {AppTheme.TEXT_SECONDARY};
                margin: 0;
            }}
        """)
        # Permite múltiplas linhas para listar NSU por certificado
        self.last_query_label.setWordWrap(True)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.last_query_label)
        
        action_layout.addWidget(title_widget)
        action_layout.addStretch()
        
        # Botões principais (removendo duplicações)
        self.refresh_btn = ModernButton("🔄 Atualizar")
        self.refresh_btn.clicked.connect(self.on_atualizar_clicked)
        
        self.search_btn = ModernButton("🔍 Buscar")
        self.search_btn.clicked.connect(self.search_nfe)
        
        action_layout.addWidget(self.refresh_btn)
        action_layout.addWidget(self.search_btn)
        
        parent_layout.addLayout(action_layout)
    
    def setup_menu(self):
        """Configura menu principal"""
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("Arquivo")
        
        refresh_action = QAction("Atualizar", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_data)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Sair", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu NFe
        nfe_menu = menubar.addMenu("NF-e")
        
        search_action = QAction("Buscar Novas", self)
        search_action.setShortcut("Ctrl+B")
        search_action.triggered.connect(self.search_nfe)
        nfe_menu.addAction(search_action)
        
        process_action = QAction("Processar XMLs", self)
        process_action.setShortcut("Ctrl+P")
        process_action.triggered.connect(self.process_xmls)
        nfe_menu.addAction(process_action)
        
        nfe_menu.addSeparator()
        
        # Nova funcionalidade: Download XMLs Completos
        download_complete_action = QAction("Primeira Busca", self)
        download_complete_action.setStatusTip("Converte resumos em XMLs completos (NFe, CTe, NFS-e)")
        download_complete_action.setShortcut("Ctrl+D")
        download_complete_action.triggered.connect(self.primeira_busca)
        nfe_menu.addAction(download_complete_action)
        
        # Menu Certificados
        cert_menu = menubar.addMenu("Certificados")
        
        manage_action = QAction("Gerenciar", self)
        manage_action.triggered.connect(self.manage_certificates)
        cert_menu.addAction(manage_action)
        
        cert_menu.addSeparator()
        
        sefaz_config_action = QAction("Configurar SEFAZ", self)
        sefaz_config_action.setStatusTip("Configurar certificados para consultas SEFAZ")
        sefaz_config_action.triggered.connect(self.configure_sefaz)
        cert_menu.addAction(sefaz_config_action)
        
        # Menu Ajuda
        help_menu = menubar.addMenu("Ajuda")
        
        about_action = QAction("Sobre", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Toolbar removida - funcionalidades integradas na barra de ações"""
        # Toolbar removida para evitar duplicação
        # Funcionalidades principais estão na barra de ações
        pass
    
    def setup_status_bar(self):
        """Configura barra de status"""
        self.status_bar = self.statusBar()
        
        # Mensagem principal
        self.status_label = QLabel("Sistema inicializado")
        self.status_bar.addWidget(self.status_label)
        
        # Contador de registros
        self.records_label = QLabel("0 registros")
        self.status_bar.addPermanentWidget(self.records_label)
        
        # Timestamp
        self.time_label = QLabel(datetime.now().strftime("%d/%m/%Y %H:%M"))
        self.status_bar.addPermanentWidget(self.time_label)
        
        # Timer para atualizar timestamp
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timestamp)
        # Também atualiza informação de última busca/cooldown
        self.timer.timeout.connect(self._update_last_query_label_with_countdown)
        self.timer.start(60000)  # 1 minuto
    
    def update_timestamp(self):
        """Atualiza timestamp na status bar"""
        self.time_label.setText(datetime.now().strftime("%d/%m/%Y %H:%M"))
    
    def set_status(self, message: str, timeout: int = 0):
        """Define mensagem na status bar"""
        self.status_label.setText(message)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText("Pronto"))
    
    def show_status(self, message: str, timeout: int = 0):
        """Alias para set_status (compatibilidade)"""
        self.set_status(message, timeout)
    
    def update_last_query_info(self):
        """Atualiza informações da última consulta NSU"""
        try:
            from datetime import datetime
            # Se temos last_search_dt, mantemos a linha de countdown; abaixo listamos por certificado
            has_countdown = bool(self.last_search_dt)

            # Monta mapa CNPJ/CPF -> alias/nome do certificado (se disponível)
            def _get_cert_alias_map():
                mapping = {}
                try:
                    from modules.certificate_manager import certificate_manager
                    certs = certificate_manager.get_certificates()
                    for c in certs:
                        doc = (c.get('cnpj') or c.get('cpf') or '').strip()
                        if not doc:
                            continue
                        doc_digits = only_digits(doc)
                        alias = c.get('alias') or c.get('cn') or 'Certificado'
                        mapping[doc_digits] = alias
                except Exception:
                    pass
                return mapping

            alias_map = _get_cert_alias_map()

            lines = []
            if has_countdown:
                # Reaproveita a linha com countdown
                rem = self._time_remaining()
                last_fmt = self.last_search_dt.strftime('%d/%m/%Y %H:%M')
                if rem is not None and rem.total_seconds() > 0:
                    mins = int(rem.total_seconds() // 60)
                    secs = int(rem.total_seconds() % 60)
                    lines.append(f"Última consulta: {last_fmt} • Próxima automática em {mins:02d}:{secs:02d}")
                else:
                    lines.append(f"Última consulta: {last_fmt} • Pronta para nova busca")

            # Busca todos os NSU por certificado
            with sqlite3.connect(self.db_manager.db_path) as conn:
                try:
                    cursor = conn.execute('''
                        SELECT informante, ult_nsu, atualizado_em 
                        FROM nsu 
                        ORDER BY atualizado_em DESC
                    ''')
                    rows = cursor.fetchall()
                except sqlite3.OperationalError:
                    cursor = conn.execute('''
                        SELECT informante, ult_nsu 
                        FROM nsu 
                    ''')
                    rows = [(r[0], r[1], None) for r in cursor.fetchall()]

            if rows:
                # Cabeçalho da listagem
                if not has_countdown:
                    lines.append("Últimos NSU por certificado:")
                for informante, ult_nsu, atualizado_em in rows:
                    # Resolve nome amigável do certificado
                    inf_digits = only_digits(str(informante or ''))
                    nome = alias_map.get(inf_digits, str(informante or ''))
                    # Formata data se houver
                    if atualizado_em:
                        try:
                            dt = datetime.fromisoformat(str(atualizado_em).replace('Z', '+00:00'))
                            dt_str = dt.strftime('%d/%m/%Y %H:%M')
                        except Exception:
                            dt_str = str(atualizado_em)[:16]
                        lines.append(f"• {nome}: NSU {ult_nsu} – {dt_str}")
                    else:
                        lines.append(f"• {nome}: NSU {ult_nsu}")
            else:
                if not has_countdown:
                    lines.append("Última consulta: Nenhuma encontrada")

            # Atualiza label com múltiplas linhas
            self.last_query_label.setText("\n".join(lines))
                    
        except Exception as e:
            logger.error(f"Erro ao buscar última consulta: {e}")
            self.last_query_label.setText("Última consulta: Erro ao verificar")

    # =============================
    # Cooldown/auto-run da Busca 🔁
    # =============================
    def _get_last_search_dt(self) -> Optional[datetime]:
        try:
            ts = QSettings(SETTINGS_ORG, SETTINGS_APP).value("search/last_success_ts", "")
            if ts:
                # Compatível com ISO
                return datetime.fromisoformat(str(ts))
        except Exception:
            pass
        return None

    def _save_last_search_now(self):
        self.last_search_dt = datetime.now()
        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("search/last_success_ts", self.last_search_dt.isoformat())
        self._schedule_next_auto_run()
        self._update_last_query_label_with_countdown()

    def _time_remaining(self) -> Optional[timedelta]:
        if not self.last_search_dt:
            return None
        next_time = self.last_search_dt + timedelta(minutes=self.COOLDOWN_MINUTES)
        remaining = next_time - datetime.now()
        if remaining.total_seconds() <= 0:
            return timedelta(0)
        return remaining

    def _update_last_query_label_with_countdown(self):
        try:
            if not self.last_search_dt:
                # Fallback para info do banco
                return self.update_last_query_info()
            
            remaining = self._time_remaining()
            last_fmt = self.last_search_dt.strftime('%d/%m/%Y %H:%M')
            if remaining is not None and remaining.total_seconds() > 0:
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                self.last_query_label.setText(f"Última consulta: {last_fmt} • Próxima automática em {mins:02d}:{secs:02d}")
            else:
                self.last_query_label.setText(f"Última consulta: {last_fmt} • Pronta para nova busca")
        except Exception:
            pass

    def _schedule_next_auto_run(self):
        try:
            if not self.last_search_dt:
                return
            remaining = self._time_remaining()
            delay_ms = 0
            if remaining is None:
                delay_ms = self.COOLDOWN_MINUTES * 60 * 1000
            else:
                delay_ms = max(0, int(remaining.total_seconds() * 1000))
            
            # Programa a próxima execução automática
            if delay_ms == 0:
                # Já vencido: não inicia automaticamente, apenas mostra "Pronta"
                self.next_run_timer.stop()
            else:
                self.next_run_timer.start(delay_ms)
        except Exception:
            pass

    def _auto_run_search(self):
        # Evita rodar se já houver processo em andamento
        if hasattr(self, 'current_worker') and self.current_worker is not None:
            # Reagenda para daqui 1 minuto
            self.next_run_timer.start(60 * 1000)
            return
        self._start_search(auto=True)
    
    def load_data(self):
        """Carrega dados do banco"""
        try:
            self.set_status("Carregando dados...")
            
            # Progress dialog
            self.progress_dialog = ProgressDialog("Carregando dados...", self)
            self.progress_dialog.show()
            
            # Worker thread
            self.data_worker = DataLoaderWorker(self.db_manager)
            self.data_worker.data_loaded.connect(self.on_data_loaded)
            self.data_worker.progress_updated.connect(self.progress_dialog.update_progress)
            self.data_worker.error_occurred.connect(self.on_load_error)
            self.data_worker.finished.connect(self.progress_dialog.close)
            
            self.data_worker.start()
            
        except Exception as e:
            logger.error(f"Erro ao iniciar carregamento: {e}")
            self.set_status(f"Erro: {str(e)}", 5000)
    
    def on_data_loaded(self, data: List[Dict[str, Any]]):
        """Callback para dados carregados"""
        self.current_data = data
        self.nfe_table.set_data(data)
        self.update_stats()
        self.update_last_query_info()  # Atualiza informações da última consulta
        
        count = len(data)
        self.set_status(f"{count:,} documentos fiscais carregados", 3000)
        self.records_label.setText(f"{count:,} registros")
    
    def on_load_error(self, error_msg: str):
        """Callback para erro no carregamento"""
        logger.error(f"Erro ao carregar dados: {error_msg}")
        self.set_status(f"Erro: {error_msg}", 5000)
        
        # Mostra dialog de erro
        msg = ModernMessageBox("Erro", f"Falha ao carregar dados:\\n{error_msg}", "error", self)
        msg.exec()
    
    def update_stats(self):
        """Atualiza estatísticas com dados por tipo de documento"""
        if not self.current_data:
            return
        
        # Contadores por tipo
        nfe_count = sum(1 for item in self.current_data if item.get('tipo', 'NFe').upper() == 'NFE')
        cte_count = sum(1 for item in self.current_data if item.get('tipo', '').upper() == 'CTE')
        nfse_count = sum(1 for item in self.current_data if item.get('tipo', '').upper() == 'NFS-E')
        
        # Contadores por status
        authorized = sum(1 for item in self.current_data 
                        if 'autorizado' in item.get('status', '').lower())
        cancelled = sum(1 for item in self.current_data 
                       if 'cancelad' in item.get('status', '').lower())
        
        # Calcula valor total
        total_value = 0
        for item in self.current_data:
            try:
                value_str = item.get('valor', '0')
                clean_value = value_str.replace('R$', '').replace('.', '').replace(',', '.').strip()
                total_value += float(clean_value) if clean_value else 0
            except:
                pass
        
        stats = {
            'nfe_count': nfe_count,
            'cte_count': cte_count,
            'nfse_count': nfse_count,
            'authorized': authorized,
            'cancelled': cancelled,
            'total_value': total_value
        }
        
        self.stats_panel.update_stats(stats)
    
    def on_filters_changed(self, filters: Dict[str, str]):
        """Callback para mudança de filtros"""
        self.nfe_table.filter_data(filters)
        
        # Atualiza contador
        filtered_count = len(self.nfe_table.filtered_data)
        total_count = len(self.current_data)
        self.records_label.setText(f"{filtered_count:,} de {total_count:,} registros")

    def on_atualizar_clicked(self):
        """Se houver seleção, baixa XML completo dos selecionados; caso contrário, recarrega dados."""
        selection = self.nfe_table.selectionModel().selectedRows() if self.nfe_table.selectionModel() else []
        if selection:
            # Coleta chaves selecionadas
            chaves = []
            for idx in selection:
                row = idx.row()
                if 0 <= row < len(self.nfe_table.filtered_data):
                    chave = self.nfe_table.filtered_data[row].get('chave')
                    if chave:
                        chaves.append(chave)
            if not chaves:
                self.load_data()
                return
            # Gera script temporário para baixar selecionados
            try:
                from pathlib import Path
                script_path = Path.cwd() / "temp_baixar_selecionados.py"
                conteudo = self._build_script_baixar_selecionados(chaves)
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(conteudo)
                self._run_script("Baixar Selecionados", script_path)
            except Exception as e:
                logger.error(f"Erro ao preparar download de selecionados: {e}")
                ModernMessageBox("Erro", f"Falha ao preparar atualização dos selecionados:\n{e}", "error", self).exec()
        else:
            self.load_data()

    def _build_script_baixar_selecionados(self, chaves: list[str]) -> str:
        """Gera o conteúdo de um script temporário que baixa XML completo para as chaves informadas."""
        chaves_list = ','.join([f"'{c}'" for c in chaves])
        return f'''# Auto-gerado para baixar XML completo dos selecionados
import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHAVES = [{chaves_list}]

def main():
    from nfe_search import NFeService, DatabaseManager, XMLProcessor
    from modules.database import DatabaseManager as UIData
    db_path = project_dir / 'notas.db'
    ui_db = UIData(db_path)
    core_db = DatabaseManager(db_path)
    core_db.criar_tabela_detalhada()
    proc = XMLProcessor()

    # Carrega certificados (legado)
    certs = core_db.get_certificados()
    cert_map = {{str(c[0]): c for c in certs}}  # cnpj -> tuple

    total = 0
    completos = 0
    for chave in CHAVES:
        total += 1
        nota = ui_db.get_note_by_chave(chave)
        if not nota:
            logger.warning(f'Nota não encontrada no banco: {{chave}}')
            continue
        informante = (nota.get('informante') or '').strip()
        if not informante or informante not in cert_map:
            logger.warning(f'Certificado não encontrado para informante={{informante}} (chave={{chave}})')
            continue
        cnpj, path, senha, inf, cuf = cert_map[informante]
        svc = NFeService(path, senha, cnpj, cuf)
        # Consulta por consChNFe
        xml = svc.fetch_by_chave(chave)
        if not xml:
            logger.warning(f'Sem resposta para chave {{chave}}')
            continue
        # Extrai documentos retornados (podem ser vários docZip)
        docs = proc.extract_docs(xml)
        encontrou_completo = False
        for nsu, xml_doc in docs:
            doc_type = proc.detect_doc_type(xml_doc)
            if doc_type in ('nfeProc', 'NFe'):
                # Salvar como COMPLETO
                dados = DatabaseManager.extrair_dados_nfe(xml_doc, core_db)
                if dados:
                    dados['xml_status'] = 'COMPLETO'
                    dados['informante'] = informante
                    dados['nsu'] = nsu
                    core_db.salvar_nota_detalhada(dados)
                    ui_db.update_xml_status(chave, 'COMPLETO')
                    completos += 1
                    encontrou_completo = True
                    break
        if not encontrou_completo:
            logger.info(f'Chave {{chave}} ainda em RESUMO')
    print(f'ATUALIZACAO_SELECIONADOS: total={{total}}, completos={{completos}}')

if __name__ == '__main__':
    main()
'''
    
    def search_nfe(self):
        """Executa busca de NF-e com respeito ao cooldown de 60 minutos"""
        try:
            # Verifica cooldown
            remaining = self._time_remaining()
            if remaining is not None and remaining.total_seconds() > 0:
                mins = int(remaining.total_seconds() // 60)
                secs = int(remaining.total_seconds() % 60)
                msg = (
                    f"A última consulta foi realizada recentemente.\n"
                    f"Faltam {mins:02d}:{secs:02d} para a próxima execução automática.\n\n"
                    f"Deseja executar a busca agora mesmo?"
                )
                reply = QMessageBox.question(
                    self, "Buscar NF-e (Cooldown em andamento)", msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    # Usuário optou por aguardar: garante que esteja agendado
                    self._schedule_next_auto_run()
                    return
            else:
                # Confirmação normal se sem cooldown
                reply = QMessageBox.question(
                    self, "Buscar NF-e", 
                    "Deseja executar a busca de novas NF-e?\nEsta operação pode demorar alguns minutos.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Inicia busca imediatamente
            self._start_search(auto=False)
        
        except Exception as e:
            logger.error(f"Erro geral no search_nfe: {e}")
            self.set_status("Erro na busca", 5000)
            QMessageBox.critical(self, "Erro", f"Erro inesperado: {str(e)}")

    def _start_search(self, auto: bool = False):
        """Dispara a busca de forma unificada (manual/automática)."""
        logger.info("Iniciando busca de NF-e..." + (" (automática)" if auto else ""))
        
        # Script principal
        script_path = SCRIPT_DIR / "nfe_search.py"
        if not script_path.exists():
            logger.error("Script de busca não encontrado")
            QMessageBox.critical(self, "Erro", "Script de busca não encontrado!")
            return
        
        self.set_status("Executando busca de NF-e...")
        
        try:
            self.search_worker = NFESearchWorker(script_path)
            self.search_worker.search_completed.connect(self.on_search_completed)
            self.search_worker.start()
            logger.info("Worker thread iniciado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar worker thread: {e}")
            self.set_status("Erro ao iniciar busca", 5000)
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar busca: {str(e)}")
    
    def on_search_completed(self, success: bool, message: str):
        """Callback para busca concluída - versão simplificada"""
        try:
            if success:
                self.set_status("Busca concluída", 3000)
                logger.info("Busca de NF-e concluída com sucesso")
                
                # Mostra notificação de sucesso
                QMessageBox.information(self, "Sucesso", message)
                
                # Salva horário da última busca bem-sucedida e agenda próxima
                self._save_last_search_now()
                
                # Recarrega dados
                QTimer.singleShot(1000, self.load_data)
            else:
                self.set_status("Erro na busca", 5000)
                logger.error(f"Erro na busca de NF-e: {message}")
                
                # Mostra erro
                QMessageBox.critical(self, "Erro na Busca", message)
                
        except Exception as e:
            logger.error(f"Erro no callback de busca: {e}")
            self.set_status("Erro no callback", 5000)

    def on_table_double_clicked(self, row: int, col: int):
        """Gera e abre o PDF (DANFE/DACTE) para a linha clicada 2x."""
        try:
            if row < 0 or row >= len(self.nfe_table.filtered_data):
                return
            item = self.nfe_table.filtered_data[row]
            chave = item.get('chave')
            if not chave:
                ModernMessageBox("Aviso", "Chave da nota não encontrada.", "warning", self).exec()
                return
            xml_status = (item.get('xml_status') or 'RESUMO').upper()
            if xml_status != 'COMPLETO':
                msg = ModernMessageBox(
                    "XML Incompleto",
                    "Esta nota está em RESUMO. Vou tentar baixar o XML completo automaticamente para gerar o PDF.",
                    "info", self
                )
                msg.exec()

            # Inicia geração em background
            self._start_pdf_worker(item)
        except Exception as e:
            logger.error(f"Erro no duplo clique da tabela: {e}")
            ModernMessageBox("Erro", f"Falha ao preparar geração do PDF:\n{e}", "error", self).exec()

    def _start_pdf_worker(self, item: Dict[str, Any]):
        try:
            self.pdf_worker = PDFWorker(item, self)
            self.pdf_progress = ProgressDialog("Gerando PDF...", self)
            self.pdf_worker.progress_updated.connect(self.pdf_progress.update_progress)
            self.pdf_worker.finished_ok.connect(self._on_pdf_ready)
            self.pdf_worker.error_occurred.connect(self._on_pdf_error)
            self.pdf_worker.finished.connect(self.pdf_progress.close)
            self.pdf_progress.show()
            self.pdf_worker.start()
        except Exception as e:
            logger.error(f"Erro ao iniciar worker de PDF: {e}")
            ModernMessageBox("Erro", f"Falha ao iniciar geração do PDF:\n{e}", "error", self).exec()

    def _on_pdf_ready(self, pdf_path: str):
        try:
            import os
            if os.path.exists(pdf_path):
                try:
                    os.startfile(pdf_path)  # type: ignore[attr-defined]
                    self.set_status("PDF aberto com sucesso", 3000)
                except Exception:
                    ModernMessageBox("Sucesso", f"PDF gerado em:\n{pdf_path}", "success", self).exec()
            else:
                ModernMessageBox("Aviso", f"PDF gerado, mas não encontrado em disco:\n{pdf_path}", "warning", self).exec()
        except Exception as e:
            ModernMessageBox("Erro", f"Falha ao abrir PDF:\n{e}", "error", self).exec()

    def _on_pdf_error(self, message: str):
        ModernMessageBox("Erro", message, "error", self).exec()
    
    def process_xmls(self):
        """Processa XMLs locais"""
        # Determina qual script usar
        script_path = SCRIPT_DIR / "download_all_xmls_melhorado.py"
        if not script_path.exists():
            script_path = SCRIPT_DIR / "DownloadAllXmls.py"
        
        if not script_path.exists():
            ModernMessageBox("Erro", "Script de processamento não encontrado!", "error", self).exec()
            return
        
        # Confirma ação
        reply = QMessageBox.question(
            self, "Processar XMLs", 
            "Deseja processar os XMLs locais?\\nEsta operação pode demorar alguns minutos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Progress dialog
        self.process_progress = ProgressDialog("Processando XMLs...", self)
        self.process_progress.show()
        
        # Worker thread
        self.process_worker = NFESearchWorker(script_path)
        self.process_worker.search_completed.connect(self.on_process_completed)
        self.process_worker.progress_updated.connect(self.process_progress.update_progress)
        self.process_worker.finished.connect(self.process_progress.close)
        
        self.process_worker.start()
        self.set_status("Processando XMLs...")
    
    def on_process_completed(self, success: bool, message: str):
        """Callback para processamento concluído"""
        if success:
            self.set_status("Processamento concluído", 3000)
            show_notification(self, "Sucesso", message)
            
            # Recarrega dados
            QTimer.singleShot(1000, self.load_data)
        else:
            self.set_status("Erro no processamento", 5000)
            msg = ModernMessageBox("Erro no Processamento", message, "error", self)
            msg.exec()
    
    def manage_certificates(self):
        """Gerencia certificados"""
        try:
            from modules.certificate_dialog import CertificateDialog
            
            dialog = CertificateDialog(self)
            dialog.certificate_changed.connect(self.on_certificate_changed)
            dialog.exec()
        except ImportError as e:
            msg = ModernMessageBox(
                "Erro", 
                f"Módulo de certificados não disponível:\n{e}\n\nInstale: pip install cryptography", 
                "error", self
            )
            msg.exec()
        except Exception as e:
            msg = ModernMessageBox(
                "Erro", 
                f"Erro ao abrir gerenciador de certificados:\n{e}", 
                "error", self
            )
            msg.exec()
    
    def configure_sefaz(self):
        """Configura certificados para SEFAZ"""
        try:
            from modules.sefaz_config_dialog import SefazConfigDialog
            
            dialog = SefazConfigDialog(self)
            dialog.exec()
        except ImportError as e:
            msg = ModernMessageBox(
                "Erro", 
                f"Módulo de configuração SEFAZ não disponível:\n{e}", 
                "error", self
            )
            msg.exec()
        except Exception as e:
            msg = ModernMessageBox(
                "Erro", 
                f"Erro ao abrir configuração SEFAZ:\n{e}", 
                "error", self
            )
            msg.exec()
    
    def primeira_busca(self):
        """Executa primeira busca: NSU zerado até o mais recente (NFe, CTe, NFSe)"""
        import logging
        logger = logging.getLogger(__name__)
        
        reply = QMessageBox.question(
            self, "Primeira Busca", 
            "Esta operação irá buscar TODOS os documentos fiscais eletrônicos\n"
            "(NFe, CTe, NFSe) desde o NSU zerado até o mais recente.\n\n"
            "Esta operação pode demorar bastante tempo.\n\n"
            "Deseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Cria script temporário para primeira busca
        script_content = '''
import sys
from pathlib import Path

# Adiciona diretório do projeto ao path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

try:
    from nfe_search import NFeService, DatabaseManager
    import logging
    
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('primeira_busca.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    def main():
        """Executa primeira busca completa"""
        logger.info("=== INICIANDO PRIMEIRA BUSCA ===")
        logger.info("Buscando NFe, CTe e NFSe desde NSU zerado")
        
        db = DatabaseManager(project_dir / "notas.db")
        
        try:
            # Busca certificados cadastrados
            certificados = db.get_certificados()
            
            if not certificados:
                logger.warning("Nenhum certificado encontrado")
                print("ERRO: Nenhum certificado cadastrado")
                return
            
            total_docs = 0
            total_marcados = 0
            
            for cnpj, path, senha, inf, cuf in certificados:
                logger.info(f"Processando certificado: {inf} - CNPJ: {cnpj}")
                
                try:
                    # Cria serviço NFe para este certificado
                    service = NFeService(path, senha, cnpj, cuf)
                    
                    # Busca distribuição desde NSU zerado
                    logger.info(f"Iniciando busca para CNPJ {cnpj} desde NSU 0")
                    
                    result = service.fetch_by_cnpj(
                        cnpj=cnpj,
                        nsu_inicial=0,  # Começar do zero
                        max_nsu=None,   # Buscar até o mais recente
                        tipos_documento=['NFe', 'CTe', 'NFSe']  # Todos os tipos
                    )
                    
                    if result.get('success'):
                        documentos = result.get('documentos', [])
                        docs_count = len(documentos)
                        total_docs += docs_count
                        
                        logger.info(f"CNPJ {cnpj}: {docs_count} documentos encontrados")
                        
                        # Processar documentos encontrados
                        marcados_para_download = 0
                        for doc in documentos:
                            # Se não veio XML completo, marcar para download na busca normal
                            if not doc.get('xml_completo'):
                                # Adiciona flag no banco para download posterior
                                try:
                                    db.marcar_para_download(doc.get('chave', ''), cnpj)
                                    marcados_para_download += 1
                                except Exception as e:
                                    logger.warning(f"Erro ao marcar documento para download: {e}")
                        
                        total_marcados += marcados_para_download
                        logger.info(f"CNPJ {cnpj}: {marcados_para_download} documentos marcados para download posterior")
                        
                    else:
                        error_msg = result.get('error', 'Erro desconhecido')
                        logger.warning(f"Erro na busca para CNPJ {cnpj}: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar certificado {inf}: {e}")
                    continue
            
            logger.info("=== PRIMEIRA BUSCA CONCLUÍDA ===")
            logger.info(f"Total de documentos encontrados: {total_docs}")
            logger.info(f"Total marcados para download: {total_marcados}")
            print(f"PRIMEIRA_BUSCA_CONCLUIDA: {total_docs} documentos, {total_marcados} marcados para download")
            
        except Exception as e:
            logger.error(f"Erro geral na primeira busca: {e}")
            print(f"ERRO: {e}")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"ERRO_IMPORT: {e}")
except Exception as e:
    print(f"ERRO: {e}")
'''
        
        # Salva script temporário
        script_path = Path.cwd() / "temp_primeira_busca.py"
        
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Verifica se o arquivo foi criado com sucesso
            if not script_path.exists():
                raise FileNotFoundError(f"Falha ao criar arquivo temporário: {script_path}")
            
            logger.info(f"Script temporário criado: {script_path}")
            self._run_script("Primeira Busca", script_path)
            
        except Exception as e:
            logger.error(f"Erro ao criar/executar script temporário: {e}")
            ModernMessageBox(
                "Erro", 
                f"Erro ao criar arquivo temporário:\n{e}\n\nTente executar como administrador.",
                "error", 
                self
            ).exec()
        finally:
            # Remove script temporário após execução
            try:
                if script_path.exists():
                    script_path.unlink()
                    logger.debug(f"Arquivo temporário removido: {script_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
    
    def _run_script(self, script_name: str, script_path: Path):
        """Executa script em background"""
        if hasattr(self, 'current_worker') and self.current_worker is not None:
            ModernMessageBox("Aviso", "Já existe uma operação em andamento!", "warning", self).exec()
            return
        
        self.show_status(f"Executando {script_name}...", 0)
        
        self.current_worker = NFESearchWorker(script_path)
        self.current_worker.search_completed.connect(self.on_script_completed)
        self.current_worker.progress_updated.connect(self.on_progress_updated)
        self.current_worker.start()
    
    def on_script_completed(self, success: bool, message: str):
        """Callback para script concluído"""
        self.current_worker = None
        
        if success:
            self.show_status("Operação concluída com sucesso", 3000)
            ModernMessageBox("Sucesso", message, "success", self).exec()
            # Recarrega dados
            QTimer.singleShot(1000, self.load_data)
        else:
            self.show_status("Operação falhou", 5000)
            ModernMessageBox("Erro", message, "error", self).exec()
    
    def on_progress_updated(self, progress: int, message: str):
        """Callback para atualização de progresso"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setValue(progress)
        self.show_status(message)
    
    def on_certificate_changed(self):
        """Callback quando certificados mudam"""
        try:
            from modules.certificate_manager import certificate_manager
            active_cert = certificate_manager.get_active_certificate()
            
            if active_cert:
                alias = active_cert.get('alias', 'Certificado')
                self.set_status(f"Certificado ativo: {alias}", 3000)
            else:
                self.set_status("Nenhum certificado ativo", 3000)
        except Exception as e:
            logging.error(f"Erro ao atualizar status do certificado: {e}")
    
    def show_about(self):
        """Mostra informações sobre o sistema"""
        about_text = """
        <h2>BOT NFe - Sistema de Gerenciamento</h2>
        <p>Sistema moderno para gerenciamento de Notas Fiscais Eletrônicas</p>
        <p><b>Versão:</b> 2.0.0</p>
        <p><b>Interface:</b> PyQt6 com Material Design 3</p>
        <p><b>Banco de Dados:</b> SQLite</p>
        <p><b>Desenvolvido em:</b> 2025</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Sobre")
        msg.setText(about_text)
        msg.setIconPixmap(create_icon_from_text("NFe").pixmap(64, 64))
        msg.exec()
    
    def _run_script(self, script_name: str, script_path: Path):
        """Executa script em background"""
        if hasattr(self, 'current_worker') and self.current_worker is not None:
            ModernMessageBox("Aviso", "Já existe uma operação em andamento!", "warning", self).exec()
            return
        
        self.show_status(f"Executando {script_name}...", 0)
        
        self.current_worker = NFESearchWorker(script_path)
        self.current_worker.search_completed.connect(self.on_script_completed)
        self.current_worker.progress_updated.connect(self.on_progress_updated)
        self.current_worker.start()
    
    def on_script_completed(self, success: bool, message: str):
        """Callback para script concluído"""
        self.current_worker = None
        
        if success:
            self.show_status("Operação concluída com sucesso", 3000)
            ModernMessageBox("Sucesso", message, "success", self).exec()
            # Recarrega dados
            QTimer.singleShot(1000, self.load_data)
        else:
            self.show_status("Operação falhou", 5000)
            ModernMessageBox("Erro", message, "error", self).exec()
    
    def on_progress_updated(self, progress: int, message: str):
        """Callback para atualização de progresso"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setValue(progress)
        self.show_status(message)
    
    def closeEvent(self, event):
        """Override para salvar estado ao fechar"""
        self.config.save_window_state(self)
        event.accept()

# ===============================================================================
# FUNÇÃO PRINCIPAL
# ===============================================================================

def main():
    """Função principal da aplicação"""
    app = QApplication(sys.argv)
    
    # Configurações da aplicação
    app.setOrganizationName(SETTINGS_ORG)
    app.setApplicationName(SETTINGS_APP)
    app.setApplicationVersion("2.0.1")
    
    # Aplica estilo moderno
    apply_modern_style(app)
    
    # Janela principal
    window = MainWindow()
    window.show()
    
    # Centraliza na tela se primeira execução
    try:
        screen = app.primaryScreen()
        if screen and not window.config.settings.value("window/geometry"):
            screen_geometry = screen.geometry()
            window_size = window.geometry()
            x = (screen_geometry.width() - window_size.width()) // 2
            y = (screen_geometry.height() - window_size.height()) // 2
            window.move(x, y)
    except Exception as e:
        logger.warning(f"Erro ao centralizar janela: {e}")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()