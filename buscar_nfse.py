import os
import sys
from pathlib import Path

# 🔧 Detecta diretório automaticamente (funciona em qualquer PC/instalação)
if getattr(sys, 'frozen', False):
    # Executável compilado (PyInstaller)
    if hasattr(sys, '_MEIPASS'):
        # Modo onefile
        base_dir = Path(sys._MEIPASS).parent
    else:
        # Modo onedir
        base_dir = Path(sys.executable).parent
else:
    # Modo desenvolvimento
    base_dir = Path(__file__).parent

# Ou usa pasta de dados do Windows (AppData)
# Melhor para dados persistentes entre instalações
import os
DATA_DIR = Path(os.getenv('APPDATA')) / 'Busca XML'
if DATA_DIR.exists() and (DATA_DIR / 'xmls').exists():
    base_dir = DATA_DIR
    print(f"📂 Usando pasta de dados: {base_dir}")
else:
    print(f"📂 Usando pasta local: {base_dir}")

chave = "31062001213891738000138240000000161624014871184399"

print(f"Procurando arquivos com chave: {chave}\n")

# Busca em todas as pastas
for pasta in ["xml_extraidos", "xmls", "xml_NFs", "xmls_nfce", "."]:
    pasta_path = base_dir / pasta
    if not pasta_path.exists():
        continue
    
    print(f"Buscando em: {pasta}")
    
    # Busca XML
    for xml_file in pasta_path.rglob(f"*{chave}*.xml"):
        print(f"  ✓ XML: {xml_file.relative_to(base_dir)}")
    
    # Busca PDF
    for pdf_file in pasta_path.rglob(f"*{chave}*.pdf"):
        print(f"  ✓ PDF: {pdf_file.relative_to(base_dir)}")

print("\n" + "="*70)
print("Buscando QUALQUER arquivo de NFS-e (primeiros 10):")

# Busca por padrão de nome
pastas_nfse = []
for pasta in ["xml_extraidos", "xmls", "xml_NFs"]:
    pasta_path = base_dir / pasta
    if pasta_path.exists():
        for item in pasta_path.rglob("*NFSe*"):
            if item.is_dir():
                pastas_nfse.append(item)
                print(f"  📁 Pasta: {item.relative_to(base_dir)}")

print("\n" + "="*70)
print("Conteúdo das pastas NFSe encontradas (primeiros 5 arquivos):")
for pasta in pastas_nfse[:3]:
    print(f"\n{pasta.relative_to(base_dir)}:")
    for idx, arquivo in enumerate(pasta.glob("*.*")):
        if idx >= 5:
            break
        print(f"  - {arquivo.name}")
