"""
Investiga de onde vêm as chaves que aparecem na interface
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
db_path = BASE_DIR / 'notas_test.db'

chaves = [
    "52260115045348000172570010014777191002562584",
    "52260115045348000172570010014777201002562593",
    "35251267452037000636570010000019781374379308"
]

print("=" * 80)
print("INVESTIGAÇÃO - De onde vêm essas chaves?")
print("=" * 80)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Lista todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = [row[0] for row in cursor.fetchall()]
print(f"\n📊 Tabelas no banco: {', '.join(tabelas)}")

for chave in chaves:
    print(f"\n🔍 Buscando chave: {chave}")
    
    # Procura em todas as tabelas
    for tabela in tabelas:
        try:
            # Pega colunas da tabela
            cursor.execute(f"PRAGMA table_info({tabela})")
            colunas = [col[1] for col in cursor.fetchall()]
            
            # Se tem coluna 'chave', procura
            if 'chave' in colunas:
                cursor.execute(f"SELECT * FROM {tabela} WHERE chave = ?", (chave,))
                rows = cursor.fetchall()
                if rows:
                    print(f"   ✅ Encontrado em '{tabela}': {len(rows)} registro(s)")
                    # Mostra primeiras colunas
                    if colunas:
                        print(f"      Colunas: {', '.join(colunas[:5])}...")
                        if rows[0]:
                            print(f"      Valores: {rows[0][:5]}...")
        except Exception as e:
            pass

conn.close()

print("\n" + "=" * 80)
print("Possibilidades:")
print("1. Chaves estão em outra tabela que alimenta a interface")
print("2. Interface carrega de arquivo cache/temporário")
print("3. Chaves vêm de consulta NSU que ainda não processou")
print("=" * 80)
