# modules/certificate_dialog.py
"""
Interface gráfica para gerenciamento de certificados digitais
"""

import os
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QInputDialog, QGroupBox,
    QHeaderView, QAbstractItemView, QFrame, QTextEdit,
    QProgressBar, QTabWidget, QWidget, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QPixmap, QIcon

from .qt_components import (
    ModernCard, ModernButton, AppTheme, StatusChip, 
    ModernMessageBox, ProgressDialog
)
from .certificate_manager import certificate_manager, CertificateInfo

class CertificateWorker(QThread):
    """Worker para operações de certificado em background"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    certificate_validated = pyqtSignal(bool, object)  # bool success, CertificateInfo
    
    def __init__(self, operation: str, **kwargs):
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs
    
    def run(self):
        try:
            if self.operation == "validate":
                self._validate_certificate()
            elif self.operation == "scan_directory":
                self._scan_directory()
            elif self.operation == "add_certificate":
                self._add_certificate()
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def _validate_certificate(self):
        file_path = self.kwargs.get('file_path')
        password = self.kwargs.get('password', '')
        
        self.progress.emit(25, "Carregando certificado...")
        is_valid, cert_info = certificate_manager.validate_certificate(file_path, password)
        
        self.progress.emit(75, "Validando informações...")
        self.certificate_validated.emit(is_valid, cert_info)
        
        self.progress.emit(100, "Concluído")
        self.finished.emit(is_valid, "Validação concluída" if is_valid else "Certificado inválido")
    
    def _scan_directory(self):
        directory = self.kwargs.get('directory')
        self.progress.emit(10, "Escaneando diretório...")
        
        cert_files = certificate_manager.scan_certificates_directory(directory)
        
        self.progress.emit(100, f"Encontrados {len(cert_files)} arquivos")
        self.finished.emit(True, f"Scan concluído: {len(cert_files)} certificados encontrados")
    
    def _add_certificate(self):
        file_path = self.kwargs.get('file_path')
        password = self.kwargs.get('password', '')
        alias = self.kwargs.get('alias', '')
        
        self.progress.emit(25, "Validando certificado...")
        
        # Primeiro valida o certificado
        is_valid, cert_info = certificate_manager.validate_certificate(file_path, password)
        
        if not is_valid:
            self.progress.emit(100, "Falha na validação")
            if not os.path.exists(file_path):
                self.finished.emit(False, "Arquivo de certificado não encontrado.")
            elif password == '':
                self.finished.emit(False, "Senha do certificado é obrigatória.")
            else:
                self.finished.emit(False, "Certificado inválido ou senha incorreta.\n\nVerifique:\n• Se o arquivo é um certificado .pfx/.p12 válido\n• Se a senha está correta\n• Se o certificado não está corrompido")
            return
        
        self.progress.emit(75, "Adicionando certificado...")
        success = certificate_manager.add_certificate(file_path, password, alias)
        
        self.progress.emit(100, "Concluído")
        if success:
            self.finished.emit(True, "Certificado adicionado com sucesso!")
        else:
            self.finished.emit(False, "Erro ao salvar certificado na configuração.")

class CertificateDetailsWidget(ModernCard):
    """Widget para exibir detalhes do certificado"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Título
        title = QLabel("Detalhes do Certificado")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_TITLE}px;
                font-weight: 600;
                color: {AppTheme.TEXT_PRIMARY};
                margin-bottom: {AppTheme.SPACING_MD}px;
            }}
        """)
        
        # Área de detalhes
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        self.details_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {AppTheme.SURFACE_VARIANT};
                border: 1px solid {AppTheme.BORDER_LIGHT};
                border-radius: {AppTheme.RADIUS_MD}px;
                padding: {AppTheme.SPACING_MD}px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: {AppTheme.FONT_SMALL}px;
            }}
        """)
        
        self.card_layout.addWidget(title)
        self.card_layout.addWidget(self.details_text)
    
    def update_details(self, cert_info: Optional[CertificateInfo]):
        if not cert_info:
            self.details_text.clear()
            return
        
        details = f"""
<b>Nome (CN):</b> {cert_info.cn}<br>
<b>CNPJ:</b> {cert_info.cnpj or 'N/A'}<br>
<b>CPF:</b> {cert_info.cpf or 'N/A'}<br>
<b>Emissor:</b> {cert_info.issuer_name}<br>
<b>Número de Série:</b> {cert_info.serial_number}<br>
<b>Válido de:</b> {cert_info.not_valid_before.strftime('%d/%m/%Y %H:%M')}<br>
<b>Válido até:</b> {cert_info.not_valid_after.strftime('%d/%m/%Y %H:%M')}<br>
<b>Status:</b> {'✅ Válido' if cert_info.is_valid else '❌ Expirado'}<br>
<b>Dias restantes:</b> {cert_info.days_until_expiry}<br>
<b>Fingerprint:</b> {cert_info.fingerprint[:32]}...
        """
        
        self.details_text.setHtml(details)

