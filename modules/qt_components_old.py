# modules/qt_components.py
"""
Componentes modernos PyQt6 para o sistema NFe
Design Material Design 3 com widgets nativos
"""

import sys
from typing import Optional, Callable, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QLineEdit, QTableWidget, 
    QTableWidgetItem, QComboBox, QDateEdit, QTextEdit, QScrollArea,
    QFrame, QSplitter, QHeaderView, QStatusBar, QMenuBar, QMenu,
    QMessageBox, QProgressBar, QTabWidget, QGroupBox, QCheckBox,
    QRadioButton, QSpinBox, QSlider, QDial, QListWidget, QTreeWidget,
    QSizePolicy, QSpacerItem, QToolBar, QFileDialog,
    QColorDialog, QFontDialog, QInputDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QRect, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup,
    QAbstractAnimation, QDate, QDateTime, QTime
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient, QFontMetrics,
    QAction, QKeySequence
)

# ===============================================================================
# TEMA E ESTILO DA APLICAÇÃO
# ===============================================================================

class AppTheme:
    """Tema unificado da aplicação - Material Design 3 para PyQt6"""
    
    # Cores principais (tema escuro moderno)
    PRIMARY = "#6366F1"
    PRIMARY_LIGHT = "#8B5CF6"
    PRIMARY_DARK = "#4338CA"
    
    SECONDARY = "#10B981"
    SECONDARY_LIGHT = "#34D399"
    SECONDARY_DARK = "#059669"
    
    # Estados
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#3B82F6"
    
    # Fundo e superfícies (tema claro moderno)
    BACKGROUND = "#F8FAFC"
    SURFACE = "#FFFFFF"
    SURFACE_VARIANT = "#F1F5F9"
    SURFACE_ELEVATED = "#FFFFFF"
    
    # Bordas
    BORDER_LIGHT = "#E2E8F0"
    BORDER_MEDIUM = "#CBD5E1"
    BORDER_DARK = "#94A3B8"
    
    # Texto
    TEXT_PRIMARY = "#0F172A"
    TEXT_SECONDARY = "#475569"
    TEXT_DISABLED = "#94A3B8"
    TEXT_ON_PRIMARY = "#FFFFFF"
    
    # Sombras
    SHADOW_LIGHT = "rgba(0, 0, 0, 0.05)"
    SHADOW_MEDIUM = "rgba(0, 0, 0, 0.10)"
    SHADOW_HEAVY = "rgba(0, 0, 0, 0.25)"
    
    # Espaçamentos
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32
    
    # Fontes
    FONT_SMALL = 11
    FONT_MEDIUM = 13
    FONT_LARGE = 14
    FONT_TITLE = 16
    FONT_HEADLINE = 18
    
    # Raios de borda
    RADIUS_SM = 6
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    
    @staticmethod
    def get_stylesheet() -> str:
        """Retorna o stylesheet principal da aplicação"""
        return f"""
        /* === ESTILO GLOBAL === */
        QMainWindow, QWidget {{
            background-color: {AppTheme.BACKGROUND};
            color: {AppTheme.TEXT_PRIMARY};
            font-family: 'Segoe UI', 'Inter', -apple-system, system-ui, sans-serif;
            font-size: {AppTheme.FONT_MEDIUM}px;
        }}
        
        /* === BOTÕES === */
        QPushButton {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_ON_PRIMARY};
            border: none;
            border-radius: {AppTheme.RADIUS_MD}px;
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_LG}px;
            font-weight: 500;
            font-size: {AppTheme.FONT_MEDIUM}px;
            min-height: 36px;
        }}
        
        QPushButton:hover {{
            background-color: {AppTheme.PRIMARY_LIGHT};
        }}
        
        QPushButton:pressed {{
            background-color: {AppTheme.PRIMARY_DARK};
        }}
        
        QPushButton:disabled {{
            background-color: {AppTheme.TEXT_DISABLED};
            color: {AppTheme.SURFACE};
        }}
        
        QPushButton[variant="outline"] {{
            background-color: {AppTheme.SURFACE};
            color: {AppTheme.PRIMARY};
            border: 2px solid {AppTheme.PRIMARY};
        }}
        
        QPushButton[variant="outline"]:hover {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_ON_PRIMARY};
        }}
        
        /* === CAMPOS DE ENTRADA === */
        QLineEdit, QComboBox, QDateEdit {{
            border: 2px solid {AppTheme.BORDER_LIGHT};
            border-radius: {AppTheme.RADIUS_MD}px;
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_MD}px;
            font-size: {AppTheme.FONT_MEDIUM}px;
            background-color: {AppTheme.SURFACE};
            color: {AppTheme.TEXT_PRIMARY};
            min-height: 32px;
        }}
        
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
            border-color: {AppTheme.PRIMARY};
        }}
        
        QLineEdit:hover, QComboBox:hover, QDateEdit:hover {{
            border-color: {AppTheme.BORDER_MEDIUM};
        }}
        
        /* === COMBOBOX === */
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border: 3px solid {AppTheme.TEXT_SECONDARY};
            border-top-color: transparent;
            border-left-color: transparent;
            border-right-color: transparent;
            width: 0px;
            height: 0px;
        }}
        
        QComboBox QAbstractItemView {{
            border: 1px solid {AppTheme.BORDER_LIGHT};
            border-radius: {AppTheme.RADIUS_MD}px;
            background-color: {AppTheme.SURFACE};
            selection-background-color: {AppTheme.PRIMARY_LIGHT};
        }}
        
        /* === TABELAS === */
        QTableWidget {{
            background-color: {AppTheme.SURFACE};
            border: 1px solid {AppTheme.BORDER_LIGHT};
            border-radius: {AppTheme.RADIUS_LG}px;
            gridline-color: {AppTheme.BORDER_LIGHT};
            font-size: {AppTheme.FONT_MEDIUM}px;
            alternate-background-color: {AppTheme.SURFACE_VARIANT};
        }}
        
        QTableWidget::item {{
            padding: {AppTheme.SPACING_MD}px {AppTheme.SPACING_SM}px;
            border: none;
            border-bottom: 1px solid {AppTheme.BORDER_LIGHT};
        }}
        
        QTableWidget::item:selected {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_ON_PRIMARY};
        }}
        
        QTableWidget::item:hover {{
            background-color: {AppTheme.SURFACE_VARIANT};
        }}
        
        QHeaderView::section {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            color: {AppTheme.TEXT_PRIMARY};
            padding: {AppTheme.SPACING_MD}px {AppTheme.SPACING_SM}px;
            border: none;
            border-bottom: 2px solid {AppTheme.BORDER_MEDIUM};
            font-weight: 600;
            font-size: {AppTheme.FONT_MEDIUM}px;
        }}
        
        /* === CARDS === */
        QFrame[class="card"] {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            border: 1px solid {AppTheme.BORDER_LIGHT};
            border-radius: {AppTheme.RADIUS_LG}px;
            padding: {AppTheme.SPACING_LG}px;
        }}
        
        /* === MENU BAR === */
        QMenuBar {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            border-bottom: 1px solid {AppTheme.BORDER_LIGHT};
            color: {AppTheme.TEXT_PRIMARY};
            padding: {AppTheme.SPACING_XS}px 0px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_MD}px;
            border-radius: {AppTheme.RADIUS_SM}px;
            margin: 0px {AppTheme.SPACING_XS}px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {AppTheme.SURFACE_VARIANT};
        }}
        
        QMenu {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            border: 1px solid {AppTheme.BORDER_LIGHT};
            border-radius: {AppTheme.RADIUS_MD}px;
            color: {AppTheme.TEXT_PRIMARY};
            padding: {AppTheme.SPACING_SM}px;
        }}
        
        QMenu::item {{
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_MD}px;
            border-radius: {AppTheme.RADIUS_SM}px;
            margin: 2px;
        }}
        
        QMenu::item:selected {{
            background-color: {AppTheme.PRIMARY};
            color: {AppTheme.TEXT_ON_PRIMARY};
        }}
        
        /* === TOOLBAR === */
        QToolBar {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            border: none;
            border-bottom: 1px solid {AppTheme.BORDER_LIGHT};
            spacing: {AppTheme.SPACING_SM}px;
            padding: {AppTheme.SPACING_SM}px;
        }}
        
        /* === STATUS BAR === */
        QStatusBar {{
            background-color: {AppTheme.SURFACE_ELEVATED};
            border-top: 1px solid {AppTheme.BORDER_LIGHT};
            color: {AppTheme.TEXT_SECONDARY};
            padding: {AppTheme.SPACING_SM}px;
        }}
        
        QStatusBar QLabel {{
            color: {AppTheme.TEXT_SECONDARY};
            padding: 0px {AppTheme.SPACING_SM}px;
        }}
        
        /* === SCROLLBAR === */
        QScrollBar:vertical {{
            background-color: {AppTheme.SURFACE_VARIANT};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {AppTheme.BORDER_MEDIUM};
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {AppTheme.TEXT_SECONDARY};
        }}
        """
            font-size: {AppTheme.FONT_MEDIUM}px;
            background-color: white;
        }}
        
        QLineEdit:focus {{
            border-color: {AppTheme.PRIMARY};
        }}
        
        /* ComboBox */
        QComboBox {{
            border: 2px solid {AppTheme.TEXT_DISABLED};
            border-radius: {AppTheme.RADIUS_MD}px;
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_MD}px;
            font-size: {AppTheme.FONT_MEDIUM}px;
            background-color: white;
        }}
        
        QComboBox:focus {{
            border-color: {AppTheme.PRIMARY};
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QComboBox::down-arrow {{
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgNkw4IDEwTDEyIDYiIHN0cm9rZT0iIzc1NzU3NSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
        }}
        
        /* Tabelas */
        QTableWidget {{
            background-color: white;
            border: 1px solid {AppTheme.TEXT_DISABLED};
            border-radius: {AppTheme.RADIUS_MD}px;
            gridline-color: {AppTheme.SURFACE_VARIANT};
            font-size: {AppTheme.FONT_MEDIUM}px;
        }}
        
        QTableWidget::item {{
            padding: {AppTheme.SPACING_SM}px;
            border-bottom: 1px solid {AppTheme.SURFACE_VARIANT};
        }}
        
        QTableWidget::item:selected {{
            background-color: {AppTheme.PRIMARY_LIGHT};
            color: white;
        }}
        
        QHeaderView::section {{
            background-color: {AppTheme.SURFACE_VARIANT};
            padding: {AppTheme.SPACING_MD}px {AppTheme.SPACING_SM}px;
            border: none;
            font-weight: 600;
            font-size: {AppTheme.FONT_MEDIUM}px;
        }}
        
        /* Cards e containers */
        QFrame[class="card"] {{
            background-color: white;
            border: 1px solid {AppTheme.SURFACE_VARIANT};
            border-radius: {AppTheme.RADIUS_LG}px;
            padding: {AppTheme.SPACING_MD}px;
        }}
        
        /* Status bar */
        QStatusBar {{
            background-color: {AppTheme.SURFACE_VARIANT};
            border-top: 1px solid {AppTheme.TEXT_DISABLED};
            color: {AppTheme.TEXT_SECONDARY};
        }}
        
        /* Menu bar */
        QMenuBar {{
            background-color: {AppTheme.SURFACE};
            border-bottom: 1px solid {AppTheme.PRIMARY_LIGHT};
        }}
        
        QMenuBar::item {{
            padding: {AppTheme.SPACING_SM}px {AppTheme.SPACING_MD}px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {AppTheme.PRIMARY_LIGHT};
            color: white;
        }}
        
        /* Progress bar */
        QProgressBar {{
            border: 2px solid {AppTheme.TEXT_DISABLED};
            border-radius: {AppTheme.RADIUS_MD}px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {AppTheme.PRIMARY};
            border-radius: {AppTheme.RADIUS_SM}px;
        }}
        """

# ===============================================================================
# COMPONENTES MODERNOS
# ===============================================================================

class ModernCard(QFrame):
    """Card moderno com sombra e bordas arredondadas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # Layout padrão
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(AppTheme.SPACING_MD, AppTheme.SPACING_MD, 
                                     AppTheme.SPACING_MD, AppTheme.SPACING_MD)
        self.card_layout.setSpacing(AppTheme.SPACING_SM)

class ModernButton(QPushButton):
    """Botão moderno com animações e variantes"""
    
    def __init__(self, text: str = "", icon: Optional[QIcon] = None, 
                 variant: str = "primary", parent=None):
        super().__init__(text, parent)
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))
        
        self.setProperty("variant", variant)
        self.setMinimumHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animação de hover
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

