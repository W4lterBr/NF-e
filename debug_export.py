"""
Script para diagnosticar problema de export - verificar banco de dados e arquivos
"""

import sqlite3
from pathlib import Path
import sys

# Verifica se está rodando como executável
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
    DATA_DIR = Path.home() / 'AppData' / 'Local' / 'Busca_XML'
else:
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR

print("=" * 80)
print("DIAGNÓSTICO DO SISTEMA DE EXPORT")
print("=" * 80)

print(f"\n📁 BASE_DIR: {BASE_DIR}")
print(f"📁 DATA_DIR: {DATA_DIR}")

# Localiza o banco de dados
db_paths = [
    DATA_DIR / 'notas_test.db',
    BASE_DIR / 'notas_test.db'
]

db_path = None
for path in db_paths:
    if path.exists():
        db_path = path
        print(f"\n✅ Banco encontrado em: {db_path}")
        break

if not db_path:
    print("\n❌ ERRO: Banco de dados não encontrado!")
    sys.exit(1)

# Conecta ao banco
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Verifica tabelas
print("\n" + "=" * 80)
print("TABELAS NO BANCO")
print("=" * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
for table in tables:
    print(f"  • {table[0]}")

# Verifica xmls_baixados
print("\n" + "=" * 80)
print("TABELA: xmls_baixados")
print("=" * 80)

cursor.execute("SELECT COUNT(*) FROM xmls_baixados")
count = cursor.fetchone()[0]
print(f"Total de registros: {count}")

if count > 0:
    print("\nPrimeiros 5 registros:")
    cursor.execute("SELECT chave, cnpj_cpf, caminho_arquivo, baixado_em FROM xmls_baixados LIMIT 5")
    for row in cursor.fetchall():
        chave, cnpj, caminho, data = row
        print(f"\n  Chave: {chave}")
        print(f"  CNPJ: {cnpj}")
        print(f"  Caminho: {caminho}")
        print(f"  Data: {data}")
        if caminho:
            arquivo_existe = Path(caminho).exists()
            print(f"  Arquivo existe? {'✅ SIM' if arquivo_existe else '❌ NÃO'}")
else:
    print("⚠️ Tabela vazia!")

# Verifica notas_detalhadas
print("\n" + "=" * 80)
print("TABELA: notas_detalhadas")
print("=" * 80)

cursor.execute("SELECT COUNT(*) FROM notas_detalhadas")
count = cursor.fetchone()[0]
print(f"Total de registros: {count}")

if count > 0:
    print("\nPrimeiros 3 registros:")
    cursor.execute("SELECT chave, numero, nome_emitente, valor FROM notas_detalhadas LIMIT 3")
    for row in cursor.fetchall():
        chave, numero, nome, valor = row
        print(f"\n  Chave: {chave}")
        print(f"  Número: {numero}")
        print(f"  Emitente: {nome}")
        print(f"  Valor: R$ {valor}")

# Verifica estrutura de arquivos
print("\n" + "=" * 80)
print("ESTRUTURA DE ARQUIVOS")
print("=" * 80)

dirs_to_check = [
    DATA_DIR / 'xmls',
    BASE_DIR / 'xmls',
    BASE_DIR / 'xmls_chave',
    BASE_DIR / 'xml_extraidos',
    BASE_DIR / 'xml_NFs'
]

for dir_path in dirs_to_check:
    if dir_path.exists():
        xml_files = list(dir_path.rglob('*.xml'))
        # Filtra debug/protocolo
        xml_files = [f for f in xml_files if not any(x in f.name.lower() for x in ['debug', 'protocolo', 'request', 'response'])]
        print(f"\n📂 {dir_path}")
        print(f"   Total de XMLs: {len(xml_files)}")
        if xml_files:
            print(f"   Exemplo: {xml_files[0].name}")
    else:
        print(f"\n📂 {dir_path}")
        print(f"   ❌ Diretório não existe")

# Testa busca de uma chave específica
print("\n" + "=" * 80)
print("TESTE DE BUSCA")
print("=" * 80)

cursor.execute("SELECT chave FROM notas_detalhadas LIMIT 1")
row = cursor.fetchone()
if row:
    chave_teste = row[0]
    print(f"\nTestando busca para chave: {chave_teste}")
    
    # Busca no banco
    cursor.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave_teste,))
    result = cursor.fetchone()
    if result:
        print(f"✅ Encontrado no banco: {result[0]}")
    else:
        print(f"❌ NÃO encontrado no banco xmls_baixados")
    
    # Busca nos diretórios
    for dir_path in dirs_to_check:
        if dir_path.exists():
            arquivo = list(dir_path.rglob(f"{chave_teste}.xml"))
            if arquivo:
                print(f"✅ Encontrado em: {arquivo[0]}")

conn.close()

print("\n" + "=" * 80)
print("FIM DO DIAGNÓSTICO")
print("=" * 80)
