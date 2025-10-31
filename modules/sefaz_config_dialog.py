# modules/sefaz_config_dialog.py
"""
Diálogo para configuração de certificados SEFAZ
Interface para ativar/desativar certificados e configurar UF
"""

import logging
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QCheckBox, QGroupBox, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from .qt_components import ModernButton, ModernCard, AppTheme
from .sefaz_integration import SefazCertificateAdapter

logger = logging.getLogger(__name__)

class SefazSyncWorker(QThread):
    """Worker thread para sincronização de certificados"""
    
    sync_completed = pyqtSignal(bool, int, str)  # success, count, message
    
    def __init__(self):
        super().__init__()
        self.adapter = SefazCertificateAdapter()
    
    def run(self):
        try:
            count = self.adapter.sync_certificates_from_manager()
            self.sync_completed.emit(True, count, f"Sincronizados {count} certificados")
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            self.sync_completed.emit(False, 0, f"Erro: {str(e)}")

class SefazConfigDialog(QDialog):
    """Diálogo para configuração de certificados SEFAZ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.adapter = SefazCertificateAdapter()
        self.certificates_data: List[Dict[str, Any]] = []
        
        self.setWindowTitle("Configuração SEFAZ - Certificados")
        self.setModal(True)
        self.resize(800, 600)
        
        # Aplicar tema
        theme = AppTheme()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.colors['surface']};
                color: {theme.colors['on_surface']};
            }}
        """)
        
        self.setup_ui()
        self.load_certificates()
    
    def setup_ui(self):
        """Configura a interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Título
        title = QLabel("Configuração de Certificados SEFAZ")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {AppTheme().colors['primary']};
            margin-bottom: 8px;
        """)
        layout.addWidget(title)
        
        # Card principal
        main_card = ModernCard()
        card_layout = QVBoxLayout(main_card)
        
        # Informações
        info_label = QLabel(
            "Configure quais certificados serão utilizados nas consultas SEFAZ.\n"
            "Apenas certificados ativos participarão das buscas automáticas."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 16px;")
        card_layout.addWidget(info_label)
        
        # Botões de ação
        actions_layout = QHBoxLayout()
        
        self.sync_btn = ModernButton("🔄 Sincronizar Certificados")
        self.sync_btn.clicked.connect(self.sync_certificates)
        actions_layout.addWidget(self.sync_btn)
        
        actions_layout.addStretch()
        
        self.refresh_btn = ModernButton("⟳ Atualizar")
        self.refresh_btn.clicked.connect(self.load_certificates)
        actions_layout.addWidget(self.refresh_btn)
        
        card_layout.addLayout(actions_layout)
        
        # Tabela de certificados
        self.setup_certificates_table()
        card_layout.addWidget(self.certificates_table)
        
        layout.addWidget(main_card)
        
        # Botões de controle
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = ModernButton("Fechar")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
    
    def setup_certificates_table(self):
        """Configura a tabela de certificados"""
        self.certificates_table = QTableWidget()
        self.certificates_table.setColumnCount(6)
        self.certificates_table.setHorizontalHeaderLabels([
            "CNPJ/CPF", "Nome do Certificado", "Validade", "Status", "UF", "Ações"
        ])
        
        # Configurar header
        header = self.certificates_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # CNPJ
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nome
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Validade
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # UF
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Ações
        
        # Estilo da tabela
        theme = AppTheme()
        self.certificates_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.colors['surface']};
                alternate-background-color: {theme.colors['surface_variant']};
                gridline-color: {theme.colors['outline']};
                border: 1px solid {theme.colors['outline']};
                border-radius: 8px;
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {theme.colors['primary_container']};
                color: {theme.colors['on_primary_container']};
            }}
            QHeaderView::section {{
                background-color: {theme.colors['surface_variant']};
                color: {theme.colors['on_surface_variant']};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
        """)
        
        self.certificates_table.setAlternatingRowColors(True)
        self.certificates_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.certificates_table.verticalHeader().setVisible(False)
    
    def load_certificates(self):
        """Carrega os certificados na tabela"""
        try:
            self.certificates_data = self.adapter.get_active_certificates_info()
            self.populate_table()
        except Exception as e:
            logger.error(f"Erro ao carregar certificados: {e}")
            QMessageBox.warning(self, "Erro", f"Erro ao carregar certificados:\n{str(e)}")
    
    def populate_table(self):
        """Popula a tabela com dados dos certificados"""
        self.certificates_table.setRowCount(len(self.certificates_data))
        
        for row, cert_data in enumerate(self.certificates_data):
            # CNPJ/CPF
            cnpj_item = QTableWidgetItem(cert_data['cnpj_cpf'])
            cnpj_item.setFlags(cnpj_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.certificates_table.setItem(row, 0, cnpj_item)
            
            # Nome do certificado
            name_item = QTableWidgetItem(cert_data['subject_name'][:50] + "..." if len(cert_data['subject_name']) > 50 else cert_data['subject_name'])
            name_item.setToolTip(cert_data['subject_name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.certificates_table.setItem(row, 1, name_item)
            
            # Validade
            validade = cert_data['valid_until'][:10] if cert_data['valid_until'] else 'N/A'
            days_left = cert_data.get('days_until_expiry', 0)
            
            validade_item = QTableWidgetItem(f"{validade}\n({days_left} dias)")
            validade_item.setFlags(validade_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Colorir conforme proximidade do vencimento
            if days_left <= 30:
                validade_item.setForeground(QColor("#d32f2f"))  # Vermelho
            elif days_left <= 90:
                validade_item.setForeground(QColor("#f57c00"))  # Laranja
            else:
                validade_item.setForeground(QColor("#388e3c"))  # Verde
            
            self.certificates_table.setItem(row, 2, validade_item)
            
            # Status (checkbox)
            status_widget = QCheckBox()
            status_widget.setChecked(cert_data['is_active'])
            status_widget.stateChanged.connect(
                lambda state, cnpj=cert_data['cnpj_cpf']: self.toggle_certificate(cnpj, state == Qt.CheckState.Checked.value)
            )
            self.certificates_table.setCellWidget(row, 3, status_widget)
            
            # UF (combobox)
            uf_combo = QComboBox()
            ufs = [
                ("43", "RS - Rio Grande do Sul"),
                ("35", "SP - São Paulo"),
                ("33", "RJ - Rio de Janeiro"),
                ("31", "MG - Minas Gerais"),
                ("41", "PR - Paraná"),
                ("42", "SC - Santa Catarina"),
                ("50", "MS - Mato Grosso do Sul"),
                ("51", "MT - Mato Grosso"),
                ("52", "GO - Goiás"),
                ("53", "DF - Distrito Federal"),
                ("21", "MA - Maranhão"),
                ("22", "PI - Piauí"),
                ("23", "CE - Ceará"),
                ("24", "RN - Rio Grande do Norte"),
                ("25", "PB - Paraíba"),
                ("26", "PE - Pernambuco"),
                ("27", "AL - Alagoas"),
                ("28", "SE - Sergipe"),
                ("29", "BA - Bahia"),
                ("11", "RO - Rondônia"),
                ("12", "AC - Acre"),
                ("13", "AM - Amazonas"),
                ("14", "RR - Roraima"),
                ("15", "PA - Pará"),
                ("16", "AP - Amapá"),
                ("17", "TO - Tocantins"),
                ("32", "ES - Espírito Santo"),
                ("91", "AN - Ambiente Nacional")
            ]
            
            for codigo, nome in ufs:
                uf_combo.addItem(nome, codigo)
            
            # Define UF padrão como RS
            uf_combo.setCurrentText("RS - Rio Grande do Sul")
            
            uf_combo.currentTextChanged.connect(
                lambda text, cnpj=cert_data['cnpj_cpf']: self.change_certificate_uf(cnpj, text)
            )
            self.certificates_table.setCellWidget(row, 4, uf_combo)
            
            # Ações (botão remover)
            remove_btn = QPushButton("🗑️ Remover")
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            remove_btn.clicked.connect(
                lambda checked, cnpj=cert_data['cnpj_cpf']: self.remove_certificate(cnpj)
            )
            self.certificates_table.setCellWidget(row, 5, remove_btn)
    
    def sync_certificates(self):
        """Sincroniza certificados do gerenciador"""
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("🔄 Sincronizando...")
        
        self.sync_worker = SefazSyncWorker()
        self.sync_worker.sync_completed.connect(self.on_sync_completed)
        self.sync_worker.start()
    
    def on_sync_completed(self, success: bool, count: int, message: str):
        """Callback da sincronização"""
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("🔄 Sincronizar Certificados")
        
        if success:
            QMessageBox.information(self, "Sucesso", message)
            self.load_certificates()
        else:
            QMessageBox.warning(self, "Erro", message)
    
    def toggle_certificate(self, cnpj_cpf: str, active: bool):
        """Ativa/desativa um certificado"""
        try:
            success = self.adapter.toggle_certificate(cnpj_cpf, active)
            if not success:
                QMessageBox.warning(self, "Erro", f"Erro ao alterar status do certificado {cnpj_cpf}")
                self.load_certificates()  # Recarrega para reverter
        except Exception as e:
            logger.error(f"Erro ao alterar certificado: {e}")
            QMessageBox.warning(self, "Erro", f"Erro: {str(e)}")
            self.load_certificates()
    
    def change_certificate_uf(self, cnpj_cpf: str, uf_text: str):
        """Altera a UF de um certificado"""
        try:
            # Extrai código da UF do texto
            uf_code = uf_text.split(" - ")[0] if " - " in uf_text else "43"
            success = self.adapter.configure_certificate_uf(cnpj_cpf, uf_code)
            if not success:
                QMessageBox.warning(self, "Erro", f"Erro ao alterar UF do certificado {cnpj_cpf}")
        except Exception as e:
            logger.error(f"Erro ao alterar UF: {e}")
            QMessageBox.warning(self, "Erro", f"Erro: {str(e)}")
    
    def remove_certificate(self, cnpj_cpf: str):
        """Remove um certificado"""
        reply = QMessageBox.question(
            self, "Confirmar Remoção",
            f"Deseja remover o certificado {cnpj_cpf} da configuração SEFAZ?\n"
            "Esta ação não afeta o arquivo do certificado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.adapter.remove_certificate(cnpj_cpf)
                if success:
                    QMessageBox.information(self, "Sucesso", f"Certificado {cnpj_cpf} removido")
                    self.load_certificates()
                else:
                    QMessageBox.warning(self, "Erro", f"Erro ao remover certificado {cnpj_cpf}")
            except Exception as e:
                logger.error(f"Erro ao remover certificado: {e}")
                QMessageBox.warning(self, "Erro", f"Erro: {str(e)}")