"""
Verifica se as chaves específicas existem em disco
"""
import sqlite3
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR

chaves_testar = [
    "52260115045348000172570010014777191002562584",
    "52260115045348000172570010014777201002562593",
    "35251267452037000636570010000019781374379308"
]

print("=" * 80)
print("VERIFICAÇÃO DE CHAVES ESPECÍFICAS")
print("=" * 80)

# Busca em todos os diretórios
dirs_to_search = [
    BASE_DIR / 'xmls_chave',
    BASE_DIR / 'xmls',
    BASE_DIR / 'xml_extraidos',
    BASE_DIR / 'xml_NFs'
]

for chave in chaves_testar:
    print(f"\n🔍 Chave: {chave}")
    
    # Verifica no banco
    db_path = BASE_DIR / 'notas_test.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Em xmls_baixados
    cursor.execute("SELECT caminho_arquivo FROM xmls_baixados WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    if row:
        print(f"   ✅ Encontrado em xmls_baixados: {row[0]}")
    else:
        print(f"   ❌ NÃO encontrado em xmls_baixados")
    
    # Em notas_detalhadas
    cursor.execute("SELECT numero, nome_emitente, xml_status FROM notas_detalhadas WHERE chave = ?", (chave,))
    row = cursor.fetchone()
    if row:
        print(f"   ✅ Encontrado em notas_detalhadas: {row[0]} - {row[1]} - Status: {row[2]}")
    else:
        print(f"   ❌ NÃO encontrado em notas_detalhadas")
    
    conn.close()
    
    # Busca em disco
    found = False
    for dir_path in dirs_to_search:
        if dir_path.exists():
            # Busca exata
            arquivo = dir_path / f"{chave}.xml"
            if arquivo.exists():
                print(f"   ✅ Arquivo encontrado: {arquivo}")
                found = True
                break
            
            # Busca recursiva
            arquivos = list(dir_path.rglob(f"*{chave}*.xml"))
            if arquivos:
                for arq in arquivos:
                    print(f"   ✅ Arquivo encontrado: {arq}")
                found = True
                break
    
    if not found:
        print(f"   ❌ Arquivo NÃO encontrado em nenhum diretório")

print("\n" + "=" * 80)
print("FIM DA VERIFICAÇÃO")
print("=" * 80)
