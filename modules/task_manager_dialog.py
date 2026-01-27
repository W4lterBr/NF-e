"""
Janela de Gerenciamento de Tarefas Agendadas
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
from modules.task_scheduler import TaskScheduler


class TaskManagerDialog(QDialog):
    """Janela para gerenciar tarefas agendadas"""
    
    def __init__(self, scheduler: TaskScheduler, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.setWindowTitle("Gerenciador de Tarefas Agendadas")
        self.setMinimumSize(700, 400)
        self.setup_ui()
        
        # Timer para atualizar a tabela
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_table)
        self.update_timer.start(1000)  # Atualiza a cada segundo
        
        # Conecta sinais do scheduler
        self.scheduler.task_added.connect(self.refresh_table)
        self.scheduler.task_removed.connect(self.refresh_table)
        
        self.refresh_table()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Cabeçalho
        header = QLabel("Tarefas Agendadas e em Execução")
        header.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(header)
        
        # Tabela de tarefas
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Tarefa", "Agendada Para", "Tempo Restante", "Status"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        layout.addWidget(self.table)
        
        # Informação
        info_label = QLabel(
            "💡 As tarefas são executadas automaticamente no horário agendado.\n"
            "   Você pode cancelar uma tarefa selecionando-a e clicando em 'Cancelar Tarefa'."
        )
        info_label.setStyleSheet("color: #666; margin: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("🔄 Atualizar")
        self.btn_refresh.clicked.connect(self.refresh_table)
        btn_layout.addWidget(self.btn_refresh)
        
        self.btn_cancel = QPushButton("❌ Cancelar Tarefa")
        self.btn_cancel.clicked.connect(self.cancel_selected_task)
        btn_layout.addWidget(self.btn_cancel)
        
        btn_layout.addStretch()
        
        self.btn_close = QPushButton("Fechar")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def refresh_table(self):
        """Atualiza a tabela com as tarefas atuais"""
        tasks = self.scheduler.get_all_tasks()
        self.table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # Nome
            self.table.setItem(row, 0, QTableWidgetItem(task.name))
            
            # Agendada para
            scheduled_time = task.scheduled_for.strftime("%d/%m/%Y %H:%M:%S")
            self.table.setItem(row, 1, QTableWidgetItem(scheduled_time))
            
            # Tempo restante
            remaining = task.get_remaining_time()
            self.table.setItem(row, 2, QTableWidgetItem(remaining))
            
            # Status
            if task.is_running:
                status = "▶️ Em execução"
            elif task.is_cancelled:
                status = "❌ Cancelada"
            else:
                status = "⏱️ Agendada"
            self.table.setItem(row, 3, QTableWidgetItem(status))
            
            # Armazena referência à tarefa
            self.table.item(row, 0).setData(Qt.UserRole, task.name)
    
    def cancel_selected_task(self):
        """Cancela a tarefa selecionada"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self,
                "Nenhuma tarefa selecionada",
                "Por favor, selecione uma tarefa para cancelar."
            )
            return
        
        task_name = self.table.item(current_row, 0).data(Qt.UserRole)
        task = self.scheduler.get_task(task_name)
        
        if task and not task.is_cancelled:
            reply = QMessageBox.question(
                self,
                "Confirmar Cancelamento",
                f"Deseja cancelar a tarefa '{task.name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.scheduler.cancel_task(task_name)
                QMessageBox.information(
                    self,
                    "Tarefa Cancelada",
                    f"A tarefa '{task.name}' foi cancelada com sucesso."
                )
                self.refresh_table()
        else:
            QMessageBox.information(
                self,
                "Tarefa já cancelada",
                "Esta tarefa já foi cancelada."
            )
    
    def closeEvent(self, event):
        """Para o timer ao fechar"""
        self.update_timer.stop()
        super().closeEvent(event)
