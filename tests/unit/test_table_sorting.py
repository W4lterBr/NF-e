import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, 
                              QTableWidgetItem, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    """Item de tabela que ordena numericamente em vez de alfabeticamente"""
    def __init__(self, text: str, numeric_value: float = 0.0):
        super().__init__(text)
        self._numeric_value = numeric_value
        self.setData(Qt.UserRole, numeric_value)
    
    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            print(f"Comparando {self.text()} ({self._numeric_value}) < {other.text()} ({other._numeric_value}) = {self._numeric_value < other._numeric_value}")
            return self._numeric_value < other._numeric_value
        try:
            self_val = self.data(Qt.UserRole)
            other_val = other.data(Qt.UserRole)
            if self_val is not None and other_val is not None:
                print(f"Comparando via UserRole: {self_val} < {other_val}")
                return float(self_val) < float(other_val)
        except Exception as e:
            print(f"Erro na comparação: {e}")
        return super().__lt__(other)

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teste de Ordenação Numérica")
        self.setGeometry(100, 100, 600, 400)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Texto", "Valor"])
        self.table.setSortingEnabled(True)
        
        # Dados de teste
        valores = [
            ("R$ 1.254,00", 1254.0),
            ("R$ 140,44", 140.44),
            ("R$ 17,60", 17.60),
            ("R$ 1.140,00", 1140.0),
            ("R$ 158,00", 158.0),
        ]
        
        self.table.setRowCount(len(valores))
        self.table.setSortingEnabled(False)  # Desabilita durante preenchimento
        
        for row, (texto, valor) in enumerate(valores):
            # Coluna de texto normal
            self.table.setItem(row, 0, QTableWidgetItem(texto))
            # Coluna com ordenação numérica
            item = NumericTableWidgetItem(texto, valor)
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 1, item)
        
        self.table.setSortingEnabled(True)  # Reabilita após preenchimento
        print(f"Sorting habilitado: {self.table.isSortingEnabled()}")
        
        layout.addWidget(self.table)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
