# modules/qt_components_fixed.py
"""
Componentes modernos PyQt6 para o sistema NFe - VERSÃO CORRIGIDA
Design Material Design 3 com widgets nativos e tema moderno
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
    QSizePolicy, QSpacerItem, QFileDialog,
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
    
    # Cores principais (tema moderno)
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
    
    # Fundo e superfícies
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

class StatusChip(QLabel):
    """Chip de status colorido"""
    
    def __init__(self, text: str, color: str = AppTheme.PRIMARY, parent=None):
        super().__init__(text, parent)
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: {AppTheme.RADIUS_SM}px;
                padding: {AppTheme.SPACING_XS}px {AppTheme.SPACING_SM}px;
                font-size: {AppTheme.FONT_SMALL}px;
                font-weight: 500;
            }}
        """)
        
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

class SearchField(QLineEdit):
    """Campo de busca simples sem ícone SVG"""
    
    def __init__(self, placeholder: str = "Buscar...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(f"🔍 {placeholder}")
        
        # Estilo customizado sem background-image SVG
        self.setStyleSheet(f"""
            QLineEdit {{
                padding-left: {AppTheme.SPACING_MD}px;
                padding-right: {AppTheme.SPACING_MD}px;
                border: 2px solid {AppTheme.BORDER_LIGHT};
                border-radius: {AppTheme.RADIUS_MD}px;
                background-color: {AppTheme.SURFACE};
                color: {AppTheme.TEXT_PRIMARY};
                font-size: {AppTheme.FONT_MEDIUM}px;
                min-height: 32px;
            }}
            QLineEdit:focus {{
                border-color: {AppTheme.PRIMARY};
            }}
            QLineEdit:hover {{
                border-color: {AppTheme.BORDER_MEDIUM};
            }}
        """)

class ModernTable(QTableWidget):
    """Tabela moderna com estilo Material Design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurações modernas
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        
        # Altura das linhas
        self.verticalHeader().setDefaultSectionSize(48)

class StatsCard(ModernCard):
    """Card de estatística com ícone e valor"""
    
    def __init__(self, title: str, value: str, icon: Optional[QIcon] = None,
                 color: str = AppTheme.PRIMARY, parent=None):
        super().__init__(parent)
        
        # Layout horizontal
        layout = QHBoxLayout()
        
        # Ícone
        if icon:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(40, 40))
            icon_label.setFixedSize(48, 48)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    border-radius: 24px;
                }}
            """)
            layout.addWidget(icon_label)
        
        # Conteúdo
        content_layout = QVBoxLayout()
        content_layout.setSpacing(AppTheme.SPACING_XS)
        
        # Valor
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_HEADLINE}px;
                font-weight: bold;
                color: {AppTheme.TEXT_PRIMARY};
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
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        # Container widget
        container = QWidget()
        container.setLayout(layout)
        self.card_layout.addWidget(container)
        
        # Guarda referências
        self.value_label = value_label
        self.title_label = title_label
    
    def update_value(self, value: str):
        """Atualiza o valor do card"""
        self.value_label.setText(value)

class FilterPanel(ModernCard):
    """Painel de filtros avançados"""
    
    filters_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Título
        title = QLabel("Filtros de Busca")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_TITLE}px;
                font-weight: 600;
                color: {AppTheme.TEXT_PRIMARY};
                margin-bottom: {AppTheme.SPACING_SM}px;
            }}
        """)
        
        self.card_layout.addWidget(title)

class ModernMessageBox:
    """MessageBox moderno personalizado"""
    
    def __init__(self, title: str, message: str, icon_type: str = "info", parent=None):
        self.dialog = QMessageBox(parent)
        self.dialog.setWindowTitle(title)
        self.dialog.setText(message)
        
        # Define ícone baseado no tipo
        if icon_type == "error":
            self.dialog.setIcon(QMessageBox.Icon.Critical)
        elif icon_type == "warning":
            self.dialog.setIcon(QMessageBox.Icon.Warning)
        elif icon_type == "question":
            self.dialog.setIcon(QMessageBox.Icon.Question)
        else:
            self.dialog.setIcon(QMessageBox.Icon.Information)
    
    def exec(self):
        """Executa o dialog"""
        return self.dialog.exec()

class ProgressDialog(QWidget):
    """Dialog de progresso moderno"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle(title)
        self.setFixedSize(400, 120)
        
        layout = QVBoxLayout(self)
        
        # Título
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Preparando...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
    
    def update_progress(self, value: int, status: str):
        """Atualiza o progresso"""
        self.progress_bar.setValue(value)
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
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Círculo de fundo
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, 32, 32)
    
    # Texto
    painter.setPen(QPen(QColor("white")))
    painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
    
    painter.end()
    return QIcon(pixmap)

def show_notification(parent, title: str, message: str, duration: int = 3000):
    """Mostra uma notificação usando QMessageBox nativo"""
    try:
        QMessageBox.information(parent, title, message)
    except Exception as e:
        print(f"Erro ao mostrar notificação: {e}")
        print(f"Notificação: {title} - {message}")