class StatusChip(QLabel):
    """Chip de status colorido"""
    
    def __init__(self, text: str, color: str = AppTheme.PRIMARY, parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: {AppTheme.RADIUS_XL}px;
                padding: {AppTheme.SPACING_XS}px {AppTheme.SPACING_MD}px;
                font-size: {AppTheme.FONT_SMALL}px;
                font-weight: 500;
            }}
        """)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMaximumHeight(24)

class SearchField(QLineEdit):
    """Campo de busca com ícone"""
    
    def __init__(self, placeholder: str = "Buscar...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        
        # Ícone de busca
        self.setStyleSheet(f"""
            QLineEdit {{
                padding-left: 30px;
                background-image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTNDMTAuMzEzNyAxMyAxMyAxMC4zMTM3IDEzIDdDMTMgMy42ODYzIDEwLjMxMzcgMSA3IDFDOM2dCM3IDEgMy42ODYzIDEgN0MxIDEwLjMxMzcgMy42ODYzIDEzIDcgMTNaIiBzdHJva2U9IiM3NTc1NzUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+CjxwYXRoIGQ9IjExIDExTDE1IDE1IiBzdHJva2U9IiM3NTc1NzUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
                background-repeat: no-repeat;
                background-position: 8px center;
            }}
        """)

class ModernTable(QTableWidget):
    """Tabela moderna com funcionalidades avançadas"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurações básicas
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        
        # Headers
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        
        # Altura das linhas
        self.verticalHeader().setDefaultSectionSize(40)