class CertificateDialog(QDialog):
    """Dialog principal para gerenciamento de certificados"""
    
    certificate_changed = pyqtSignal()  # Emitido quando certificados mudam
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciamento de Certificados Digitais")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        # Aplicar tema
        self.setStyleSheet(AppTheme.get_stylesheet())
        
        self.worker = None
        self.progress_dialog = None
        
        self.setup_ui()
        self.load_certificates()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(AppTheme.SPACING_LG)
        
        # Cabeçalho
        header_layout = QHBoxLayout()
        
        title = QLabel("Certificados Digitais")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {AppTheme.FONT_HEADLINE}px;
                font-weight: bold;
                color: {AppTheme.TEXT_PRIMARY};
            }}
        """)
        
        # Botões do cabeçalho
        self.add_cert_btn = ModernButton("Adicionar Certificado")
        self.add_cert_btn.clicked.connect(self.add_certificate)
        
        self.scan_btn = ModernButton("Escanear Pasta", variant="outline")
        self.scan_btn.clicked.connect(self.scan_directory)
        
        self.refresh_btn = ModernButton("Atualizar", variant="outline")
        self.refresh_btn.clicked.connect(self.load_certificates)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.scan_btn)
        header_layout.addWidget(self.add_cert_btn)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Conteúdo principal com tabs
        tabs = QTabWidget()
        
        # Tab 1: Lista de certificados
        certs_tab = QWidget()
        certs_layout = QVBoxLayout(certs_tab)
        
        # Tabela de certificados
        self.certs_table = QTableWidget()
        self.setup_certificates_table()
        certs_layout.addWidget(self.certs_table)
        
        # Botões de ação da tabela
        table_buttons = QHBoxLayout()
        
        self.set_active_btn = ModernButton("Definir como Ativo")
        self.set_active_btn.clicked.connect(self.set_active_certificate)
        self.set_active_btn.setEnabled(False)
        
        self.remove_btn = ModernButton("Remover", variant="outline")
        self.remove_btn.clicked.connect(self.remove_certificate)
        self.remove_btn.setEnabled(False)
        
        self.test_btn = ModernButton("Testar Senha", variant="outline")
        self.test_btn.clicked.connect(self.test_certificate)
        self.test_btn.setEnabled(False)
        
        table_buttons.addWidget(self.set_active_btn)
        table_buttons.addWidget(self.test_btn)
        table_buttons.addStretch()
        table_buttons.addWidget(self.remove_btn)
        
        certs_layout.addLayout(table_buttons)
        
        tabs.addTab(certs_tab, "Certificados")
        
        # Tab 2: Detalhes
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        
        self.details_widget = CertificateDetailsWidget()
        details_layout.addWidget(self.details_widget)
        
        tabs.addTab(details_tab, "Detalhes")
        
        layout.addWidget(tabs)
        
        # Rodapé
        footer_layout = QHBoxLayout()
        
        # Status do certificado ativo
        self.status_label = QLabel("Nenhum certificado ativo")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {AppTheme.TEXT_SECONDARY};
                font-size: {AppTheme.FONT_MEDIUM}px;
            }}
        """)
        
        # Botões finais
        self.close_btn = ModernButton("Fechar", variant="outline")
        self.close_btn.clicked.connect(self.accept)
        
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.close_btn)
        
        layout.addLayout(footer_layout)
        
        # Conectar seleção da tabela
        self.certs_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
    
    def setup_certificates_table(self):
        """Configura a tabela de certificados"""
        self.certs_table.setColumnCount(6)
        headers = ["Ativo", "Nome/Alias", "CNPJ/CPF", "Válido até", "Status", "Arquivo"]
        self.certs_table.setHorizontalHeaderLabels(headers)
        
        # Configurações da tabela
        self.certs_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.certs_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.certs_table.setAlternatingRowColors(True)
        
        # Ajustar colunas
        header = self.certs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Ativo
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nome
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # CNPJ
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Válido até
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Arquivo
        
        self.certs_table.setColumnWidth(0, 60)
    
    def load_certificates(self):
        """Carrega certificados na tabela"""
        certificates = certificate_manager.get_certificates()
        active_cert = certificate_manager.get_active_certificate()
        
        self.certs_table.setRowCount(len(certificates))
        
        for row, cert in enumerate(certificates):
            # Coluna 0: Ativo
            active_item = QTableWidgetItem("✓" if cert['file_path'] == certificate_manager.active_certificate else "")
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if cert['file_path'] == certificate_manager.active_certificate:
                # QTableWidgetItem não tem setStyleSheet, usar setForeground
                from PyQt6.QtGui import QColor
                active_item.setForeground(QColor(AppTheme.SUCCESS))
                # Para bold, usar setFont
                font = active_item.font()
                font.setBold(True)
                active_item.setFont(font)
            self.certs_table.setItem(row, 0, active_item)
            
            # Coluna 1: Nome/Alias
            name_item = QTableWidgetItem(cert.get('alias', cert.get('cn', 'Sem nome')))
            self.certs_table.setItem(row, 1, name_item)
            
            # Coluna 2: CNPJ/CPF
            doc = cert.get('cnpj') or cert.get('cpf') or 'N/A'
            if doc != 'N/A' and len(doc) == 14:
                doc = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
            elif doc != 'N/A' and len(doc) == 11:
                doc = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
            doc_item = QTableWidgetItem(doc)
            self.certs_table.setItem(row, 2, doc_item)
            
            # Coluna 3: Válido até
            try:
                expiry_date = datetime.fromisoformat(cert['not_valid_after'].replace('Z', '+00:00'))
                expiry_str = expiry_date.strftime('%d/%m/%Y')
            except:
                expiry_str = 'N/A'
            expiry_item = QTableWidgetItem(expiry_str)
            self.certs_table.setItem(row, 3, expiry_item)
            
            # Coluna 4: Status
            is_valid = cert.get('is_valid', False)
            days_left = cert.get('days_until_expiry', 0)
            
            if is_valid:
                if days_left > 30:
                    status = "✅ Válido"
                    color = AppTheme.SUCCESS
                elif days_left > 7:
                    status = f"⚠️ {days_left}d"
                    color = AppTheme.WARNING
                else:
                    status = f"🔶 {days_left}d"
                    color = AppTheme.ERROR
            else:
                status = "❌ Expirado"
                color = AppTheme.ERROR
            
            status_item = QTableWidgetItem(status)
            # Usar QColor para setForeground
            from PyQt6.QtGui import QColor
            status_item.setForeground(QColor(color))
            self.certs_table.setItem(row, 4, status_item)
            
            # Coluna 5: Arquivo
            file_path = cert['file_path']
            file_name = os.path.basename(file_path)
            file_item = QTableWidgetItem(file_name)
            file_item.setToolTip(file_path)
            self.certs_table.setItem(row, 5, file_item)
            
            # Armazenar dados do certificado na linha
            for col in range(6):
                item = self.certs_table.item(row, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, cert)
        
        # Atualizar status
        self.update_status_label()
    
    def update_status_label(self):
        """Atualiza label de status do certificado ativo"""
        active_cert = certificate_manager.get_active_certificate()
        
        if active_cert:
            alias = active_cert.get('alias', 'Certificado ativo')
            doc = active_cert.get('cnpj') or active_cert.get('cpf')
            if doc:
                if len(doc) == 14:
                    doc = f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
                elif len(doc) == 11:
                    doc = f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
                self.status_label.setText(f"Certificado ativo: {alias} ({doc})")
            else:
                self.status_label.setText(f"Certificado ativo: {alias}")
        else:
            self.status_label.setText("Nenhum certificado ativo")
    
    def on_selection_changed(self):
        """Chamado quando seleção da tabela muda"""
        selected_rows = self.certs_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        
        self.set_active_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        self.test_btn.setEnabled(has_selection)
        
        if has_selection:
            row = selected_rows[0].row()
            cert_data = self.certs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            
            # Carregar detalhes do certificado
            if cert_data:
                file_path = cert_data['file_path']
                password = cert_data.get('password', '')
                cert_info = certificate_manager.get_certificate_details(file_path, password)
                self.details_widget.update_details(cert_info)
        else:
            self.details_widget.update_details(None)
    
    def add_certificate(self):
        """Adiciona um novo certificado"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Certificado Digital",
            "",
            "Certificados (*.pfx *.p12);;Todos os arquivos (*)"
        )
        
        if not file_path:
            return
        
        # Solicitar senha
        password, ok = QInputDialog.getText(
            self,
            "Senha do Certificado",
            "Digite a senha do certificado:",
            QLineEdit.EchoMode.Password
        )
        
        if not ok:
            return
        
        # Solicitar alias (opcional)
        alias, ok = QInputDialog.getText(
            self,
            "Nome do Certificado",
            "Digite um nome para o certificado (opcional):"
        )
        
        if not ok:
            alias = ""
        
        # Validar e adicionar em background
        self.show_progress("Adicionando certificado...")
        
        self.worker = CertificateWorker(
            "add_certificate",
            file_path=file_path,
            password=password,
            alias=alias
        )
        self.worker.finished.connect(self.on_add_certificate_finished)
        self.worker.start()
    
    def on_add_certificate_finished(self, success: bool, message: str):
        """Callback para adição de certificado"""
        self.hide_progress()
        
        if success:
            self.load_certificates()
            self.certificate_changed.emit()
            ModernMessageBox("Sucesso", "Certificado adicionado com sucesso!", "info", self).exec()
        else:
            ModernMessageBox("Erro", f"Erro ao adicionar certificado:\n{message}", "error", self).exec()
    
    def remove_certificate(self):
        """Remove o certificado selecionado"""
        selected_rows = self.certs_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        cert_data = self.certs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if not cert_data:
            return
        
        # Confirmar remoção
        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Deseja remover o certificado '{cert_data.get('alias', 'Sem nome')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if certificate_manager.remove_certificate(cert_data['file_path']):
                self.load_certificates()
                self.certificate_changed.emit()
                ModernMessageBox("Sucesso", "Certificado removido com sucesso!", "info", self).exec()
            else:
                ModernMessageBox("Erro", "Erro ao remover certificado.", "error", self).exec()
    
    def set_active_certificate(self):
        """Define o certificado selecionado como ativo"""
        selected_rows = self.certs_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        cert_data = self.certs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if not cert_data:
            return
        
        if certificate_manager.set_active_certificate(cert_data['file_path']):
            self.load_certificates()
            self.certificate_changed.emit()
            ModernMessageBox("Sucesso", "Certificado definido como ativo!", "info", self).exec()
        else:
            ModernMessageBox("Erro", "Erro ao definir certificado ativo.", "error", self).exec()
    
    def test_certificate(self):
        """Testa a senha do certificado selecionado"""
        selected_rows = self.certs_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        cert_data = self.certs_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if not cert_data:
            return
        
        # Solicitar senha
        password, ok = QInputDialog.getText(
            self,
            "Testar Certificado",
            "Digite a senha do certificado:",
            QLineEdit.EchoMode.Password
        )
        
        if not ok:
            return
        
        # Testar em background
        self.show_progress("Testando certificado...")
        
        self.worker = CertificateWorker(
            "validate",
            file_path=cert_data['file_path'],
            password=password
        )
        self.worker.certificate_validated.connect(self.on_certificate_tested)
        self.worker.start()
    
    def on_certificate_tested(self, success: bool, cert_info):
        """Callback para teste de certificado"""
        self.hide_progress()
        
        if success and cert_info:
            ModernMessageBox(
                "Teste Bem-sucedido", 
                f"Certificado válido!\n\nNome: {cert_info.cn}\nCNPJ/CPF: {cert_info.cnpj or cert_info.cpf or 'N/A'}\nVálido até: {cert_info.not_valid_after.strftime('%d/%m/%Y')}", 
                "info", 
                self
            ).exec()
        else:
            ModernMessageBox("Teste Falhou", "Senha incorreta ou certificado inválido.", "error", self).exec()
    
    def scan_directory(self):
        """Escaneia um diretório em busca de certificados"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta para Escanear"
        )
        
        if not directory:
            return
        
        # Escanear em background
        self.show_progress("Escaneando pasta...")
        
        self.worker = CertificateWorker("scan_directory", directory=directory)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()
    
    def on_scan_finished(self, success: bool, message: str):
        """Callback para scan de diretório"""
        self.hide_progress()
        ModernMessageBox("Scan Concluído", message, "info", self).exec()
    
    def show_progress(self, message: str):
        """Mostra dialog de progresso"""
        if not self.progress_dialog:
            self.progress_dialog = ProgressDialog("Processando...", self)
        
        self.progress_dialog.update_progress(0, message)
        self.progress_dialog.show()
        
        if self.worker:
            self.worker.progress.connect(self.progress_dialog.update_progress)
    
    def hide_progress(self):
        """Esconde dialog de progresso"""
        if self.progress_dialog:
            self.progress_dialog.hide()
    
    def closeEvent(self, event):
        """Evento de fechamento"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()