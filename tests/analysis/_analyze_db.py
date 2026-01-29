import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

db_path = Path(r"C:\Users\Nasci\AppData\Roaming\Busca XML\notas.db")

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

print("=" * 60)
print("ANÁLISE DO BANCO DE DADOS")
print("=" * 60)

# XMLs baixados hoje
today = datetime.now().strftime("%Y-%m-%d")
cur.execute("SELECT COUNT(*) FROM xmls_baixados WHERE data_download >= ?", (today,))
count_today = cur.fetchone()[0]
print(f"\n✅ XMLs baixados HOJE ({today}): {count_today}")

# XMLs baixados nos últimos 7 dias
week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
cur.execute("SELECT COUNT(*) FROM xmls_baixados WHERE data_download >= ?", (week_ago,))
count_week = cur.fetchone()[0]
print(f"📊 XMLs baixados últimos 7 dias: {count_week}")

# Total de XMLs
cur.execute("SELECT COUNT(*) FROM xmls_baixados")
total_xmls = cur.fetchone()[0]
print(f"📦 Total de XMLs baixados: {total_xmls}")

# Notas detalhadas
cur.execute("SELECT COUNT(*) FROM notas_detalhadas")
total_notas = cur.fetchone()[0]
print(f"📋 Notas detalhadas no banco: {total_notas}")

# Últimos 5 XMLs baixados
print(f"\n{'=' * 60}")
print("ÚLTIMOS 5 XMLs BAIXADOS:")
print("=" * 60)
cur.execute("""
    SELECT chave, caminho_xml, informante, data_download 
    FROM xmls_baixados 
    ORDER BY data_download DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    chave, caminho, info, data = row
    print(f"🔑 {chave[:10]}...{chave[-10:]}")
    print(f"   📁 {caminho}")
    print(f"   🏢 Informante: {info}")
    print(f"   📅 Baixado em: {data}")
    print()

# Verificar se XMLs existem no disco
print(f"\n{'=' * 60}")
print("VERIFICAÇÃO DE ARQUIVOS:")
print("=" * 60)
cur.execute("SELECT caminho_xml FROM xmls_baixados ORDER BY data_download DESC LIMIT 10")
exists_count = 0
missing_count = 0
for (caminho,) in cur.fetchall():
    if Path(caminho).exists():
        exists_count += 1
    else:
        missing_count += 1
        
print(f"✅ Arquivos existentes (últimos 10): {exists_count}")
print(f"❌ Arquivos faltando (últimos 10): {missing_count}")

conn.close()
