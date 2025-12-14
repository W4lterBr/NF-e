from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import sqlite3

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QComboBox, QProgressBar, QTextEdit,
    QDialog, QMessageBox, QFileDialog, QInputDialog, QStatusBar,
    QTreeWidget, QTreeWidgetItem, QSplitter, QAction, QMenu, QSystemTrayIcon,
    QProgressDialog, QStyledItemDelegate, QStyleOptionViewItem
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
        data_dir = app_data / "BOT Busca NFE"
    else:
        # Desenvolvimento: usa pasta local
        data_dir = Path(__file__).parent
    
    # Garante que o diretório existe
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"AVISO: Não foi possível criar {data_dir}: {e}")
        # Fallback para pasta temporária
        data_dir = Path(os.environ.get('TEMP', Path.home())) / "BOT Busca NFE"
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
            row = conn.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,)).fetchone()
            if row and row[0] and os.path.exists(row[0]):
                try:
                    return Path(row[0]).read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass
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
                    return f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
        for r in roots:
            if not r.exists():
                continue
            for f in r.rglob("*.xml"):
                try:
                    head = f.read_text(encoding="utf-8", errors="ignore")
                    if chave in head:
                        return head
                except Exception:
                    continue
    except Exception:
        pass
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
        
        # Define o ícone da janela principal
        icon_path = BASE_DIR / 'Logo.png'
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        ensure_logs_dir()

        self.db = UIDB(DB_PATH)

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
        self.status_dd = QComboBox(); self.status_dd.addItems(["Todos","Autorizado","Cancelado","Denegado"])
        self.status_dd.currentTextChanged.connect(self.refresh_table)
        self.tipo_dd = QComboBox(); self.tipo_dd.addItems(["Todos","NFe","CTe","NFS-e"])
        self.tipo_dd.currentTextChanged.connect(self.refresh_table)
        
        # Seletor de quantidade de linhas exibidas
        limit_label = QLabel("Exibir:")
        self.limit_dd = QComboBox()
        self.limit_dd.addItems(["50", "100", "500", "1000", "Todos"])
        self.limit_dd.setCurrentText("100")  # Padrão: 100 linhas
        self.limit_dd.currentTextChanged.connect(self.refresh_table)
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

        # Second tab: placeholder (emitidos pela empresa)
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.addWidget(QLabel("Emitidos pela empresa - (vazio)"))
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
                xmls_dir = BASE_DIR / "xmls"
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
        """Atualiza as UFs dos certificados existentes consultando a API Brasil."""
        try:
            print("[DEBUG] Atualizando UFs dos certificados existentes...")
            
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
                
                if len(cnpj) == 14:  # É CNPJ
                    try:
                        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
                        response = requests.get(url, timeout=5)
                        
                        if response.status_code == 200:
                            data = response.json()
                            uf = data.get('uf')
                            codigo_uf = uf_to_codigo.get(uf)
                            
                            if codigo_uf and codigo_uf != uf_atual:
                                print(f"[DEBUG] Atualizando UF do certificado {cnpj}: {uf_atual} -> {codigo_uf} ({uf})")
                                # Atualiza no banco usando context manager
                                with sqlite3.connect(str(DB_PATH)) as conn:
                                    conn.execute("UPDATE certificados SET cUF_autor = ? WHERE id = ?", (codigo_uf, cert_id))
                                    conn.commit()
                            elif codigo_uf == uf_atual:
                                print(f"[DEBUG] UF do certificado {cnpj} já está correta: {uf_atual}")
                            else:
                                print(f"[DEBUG] Não foi possível mapear UF {uf} para código")
                    except Exception as e:
                        print(f"[DEBUG] Erro ao atualizar UF do certificado {cnpj}: {e}")
            
            print("[DEBUG] Atualização de UFs concluída")
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar UFs dos certificados: {e}")
    
    def set_status(self, msg: str, timeout_ms: int = 0):
        self.status_label.setText(msg)
        if timeout_ms:
            QTimer.singleShot(timeout_ms, lambda: self.status_label.setText("Pronto"))
    
    def _setup_system_tray(self):
        """Configura o ícone na bandeja do sistema."""
        try:
            # Cria o ícone da bandeja
            self.tray_icon = QSystemTrayIcon(self)
            
            # Tenta carregar ícone personalizado, senão usa ícone padrão
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
            self.tray_icon.setToolTip("Busca de Notas Fiscais")
            
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
    
    def _quit_application(self):
        """Encerra a aplicação completamente."""
        reply = QMessageBox.question(
            self,
            "Confirmar saída",
            "Deseja realmente encerrar o sistema?\n\nA busca automática de notas fiscais será interrompida.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print("[DEBUG] Encerrando aplicação")
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            QApplication.quit()
    
    def closeEvent(self, event: QCloseEvent):
        """Intercepta o evento de fechar a janela."""
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
        # Cria um menu 'Tarefas' no menu bar com as ações principais
        menubar = self.menuBar()
        tarefas = menubar.addMenu("Tarefas")

        # Helper para criar ações com ícone opcional
        def add_action(menu: QMenu, text: str, slot, shortcut: Optional[str] = None, icon_name: Optional[str] = None):
            act = QAction(text, self)
            if shortcut:
                try:
                    act.setShortcut(shortcut)
                except Exception:
                    pass
            if icon_name:
                try:
                    act.setIcon(QIcon(str((BASE_DIR / 'Icone' / icon_name))))
                except Exception:
                    pass
            act.triggered.connect(slot)
            menu.addAction(act)
            return act

        # Ações principais já presentes na toolbar
        add_action(tarefas, "Atualizar", self.refresh_all, "F5", "refresh.png")
        tarefas.addSeparator()
        add_action(tarefas, "Buscar na SEFAZ", self.do_search, "Ctrl+B", "search.png")
        add_action(tarefas, "Busca Completa", self.do_busca_completa, "Ctrl+Shift+B", "search.png")
        add_action(tarefas, "PDFs em lote…", self.do_batch_pdf, "Ctrl+P", "pdf.png")
        tarefas.addSeparator()
        add_action(tarefas, "Busca por chave", self.buscar_por_chave, "Ctrl+K", "search.png")
        add_action(tarefas, "Certificados…", self.open_certificates, "Ctrl+Shift+C", "certificate.png")
        tarefas.addSeparator()
        add_action(tarefas, "🔄 Atualizações", self.check_updates, "Ctrl+U", "update.png")
        tarefas.addSeparator()
        add_action(tarefas, "Limpar", self.limpar_dados, "Ctrl+Shift+L", "xml.png")
        tarefas.addSeparator()
        add_action(tarefas, "Abrir XMLs", self.open_xmls_folder, "Ctrl+Shift+X", "xml.png")
        add_action(tarefas, "Abrir logs", self.open_logs_folder, "Ctrl+L", "log.png")

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
                self.set_status(f"{len(self.notes)} registros carregados", 3000)
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

    def filtered(self) -> List[Dict[str, Any]]:
        q = (self.search_edit.text() or "").lower().strip()
        selected_cert = getattr(self, '_selected_cert_cnpj', None)
        st = (self.status_dd.currentText() or "Todos").lower()
        tp = (self.tipo_dd.currentText() or "Todos").lower().replace('-', '')
        
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
            out.append(it)
            
            # Aplica limite se definido
            if limit and len(out) >= limit:
                break
        
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
            
            # Ordena por informante
            def keyf(c: Dict[str, Any]):
                return (str(c.get('informante') or '') + ' ' + str(c.get('cnpj_cpf') or '')).lower()
            
            for c in sorted(certs, key=keyf):
                informante = (c.get('informante') or '').strip()
                cnpj = (c.get('cnpj_cpf') or '').strip()
                label = informante or cnpj or 'Sem nome'
                if cnpj and informante and informante != cnpj:
                    label = f"{informante} ({cnpj})"
                node = QTreeWidgetItem([label])
                node.setToolTip(0, str(c.get('caminho') or ''))
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

    def _populate_row(self, r: int, it: Dict[str, Any]):
        def cell(c: Any) -> QTableWidgetItem:
            return QTableWidgetItem(str(c or ""))
        
        xml_status = (it.get("xml_status") or "RESUMO").upper()
        
        # Define texto e cores baseado no tipo (eventos não aparecem aqui pois são filtrados)
        if xml_status == "COMPLETO":
            status_text = ""  # Apenas ícone, sem texto
            bg_color = QColor(214, 245, 224)  # Verde claro
        else:  # RESUMO
            status_text = ""  # Apenas ícone, sem texto
            bg_color = QColor(235, 235, 235)  # Cinza claro
        
        c0 = cell(status_text)
        c0.setBackground(QBrush(bg_color))
        c0.setTextAlignment(Qt.AlignCenter)
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
        
        self.setWindowTitle(f"Busca de Notas Fiscais - v{version}")
    
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
        
        # Opção: Buscar XML Completo (só para RESUMO)
        if xml_status == 'RESUMO':
            action_buscar = menu.addAction("🔍 Buscar XML Completo na SEFAZ")
        else:
            action_buscar = None
        
        # Opção: Eventos (sempre disponível)
        menu.addSeparator()
        action_eventos = menu.addAction("📋 Ver Eventos")
        
        # Mostra menu e pega ação
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        
        if action == action_buscar:
            self._buscar_xml_completo(item)
        elif action == action_eventos:
            self._mostrar_eventos(item)
    
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
        
        # Busca eventos nos XMLs locais
        eventos_encontrados = []
        
        try:
            # Procura na pasta Eventos dentro da estrutura de XMLs
            xmls_root = BASE_DIR / "xmls" / informante
            if xmls_root.exists():
                # Busca em todas as pastas de eventos
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
            QMessageBox.warning(self, "Erro", f"Erro ao buscar eventos:\n{e}")
            return
        
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
            eventos_path = BASE_DIR / "xmls" / informante
            if eventos_path.exists():
                if sys.platform == "win32":
                    os.startfile(str(eventos_path))  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", str(eventos_path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao abrir pasta: {e}")

    def _on_table_double_clicked(self, row: int, col: int):
        """Abre PDF (em thread separada para não travar a interface)"""
        # Obtém o item pela linha clicada da lista filtrada
        flt = self.filtered()
        item = flt[row] if 0 <= row < len(flt) else None
        if not item:
            return
        
        # OTIMIZAÇÃO: Verifica primeiro se o PDF já existe localmente (RÁPIDO - UI thread)
        chave = item.get('chave', '')
        informante = item.get('informante', '')
        tipo = (item.get('tipo') or 'NFe').strip().upper().replace('-', '')
        
        # Tenta localizar PDF existente rapidamente
        pdf_path = None
        if chave and informante:
            xmls_root = BASE_DIR / "xmls" / informante
            if xmls_root.exists():
                # Busca na estrutura nova (com tipo)
                tipo_folder = xmls_root / tipo
                if tipo_folder.exists():
                    for xml_file in tipo_folder.rglob(f"{chave}.xml"):
                        potential_pdf = xml_file.with_suffix('.pdf')
                        if potential_pdf.exists():
                            pdf_path = potential_pdf
                            break
                # Se não encontrou, busca na estrutura antiga (sem tipo)
                if not pdf_path:
                    for xml_file in xmls_root.rglob(f"{chave}.xml"):
                        potential_pdf = xml_file.with_suffix('.pdf')
                        if potential_pdf.exists():
                            pdf_path = potential_pdf
                            break
        
        # Se PDF existe, abre imediatamente (RÁPIDO - não precisa de thread!)
        if pdf_path and pdf_path.exists():
            try:
                pdf_str = str(pdf_path.absolute())
                if sys.platform == "win32":
                    os.startfile(pdf_str)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", pdf_str])
                self.set_status("PDF aberto", 1000)
                return
            except Exception as e:
                QMessageBox.warning(self, "Erro ao abrir PDF", f"Erro: {e}")
                return
        
        # Se não tem PDF, precisa gerar (LENTO) - executa em thread separada
        self.set_status("⏳ Processando... Por favor aguarde...")
        QApplication.processEvents()
        
        # Cria worker thread para não travar a interface
        self._process_pdf_async(item)
        
        # Se não tem PDF, precisa gerar (LENTO) - executa em thread separada
        self.set_status("⏳ Processando... Por favor aguarde...")
        QApplication.processEvents()
        
        # Cria worker thread para não travar a interface
        self._process_pdf_async(item)
    
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
                                xmls_root = BASE_DIR / "xmls" / informante / tipo / year_month
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
                    
                    # Determine PDF path
                    if saved_xml_path:
                        pdf_path = Path(saved_xml_path).with_suffix('.pdf')
                    else:
                        if chave and informante:
                            xmls_root = BASE_DIR / "xmls" / informante
                            found_xml = None
                            if xmls_root.exists():
                                tipo_folder = xmls_root / tipo
                                if tipo_folder.exists():
                                    for xml_file in tipo_folder.rglob(f"{chave}.xml"):
                                        found_xml = xml_file
                                        break
                                if not found_xml:
                                    for xml_file in xmls_root.rglob(f"{chave}.xml"):
                                        found_xml = xml_file
                                        break
                            if found_xml:
                                pdf_path = found_xml.with_suffix('.pdf')
                            else:
                                import tempfile
                                tmp = Path(tempfile.gettempdir()) / "BOT_Busca_NFE_PDFs"
                                tmp.mkdir(parents=True, exist_ok=True)
                                pdf_path = tmp / f"{tipo}-{chave}.pdf"
                        else:
                            import tempfile
                            tmp = Path(tempfile.gettempdir()) / "BOT_Busca_NFE_PDFs"
                            tmp.mkdir(parents=True, exist_ok=True)
                            pdf_path = tmp / f"{tipo}-{chave}.pdf"
                    
                    # Check if PDF exists (pode ter sido criado entre a verificação inicial e agora)
                    if pdf_path.exists():
                        self.finished.emit({"ok": True, "pdf_path": str(pdf_path)})
                        return
                    
                    # Generate PDF
                    self.status_update.emit("📄 Gerando PDF...")
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
                        os.startfile(pdf_path)  # type: ignore[attr-defined]
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
                
                self.set_status(f"NSU resetado para {len(informantes)} certificado(s) e bloqueios limpos", 2000)
            except Exception as e:
                QMessageBox.critical(self, "Busca Completa", f"Erro ao resetar NSU: {e}")
                self._search_in_progress = False
                return
            
            # Inicia busca na SEFAZ (mesma lógica do do_search)
            # Sem SearchDialog - usando apenas barra de status
            self.set_status("🔄 Busca Completa: resetando NSU e buscando todos XMLs...", 0)

            def on_progress(line: str):
                if not line:
                    return
                
                # Detecta se a busca foi finalizada e vai dormir
                if "Busca de NSU finalizada" in line or "Dormindo por" in line:
                    # Marca que a busca finalizou
                    self._search_in_progress = False
                    
                    # Extrai tempo de espera (em minutos)
                    import re
                    match = re.search(r'(\d+)\s*minutos', line)
                    if match:
                        minutos = int(match.group(1))
                        # Calcula próxima busca
                        self._next_search_time = datetime.now() + timedelta(minutes=minutos)
                        self.set_status(f"✅ Busca completa finalizada. Próxima em {minutos} minutos", 3000)
                    else:
                        self.set_status("✅ Busca completa finalizada", 3000)
                    return
                
                # Atualiza status com a linha de progresso
                print(line)  # Logs no console

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
                    self._search_in_progress = False  # Libera para nova busca
                # Diálogo será fechado automaticamente por on_progress
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
        btn_del.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.accept)
        
        h.addStretch(1)
        h.addWidget(btn_add)
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
            ok = self.db.save_certificate(data)
            if ok:
                QMessageBox.information(
                    self,
                    "✅ Sucesso",
                    f"Certificado adicionado com sucesso!\n\n"
                    f"Informante: {data.get('informante', 'N/D')}\n\n"
                    f"Observação: Se havia um registro antigo com o mesmo CNPJ/CPF,\n"
                    f"ele foi substituído automaticamente."
                )
            else:
                QMessageBox.critical(
                    self, 
                    "❌ Erro", 
                    f"Não foi possível salvar o certificado.\n\n"
                    f"Verifique os logs no terminal para mais detalhes."
                )
            self.reload()

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
        
        # UF
        grid.addWidget(QLabel("📍 UF Autor:"), 2, 0)
        self.uf_edit = QLineEdit()
        self.uf_edit.setPlaceholderText("Ex: 33 (Rio de Janeiro)")
        grid.addWidget(self.uf_edit, 2, 1)
        
        # Titular
        grid.addWidget(QLabel("📋 Titular:"), 3, 0)
        self.titular_edit = QLineEdit()
        self.titular_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.titular_edit.setReadOnly(True)
        grid.addWidget(self.titular_edit, 3, 1)
        
        # Validade
        grid.addWidget(QLabel("📅 Válido até:"), 4, 0)
        self.validade_edit = QLineEdit()
        self.validade_edit.setPlaceholderText("Será preenchido automaticamente...")
        self.validade_edit.setReadOnly(True)
        grid.addWidget(self.validade_edit, 4, 1)
        
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
    
    def _consultar_uf_cnpj(self, cnpj: str) -> Optional[str]:
        """Consulta UF do CNPJ via API Brasil."""
        try:
            import requests
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
            print(f"[DEBUG] Consultando UF do CNPJ {cnpj} via API Brasil...")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                uf = data.get('uf')
                print(f"[DEBUG] UF encontrada: {uf}")
                return uf
            else:
                print(f"[DEBUG] Erro ao consultar CNPJ: status {response.status_code}")
                return None
        except Exception as e:
            print(f"[DEBUG] Erro ao consultar API Brasil: {e}")
            return None
    
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
                
                # Consulta UF automaticamente via API Brasil
                if len(documento) == 14:  # É CNPJ
                    uf_encontrada = self._consultar_uf_cnpj(documento)
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
            if len(documento or '') == 14:
                uf_msg = f"\n\nUF foi preenchida automaticamente."
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"Informações extraídas com sucesso!\n\n"
                f"Titular: {cn or 'N/D'}\n"
                f"CNPJ/CPF: {documento or 'Não encontrado'}\n"
                f"Validade: {status_validade}\n\n"
                f"Não esqueça de preencher o campo 'UF Autor' antes de salvar!"
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
        
        if not cert_path:
            QMessageBox.warning(self, "Atenção", "Selecione o arquivo do certificado!")
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
        
        return {
            "informante": informante,
            "cnpj_cpf": cnpj_cpf,
            "caminho": cert_path,
            "senha": senha,
            "cUF_autor": cuf,
            "ativo": 1
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


def main():
    # Keep console open when run under VS Code for visibility
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    app = QApplication(sys.argv)
    
    # Não encerra o app quando a janela é fechada (vai para bandeja)
    app.setQuitOnLastWindowClosed(False)
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