class StatsCard(ModernCard):
    """Card de estatística com ícone e valor"""
    
    def __init__(self, title: str, value: str, icon: Optional[QIcon] = None,
                 color: str = AppTheme.PRIMARY, parent=None):
        super().__init__(parent)
        
        # Usa o layout existente do ModernCard
        layout = QHBoxLayout()
        
        # Ícone
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(32, 32))
            layout.addWidget(icon_label)
        
        # Conteúdo
        content_layout = QVBoxLayout()
        
        # Valor
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_HEADLINE}px;
                font-weight: bold;
                color: {color};
                margin: 0;
            }}
        """)
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_MEDIUM}px;
                color: {AppTheme.TEXT_SECONDARY};
                margin: 0;
            }}
        """)
        
        content_layout.addWidget(value_label)
        content_layout.addWidget(title_label)
        content_layout.setSpacing(AppTheme.SPACING_XS)
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        # Adiciona ao layout existente do ModernCard
        container = QWidget()
        container.setLayout(layout)
        self.card_layout.addWidget(container)
        
        # Guarda referências para atualização
        self.value_label = value_label
        self.title_label = title_label
    
    def update_value(self, value: str):
        """Atualiza o valor do card"""
        self.value_label.setText(value)

class FilterPanel(ModernCard):
    """Painel de filtros avançados"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurações
        self.filters_changed = pyqtSignal(dict)
        
        # Campo de busca principal
        self.search_field = SearchField("Buscar por emitente, número ou CNPJ...")
        self.search_field.textChanged.connect(self._on_filter_change)
        
        # Filtros específicos
        filter_layout = QHBoxLayout()
        
        # Número da NF-e
        self.numero_field = QLineEdit()
        self.numero_field.setPlaceholderText("Número")
        self.numero_field.setMaximumWidth(120)
        self.numero_field.textChanged.connect(self._on_filter_change)
        
        # CNPJ
        self.cnpj_field = QLineEdit()
        self.cnpj_field.setPlaceholderText("CNPJ")
        self.cnpj_field.setMaximumWidth(160)
        self.cnpj_field.textChanged.connect(self._on_filter_change)
        
        # Data início
        self.data_inicio = QDateEdit()
        self.data_inicio.setCalendarPopup(True)
        self.data_inicio.setMaximumWidth(120)
        self.data_inicio.dateChanged.connect(self._on_filter_change)
        
        # Data fim
        self.data_fim = QDateEdit()
        self.data_fim.setCalendarPopup(True)
        self.data_fim.setMaximumWidth(120)
        self.data_fim.dateChanged.connect(self._on_filter_change)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Todos", "Autorizado", "Cancelado", "Denegado"])
        self.status_combo.setMaximumWidth(120)
        self.status_combo.currentTextChanged.connect(self._on_filter_change)
        
        # Botões
        self.apply_btn = ModernButton("Filtrar")
        self.apply_btn.clicked.connect(self._on_filter_change)
        
        self.clear_btn = ModernButton("Limpar", variant="outline")
        self.clear_btn.clicked.connect(self._clear_filters)
        
        # Layout
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
        filter_layout.addStretch()
        filter_layout.addWidget(self.apply_btn)
        filter_layout.addWidget(self.clear_btn)
        
        # Layout principal
        self.layout.addWidget(self.search_field)
        self.layout.addLayout(filter_layout)
    
    def _on_filter_change(self):
        """Emite sinal quando filtros mudam"""
        filters = {
            'search': self.search_field.text(),
            'numero': self.numero_field.text(),
            'cnpj': self.cnpj_field.text(),
            'data_inicio': self.data_inicio.date().toString('dd/MM/yyyy'),
            'data_fim': self.data_fim.date().toString('dd/MM/yyyy'),
            'status': self.status_combo.currentText()
        }
        # Note: Signal emission would need proper setup in actual implementation
        print(f"Filters changed: {filters}")  # Debug for now
    
    def _clear_filters(self):
        """Limpa todos os filtros"""
        self.search_field.clear()
        self.numero_field.clear()
        self.cnpj_field.clear()
        self.data_inicio.setDate(QDate.currentDate())
        self.data_fim.setDate(QDate.currentDate())
        self.status_combo.setCurrentIndex(0)
        self._on_filter_change()

# ===============================================================================
# DIALOGS MODERNOS
# ===============================================================================

class ModernMessageBox(QMessageBox):
    """MessageBox moderno"""
    
    def __init__(self, title: str, message: str, icon_type: str = "info", parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setText(message)
        
        # Ícones
        icons = {
            "info": QMessageBox.Icon.Information,
            "warning": QMessageBox.Icon.Warning,
            "error": QMessageBox.Icon.Critical,
            "question": QMessageBox.Icon.Question
        }
        
        self.setIcon(icons.get(icon_type, QMessageBox.Icon.Information))
        
        # Botões modernos
        self.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Estilo moderno
        self.setStyleSheet(f"""
            QMessageBox {{
                background-color: white;
                font-size: {AppTheme.FONT_MEDIUM}px;
            }}
            QMessageBox QPushButton {{
                min-width: 80px;
                min-height: 32px;
            }}
        """)

class ProgressDialog(QWidget):
    """Dialog de progresso moderno"""
    
    def __init__(self, title: str = "Processando...", parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_LARGE}px;
                font-weight: bold;
                margin: {AppTheme.SPACING_MD}px 0;
            }}
        """)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        # Status
        self.status_label = QLabel("Iniciando...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {AppTheme.TEXT_SECONDARY};
                font-size: {AppTheme.FONT_MEDIUM}px;
            }}
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def update_progress(self, value: int, status: str = ""):
        """Atualiza o progresso"""
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)

# ===============================================================================
# UTILITÁRIOS
# ===============================================================================

def apply_modern_style(app: QApplication):
    """Aplica o estilo moderno à aplicação"""
    app.setStyleSheet(AppTheme.get_stylesheet())
    
    # Fonte padrão
    font = QFont("Segoe UI", AppTheme.FONT_MEDIUM)
    app.setFont(font)

def create_icon_from_text(text: str, color: str = AppTheme.PRIMARY) -> QIcon:
    """Cria um ícone simples a partir de texto"""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Círculo de fundo
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, 24, 24)
    
    # Texto
    painter.setPen(QPen(QColor("white")))
    painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
    
    painter.end()
    
    return QIcon(pixmap)

def show_notification(parent, title: str, message: str, duration: int = 3000):
    """Exibe uma notificação temporária"""
    msg = ModernMessageBox(title, message, "info", parent)
    
    # Timer para fechar automaticamente
    QTimer.singleShot(duration, msg.close)
    
    msg.show()