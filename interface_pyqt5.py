from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import sqlite3
import ctypes
from ctypes import wintypes

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QComboBox, QProgressBar, QTextEdit,
    QDialog, QMessageBox, QFileDialog, QInputDialog, QStatusBar,
    QTreeWidget, QTreeWidgetItem, QSplitter, QAction, QMenu, QSystemTrayIcon,
    QProgressDialog, QStyledItemDelegate, QStyleOptionViewItem, QScrollArea, QFrame,
    QGroupBox, QRadioButton, QDateEdit, QStyle
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QColor, QBrush, QFont, QCloseEvent

# Classe customizada para ordenação numérica
class NumericTableWidgetItem(QTableWidgetItem):
    """Item de tabela que ordena numericamente em vez de alfabeticamente"""
    def __init__(self, text: str, numeric_value: float = 0.0):
        super().__init__(text)
        self._numeric_value = numeric_value
        # Armazena o valor também no UserRole para debug
        self.setData(Qt.UserRole, numeric_value)
    
    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self._numeric_value < other._numeric_value
        # Fallback: tenta comparar pelo UserRole
        try:
            self_val = self.data(Qt.UserRole)
            other_val = other.data(Qt.UserRole)
            if self_val is not None and other_val is not None:
                return float(self_val) < float(other_val)
        except:
            pass
        return super().__lt__(other)

# Delegate para centralizar ícones na coluna XML e Status
class CenterIconDelegate(QStyledItemDelegate):
    """Delegate que centraliza ícones em células"""
    def paint(self, painter, option, index):
        if index.column() in (0, 6):  # XML e Status
            # Força centralização do ícone
            option.decorationAlignment = Qt.AlignCenter
            option.decorationPosition = QStyleOptionViewItem.Top
            option.displayAlignment = Qt.AlignCenter
        super().paint(painter, option, index)
    
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Força alinhamento centralizado para XML e Status
        if index.column() in (0, 6):
            option.decorationAlignment = Qt.AlignCenter
            option.displayAlignment = Qt.AlignCenter

def get_data_dir():
    """Retorna o diretório de dados do aplicativo (AppData para compilados, local para dev)."""
    import sys
    
    # Se estiver executando como executável PyInstaller
    if getattr(sys, 'frozen', False):
        # Usa AppData do usuário para dados persistentes
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "Busca XML"
    else:
        # Desenvolvimento: usa pasta local
        data_dir = Path(__file__).parent
    
    # Garante que o diretório existe
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"AVISO: Não foi possível criar {data_dir}: {e}")
        # Fallback para pasta temporária
        data_dir = Path(os.environ.get('TEMP', Path.home())) / "Busca XML"
        data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir

# Paths
BASE_DIR = Path(__file__).parent if not getattr(sys, 'frozen', False) else Path(sys.executable).parent
DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "notas.db"
LOGS_DIR = DATA_DIR / "logs"

# Backend
from modules.database import DatabaseManager as UIDB
from modules import sandbox_worker as sandbox


def ensure_logs_dir():
    try:
        LOGS_DIR.mkdir(exist_ok=True)
    except Exception:
        pass


