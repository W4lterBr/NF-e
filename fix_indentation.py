"""Script para remover código órfão entre GerenciadorTrabalhosDialog e CertificateDialog"""

# Ler o arquivo
with open('interface_pyqt5.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar os índices
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    # Procurar pelo closeEvent do Gerenciador
    if 'def closeEvent(self, event):' in line and start_idx is None and i > 3000:
        # Encontrar o final deste método (event.accept())
        for j in range(i, min(i+20, len(lines))):
            if 'event.accept()' in lines[j]:
                start_idx = j + 1  # Linha após event.accept()
                break
    
    # Procurar pelo CertificateDialog correto (com def __init__ e super().__init__)
    if 'class CertificateDialog(QDialog):' in line and i > 6000:
        # Verificar se a próxima função é def __init__ com super().__init__
        for j in range(i, min(i+5, len(lines))):
            if 'def __init__(self, db: UIDB, parent=None):' in lines[j]:
                if j+1 < len(lines) and 'super().__init__(parent)' in lines[j+1]:
                    end_idx = i
                    break
        if end_idx:
            break

print(f"Start index: {start_idx} (linha {start_idx+1 if start_idx else None})")
print(f"End index: {end_idx} (linha {end_idx+1 if end_idx else None})")

if start_idx and end_idx and start_idx < end_idx:
    # Criar novo arquivo sem as linhas órfãs
    new_lines = lines[:start_idx]
    new_lines.append('\n')
    new_lines.append('\n')
    new_lines.append('# ====== DIÁLOGOS DE CERTIFICADO ======\n')
    new_lines.append('\n')
    new_lines.extend(lines[end_idx:])
    
    # Salvar
    with open('interface_pyqt5.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ Arquivo corrigido! Removidas {end_idx - start_idx} linhas órfãs.")
    print(f"Novo total de linhas: {len(new_lines)}")
else:
    print("\n❌ Não foi possível encontrar os índices corretos.")
