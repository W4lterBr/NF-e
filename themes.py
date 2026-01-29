"""
Sistema de Temas para Busca NF-e
Autor: Sistema Busca NF-e
Data: 27/01/2026

Este módulo gerencia os temas visuais da aplicação.
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
import json
import os


class ThemeManager:
    """Gerenciador de temas da aplicação."""
    
    THEMES = {
        "Padrão": {
            "name": "Padrão",
            "description": "Tema claro padrão do sistema",
            "type": "light",
            "colors": {
                # Cores de fundo
                "window": "#f0f0f0",
                "base": "#ffffff",
                "alternate_base": "#f9f9f9",
                
                # Cores de texto
                "text": "#000000",
                "bright_text": "#ffffff",
                
                # Cores de destaque
                "highlight": "#0078d7",
                "highlight_text": "#ffffff",
                
                # Cores de botões
                "button": "#e1e1e1",
                "button_text": "#000000",
                
                # Cores de links
                "link": "#0066cc",
                "link_visited": "#551a8b",
                
                # Cores especiais
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
                "info": "#17a2b8",
                
                # Cores de status na tabela
                "status_autorizada": "#d6f5e0",  # Verde claro
                "status_cancelada": "#ffdcdc",   # Vermelho claro
                "status_outros": "#ebebeb",      # Cinza claro
            },
            "stylesheet": """
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QTableWidget {
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    gridline-color: #ededed;
                    background-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #e1e1e1;
                    padding: 5px;
                    border: 1px solid #d0d0d0;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #e1e1e1;
                    border: 1px solid #adadad;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #b0b0b0;
                }
                QLineEdit, QTextEdit, QSpinBox, QComboBox {
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 4px;
                    background-color: #ffffff;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #0078d7;
                }
                QGroupBox {
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QToolTip {
                    border: 1px solid #333;
                    padding: 4px;
                    border-radius: 3px;
                    background-color: #ffffcc;
                    color: #000000;
                }
            """
        },
        
        "Escuro": {
            "name": "Escuro",
            "description": "Tema escuro moderno para reduzir fadiga visual",
            "type": "dark",
            "colors": {
                "window": "#2b2b2b",
                "base": "#1e1e1e",
                "alternate_base": "#252526",
                
                "text": "#d4d4d4",
                "bright_text": "#ffffff",
                
                "highlight": "#0e639c",
                "highlight_text": "#ffffff",
                
                "button": "#3c3c3c",
                "button_text": "#e0e0e0",
                
                "link": "#3794ff",
                "link_visited": "#9b59b6",
                
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
                "info": "#2196f3",
                
                "status_autorizada": "#2d5016",
                "status_cancelada": "#5c1010",
                "status_outros": "#3a3a3a",
            },
            "stylesheet": """
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #d4d4d4;
                }
                QWidget {
                    color: #d4d4d4;
                }
                QTableWidget {
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    gridline-color: #3e3e42;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                QHeaderView::section {
                    background-color: #3c3c3c;
                    padding: 5px;
                    border: 1px solid #3e3e42;
                    font-weight: bold;
                    color: #e0e0e0;
                }
                QPushButton {
                    background-color: #0e639c;
                    border: 1px solid #0e639c;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-height: 20px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #0d5689;
                }
                QLineEdit, QTextEdit, QSpinBox, QComboBox {
                    border: 1px solid #3e3e42;
                    border-radius: 3px;
                    padding: 4px;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #0e639c;
                }
                QGroupBox {
                    border: 1px solid #3e3e42;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: bold;
                    color: #e0e0e0;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #d4d4d4;
                }
                QToolTip {
                    border: 1px solid #3e3e42;
                    padding: 4px;
                    border-radius: 3px;
                    background-color: #2b2b2b;
                    color: #d4d4d4;
                }
                QMenuBar {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                }
                QMenuBar::item:selected {
                    background-color: #0e639c;
                }
                QMenu {
                    background-color: #252526;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                }
                QMenu::item:selected {
                    background-color: #0e639c;
                }
                QTreeWidget {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: 1px solid #3e3e42;
                }
            """
        },
        
        "Azul Profissional": {
            "name": "Azul Profissional",
            "description": "Tema azul elegante para ambiente corporativo",
            "type": "light",
            "colors": {
                "window": "#f5f5f5",
                "base": "#ffffff",
                "alternate_base": "#fafafa",
                
                "text": "#000000",
                "bright_text": "#ffffff",
                
                "highlight": "#0078d7",
                "highlight_text": "#ffffff",
                
                "button": "#0078d7",
                "button_text": "#ffffff",
                
                "link": "#0066cc",
                "link_visited": "#551a8b",
                
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
                "info": "#0078d7",
                
                "status_autorizada": "#d6f5e0",
                "status_cancelada": "#ffdcdc",
                "status_outros": "#ebebeb",
            },
            "stylesheet": """
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QTableWidget {
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    gridline-color: #ededed;
                    background-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #0078d7;
                    padding: 5px;
                    border: 1px solid #0066b8;
                    font-weight: bold;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #0078d7;
                    border: 1px solid #0066b8;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-height: 20px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0063b1;
                }
                QPushButton:pressed {
                    background-color: #00518a;
                }
                QLineEdit, QTextEdit, QSpinBox, QComboBox {
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 4px;
                    background-color: #ffffff;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #0078d7;
                }
                QGroupBox {
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QToolTip {
                    border: 1px solid #333;
                    padding: 4px;
                    border-radius: 3px;
                    background-color: #ffffcc;
                    color: #000000;
                }
                QTreeWidget {
                    background-color: #ffffff;
                    border: 1px solid #d0d0d0;
                }
            """
        },
        
        "Verde Natureza": {
            "name": "Verde Natureza",
            "description": "Tema verde suave inspirado na natureza",
            "type": "light",
            "colors": {
                "window": "#e8f5e9",
                "base": "#ffffff",
                "alternate_base": "#f1f8f4",
                
                "text": "#1b5e20",
                "bright_text": "#ffffff",
                
                "highlight": "#4caf50",
                "highlight_text": "#ffffff",
                
                "button": "#c8e6c9",
                "button_text": "#1b5e20",
                
                "link": "#388e3c",
                "link_visited": "#1b5e20",
                
                "success": "#4caf50",
                "warning": "#ff9800",
                "error": "#f44336",
                "info": "#2196f3",
                
                "status_autorizada": "#a5d6a7",
                "status_cancelada": "#ffccbc",
                "status_outros": "#e0e0e0",
            },
            "stylesheet": """
                QMainWindow {
                    background-color: #e8f5e9;
                }
                QTableWidget {
                    border: 1px solid #81c784;
                    border-radius: 4px;
                    gridline-color: #c8e6c9;
                    background-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #4caf50;
                    padding: 5px;
                    border: 1px solid #388e3c;
                    font-weight: bold;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #4caf50;
                    border: 1px solid #388e3c;
                    border-radius: 4px;
                    padding: 5px 15px;
                    min-height: 20px;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #388e3c;
                }
                QLineEdit, QTextEdit, QSpinBox, QComboBox {
                    border: 1px solid #81c784;
                    border-radius: 3px;
                    padding: 4px;
                    background-color: #ffffff;
                }
                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #4caf50;
                }
                QGroupBox {
                    border: 2px solid #4caf50;
                    border-radius: 5px;
                    margin-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    color: #2e7d32;
                }
                QToolTip {
                    border: 1px solid #4caf50;
                    padding: 4px;
                    border-radius: 3px;
                    background-color: #f1f8f4;
                    color: #1b5e20;
                }
            """
        }
    }
    
    @staticmethod
    def get_config_path():
        """Retorna o caminho do arquivo de configuração de tema."""
        return os.path.join(os.path.dirname(__file__), "theme_config.json")
    
    @staticmethod
    def load_theme_preference():
        """Carrega a preferência de tema salva."""
        try:
            config_path = ThemeManager.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('theme', 'Padrão')
        except Exception as e:
            print(f"[THEME] Erro ao carregar preferência: {e}")
        return 'Padrão'
    
    @staticmethod
    def save_theme_preference(theme_name):
        """Salva a preferência de tema."""
        try:
            config_path = ThemeManager.get_config_path()
            config = {'theme': theme_name}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[THEME] Erro ao salvar preferência: {e}")
            return False
    
    @staticmethod
    def apply_theme(app, theme_name):
        """
        Aplica um tema à aplicação.
        
        Args:
            app: Instância do QApplication
            theme_name: Nome do tema a ser aplicado
            
        Returns:
            bool: True se o tema foi aplicado com sucesso
        """
        if theme_name not in ThemeManager.THEMES:
            print(f"[THEME] Tema '{theme_name}' não encontrado. Usando 'Padrão'.")
            theme_name = 'Padrão'
        
        theme = ThemeManager.THEMES[theme_name]
        
        try:
            # Aplica o stylesheet
            app.setStyleSheet(theme['stylesheet'])
            
            # Aplica a paleta de cores
            palette = QPalette()
            colors = theme['colors']
            
            # Cores principais
            palette.setColor(QPalette.Window, QColor(colors['window']))
            palette.setColor(QPalette.WindowText, QColor(colors['text']))
            palette.setColor(QPalette.Base, QColor(colors['base']))
            palette.setColor(QPalette.AlternateBase, QColor(colors['alternate_base']))
            palette.setColor(QPalette.Text, QColor(colors['text']))
            palette.setColor(QPalette.BrightText, QColor(colors['bright_text']))
            palette.setColor(QPalette.Button, QColor(colors['button']))
            palette.setColor(QPalette.ButtonText, QColor(colors['button_text']))
            palette.setColor(QPalette.Link, QColor(colors['link']))
            palette.setColor(QPalette.LinkVisited, QColor(colors['link_visited']))
            palette.setColor(QPalette.Highlight, QColor(colors['highlight']))
            palette.setColor(QPalette.HighlightedText, QColor(colors['highlight_text']))
            
            app.setPalette(palette)
            
            print(f"[THEME] ✅ Tema '{theme_name}' aplicado com sucesso!")
            return True
            
        except Exception as e:
            print(f"[THEME] ❌ Erro ao aplicar tema '{theme_name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_theme_names():
        """Retorna lista com os nomes de todos os temas disponíveis."""
        return list(ThemeManager.THEMES.keys())
    
    @staticmethod
    def get_theme_info(theme_name):
        """Retorna informações sobre um tema específico."""
        return ThemeManager.THEMES.get(theme_name, ThemeManager.THEMES['Padrão'])
    
    @staticmethod
    def get_status_colors(theme_name):
        """
        Retorna as cores de status da tabela para um tema específico.
        
        Returns:
            dict: Dicionário com cores para autorizada, cancelada e outros
        """
        theme = ThemeManager.THEMES.get(theme_name, ThemeManager.THEMES['Padrão'])
        colors = theme['colors']
        return {
            'autorizada': colors.get('status_autorizada', '#d6f5e0'),
            'cancelada': colors.get('status_cancelada', '#ffdcdc'),
            'outros': colors.get('status_outros', '#ebebeb')
        }
    
    @staticmethod
    def get_message_colors(theme_name):
        """
        Retorna as cores de mensagens de status para um tema específico.
        
        Returns:
            dict: Dicionário com cores para success, error, warning e info
        """
        theme = ThemeManager.THEMES.get(theme_name, ThemeManager.THEMES['Padrão'])
        colors = theme['colors']
        return {
            'success': colors.get('success', '#28a745'),
            'error': colors.get('error', '#dc3545'),
            'warning': colors.get('warning', '#ffc107'),
            'info': colors.get('info', '#17a2b8')
        }