def run_search(progress_cb: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Executa a busca de NFe/CTe na SEFAZ."""
    # Usa sys.__stdout__ que é garantido ser o stdout original
    original_stdout = sys.__stdout__ if hasattr(sys, '__stdout__') else sys.stdout
    old_stdout = sys.stdout
    
    try:
        # Adiciona BASE_DIR ao sys.path para importação
        if str(BASE_DIR) not in sys.path:
            sys.path.insert(0, str(BASE_DIR))
        
        # Importa o módulo nfe_search dinamicamente
        import importlib.util
        spec = importlib.util.spec_from_file_location("nfe_search", BASE_DIR / "nfe_search.py")
        if spec is None or spec.loader is None:
            return {"ok": False, "error": f"nfe_search.py não encontrado em {BASE_DIR}"}
        
        nfe_search = importlib.util.module_from_spec(spec)
        sys.modules['nfe_search'] = nfe_search
        spec.loader.exec_module(nfe_search)
        
        # Usa threading.Lock para proteção thread-safe contra recursão
        import threading
        _callback_lock = threading.Lock()
        
        # Classe para capturar e enviar progresso em tempo real
        class ProgressCapture:
            def write(self, text):
                try:
                    # Usa original_stdout que nunca é None
                    if original_stdout:
                        original_stdout.write(text)
                    
                    # PROTEÇÃO: Usa trylock para evitar recursão sem bloquear
                    if progress_cb and text.strip():
                        if _callback_lock.acquire(blocking=False):
                            try:
                                progress_cb(text.rstrip())
                            finally:
                                _callback_lock.release()
                except Exception as e:
                    # Fallback: tenta imprimir no console de qualquer forma
                    try:
                        if original_stdout:
                            original_stdout.write(f"[ERRO ProgressCapture] {e}\n")
                    except:
                        pass  # Silenciosamente ignora se nem isso funcionar
                    
            def flush(self):
                try:
                    if original_stdout:
                        original_stdout.flush()
                except Exception:
                    pass
        
        # Adiciona handler ao logger para capturar logs
        import logging
        if progress_cb:
            class ProgressHandler(logging.Handler):
                def emit(self, record):
                    try:
                        # PROTEÇÃO: Usa trylock para evitar recursão
                        if _callback_lock.acquire(blocking=False):
                            try:
                                msg = self.format(record)
                                progress_cb(msg)
                            finally:
                                _callback_lock.release()
                    except:
                        pass
            
            # Obtém o logger do nfe_search
            logger = logging.getLogger('nfe_search')
            
            # Remove apenas ProgressHandler antigos para evitar duplicação
            # MAS mantém StreamHandler (console) e FileHandler
            handlers_to_remove = [h for h in logger.handlers if isinstance(h, ProgressHandler)]
            for h in handlers_to_remove:
                logger.removeHandler(h)
            
            handler = ProgressHandler()
            handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        sys.stdout = ProgressCapture()
        
        # Executa apenas UMA iteração de busca (sem loop infinito)
        try:
            nfe_search.run_single_cycle()
        except SystemExit:
            # nfe_search pode chamar sys.exit() - ignorar
            pass
        except Exception as e:
            import traceback
            error_msg = f"Erro durante execução do nfe_search: {str(e)}\n{traceback.format_exc()}"
            sys.stdout = old_stdout if old_stdout else original_stdout
            return {"ok": False, "error": error_msg}
        
        # Restaura stdout
        sys.stdout = old_stdout if old_stdout else original_stdout
        
        return {"ok": True, "message": "Busca concluída"}
        
    except Exception as e:
        sys.stdout = old_stdout if old_stdout else original_stdout
        import traceback
        error_msg = f"Erro na busca: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log no console
        return {"ok": False, "error": error_msg}
    finally:
        # Garante que stdout sempre será restaurado
        try:
            sys.stdout = old_stdout if old_stdout else original_stdout
        except:
            sys.stdout = original_stdout
        sys.stdout = old_stdout


def resolve_xml_text(item: Dict[str, Any]) -> Optional[str]:
    try:
        chave = (item.get("chave") or "").strip()
        if not chave:
            return None
        import sqlite3
        with sqlite3.connect(str(DB_PATH)) as conn:
            # Tenta pegar xml_completo primeiro (mais rápido)
            row = conn.execute("SELECT xml_completo, caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,)).fetchone()
            if row:
                # Se tem xml_completo no banco, usa ele
                if row[0]:
                    print(f"[DEBUG XML] ✅ XML encontrado no banco (xml_completo)")
                    return row[0]
                # Se não, tenta ler do arquivo
                if row[1] and os.path.exists(row[1]):
                    try:
                        print(f"[DEBUG XML] ✅ XML encontrado no arquivo: {row[1]}")
                        return Path(row[1]).read_text(encoding="utf-8", errors="ignore")
                    except Exception as e:
                        print(f"[DEBUG XML] ⚠️ Erro ao ler arquivo: {e}")
        
        print(f"[DEBUG XML] Buscando XML nas pastas locais para chave: {chave}")
        roots = [
            DATA_DIR / "xmls",
            DATA_DIR / "xmls_chave",
            DATA_DIR / "xmls_nfce",
            DATA_DIR / "xml_NFs",
            DATA_DIR / "xml_envio",
            DATA_DIR / "xml_extraidos",
            BASE_DIR / "xmls",  # Fallback para desenvolvimento
            BASE_DIR / "xmls_chave",
            BASE_DIR / "xmls_nfce",
        ]
        # Pastas configuradas pelo usuário por CNPJ (emitidos)
        try:
            digits_inf = ''.join(ch for ch in str(item.get('informante') or '') if ch.isdigit())
            if digits_inf:
                s = QSettings('NFE_System', 'BOT_NFE')
                extra = str(s.value(f'emit_dirs/{digits_inf}', '') or '')
                for p in extra.split(';'):
                    p = p.strip()
                    if p:
                        roots.append(Path(p))
        except Exception:
            pass
        for r in roots:
            if not r.exists():
                continue
            for f in r.rglob(f"*{chave}*.xml"):
                try:
                    print(f"[DEBUG XML] ✅ XML encontrado em: {f}")
                    return f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
        
        # Segunda tentativa: busca pelo conteúdo
        print(f"[DEBUG XML] Segunda tentativa: buscando pelo conteúdo da chave")
        for r in roots:
            if not r.exists():
                continue
            for f in r.rglob("*.xml"):
                try:
                    head = f.read_text(encoding="utf-8", errors="ignore")
                    if chave in head:
                        print(f"[DEBUG XML] ✅ XML encontrado por conteúdo em: {f}")
                        return head
                except Exception:
                    continue
        
        print(f"[DEBUG XML] ❌ XML não encontrado em nenhuma pasta")
    except Exception as e:
        print(f"[DEBUG XML] ❌ Erro ao buscar XML: {e}")
    return None


class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar na SEFAZ")
        self.resize(700, 420)
        v = QVBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.progress)
        v.addWidget(self.log)

    def append(self, text: str):
        self.log.append(text)
        self.log.ensureCursorVisible()

    def set_percent(self, p: int):
        self.progress.setValue(max(0, min(100, p)))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self._update_window_title()
        self.resize(1200, 720)
        
        # Define o ícone da janela principal (tenta .ico primeiro, depois .png)
        icon_path = BASE_DIR / 'Logo.ico'
        if not icon_path.exists():
            icon_path = BASE_DIR / 'Logo.png'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        ensure_logs_dir()

        self.db = UIDB(DB_PATH)
        
        # Cache de PDFs para abertura rápida {chave: pdf_path}
        self._pdf_cache = {}
        self._cache_building = False
        self._cache_worker = None  # Referência para a thread do cache
        self._refreshing_emitidos = False  # Flag para evitar múltiplos refreshes simultâneos

        central = QWidget()
        self.setCentralWidget(central)

        # Use a horizontal splitter: left = certificados tree, right = main area (toolbar + tabs)
        main_split = QSplitter()
        main_split.setChildrenCollapsible(False)

        # Left panel: certificados tree
        left_widget = QWidget()
        left_v = QVBoxLayout(left_widget)
        left_v.setContentsMargins(4, 4, 4, 4)
        # Left header with title and filter
        lh = QHBoxLayout()
        lbl_left = QLabel("Certificados")
        f = lbl_left.font(); f.setBold(True); lbl_left.setFont(f)
        self.cert_filter = QLineEdit(); self.cert_filter.setPlaceholderText("Filtrar…")
        self.cert_filter.textChanged.connect(self._filter_certs_tree)
        btn_clear_filter = QPushButton("Limpar")
        btn_clear_filter.setToolTip("Limpar filtro/seleção")
        btn_clear_filter.clicked.connect(self._clear_cert_filter)
        lh.addWidget(lbl_left)
        lh.addStretch(1)
        lh.addWidget(self.cert_filter)
        lh.addWidget(btn_clear_filter)
        left_v.addLayout(lh)
        self.tree_certs = QTreeWidget()
        self.tree_certs.setHeaderLabels(["Certificados"])
        self.tree_certs.setColumnCount(1)
        self.tree_certs.itemClicked.connect(self._on_tree_cert_clicked)
        left_v.addWidget(self.tree_certs)

        # Right panel: toolbar + content
        right_widget = QWidget()
        v = QVBoxLayout(right_widget)
        v.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        t = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por emitente, número ou CNPJ…")
        self.search_edit.textChanged.connect(self.refresh_table)
        
        # Filtros de data
        from PyQt5.QtCore import QDate
        date_label = QLabel("Data:")
        self.date_inicio = QDateEdit()
        self.date_inicio.setCalendarPopup(True)
        self.date_inicio.setDisplayFormat("dd/MM/yyyy")
        self.date_inicio.setDate(QDate.currentDate().addMonths(-3))  # Padrão: 3 meses atrás
        self.date_inicio.dateChanged.connect(self.refresh_table)
        self.date_inicio.setToolTip("Data inicial do filtro")
        
        date_ate_label = QLabel("até:")
        self.date_fim = QDateEdit()
        self.date_fim.setCalendarPopup(True)
        self.date_fim.setDisplayFormat("dd/MM/yyyy")
        self.date_fim.setDate(QDate.currentDate())  # Padrão: hoje
        self.date_fim.dateChanged.connect(self.refresh_table)
        self.date_fim.setToolTip("Data final do filtro")
        
        # Botão para limpar filtro de data
        btn_clear_dates = QPushButton("✖")
        btn_clear_dates.setMaximumWidth(30)
        btn_clear_dates.setToolTip("Limpar filtro de data")
        btn_clear_dates.clicked.connect(self._clear_date_filters)
        
        self.status_dd = QComboBox(); self.status_dd.addItems(["Todos","Autorizado","Cancelado","Denegado"])
        self.status_dd.currentTextChanged.connect(self.refresh_table)
        self.tipo_dd = QComboBox(); self.tipo_dd.addItems(["Todos","NFe","CTe","NFS-e"])
        self.tipo_dd.currentTextChanged.connect(self.refresh_table)
        
        # Seletor de quantidade de linhas exibidas
        limit_label = QLabel("Exibir:")
        self.limit_dd = QComboBox()
        self.limit_dd.addItems(["50", "100", "500", "1000", "Todos"])
        
        # Restaura a seleção salva do usuário
        settings = QSettings('NFE_System', 'BOT_NFE')
        saved_limit = settings.value('display/limit', '100')  # Padrão: 100 linhas
        self.limit_dd.setCurrentText(str(saved_limit))
        
        self.limit_dd.currentTextChanged.connect(self.refresh_table)
        self.limit_dd.currentTextChanged.connect(self._save_limit_preference)
        self.limit_dd.setToolTip("Quantidade de documentos a exibir na tabela")
        
        self.btn_refresh = QPushButton("Atualizar"); self.btn_refresh.clicked.connect(self.refresh_all)
        btn_busca = QPushButton("Buscar na SEFAZ"); btn_busca.clicked.connect(self.do_search)
        btn_busca_completa = QPushButton("Busca Completa"); btn_busca_completa.clicked.connect(self.do_busca_completa)
        btn_busca_chave = QPushButton("Busca por chave"); btn_busca_chave.clicked.connect(self.buscar_por_chave)
        
        # Seletor de intervalo entre buscas
        from PyQt5.QtWidgets import QSpinBox
        intervalo_label = QLabel("Intervalo de busca:")
        self.spin_intervalo = QSpinBox()
        self.spin_intervalo.setMinimum(1)
        self.spin_intervalo.setMaximum(23)
        self.spin_intervalo.setSuffix(" horas")
        self.spin_intervalo.setValue(self._load_intervalo_config())
        self.spin_intervalo.valueChanged.connect(self._save_intervalo_config)
        self.spin_intervalo.setToolTip("Intervalo mínimo: 1 hora | Intervalo máximo: 23 horas")
        
        # Checkbox para habilitar/desabilitar consulta de status
        from PyQt5.QtWidgets import QCheckBox
        self.check_consultar_status = QCheckBox("Consultar status (protocolo)")
        self.check_consultar_status.setChecked(self._load_consultar_status_config())
        self.check_consultar_status.stateChanged.connect(self._save_consultar_status_config)
        self.check_consultar_status.setToolTip(
            "Se habilitado, consulta o status de notas sem status após buscar documentos.\n"
            "DICA: Desabilite se a consulta estiver travando a busca de novos documentos."
        )

        # Icons (fallback to standard icons if custom not found)
        def _icon(name: str, std=None) -> QIcon:
            p = BASE_DIR / 'Icone' / name
            if p.exists():
                return QIcon(str(p))
            try:
                return self.style().standardIcon(std) if std is not None else QIcon()
            except Exception:
                return QIcon()

        try:
            from PyQt5.QtWidgets import QStyle
            self.btn_refresh.setIcon(_icon('refresh.png', QStyle.SP_BrowserReload))
            btn_busca.setIcon(_icon('search.png', QStyle.SP_FileDialogContentsView))
            btn_busca_completa.setIcon(_icon('search.png', QStyle.SP_FileDialogContentsView))
        except Exception:
            pass
        t.addWidget(self.search_edit)
        t.addWidget(date_label)
        t.addWidget(self.date_inicio)
        t.addWidget(date_ate_label)
        t.addWidget(self.date_fim)
        t.addWidget(btn_clear_dates)
        t.addWidget(self.status_dd)
        t.addWidget(self.tipo_dd)
        t.addWidget(limit_label)
        t.addWidget(self.limit_dd)
        t.addStretch(1)
        t.addWidget(self.check_consultar_status)
        t.addWidget(intervalo_label)
        t.addWidget(self.spin_intervalo)
        t.addWidget(self.btn_refresh)
        t.addWidget(btn_busca)
        t.addWidget(btn_busca_completa)
        t.addWidget(btn_busca_chave)
        v.addLayout(t)

        # Tabs: create a tab widget to host different views (emitidos por terceiros / pela empresa)
        from PyQt5.QtWidgets import QTabWidget
        self.tabs = QTabWidget()

        # Table (main) inside first tab
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        self.table = QTableWidget()
        headers = [
            "XML","Num","D/Emit","Tipo","Valor","Venc.","Status",
            "Emissor CNPJ","Emissor Nome","Natureza","UF","Base ICMS",
            "Valor ICMS","CFOP","NCM","Tomador IE","Chave"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Habilita ordenação clicável nos cabeçalhos
        self.table.setSortingEnabled(True)
        # Centraliza ícones na coluna XML (coluna 0)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        # Aplica delegate para centralizar ícones
        self.table.setItemDelegateForColumn(0, CenterIconDelegate(self.table))
        self.table.setItemDelegateForColumn(6, CenterIconDelegate(self.table))  # Status também
        # Menu de contexto para buscar XML completo
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        # Use o sinal específico da tabela com linha/coluna
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)
        
        # Tooltip instantâneo (100ms de delay)
        QApplication.instance().setStyleSheet(QApplication.instance().styleSheet() + 
            "QToolTip { border: 1px solid #333; padding: 4px; border-radius: 3px; }")
        # Configura delay mínimo para tooltips aparecerem rapidamente
        self.table.setMouseTracking(True)
        hh = self.table.horizontalHeader()
        try:
            hh.setSectionResizeMode(QHeaderView.Interactive)
        except Exception:
            pass
        try:
            hh.setStretchLastSection(False)
        except Exception:
            pass
        # Column sizing to approximate the desired layout
        try:
            self.table.setColumnWidth(0, 50)  # XML - ajustado para ícone
            self.table.setColumnWidth(1, 80)
            self.table.setColumnWidth(2, 92)
            self.table.setColumnWidth(4, 100)
            self.table.setColumnWidth(5, 92)
            self.table.setColumnWidth(6, 50)  # Status - ajustado para ícone
            self.table.setColumnWidth(7, 130)
            # Column 8 (Emissor Nome) no longer stretches during fill
        except Exception:
            pass
        tab1_layout.addWidget(self.table)
        self.tabs.addTab(tab1, "Emitidos por terceiros")

        # Second tab: Emitidos pela empresa
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        
        # Cria tabela para notas emitidas pela empresa
        self.table_emitidos = QTableWidget()
        headers_emitidos = [
            "XML","Num","D/Emit","Tipo","Valor","Venc.","Status",
            "Destinatário CNPJ","Destinatário Nome","Natureza","UF","Base ICMS",
            "Valor ICMS","CFOP","NCM","Tomador IE","Chave"
        ]
        self.table_emitidos.setColumnCount(len(headers_emitidos))
        self.table_emitidos.setHorizontalHeaderLabels(headers_emitidos)
        self.table_emitidos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_emitidos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_emitidos.setSortingEnabled(True)
        self.table_emitidos.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table_emitidos.setItemDelegateForColumn(0, CenterIconDelegate(self.table_emitidos))
        self.table_emitidos.setItemDelegateForColumn(6, CenterIconDelegate(self.table_emitidos))
        self.table_emitidos.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_emitidos.customContextMenuRequested.connect(self._on_table_emitidos_context_menu)
        self.table_emitidos.cellDoubleClicked.connect(self._on_table_emitidos_double_clicked)
        self.table_emitidos.setMouseTracking(True)
        
        # Configura larguras das colunas
        try:
            hh_emitidos = self.table_emitidos.horizontalHeader()
            hh_emitidos.setSectionResizeMode(QHeaderView.Interactive)
            hh_emitidos.setStretchLastSection(False)
            self.table_emitidos.setColumnWidth(0, 50)
            self.table_emitidos.setColumnWidth(1, 80)
            self.table_emitidos.setColumnWidth(2, 92)
            self.table_emitidos.setColumnWidth(4, 100)
            self.table_emitidos.setColumnWidth(5, 92)
            self.table_emitidos.setColumnWidth(6, 50)
            self.table_emitidos.setColumnWidth(7, 130)
        except Exception:
            pass
        
        tab2_layout.addWidget(self.table_emitidos)
        self.tabs.addTab(tab2, "Emitidos pela empresa")

        v.addWidget(self.tabs)

        # Add widgets to splitter
        main_split.addWidget(left_widget)
        main_split.addWidget(right_widget)
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)

        # Place splitter in central layout
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(main_split)

        # Status bar com resumo de busca
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        
        # Inicializa status com última hora de busca
        last_search_text = self._get_last_search_status()
        self.status_label = QLabel(last_search_text)
        self._statusbar.addWidget(self.status_label, 1)  # stretch=1
        
        # Resumo de busca (sempre visível)
        self.search_summary_label = QLabel("")
        self.search_summary_label.setStyleSheet("color: #0066cc; font-weight: bold; padding: 0 10px;")
        self._statusbar.addPermanentWidget(self.search_summary_label)
        
        # Progress bar compacta na status bar
        self.search_progress = QProgressBar()
        self.search_progress.setMaximumWidth(200)
        self.search_progress.setMaximumHeight(16)
        self.search_progress.setTextVisible(True)
        self.search_progress.setVisible(False)
        self._statusbar.addPermanentWidget(self.search_progress)

        # Menus (Central de Tarefas)
        try:
            self._setup_tasks_menu()
        except Exception:
            pass

        # Data cache
        self.notes = []
        
        # Estatísticas de busca
        self._search_stats = {
            'nfes_found': 0,
            'ctes_found': 0,
            'start_time': None,
            'last_cert': ''
        }

        # Incremental table fill state
        self._table_fill_timer = QTimer(self)
        self._table_fill_timer.setInterval(0)
        self._table_fill_timer.timeout.connect(self._fill_table_step)
        self._table_fill_items = []
        self._table_fill_index = 0
        self._table_fill_chunk = 100
        self._table_filling = False

        # Loading flags/workers
        self._loading_notes = False
        self._load_worker = None
        self._search_worker = None
        self._search_in_progress = False
        self._next_search_time = None
        self._selected_cert_cnpj = None  # Inicializa seleção de certificado
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_search_status)
        self._status_timer.start(1000)  # Atualiza a cada segundo

        # Initial load
        QTimer.singleShot(50, self.refresh_all)
        # Atualiza UFs dos certificados existentes
        QTimer.singleShot(100, self._atualizar_ufs_certificados)
        # Gera PDFs faltantes
        QTimer.singleShot(500, self._gerar_pdfs_faltantes)
        # Auto-start search removido - usuário deve clicar em "Buscar na SEFAZ"
        # QTimer.singleShot(2000, self._auto_start_search)
        self._apply_theme()
        
        # System Tray Icon
        self._setup_system_tray()

    def _gerar_pdfs_faltantes(self):
        """Gera PDFs para XMLs que ainda não possuem PDF (em background)."""
        from threading import Thread
        
        def _worker():
            try:
                xmls_dir = DATA_DIR / "xmls"
                if not xmls_dir.exists():
                    return
                
                print("[VERIFICAÇÃO] Procurando XMLs sem PDF...")
                count = 0
                for xml_file in xmls_dir.rglob("*.xml"):
                    # Pula eventos (não gera PDF para eventos)
                    nome_arquivo = xml_file.stem.upper()
                    if any(keyword in nome_arquivo for keyword in ['EVENTO', 'CIENCIA', '-CANCELAMENTO', '-CORRECAO', 'RESUMO']):
                        continue
                    
                    pdf_file = xml_file.with_suffix('.pdf')
                    if not pdf_file.exists():
                        try:
                            xml_text = xml_file.read_text(encoding='utf-8')
                            
                            # ⛔ APENAS DOCUMENTOS COMPLETOS: Pula eventos, resumos, etc
                            # Só gera PDF se for nfeProc ou cteProc (documentos completos)
                            if '<nfeProc' not in xml_text and '<cteProc' not in xml_text:
                                continue
                            
                            # Detecta tipo do documento
                            tipo = "CTe" if "<CTe" in xml_text or "<cte" in xml_text else "NFe"
                            
                            from modules.pdf_simple import generate_danfe_pdf
                            success = generate_danfe_pdf(xml_text, str(pdf_file), tipo)
                            if success:
                                count += 1
                                print(f"[PDF GERADO] {pdf_file.name}")
                        except Exception as e:
                            print(f"[ERRO PDF] {xml_file.name}: {e}")
                
                if count > 0:
                    print(f"[CONCLUÍDO] {count} PDFs gerados")
                else:
                    print("[INFO] Todos os XMLs já possuem PDFs")
            except Exception as e:
                print(f"[ERRO] Falha ao gerar PDFs: {e}")
        
        # Executa em thread separada para não travar a interface
        thread = Thread(target=_worker, daemon=True)
        thread.start()

    def _atualizar_ufs_certificados(self):
        """Atualiza as UFs e razões sociais dos certificados existentes consultando a API Brasil."""
        try:
            print("[DEBUG] Atualizando UFs e razões sociais dos certificados existentes...")
            
            # Mapeia UF para código
            uf_to_codigo = {
                'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                'SE': '28', 'TO': '17'
            }
            
            import requests
            certificados = self.db.load_certificates()
            
            for cert in certificados:
                cert_id = cert.get('id')
                cnpj = cert.get('cnpj_cpf', '')
                uf_atual = cert.get('cUF_autor', '')
                razao_atual = cert.get('razao_social', '')
                
                if len(cnpj) == 14:  # É CNPJ
                    try:
                        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
                        response = requests.get(url, timeout=5)
                        
                        if response.status_code == 200:
                            data = response.json()
                            uf = data.get('uf')
                            codigo_uf = uf_to_codigo.get(uf)
                            razao_social = data.get('razao_social', '')
                            
                            # Flags para controlar o que precisa atualizar
                            atualizar_uf = codigo_uf and codigo_uf != uf_atual
                            atualizar_razao = razao_social and not razao_atual
                            
                            if atualizar_uf or atualizar_razao:
                                if atualizar_uf:
                                    print(f"[DEBUG] Atualizando UF do certificado {cnpj}: {uf_atual} -> {codigo_uf} ({uf})")
                                if atualizar_razao:
                                    print(f"[DEBUG] Adicionando razão social do certificado {cnpj}: {razao_social}")
                                
                                # Atualiza no banco
                                with sqlite3.connect(str(DB_PATH)) as conn:
                                    if atualizar_uf and atualizar_razao:
                                        conn.execute("UPDATE certificados SET cUF_autor = ?, razao_social = ? WHERE id = ?", 
                                                   (codigo_uf, razao_social, cert_id))
                                    elif atualizar_uf:
                                        conn.execute("UPDATE certificados SET cUF_autor = ? WHERE id = ?", 
                                                   (codigo_uf, cert_id))
                                    elif atualizar_razao:
                                        conn.execute("UPDATE certificados SET razao_social = ? WHERE id = ?", 
                                                   (razao_social, cert_id))
                                    conn.commit()
                            elif codigo_uf == uf_atual and razao_atual:
                                print(f"[DEBUG] Certificado {cnpj} já está completo (UF: {uf_atual}, Razão: {razao_atual[:40]}...)")
                    except Exception as e:
                        print(f"[DEBUG] Erro ao atualizar certificado {cnpj}: {e}")
            
            print("[DEBUG] Atualização de certificados concluída")
            
            # Recarrega a árvore de certificados para exibir as razões sociais
            self._populate_certs_tree()
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar certificados: {e}")
    
    def set_status(self, msg: str, timeout_ms: int = 0):
        self.status_label.setText(msg)
        if timeout_ms:
            QTimer.singleShot(timeout_ms, lambda: self.status_label.setText("Pronto"))
    
    def _setup_system_tray(self):
        """Configura o ícone na bandeja do sistema."""
        try:
            # Cria o ícone da bandeja
            self.tray_icon = QSystemTrayIcon(self)
            
            # Tenta carregar ícone personalizado (prioriza .ico)
            icon_path = BASE_DIR / 'Logo.ico'
            if not icon_path.exists():
                icon_path = BASE_DIR / 'Logo.png'
            if icon_path.exists():
                self.tray_icon.setIcon(QIcon(str(icon_path)))
            else:
                # Usa ícone padrão do sistema
                try:
                    from PyQt5.QtWidgets import QStyle
                    self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
                except Exception:
                    pass
            
            # Cria menu de contexto
            tray_menu = QMenu()
            
            # Ação: Mostrar/Ocultar
            show_action = QAction("Mostrar", self)
            show_action.triggered.connect(self._show_window)
            tray_menu.addAction(show_action)
            
            tray_menu.addSeparator()
            
            # Ação: Buscar agora
            search_action = QAction("Buscar na SEFAZ", self)
            search_action.triggered.connect(self.do_search)
            tray_menu.addAction(search_action)
            
            tray_menu.addSeparator()
            
            # Ação: Fechar
            quit_action = QAction("Fechar", self)
            quit_action.triggered.connect(self._quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            
            # Duplo clique na bandeja restaura a janela
            self.tray_icon.activated.connect(self._on_tray_activated)
            
            # Mostra o ícone na bandeja
            self.tray_icon.show()
            
            # Tooltip
            self.tray_icon.setToolTip("Busca XML")
            
        except Exception as e:
            print(f"[DEBUG] Erro ao configurar system tray: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_tray_activated(self, reason):
        """Chamado quando o ícone da bandeja é clicado."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()
    
    def _show_window(self):
        """Mostra e restaura a janela."""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self._center_window()
    
    def _quit_application(self):
        """Encerra a aplicação completamente."""
        reply = QMessageBox.question(
            self,
            "Confirmar saída",
            "Deseja realmente encerrar o Busca XML?\n\nA busca automática de documentos fiscais será interrompida.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print("[DEBUG] Encerrando aplicação")
            
            # Finaliza threads ativas
            if self._cache_worker and self._cache_worker.isRunning():
                print("[DEBUG] Finalizando thread do cache...")
                self._cache_worker.wait(1000)  # Aguarda até 1 segundo
                if self._cache_worker.isRunning():
                    self._cache_worker.terminate()
            
            if hasattr(self, '_load_worker') and self._load_worker and self._load_worker.isRunning():
                print("[DEBUG] Finalizando thread de carregamento...")
                self._load_worker.wait(1000)
                if self._load_worker.isRunning():
                    self._load_worker.terminate()
            
            # Finaliza threads de geração de PDF
            if hasattr(self, '_pdf_workers'):
                for worker in self._pdf_workers[:]:  # Cópia da lista
                    if worker and worker.isRunning():
                        print(f"[DEBUG] Aguardando finalização de thread PDF...")
                        worker.wait(2000)  # Aguarda até 2 segundos
                        if worker.isRunning():
                            print(f"[DEBUG] Forçando término de thread PDF...")
                            worker.terminate()
                            worker.wait(500)
                self._pdf_workers.clear()
            
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            QApplication.quit()
    
    def closeEvent(self, event: QCloseEvent):
        """Intercepta o evento de fechar a janela."""
        # Finaliza threads ativas
        if self._cache_worker and self._cache_worker.isRunning():
            self._cache_worker.wait(1000)  # Aguarda até 1 segundo
            if self._cache_worker.isRunning():
                self._cache_worker.terminate()  # Força finalização se necessário
        
        if hasattr(self, '_load_worker') and self._load_worker and self._load_worker.isRunning():
            self._load_worker.wait(1000)
            if self._load_worker.isRunning():
                self._load_worker.terminate()
        
        # Finaliza threads de geração de PDF
        if hasattr(self, '_pdf_workers'):
            for worker in self._pdf_workers[:]:  # Cópia da lista
                if worker and worker.isRunning():
                    print(f"[DEBUG] Aguardando finalização de thread PDF...")
                    worker.wait(2000)  # Aguarda até 2 segundos
                    if worker.isRunning():
                        print(f"[DEBUG] Forçando término de thread PDF...")
                        worker.terminate()
                        worker.wait(500)
            self._pdf_workers.clear()
        
        # Ao invés de fechar, minimiza para bandeja
        event.ignore()
        self.hide()
        
        # Mostra notificação
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Busca de Notas Fiscais",
                "O sistema continua rodando em segundo plano. Clique com botão direito no ícone da bandeja para acessar as opções.",
                QSystemTrayIcon.Information,
                3000
            )
    
    def _update_search_status(self):
        """Atualiza o status da busca no rodapé."""
        try:
            if self._search_in_progress:
                self.status_label.setText("🔄 Busca em andamento...")
            elif self._next_search_time:
                from datetime import datetime
                now = datetime.now()
                diff = (self._next_search_time - now).total_seconds()
                
                if diff > 0:
                    minutes = int(diff / 60)
                    seconds = int(diff % 60)
                    if minutes > 0:
                        self.status_label.setText(f"⏳ Próxima busca em {minutes}min {seconds}s")
                    else:
                        self.status_label.setText(f"⏳ Próxima busca em {seconds}s")
                else:
                    self.status_label.setText("⏳ Iniciando próxima busca...")
                    self._next_search_time = None
            else:
                # Atualiza com última busca se não estiver buscando
                last_search_text = self._get_last_search_status()
                self.status_label.setText(last_search_text)
        except Exception as e:
            print(f"[DEBUG] Erro em _update_search_status: {e}")
            import traceback
            traceback.print_exc()

    def _setup_tasks_menu(self):
        # Cria um menu 'Configurações' no menu bar com as ações principais
        menubar = self.menuBar()
        tarefas = menubar.addMenu("Configurações")

        # Helper para criar ações com ícone opcional (QStyle ou arquivo)
        def add_action(menu: QMenu, text: str, slot, shortcut: Optional[str] = None, icon_name: Optional[str] = None, qstyle_icon=None):
            act = QAction(text, self)
            if shortcut:
                try:
                    act.setShortcut(shortcut)
                except Exception:
                    pass
            # Tenta QStyle icon primeiro, depois arquivo
            if qstyle_icon:
                try:
                    act.setIcon(self.style().standardIcon(qstyle_icon))
                except Exception:
                    pass
            elif icon_name:
                try:
                    icon_path = BASE_DIR / 'Icone' / icon_name
                    if icon_path.exists():
                        act.setIcon(QIcon(str(icon_path)))
                except Exception:
                    pass
            act.triggered.connect(slot)
            menu.addAction(act)
            return act

        # Ações principais já presentes na toolbar
        add_action(tarefas, "Atualizar", self.refresh_all, "F5", qstyle_icon=QStyle.SP_BrowserReload)
        add_action(tarefas, "🔄 Sincronizar XMLs", self.sincronizar_xmls_interface, "Ctrl+Shift+S", qstyle_icon=QStyle.SP_FileDialogDetailedView)
        add_action(tarefas, "📥 Baixar XMLs Faltantes", self.baixar_xmls_faltantes_por_chave, "Ctrl+Shift+D", qstyle_icon=QStyle.SP_ArrowDown)
        tarefas.addSeparator()
        add_action(tarefas, "Buscar na SEFAZ", self.do_search, "Ctrl+B", qstyle_icon=QStyle.SP_FileDialogContentsView)
        add_action(tarefas, "Busca Completa", self.do_busca_completa, "Ctrl+Shift+B", qstyle_icon=QStyle.SP_FileDialogDetailedView)
        add_action(tarefas, "PDFs em lote…", self.do_batch_pdf, "Ctrl+P", qstyle_icon=QStyle.SP_FileIcon)
        tarefas.addSeparator()
        add_action(tarefas, "Busca por chave", self.buscar_por_chave, "Ctrl+K", qstyle_icon=QStyle.SP_FileDialogListView)
        add_action(tarefas, "Certificados…", self.open_certificates, "Ctrl+Shift+C", qstyle_icon=QStyle.SP_DialogApplyButton)
        tarefas.addSeparator()
        add_action(tarefas, "💾 Armazenamento…", self.open_storage_config, "Ctrl+Shift+A", qstyle_icon=QStyle.SP_DriveFDIcon)
        tarefas.addSeparator()
        add_action(tarefas, "🔄 Atualizações", self.check_updates, "Ctrl+U", qstyle_icon=QStyle.SP_BrowserReload)
        tarefas.addSeparator()
        add_action(tarefas, "Limpar", self.limpar_dados, "Ctrl+Shift+L", qstyle_icon=QStyle.SP_TrashIcon)
        tarefas.addSeparator()
        add_action(tarefas, "Abrir XMLs", self.open_xmls_folder, "Ctrl+Shift+X", qstyle_icon=QStyle.SP_DirIcon)
        add_action(tarefas, "Abrir logs", self.open_logs_folder, "Ctrl+L", qstyle_icon=QStyle.SP_FileDialogInfoView)

        # Alternativa: alternar 'PDF simples' (guarda em QSettings). Útil para modo seguro.
        try:
            self._act_pdf_simples = QAction("Usar PDF simples (modo seguro)", self)
            self._act_pdf_simples.setCheckable(True)
            s = QSettings('NFE_System', 'BOT_NFE')
            enabled = bool(s.value('pdf/force_simple_fallback', False, type=bool))
            self._act_pdf_simples.setChecked(enabled)
            def _toggle_pdf_simple(checked: bool):
                try:
                    QSettings('NFE_System', 'BOT_NFE').setValue('pdf/force_simple_fallback', bool(checked))
                except Exception:
                    pass
                self.set_status("PDF simples: " + ("ativado" if checked else "desativado"), 2500)
            self._act_pdf_simples.toggled.connect(_toggle_pdf_simple)
            tarefas.addSeparator()
            tarefas.addAction(self._act_pdf_simples)
        except Exception:
            pass

    def sincronizar_xmls_interface(self):
        """Sincroniza dados da interface com XMLs físicos.
        Remove registros órfãos (sem XML correspondente)."""
        try:
            from pathlib import Path
            import os
            
            # Confirma operação
            reply = QMessageBox.question(
                self,
                "Sincronizar XMLs",
                "Esta operação irá:\n\n"
                "• Verificar todos os registros na interface\n"
                "• Remover registros sem XML físico correspondente\n"
                "• Verificar XMLs em pastas locais e banco de dados\n\n"
                "Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            self.set_status("Sincronizando XMLs com interface...", 0)
            QApplication.processEvents()
            
            # Estatísticas
            total_registros = 0
            registros_ok = 0
            registros_removidos = 0
            chaves_removidas = []
            
            # Carrega todos os registros do banco
            with sqlite3.connect(str(DB_PATH)) as conn:
                rows = conn.execute("SELECT chave FROM xmls_baixados").fetchall()
                total_registros = len(rows)
                
                # Cria diálogo de progresso
                from PyQt5.QtWidgets import QProgressDialog
                progress = QProgressDialog(
                    "Sincronizando XMLs...",
                    "Cancelar",
                    0,
                    total_registros,
                    self
                )
                progress.setWindowTitle("Sincronização")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)
                
                cancelado = False
                
                for idx, (chave,) in enumerate(rows):
                    if progress.wasCanceled():
                        cancelado = True
                        break
                    
                    # Atualiza progresso
                    progress.setLabelText(
                        f"Verificando registro {idx + 1}/{total_registros}\n"
                        f"Chave: ...{chave[-12:]}\n\n"
                        f"✅ Encontrados: {registros_ok}\n"
                        f"❌ Removidos: {registros_removidos}"
                    )
                    progress.setValue(idx)
                    QApplication.processEvents()
                    
                    xml_existe = False
                    
                    # Busca em pastas locais
                    pastas = [
                        DATA_DIR / "xmls",
                        DATA_DIR / "xmls_chave",
                        DATA_DIR / "xml_NFs",
                        DATA_DIR / "xml_envio",
                        DATA_DIR / "xml_extraidos",
                        DATA_DIR / "xml_resposta_sefaz"
                    ]
                    
                    for pasta in pastas:
                        if not pasta.exists():
                            continue
                        
                        # Busca por nome de arquivo contendo a chave
                        for xml_file in pasta.rglob(f"*{chave}*.xml"):
                            xml_existe = True
                            break
                        
                        if xml_existe:
                            break
                    
                    if xml_existe:
                        registros_ok += 1
                    else:
                        # Remove registro órfão
                        conn.execute("DELETE FROM xmls_baixados WHERE chave = ?", (chave,))
                        registros_removidos += 1
                        chaves_removidas.append(chave)
                
                progress.setValue(total_registros)
                progress.close()
                
                if not cancelado:
                    conn.commit()
                else:
                    conn.rollback()
            
            # Mostra resumo
            if cancelado:
                mensagem = f"⏸️ Sincronização cancelada!\n\n"
            else:
                mensagem = f"✅ Sincronização concluída!\n\n"
            
            mensagem += f"Total de registros verificados: {idx + 1}/{total_registros}\n"
            mensagem += f"✅ XMLs encontrados: {registros_ok}\n"
            mensagem += f"❌ Registros removidos: {registros_removidos}\n"
            
            if chaves_removidas:
                mensagem += f"\n📋 Chaves removidas (primeiras 10):\n"
                for chave in chaves_removidas[:10]:
                    mensagem += f"  • {chave[:8]}...{chave[-8:]}\n"
                
                if len(chaves_removidas) > 10:
                    mensagem += f"  ... e mais {len(chaves_removidas) - 10} chaves\n"
            
            QMessageBox.information(self, "Sincronização Concluída", mensagem)
            
            # Atualiza interface
            self.refresh_all()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro na Sincronização", f"Erro ao sincronizar XMLs: {e}")
        finally:
            self.set_status("Sincronização concluída", 3000)

    def baixar_xmls_faltantes_por_chave(self):
        """Baixa XMLs completos usando consulta por chave (sem erro 656).
        Ideal para buscar XMLs que faltam quando tem bloqueio no NSU."""
        try:
            # Busca chaves sem arquivo XML
            with sqlite3.connect(str(DB_PATH)) as conn:
                # Busca chaves que não tem caminho_arquivo
                rows = conn.execute("""
                    SELECT xmls_baixados.chave, xmls_baixados.cnpj_cpf, 
                           certificados.cnpj_cpf, certificados.caminho, 
                           certificados.senha, certificados.cUF_autor
                    FROM xmls_baixados
                    JOIN certificados ON xmls_baixados.cnpj_cpf = certificados.informante
                    WHERE (xmls_baixados.caminho_arquivo IS NULL OR xmls_baixados.caminho_arquivo = '')
                    LIMIT 100
                """).fetchall()
                
                total_faltantes = len(rows)
            
            if total_faltantes == 0:
                QMessageBox.information(
                    self,
                    "XMLs Completos",
                    "✅ Todos os registros já possuem XML completo!"
                )
                return
            
            # Confirma operação
            reply = QMessageBox.question(
                self,
                "Baixar XMLs Faltantes",
                f"Encontradas {total_faltantes} chaves sem XML completo.\n\n"
                f"Esta operação irá:\n"
                f"• Consultar cada chave individualmente na SEFAZ\n"
                f"• Baixar XML completo usando consulta por chave\n"
                f"• NÃO gera erro 656 (pode usar a qualquer momento)\n"
                f"• Respeita limite de ~50 consultas/minuto\n\n"
                f"⏱️ Tempo estimado: ~{(total_faltantes / 50):.0f}-{(total_faltantes / 40):.0f} minutos\n\n"
                f"Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Importa função de consulta
            import sys
            sys.path.insert(0, str(BASE_DIR))
            from nfe_search import consultar_nfe_por_chave
            
            # Importa sistema de descriptografia
            try:
                from modules.crypto_portable import get_portable_crypto as get_crypto
                crypto = get_crypto()
                CRYPTO_AVAILABLE = True
            except ImportError:
                CRYPTO_AVAILABLE = False
                print("⚠️ Sistema de criptografia não disponível")
            
            # Dicionário para rastrear certificados com problemas
            certificados_com_erro = {}
            
            # Progresso
            from PyQt5.QtWidgets import QProgressDialog
            progress = QProgressDialog(
                "Baixando XMLs por chave...",
                "Cancelar",
                0,
                total_faltantes,
                self
            )
            progress.setWindowTitle("Baixando XMLs")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            sucessos = 0
            falhas = 0
            cancelado = False
            
            import time
            
            for idx, (chave, cnpj_cpf, cnpj_cert, cert_path, senha_encriptada, cuf) in enumerate(rows):
                if progress.wasCanceled():
                    cancelado = True
                    break
                
                try:
                    # Descriptografa a senha se necessário
                    senha = senha_encriptada
                    if CRYPTO_AVAILABLE and senha_encriptada:
                        try:
                            senha = crypto.decrypt(senha_encriptada)
                        except Exception as e:
                            # Se falhar ao descriptografar, assume que é texto plano
                            print(f"⚠️ Usando senha em texto plano (não descriptografada): {e}")
                            senha = senha_encriptada
                    
                    progress.setLabelText(
                        f"Baixando XML {idx + 1}/{total_faltantes}\n"
                        f"Chave: ...{chave[-12:]}\n"
                        f"✅ Sucessos: {sucessos} | ❌ Falhas: {falhas}"
                    )
                    progress.setValue(idx)
                    QApplication.processEvents()
                    
                    # Consulta por chave (sem erro 656!)
                    xml = consultar_nfe_por_chave(chave, cert_path, senha, cnpj_cert, cuf)
                    
                    if xml:
                        # Salva XML em arquivo na pasta xmls_chave/cnpj/
                        pasta_cnpj = DATA_DIR / "xmls_chave" / cnpj_cpf
                        pasta_cnpj.mkdir(parents=True, exist_ok=True)
                        
                        caminho_xml = pasta_cnpj / f"{chave}.xml"
                        caminho_xml.write_text(xml, encoding='utf-8')
                        
                        # Atualiza caminho no banco
                        with sqlite3.connect(str(DB_PATH)) as conn:
                            conn.execute(
                                "UPDATE xmls_baixados SET caminho_arquivo = ? WHERE chave = ?",
                                (str(caminho_xml), chave)
                            )
                            conn.commit()
                        sucessos += 1
                    else:
                        falhas += 1
                    
                    # Rate limit: ~50 por minuto = 1.2 segundos entre requisições
                    if (idx + 1) % 50 == 0:
                        # A cada 50 requisições, aguarda 1 minuto
                        for segundo in range(60, 0, -1):
                            if progress.wasCanceled():
                                cancelado = True
                                break
                            progress.setLabelText(
                                f"⏸️ Rate limit: aguardando {segundo}s...\n"
                                f"Processados: {idx + 1}/{total_faltantes}\n"
                                f"✅ Sucessos: {sucessos} | ❌ Falhas: {falhas}"
                            )
                            QApplication.processEvents()
                            time.sleep(1)
                        
                        if cancelado:
                            break
                    else:
                        # Pequeno delay entre requisições
                        time.sleep(1.2)
                    
                except Exception as e:
                    erro_msg = str(e)
                    print(f"Erro ao consultar chave {chave}: {erro_msg}")
                    
                    # Rastreia certificados com problema
                    cert_info = f"{cert_cnpj} (UF {cuf}) - {cert_path}"
                    if cert_info not in certificados_com_erro:
                        certificados_com_erro[cert_info] = {
                            'count': 0,
                            'erro': erro_msg,
                            'chaves': []
                        }
                    certificados_com_erro[cert_info]['count'] += 1
                    if len(certificados_com_erro[cert_info]['chaves']) < 3:
                        certificados_com_erro[cert_info]['chaves'].append(chave[:20] + '...')
                    
                    falhas += 1
            
            progress.setValue(total_faltantes)
            progress.close()
            
            # Mostra resumo
            if cancelado:
                mensagem = f"⏸️ Operação cancelada!\n\n"
            else:
                mensagem = f"✅ Download concluído!\n\n"
            
            mensagem += f"Total processado: {idx + 1}/{total_faltantes}\n"
            mensagem += f"✅ Sucessos: {sucessos}\n"
            mensagem += f"❌ Falhas: {falhas}\n"
            
            if sucessos > 0:
                mensagem += f"\n💾 {sucessos} XMLs salvos no banco de dados!"
            
            # Adiciona relatório de certificados com problema
            if certificados_com_erro:
                mensagem += "\n\n⚠️ CERTIFICADOS COM PROBLEMAS:\n"
                mensagem += "=" * 50 + "\n"
                for cert_info, dados in certificados_com_erro.items():
                    mensagem += f"\n📜 {cert_info}\n"
                    mensagem += f"   Erro: {dados['erro']}\n"
                    mensagem += f"   Falhas: {dados['count']}\n"
                    if dados['chaves']:
                        mensagem += f"   Exemplos: {', '.join(dados['chaves'])}\n"
            
            QMessageBox.information(self, "Download Concluído", mensagem)
            
            # Atualiza interface
            if sucessos > 0:
                self.refresh_all()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao baixar XMLs: {e}")

    def refresh_all(self):
        # Evita reentrância e trava de UI: carrega notas em thread
        if self._loading_notes:
            return
        self._loading_notes = True
        try:
            if self.btn_refresh:
                self.btn_refresh.setEnabled(False)
        except Exception:
            pass
        self.set_status("Carregando…")

        class LoadNotesWorker(QThread):
            finished_notes = pyqtSignal(list)
            def __init__(self, db: UIDB, limit: int = 1000):
                super().__init__()
                self.db = db
                self.limit = limit
            def run(self):
                try:
                    notes = self.db.load_notes(limit=self.limit)
                except Exception:
                    notes = []
                self.finished_notes.emit(notes)

        def on_loaded(notes: List[Dict[str, Any]]):
            try:
                self.notes = notes or []
                try:
                    self._populate_certs_tree()
                except Exception:
                    pass
                self.refresh_table()
                self.refresh_emitidos_table()  # Popula também a tabela de emitidos
                self.set_status(f"{len(self.notes)} registros carregados", 3000)
                
                # Constrói cache de PDFs em background (não bloqueia UI)
                if self.notes and not self._cache_building:
                    self._build_pdf_cache_async()
                
                # Gera PDFs faltantes em segundo plano
                QTimer.singleShot(1000, self._gerar_pdfs_faltantes)
                    
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao carregar dados: {e}")
            finally:
                self._loading_notes = False
                try:
                    if self.btn_refresh:
                        self.btn_refresh.setEnabled(True)
                except Exception:
                    pass
                self._load_worker = None

        self._load_worker = LoadNotesWorker(self.db, limit=1000)
        self._load_worker.finished_notes.connect(on_loaded)
        self._load_worker.start()
    
    def _clear_date_filters(self):
        """Limpa os filtros de data (volta ao padrão)"""
        try:
            from PyQt5.QtCore import QDate
            # Remove valores dos campos de data (desabilita filtro)
            self.date_inicio.setDate(QDate.currentDate().addMonths(-3))
            self.date_fim.setDate(QDate.currentDate())
            self.set_status("Filtro de data limpo", 1500)
        except Exception as e:
            print(f"[DEBUG] Erro ao limpar filtros de data: {e}")
    
    def _save_limit_preference(self, limit_text: str):
        """Salva a preferência de limite de exibição do usuário"""
        try:
            settings = QSettings('NFE_System', 'BOT_NFE')
            settings.setValue('display/limit', limit_text)
            settings.sync()
        except Exception as e:
            print(f"[DEBUG] Erro ao salvar preferência de limite: {e}")

    def filtered(self) -> List[Dict[str, Any]]:
        q = (self.search_edit.text() or "").lower().strip()
        selected_cert = getattr(self, '_selected_cert_cnpj', None)
        st = (self.status_dd.currentText() or "Todos").lower()
        tp = (self.tipo_dd.currentText() or "Todos").lower().replace('-', '')
        
        # Filtro de data
        date_inicio_filter = None
        date_fim_filter = None
        if hasattr(self, 'date_inicio') and hasattr(self, 'date_fim'):
            try:
                from PyQt5.QtCore import QDate
                # Verifica se não é a data padrão (não aplicar filtro se usuário não alterou)
                date_inicio_qdate = self.date_inicio.date()
                date_fim_qdate = self.date_fim.date()
                
                # Só aplica filtro se as datas forem válidas
                if date_inicio_qdate.isValid() and date_fim_qdate.isValid():
                    date_inicio_filter = date_inicio_qdate.toString("yyyy-MM-dd")
                    date_fim_filter = date_fim_qdate.toString("yyyy-MM-dd")
            except Exception as e:
                print(f"[DEBUG] Erro ao processar filtro de data: {e}")
        
        # Limite de linhas
        limit_text = self.limit_dd.currentText()
        limit = None if limit_text == "Todos" else int(limit_text)
        
        out: List[Dict[str, Any]] = []
        for it in (self.notes or []):
            # NÃO MOSTRAR eventos na interface (apenas armazenar em disco)
            xml_status = (it.get('xml_status') or '').upper()
            if xml_status == 'EVENTO':
                continue
            
            if selected_cert:
                # Filtra por 'informante' (CNPJ/CPF do certificado que trouxe a nota)
                nota_informante = str(it.get('informante') or '').strip()
                if nota_informante != str(selected_cert).strip():
                    continue
            if q:
                if q not in (it.get("nome_emitente", "").lower()) and q not in (str(it.get("numero", "")).lower()) and q not in (it.get("cnpj_emitente", "").lower()):
                    continue
            if st != "todos" and st not in (it.get("status", "").lower()):
                continue
            if tp != "todos":
                raw = (it.get("tipo", "") or "").strip().upper().replace('_','').replace(' ','')
                if tp == "nfe" and raw not in ("NFE", "NF-E"):
                    continue
                if tp == "cte" and raw not in ("CTE", "CT-E"):
                    continue
                if tp == "nfse" and raw not in ("NFSE", "NFS-E"):
                    continue
            
            # Filtro de data
            if date_inicio_filter and date_fim_filter:
                data_emissao = (it.get("data_emissao") or "")[:10]  # YYYY-MM-DD
                if data_emissao:
                    if not (date_inicio_filter <= data_emissao <= date_fim_filter):
                        continue
            
            out.append(it)
            
            # Aplica limite se definido
            if limit and len(out) >= limit:
                break
        
        return out
    
    def filtered_emitidos(self) -> List[Dict[str, Any]]:
        """Filtra notas emitidas pela empresa (onde cnpj_emitente pertence a um certificado)"""
        q = (self.search_edit.text() or "").lower().strip()
        selected_cert = getattr(self, '_selected_cert_cnpj', None)
        st = (self.status_dd.currentText() or "Todos").lower()
        tp = (self.tipo_dd.currentText() or "Todos").lower().replace('-', '')
        
        # Filtro de data
        date_inicio_filter = None
        date_fim_filter = None
        if hasattr(self, 'date_inicio') and hasattr(self, 'date_fim'):
            try:
                from PyQt5.QtCore import QDate
                date_inicio_qdate = self.date_inicio.date()
                date_fim_qdate = self.date_fim.date()
                
                if date_inicio_qdate.isValid() and date_fim_qdate.isValid():
                    date_inicio_filter = date_inicio_qdate.toString("yyyy-MM-dd")
                    date_fim_filter = date_fim_qdate.toString("yyyy-MM-dd")
            except Exception as e:
                print(f"[DEBUG] Erro ao processar filtro de data: {e}")
        
        # Limite de linhas
        limit_text = self.limit_dd.currentText()
        limit = None if limit_text == "Todos" else int(limit_text)
        
        # Função para normalizar CNPJ (remove pontuação)
        def normalizar_cnpj(cnpj: str) -> str:
            return ''.join(c for c in str(cnpj or '') if c.isdigit())
        
        # Carrega CNPJs dos certificados cadastrados
        try:
            certs = self.db.load_certificates()
            company_cnpjs = {normalizar_cnpj(c.get('cnpj_cpf') or '') for c in certs}
            company_cnpjs.discard('')  # Remove string vazia se houver
            print(f"[DEBUG] Certificados encontrados: {len(certs)}")
            print(f"[DEBUG] CNPJs da empresa (normalizados): {company_cnpjs}")
        except Exception as e:
            print(f"[DEBUG] Erro ao carregar certificados: {e}")
            company_cnpjs = set()
        
        if not company_cnpjs:
            print(f"[DEBUG] Nenhum certificado encontrado, retornando lista vazia")
            return []
        
        # ALTERAÇÃO: Carrega DIRETAMENTE do banco com filtros SQL em vez de usar self.notes
        # Isso garante que todas as notas emitidas sejam encontradas, não apenas as primeiras 1000
        out: List[Dict[str, Any]] = []
        
        try:
            with self.db._connect() as conn:
                # DIAGNÓSTICO: Verifica o que existe no banco
                try:
                    total_notas = conn.execute("SELECT COUNT(*) FROM notas_detalhadas").fetchone()[0]
                    total_nao_eventos = conn.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status != 'EVENTO'").fetchone()[0]
                    print(f"[DEBUG] Total de notas no banco: {total_notas}")
                    print(f"[DEBUG] Total de notas não-eventos: {total_nao_eventos}")
                    
                    # Verifica se cnpj_emitente tem valores
                    sample_cnpjs = conn.execute("""
                        SELECT DISTINCT cnpj_emitente 
                        FROM notas_detalhadas 
                        WHERE cnpj_emitente IS NOT NULL AND cnpj_emitente != '' 
                        LIMIT 10
                    """).fetchall()
                    print(f"[DEBUG] Exemplos de cnpj_emitente no banco:")
                    for (cnpj,) in sample_cnpjs[:5]:
                        normalized = ''.join(c for c in str(cnpj or '') if c.isdigit())
                        print(f"[DEBUG]   - {cnpj} (normalizado: {normalized})")
                    
                    # Testa a query de normalização diretamente
                    for test_cnpj in list(company_cnpjs)[:2]:
                        test_result = conn.execute(f"""
                            SELECT COUNT(*) 
                            FROM notas_detalhadas 
                            WHERE REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '/', ''), '-', '') = ?
                            AND xml_status != 'EVENTO'
                        """, (test_cnpj,)).fetchone()[0]
                        print(f"[DEBUG] Teste CNPJ {test_cnpj}: {test_result} notas encontradas")
                except Exception as e:
                    print(f"[DEBUG] Erro no diagnóstico: {e}")
                
                # Constrói query SQL com filtros
                where_clauses = ["xml_status != 'EVENTO'"]
                params = []
                
                # Filtro PRINCIPAL: cnpj_emitente nos certificados da empresa
                # Normaliza CNPJ removendo pontuação (apenas dígitos) para comparação
                cnpjs_placeholders = ','.join(['?' for _ in company_cnpjs])
                where_clauses.append(f"REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '/', ''), '-', '') IN ({cnpjs_placeholders})")
                params.extend(list(company_cnpjs))
                
                # Filtro por certificado selecionado
                if selected_cert:
                    where_clauses.append("REPLACE(REPLACE(REPLACE(cnpj_emitente, '.', ''), '/', ''), '-', '') = ?")
                    params.append(normalizar_cnpj(str(selected_cert)))
                
                # Filtro por status
                if st != "todos":
                    where_clauses.append("LOWER(status) LIKE ?")
                    params.append(f"%{st}%")
                
                # Filtro por tipo
                if tp != "todos":
                    tipo_patterns = []
                    if tp == "nfe":
                        tipo_patterns = ["NFE", "NF-E"]
                    elif tp == "cte":
                        tipo_patterns = ["CTE", "CT-E"]
                    elif tp == "nfse":
                        tipo_patterns = ["NFSE", "NFS-E"]
                    
                    if tipo_patterns:
                        tipo_clauses = " OR ".join(["UPPER(REPLACE(REPLACE(tipo, '_', ''), ' ', '')) = ?" for _ in tipo_patterns])
                        where_clauses.append(f"({tipo_clauses})")
                        params.extend(tipo_patterns)
                
                # Filtro por data
                if date_inicio_filter and date_fim_filter:
                    where_clauses.append("SUBSTR(data_emissao, 1, 10) BETWEEN ? AND ?")
                    params.extend([date_inicio_filter, date_fim_filter])
                
                # Busca por texto (nome, número, CNPJ)
                if q:
                    where_clauses.append("(LOWER(nome_emitente) LIKE ? OR CAST(numero AS TEXT) LIKE ? OR cnpj_emitente LIKE ?)")
                    params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
                
                # Monta query completa
                where_sql = " AND ".join(where_clauses)
                query = f"SELECT * FROM notas_detalhadas WHERE {where_sql} ORDER BY data_emissao DESC"
                
                # Aplica limite se definido
                if limit:
                    query += f" LIMIT {limit}"
                
                print(f"[DEBUG] Query SQL para notas emitidas: {query[:200]}...")
                print(f"[DEBUG] Parâmetros: {params[:10]}...")
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                for row in rows:
                    out.append(dict(zip(columns, row)))
                
                print(f"[DEBUG] Total de notas emitidas carregadas do banco: {len(out)}")
                
        except Exception as e:
            print(f"[DEBUG] Erro ao carregar notas emitidas do banco: {e}")
            import traceback
            traceback.print_exc()
        
        return out

    def _populate_certs_tree(self):
        # Preenche a árvore com certificados do banco (ativos)
        try:
            certs = self.db.load_certificates()
        except Exception:
            certs = []
        
        # Salva a seleção atual antes de limpar
        current_selection = getattr(self, '_selected_cert_cnpj', None)
        
        # Bloqueia sinais para evitar múltiplos triggers durante repopulação
        self.tree_certs.blockSignals(True)
        try:
            self.tree_certs.clear()
            # Add 'Todos' entry on top
            all_item = QTreeWidgetItem(["Todos"])
            all_item.setData(0, 32, None)
            self.tree_certs.addTopLevelItem(all_item)
            
            # Se não há seleção, seleciona "Todos" por padrão
            if current_selection is None:
                all_item.setSelected(True)
            
            # Ordena por razao_social ou informante
            def keyf(c: Dict[str, Any]):
                razao = (c.get('razao_social') or '').strip()
                informante = (c.get('informante') or '').strip()
                cnpj = (c.get('cnpj_cpf') or '').strip()
                return (razao or informante or cnpj).lower()
            
            for c in sorted(certs, key=keyf):
                informante = (c.get('informante') or '').strip()
                cnpj = (c.get('cnpj_cpf') or '').strip()
                razao_social = (c.get('razao_social') or '').strip()
                
                # Prioriza razão social, depois informante, depois CNPJ
                if razao_social:
                    label = f"{razao_social}"
                elif informante and informante != cnpj:
                    label = f"{informante}"
                elif cnpj:
                    label = cnpj
                else:
                    label = 'Sem nome'
                
                node = QTreeWidgetItem([label])
                node.setToolTip(0, f"CNPJ: {cnpj}\nCaminho: {c.get('caminho') or ''}")
                node.setData(0, 32, informante)  # Salva informante, não cnpj_cpf
                self.tree_certs.addTopLevelItem(node)
                
                # Restaura seleção se corresponder ao item atual
                if current_selection and str(informante).strip() == str(current_selection).strip():
                    node.setSelected(True)
        finally:
            # Reativa sinais
            self.tree_certs.blockSignals(False)

    def _on_tree_cert_clicked(self, item: QTreeWidgetItem, col: int):
        try:
            informante = item.data(0, 32)
            # Converte para string ou None
            if informante:
                new_selection = str(informante).strip()
            else:
                new_selection = None
            
            # Só atualiza se a seleção mudou
            if new_selection != self._selected_cert_cnpj:
                self._selected_cert_cnpj = new_selection
                self.search_edit.clear()
                self.refresh_table()
        except Exception:
            pass

    def _format_date_br(self, date_str: str) -> str:
        """Converte data de AAAA-MM-DD para DD/MM/AAAA."""
        if not date_str:
            return ""
        try:
            # Se já está no formato DD/MM/AAAA, retorna como está
            if "/" in date_str:
                return date_str
            # Converte de AAAA-MM-DD para DD/MM/AAAA
            date_part = date_str[:10]  # Pega apenas a parte da data
            if len(date_part) == 10 and date_part[4] == '-' and date_part[7] == '-':
                ano, mes, dia = date_part.split('-')
                return f"{dia}/{mes}/{ano}"
            return date_str
        except Exception:
            return date_str
    
    def _codigo_uf_to_sigla(self, codigo: str) -> str:
        """Converte código UF para sigla."""
        if not codigo:
            return ""
        # Mapeamento de código para sigla UF
        codigo_to_uf = {
            '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA',
            '16': 'AP', '17': 'TO', '21': 'MA', '22': 'PI', '23': 'CE',
            '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE',
            '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP',
            '41': 'PR', '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT',
            '52': 'GO', '53': 'DF'
        }
        return codigo_to_uf.get(str(codigo).strip(), codigo)
    
    def refresh_table(self):
        # Stop any ongoing fill
        try:
            if self._table_fill_timer.isActive():
                self._table_fill_timer.stop()
        except Exception:
            pass
        items = self.filtered()
        # Prepare table
        try:
            self._restore_sorting = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
        except Exception:
            self._restore_sorting = False
        try:
            self.table.clearContents()
            self.table.setRowCount(len(items))
        except Exception:
            pass
        # Start incremental fill
        self._table_fill_items = items
        self._table_fill_index = 0
        self._table_filling = True
        self.set_status("Montando tabela…")
        try:
            self._table_fill_timer.start()
        except Exception:
            # Fallback: if timer fails, do synchronous (last resort)
            for r, it in enumerate(items):
                self._populate_row(r, it)
            try:
                self.table.setSortingEnabled(self._restore_sorting)
            except Exception:
                pass
            self._table_filling = False
            self.set_status(f"{len(items)} registros carregados", 2000)
    
    def refresh_emitidos_table(self):
        """Popula a tabela de notas emitidas pela empresa (usa mesma lógica de _populate_row)"""
        # Evitar múltiplas execuções simultâneas
        if self._refreshing_emitidos:
            print("[DEBUG] ⏭️ refresh_emitidos_table já está executando, pulando chamada duplicada")
            return
        
        self._refreshing_emitidos = True
        try:
            print("[DEBUG] ========== REFRESH_EMITIDOS_TABLE CHAMADO ==========")
            items = self.filtered_emitidos()
            print(f"[DEBUG] Populando tabela_emitidos com {len(items)} itens")
            
            try:
                sorting_enabled = self.table_emitidos.isSortingEnabled()
                self.table_emitidos.setSortingEnabled(False)
            except Exception:
                sorting_enabled = False
            
            try:
                self.table_emitidos.clearContents()
                self.table_emitidos.setRowCount(len(items))
            except Exception:
                pass
            
            # Popula diretamente (sem timer, pois geralmente há menos itens)
            for r, it in enumerate(items):
                self._populate_emitidos_row(r, it)
            
            try:
                self.table_emitidos.setSortingEnabled(sorting_enabled)
            except Exception:
                pass
        finally:
            self._refreshing_emitidos = False

    def _populate_row(self, r: int, it: Dict[str, Any]):
        def cell(c: Any) -> QTableWidgetItem:
            return QTableWidgetItem(str(c or ""))
        
        xml_status = (it.get("xml_status") or "RESUMO").upper()
        
        # Define texto e cores baseado no tipo (eventos não aparecem aqui pois são filtrados)
        if xml_status == "COMPLETO":
            status_text = ""  # Apenas ícone, sem texto
            bg_color = QColor(214, 245, 224)  # Verde claro
            tooltip_text = "✅ XML Completo disponível"
        else:  # RESUMO
            status_text = ""  # Apenas ícone, sem texto
            bg_color = QColor(235, 235, 235)  # Cinza claro
            tooltip_text = "⚠️ Apenas Resumo - clique para baixar XML completo"
        
        c0 = cell(status_text)
        c0.setBackground(QBrush(bg_color))
        c0.setTextAlignment(Qt.AlignCenter)
        c0.setToolTip(tooltip_text)
        try:
            icon_path = BASE_DIR / 'Icone' / 'xml.png'
            if icon_path.exists():
                c0.setIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        self.table.setItem(r, 0, c0)
        # Coluna Número - ordenação numérica
        numero = it.get("numero") or ""
        try:
            numero_int = int(str(numero)) if numero else 0
        except Exception:
            numero_int = 0
        self.table.setItem(r, 1, NumericTableWidgetItem(str(numero), float(numero_int)))
        # Coluna Data Emissão - ordenação por timestamp
        data_emissao_raw = it.get("data_emissao") or ""
        data_emissao_br = self._format_date_br(data_emissao_raw)
        # Converte data para timestamp para ordenação correta
        try:
            if data_emissao_raw and len(data_emissao_raw) >= 10:
                from datetime import datetime
                dt = datetime.strptime(data_emissao_raw[:10], "%Y-%m-%d")
                timestamp = dt.timestamp()
            else:
                timestamp = 0.0
        except Exception:
            timestamp = 0.0
        self.table.setItem(r, 2, NumericTableWidgetItem(data_emissao_br, timestamp))
        self.table.setItem(r, 3, cell(it.get("tipo")))
        # Coluna Valor - ordenação numérica com exibição formatada
        valor_raw = it.get("valor")
        valor_formatado = ""
        valor_num = 0.0
        try:
            if valor_raw:
                # Se já estiver formatado (R$ 1.234,56), precisa limpar antes
                valor_str = str(valor_raw).replace("R$", "").strip()
                # Remove pontos (milhares) e substitui vírgula por ponto (decimal)
                valor_str = valor_str.replace(".", "").replace(",", ".")
                valor_num = float(valor_str)
                # Formata no padrão brasileiro
                valor_formatado = f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_formatado = ""
        except Exception as e:
            # Se falhar, tenta conversão simples
            try:
                valor_num = float(str(valor_raw).replace(",", "."))
                valor_formatado = f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                valor_formatado = str(valor_raw or "")
                valor_num = 0.0
        c_val = NumericTableWidgetItem(valor_formatado, valor_num)
        c_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(r, 4, c_val)
        # Coluna Vencimento - ordenação por timestamp
        vencimento_raw = it.get("vencimento") or ""
        vencimento_br = self._format_date_br(vencimento_raw)
        try:
            if vencimento_raw and len(vencimento_raw) >= 10:
                from datetime import datetime
                dt = datetime.strptime(vencimento_raw[:10], "%Y-%m-%d")
                timestamp = dt.timestamp()
            else:
                timestamp = 0.0
        except Exception:
            timestamp = 0.0
        self.table.setItem(r, 5, NumericTableWidgetItem(vencimento_br, timestamp))
        
        # Coluna Status - ícone visual com cor de fundo
        status_low = (it.get("status") or '').lower()
        
        if 'cancelad' in status_low:
            # Cancelado: ✕ vermelho com fundo vermelho claro
            c_status = cell("✕")
            c_status.setForeground(QBrush(QColor(200, 0, 0)))
            c_status.setBackground(QBrush(QColor(255, 220, 220)))
            c_status.setFont(QFont("Arial", 16, QFont.Bold))
        elif 'autorizad' in status_low:
            # Autorizado: ✓ verde com fundo verde claro
            c_status = cell("✓")
            c_status.setForeground(QBrush(QColor(0, 150, 0)))
            c_status.setBackground(QBrush(QColor(214, 245, 224)))
            c_status.setFont(QFont("Arial", 16, QFont.Bold))
        elif 'denegad' in status_low or 'rejeitad' in status_low:
            # Denegado: ⚠ laranja com fundo amarelo claro
            c_status = cell("⚠")
            c_status.setForeground(QBrush(QColor(200, 120, 0)))
            c_status.setBackground(QBrush(QColor(255, 245, 200)))
            c_status.setFont(QFont("Arial", 14, QFont.Bold))
        else:
            # Outros: • cinza com fundo cinza claro
            c_status = cell("•")
            c_status.setForeground(QBrush(QColor(120, 120, 120)))
            c_status.setBackground(QBrush(QColor(240, 240, 240)))
            c_status.setFont(QFont("Arial", 14, QFont.Bold))
        
        c_status.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(r, 6, c_status)
        self.table.setItem(r, 7, cell(it.get("cnpj_emitente")))
        self.table.setItem(r, 8, cell(it.get("nome_emitente")))
        self.table.setItem(r, 9, cell(it.get("natureza")))
        self.table.setItem(r,10, cell(self._codigo_uf_to_sigla(it.get("uf") or "")))
        # Coluna Base ICMS - ordenação numérica
        base_icms_text = it.get("base_icms") or ""
        base_icms_num = 0.0
        try:
            # Remove "R$ " e converte formato brasileiro para float
            base_clean = str(base_icms_text).replace("R$", "").replace(".", "").replace(",", ".").strip()
            if base_clean:
                base_icms_num = float(base_clean)
        except Exception:
            pass
        c_base = NumericTableWidgetItem(base_icms_text, base_icms_num)
        c_base.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(r,11, c_base)
        # Coluna Valor ICMS - ordenação numérica
        valor_icms_text = it.get("valor_icms") or ""
        valor_icms_num = 0.0
        try:
            # Remove "R$ " e converte formato brasileiro para float
            icms_clean = str(valor_icms_text).replace("R$", "").replace(".", "").replace(",", ".").strip()
            if icms_clean:
                valor_icms_num = float(icms_clean)
        except Exception:
            pass
        c_icms = NumericTableWidgetItem(valor_icms_text, valor_icms_num)
        c_icms.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(r,12, c_icms)
        self.table.setItem(r,13, cell(it.get("cfop")))
        self.table.setItem(r,14, cell(it.get("ncm")))
        self.table.setItem(r,15, cell(it.get("ie_tomador")))
        self.table.setItem(r,16, cell(it.get("chave")))
    
    def _populate_emitidos_row(self, r: int, it: Dict[str, Any]):
        """Popula uma linha da tabela de emitidos (mesma estrutura que _populate_row)"""
        def cell(c: Any) -> QTableWidgetItem:
            return QTableWidgetItem(str(c or ""))
        
        xml_status = (it.get("xml_status") or "RESUMO").upper()
        
        # Define texto e cores baseado no tipo
        if xml_status == "COMPLETO":
            status_text = ""
            bg_color = QColor(214, 245, 224)
            tooltip_text = "✅ XML Completo disponível"
        else:
            status_text = ""
            bg_color = QColor(235, 235, 235)
            tooltip_text = "⚠️ Apenas Resumo - clique para baixar XML completo"
        
        c0 = cell(status_text)
        c0.setBackground(QBrush(bg_color))
        c0.setTextAlignment(Qt.AlignCenter)
        c0.setToolTip(tooltip_text)
        try:
            icon_path = BASE_DIR / 'Icone' / 'xml.png'
            if icon_path.exists():
                c0.setIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        self.table_emitidos.setItem(r, 0, c0)
        
        # Coluna Número - ordenação numérica
        numero = it.get("numero") or ""
        try:
            numero_int = int(str(numero)) if numero else 0
        except Exception:
            numero_int = 0
        self.table_emitidos.setItem(r, 1, NumericTableWidgetItem(str(numero), float(numero_int)))
        
        # Coluna Data Emissão - ordenação por timestamp
        data_emissao_raw = it.get("data_emissao") or ""
        data_emissao_br = self._format_date_br(data_emissao_raw)
        try:
            if data_emissao_raw and len(data_emissao_raw) >= 10:
                from datetime import datetime
                dt = datetime.strptime(data_emissao_raw[:10], "%Y-%m-%d")
                timestamp = dt.timestamp()
            else:
                timestamp = 0.0
        except Exception:
            timestamp = 0.0
        self.table_emitidos.setItem(r, 2, NumericTableWidgetItem(data_emissao_br, timestamp))
        
        self.table_emitidos.setItem(r, 3, cell(it.get("tipo")))
        
        # Coluna Valor - ordenação numérica com exibição formatada
        valor_raw = it.get("valor")
        valor_formatado = ""
        valor_num = 0.0
        try:
            if valor_raw:
                valor_str = str(valor_raw).replace("R$", "").strip()
                valor_str = valor_str.replace(".", "").replace(",", ".")
                valor_num = float(valor_str)
                valor_formatado = f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_formatado = ""
        except Exception:
            try:
                valor_num = float(str(valor_raw).replace(",", "."))
                valor_formatado = f"R$ {valor_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                valor_formatado = str(valor_raw or "")
                valor_num = 0.0
        c_val = NumericTableWidgetItem(valor_formatado, valor_num)
        c_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table_emitidos.setItem(r, 4, c_val)
        
        # Coluna Vencimento - ordenação por timestamp
        vencimento_raw = it.get("vencimento") or ""
        vencimento_br = self._format_date_br(vencimento_raw)
        try:
            if vencimento_raw and len(vencimento_raw) >= 10:
                from datetime import datetime
                dt = datetime.strptime(vencimento_raw[:10], "%Y-%m-%d")
                timestamp = dt.timestamp()
            else:
                timestamp = 0.0
        except Exception:
            timestamp = 0.0
        self.table_emitidos.setItem(r, 5, NumericTableWidgetItem(vencimento_br, timestamp))
        
        # Coluna Status - ícone visual com cor de fundo
        status_low = (it.get("status") or '').lower()
        
        if 'cancelad' in status_low:
            c_status = cell("✕")
            c_status.setForeground(QBrush(QColor(200, 0, 0)))
            c_status.setBackground(QBrush(QColor(255, 220, 220)))
            c_status.setFont(QFont("Arial", 16, QFont.Bold))
        elif 'autorizad' in status_low:
            c_status = cell("✓")
            c_status.setForeground(QBrush(QColor(0, 150, 0)))
            c_status.setBackground(QBrush(QColor(214, 245, 224)))
            c_status.setFont(QFont("Arial", 16, QFont.Bold))
        elif 'denegad' in status_low or 'rejeitad' in status_low:
            c_status = cell("⚠")
            c_status.setForeground(QBrush(QColor(200, 120, 0)))
            c_status.setBackground(QBrush(QColor(255, 245, 200)))
            c_status.setFont(QFont("Arial", 14, QFont.Bold))
        else:
            c_status = cell("•")
            c_status.setForeground(QBrush(QColor(120, 120, 120)))
            c_status.setBackground(QBrush(QColor(240, 240, 240)))
            c_status.setFont(QFont("Arial", 14, QFont.Bold))
        
        c_status.setTextAlignment(Qt.AlignCenter)
        self.table_emitidos.setItem(r, 6, c_status)
        
        # IMPORTANTE: Para emitidos, mostramos informante (que é o destinatário)
        # Os headers já foram renomeados para "Destinatário CNPJ" e "Destinatário Nome"
        self.table_emitidos.setItem(r, 7, cell(it.get("informante")))
        # Para o nome do destinatário, tentamos obter de outro campo se existir
        # Por enquanto, deixamos vazio ou usamos algum campo disponível
        self.table_emitidos.setItem(r, 8, cell(""))  # Nome destinatário (não disponível na estrutura atual)
        
        self.table_emitidos.setItem(r, 9, cell(it.get("natureza")))
        self.table_emitidos.setItem(r,10, cell(self._codigo_uf_to_sigla(it.get("uf") or "")))
        
        # Coluna Base ICMS - ordenação numérica
        base_icms_text = it.get("base_icms") or ""
        base_icms_num = 0.0
        try:
            base_clean = str(base_icms_text).replace("R$", "").replace(".", "").replace(",", ".").strip()
            if base_clean:
                base_icms_num = float(base_clean)
        except Exception:
            pass
        c_base = NumericTableWidgetItem(base_icms_text, base_icms_num)
        c_base.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table_emitidos.setItem(r,11, c_base)
        
        # Coluna Valor ICMS - ordenação numérica
        valor_icms_text = it.get("valor_icms") or ""
        valor_icms_num = 0.0
        try:
            icms_clean = str(valor_icms_text).replace("R$", "").replace(".", "").replace(",", ".").strip()
            if icms_clean:
                valor_icms_num = float(icms_clean)
        except Exception:
            pass
        c_icms = NumericTableWidgetItem(valor_icms_text, valor_icms_num)
        c_icms.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table_emitidos.setItem(r,12, c_icms)
        
        self.table_emitidos.setItem(r,13, cell(it.get("cfop")))
        self.table_emitidos.setItem(r,14, cell(it.get("ncm")))
        self.table_emitidos.setItem(r,15, cell(it.get("ie_tomador")))
        self.table_emitidos.setItem(r,16, cell(it.get("chave")))

    def _fill_table_step(self):
        try:
            total = len(self._table_fill_items)
            if self._table_fill_index >= total:
                # Done
                try:
                    self._table_fill_timer.stop()
                except Exception:
                    pass
                self._table_filling = False
                # Sempre habilita sorting após preenchimento
                try:
                    self.table.setSortingEnabled(True)
                except Exception:
                    pass
                self.set_status(f"{total} registros carregados", 2000)
                return
            start = self._table_fill_index
            end = min(start + self._table_fill_chunk, total)
            for r in range(start, end):
                it = self._table_fill_items[r]
                self._populate_row(r, it)
            self._table_fill_index = end
            # Update status lightly
            try:
                pct = int((end / max(1, total)) * 100)
                self.set_status(f"Montando tabela… {pct}%")
            except Exception:
                pass
        except Exception:
            # On any error, stop to avoid tight loop
            try:
                self._table_fill_timer.stop()
            except Exception:
                pass
            self._table_filling = False

        # Table tweaks
        try:
            self.table.setAlternatingRowColors(True)
            self.table.verticalHeader().setDefaultSectionSize(24)
        except Exception:
            pass

    def _update_window_title(self):
        """Atualiza o título da janela com a versão atual."""
        try:
            version_file = BASE_DIR / "version.txt"
            if version_file.exists():
                version = version_file.read_text(encoding='utf-8').strip()
            else:
                version = "1.0.0"
        except Exception:
            version = "1.0.0"
        
        self.setWindowTitle(f"Busca XML - v{version}")
    
    def _center_window(self):
        """Centraliza a janela na tela."""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QRect
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def _update_search_summary(self):
        """Atualiza resumo de busca em tempo real."""
        from datetime import datetime
        try:
            elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
            cert_info = f"Cert: ...{self._search_stats['last_cert']}" if self._search_stats['last_cert'] else ""
            
            summary = f"🔍 NFes: {self._search_stats['nfes_found']} | CTes: {self._search_stats['ctes_found']}"
            if cert_info:
                summary += f" | {cert_info}"
            summary += f" | {elapsed:.0f}s"
            
            self.search_summary_label.setText(summary)
            # REMOVIDO: QApplication.processEvents() causava reentrância e travamento
        except Exception:
            pass  # Silencioso para evitar recursão
    
    def _get_last_search_status(self):
        """Retorna texto com status da última busca."""
        from datetime import datetime
        try:
            last_search = self.db.get_last_search_time()
            if last_search:
                last_dt = datetime.fromisoformat(last_search)
                now = datetime.now()
                diff_minutes = (now - last_dt).total_seconds() / 60
                
                # Formata tempo decorrido
                if diff_minutes < 60:
                    tempo = f"{diff_minutes:.0f}min"
                elif diff_minutes < 1440:  # menos de 24h
                    horas = diff_minutes / 60
                    tempo = f"{horas:.1f}h"
                else:
                    dias = diff_minutes / 1440
                    tempo = f"{dias:.1f}d"
                
                # Formata hora
                hora = last_dt.strftime("%H:%M")
                return f"Última busca: {hora} (há {tempo})"
            else:
                return "Pronto - Nenhuma busca realizada"
        except Exception:
            return "Pronto"  # Silencioso para evitar recursão
    
    def _load_intervalo_config(self) -> int:
        """Carrega intervalo de busca configurado (em horas). Padrão: 1 hora."""
        try:
            intervalo_minutos = self.db.get_next_search_interval()
            # Converte de minutos para horas
            return max(1, min(23, intervalo_minutos // 60))
        except Exception:
            return 1  # Padrão: 1 hora
    
    def _save_intervalo_config(self, horas: int):
        """Salva intervalo de busca configurado (converte horas para minutos)."""
        try:
            minutos = horas * 60
            self.db.set_next_search_interval(minutos)
            self.set_status(f"Intervalo de busca atualizado: {horas} hora(s)", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar intervalo: {e}")
    
    def _load_consultar_status_config(self) -> bool:
        """Carrega configuração se deve consultar status de protocolo. Padrão: True."""
        try:
            valor = self.db.get_config('consultar_status_protocolo', '1')
            return valor == '1'
        except Exception:
            return True  # Padrão: habilitado
    
    def _save_consultar_status_config(self, state: int):
        """Salva configuração de consulta de status (0=desabilitado, 2=habilitado)."""
        try:
            # Qt.CheckState: 0=Unchecked, 2=Checked
            valor = '1' if state == 2 else '0'
            self.db.set_config('consultar_status_protocolo', valor)
            status_text = "habilitada" if state == 2 else "desabilitada"
            self.set_status(f"Consulta de status {status_text}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar configuração: {e}")

    def _apply_theme(self):
        # Global stylesheet for a clean modern look
        try:
            self.setStyleSheet(
                """
                QWidget { font-size: 11px; }
                QLineEdit, QComboBox { padding: 4px 6px; }
                QPushButton { padding: 4px 10px; }
                QTreeWidget { border: 1px solid #d0d0d0; border-radius: 4px; }
                QTableWidget { border: 1px solid #d0d0d0; border-radius: 4px; gridline-color: #ededed; }
                QHeaderView::section { background: #fafafa; padding: 6px; border: 0px; border-bottom: 1px solid #e0e0e0; font-weight: 600; }
                QStatusBar { background: #f6f6f6; }
                """
            )
            # Slightly larger headers
            hfont = self.table.horizontalHeader().font()
            current_size = hfont.pointSize()
            if current_size > 0:
                hfont.setPointSize(current_size + 1)
            else:
                hfont.setPointSize(10)  # Tamanho padrão se não conseguir obter
            hfont.setBold(True)
            self.table.horizontalHeader().setFont(hfont)
        except Exception:
            pass

    def _filter_certs_tree(self, text: str):
        try:
            text = (text or '').lower().strip()
            for i in range(self.tree_certs.topLevelItemCount()):
                it = self.tree_certs.topLevelItem(i)
                visible = (text in (it.text(0) or '').lower()) if text else True
                it.setHidden(not visible)
        except Exception:
            pass

    def _clear_cert_filter(self):
        try:
            self.cert_filter.clear()
            self._selected_cert_cnpj = None
            # Limpa seleção visual na árvore
            self.tree_certs.clearSelection()
            # Seleciona "Todos"
            if self.tree_certs.topLevelItemCount() > 0:
                todos_item = self.tree_certs.topLevelItem(0)
                todos_item.setSelected(True)
            self.refresh_table()
        except Exception:
            pass

    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        sel = self.table.selectionModel()
        if sel is None:
            return None
        idxs = sel.selectedRows()
        if not idxs:
            return None
        row = idxs[0].row()
        # We need to map back to filtered list order
        flt = self.filtered()
        if 0 <= row < len(flt):
            return flt[row]
        return None

    def _on_table_context_menu(self, pos):
        """Menu de contexto com opções para a nota/CT-e selecionada"""
        # Pega o item clicado
        item_at_pos = self.table.itemAt(pos)
        if not item_at_pos:
            return
        
        row = item_at_pos.row()
        flt = self.filtered()
        if row < 0 or row >= len(flt):
            return
        
        item = flt[row]
        xml_status = (item.get('xml_status') or '').upper()
        
        # Cria menu
        menu = QMenu(self)
        
        # Opção: Ver Detalhes Completos (sempre disponível)
        action_detalhes = menu.addAction("📄 Ver Detalhes Completos")
        
        # Opção: Buscar XML Completo (só para RESUMO)
        menu.addSeparator()
        if xml_status == 'RESUMO':
            action_buscar = menu.addAction("🔍 Buscar XML Completo na SEFAZ")
        else:
            action_buscar = None
        
        # Opção: Eventos (sempre disponível)
        menu.addSeparator()
        action_eventos = menu.addAction("📋 Ver Eventos")
        
        # Mostra menu e pega ação
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == action_detalhes:
            self._mostrar_detalhes_nota(item)
        elif action == action_buscar:
            self._buscar_xml_completo(item)
        elif action == action_eventos:
            self._mostrar_eventos(item)
    
    def _on_table_emitidos_context_menu(self, pos):
        """Menu de contexto para a tabela de notas emitidas pela empresa"""
        # Pega o item clicado
        item_at_pos = self.table_emitidos.itemAt(pos)
        if not item_at_pos:
            return
        
        row = item_at_pos.row()
        flt = self.filtered_emitidos()
        if row < 0 or row >= len(flt):
            return
        
        item = flt[row]
        xml_status = (item.get('xml_status') or '').upper()
        
        # Cria menu
        menu = QMenu(self)
        
        # Opção: Ver Detalhes Completos (sempre disponível)
        action_detalhes = menu.addAction("📄 Ver Detalhes Completos")
        
        # Opção: Buscar XML Completo (só para RESUMO)
        menu.addSeparator()
        if xml_status == 'RESUMO':
            action_buscar = menu.addAction("🔍 Buscar XML Completo na SEFAZ")
        else:
            action_buscar = None
        
        # Opção: Eventos (sempre disponível)
        menu.addSeparator()
        action_eventos = menu.addAction("📋 Ver Eventos")
        
        # Mostra menu e pega ação
        action = menu.exec_(self.table_emitidos.viewport().mapToGlobal(pos))
        
        if action == action_detalhes:
            self._mostrar_detalhes_nota(item)
        elif action == action_buscar:
            self._buscar_xml_completo(item)
        elif action == action_eventos:
            self._mostrar_eventos(item)
    
    def _mostrar_detalhes_nota(self, item: Dict[str, Any]):
        """Exibe uma janela com todos os detalhes da nota fiscal"""
        if not item:
            return
        
        # Cria janela de diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalhes - Nota {item.get('numero', 'N/A')}")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(600)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Área de scroll para o conteúdo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Função helper para adicionar campo
        def add_field(label: str, value: Any, is_header: bool = False):
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(5, 5, 5, 5)
            
            label_widget = QLabel(f"<b>{label}:</b>")
            label_widget.setMinimumWidth(180)
            
            value_str = str(value or "")
            value_widget = QLabel(value_str)
            value_widget.setWordWrap(True)
            value_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            
            if is_header:
                font = value_widget.font()
                font.setPointSize(font.pointSize() + 2)
                font.setBold(True)
                value_widget.setFont(font)
                label_widget.setFont(font)
            
            h_layout.addWidget(label_widget)
            h_layout.addWidget(value_widget, 1)
            
            scroll_layout.addWidget(container)
        
        # Função para adicionar separador
        def add_separator(title: str = ""):
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            scroll_layout.addWidget(line)
            
            if title:
                title_label = QLabel(f"<h3>{title}</h3>")
                scroll_layout.addWidget(title_label)
        
        # === INFORMAÇÕES PRINCIPAIS ===
        add_field("Número da Nota", item.get('numero', 'N/A'), is_header=True)
        add_field("Tipo", item.get('tipo', 'N/A'))
        add_field("Status", item.get('status', 'N/A'))
        add_field("Status XML", item.get('xml_status', 'N/A'))
        
        add_separator("Emissor")
        add_field("Nome do Emitente", item.get('nome_emitente', 'N/A'))
        add_field("CNPJ Emitente", item.get('cnpj_emitente', 'N/A'))
        add_field("UF", self._codigo_uf_to_sigla(item.get('uf', '')))
        
        add_separator("Valores")
        add_field("Valor Total", item.get('valor', 'N/A'))
        add_field("Base ICMS", item.get('base_icms', 'N/A'))
        add_field("Valor ICMS", item.get('valor_icms', 'N/A'))
        
        add_separator("Datas")
        add_field("Data de Emissão", self._format_date_br(item.get('data_emissao', '')))
        add_field("Data de Vencimento", self._format_date_br(item.get('vencimento', '')))
        add_field("Atualizado em", item.get('atualizado_em', 'N/A'))
        
        add_separator("Informações Fiscais")
        add_field("CFOP", item.get('cfop', 'N/A'))
        add_field("NCM", item.get('ncm', 'N/A'))
        add_field("Natureza da Operação", item.get('natureza', 'N/A'))
        add_field("IE Tomador", item.get('ie_tomador', 'N/A'))
        
        add_separator("Informações do Sistema")
        add_field("Informante (CNPJ Consulta)", item.get('informante', 'N/A'))
        add_field("Chave de Acesso", item.get('chave', 'N/A'))
        
        # CNPJ Destinatário (se disponível)
        if item.get('cnpj_destinatario'):
            add_field("CNPJ Destinatário", item.get('cnpj_destinatario', 'N/A'))
        
        # Finaliza scroll
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Botões
        button_box = QWidget()
        button_layout = QHBoxLayout(button_box)
        
        # Botão Copiar Chave
        btn_copy_chave = QPushButton("📋 Copiar Chave")
        btn_copy_chave.clicked.connect(lambda: self._copiar_para_clipboard(item.get('chave', '')))
        button_layout.addWidget(btn_copy_chave)
        
        # Botão Copiar CNPJ
        btn_copy_cnpj = QPushButton("📋 Copiar CNPJ Emitente")
        btn_copy_cnpj.clicked.connect(lambda: self._copiar_para_clipboard(item.get('cnpj_emitente', '')))
        button_layout.addWidget(btn_copy_cnpj)
        
        button_layout.addStretch()
        
        # Botão Fechar
        btn_close = QPushButton("✖ Fechar")
        btn_close.clicked.connect(dialog.accept)
        button_layout.addWidget(btn_close)
        
        layout.addWidget(button_box)
        
        # Exibe o diálogo
        dialog.exec_()
    
    def _copiar_para_clipboard(self, texto: str):
        """Copia texto para a área de transferência"""
        if texto:
            clipboard = QApplication.clipboard()
            clipboard.setText(texto)
            self.set_status(f"✅ Copiado: {texto}", 2000)
    
    def _buscar_xml_completo(self, item: Dict[str, Any]):
        """Busca o XML completo de um resumo na SEFAZ"""
        chave = item.get('chave')
        if not chave or len(chave) != 44:
            QMessageBox.warning(self, "Erro", "Chave de acesso inválida!")
            return
        
        # Determina qual certificado usar
        informante = item.get('informante')
        certs = self.db.load_certificates()
        
        cert_to_use = None
        if informante:
            # Tenta usar o certificado que baixou esse resumo
            for c in certs:
                if c.get('informante') == informante:
                    cert_to_use = c
                    break
        
        if not cert_to_use and certs:
            # Usa o primeiro certificado ativo
            cert_to_use = certs[0]
        
        if not cert_to_use:
            QMessageBox.warning(self, "Erro", "Nenhum certificado disponível!")
            return
        
        # Busca na SEFAZ
        try:
            from nfe_search import consultar_nfe_por_chave
            
            self.set_status(f"Buscando XML completo da chave {chave[:10]}...")
            QApplication.processEvents()
            
            xml_completo = consultar_nfe_por_chave(
                chave=chave,
                certificado_path=cert_to_use.get('caminho'),
                senha=cert_to_use.get('senha'),
                cnpj=cert_to_use.get('cnpj_cpf'),
                cuf=cert_to_use.get('cUF_autor')
            )
            
            if xml_completo:
                # Verifica se é XML completo (com dados da nota) ou apenas protocolo
                xml_lower = xml_completo.lower()
                is_only_protocol = (
                    '<retconssit' in xml_lower and 
                    '<protnfe' in xml_lower and
                    '<nfeproc' not in xml_lower and
                    '<nfe' not in xml_lower.replace('nferesultmsg', '').replace('protnfe', '')
                )
                
                if is_only_protocol:
                    # Apenas protocolo disponível, XML completo não está mais acessível
                    self.set_status("⚠ Apenas protocolo disponível (XML completo não acessível)", 5000)
                    
                    # Remove da interface (deleta do banco)
                    self.db.deletar_nota_detalhada(chave)
                    self.refresh_table()
                    
                    QMessageBox.warning(
                        self, 
                        "XML Completo Não Disponível", 
                        f"A SEFAZ retornou apenas o protocolo de autorização.\n\n"
                        f"O XML completo da NFe não está mais disponível para consulta.\n\n"
                        f"Possíveis causas:\n"
                        f"• NFe muito antiga (fora do período de disponibilidade)\n"
                        f"• Nota cancelada\n"
                        f"• Acesso negado\n\n"
                        f"O resumo foi removido da listagem."
                    )
                else:
                    # XML completo obtido com sucesso
                    from nfe_search import salvar_xml_por_certificado
                    salvar_xml_por_certificado(xml_completo, informante or cert_to_use.get('cnpj_cpf'))
                    
                    # Atualiza no banco
                    from modules.xml_parser import XMLParser
                    parser = XMLParser()
                    
                    nota = item.copy()
                    nota['xml_status'] = 'COMPLETO'
                    self.db.salvar_nota_detalhada(nota)
                    
                    self.set_status(f"✓ XML completo baixado e salvo!", 3000)
                    self.refresh_table()
                    
                    QMessageBox.information(
                        self, 
                        "Sucesso", 
                        f"XML completo da nota {item.get('numero')} baixado com sucesso!\n\n"
                        f"O registro foi atualizado de 'Resumo' para 'Completo'."
                    )
            else:
                self.set_status("Erro ao buscar XML completo", 3000)
                QMessageBox.warning(
                    self, 
                    "Erro", 
                    "Não foi possível obter o XML completo da SEFAZ.\n\n"
                    "Possíveis causas:\n"
                    "- Nota não encontrada\n"
                    "- Certificado sem permissão de acesso\n"
                    "- Problema de conexão com SEFAZ"
                )
        except Exception as e:
            self.set_status(f"Erro: {str(e)}", 5000)
            QMessageBox.critical(self, "Erro", f"Erro ao buscar XML completo:\n\n{str(e)}")
    
    def _mostrar_eventos(self, item: Dict[str, Any]):
        """Mostra os eventos vinculados a uma NFe/CT-e"""
        chave = item.get('chave', '')
        if not chave or len(chave) != 44:
            QMessageBox.warning(self, "Eventos", "Chave de acesso inválida!")
            return
        
        informante = item.get('informante', '')
        tipo = (item.get('tipo') or 'NFe').strip().upper().replace('-', '')
        numero = item.get('numero', chave[:10])
        
        # Mostra indicador de busca
        self.set_status("🔍 Procurando eventos...")
        QApplication.processEvents()  # Atualiza UI
        
        # Busca eventos nos XMLs locais
        eventos_encontrados = []
        
        try:
            # Procura em TODAS as pastas de eventos (não só do informante)
            # porque eventos podem estar na pasta do destinatário
            xmls_root = DATA_DIR / "xmls"
            if xmls_root.exists():
                # Busca em todas as pastas de eventos de todos os CNPJs
                for eventos_folder in xmls_root.rglob("Eventos"):
                    for xml_file in eventos_folder.glob("*.xml"):
                        try:
                            xml_content = xml_file.read_text(encoding='utf-8')
                            # Verifica se a chave está no XML
                            if chave in xml_content:
                                # Extrai informações do evento
                                from lxml import etree
                                tree = etree.fromstring(xml_content.encode('utf-8'))
                                
                                # Tenta diferentes estruturas de evento
                                ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                                
                                # Tipo de evento
                                tp_evento = tree.findtext('.//nfe:tpEvento', namespaces=ns) or 'N/A'
                                # Descrição do evento
                                desc_evento = tree.findtext('.//nfe:descEvento', namespaces=ns) or tree.findtext('.//nfe:xEvento', namespaces=ns) or 'N/A'
                                # Data/hora do evento
                                dh_evento = tree.findtext('.//nfe:dhEvento', namespaces=ns) or tree.findtext('.//nfe:dhRegEvento', namespaces=ns) or 'N/A'
                                # Status
                                cstat = tree.findtext('.//nfe:cStat', namespaces=ns) or 'N/A'
                                xmotivo = tree.findtext('.//nfe:xMotivo', namespaces=ns) or 'N/A'
                                
                                # Mapeia tipo de evento para descrição amigável
                                tipos_eventos = {
                                    '110111': '❌ Cancelamento',
                                    '110110': '✏️ Carta de Correção',
                                    '210200': '📬 Confirmação da Operação',
                                    '210210': '❓ Ciência da Operação',
                                    '210220': '⛔ Desconhecimento da Operação',
                                    '210240': '🚫 Operação não Realizada',
                                    '110140': '🔒 EPEC (Contingência)',
                                }
                                
                                evento_desc = tipos_eventos.get(tp_evento, f"Evento {tp_evento}")
                                
                                eventos_encontrados.append({
                                    'arquivo': xml_file.name,
                                    'tipo': evento_desc,
                                    'descricao': desc_evento,
                                    'data': dh_evento[:19] if len(dh_evento) >= 19 else dh_evento,
                                    'status': f"{cstat} - {xmotivo}",
                                    'caminho': str(xml_file)
                                })
                        except Exception:
                            continue
        except Exception as e:
            self.set_status("❌ Erro ao buscar eventos", 3000)
            QMessageBox.warning(self, "Erro", f"Erro ao buscar eventos:\n{e}")
            return
        finally:
            # Limpa status após busca
            if eventos_encontrados:
                self.set_status(f"✅ {len(eventos_encontrados)} evento(s) encontrado(s)", 2000)
            else:
                self.set_status("ℹ️ Nenhum evento encontrado", 2000)
        
        # Cria dialog para mostrar eventos
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Eventos - {tipo} {numero}")
        dialog.resize(800, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Informações do documento
        info_label = QLabel(f"<b>{tipo} Nº {numero}</b><br>Chave: {chave}")
        layout.addWidget(info_label)
        
        if not eventos_encontrados:
            no_eventos_label = QLabel("ℹ️ Nenhum evento encontrado para este documento.")
            no_eventos_label.setStyleSheet("padding: 20px; color: #666;")
            layout.addWidget(no_eventos_label)
        else:
            # Tabela de eventos
            eventos_table = QTableWidget()
            eventos_table.setColumnCount(4)
            eventos_table.setHorizontalHeaderLabels(["Tipo", "Descrição", "Data/Hora", "Status"])
            eventos_table.setRowCount(len(eventos_encontrados))
            eventos_table.setEditTriggers(QTableWidget.NoEditTriggers)
            eventos_table.setSelectionBehavior(QTableWidget.SelectRows)
            
            for i, evento in enumerate(eventos_encontrados):
                eventos_table.setItem(i, 0, QTableWidgetItem(evento['tipo']))
                eventos_table.setItem(i, 1, QTableWidgetItem(evento['descricao']))
                eventos_table.setItem(i, 2, QTableWidgetItem(evento['data']))
                eventos_table.setItem(i, 3, QTableWidgetItem(evento['status']))
            
            eventos_table.resizeColumnsToContents()
            eventos_table.horizontalHeader().setStretchLastSection(True)
            
            layout.addWidget(eventos_table)
            
            # Botão para abrir pasta de eventos
            btn_abrir_pasta = QPushButton("📁 Abrir pasta de eventos")
            btn_abrir_pasta.clicked.connect(lambda: self._abrir_pasta_eventos(informante))
            layout.addWidget(btn_abrir_pasta)
        
        # Botão fechar
        btn_fechar = QPushButton("Fechar")
        btn_fechar.clicked.connect(dialog.close)
        layout.addWidget(btn_fechar)
        
        dialog.exec_()
    
    def _abrir_pasta_eventos(self, informante: str):
        """Abre a pasta de eventos do informante no Windows Explorer"""
        try:
            eventos_path = DATA_DIR / "xmls" / informante
            if eventos_path.exists():
                if sys.platform == "win32":
                    os.startfile(str(eventos_path))  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", str(eventos_path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao abrir pasta: {e}")
    
    def _build_pdf_cache_async(self):
        """Constrói cache de PDFs em background para abertura rápida"""
        if self._cache_building:
            return
        
        self._cache_building = True
        
        class CacheBuilder(QThread):
            cache_ready = pyqtSignal(dict)  # {chave: pdf_path}
            
            def __init__(self, notes, base_dir):
                super().__init__()
                self.notes = notes
                self.base_dir = base_dir
            
            def run(self):
                cache = {}
                try:
                    for note in self.notes:
                        chave = note.get('chave', '')
                        informante = note.get('informante', '')
                        data_emissao = (note.get('data_emissao') or '')[:10]
                        tipo = (note.get('tipo') or 'NFe').strip().upper().replace('-', '')
                        
                        if not (chave and informante and data_emissao):
                            continue
                        
                        # Extrai ano-mês
                        try:
                            year_month = data_emissao[:7] if len(data_emissao) >= 7 else None
                            if year_month:
                                # Verifica caminho direto (com tipo)
                                pdf_path = DATA_DIR / "xmls" / informante / tipo / year_month / f"{chave}.pdf"
                                if pdf_path.exists():
                                    cache[chave] = str(pdf_path)
                                    continue
                                
                                # Verifica caminho antigo (sem tipo)
                                pdf_path = DATA_DIR / "xmls" / informante / year_month / f"{chave}.pdf"
                                if pdf_path.exists():
                                    cache[chave] = str(pdf_path)
                                    continue
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[DEBUG] Erro ao construir cache de PDFs: {e}")
                
                self.cache_ready.emit(cache)
        
        def on_cache_ready(cache: dict):
            self._pdf_cache = cache
            self._cache_building = False
            self._cache_worker = None
            print(f"[DEBUG] Cache de PDFs construído: {len(cache)} arquivos indexados")
        
        self._cache_worker = CacheBuilder(self.notes, BASE_DIR)
        self._cache_worker.cache_ready.connect(on_cache_ready)
        self._cache_worker.start()

    def _on_table_double_clicked(self, row: int, col: int):
        """Abre PDF (verifica existência primeiro, só gera se necessário) - OTIMIZADO"""
        import time
        start_time = time.time()
        print(f"\n[DEBUG PDF] ========== DUPLO CLIQUE ===========")
        print(f"[DEBUG PDF] Linha: {row}, Coluna: {col}")
        
        # Obtém o item pela linha clicada da lista filtrada
        flt = self.filtered()
        item = flt[row] if 0 <= row < len(flt) else None
        if not item:
            print(f"[DEBUG PDF] ❌ Item não encontrado")
            return
        
        chave = item.get('chave', '')
        if not chave:
            print(f"[DEBUG PDF] ❌ Chave vazia")
            return
        
        print(f"[DEBUG PDF] Chave: {chave}")
        print(f"[DEBUG PDF] Informante: {item.get('informante', 'N/A')}")
        print(f"[DEBUG PDF] Tipo: {item.get('tipo', 'N/A')}")
        
        # OTIMIZAÇÃO 1: Verifica cache primeiro (INSTANTÂNEO)
        print(f"[DEBUG PDF] Etapa 1: Verificando cache...")
        cache_start = time.time()
        if chave in self._pdf_cache:
            print(f"[DEBUG PDF] ✅ Encontrado no cache: {self._pdf_cache[chave]}")
            cached_pdf = Path(self._pdf_cache[chave])
            if cached_pdf.exists():
                try:
                    print(f"[DEBUG PDF] ⚡ Cache hit! Tempo: {time.time() - cache_start:.3f}s")
                    pdf_str = str(cached_pdf.absolute())
                    if sys.platform == "win32":
                        # Abre PDF com visualizador padrão do Windows (evita abrir interface se PDF estiver associado incorretamente)
                        subprocess.Popen(["cmd", "/c", "start", "", pdf_str], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)  # type: ignore[attr-defined]
                    else:
                        subprocess.Popen(["xdg-open", pdf_str])
                    total_time = time.time() - start_time
                    print(f"[DEBUG PDF] ✅ PDF aberto (cache) - Tempo total: {total_time:.3f}s")
                    self.set_status("✅ PDF aberto (cache)", 1000)
                    return
                except Exception as e:
                    print(f"[DEBUG PDF] ❌ Erro ao abrir PDF do cache: {e}")
                    QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
                    return
            else:
                print(f"[DEBUG PDF] ⚠️ PDF no cache não existe mais no disco")
        else:
            print(f"[DEBUG PDF] Cache miss (tamanho do cache: {len(self._pdf_cache)})")
        
        print(f"[DEBUG PDF] Etapa 1 concluída em {time.time() - cache_start:.3f}s")
        
        # OTIMIZAÇÃO 2: Busca direta baseada na data de emissão (MUITO MAIS RÁPIDO)
        print(f"[DEBUG PDF] Etapa 2: Busca direta na pasta...")
        direct_start = time.time()
        informante = item.get('informante', '')
        tipo = (item.get('tipo') or 'NFe').strip().upper().replace('-', '')
        data_emissao = (item.get('data_emissao') or '')[:10]
        
        print(f"[DEBUG PDF] Informante: {informante}")
        print(f"[DEBUG PDF] Tipo: {tipo}")
        print(f"[DEBUG PDF] Data emissão: {data_emissao}")
        
        pdf_path = None
        
        if chave and informante and data_emissao:
            # Extrai ano-mês da data de emissão
            try:
                year_month = data_emissao[:7] if len(data_emissao) >= 7 else None
                print(f"[DEBUG PDF] Ano-mês extraído: {year_month}")
                if year_month:
                    # Busca direta na pasta específica do mês (SEM recursão)
                    specific_path = DATA_DIR / "xmls" / informante / tipo / year_month / f"{chave}.pdf"
                    print(f"[DEBUG PDF] Buscando em: {specific_path}")
                    if specific_path.exists():
                        print(f"[DEBUG PDF] ✅ Encontrado na busca direta!")
                        pdf_path = specific_path
                    else:
                        # Tenta sem o tipo (estrutura antiga)
                        old_path = DATA_DIR / "xmls" / informante / year_month / f"{chave}.pdf"
                        print(f"[DEBUG PDF] Tentando estrutura antiga: {old_path}")
                        if old_path.exists():
                            print(f"[DEBUG PDF] ✅ Encontrado na estrutura antiga!")
                            pdf_path = old_path
                        else:
                            print(f"[DEBUG PDF] ❌ Não encontrado na busca direta")
            except Exception as e:
                print(f"[DEBUG PDF] ❌ Erro na busca direta: {e}")
                pass
        
        print(f"[DEBUG PDF] Etapa 2 concluída em {time.time() - direct_start:.3f}s")
        
        # OTIMIZAÇÃO 3: Apenas se não encontrou acima, busca em toda estrutura (LENTO - último recurso)
        print(f"[DEBUG PDF] Etapa 3: Busca recursiva (se necessário)...")
        recursive_start = time.time()
        if not pdf_path and chave and informante:
            print(f"[DEBUG PDF] PDF não encontrado na busca direta, iniciando busca recursiva...")
            xmls_root = DATA_DIR / "xmls" / informante
            print(f"[DEBUG PDF] Pasta raiz: {xmls_root}")
            if xmls_root.exists():
                # Lista todas as pastas de ano-mês (diretamente na raiz E em subpastas de tipo)
                folders = list(sorted(xmls_root.glob("20*"), reverse=True))  # Busca direta: 2025-05/, 2025-06/
                folders.extend(sorted(xmls_root.glob("*/20*"), reverse=True))  # Busca com tipo: NFE/2025-05/, CTe/2025-06/
                print(f"[DEBUG PDF] Encontradas {len(folders)} pastas para varrer")
                if folders:
                    print(f"[DEBUG PDF] Pastas encontradas: {[f.name for f in folders[:10]]}")
                for idx, year_month_folder in enumerate(folders):
                    potential_pdf = year_month_folder / f"{chave}.pdf"
                    print(f"[DEBUG PDF] Verificando [{idx+1}/{len(folders)}]: {year_month_folder}")
                    if potential_pdf.exists():
                        print(f"[DEBUG PDF] ✅ Encontrado na pasta {idx+1}/{len(folders)}: {year_month_folder}")
                        pdf_path = potential_pdf
                        break
                    else:
                        print(f"[DEBUG PDF] ❌ Não encontrado em: {potential_pdf}")
            else:
                print(f"[DEBUG PDF] Pasta raiz não existe: {xmls_root}")
        else:
            if pdf_path:
                print(f"[DEBUG PDF] PDF já encontrado, pulando busca recursiva")
            else:
                print(f"[DEBUG PDF] Dados insuficientes para busca recursiva (chave ou informante faltando)")
        
        print(f"[DEBUG PDF] Etapa 3 concluída em {time.time() - recursive_start:.3f}s")
        
        # Etapa 3.5: Se ainda não encontrou, busca pelo XML/PDF com número da nota (OTIMIZADO - 1000x mais rápido)
        if not pdf_path and chave:
            print(f"[DEBUG PDF] Etapa 3.5: Busca otimizada por nome/conteúdo...")
            xml_search_start = time.time()
            try:
                # Extrai número da nota da chave (para buscar por padrão número-nome)
                # Exemplo chave: 31251212260426000759570050000343921003100920
                # Posições 25-34 = número da nota (00034392)
                numero_nf = chave[25:34] if len(chave) >= 34 else None
                numero_nf_sem_zeros = numero_nf.lstrip('0') if numero_nf else None
                
                print(f"[DEBUG PDF] Número da NF extraído: {numero_nf_sem_zeros}")
                
                xmls_root = DATA_DIR / "xmls"
                if xmls_root.exists():
                    xml_found = None
                    pdf_found = None
                    
                    # OTIMIZAÇÃO: Busca 1 - Por padrão de nome (número-*) - MUITO MAIS RÁPIDO
                    if informante and numero_nf_sem_zeros:
                        informante_folder = xmls_root / informante
                        if informante_folder.exists():
                            # Busca PDF primeiro (se já existe, não precisa do XML)
                            print(f"[DEBUG PDF] Buscando PDF por padrão: {numero_nf_sem_zeros}-*.pdf")
                            for pdf_file in informante_folder.rglob(f"{numero_nf_sem_zeros}-*.pdf"):
                                if 'backup' not in str(pdf_file).lower():
                                    pdf_found = pdf_file
                                    print(f"[DEBUG PDF] ⚡ PDF encontrado por nome: {pdf_file}")
                                    break
                            
                            # Se não achou PDF, busca XML por padrão
                            if not pdf_found:
                                print(f"[DEBUG PDF] Buscando XML por padrão: {numero_nf_sem_zeros}-*.xml")
                                for xml_file in informante_folder.rglob(f"{numero_nf_sem_zeros}-*.xml"):
                                    if 'backup' not in str(xml_file).lower():
                                        xml_found = xml_file
                                        print(f"[DEBUG PDF] ⚡ XML encontrado por nome: {xml_file}")
                                        break
                    
                    # Busca 2: Por chave no nome do arquivo (mais rápido que ler conteúdo)
                    if not xml_found and not pdf_found and informante:
                        informante_folder = xmls_root / informante
                        if informante_folder.exists():
                            print(f"[DEBUG PDF] Buscando por chave no nome do arquivo...")
                            for xml_file in informante_folder.rglob("*.xml"):
                                if chave in xml_file.name and 'backup' not in str(xml_file).lower():
                                    xml_found = xml_file
                                    print(f"[DEBUG PDF] ✅ XML encontrado por chave no nome: {xml_file}")
                                    break
                    
                    # Busca 3: Em Debug de notas (por padrão de nome)
                    if not xml_found and not pdf_found and numero_nf_sem_zeros:
                        debug_folder = xmls_root / "Debug de notas"
                        if debug_folder.exists():
                            print(f"[DEBUG PDF] Buscando em Debug de notas por padrão: {numero_nf_sem_zeros}-*")
                            for pdf_file in debug_folder.glob(f"{numero_nf_sem_zeros}-*.pdf"):
                                pdf_found = pdf_file
                                print(f"[DEBUG PDF] ⚡ PDF encontrado em Debug: {pdf_file}")
                                break
                            if not pdf_found:
                                for xml_file in debug_folder.glob(f"{numero_nf_sem_zeros}-*.xml"):
                                    xml_found = xml_file
                                    print(f"[DEBUG PDF] ⚡ XML encontrado em Debug: {xml_file}")
                                    break
                    
                    # Busca 4: ÚLTIMO RECURSO - Lê conteúdo dos XMLs (LENTO - só se não achou por nome)
                    if not xml_found and not pdf_found and informante:
                        print(f"[DEBUG PDF] ⚠️ Busca por conteúdo (lenta) - último recurso...")
                        informante_folder = xmls_root / informante
                        if informante_folder.exists():
                            for xml_file in informante_folder.rglob("*.xml"):
                                try:
                                    if 'backup' in str(xml_file).lower():
                                        continue
                                    if chave in xml_file.read_text(encoding='utf-8', errors='ignore'):
                                        xml_found = xml_file
                                        print(f"[DEBUG PDF] ✅ XML encontrado por conteúdo: {xml_file}")
                                        break
                                except:
                                    continue
                    
                    # Se encontrou PDF diretamente, usa ele
                    if pdf_found:
                        pdf_path = pdf_found
                    # Se encontrou XML, verifica se tem PDF
                    elif xml_found:
                        pdf_candidate = xml_found.with_suffix('.pdf')
                        if pdf_candidate.exists():
                            print(f"[DEBUG PDF] ✅ PDF encontrado via XML: {pdf_candidate}")
                            pdf_path = pdf_candidate
                        else:
                            print(f"[DEBUG PDF] ℹ️ PDF não existe ainda, será gerado em: {pdf_candidate}")
            except Exception as e:
                print(f"[DEBUG PDF] Erro na busca: {e}")
                import traceback
                traceback.print_exc()
            print(f"[DEBUG PDF] Etapa 3.5 concluída em {time.time() - xml_search_start:.3f}s")
        
        # Se PDF existe, abre imediatamente e adiciona ao cache
        print(f"[DEBUG PDF] Etapa 4: Abertura do PDF...")
        open_start = time.time()
        if pdf_path and pdf_path.exists():
            print(f"[DEBUG PDF] Abrindo PDF: {pdf_path}")
            try:
                # Adiciona ao cache para próximas aberturas
                self._pdf_cache[chave] = str(pdf_path)
                print(f"[DEBUG PDF] PDF adicionado ao cache (tamanho: {len(self._pdf_cache)})")
                
                pdf_str = str(pdf_path.absolute())
                if sys.platform == "win32":
                    # Abre PDF com visualizador padrão do Windows (evita abrir interface se PDF estiver associado incorretamente)
                    subprocess.Popen(["cmd", "/c", "start", "", pdf_str], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", pdf_str])
                print(f"[DEBUG PDF] Etapa 4 concluída em {time.time() - open_start:.3f}s")
                total_time = time.time() - start_time
                print(f"[DEBUG PDF] ✅ PDF aberto com sucesso - Tempo total: {total_time:.3f}s\n")
                self.set_status("✅ PDF aberto", 1000)
                return
            except Exception as e:
                print(f"[DEBUG PDF] ❌ Erro ao abrir PDF: {e}")
                QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
                return
        
        # Se não tem PDF, verifica se tem XML antes de gerar
        print(f"[DEBUG PDF] Etapa 5: Verificando XML antes de gerar PDF...")
        xml_check_start = time.time()
        
        # Busca o XML localmente primeiro
        xml_text = resolve_xml_text(item)
        if not xml_text:
            print(f"[DEBUG PDF] ❌ XML não encontrado localmente")
            QMessageBox.warning(
                self, 
                "XML não encontrado", 
                f"Não foi possível encontrar o XML para a chave {chave}.\n\n"
                "O PDF só pode ser gerado se o XML estiver disponível."
            )
            return
        
        print(f"[DEBUG PDF] ✅ XML encontrado, iniciando geração de PDF...")
        print(f"[DEBUG PDF] Etapa 5 concluída em {time.time() - xml_check_start:.3f}s")
        
        # Tem XML, pode gerar PDF (LENTO) - executa em thread separada
        print(f"[DEBUG PDF] Etapa 6: Geração de PDF necessária...")
        generation_start = time.time()
        self.set_status("⏳ Gerando PDF... Por favor aguarde...")
        QApplication.processEvents()
        
        # Cria worker thread para não travar a interface
        print(f"[DEBUG PDF] Criando worker thread para geração assíncrona...")
        self._process_pdf_async(item)
        print(f"[DEBUG PDF] Worker criado - aguardando conclusão em background")
        print(f"[DEBUG PDF] ========================================\n")
    
    def _on_table_emitidos_double_clicked(self, row: int, col: int):
        """Abre PDF da tabela de notas emitidas (mesma lógica que _on_table_double_clicked)"""
        import time
        start_time = time.time()
        
        print(f"\n[DEBUG PDF EMITIDOS] ========== DUPLO CLIQUE ===========")
        
        # Obtém o item pela linha clicada da lista filtrada de emitidos
        flt = self.filtered_emitidos()
        item = flt[row] if 0 <= row < len(flt) else None
        if not item:
            print(f"[DEBUG PDF EMITIDOS] ❌ Item não encontrado na linha {row}")
            return
        
        chave = item.get('chave', '')
        if not chave:
            print(f"[DEBUG PDF EMITIDOS] ❌ Chave não encontrada no item")
            return
        
        print(f"[DEBUG PDF EMITIDOS] Chave: {chave}")
        print(f"[DEBUG PDF EMITIDOS] Informante: {item.get('informante', 'N/A')}")
        print(f"[DEBUG PDF EMITIDOS] Tipo: {item.get('tipo', 'N/A')}")
        
        # OTIMIZAÇÃO 1: Verifica cache primeiro (INSTANTÂNEO)
        print(f"[DEBUG PDF EMITIDOS] Etapa 1: Verificando cache...")
        cache_start = time.time()
        if chave in self._pdf_cache:
            print(f"[DEBUG PDF EMITIDOS] ✅ Encontrado no cache: {self._pdf_cache[chave]}")
            cached_pdf = Path(self._pdf_cache[chave])
            if cached_pdf.exists():
                try:
                    print(f"[DEBUG PDF EMITIDOS] ⚡ Cache hit! Tempo: {time.time() - cache_start:.3f}s")
                    pdf_str = str(cached_pdf.absolute())
                    if sys.platform == "win32":
                        # Abre PDF com visualizador padrão do Windows (evita abrir interface se PDF estiver associado incorretamente)
                        subprocess.Popen(["cmd", "/c", "start", "", pdf_str], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)  # type: ignore[attr-defined]
                    else:
                        subprocess.Popen(["xdg-open", pdf_str])
                    total_time = time.time() - start_time
                    print(f"[DEBUG PDF EMITIDOS] ✅ PDF aberto (cache) - Tempo total: {total_time:.3f}s")
                    self.set_status("✅ PDF aberto (cache)", 1000)
                    return
                except Exception as e:
                    print(f"[DEBUG PDF EMITIDOS] ❌ Erro ao abrir PDF do cache: {e}")
                    QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
                    return
            else:
                print(f"[DEBUG PDF EMITIDOS] ⚠️ PDF no cache não existe mais no disco")
        else:
            print(f"[DEBUG PDF EMITIDOS] Cache miss (tamanho do cache: {len(self._pdf_cache)})")
        
        print(f"[DEBUG PDF EMITIDOS] Etapa 1 concluída em {time.time() - cache_start:.3f}s")
        
        # OTIMIZAÇÃO 2: Busca direta baseada na data de emissão (MUITO MAIS RÁPIDO)
        print(f"[DEBUG PDF EMITIDOS] Etapa 2: Busca direta na pasta...")
        direct_start = time.time()
        # Para notas emitidas, o cnpj_emitente é da empresa (quem emitiu)
        # e o informante é quem recebeu (destinatário)
        # O XML está salvo pelo informante (quem baixou)
        informante = item.get('informante', '')
        tipo = (item.get('tipo') or 'NFe').strip().upper().replace('-', '')
        data_emissao = (item.get('data_emissao') or '')[:10]
        
        print(f"[DEBUG PDF EMITIDOS] Informante: {informante}")
        print(f"[DEBUG PDF EMITIDOS] Tipo: {tipo}")
        print(f"[DEBUG PDF EMITIDOS] Data emissão: {data_emissao}")
        
        pdf_path = None
        
        if chave and informante and data_emissao:
            # Extrai ano-mês da data de emissão
            try:
                year_month = data_emissao[:7] if len(data_emissao) >= 7 else None
                print(f"[DEBUG PDF EMITIDOS] Ano-mês extraído: {year_month}")
                if year_month:
                    # Busca direta na pasta específica do mês (SEM recursão)
                    specific_path = DATA_DIR / "xmls" / informante / tipo / year_month / f"{chave}.pdf"
                    print(f"[DEBUG PDF EMITIDOS] Buscando em: {specific_path}")
                    if specific_path.exists():
                        print(f"[DEBUG PDF EMITIDOS] ✅ Encontrado na busca direta!")
                        pdf_path = specific_path
                    else:
                        # Tenta sem o tipo (estrutura antiga)
                        old_path = DATA_DIR / "xmls" / informante / year_month / f"{chave}.pdf"
                        print(f"[DEBUG PDF EMITIDOS] Tentando estrutura antiga: {old_path}")
                        if old_path.exists():
                            print(f"[DEBUG PDF EMITIDOS] ✅ Encontrado na estrutura antiga!")
                            pdf_path = old_path
                        else:
                            print(f"[DEBUG PDF EMITIDOS] ❌ Não encontrado na busca direta")
            except Exception as e:
                print(f"[DEBUG PDF EMITIDOS] ❌ Erro na busca direta: {e}")
                pass
        
        print(f"[DEBUG PDF EMITIDOS] Etapa 2 concluída em {time.time() - direct_start:.3f}s")
        
        # OTIMIZAÇÃO 3: Apenas se não encontrou acima, busca em toda estrutura (LENTO - último recurso)
        print(f"[DEBUG PDF EMITIDOS] Etapa 3: Busca recursiva (se necessário)...")
        recursive_start = time.time()
        if not pdf_path and chave and informante:
            print(f"[DEBUG PDF EMITIDOS] PDF não encontrado na busca direta, iniciando busca recursiva...")
            xmls_root = DATA_DIR / "xmls" / informante
            print(f"[DEBUG PDF EMITIDOS] Pasta raiz: {xmls_root}")
            if xmls_root.exists():
                # Lista todas as pastas de ano-mês (diretamente na raiz E em subpastas de tipo)
                folders = list(sorted(xmls_root.glob("20*"), reverse=True))  # Busca direta: 2025-05/, 2025-06/
                folders.extend(sorted(xmls_root.glob("*/20*"), reverse=True))  # Busca com tipo: NFE/2025-05/, CTe/2025-06/
                print(f"[DEBUG PDF EMITIDOS] Encontradas {len(folders)} pastas para varrer")
                if folders:
                    print(f"[DEBUG PDF EMITIDOS] Pastas encontradas: {[f.name for f in folders[:10]]}")
                for idx, year_month_folder in enumerate(folders):
                    potential_pdf = year_month_folder / f"{chave}.pdf"
                    print(f"[DEBUG PDF EMITIDOS] Verificando [{idx+1}/{len(folders)}]: {year_month_folder}")
                    if potential_pdf.exists():
                        print(f"[DEBUG PDF EMITIDOS] ✅ Encontrado na pasta {idx+1}/{len(folders)}: {year_month_folder}")
                        pdf_path = potential_pdf
                        break
                    else:
                        print(f"[DEBUG PDF EMITIDOS] ❌ Não encontrado em: {potential_pdf}")
            else:
                print(f"[DEBUG PDF EMITIDOS] Pasta raiz não existe: {xmls_root}")
        else:
            if pdf_path:
                print(f"[DEBUG PDF EMITIDOS] PDF já encontrado, pulando busca recursiva")
            else:
                print(f"[DEBUG PDF EMITIDOS] Dados insuficientes para busca recursiva (chave ou informante faltando)")
        
        print(f"[DEBUG PDF EMITIDOS] Etapa 3 concluída em {time.time() - recursive_start:.3f}s")
        
        # Etapa 3.5: Se ainda não encontrou, busca otimizada por nome/conteúdo (1000x mais rápido)
        if not pdf_path and chave and informante:
            print(f"[DEBUG PDF EMITIDOS] Etapa 3.5: Busca otimizada por nome/conteúdo...")
            xml_search_start = time.time()
            try:
                # Extrai número da nota da chave
                numero_nf = chave[25:34] if len(chave) >= 34 else None
                numero_nf_sem_zeros = numero_nf.lstrip('0') if numero_nf else None
                
                print(f"[DEBUG PDF EMITIDOS] Número da NF extraído: {numero_nf_sem_zeros}")
                
                xmls_root = DATA_DIR / "xmls" / informante
                if xmls_root.exists():
                    xml_found = None
                    pdf_found = None
                    
                    # OTIMIZAÇÃO: Busca 1 - Por padrão de nome (número-*) - MUITO MAIS RÁPIDO
                    if numero_nf_sem_zeros:
                        # Busca PDF primeiro
                        print(f"[DEBUG PDF EMITIDOS] Buscando PDF por padrão: {numero_nf_sem_zeros}-*.pdf")
                        for pdf_file in xmls_root.rglob(f"{numero_nf_sem_zeros}-*.pdf"):
                            if 'backup' not in str(pdf_file).lower():
                                pdf_found = pdf_file
                                print(f"[DEBUG PDF EMITIDOS] ⚡ PDF encontrado por nome: {pdf_file}")
                                break
                        
                        # Se não achou PDF, busca XML
                        if not pdf_found:
                            print(f"[DEBUG PDF EMITIDOS] Buscando XML por padrão: {numero_nf_sem_zeros}-*.xml")
                            for xml_file in xmls_root.rglob(f"{numero_nf_sem_zeros}-*.xml"):
                                if 'backup' not in str(xml_file).lower():
                                    xml_found = xml_file
                                    print(f"[DEBUG PDF EMITIDOS] ⚡ XML encontrado por nome: {xml_file}")
                                    break
                    
                    # Busca 2: Por chave no nome do arquivo
                    if not xml_found and not pdf_found:
                        print(f"[DEBUG PDF EMITIDOS] Buscando por chave no nome...")
                        for xml_file in xmls_root.rglob("*.xml"):
                            if chave in xml_file.name and 'backup' not in str(xml_file).lower():
                                xml_found = xml_file
                                print(f"[DEBUG PDF EMITIDOS] ✅ XML encontrado por chave no nome: {xml_file}")
                                break
                    
                    # Busca 3: ÚLTIMO RECURSO - Lê conteúdo (LENTO)
                    if not xml_found and not pdf_found:
                        print(f"[DEBUG PDF EMITIDOS] ⚠️ Busca por conteúdo (lenta) - último recurso...")
                        for xml_file in xmls_root.rglob("*.xml"):
                            try:
                                if 'backup' in str(xml_file).lower():
                                    continue
                                if chave in xml_file.read_text(encoding='utf-8', errors='ignore'):
                                    xml_found = xml_file
                                    print(f"[DEBUG PDF EMITIDOS] ✅ XML encontrado por conteúdo: {xml_file}")
                                    break
                            except:
                                continue
                    
                    # Se encontrou PDF diretamente, usa ele
                    if pdf_found:
                        pdf_path = pdf_found
                    # Se encontrou XML, verifica se tem PDF
                    elif xml_found:
                        pdf_candidate = xml_found.with_suffix('.pdf')
                        if pdf_candidate.exists():
                            print(f"[DEBUG PDF EMITIDOS] ✅ PDF encontrado via XML: {pdf_candidate}")
                            pdf_path = pdf_candidate
                        else:
                            print(f"[DEBUG PDF EMITIDOS] ℹ️ PDF não existe ainda, será gerado em: {pdf_candidate}")
            except Exception as e:
                print(f"[DEBUG PDF EMITIDOS] Erro na busca: {e}")
                import traceback
                traceback.print_exc()
            print(f"[DEBUG PDF EMITIDOS] Etapa 3.5 concluída em {time.time() - xml_search_start:.3f}s")
        
        # Se PDF existe, abre imediatamente e adiciona ao cache
        print(f"[DEBUG PDF EMITIDOS] Etapa 4: Abertura do PDF...")
        open_start = time.time()
        if pdf_path and pdf_path.exists():
            print(f"[DEBUG PDF EMITIDOS] Abrindo PDF: {pdf_path}")
            try:
                # Adiciona ao cache para próximas aberturas
                self._pdf_cache[chave] = str(pdf_path)
                print(f"[DEBUG PDF EMITIDOS] PDF adicionado ao cache (tamanho: {len(self._pdf_cache)})")
                
                pdf_str = str(pdf_path.absolute())
                if sys.platform == "win32":
                    # Abre PDF com visualizador padrão do Windows (evita abrir interface se PDF estiver associado incorretamente)
                    subprocess.Popen(["cmd", "/c", "start", "", pdf_str], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", pdf_str])
                print(f"[DEBUG PDF EMITIDOS] Etapa 4 concluída em {time.time() - open_start:.3f}s")
                total_time = time.time() - start_time
                print(f"[DEBUG PDF EMITIDOS] ✅ PDF aberto com sucesso - Tempo total: {total_time:.3f}s\n")
                self.set_status("✅ PDF aberto", 1000)
                return
            except Exception as e:
                print(f"[DEBUG PDF EMITIDOS] ❌ Erro ao abrir PDF: {e}")
                QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
                return
        
        # Se não tem PDF, verifica se tem XML antes de gerar
        print(f"[DEBUG PDF EMITIDOS] Etapa 5: Verificando XML antes de gerar PDF...")
        xml_check_start = time.time()
        
        # Busca o XML localmente primeiro
        xml_text = resolve_xml_text(item)
        if not xml_text:
            print(f"[DEBUG PDF EMITIDOS] ❌ XML não encontrado localmente")
            QMessageBox.warning(
                self, 
                "XML não encontrado", 
                f"Não foi possível encontrar o XML para a chave {chave}.\n\n"
                "O PDF só pode ser gerado se o XML estiver disponível."
            )
            return
        
        print(f"[DEBUG PDF EMITIDOS] ✅ XML encontrado, iniciando geração de PDF...")
        print(f"[DEBUG PDF EMITIDOS] Etapa 5 concluída em {time.time() - xml_check_start:.3f}s")
        
        # Tem XML, pode gerar PDF (LENTO) - executa em thread separada
        print(f"[DEBUG PDF EMITIDOS] Etapa 6: Geração de PDF necessária...")
        generation_start = time.time()
        self.set_status("⏳ Gerando PDF... Por favor aguarde...")
        QApplication.processEvents()
        
        # Cria worker thread para não travar a interface
        print(f"[DEBUG PDF EMITIDOS] Criando worker thread para geração assíncrona...")
        self._process_pdf_async(item)
        print(f"[DEBUG PDF EMITIDOS] Worker criado - aguardando conclusão em background")
        print(f"[DEBUG PDF EMITIDOS] ========================================\n")
    
    def _process_pdf_async(self, item: Dict[str, Any]):
        """Processa PDF em thread separada para não travar a UI"""
        
        class PDFWorker(QThread):
            finished = pyqtSignal(dict)  # {ok, pdf_path, error}
            status_update = pyqtSignal(str)  # Para atualizar status na UI
            
            def __init__(self, parent_window, item_data):
                super().__init__()
                self.parent_window = parent_window
                self.item = item_data
            
            def run(self):
                try:
                    chave = self.item.get('chave', '')
                    informante = self.item.get('informante', '')
                    tipo = (self.item.get('tipo') or 'NFe').strip().upper().replace('-', '')
                    
                    # Resolve XML
                    self.status_update.emit("🔍 Buscando XML...")
                    xml_text = resolve_xml_text(self.item)
                    
                    # Verifica se precisa buscar XML completo
                    def _is_nfe_full(x: str) -> bool:
                        xl = (x or '').lower()
                        return ('<nfeproc' in xl) or ('<protnfe' in xl)
                    def _is_cte_full(x: str) -> bool:
                        xl = (x or '').lower()
                        return ('<proccte' in xl) or ('<protcte' in xl)
                    
                    need_fetch = False
                    downloaded_from_sefaz = False
                    
                    if not xml_text:
                        need_fetch = True
                    else:
                        if tipo == 'NFE' and not _is_nfe_full(xml_text):
                            need_fetch = True
                        if tipo == 'CTE' and not _is_cte_full(xml_text):
                            need_fetch = True
                    
                    if need_fetch:
                        self.status_update.emit("⏳ Baixando XML completo da SEFAZ...")
                        try:
                            certs = self.parent_window.db.load_certificates()
                            selected = getattr(self.parent_window, '_selected_cert_cnpj', None)
                            if selected:
                                try:
                                    certs.sort(key=lambda c: 0 if (str(c.get('cnpj_cpf') or '') == selected or str(c.get('informante') or '') == selected) else 1)
                                except Exception:
                                    pass
                            prefer = ('nfeProc', 'NFe') if tipo == 'NFE' else ('procCTe', 'CTe')
                            for c in certs:
                                payload = {
                                    'cert': {
                                        'path': c.get('caminho') or '',
                                        'senha': c.get('senha') or '',
                                        'cnpj': c.get('cnpj_cpf') or '',
                                        'cuf': c.get('cUF_autor') or ''
                                    },
                                    'chave': chave,
                                    'prefer': list(prefer)
                                }
                                res = sandbox.run_task('fetch_by_chave', payload, timeout=240)
                                if res.get('ok') and res.get('data', {}).get('xml'):
                                    xml_text = res['data']['xml']
                                    downloaded_from_sefaz = True
                                    break
                        except Exception:
                            pass
                    
                    if not xml_text:
                        self.finished.emit({"ok": False, "error": "XML completo não encontrado (local/SEFAZ)."})
                        return
                    
                    # Save downloaded XML
                    saved_xml_path = None
                    if downloaded_from_sefaz:
                        self.status_update.emit("💾 Salvando XML...")
                        try:
                            data_emissao = (self.item.get('data_emissao') or '')[:10]
                            if chave and informante:
                                year_month = data_emissao[:7] if len(data_emissao) >= 7 else datetime.now().strftime("%Y-%m")
                                xmls_root = DATA_DIR / "xmls" / informante / tipo / year_month
                                xmls_root.mkdir(parents=True, exist_ok=True)
                                xml_file = xmls_root / f"{chave}.xml"
                                xml_file.write_text(xml_text, encoding='utf-8')
                                saved_xml_path = str(xml_file)
                                self.parent_window.db.register_xml_download(chave, saved_xml_path, informante)
                                upd = {'chave': chave, 'xml_status': 'COMPLETO', 'informante': informante}
                                for k in ['ie_tomador', 'nome_emitente', 'cnpj_emitente', 'numero',
                                          'data_emissao', 'tipo', 'valor', 'cfop', 'vencimento',
                                          'ncm', 'status', 'natureza', 'uf', 'base_icms', 'valor_icms']:
                                    if k in self.item:
                                        upd[k] = self.item[k]
                                self.parent_window.db.save_note(upd)
                        except Exception:
                            pass
                    
                    # Determine PDF path - OTIMIZADO para buscar o XML em toda estrutura
                    if saved_xml_path:
                        pdf_path = Path(saved_xml_path).with_suffix('.pdf')
                    else:
                        if chave and informante:
                            # Busca o XML em toda a estrutura do informante (incluindo Debug de notas)
                            xmls_root = DATA_DIR / "xmls"
                            found_xml = None
                            
                            # Busca 1: Na pasta do informante (mais provável)
                            informante_folder = xmls_root / informante
                            if informante_folder.exists():
                                for xml_file in informante_folder.rglob(f"{chave}.xml"):
                                    found_xml = xml_file
                                    break
                            
                            # Busca 2: Se não encontrou, busca em Debug de notas
                            if not found_xml:
                                debug_folder = xmls_root / "Debug de notas"
                                if debug_folder.exists():
                                    for xml_file in debug_folder.glob(f"*{chave}*.xml"):
                                        found_xml = xml_file
                                        break
                            
                            # Busca 3: Se ainda não encontrou, busca em toda estrutura
                            if not found_xml and xmls_root.exists():
                                for xml_file in xmls_root.rglob(f"*{chave}*.xml"):
                                    # Ignora pastas de backup
                                    if 'backup' not in str(xml_file).lower():
                                        found_xml = xml_file
                                        break
                            
                            if found_xml:
                                # Salva PDF junto com o XML encontrado
                                pdf_path = found_xml.with_suffix('.pdf')
                            else:
                                # Último recurso: pasta temporária
                                import tempfile
                                tmp = Path(tempfile.gettempdir()) / "BOT_Busca_NFE_PDFs"
                                tmp.mkdir(parents=True, exist_ok=True)
                                pdf_path = tmp / f"{tipo}-{chave}.pdf"
                        else:
                            import tempfile
                            tmp = Path(tempfile.gettempdir()) / "BOT_Busca_NFE_PDFs"
                            tmp.mkdir(parents=True, exist_ok=True)
                            pdf_path = tmp / f"{tipo}-{chave}.pdf"
                    
                    # Check if PDF exists (pode ter sido salvo junto com o XML)
                    if pdf_path.exists():
                        self.status_update.emit("✅ PDF encontrado!")
                        self.finished.emit({"ok": True, "pdf_path": str(pdf_path)})
                        return
                    
                    # Generate PDF
                    self.status_update.emit("📄 Gerando PDF do XML...")
                    payload: Dict[str, Any] = {
                        "xml": xml_text,
                        "tipo": (self.item.get("tipo") or "NFe"),
                        "out_path": str(pdf_path),
                        "force_simple_fallback": False,
                    }
                    res = sandbox.run_task("generate_pdf", payload, timeout=240)
                    if res.get("ok"):
                        if pdf_path.exists():
                            self.finished.emit({"ok": True, "pdf_path": str(pdf_path)})
                        else:
                            self.finished.emit({"ok": False, "error": "PDF não foi gerado"})
                    else:
                        self.finished.emit({"ok": False, "error": f"Falha ao gerar PDF: {res.get('error')}"})
                
                except Exception as e:
                    import traceback
                    self.finished.emit({"ok": False, "error": f"Erro: {str(e)}\n{traceback.format_exc()}"})
        
        # Cria e inicia worker
        worker = PDFWorker(self, item)
        
        def on_status(msg: str):
            self.set_status(msg)
        
        def on_finished(result: dict):
            if result.get("ok"):
                pdf_path = result.get("pdf_path")
                try:
                    if sys.platform == "win32":
                        # Abre PDF com visualizador padrão do Windows (evita abrir interface se PDF estiver associado incorretamente)
                        subprocess.Popen(["cmd", "/c", "start", "", pdf_path], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)  # type: ignore[attr-defined]
                    else:
                        subprocess.Popen(["xdg-open", pdf_path])
                    self.set_status("✅ PDF gerado e aberto com sucesso!", 2000)
                except Exception as e:
                    self.set_status("")
                    QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
            else:
                self.set_status("")
                error_msg = result.get("error", "Erro desconhecido")
                QMessageBox.critical(self, "Erro", error_msg)
        
        worker.status_update.connect(on_status)
        worker.finished.connect(on_finished)
        worker.start()
        
        # Mantém referência para evitar garbage collection
        if not hasattr(self, '_pdf_workers'):
            self._pdf_workers = []
        self._pdf_workers.append(worker)
        worker.finished.connect(lambda: self._pdf_workers.remove(worker) if worker in self._pdf_workers else None)

    def _auto_start_search(self):
        """Inicia busca automaticamente ao iniciar o sistema."""
        from datetime import datetime, timedelta
        
        try:
            # Usa o intervalo configurado pelo usuário (em horas)
            intervalo_horas = self.spin_intervalo.value()
            intervalo_minutos = intervalo_horas * 60
            
            # Verificar última execução
            last_search = self.db.get_last_search_time()
            
            if last_search:
                # Converter para datetime
                try:
                    last_dt = datetime.fromisoformat(last_search)
                    now = datetime.now()
                    diff_minutes = (now - last_dt).total_seconds() / 60
                    
                    # Se já passou o intervalo, inicia busca imediatamente
                    if diff_minutes >= intervalo_minutos:
                        self._search_in_progress = True
                        self.set_status(f"Última busca: {diff_minutes:.0f} minutos atrás. Iniciando busca automática...", 5000)
                        # Registra o horário da busca
                        self.db.set_last_search_time(datetime.now().isoformat())
                        # Inicia a busca
                        QTimer.singleShot(500, self.do_search)
                    else:
                        # Ainda está no intervalo de espera, calcula próxima busca
                        minutos_restantes = intervalo_minutos - diff_minutes
                        self._next_search_time = now + timedelta(minutes=minutos_restantes)
                        self.set_status(f"Última busca há {diff_minutes:.0f} minutos. Próxima em {minutos_restantes:.0f} minutos.", 5000)
                        
                        # Agenda a próxima busca
                        delay_ms = int(minutos_restantes * 60 * 1000)
                        QTimer.singleShot(delay_ms, self._auto_start_search)
                        
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self._search_in_progress = True
                    self.set_status("Iniciando busca automática...", 3000)
                    self.db.set_last_search_time(datetime.now().isoformat())
                    QTimer.singleShot(500, self.do_search)
            else:
                # Primeira execução
                self._search_in_progress = True
                self.set_status("Primeira execução. Iniciando busca automática...", 3000)
                # Registra o horário da busca
                self.db.set_last_search_time(datetime.now().isoformat())
                # Inicia a busca
                QTimer.singleShot(500, self.do_search)
            
        except Exception as e:
            print(f"[DEBUG] Erro em _auto_start_search: {e}")
            import traceback
            traceback.print_exc()
            self._search_in_progress = False
            self.set_status(f"Erro ao iniciar busca automática: {e}", 5000)
    
    def do_search(self):
        from datetime import datetime, timedelta
        
        # Marca busca em andamento
        self._search_in_progress = True
        self._next_search_time = None
        
        # Reseta estatísticas
        self._search_stats = {
            'nfes_found': 0,
            'ctes_found': 0,
            'start_time': datetime.now(),
            'last_cert': '',
            'total_docs': 0
        }
        
        # Mostra progress bar
        self.search_progress.setVisible(True)
        self.search_progress.setRange(0, 0)  # Modo indeterminado
        self.search_summary_label.setText("🔍 Iniciando busca...")
        
        # Atualiza timestamp da última busca
        try:
            self.db.set_last_search_time(datetime.now().isoformat())
        except Exception:
            pass  # Silencioso para evitar recursão
        
        # Janela de debug desabilitada - usando apenas status bar
        # dlg = SearchDialog(self)
        # dlg.show()
        # QApplication.processEvents()

        def on_progress(line: str):
            if not line:
                return
            
            # Atualiza resumo baseado nos logs
            try:
                # Detecta processamento de certificado
                if "Processando certificado" in line:
                    import re
                    match = re.search(r'CNPJ=(\d+)', line)
                    if match:
                        cnpj = match.group(1)
                        self._search_stats['last_cert'] = cnpj[-4:]  # Últimos 4 dígitos
                        self._update_search_summary()
                
                # Detecta NFe encontrada
                if "registrar_xml" in line.lower() or "infnfe" in line.lower():
                    self._search_stats['nfes_found'] += 1
                    self._update_search_summary()
                
                # Detecta CTe encontrado
                if "processar_cte" in line.lower() or "🚛" in line:
                    self._search_stats['ctes_found'] += 1
                    self._update_search_summary()
                
                # Detecta documentos processados
                if "docZip" in line or "NSU" in line:
                    self._search_stats['total_docs'] += 1
                    self._update_search_summary()
                    
            except Exception:
                pass  # REMOVIDO print() para evitar recursão via ProgressCapture
            
            # Detecta se a busca foi finalizada
            if "Busca de NSU finalizada" in line or "Próxima busca será agendada" in line or "Busca concluída" in line:
                # Marca que a busca finalizou
                self._search_in_progress = False
                
                # Oculta progress bar
                self.search_progress.setVisible(False)
                
                # Mostra resumo final
                elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
                self.search_summary_label.setText(
                    f"✅ NFes: {self._search_stats['nfes_found']} | "
                    f"CTes: {self._search_stats['ctes_found']} | "
                    f"Tempo: {elapsed:.0f}s"
                )
                
                # Usa o intervalo configurado pelo usuário (em horas)
                intervalo_horas = self.spin_intervalo.value()
                intervalo_minutos = intervalo_horas * 60
                
                # Calcula próxima busca baseado no intervalo configurado
                self._next_search_time = datetime.now() + timedelta(minutes=intervalo_minutos)
                
                # Atualiza status
                if intervalo_horas == 1:
                    self.set_status(f"Próxima busca em {intervalo_horas} hora", 0)
                else:
                    self.set_status(f"Próxima busca em {intervalo_horas} horas", 0)
                
                # Agenda a próxima busca automaticamente
                delay_ms = int(intervalo_minutos * 60 * 1000)
                QTimer.singleShot(delay_ms, self._auto_start_search)
                
                return
            
            # Linha de progresso é exibida apenas nos logs (não mais em janela)
            # Mantém apenas para compatibilidade com código existente

        # Worker thread para não travar a interface
        class SearchWorker(QThread):
            finished_search = pyqtSignal(dict)
            progress_line = pyqtSignal(str)
            error_occurred = pyqtSignal(str)
            
            def run(self):
                try:
                    res = run_search(progress_cb=lambda line: self.progress_line.emit(line))
                    self.finished_search.emit(res)
                except Exception as e:
                    import traceback
                    error_msg = f"Erro fatal na thread de busca: {str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    self.error_occurred.emit(error_msg)
                    self.finished_search.emit({"ok": False, "error": error_msg})
        
        def on_finished(res: Dict[str, Any]):
            try:
                if not res.get("ok"):
                    error = res.get('error') or res.get('message')
                    print(f"\nErro na busca: {error}")
                    self._search_in_progress = False
                    self.search_summary_label.setText(f"❌ Erro: {error[:50]}...")
                self.refresh_all()
                self._search_worker = None
                
                # Gera PDFs dos novos XMLs em background
                print("[INFO] Iniciando geração de PDFs dos novos XMLs...")
                QTimer.singleShot(1000, self._gerar_pdfs_faltantes)
            except Exception as e:
                import traceback
                error_msg = f"Erro em on_finished: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                QMessageBox.critical(self, "Erro", error_msg)
        
        def on_error(error_msg: str):
            try:
                print(f"[ERRO] {error_msg}")
                self._search_in_progress = False
                self.search_summary_label.setText(f"❌ Erro fatal")
                QMessageBox.critical(self, "Erro Fatal na Busca", error_msg)
            except Exception as e:
                print(f"Erro ao processar on_error: {e}")
        
        # Conecta sinais
        self._search_worker = SearchWorker()
        self._search_worker.progress_line.connect(on_progress)
        self._search_worker.finished_search.connect(on_finished)
        self._search_worker.error_occurred.connect(on_error)
        self._search_worker.start()

    # ==========================
    # Novas funções implementadas
    # ==========================
    def buscar_por_chave(self):
        """Busca NF-e/CT-e por chave de acesso (individual ou arquivo TXT)."""
        try:
            # Dialog para escolher método de entrada
            reply = QMessageBox.question(
                self,
                "Busca por Chave",
                "Como deseja informar a(s) chave(s) de acesso?\n\n"
                "• Sim = Digitar chave única\n"
                "• No = Importar arquivo .txt com múltiplas chaves",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Cancel:
                return
            
            chaves = []
            
            if reply == QMessageBox.Yes:
                # Entrada manual de chave única
                chave, ok = QInputDialog.getText(
                    self,
                    "Busca por Chave",
                    "Informe a chave de acesso (44 dígitos):"
                )
                if not ok or not chave:
                    return
                # Remove espaços e caracteres não numéricos
                chave_limpa = ''.join(c for c in chave if c.isdigit())
                if len(chave_limpa) != 44:
                    QMessageBox.warning(self, "Busca por Chave", "Chave inválida! Deve conter exatamente 44 dígitos.")
                    return
                chaves.append(chave_limpa)
            else:
                # Importar arquivo TXT
                arquivo, _ = QFileDialog.getOpenFileName(
                    self,
                    "Selecionar arquivo TXT com chaves",
                    "",
                    "Arquivos de texto (*.txt);;Todos os arquivos (*.*)"
                )
                if not arquivo:
                    return
                
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        for linha in f:
                            chave_limpa = ''.join(c for c in linha if c.isdigit())
                            if len(chave_limpa) == 44:
                                chaves.append(chave_limpa)
                    
                    if not chaves:
                        QMessageBox.warning(self, "Busca por Chave", "Nenhuma chave válida encontrada no arquivo.")
                        return
                except Exception as e:
                    QMessageBox.critical(self, "Busca por Chave", f"Erro ao ler arquivo: {e}")
                    return
            
            # Confirma busca
            total_chaves = len(chaves)
            reply = QMessageBox.question(
                self,
                "Busca por Chave",
                f"Buscar {total_chaves} chave(s) de acesso na SEFAZ?\n\n"
                f"As notas encontradas serão salvas automaticamente.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Executa busca em thread separada
            self._executar_busca_por_chaves(chaves)
            
        except Exception as e:
            QMessageBox.critical(self, "Busca por Chave", f"Erro: {e}")
    
    def _executar_busca_por_chaves(self, chaves):
        """Executa a busca das chaves em background."""
        import sys
        from lxml import etree
        sys.path.insert(0, str(BASE_DIR))
        from nfe_search import NFeService, XMLProcessor, DatabaseManager, salvar_xml_por_certificado, extrair_nota_detalhada
        
        # Cria dialog de progresso
        progress = QProgressDialog("Buscando chaves na SEFAZ...", "Cancelar", 0, len(chaves), self)
        progress.setWindowTitle("Busca por Chave")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        db = DatabaseManager(DB_PATH)
        parser = XMLProcessor()
        encontradas = 0
        nao_encontradas = 0
        erros = []
        
        # Carrega todos os certificados
        certificados = db.get_certificados()
        if not certificados:
            QMessageBox.warning(self, "Busca por Chave", "Nenhum certificado cadastrado!")
            return
        
        # Índice do certificado que teve sucesso (para priorizar nos próximos)
        ultimo_cert_sucesso = 0
        
        for idx, chave in enumerate(chaves):
            if progress.wasCanceled():
                break
            
            print(f"\n{'='*80}")
            print(f"[BUSCA POR CHAVE] Processando {idx+1}/{len(chaves)}: {chave}")
            print(f"{'='*80}")
            
            progress.setValue(idx)
            progress.setLabelText(f"Buscando chave {idx+1}/{len(chaves)}...\n{chave}")
            QApplication.processEvents()
            
            resp_xml = None
            cert_encontrado = None
            
            # Extrai UF da chave (primeiros 2 dígitos)
            uf_chave = chave[:2] if len(chave) >= 2 else None
            print(f"[DEBUG] UF da chave: {uf_chave}")
            
            # Ordena certificados: prioriza UF da chave, depois último sucesso, depois resto
            ordem_certs = []
            
            # 1. Certificados da mesma UF da chave
            for i, cert in enumerate(certificados):
                if cert[4] == uf_chave:  # cuf == uf_chave
                    ordem_certs.append(i)
            
            # 2. Último certificado com sucesso (se não estiver na lista)
            if ultimo_cert_sucesso not in ordem_certs:
                ordem_certs.insert(0, ultimo_cert_sucesso)
            
            # 3. Resto dos certificados
            for i in range(len(certificados)):
                if i not in ordem_certs:
                    ordem_certs.append(i)
            
            print(f"[DEBUG] Ordem de tentativa dos certificados: {[i+1 for i in ordem_certs]}")
            
            for cert_idx in ordem_certs:
                try:
                    cnpj, path, senha, inf, cuf = certificados[cert_idx]
                    print(f"[DEBUG] Tentando certificado {cert_idx+1}/{len(certificados)}: CNPJ={cnpj}, Informante={inf}, UF={cuf}")
                    
                    svc = NFeService(path, senha, cnpj, cuf)
                    
                    # Busca o XML da nota
                    print(f"[DEBUG] Chamando fetch_prot_nfe para chave: {chave}")
                    resp_xml = svc.fetch_prot_nfe(chave)
                    print(f"[DEBUG] Resposta recebida: {resp_xml[:200] if resp_xml else 'None'}...")
                    
                    if resp_xml:
                        # Verifica se é erro que indica "tente outro certificado"
                        # 217 = Nota não consta na base, 226 = UF divergente, 404 = namespace
                        erros_tentar_outro = ['217', '226', '404']
                        tem_erro_cert = any(f'<cStat>{cod}</cStat>' in resp_xml for cod in erros_tentar_outro)
                        
                        if not tem_erro_cert:
                            cert_encontrado = (cnpj, path, senha, inf, cuf)
                            ultimo_cert_sucesso = cert_idx
                            print(f"[SUCCESS] Nota encontrada com certificado {cert_idx+1}!")
                            break
                        else:
                            # Identifica qual erro
                            if '<cStat>217</cStat>' in resp_xml:
                                print(f"[INFO] Nota não consta na base deste certificado (217), tentando próximo...")
                            elif '<cStat>226</cStat>' in resp_xml:
                                print(f"[INFO] UF divergente (226), tentando próximo...")
                            elif '<cStat>404</cStat>' in resp_xml:
                                print(f"[INFO] Erro de namespace (404), tentando próximo...")
                            else:
                                print(f"[INFO] Erro ao buscar, tentando próximo certificado...")
                    
                except Exception as e:
                    print(f"[ERRO] Erro ao tentar certificado {cert_idx+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Processa resultado
            try:
                if not resp_xml or not cert_encontrado:
                    nao_encontradas += 1
                    erros.append(f"{chave}: Não encontrada em nenhum certificado")
                    print(f"[ERRO] Chave não encontrada em nenhum certificado")
                    continue
                
                if resp_xml:
                    print(f"[DEBUG] Processando resposta XML...")
                    # Parse da resposta
                    try:
                        tree = etree.fromstring(resp_xml.encode('utf-8') if isinstance(resp_xml, str) else resp_xml)
                        print(f"[DEBUG] XML parseado com sucesso")
                        
                        # Extrai informações do protocolo
                        NS = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                        prot = tree.find('.//nfe:protNFe', namespaces=NS)
                        print(f"[DEBUG] protNFe encontrado: {prot is not None}")
                        
                        if prot is not None:
                            ch = prot.findtext('nfe:infProt/nfe:chNFe', namespaces=NS) or ''
                            cStat = prot.findtext('nfe:infProt/nfe:cStat', namespaces=NS) or ''
                            xMotivo = prot.findtext('nfe:infProt/nfe:xMotivo', namespaces=NS) or ''
                            print(f"[DEBUG] Protocolo: chave={ch}, cStat={cStat}, xMotivo={xMotivo}")
                            
                            # Salva status
                            if ch and cStat:
                                db.set_nf_status(ch, cStat, xMotivo)
                                print(f"[DEBUG] Status salvo no banco")
                            
                            # Se autorizada
                            if cStat in ['100', '101', '110', '150', '301', '302']:
                                # Registra no banco usando informante do certificado correto
                                _, _, _, inf_correto, _ = cert_encontrado
                                db.registrar_xml(chave, inf_correto)
                                encontradas += 1
                                print(f"[SUCCESS] Nota autorizada e registrada com certificado {inf_correto}!")
                            else:
                                nao_encontradas += 1
                                erros.append(f"{chave}: {cStat} - {xMotivo}")
                                print(f"[ERRO] Nota não autorizada: {cStat} - {xMotivo}")
                        else:
                            # Tenta extrair erro da consulta
                            cStat = tree.findtext('.//nfe:cStat', namespaces=NS) or ''
                            xMotivo = tree.findtext('.//nfe:xMotivo', namespaces=NS) or 'Protocolo não encontrado'
                            print(f"[ERRO] protNFe não encontrado. cStat={cStat}, xMotivo={xMotivo}")
                            nao_encontradas += 1
                            erros.append(f"{chave}: {cStat} - {xMotivo}")
                    
                    except Exception as e:
                        print(f"[EXCEPTION] Erro ao processar XML: {e}")
                        import traceback
                        traceback.print_exc()
                        nao_encontradas += 1
                        erros.append(f"{chave}: Erro ao processar XML - {str(e)}")
                else:
                    nao_encontradas += 1
                    erros.append(f"{chave}: Falha na comunicação")
                    
            except Exception as e:
                nao_encontradas += 1
                erros.append(f"{chave}: {str(e)}")
        
        progress.setValue(len(chaves))
        
        # Atualiza tabela
        self.refresh_all()
        
        # Mostra resultado
        mensagem = f"Busca concluída!\n\n"
        mensagem += f"✅ Encontradas e salvas: {encontradas}\n"
        mensagem += f"❌ Não encontradas/erro: {nao_encontradas}"
        
        if erros and len(erros) <= 10:
            mensagem += "\n\nErros:\n" + "\n".join(erros[:10])
        elif erros:
            mensagem += f"\n\n({len(erros)} erros - veja o log para detalhes)"
        
        QMessageBox.information(self, "Busca por Chave", mensagem)

    def do_busca_completa(self):
        """Busca completa: reseta NSU para 0 e busca todos os XMLs da SEFAZ."""
        from datetime import datetime, timedelta
        
        try:
            # Confirma operação
            reply = QMessageBox.question(
                self,
                "Busca Completa",
                "Esta operação irá:\n\n"
                "• Resetar o NSU para 0 (zero) - NFe e CTe\n"
                "• Limpar todos os bloqueios de erro 656\n"
                "• Buscar TODOS os XMLs disponíveis na SEFAZ (NFe + CTe)\n"
                "• Pode demorar muito tempo dependendo da quantidade\n\n"
                "Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Marca busca em andamento
            self._search_in_progress = True
            self._next_search_time = None
            
            # Reseta NSU para 0 no banco de dados e limpa bloqueios de erro 656
            try:
                with sqlite3.connect(str(DB_PATH)) as conn:
                    # Busca todos os certificados (informantes)
                    informantes = conn.execute("SELECT DISTINCT informante FROM certificados").fetchall()
                    total_informantes = len(informantes)
                    
                    # Reseta NSU individualmente para cada certificado (NFe E CTe)
                    for (informante,) in informantes:
                        conn.execute(
                            "INSERT OR REPLACE INTO nsu (informante, ult_nsu) VALUES (?, ?)",
                            (informante, '000000000000000')
                        )
                        # Reseta também NSU do CTe
                        conn.execute(
                            "INSERT OR REPLACE INTO nsu_cte (informante, ult_nsu) VALUES (?, ?)",
                            (informante, '000000000000000')
                        )
                    
                    # Limpa todos os bloqueios de erro 656
                    conn.execute("DELETE FROM erro_656")
                    conn.commit()
                    
                # Atualiza timestamp da última busca
                self.db.set_last_search_time(datetime.now().isoformat())
                
                self.set_status(f"NSU resetado para {total_informantes} certificado(s) e bloqueios limpos", 2000)
            except Exception as e:
                QMessageBox.critical(self, "Busca Completa", f"Erro ao resetar NSU: {e}")
                self._search_in_progress = False
                return
            
            # Reseta estatísticas para busca completa
            self._search_stats = {
                'nfes_found': 0,
                'ctes_found': 0,
                'start_time': datetime.now(),
                'last_cert': '',
                'total_docs': 0,
                'current_cert': 0,
                'total_certs': total_informantes
            }
            
            # Mostra progress bar com range determinado
            self.search_progress.setVisible(True)
            self.search_progress.setRange(0, total_informantes)
            self.search_progress.setValue(0)
            self.search_summary_label.setText(f"🔄 Busca Completa: 0/{total_informantes} certificados | NFes: 0 | CTes: 0")
            
            # Inicia busca na SEFAZ
            self.set_status("🔄 Busca Completa iniciada - aguarde...", 0)

            def on_progress(line: str):
                if not line:
                    return
                
                # Atualiza progresso baseado nos logs
                try:
                    import re
                    
                    # Detecta processamento de certificado
                    if "Processando certificado" in line:
                        match = re.search(r'CNPJ[=:]?\s*(\d+)', line, re.IGNORECASE)
                        if match:
                            cnpj = match.group(1)
                            self._search_stats['current_cert'] += 1
                            self._search_stats['last_cert'] = cnpj[-4:]
                            
                            # Atualiza progress bar
                            self.search_progress.setValue(self._search_stats['current_cert'])
                            
                            # Atualiza resumo
                            elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
                            self.search_summary_label.setText(
                                f"🔄 Busca Completa: {self._search_stats['current_cert']}/{total_informantes} certificados | "
                                f"NFes: {self._search_stats['nfes_found']} | "
                                f"CTes: {self._search_stats['ctes_found']} | "
                                f"Cert: ...{self._search_stats['last_cert']} | "
                                f"{elapsed:.0f}s"
                            )
                    
                    # Detecta NFe encontrada
                    if "registrar_xml" in line.lower() or "infnfe" in line.lower():
                        self._search_stats['nfes_found'] += 1
                        elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
                        self.search_summary_label.setText(
                            f"🔄 Busca Completa: {self._search_stats['current_cert']}/{total_informantes} certificados | "
                            f"NFes: {self._search_stats['nfes_found']} | "
                            f"CTes: {self._search_stats['ctes_found']} | "
                            f"Cert: ...{self._search_stats['last_cert']} | "
                            f"{elapsed:.0f}s"
                        )
                    
                    # Detecta CTe encontrado
                    if "processar_cte" in line.lower() or "🚛" in line:
                        self._search_stats['ctes_found'] += 1
                        elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
                        self.search_summary_label.setText(
                            f"🔄 Busca Completa: {self._search_stats['current_cert']}/{total_informantes} certificados | "
                            f"NFes: {self._search_stats['nfes_found']} | "
                            f"CTes: {self._search_stats['ctes_found']} | "
                            f"Cert: ...{self._search_stats['last_cert']} | "
                            f"{elapsed:.0f}s"
                        )
                        
                except Exception:
                    pass  # Silencioso para evitar recursão
                
                # Detecta se a busca foi finalizada
                if "Busca de NSU finalizada" in line or "Dormindo por" in line or "Busca concluída" in line:
                    # Marca que a busca finalizou
                    self._search_in_progress = False
                    
                    # Oculta progress bar
                    self.search_progress.setVisible(False)
                    
                    # Mostra resumo final
                    elapsed = (datetime.now() - self._search_stats['start_time']).total_seconds()
                    minutos = int(elapsed / 60)
                    segundos = int(elapsed % 60)
                    
                    tempo_str = f"{minutos}min {segundos}s" if minutos > 0 else f"{segundos}s"
                    
                    self.search_summary_label.setText(
                        f"✅ Busca Completa finalizada! NFes: {self._search_stats['nfes_found']} | "
                        f"CTes: {self._search_stats['ctes_found']} | "
                        f"Tempo: {tempo_str}"
                    )
                    
                    # Extrai tempo de espera (em minutos)
                    import re
                    match = re.search(r'(\d+)\s*minutos', line)
                    if match:
                        minutos_espera = int(match.group(1))
                        self._next_search_time = datetime.now() + timedelta(minutes=minutos_espera)
                        self.set_status(f"✅ Busca completa finalizada. Próxima em {minutos_espera} minutos", 3000)
                    else:
                        self.set_status("✅ Busca completa finalizada", 3000)
                    return
                
                # Logs no console
                print(line)

            # Worker thread para não travar a interface
            class SearchWorker(QThread):
                finished_search = pyqtSignal(dict)
                progress_line = pyqtSignal(str)
                
                def run(self):
                    res = run_search(progress_cb=lambda line: self.progress_line.emit(line))
                    self.finished_search.emit(res)
            
            def on_finished(res: Dict[str, Any]):
                if not res.get("ok"):
                    error = res.get('error') or res.get('message')
                    print(f"Erro na busca completa: {error}")
                    self.set_status(f"❌ Erro: {error[:50]}...", 5000)
                    self._search_in_progress = False
                    
                    # Oculta progress bar em caso de erro
                    self.search_progress.setVisible(False)
                    self.search_summary_label.setText(f"❌ Erro na busca completa")
                    
                # Atualiza interface
                self.refresh_all()
                self._search_worker = None
            
            # Conecta sinais
            self._search_worker = SearchWorker()
            self._search_worker.progress_line.connect(on_progress)
            self._search_worker.finished_search.connect(on_finished)
            self._search_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Busca Completa", f"Erro: {e}")

    def do_batch_pdf(self):
        try:
            root = QFileDialog.getExistingDirectory(self, "Selecionar pasta com XMLs")
            if not root:
                return
            root_path = Path(root)
            files = list(root_path.rglob('*.xml'))
            if not files:
                QMessageBox.information(self, "PDFs em lote", "Nenhum XML encontrado.")
                return
            # Sem SearchDialog - usando barra de status
            total = len(files)
            self.set_status(f"📄 Gerando PDFs: 0/{total}", 0)
            
            erros = 0
            for idx, f in enumerate(files, start=1):
                try:
                    self.set_status(f"📄 Gerando PDFs: {idx}/{total} ({int(idx/total*100)}%)", 0)
                    QApplication.processEvents()
                    
                    xml = f.read_text(encoding='utf-8', errors='ignore')
                    # detectar tipo simples
                    low = xml.lower()
                    if '<infcte' in low:
                        tipo = 'CTe'
                    elif '<nfse' in low:
                        tipo = 'NFS-e'
                    else:
                        tipo = 'NFe'
                    out_path = str(f.with_suffix('.pdf'))
                    payload: Dict[str, Any] = {"xml": xml, "tipo": tipo, "out_path": out_path, "force_simple_fallback": True}
                    res = sandbox.run_task("generate_pdf", payload, timeout=240)
                    if not res.get('ok'):
                        erros += 1
                except Exception:
                    erros += 1
                    continue
            
            msg = f"✅ PDFs gerados: {total - erros}/{total}"
            if erros > 0:
                msg += f" ({erros} erros)"
            self.set_status(msg, 5000)
            QMessageBox.information(self, "PDFs em lote", msg)
        except Exception as e:
            QMessageBox.critical(self, "PDFs em lote", f"Erro: {e}")

    def open_logs_folder(self):
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            path = str(LOGS_DIR)
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Logs", f"Erro ao abrir pasta de logs: {e}")

    def check_updates(self):
        """Verifica e aplica atualizações do GitHub."""
        from modules.updater import GitHubUpdater
        from PyQt5.QtWidgets import QProgressDialog, QMessageBox
        from PyQt5.QtCore import Qt
        
        try:
            # BASE_DIR: onde estão os arquivos .py (para atualizar)
            # DATA_DIR: onde criar backups (tem permissão de escrita)
            updater = GitHubUpdater("W4lterBr/NF-e", BASE_DIR, backup_dir=DATA_DIR / "backups")
            
            # Verifica se há atualizações
            has_update, current, remote = updater.check_for_updates()
            
            if remote == "Erro ao conectar":
                QMessageBox.warning(
                    self, 
                    "Atualizações",
                    "❌ Não foi possível conectar ao servidor de atualizações.\nVerifique sua conexão com a internet."
                )
                return
            
            if not has_update:
                QMessageBox.information(
                    self,
                    "Atualizações",
                    f"✅ Você já está na versão mais recente!\n\nVersão atual: {current}"
                )
                return
            
            # Pergunta se deseja atualizar
            reply = QMessageBox.question(
                self,
                "Atualização Disponível",
                f"📦 Nova versão disponível!\n\n"
                f"Versão atual: {current}\n"
                f"Nova versão: {remote}\n\n"
                f"Deseja atualizar agora?\n\n"
                f"⚠️ O aplicativo será reiniciado após a atualização.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Cria diálogo de progresso
            progress = QProgressDialog("Baixando atualizações...", "Cancelar", 0, 0, self)
            progress.setWindowTitle("Atualizando")
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.setCancelButton(None)  # Não permitir cancelar
            progress.show()
            
            def update_progress(msg):
                progress.setLabelText(msg)
                QApplication.processEvents()
            
            # Aplica atualização
            result = updater.apply_update(progress_callback=update_progress)
            
            progress.close()
            
            if result['success']:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowTitle("Atualização Concluída")
                msg_box.setText(result['message'])
                
                if result['updated_files']:
                    details = "Arquivos atualizados:\n" + "\n".join(f"• {f}" for f in result['updated_files'])
                    msg_box.setDetailedText(details)
                
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec_()
                
                # Pergunta se deseja reiniciar
                reply = QMessageBox.question(
                    self,
                    "Reiniciar Aplicativo",
                    "✅ Atualização concluída!\n\nDeseja reiniciar o aplicativo agora?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    # Atualiza o título antes de reiniciar (caso usuário cancele)
                    self._update_window_title()
                    QApplication.quit()
                    if getattr(sys, 'frozen', False):
                        # Executável compilado
                        os.startfile(sys.executable)
                    else:
                        # Desenvolvimento
                        os.execl(sys.executable, sys.executable, *sys.argv)
                else:
                    # Usuário não quer reiniciar agora - atualiza título mesmo assim
                    self._update_window_title()
            else:
                QMessageBox.warning(
                    self,
                    "Erro na Atualização",
                    f"❌ Erro ao aplicar atualização:\n\n{result['message']}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"❌ Erro inesperado ao verificar atualizações:\n\n{str(e)}"
            )

    def open_xmls_folder(self):
        try:
            xmls_dir = DATA_DIR / 'xmls'
            xmls_dir.mkdir(parents=True, exist_ok=True)
            base = str(xmls_dir)
            if sys.platform == "win32":
                os.startfile(base)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", base])
        except Exception as e:
            QMessageBox.critical(self, "XMLs", f"Erro ao abrir pasta xmls: {e}")

    def open_certificates(self):
        try:
            dlg = CertificateDialog(self.db, self)
            dlg.exec_()
            # Após fechar, recarrega dados (caso certificados impactem buscas futuras)
            try:
                self._populate_certs_tree()
            except Exception:
                pass
            self.set_status("Certificados atualizados", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Certificados", f"Erro: {e}")

    def limpar_dados(self):
        """Limpa interface e deleta XMLs baixados da SEFAZ."""
        try:
            # Confirmar ação
            reply = QMessageBox.question(
                self, 
                "Limpar Dados",
                "Esta ação irá:\n\n"
                "• Limpar a interface (tabela)\n"
                "• Deletar TODOS os XMLs baixados da SEFAZ\n"
                "• Limpar registros do banco de dados\n\n"
                "Esta operação NÃO pode ser desfeita!\n\n"
                "Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            self.set_status("Limpando dados…")
            QApplication.processEvents()
            
            # 1. Limpar tabela da interface
            self.notes = []
            self.table.clearContents()
            self.table.setRowCount(0)
            
            # 2. Limpar banco de dados
            try:
                with sqlite3.connect(str(DB_PATH)) as conn:
                    # Limpar tabelas principais
                    conn.execute("DELETE FROM notas_detalhadas")
                    conn.execute("DELETE FROM xmls_baixados")
                    conn.execute("DELETE FROM nf_status")
                    # Resetar NSU para recomeçar do zero
                    conn.execute("DELETE FROM nsu")
                    conn.commit()
            except Exception as e:
                QMessageBox.warning(self, "Limpar", f"Erro ao limpar banco de dados: {e}")
            
            # 3. Deletar XMLs da pasta xmls/
            xmls_folder = DATA_DIR / "xmls"
            deleted_count = 0
            try:
                if xmls_folder.exists():
                    import shutil
                    # Percorre todas as subpastas e deleta XMLs
                    for item in xmls_folder.iterdir():
                        if item.is_dir():
                            try:
                                shutil.rmtree(item)
                                deleted_count += 1
                            except Exception:
                                pass
                        elif item.suffix.lower() == '.xml':
                            try:
                                item.unlink()
                                deleted_count += 1
                            except Exception:
                                pass
            except Exception as e:
                QMessageBox.warning(self, "Limpar", f"Erro ao deletar XMLs: {e}")
            
            self.set_status(f"Dados limpos com sucesso ({deleted_count} itens removidos)", 3000)
            QMessageBox.information(
                self, 
                "Limpar Dados",
                f"Operação concluída!\n\n"
                f"• Interface limpa\n"
                f"• Banco de dados resetado\n"
                f"• {deleted_count} XMLs/pastas removidos"
            )
            
        except Exception as e:
            self.set_status("")
            QMessageBox.critical(self, "Limpar", f"Erro ao limpar dados: {e}")

    def open_storage_config(self):
        """Abre diálogo de configuração de armazenamento"""
        try:
            dlg = StorageConfigDialog(self.db, self)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Armazenamento", f"Erro: {e}")


class CertificateDialog(QDialog):
    def __init__(self, db: UIDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Gerenciar Certificados Digitais")
        self.resize(1100, 500)
        
        # Layout principal
        v = QVBoxLayout(self)
        v.setSpacing(15)
        v.setContentsMargins(20, 20, 20, 20)
        
        # Cabeçalho com título e estatísticas
        header = QHBoxLayout()
        title_label = QLabel("📜 Certificados Cadastrados")
        title_font = title_label.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header.addWidget(title_label)
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        header.addWidget(self.stats_label)
        header.addStretch(1)
        v.addLayout(header)

        # Tabela estilizada
        self.table = QTableWidget()
        headers = ["Informante", "CNPJ/CPF", "Nome do Certificado", "UF", "Status", "Vencimento"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        # Habilita ordenação clicável nos cabeçalhos
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # Ajustar larguras das colunas
        self.table.setColumnWidth(0, 180)  # Informante
        self.table.setColumnWidth(1, 180)  # CNPJ
        self.table.setColumnWidth(2, 350)  # Nome do Certificado
        self.table.setColumnWidth(3, 60)   # UF
        self.table.setColumnWidth(4, 120)  # Status
        self.table.setColumnWidth(5, 180)  # Vencimento
        
        v.addWidget(self.table)

        # Botões estilizados
        h = QHBoxLayout()
        h.setSpacing(10)
        
        btn_add = QPushButton("➕ Adicionar Certificado")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        btn_edit = QPushButton("✏️ Editar Selecionado")
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        
        btn_replace = QPushButton("🔄 Substituir Certificado")
        btn_replace.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E64A19;
            }
        """)
        
        btn_del = QPushButton("🗑️ Remover Selecionado")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c4180a;
            }
        """)
        
        btn_close = QPushButton("✖️ Fechar")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:pressed {
                background-color: #455A64;
            }
        """)
        
        btn_add.clicked.connect(self._on_add)
        btn_edit.clicked.connect(self._on_edit)
        btn_replace.clicked.connect(self._on_replace)
        btn_del.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.accept)
        
        h.addStretch(1)
        h.addWidget(btn_add)
        h.addWidget(btn_edit)
        h.addWidget(btn_replace)
        h.addWidget(btn_del)
        h.addWidget(btn_close)
        v.addLayout(h)

        self.reload()

    def _extract_cert_name(self, cert_path: str) -> str:
        """Extrai o nome do certificado (CN) do arquivo .pfx"""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            import os
            
            if not os.path.exists(cert_path):
                return "❌ Arquivo não encontrado"
            
            # Tenta extrair informações do certificado
            # Nota: cryptography requer senha, então vamos apenas mostrar o nome do arquivo
            filename = os.path.basename(cert_path)
            return filename.replace('.pfx', '').replace('.p12', '')
        except Exception:
            # Fallback: retorna apenas o nome do arquivo
            try:
                import os
                filename = os.path.basename(cert_path)
                return filename.replace('.pfx', '').replace('.p12', '')
            except Exception:
                return "N/D"
    
    def _extract_cert_expiry(self, cert_path: str, senha: str = "") -> str:
        """Extrai a data de vencimento do certificado .pfx"""
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.hazmat.backends import default_backend
            import os
            from datetime import datetime
            
            if not os.path.exists(cert_path):
                return "❌ Não encontrado"
            
            # Lê o arquivo do certificado
            with open(cert_path, 'rb') as f:
                pfx_data = f.read()
            
            # Tenta carregar o certificado
            try:
                # Tenta sem senha primeiro
                private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                    pfx_data, None, default_backend()
                )
            except Exception:
                try:
                    # Tenta com senha se fornecida
                    if senha:
                        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                            pfx_data, senha.encode(), default_backend()
                        )
                    else:
                        return "N/D"
                except Exception:
                    return "N/D"
            
            if certificate:
                # Extrai data de validade
                expiry = certificate.not_valid_after_utc if hasattr(certificate, 'not_valid_after_utc') else certificate.not_valid_after
                expiry_str = expiry.strftime("%d/%m/%Y")
                
                # Verifica se está vencido
                hoje = datetime.now()
                if expiry.replace(tzinfo=None) < hoje:
                    return f"🔴 {expiry_str} (Vencido)"
                else:
                    # Verifica se vence em menos de 30 dias
                    dias_restantes = (expiry.replace(tzinfo=None) - hoje).days
                    if dias_restantes <= 30:
                        return f"🟡 {expiry_str} ({dias_restantes}d)"
                    else:
                        return f"🟢 {expiry_str}"
            
            return "N/D"
        except Exception as e:
            return "N/D"

    def reload(self):
        try:
            certs = self.db.load_certificates()
        except Exception:
            certs = []
        
        # Atualizar estatísticas
        total = len(certs)
        ativos = sum(1 for c in certs if c.get('ativo', 1) == 1)
        inativos = total - ativos
        self.stats_label.setText(f"Total: {total} | Ativos: {ativos} | Inativos: {inativos}")
        
        self.table.setRowCount(len(certs))
        for r, c in enumerate(certs):
            # Armazena ID como dado oculto na primeira coluna
            cert_id = c.get('id')
            
            def cell(x: Any, alignment=None):
                item = QTableWidgetItem(str(x or ""))
                if alignment:
                    item.setTextAlignment(alignment)
                # Armazena ID como UserRole em cada célula para referência
                item.setData(Qt.UserRole, cert_id)
                return item
            
            # Informante (CNPJ formatado)
            informante = c.get('informante', '')
            if informante and len(informante) >= 11:
                if len(informante) == 14:  # CNPJ
                    informante_fmt = f"{informante[:2]}.{informante[2:5]}.{informante[5:8]}/{informante[8:12]}-{informante[12:]}"
                else:  # CPF
                    informante_fmt = f"{informante[:3]}.{informante[3:6]}.{informante[6:9]}-{informante[9:]}"
            else:
                informante_fmt = informante
            self.table.setItem(r, 0, cell(informante_fmt))
            
            # CNPJ/CPF do certificado (formatado)
            cnpj_cpf = c.get('cnpj_cpf', '')
            if cnpj_cpf and len(cnpj_cpf) >= 11:
                if len(cnpj_cpf) == 14:
                    cnpj_fmt = f"{cnpj_cpf[:2]}.{cnpj_cpf[2:5]}.{cnpj_cpf[5:8]}/{cnpj_cpf[8:12]}-{cnpj_cpf[12:]}"
                else:
                    cnpj_fmt = f"{cnpj_cpf[:3]}.{cnpj_cpf[3:6]}.{cnpj_cpf[6:9]}-{cnpj_cpf[9:]}"
            else:
                cnpj_fmt = cnpj_cpf
            self.table.setItem(r, 1, cell(cnpj_fmt))
            
            # Nome do Certificado
            # Prioriza o nome personalizado, senão extrai do arquivo
            nome_cert = c.get('nome_certificado')
            if nome_cert:
                cert_name = nome_cert
            else:
                cert_name = self._extract_cert_name(c.get('caminho', ''))
            
            name_cell = cell(cert_name)
            name_cell.setForeground(QBrush(QColor("#2196F3")))
            name_cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(r, 2, name_cell)
            
            # UF
            uf_cell = cell(c.get('cUF_autor', ''), Qt.AlignCenter)
            self.table.setItem(r, 3, uf_cell)
            
            # Status (Ativo/Inativo com ícones)
            ativo = c.get('ativo', 1)
            status_text = "🟢 Ativo" if ativo == 1 else "🔴 Inativo"
            status_cell = cell(status_text, Qt.AlignCenter)
            if ativo == 1:
                status_cell.setForeground(QBrush(QColor("#4CAF50")))
            else:
                status_cell.setForeground(QBrush(QColor("#f44336")))
            status_cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(r, 4, status_cell)
            
            # Data de vencimento do certificado
            senha = c.get('senha', '')
            vencimento = self._extract_cert_expiry(c.get('caminho', ''), senha)
            venc_cell = cell(vencimento, Qt.AlignCenter)
            
            # Colorir conforme status do vencimento
            if "🔴" in vencimento:  # Vencido
                venc_cell.setForeground(QBrush(QColor("#f44336")))
                venc_cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif "🟡" in vencimento:  # Próximo ao vencimento
                venc_cell.setForeground(QBrush(QColor("#FF9800")))
                venc_cell.setFont(QFont("Segoe UI", 9, QFont.Bold))
            elif "🟢" in vencimento:  # Válido
                venc_cell.setForeground(QBrush(QColor("#4CAF50")))
            else:
                venc_cell.setForeground(QBrush(QColor("#999")))
            
            self.table.setItem(r, 5, venc_cell)

    def _on_add(self):
        dlg = AddCertificateDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            
            success, error_msg = self.db.save_certificate(data)
            
            if success:
                QMessageBox.information(
                    self,
                    "✅ Sucesso",
                    f"Certificado adicionado com sucesso!\n\n"
                    f"Informante: {data.get('informante', 'N/D')}\n\n"
                    f"Observação: Se havia um registro antigo com o mesmo CNPJ/CPF,\n"
                    f"ele foi substituído automaticamente."
                )
            else:
                error_details = error_msg or "Erro desconhecido"
                QMessageBox.critical(
                    self, 
                    "❌ Erro ao Salvar Certificado", 
                    f"Não foi possível salvar o certificado.\n\n"
                    f"Detalhes do erro:\n{error_details}\n\n"
                    f"Verifique também os logs no terminal para mais informações."
                )
            self.reload()

    def _on_edit(self):
        """Abre diálogo para editar certificado selecionado"""
        idxs = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not idxs:
            QMessageBox.warning(self, "Editar", "Selecione um certificado para editar!")
            return
        
        row = idxs[0].row()
        # Recupera ID armazenado no UserRole da primeira coluna
        first_item = self.table.item(row, 0)
        if not first_item:
            return
        cert_id = first_item.data(Qt.UserRole)
        if not cert_id:
            return
        
        # Busca dados do certificado no banco
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM certificados WHERE id = ?", (cert_id,))
                cert_data = cursor.fetchone()
                
                if not cert_data:
                    QMessageBox.warning(self, "Editar", "Certificado não encontrado!")
                    return
                
                # Converte para dict
                cert_dict = dict(cert_data)
                
        except Exception as e:
            QMessageBox.critical(self, "Editar", f"Erro ao carregar certificado: {e}")
            return
        
        # Abre diálogo de edição
        dlg = EditCertificateDialog(self, cert_dict)
        if dlg.exec_() == QDialog.Accepted:
            updated_data = dlg.get_data()
            if updated_data:
                # Atualiza no banco
                try:
                    with sqlite3.connect(self.db.db_path) as conn:
                        conn.execute("""
                            UPDATE certificados 
                            SET nome_certificado = ?, cUF_autor = ?
                            WHERE id = ?
                        """, (updated_data.get('nome_certificado'), 
                              updated_data.get('cUF_autor'),
                              cert_id))
                        conn.commit()
                    
                    QMessageBox.information(
                        self,
                        "✅ Sucesso",
                        "Certificado atualizado com sucesso!"
                    )
                    self.reload()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao atualizar certificado: {e}")

    def _on_replace(self):
        """Substitui o arquivo e senha do certificado mantendo o histórico"""
        idxs = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not idxs:
            QMessageBox.warning(self, "Substituir", "Selecione um certificado para substituir!")
            return
        
        row = idxs[0].row()
        # Recupera ID armazenado no UserRole da primeira coluna
        first_item = self.table.item(row, 0)
        if not first_item:
            return
        cert_id = first_item.data(Qt.UserRole)
        if not cert_id:
            return
        
        # Busca dados do certificado no banco
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM certificados WHERE id = ?", (cert_id,))
                cert_data = cursor.fetchone()
                
                if not cert_data:
                    QMessageBox.warning(self, "Substituir", "Certificado não encontrado!")
                    return
                
                # Converte para dict
                cert_dict = dict(cert_data)
                
        except Exception as e:
            QMessageBox.critical(self, "Substituir", f"Erro ao carregar certificado: {e}")
            return
        
        # Abre diálogo de substituição
        dlg = ReplaceCertificateDialog(self, cert_dict)
        if dlg.exec_() == QDialog.Accepted:
            replacement_data = dlg.get_data()
            if replacement_data:
                # Atualiza no banco (apenas caminho e senha)
                try:
                    # Criptografa a senha antes de salvar
                    from modules.crypto_portable import get_portable_crypto as get_crypto
                    senha_to_save = replacement_data.get('senha', '')
                    if senha_to_save:
                        crypto = get_crypto()
                        senha_to_save = crypto.encrypt(senha_to_save)
                    
                    with sqlite3.connect(self.db.db_path) as conn:
                        conn.execute("""
                            UPDATE certificados 
                            SET caminho = ?, senha = ?
                            WHERE id = ?
                        """, (replacement_data.get('caminho'), 
                              senha_to_save,
                              cert_id))
                        conn.commit()
                    
                    QMessageBox.information(
                        self,
                        "✅ Sucesso",
                        f"Certificado substituído com sucesso!\n\n"
                        f"✔️ Novo arquivo: {replacement_data.get('caminho')}\n"
                        f"✔️ Nova validade: {replacement_data.get('validade', 'N/D')}\n\n"
                        f"📂 Todo o histórico de notas foi mantido."
                    )
                    self.reload()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao substituir certificado: {e}")

    def _on_delete(self):
        idxs = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not idxs:
            return
        row = idxs[0].row()
        # Recupera ID armazenado no UserRole da primeira coluna
        first_item = self.table.item(row, 0)
        if not first_item:
            return
        cert_id = first_item.data(Qt.UserRole)
        if not cert_id:
            return
        if QMessageBox.question(self, "Remover", f"Remover certificado selecionado?") != QMessageBox.Yes:
            return
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("DELETE FROM certificados WHERE id = ?", (cert_id,))
                conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Remover", f"Erro ao remover: {e}")
            return
        self.reload()


class ReplaceCertificateDialog(QDialog):
    """Diálogo para substituir arquivo e senha do certificado"""
    def __init__(self, parent=None, cert_data: dict = None):
        super().__init__(parent)
        self.cert_data = cert_data or {}
        self.setWindowTitle("🔄 Substituir Certificado")
        self.resize(700, 550)
        
        # Estilo moderno
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #FF9800;
            }
            QLineEdit:disabled {
                background-color: #f5f5f5;
                color: #666;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        v = QVBoxLayout(self)
        v.setSpacing(20)
        v.setContentsMargins(30, 30, 30, 30)
        
        # Cabeçalho
        header_label = QLabel("🔄 Substituir Certificado Digital")
        header_font = header_label.font()
        header_font.setPointSize(13)
        header_font.setBold(True)
        header_label.setFont(header_font)
        v.addWidget(header_label)
        
        # Aviso importante
        warning_box = QLabel(
            "⚠️ <b>Importante:</b> Esta operação substitui apenas o arquivo .pfx e a senha.<br>"
            "Todo o histórico de notas e configurações serão mantidos."
        )
        warning_box.setStyleSheet("""
            QLabel {
                background-color: #FFF3CD;
                border: 2px solid #FFA726;
                border-radius: 5px;
                padding: 10px;
                color: #856404;
            }
        """)
        warning_box.setWordWrap(True)
        v.addWidget(warning_box)
        
        # Info do certificado atual (somente leitura)
        current_group = QGroupBox("📋 Certificado Atual")
        current_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        current_layout = QVBoxLayout()
        current_layout.setSpacing(8)
        
        # Informações do certificado atual
        cnpj_label = QLabel(f"🆔 CNPJ/CPF: {self.cert_data.get('cnpj_cpf', 'N/D')}")
        cnpj_label.setStyleSheet("color: #333; font-weight: normal;")
        current_layout.addWidget(cnpj_label)
        
        inf_label = QLabel(f"👤 Informante: {self.cert_data.get('informante', 'N/D')}")
        inf_label.setStyleSheet("color: #333; font-weight: normal;")
        current_layout.addWidget(inf_label)
        
        razao = self.cert_data.get('razao_social', 'N/D')
        if razao and razao != 'N/D' and len(razao) > 50:
            razao = razao[:50] + "..."
        razao_label = QLabel(f"🏢 Razão Social: {razao}")
        razao_label.setStyleSheet("color: #333; font-weight: normal;")
        current_layout.addWidget(razao_label)
        
        # Arquivo atual
        arquivo_atual = self.cert_data.get('caminho', 'N/D')
        if len(arquivo_atual) > 60:
            arquivo_atual = "..." + arquivo_atual[-60:]
        arquivo_label = QLabel(f"📄 Arquivo atual: {arquivo_atual}")
        arquivo_label.setStyleSheet("color: #666; font-style: italic; font-weight: normal; font-size: 10px;")
        arquivo_label.setWordWrap(True)
        current_layout.addWidget(arquivo_label)
        
        current_group.setLayout(current_layout)
        v.addWidget(current_group)
        
        # Novo certificado
        new_group = QGroupBox("🆕 Novo Certificado")
        new_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        new_layout = QVBoxLayout()
        new_layout.setSpacing(15)
        
        # Campo de arquivo
        arquivo_label = QLabel("📁 Novo Arquivo do Certificado:")
        arquivo_label.setStyleSheet("font-weight: bold; color: #333;")
        new_layout.addWidget(arquivo_label)
        
        cert_layout = QHBoxLayout()
        self.cert_edit = QLineEdit()
        self.cert_edit.setPlaceholderText("Selecione o novo arquivo .pfx...")
        self.cert_edit.setReadOnly(True)
        
        btn_browse = QPushButton("🔍 Procurar...")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        btn_browse.clicked.connect(self._browse_cert)
        
        cert_layout.addWidget(self.cert_edit, 1)
        cert_layout.addWidget(btn_browse)
        new_layout.addLayout(cert_layout)
        
        # Campo de senha
        senha_label = QLabel("🔐 Nova Senha do Certificado:")
        senha_label.setStyleSheet("font-weight: bold; color: #333;")
        new_layout.addWidget(senha_label)
        
        self.senha_edit = QLineEdit()
        self.senha_edit.setPlaceholderText("Digite a senha do novo certificado...")
        self.senha_edit.setEchoMode(QLineEdit.Password)
        new_layout.addWidget(self.senha_edit)
        
        # Botão para validar
        validate_layout = QHBoxLayout()
        validate_layout.addStretch()
        btn_validate = QPushButton("🔎 Validar Novo Certificado")
        btn_validate.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_validate.clicked.connect(self._validate_cert)
        validate_layout.addWidget(btn_validate)
        validate_layout.addStretch()
        new_layout.addLayout(validate_layout)
        
        # Label de validação
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("padding: 5px; font-weight: normal;")
        self.validation_label.setWordWrap(True)
        new_layout.addWidget(self.validation_label)
        
        new_group.setLayout(new_layout)
        v.addWidget(new_group)
        
        v.addStretch()
        
        # Botões finais
        h = QHBoxLayout()
        h.addStretch()
        
        self.btn_save = QPushButton("🔄 Substituir")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setEnabled(False)  # Desabilitado até validar
        
        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        h.addWidget(self.btn_save)
        h.addWidget(btn_cancel)
        v.addLayout(h)
        
        # Armazena dados de validação
        self.validated_data = None
    
    def _browse_cert(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Novo Certificado Digital",
            "",
            "Certificados (*.pfx *.p12);;Todos os arquivos (*.*)"
        )
        if path:
            self.cert_edit.setText(path)
            self.validation_label.setText("")
            self.btn_save.setEnabled(False)
            self.validated_data = None
    
    def _validate_cert(self):
        """Valida o novo certificado"""
        cert_path = self.cert_edit.text().strip()
        senha = self.senha_edit.text().strip()
        
        if not cert_path:
            self.validation_label.setText("⚠️ Selecione o arquivo do certificado!")
            self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
            return
        
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.hazmat.backends import default_backend
            from cryptography import x509
            from datetime import datetime
            import os
            
            if not os.path.exists(cert_path):
                self.validation_label.setText("❌ Arquivo não encontrado!")
                self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
                return
            
            # Lê o arquivo
            with open(cert_path, 'rb') as f:
                pfx_data = f.read()
            
            # Tenta carregar o certificado
            try:
                private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                    pfx_data,
                    senha.encode() if senha else None,
                    default_backend()
                )
            except Exception as e:
                self.validation_label.setText(f"❌ Erro ao carregar certificado!\n{str(e)[:100]}")
                self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
                return
            
            if not certificate:
                self.validation_label.setText("❌ Certificado não encontrado no arquivo!")
                self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
                return
            
            # Extrai CNPJ do novo certificado
            subject = certificate.subject
            cn = None
            for attr in subject:
                if attr.oid._name == 'commonName':
                    cn = attr.value
                    break
            
            # Extrai CNPJ do CN
            import re
            novo_cnpj = None
            if cn:
                match = re.search(r'\d{14}', cn)
                if match:
                    novo_cnpj = match.group(0)
            
            # Valida se é o mesmo CNPJ
            cnpj_atual = self.cert_data.get('informante', '')
            if novo_cnpj != cnpj_atual:
                self.validation_label.setText(
                    f"❌ CNPJ incompatível!\n"
                    f"Atual: {cnpj_atual}\n"
                    f"Novo: {novo_cnpj or 'Não identificado'}"
                )
                self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
                return
            
            # Extrai validade
            validade = certificate.not_valid_after_utc
            validade_str = validade.strftime("%d/%m/%Y")
            
            # Verifica se não está vencido
            hoje = datetime.now(validade.tzinfo)
            if validade < hoje:
                self.validation_label.setText(
                    f"⚠️ Certificado já vencido!\n"
                    f"Vencimento: {validade_str}"
                )
                self.validation_label.setStyleSheet("color: #FF9800; padding: 5px;")
                self.btn_save.setEnabled(False)
                return
            
            # Sucesso!
            dias_restantes = (validade.replace(tzinfo=None) - datetime.now()).days
            self.validation_label.setText(
                f"✅ Certificado válido!\n"
                f"CNPJ: {novo_cnpj}\n"
                f"Validade: {validade_str} ({dias_restantes} dias)"
            )
            self.validation_label.setStyleSheet("color: #4CAF50; padding: 5px; font-weight: bold;")
            self.btn_save.setEnabled(True)
            
            # Armazena dados validados
            self.validated_data = {
                'caminho': cert_path,
                'senha': senha,
                'cnpj': novo_cnpj,
                'validade': validade_str
            }
            
        except Exception as e:
            self.validation_label.setText(f"❌ Erro na validação: {str(e)[:100]}")
            self.validation_label.setStyleSheet("color: #f44336; padding: 5px;")
            import traceback
            traceback.print_exc()
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """Retorna os dados validados"""
        return self.validated_data


class EditCertificateDialog(QDialog):
    """Diálogo para editar dados do certificado"""
    def __init__(self, parent=None, cert_data: dict = None):
        super().__init__(parent)
        self.cert_data = cert_data or {}
        self.setWindowTitle("✏️ Editar Certificado")
        self.resize(600, 400)
        
        # Estilo moderno
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit:disabled {
                background-color: #f5f5f5;
                color: #666;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        v = QVBoxLayout(self)
        v.setSpacing(20)
        v.setContentsMargins(30, 30, 30, 30)
        
        # Cabeçalho
        header_label = QLabel("Editar dados do certificado")
        header_font = header_label.font()
        header_font.setPointSize(13)
        header_font.setBold(True)
        header_label.setFont(header_font)
        v.addWidget(header_label)
        
        # Info do certificado (somente leitura)
        info_group = QGroupBox("📋 Informações do Certificado")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        
        # CNPJ/CPF
        cnpj_label = QLabel(f"🆔 CNPJ/CPF: {self.cert_data.get('cnpj_cpf', 'N/D')}")
        cnpj_label.setStyleSheet("color: #333; font-weight: normal;")
        info_layout.addWidget(cnpj_label)
        
        # Informante
        inf_label = QLabel(f"👤 Informante: {self.cert_data.get('informante', 'N/D')}")
        inf_label.setStyleSheet("color: #333; font-weight: normal;")
        info_layout.addWidget(inf_label)
        
        # Razão Social
        razao = self.cert_data.get('razao_social', 'N/D')
        if razao and razao != 'N/D' and len(razao) > 50:
            razao = razao[:50] + "..."
        razao_label = QLabel(f"🏢 Razão Social: {razao}")
        razao_label.setStyleSheet("color: #333; font-weight: normal;")
        info_layout.addWidget(razao_label)
        
        info_group.setLayout(info_layout)
        v.addWidget(info_group)
        
        # Campos editáveis
        edit_group = QGroupBox("✏️ Campos Editáveis")
        edit_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        edit_layout = QVBoxLayout()
        edit_layout.setSpacing(15)
        
        # Nome do Certificado
        nome_label = QLabel("📝 Nome do Certificado:")
        nome_label.setStyleSheet("font-weight: bold; color: #333;")
        edit_layout.addWidget(nome_label)
        
        self.nome_edit = QLineEdit()
        self.nome_edit.setText(self.cert_data.get('nome_certificado', ''))
        self.nome_edit.setPlaceholderText("Ex: Walter Transportes, Empresa Filial SP...")
        self.nome_edit.setStyleSheet("""
            QLineEdit {
                background-color: #fffef0;
                border: 2px solid #FFA726;
            }
            QLineEdit:focus {
                border: 2px solid #FF9800;
            }
        """)
        edit_layout.addWidget(self.nome_edit)
        
        # Nota sobre nome
        nota_nome = QLabel("💡 Este nome será usado ao salvar arquivos em vez do CNPJ")
        nota_nome.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        nota_nome.setWordWrap(True)
        edit_layout.addWidget(nota_nome)
        
        # UF Autor
        uf_label = QLabel("📍 UF Autor:")
        uf_label.setStyleSheet("font-weight: bold; color: #333;")
        edit_layout.addWidget(uf_label)
        
        self.uf_edit = QLineEdit()
        self.uf_edit.setText(str(self.cert_data.get('cUF_autor', '')))
        self.uf_edit.setPlaceholderText("Ex: 33 (Rio de Janeiro)")
        edit_layout.addWidget(self.uf_edit)
        
        edit_group.setLayout(edit_layout)
        v.addWidget(edit_group)
        
        v.addStretch()
        
        # Botões
        h = QHBoxLayout()
        h.addStretch()
        
        btn_save = QPushButton("💾 Salvar")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        h.addWidget(btn_save)
        h.addWidget(btn_cancel)
        v.addLayout(h)
    
    def get_data(self) -> Optional[Dict[str, Any]]:
        """Retorna os dados editados"""
        nome = self.nome_edit.text().strip()
        uf = self.uf_edit.text().strip()
        
        return {
            "nome_certificado": nome if nome else None,
            "cUF_autor": uf if uf else self.cert_data.get('cUF_autor')
        }


class AddCertificateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📜 Adicionar Certificado Digital")
        self.resize(700, 600)
        
        # Estilo moderno para o diálogo
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QLabel {
                font-size: 12px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit:disabled {
                background-color: #f5f5f5;
                color: #666;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        v = QVBoxLayout(self)
        v.setSpacing(20)
        v.setContentsMargins(30, 30, 30, 30)
        
        # Cabeçalho
        header_label = QLabel("Selecione o arquivo do certificado digital (.pfx)")
        header_font = header_label.font()
        header_font.setPointSize(13)
        header_font.setBold(True)
        header_label.setFont(header_font)
        v.addWidget(header_label)
        
        # Seção: Arquivo do certificado
        cert_section = QVBoxLayout()
        cert_section.setSpacing(10)
        
        cert_label = QLabel("📁 Arquivo do Certificado:")
        cert_label.setStyleSheet("font-weight: bold; color: #333;")
        cert_section.addWidget(cert_label)
        
        cert_layout = QHBoxLayout()
        self.cert_edit = QLineEdit()
        self.cert_edit.setPlaceholderText("Selecione o arquivo .pfx do certificado...")
        self.cert_edit.setReadOnly(True)
        
        btn_browse = QPushButton("🔍 Procurar...")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_browse.clicked.connect(self._browse_cert)
        
        cert_layout.addWidget(self.cert_edit, 1)
        cert_layout.addWidget(btn_browse)
        cert_section.addLayout(cert_layout)
        v.addLayout(cert_section)
        
        # Seção: Senha
        senha_section = QVBoxLayout()
        senha_section.setSpacing(10)
        
        senha_label = QLabel("🔐 Senha do Certificado:")
        senha_label.setStyleSheet("font-weight: bold; color: #333;")
        senha_section.addWidget(senha_label)
        
        self.senha_edit = QLineEdit()
        self.senha_edit.setPlaceholderText("Digite a senha do certificado...")
        self.senha_edit.setEchoMode(QLineEdit.Password)
        senha_section.addWidget(self.senha_edit)
        v.addLayout(senha_section)
        
        # Botão para extrair informações
        extract_layout = QHBoxLayout()
        extract_layout.addStretch()
        btn_extract = QPushButton("🔎 Extrair Informações do Certificado")
        btn_extract.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        btn_extract.clicked.connect(self._extract_cert_info)
        extract_layout.addWidget(btn_extract)
        extract_layout.addStretch()
        v.addLayout(extract_layout)
        
        # Linha separadora
        separator = QLabel()
        separator.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        separator.setStyleSheet("background-color: #ddd; max-height: 2px;")
        v.addWidget(separator)
        
        # Informações extraídas (desabilitadas por padrão)
        info_label = QLabel("ℹ️ Informações Extraídas:")
        info_label.setStyleSheet("font-weight: bold; color: #333; font-size: 13px;")
        v.addWidget(info_label)
        
        # Grid com informações
        from PyQt5.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setColumnStretch(1, 1)
        
        # Informante
        grid.addWidget(QLabel("👤 Informante (CNPJ/CPF):"), 0, 0)
        self.informante_edit = QLineEdit()
        self.informante_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.informante_edit.setReadOnly(True)
        grid.addWidget(self.informante_edit, 0, 1)
        
        # CNPJ/CPF do certificado
        grid.addWidget(QLabel("🆔 CNPJ/CPF do Certificado:"), 1, 0)
        self.cnpj_edit = QLineEdit()
        self.cnpj_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.cnpj_edit.setReadOnly(True)
        grid.addWidget(self.cnpj_edit, 1, 1)
        
        # Razão Social
        grid.addWidget(QLabel("🏢 Razão Social:"), 2, 0)
        self.razao_social_edit = QLineEdit()
        self.razao_social_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.razao_social_edit.setReadOnly(True)
        grid.addWidget(self.razao_social_edit, 2, 1)
        
        # UF
        grid.addWidget(QLabel("📍 UF Autor:"), 3, 0)
        self.uf_edit = QLineEdit()
        self.uf_edit.setPlaceholderText("Ex: 33 (Rio de Janeiro)")
        grid.addWidget(self.uf_edit, 3, 1)
        
        # Titular
        grid.addWidget(QLabel("📋 Titular:"), 4, 0)
        self.titular_edit = QLineEdit()
        self.titular_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.titular_edit.setReadOnly(True)
        grid.addWidget(self.titular_edit, 4, 1)
        
        # Validade
        grid.addWidget(QLabel("📅 Válido até:"), 5, 0)
        self.validade_edit = QLineEdit()
        self.validade_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.validade_edit.setReadOnly(True)
        grid.addWidget(self.validade_edit, 5, 1)
        
        # Nome do Certificado (campo editável)
        grid.addWidget(QLabel("📝 Nome do Certificado:"), 6, 0)
        self.nome_cert_edit = QLineEdit()
        self.nome_cert_edit.setPlaceholderText("Ex: Walter Transportes, Empresa Filial SP...")
        self.nome_cert_edit.setReadOnly(False)
        self.nome_cert_edit.setStyleSheet("""
            QLineEdit {
                background-color: #fffef0;
                border: 2px solid #FFA726;
            }
            QLineEdit:focus {
                border: 2px solid #FF9800;
            }
        """)
        grid.addWidget(self.nome_cert_edit, 6, 1)
        
        # Nota explicativa
        nota_label = QLabel("💡 O nome do certificado será usado ao salvar arquivos em vez do CNPJ")
        nota_label.setStyleSheet("color: #666; font-style: italic; font-size: 10px; padding-top: 5px;")
        nota_label.setWordWrap(True)
        grid.addWidget(nota_label, 7, 0, 1, 2)
        
        v.addLayout(grid)
        
        v.addStretch()
        
        # Botões finais
        h = QHBoxLayout()
        h.addStretch()
        
        btn_save = QPushButton("💾 Salvar")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        h.addWidget(btn_save)
        h.addWidget(btn_cancel)
        v.addLayout(h)
    
    def _browse_cert(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Certificado Digital",
            "",
            "Certificados (*.pfx *.p12);;Todos os arquivos (*.*)"
        )
        if path:
            self.cert_edit.setText(path)
    
    def _consultar_uf_cnpj(self, cnpj: str) -> tuple[Optional[str], Optional[str]]:
        """Consulta UF e Razão Social do CNPJ via API Brasil.
        
        Returns:
            tuple: (uf, razao_social) ou (None, None) em caso de erro
        """
        try:
            import requests
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
            print(f"[DEBUG] Consultando dados do CNPJ {cnpj} via API Brasil...")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                uf = data.get('uf')
                razao_social = data.get('razao_social')
                print(f"[DEBUG] UF encontrada: {uf}, Razão Social: {razao_social}")
                return (uf, razao_social)
            else:
                print(f"[DEBUG] Erro ao consultar CNPJ: status {response.status_code}")
                return (None, None)
        except Exception as e:
            print(f"[DEBUG] Erro ao consultar API Brasil: {e}")
            return (None, None)
    
    def _extract_cert_info(self):
        """Extrai informações do certificado automaticamente."""
        cert_path = self.cert_edit.text().strip()
        senha = self.senha_edit.text().strip()
        
        if not cert_path:
            QMessageBox.warning(self, "Atenção", "Selecione primeiro o arquivo do certificado!")
            return
        
        if not senha:
            reply = QMessageBox.question(
                self,
                "Senha",
                "Nenhuma senha foi fornecida. Deseja tentar extrair sem senha?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.hazmat.backends import default_backend
            from cryptography import x509
            from datetime import datetime
            import os
            
            if not os.path.exists(cert_path):
                QMessageBox.critical(self, "Erro", "Arquivo do certificado não encontrado!")
                return
            
            # Lê o arquivo
            with open(cert_path, 'rb') as f:
                pfx_data = f.read()
            
            # Tenta carregar o certificado
            try:
                private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                    pfx_data,
                    senha.encode() if senha else None,
                    default_backend()
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erro ao Carregar Certificado",
                    f"Não foi possível carregar o certificado.\n\n"
                    f"Verifique se a senha está correta.\n\n"
                    f"Erro: {e}"
                )
                return
            
            if not certificate:
                QMessageBox.warning(self, "Aviso", "Certificado não encontrado no arquivo!")
                return
            
            # Extrai informações do certificado
            subject = certificate.subject
            
            # Nome comum (CN)
            cn = None
            for attr in subject:
                if attr.oid == x509.NameOID.COMMON_NAME:
                    cn = attr.value
                    break
            
            # CNPJ ou CPF (procura em diferentes campos)
            documento = None
            
            # Tenta extrair do campo serialNumber ou do CN
            for attr in subject:
                if attr.oid == x509.NameOID.SERIAL_NUMBER:
                    # Remove caracteres não numéricos
                    serial = ''.join(c for c in attr.value if c.isdigit())
                    if len(serial) in [11, 14]:  # CPF ou CNPJ
                        documento = serial
                        break
            
            # Se não encontrou no serialNumber, tenta extrair do CN
            if not documento and cn:
                # Procura padrão de CNPJ/CPF no CN
                import re
                # CNPJ: XX.XXX.XXX/XXXX-XX ou 14 dígitos
                cnpj_match = re.search(r'(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})', cn)
                if cnpj_match:
                    documento = ''.join(c for c in cnpj_match.group(1) if c.isdigit())
                else:
                    # CPF: XXX.XXX.XXX-XX ou 11 dígitos
                    cpf_match = re.search(r'(\d{3}\.?\d{3}\.?\d{3}-?\d{2})', cn)
                    if cpf_match:
                        documento = ''.join(c for c in cpf_match.group(1) if c.isdigit())
            
            # Data de validade
            expiry = certificate.not_valid_after_utc if hasattr(certificate, 'not_valid_after_utc') else certificate.not_valid_after
            validade_str = expiry.strftime("%d/%m/%Y")
            
            # Verifica se está vencido
            hoje = datetime.now()
            if expiry.replace(tzinfo=None) < hoje:
                status_validade = f"❌ VENCIDO em {validade_str}"
            else:
                dias_restantes = (expiry.replace(tzinfo=None) - hoje).days
                if dias_restantes <= 30:
                    status_validade = f"⚠️ {validade_str} (Vence em {dias_restantes} dias)"
                else:
                    status_validade = f"✅ {validade_str}"
            
            # Preenche os campos
            if documento:
                self.informante_edit.setText(documento)
                self.cnpj_edit.setText(documento)
                
                # Consulta UF e Razão Social automaticamente via API Brasil
                if len(documento) == 14:  # É CNPJ
                    uf_encontrada, razao_social = self._consultar_uf_cnpj(documento)
                    
                    # Preenche razão social
                    if razao_social:
                        self.razao_social_edit.setText(razao_social)
                        print(f"[DEBUG] Razão Social preenchida: {razao_social}")
                    
                    # Preenche UF
                    if uf_encontrada:
                        # Mapeia UF para código
                        uf_to_codigo = {
                            'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
                            'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
                            'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
                            'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
                            'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
                            'SE': '28', 'TO': '17'
                        }
                        codigo_uf = uf_to_codigo.get(uf_encontrada)
                        if codigo_uf:
                            # Preenche no campo de texto
                            self.uf_edit.setText(codigo_uf)
                            print(f"[DEBUG] UF preenchida automaticamente: {codigo_uf} ({uf_encontrada})")
            else:
                QMessageBox.warning(
                    self,
                    "Atenção",
                    "Não foi possível extrair o CNPJ/CPF do certificado.\n"
                    "Você precisará preencher manualmente."
                )
            
            self.titular_edit.setText(cn or "N/D")
            self.validade_edit.setText(status_validade)
            
            uf_msg = ""
            razao_msg = ""
            if len(documento or '') == 14:
                uf_msg = f"\nUF: Preenchida automaticamente"
                if self.razao_social_edit.text():
                    razao_msg = f"\nRazão Social: {self.razao_social_edit.text()}"
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"Informações extraídas com sucesso!\n\n"
                f"Titular: {cn or 'N/D'}\n"
                f"CNPJ/CPF: {documento or 'Não encontrado'}{razao_msg}\n"
                f"Validade: {status_validade}{uf_msg}"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao extrair informações do certificado:\n\n{e}"
            )

    def get_data(self) -> Optional[Dict[str, Any]]:
        """Retorna os dados preenchidos no formulário."""
        cert_path = self.cert_edit.text().strip()
        senha = self.senha_edit.text().strip()
        informante = self.informante_edit.text().strip()
        cnpj_cpf = self.cnpj_edit.text().strip()
        cuf = self.uf_edit.text().strip()
        razao_social = self.razao_social_edit.text().strip()
        nome_certificado = self.nome_cert_edit.text().strip()
        
        if not cert_path:
            QMessageBox.warning(self, "Atenção", "Selecione o arquivo do certificado!")
            return None
        
        # Verifica se o arquivo existe
        import os
        if not os.path.exists(cert_path):
            QMessageBox.critical(
                self, 
                "Erro",
                f"Arquivo do certificado não encontrado:\n\n{cert_path}\n\n"
                "Verifique se o arquivo ainda existe no local especificado."
            )
            return None
        
        if not informante:
            QMessageBox.warning(self, "Atenção", "Informante não foi preenchido!\n\nClique em 'Extrair Informações' primeiro.")
            return None
        
        if not cnpj_cpf:
            QMessageBox.warning(self, "Atenção", "CNPJ/CPF do certificado não foi preenchido!\n\nClique em 'Extrair Informações' primeiro.")
            return None
        
        if not cuf:
            QMessageBox.warning(self, "Atenção", "Preencha o campo 'UF Autor' (código da UF, ex: 33 para RJ)")
            return None
        
        # Validação do código UF (deve ser numérico entre 11 e 53)
        try:
            cuf_int = int(cuf)
            if cuf_int < 11 or cuf_int > 53:
                QMessageBox.warning(
                    self, 
                    "Atenção",
                    f"Código UF inválido: {cuf}\n\n"
                    "Use um código entre 11 e 53.\n"
                    "Ex: 33 (Rio de Janeiro), 35 (São Paulo)"
                )
                return None
        except ValueError:
            QMessageBox.warning(
                self,
                "Atenção", 
                f"Código UF deve ser numérico!\n\n"
                f"Valor informado: '{cuf}'\n\n"
                "Ex: 33 (Rio de Janeiro), 35 (São Paulo)"
            )
            return None
        
        print(f"[DEBUG] Dados do certificado validados:")
        print(f"  - Informante: {informante}")
        print(f"  - CNPJ/CPF: {cnpj_cpf}")
        print(f"  - Caminho: {cert_path}")
        print(f"  - UF Autor: {cuf}")
        print(f"  - Razão Social: {razao_social or '(não preenchido)'}")
        print(f"  - Nome Certificado: {nome_certificado or '(não preenchido)'}")
        
        return {
            "informante": informante,
            "cnpj_cpf": cnpj_cpf,
            "caminho": cert_path,
            "senha": senha,
            "cUF_autor": cuf,
            "ativo": 1,
            "razao_social": razao_social if razao_social else None,
            "nome_certificado": nome_certificado if nome_certificado else None
        }


class AutofillWorker(QThread):
    log_line = pyqtSignal(str)
    percent = pyqtSignal(int)

    def __init__(self, db: UIDB, items: List[Dict[str, Any]]):
        super().__init__()
        self.db = db
        self.items = items

    def _emit(self, txt: str):
        try:
            self.log_line.emit(txt)
        except Exception:
            pass

    def run(self):
        try:
            total = max(1, len(self.items))
            # Pré-carrega certificados
            try:
                certs = self.db.load_certificates()
            except Exception:
                certs = []
            for idx, item in enumerate(self.items, start=1):
                chave = (item.get('chave') or '').strip()
                tipo = (item.get('tipo') or 'NFe').strip()
                informante = (item.get('informante') or '').strip()
                if not chave:
                    continue
                self.percent.emit(int((idx-1)/total*100))
                self._emit(f"[Autofill] {idx}/{len(self.items)} chave={chave}")

                # 1) Tenta XML local
                xml_text = resolve_xml_text(item)
                # 2) Se não encontrou, tenta SEFAZ via sandbox com os certificados
                if not xml_text:
                    # Prioriza certificado do informante quando possível
                    ordered = list(certs)
                    try:
                        ordered.sort(key=lambda c: 0 if (str(c.get('informante') or '').strip() == informante) else 1)
                    except Exception:
                        pass
                    prefer = ('nfeProc', 'NFe') if tipo.upper().replace('-', '') in ('NFE', 'NFE') else ('procCTe', 'CTe')
                    for c in ordered:
                        try:
                            payload = {
                                "cert": {
                                    "path": c.get('caminho') or '',
                                    "senha": c.get('senha') or '',
                                    "cnpj": c.get('cnpj_cpf') or '',
                                    "cuf": c.get('cUF_autor') or ''
                                },
                                "chave": chave,
                                "prefer": list(prefer)
                            }
                            res = sandbox.run_task("fetch_by_chave", payload, timeout=240)
                            if res.get("ok") and res.get("data", {}).get("xml"):
                                xml_text = res["data"]["xml"]
                                break
                        except Exception:
                            continue
                if not xml_text:
                    self._emit(f"  - XML não encontrado (local/SEFAZ): {chave}")
                    continue
                # 3) Extrai número/data e atualiza banco (e xml_status COMPLETO)
                numero = ''
                data_emissao = ''
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.fromstring(xml_text.encode('utf-8'))
                    nfe_ns = '{http://www.portalfiscal.inf.br/nfe}'
                    cte_ns = '{http://www.portalfiscal.inf.br/cte}'
                    if tree.find(f'.//{nfe_ns}infNFe') is not None:
                        numero = tree.findtext(f'.//{nfe_ns}ide/{nfe_ns}nNF') or ''
                        data_emissao = tree.findtext(f'.//{nfe_ns}ide/{nfe_ns}dhEmi') or tree.findtext(f'.//{nfe_ns}ide/{nfe_ns}dEmi') or ''
                    elif tree.find(f'.//{cte_ns}infCte') is not None:
                        numero = tree.findtext(f'.//{cte_ns}ide/{cte_ns}nCT') or ''
                        data_emissao = tree.findtext(f'.//{cte_ns}ide/{cte_ns}dhEmi') or tree.findtext(f'.//{cte_ns}ide/{cte_ns}dEmi') or ''
                    if data_emissao:
                        data_emissao = data_emissao[:19]
                except Exception:
                    pass
                upd: Dict[str, Any] = {'chave': chave}
                if numero:
                    upd['numero'] = numero
                if data_emissao:
                    upd['data_emissao'] = data_emissao
                if xml_text:
                    upd['xml_status'] = 'COMPLETO'
                if len(upd) > 1:
                    ok = self.db.save_note(upd)
                    if ok:
                        self._emit(f"  - Atualizado: numero={numero or '-'} data={data_emissao or '-'} status={'COMPLETO' if xml_text else 'RESUMO'}")
                self.percent.emit(int(idx/total*100))
        except Exception as e:
            try:
                self._emit(f"[Autofill] Erro: {e}")
            except Exception:
                pass


class StorageConfigDialog(QDialog):
    """Diálogo para configurar como os arquivos XML e PDF são armazenados"""
    
    def __init__(self, db: UIDB, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("⚙️ Configurações de Armazenamento")
        self.resize(700, 550)
        
        # Estilo moderno
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2196F3;
                font-size: 13px;
            }
            QLabel {
                font-size: 11px;
            }
            QLineEdit, QComboBox {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #2196F3;
            }
            QRadioButton {
                font-size: 11px;
                spacing: 8px;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("📁 Configure como seus arquivos serão organizados")
        title_font = title.font()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # === GRUPO 1: Pasta Base ===
        group_pasta = QGroupBox("📂 Pasta Base de Armazenamento")
        pasta_layout = QVBoxLayout()
        pasta_layout.setSpacing(10)
        
        pasta_label = QLabel("Caminho completo da pasta onde os arquivos serão salvos:")
        pasta_label.setStyleSheet("font-weight: normal; color: #666;")
        pasta_layout.addWidget(pasta_label)
        
        # Layout horizontal para campo + botão
        pasta_h_layout = QHBoxLayout()
        pasta_h_layout.setSpacing(8)
        
        self.pasta_edit = QLineEdit()
        self.pasta_edit.setPlaceholderText("Ex: C:/Arquivo Walter - Empresas/Notas NFe")
        pasta_h_layout.addWidget(self.pasta_edit, 1)
        
        btn_browse = QPushButton("📁 Procurar...")
        btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_browse.clicked.connect(self._browse_folder)
        pasta_h_layout.addWidget(btn_browse)
        
        pasta_layout.addLayout(pasta_h_layout)
        
        pasta_obs = QLabel("💡 Os arquivos serão salvos em: [PASTA_BASE]/[CNPJ]/[MÊS]/[TIPO]/")
        pasta_obs.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        pasta_layout.addWidget(pasta_obs)
        
        group_pasta.setLayout(pasta_layout)
        layout.addWidget(group_pasta)
        
        # === GRUPO 2: Formato do Mês ===
        group_mes = QGroupBox("📅 Formato da Pasta de Mês")
        mes_layout = QVBoxLayout()
        mes_layout.setSpacing(10)
        
        mes_label = QLabel("Como deseja organizar as pastas por mês:")
        mes_label.setStyleSheet("font-weight: normal; color: #666;")
        mes_layout.addWidget(mes_label)
        
        self.formato_combo = QComboBox()
        self.formato_combo.addItem("📅 AAAA-MM  (2025-01, 2025-02...)", "AAAA-MM")
        self.formato_combo.addItem("📅 MM-AAAA  (01-2025, 02-2025...)", "MM-AAAA")
        self.formato_combo.addItem("📅 AAAA/MM  (2025/01, 2025/02...)", "AAAA/MM")
        self.formato_combo.addItem("📅 MM/AAAA  (01/2025, 02/2025...)", "MM/AAAA")
        mes_layout.addWidget(self.formato_combo)
        
        mes_exemplo = QLabel("📁 Exemplo: xmls/33251845000109/2025-01/NFe/")
        mes_exemplo.setStyleSheet("color: #888; font-size: 10px; font-style: italic; margin-top: 5px;")
        mes_layout.addWidget(mes_exemplo)
        
        group_mes.setLayout(mes_layout)
        layout.addWidget(group_mes)
        
        # === GRUPO 3: Organização XML/PDF ===
        group_org = QGroupBox("🗂️ Organização de XML e PDF")
        org_layout = QVBoxLayout()
        org_layout.setSpacing(12)
        
        org_label = QLabel("Como deseja organizar XML e PDF:")
        org_label.setStyleSheet("font-weight: normal; color: #666;")
        org_layout.addWidget(org_label)
        
        self.radio_juntos = QRadioButton("📄 XMLs e PDFs na mesma pasta")
        self.radio_juntos.setToolTip("Exemplo: xmls/33251845000109/2025-01/NFe/ (contém .xml e .pdf)")
        org_layout.addWidget(self.radio_juntos)
        
        juntos_exemplo = QLabel("      └─ Exemplo: NFe/nota12345.xml + nota12345.pdf na mesma pasta")
        juntos_exemplo.setStyleSheet("color: #888; font-size: 10px; margin-left: 30px;")
        org_layout.addWidget(juntos_exemplo)
        
        self.radio_separados = QRadioButton("📁 XMLs e PDFs em pastas separadas")
        self.radio_separados.setToolTip("Exemplo: xmls/ e pdfs/ em pastas diferentes")
        self.radio_separados.setChecked(True)
        org_layout.addWidget(self.radio_separados)
        
        sep_exemplo = QLabel("      └─ Exemplo: xmls/33251845000109/2025-01/NFe/ e pdfs/33251845000109/2025-01/NFe/")
        sep_exemplo.setStyleSheet("color: #888; font-size: 10px; margin-left: 30px;")
        org_layout.addWidget(sep_exemplo)
        
        group_org.setLayout(org_layout)
        layout.addWidget(group_org)
        
        # === INFORMAÇÃO ADICIONAL ===
        info_box = QLabel(
            "ℹ️ <b>Estrutura de Pastas:</b><br>"
            "   • <b>NFe</b>: Notas Fiscais Eletrônicas<br>"
            "   • <b>CTe</b>: Conhecimentos de Transporte<br>"
            "   • <b>NFe/Eventos</b>: Eventos de NF-e (cancelamento, carta de correção...)<br>"
            "   • <b>CTe/Eventos</b>: Eventos de CT-e"
        )
        info_box.setStyleSheet("""
            background-color: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 6px;
            padding: 12px;
            color: #1565c0;
            font-size: 10px;
        """)
        info_box.setWordWrap(True)
        layout.addWidget(info_box)
        
        layout.addStretch()
        
        # === BOTÕES ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_save = QPushButton("💾 Salvar")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_save.clicked.connect(self.save_config)
        
        btn_cancel = QPushButton("✖ Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        # Carrega configurações atuais
        self.load_current_config()
        
        # Conecta mudanças para atualizar exemplo
        self.pasta_edit.textChanged.connect(self.update_example)
        self.formato_combo.currentIndexChanged.connect(self.update_example)
    
    def _browse_folder(self):
        """Abre diálogo para selecionar pasta"""
        current_path = self.pasta_edit.text().strip()
        
        # Se já tem um caminho, usa como inicial
        if current_path and os.path.exists(current_path):
            initial_dir = current_path
        else:
            initial_dir = str(Path.home())
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta de Armazenamento",
            initial_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.pasta_edit.setText(folder)
        
    def load_current_config(self):
        """Carrega as configurações atuais do banco"""
        try:
            # Pasta base - agora é caminho completo
            pasta = self.db.get_config('storage_pasta_base', str(DATA_DIR / 'xmls'))
            self.pasta_edit.setText(pasta)
            
            # Formato do mês
            formato = self.db.get_config('storage_formato_mes', 'AAAA-MM')
            for i in range(self.formato_combo.count()):
                if self.formato_combo.itemData(i) == formato:
                    self.formato_combo.setCurrentIndex(i)
                    break
            
            # Organização XML/PDF
            separado = self.db.get_config('storage_xml_pdf_separado', '1')
            if separado == '1':
                self.radio_separados.setChecked(True)
            else:
                self.radio_juntos.setChecked(True)
        except Exception as e:
            print(f"[ERRO] Ao carregar config de armazenamento: {e}")
    
    def update_example(self):
        """Atualiza o exemplo de caminho conforme as configurações"""
        try:
            pasta = self.pasta_edit.text().strip()
            if not pasta:
                pasta = str(DATA_DIR / 'xmls')
            
            formato = self.formato_combo.currentData() or 'AAAA-MM'
            
            # Gera exemplo de mês
            from datetime import datetime
            now = datetime.now()
            if formato == 'AAAA-MM':
                mes_exemplo = f"{now.year}-{now.month:02d}"
            elif formato == 'MM-AAAA':
                mes_exemplo = f"{now.month:02d}-{now.year}"
            elif formato == 'AAAA/MM':
                mes_exemplo = f"{now.year}/{now.month:02d}"
            else:  # MM/AAAA
                mes_exemplo = f"{now.month:02d}/{now.year}"
            
            # Atualiza label de exemplo
            exemplo = f"📁 Exemplo: {pasta}/33251845000109/{mes_exemplo}/NFe/"
            
            # Encontra o label de exemplo e atualiza
            for widget in self.findChildren(QLabel):
                if widget.text().startswith("📁 Exemplo:"):
                    widget.setText(exemplo)
                    break
        except Exception:
            pass
    
    def save_config(self):
        """Salva as configurações no banco"""
        try:
            pasta = self.pasta_edit.text().strip()
            
            if not pasta:
                QMessageBox.warning(self, "Atenção", "Por favor, informe o caminho da pasta base!")
                return
            
            # Converte para Path para normalizar
            try:
                pasta_path = Path(pasta)
                
                # Cria a pasta se não existir
                if not pasta_path.exists():
                    reply = QMessageBox.question(
                        self,
                        "Pasta não existe",
                        f"A pasta:\n{pasta}\n\nNão existe. Deseja criá-la?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        pasta_path.mkdir(parents=True, exist_ok=True)
                    else:
                        return
                
                # Verifica se é um diretório válido
                if not pasta_path.is_dir():
                    QMessageBox.warning(
                        self,
                        "Atenção",
                        "O caminho informado não é um diretório válido!"
                    )
                    return
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Caminho inválido:\n{e}"
                )
                return
            
            # Salva configurações (caminho normalizado)
            self.db.set_config('storage_pasta_base', str(pasta_path))
            self.db.set_config('storage_formato_mes', self.formato_combo.currentData())
            self.db.set_config('storage_xml_pdf_separado', '1' if self.radio_separados.isChecked() else '0')
            
            # Pergunta se quer copiar os arquivos existentes
            pasta_antiga = DATA_DIR / 'xmls'
            if pasta_antiga.exists() and pasta_antiga != pasta_path:
                reply = QMessageBox.question(
                    self,
                    "Copiar arquivos existentes?",
                    f"Deseja copiar todos os XMLs e PDFs da pasta atual para a nova localização?\n\n"
                    f"De: {pasta_antiga}\n"
                    f"Para: {pasta_path}\n\n"
                    f"Isso pode levar alguns minutos dependendo da quantidade de arquivos.",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self._copiar_arquivos(pasta_antiga, pasta_path)
            
            QMessageBox.information(
                self,
                "✅ Sucesso",
                f"Configurações de armazenamento salvas!\n\n"
                f"Pasta base: {pasta_path}\n"
                f"Formato mês: {self.formato_combo.currentData()}\n"
                f"XML/PDF: {'Separados' if self.radio_separados.isChecked() else 'Juntos'}\n\n"
                f"As novas configurações serão aplicadas aos próximos arquivos salvos."
            )
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configurações:\n{e}")
    
    def _copiar_arquivos(self, origem: Path, destino: Path):
        """Copia os arquivos XML e PDF da pasta antiga para a nova"""
        try:
            import shutil
            import re
            
            # Cria diálogo de progresso
            progress = QProgressDialog("Preparando cópia de arquivos...", "Cancelar", 0, 100, self)
            progress.setWindowTitle("Copiando Arquivos")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            # Pastas a ignorar
            pastas_ignorar = ['Debug de notas', 'Resumos', 'debug', 'resumos']
            
            # Lista todos os arquivos XML e PDF recursivamente, exceto das pastas ignoradas
            arquivos = []
            for ext in ['*.xml', '*.pdf']:
                for arquivo in origem.rglob(ext):
                    # Verifica se o arquivo está em uma pasta que deve ser ignorada
                    deve_ignorar = False
                    for parte in arquivo.parts:
                        if parte in pastas_ignorar:
                            deve_ignorar = True
                            break
                    
                    if not deve_ignorar:
                        arquivos.append(arquivo)
            
            total = len(arquivos)
            if total == 0:
                QMessageBox.information(self, "Informação", "Nenhum arquivo encontrado para copiar.")
                return
            
            progress.setMaximum(total)
            progress.setLabelText(f"Copiando {total} arquivo(s)...")
            
            # Pega formato de mês configurado
            formato_mes = self.formato_combo.currentData()
            
            # Carrega mapeamento de CNPJ -> Nome do Certificado
            mapeamento_nomes = {}
            try:
                certs = self.db.load_certificates()
                for cert in certs:
                    informante = cert.get('informante', '')
                    nome_cert = cert.get('nome_certificado', '')
                    if informante and nome_cert:
                        # Remove caracteres inválidos do nome
                        nome_limpo = re.sub(r'[\\/*?:"<>|]', "_", nome_cert).strip()
                        mapeamento_nomes[informante] = nome_limpo
                        print(f"[DEBUG] Mapeamento: {informante} -> {nome_limpo}")
            except Exception as e:
                print(f"[ERRO] Ao carregar mapeamento de certificados: {e}")
            
            copiados = 0
            erros = 0
            ignorados = 0
            
            for idx, arquivo in enumerate(arquivos):
                if progress.wasCanceled():
                    QMessageBox.information(self, "Cancelado", f"Cópia cancelada. {copiados} arquivo(s) copiado(s).")
                    return
                
                try:
                    # Calcula o caminho relativo
                    caminho_relativo = arquivo.relative_to(origem)
                    partes = list(caminho_relativo.parts)
                    
                    # Verifica se há pelo menos 3 partes: CNPJ/MES/resto
                    if len(partes) >= 3:
                        cnpj_pasta = partes[0]
                        mes_pasta = partes[1]
                        resto = partes[2:]
                        
                        # NOVO: Busca nome do certificado para este CNPJ
                        nome_pasta_cert = mapeamento_nomes.get(cnpj_pasta, cnpj_pasta)
                        if nome_pasta_cert != cnpj_pasta:
                            print(f"[DEBUG] Convertendo pasta de {cnpj_pasta} para {nome_pasta_cert}")
                        
                        # Tenta converter o formato do mês se necessário
                        # Detecta formato AAAA-MM ou MM-AAAA
                        match_aaaa_mm = re.match(r'^(\d{4})-(\d{2})$', mes_pasta)
                        match_mm_aaaa = re.match(r'^(\d{2})-(\d{4})$', mes_pasta)
                        match_aaaa_slash_mm = re.match(r'^(\d{4})/(\d{2})$', mes_pasta)
                        match_mm_slash_aaaa = re.match(r'^(\d{2})/(\d{4})$', mes_pasta)
                        
                        nova_mes_pasta = mes_pasta  # Padrão: mantém original
                        
                        if match_aaaa_mm:
                            ano, mes = match_aaaa_mm.groups()
                            if formato_mes == 'AAAA-MM':
                                nova_mes_pasta = f"{ano}-{mes}"
                            elif formato_mes == 'MM-AAAA':
                                nova_mes_pasta = f"{mes}-{ano}"
                            elif formato_mes == 'AAAA/MM':
                                nova_mes_pasta = f"{ano}/{mes}"
                            elif formato_mes == 'MM/AAAA':
                                nova_mes_pasta = f"{mes}/{ano}"
                        
                        elif match_mm_aaaa:
                            mes, ano = match_mm_aaaa.groups()
                            if formato_mes == 'AAAA-MM':
                                nova_mes_pasta = f"{ano}-{mes}"
                            elif formato_mes == 'MM-AAAA':
                                nova_mes_pasta = f"{mes}-{ano}"
                            elif formato_mes == 'AAAA/MM':
                                nova_mes_pasta = f"{ano}/{mes}"
                            elif formato_mes == 'MM/AAAA':
                                nova_mes_pasta = f"{mes}/{ano}"
                        
                        elif match_aaaa_slash_mm:
                            ano, mes = match_aaaa_slash_mm.groups()
                            if formato_mes == 'AAAA-MM':
                                nova_mes_pasta = f"{ano}-{mes}"
                            elif formato_mes == 'MM-AAAA':
                                nova_mes_pasta = f"{mes}-{ano}"
                            elif formato_mes == 'AAAA/MM':
                                nova_mes_pasta = f"{ano}/{mes}"
                            elif formato_mes == 'MM/AAAA':
                                nova_mes_pasta = f"{mes}/{ano}"
                        
                        elif match_mm_slash_aaaa:
                            mes, ano = match_mm_slash_aaaa.groups()
                            if formato_mes == 'AAAA-MM':
                                nova_mes_pasta = f"{ano}-{mes}"
                            elif formato_mes == 'MM-AAAA':
                                nova_mes_pasta = f"{mes}-{ano}"
                            elif formato_mes == 'AAAA/MM':
                                nova_mes_pasta = f"{ano}/{mes}"
                            elif formato_mes == 'MM/AAAA':
                                nova_mes_pasta = f"{mes}/{ano}"
                        
                        # Reconstrói o caminho com nome do certificado (se disponível) e novo formato
                        novo_caminho_relativo = Path(nome_pasta_cert) / nova_mes_pasta / Path(*resto)
                        arquivo_destino = destino / novo_caminho_relativo
                    else:
                        # Se não tem estrutura esperada, mantém como está
                        arquivo_destino = destino / caminho_relativo
                    
                    # Cria as pastas necessárias
                    arquivo_destino.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copia o arquivo (não sobrescreve se já existir)
                    if not arquivo_destino.exists():
                        shutil.copy2(arquivo, arquivo_destino)
                        copiados += 1
                    else:
                        ignorados += 1
                    
                    progress.setValue(idx + 1)
                    progress.setLabelText(f"Copiando {idx + 1}/{total}: {arquivo.name}")
                    QApplication.processEvents()
                    
                except Exception as e:
                    print(f"[ERRO] Ao copiar {arquivo}: {e}")
                    erros += 1
            
            progress.close()
            
            # Mensagem final
            msg = f"✅ Cópia concluída!\n\n"
            msg += f"Arquivos copiados: {copiados}\n"
            if ignorados > 0:
                msg += f"Arquivos já existentes (ignorados): {ignorados}\n"
            if erros > 0:
                msg += f"Erros: {erros}\n"
            msg += f"\n📁 Pastas ignoradas: Debug de notas, Resumos"
            msg += f"\n\nOs arquivos originais foram mantidos em:\n{origem}"
            
            QMessageBox.information(self, "Cópia Concluída", msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao copiar arquivos:\n{e}")


def main():
    # Keep console open when run under VS Code for visibility
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    
    # ===== PROTEÇÃO CONTRA MÚLTIPLAS INSTÂNCIAS =====
    # Cria um mutex único para o sistema "Busca XML"
    # Se já existir, significa que outra instância está rodando
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        
        # Nome único do mutex (pode ser qualquer string única)
        mutex_name = "Global\\BuscaXML_SingleInstance_Mutex_9A8B7C6D"
        
        # Tenta criar o mutex
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = kernel32.GetLastError()
        
        # Se o mutex já existe, outra instância está rodando
        if last_error == ERROR_ALREADY_EXISTS:
            # Mostra mensagem de erro usando MessageBox do Windows (mais confiável que QMessageBox antes do QApplication)
            user32 = ctypes.windll.user32
            MB_OK = 0x00000000
            MB_ICONWARNING = 0x00000030
            MB_TOPMOST = 0x00040000
            
            mensagem = (
                "O sistema 'Busca XML' já está em execução!\n\n"
                "Não é permitido abrir múltiplas instâncias do programa.\n\n"
                "Por favor, use a instância que já está aberta."
            )
            user32.MessageBoxW(None, mensagem, "Busca XML - Já em Execução", MB_OK | MB_ICONWARNING | MB_TOPMOST)
            sys.exit(1)
        
        # Mantém o mutex aberto durante toda a execução do programa
        # Ele será automaticamente liberado quando o processo terminar
    # ===== FIM DA PROTEÇÃO =====
    
    app = QApplication(sys.argv)
    
    # Define o ícone do aplicativo (aparece na barra de tarefas do Windows)
    icon_path = BASE_DIR / 'Logo.ico'
    if not icon_path.exists():
        icon_path = BASE_DIR / 'Logo.png'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Não encerra o app quando a janela é fechada (vai para bandeja)
    app.setQuitOnLastWindowClosed(False)
    
    w = MainWindow()
    w.show()
    w._center_window()  # Centraliza depois de mostrar
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
