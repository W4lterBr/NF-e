#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste rápido do submenu
"""

from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QActionGroup
import sys

app = QApplication(sys.argv)
win = QMainWindow()

# Menu principal
menu = win.menuBar().addMenu('Configurações')

# Adiciona algumas ações
act1 = QAction('Atualizar', win)
menu.addAction(act1)

menu.addSeparator()

# Submenu
submenu = menu.addMenu('⏱️ Intervalo de Busca Automática')
group = QActionGroup(win)
group.setExclusive(True)

for horas in [1, 2, 3, 4, 6, 8, 12]:
    act = QAction(f"{horas} {'hora' if horas == 1 else 'horas'}", win)
    act.setCheckable(True)
    if horas == 1:
        act.setChecked(True)
    group.addAction(act)
    submenu.addAction(act)

print(f'Submenu criado com {len(submenu.actions())} ações')
print('Ações no submenu:')
for act in submenu.actions():
    print(f'  - {act.text()}')

# Checkbox
menu.addSeparator()
act_check = QAction('✅ Consultar Status na SEFAZ', win)
act_check.setCheckable(True)
act_check.setChecked(True)
menu.addAction(act_check)

win.setWindowTitle('Teste de Menu')
win.resize(800, 600)
win.show()

print('\nJanela aberta. Verifique o menu "Configurações"')
print('Pressione Ctrl+C no terminal para fechar')

sys.exit(app.exec_())
