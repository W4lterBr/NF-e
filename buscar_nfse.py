import os
from pathlib import Path

chave = "31062001213891738000138240000000161624014871184399"

# Busca recursivamente pelo arquivo
base_dir = Path(r"c:\Users\Nasci\OneDrive\Documents\Programas VS Code\BOT - Busca NFE")

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
