from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, numeric_value=0.0):
        super().__init__(text)
        self._numeric_value = numeric_value
    
    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            print(f"Comparando {self._numeric_value} < {other._numeric_value} = {self._numeric_value < other._numeric_value}")
            return self._numeric_value < other._numeric_value
        return super().__lt__(other)

# Teste
item1 = NumericTableWidgetItem('R$ 1.254,00', 1254.0)
item2 = NumericTableWidgetItem('R$ 140,44', 140.44)
item3 = NumericTableWidgetItem('R$ 17,60', 17.60)

print('Teste de comparação:')
print(f'17.60 < 140.44: {item3 < item2}')
print(f'140.44 < 1254.0: {item2 < item1}')
print(f'Valores: {item3._numeric_value}, {item2._numeric_value}, {item1._numeric_value}')
print('\nOrdenação simulada:')
items = [item1, item2, item3]
sorted_items = sorted(items)
for item in sorted_items:
    print(f'{item.text()} -> {item._numeric_value}')
