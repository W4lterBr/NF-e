"""
Gerenciador de Tarefas Agendadas
Controla tarefas em background como busca automática
"""
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List
from PyQt5.QtCore import QTimer, QObject, pyqtSignal


class ScheduledTask(QObject):
    """Representa uma tarefa agendada"""
    
    # Sinais
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()
    progress = pyqtSignal(str)  # Mensagem de progresso
    
    def __init__(self, name: str, callback: Callable, delay_seconds: int):
        super().__init__()
        self.name = name
        self.callback = callback
        self.delay_seconds = delay_seconds
        self.created_at = datetime.now()
        self.scheduled_for = self.created_at + timedelta(seconds=delay_seconds)
        self.is_running = False
        self.is_cancelled = False
        self.timer = None
        
    def start(self):
        """Inicia o timer da tarefa"""
        if self.is_cancelled:
            return
            
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._execute)
        self.timer.start(self.delay_seconds * 1000)  # Converte para milissegundos
        print(f"[TASK] Agendada: {self.name} em {self.delay_seconds}s")
        
    def _execute(self):
        """Executa a tarefa"""
        if self.is_cancelled:
            return
            
        self.is_running = True
        self.started.emit()
        print(f"[TASK] Executando: {self.name}")
        
        try:
            self.callback()
            print(f"[TASK] Concluída: {self.name}")
        except Exception as e:
            print(f"[TASK] Erro em {self.name}: {e}")
        finally:
            self.is_running = False
            self.finished.emit()
    
    def cancel(self):
        """Cancela a tarefa"""
        self.is_cancelled = True
        if self.timer and self.timer.isActive():
            self.timer.stop()
        self.cancelled.emit()
        print(f"[TASK] Cancelada: {self.name}")
    
    def get_remaining_time(self) -> str:
        """Retorna tempo restante formatado"""
        if self.is_running:
            return "Em execução..."
        if self.is_cancelled:
            return "Cancelada"
            
        remaining = (self.scheduled_for - datetime.now()).total_seconds()
        if remaining <= 0:
            return "Aguardando..."
            
        minutes, seconds = divmod(int(remaining), 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class TaskScheduler(QObject):
    """Gerenciador de tarefas agendadas"""
    
    # Sinais
    task_added = pyqtSignal(object)  # ScheduledTask
    task_removed = pyqtSignal(str)   # task name
    
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, ScheduledTask] = {}
        
        # Timer para atualizar status das tarefas
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._cleanup_finished_tasks)
        self.update_timer.start(1000)  # Atualiza a cada segundo
    
    def schedule_task(self, name: str, callback: Callable, delay_seconds: int) -> ScheduledTask:
        """Agenda uma nova tarefa"""
        # Cancela tarefa existente com mesmo nome
        if name in self.tasks:
            self.tasks[name].cancel()
            
        task = ScheduledTask(name, callback, delay_seconds)
        task.finished.connect(lambda: self._on_task_finished(name))
        task.cancelled.connect(lambda: self._on_task_cancelled(name))
        
        self.tasks[name] = task
        task.start()
        self.task_added.emit(task)
        
        return task
    
    def cancel_task(self, name: str) -> bool:
        """Cancela uma tarefa agendada"""
        if name in self.tasks:
            self.tasks[name].cancel()
            return True
        return False
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Retorna uma tarefa pelo nome"""
        return self.tasks.get(name)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """Retorna todas as tarefas ativas"""
        return list(self.tasks.values())
    
    def has_pending_tasks(self) -> bool:
        """Verifica se há tarefas pendentes"""
        return any(not task.is_cancelled and not task.is_running 
                   for task in self.tasks.values())
    
    def _on_task_finished(self, name: str):
        """Callback quando tarefa termina"""
        print(f"[SCHEDULER] Tarefa finalizada: {name}")
    
    def _on_task_cancelled(self, name: str):
        """Callback quando tarefa é cancelada"""
        if name in self.tasks:
            del self.tasks[name]
            self.task_removed.emit(name)
    
    def _cleanup_finished_tasks(self):
        """Remove tarefas finalizadas antigas (mais de 1 minuto)"""
        to_remove = []
        for name, task in self.tasks.items():
            if not task.is_running and not task.timer.isActive():
                # Remove se finalizou há mais de 60 segundos
                elapsed = (datetime.now() - task.created_at).total_seconds()
                if elapsed > task.delay_seconds + 60:
                    to_remove.append(name)
        
        for name in to_remove:
            del self.tasks[name]
            self.task_removed.emit(name)
