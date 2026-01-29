"""
Script para popular a tabela xmls_baixados com os XMLs já existentes no disco
"""

import sqlite3
from pathlib import Path
import sys
import re

# Verifica se está rodando como executável
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    DATA_DIR = Path.home() / 'AppData' / 'Local' / 'Busca_XML'
else:
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR

print("=" * 80)
print("CORREÇÃO DO BANCO DE DADOS - xmls_baixados")
print("=" * 80)

# Localiza o banco de dados
db_path = DATA_DIR / 'notas_test.db'
if not db_path.exists():
    db_path = BASE_DIR / 'notas_test.db'

print(f"\n📁 Banco de dados: {db_path}")

# Conecta ao banco
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Verifica situação atual
cursor.execute("SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL")
count_com_caminho = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM xmls_baixados")
count_total = cursor.fetchone()[0]

print(f"\n📊 Situação atual:")
print(f"   Total de registros: {count_total}")
print(f"   Com caminho: {count_com_caminho}")
print(f"   Sem caminho: {count_total - count_com_caminho}")

# Busca XMLs nos diretórios
dirs_to_search = [
    BASE_DIR / 'xmls_chave',
    BASE_DIR / 'xmls',
    BASE_DIR / 'xml_extraidos',
    BASE_DIR / 'xml_NFs'
]

# Padrão de chave de 44 dígitos
chave_pattern = re.compile(r'\d{44}')

print(f"\n🔍 Buscando XMLs...")
xml_files = []
for dir_path in dirs_to_search:
    if dir_path.exists():
        files = list(dir_path.rglob('*.xml'))
        # Filtra debug/protocolo
        files = [f for f in files if not any(x in f.name.lower() for x in ['debug', 'protocolo', 'request', 'response'])]
        xml_files.extend(files)
        print(f"   {dir_path.name}: {len(files)} arquivos")

print(f"\n📄 Total de XMLs encontrados: {len(xml_files)}")

# Extrai chaves dos nomes dos arquivos
chaves_encontradas = {}
for xml_file in xml_files:
    # Tenta extrair chave do nome do arquivo
    match = chave_pattern.search(xml_file.stem)
    if match:
        chave = match.group()
        if chave not in chaves_encontradas:
            chaves_encontradas[chave] = str(xml_file.absolute())

print(f"\n🔑 Chaves únicas extraídas: {len(chaves_encontradas)}")

# Atualiza o banco de dados
print(f"\n💾 Atualizando banco de dados...")
updated = 0
inserted = 0

for chave, caminho in chaves_encontradas.items():
    # Verifica se já existe no banco
    cursor.execute("SELECT rowid, caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    
    if row:
        # Atualiza se não tem caminho
        if not row[1]:
            cursor.execute(
                "UPDATE xmls_baixados SET caminho_arquivo = ? WHERE rowid = ?",
                (caminho, row[0])
            )
            updated += 1
    else:
        # Insere novo registro
        # Tenta buscar CNPJ da nota detalhada
        cursor.execute("SELECT cnpj_emitente FROM notas_detalhadas WHERE chave = ?", (chave,))
        nota_row = cursor.fetchone()
        cnpj = nota_row[0] if nota_row else None
        
        cursor.execute(
            "INSERT INTO xmls_baixados (chave, cnpj_cpf, caminho_arquivo) VALUES (?, ?, ?)",
            (chave, cnpj, caminho)
        )
        inserted += 1

conn.commit()

print(f"   ✅ Atualizados: {updated}")
print(f"   ✅ Inseridos: {inserted}")

# Verifica situação final
cursor.execute("SELECT COUNT(*) FROM xmls_baixados WHERE caminho_arquivo IS NOT NULL")
count_com_caminho = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM xmls_baixados")
count_total = cursor.fetchone()[0]

print(f"\n📊 Situação final:")
print(f"   Total de registros: {count_total}")
print(f"   Com caminho: {count_com_caminho}")
print(f"   Sem caminho: {count_total - count_com_caminho}")

conn.close()

print("\n" + "=" * 80)
print("✅ CORREÇÃO CONCLUÍDA")
print("=" * 80)
