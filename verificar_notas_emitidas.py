"""
Script para verificar notas emitidas no banco de dados
"""
import sqlite3
from pathlib import Path
import sys
import os

# Determina o diretório de dados
if getattr(sys, 'frozen', False):
    app_data = Path(os.environ.get('APPDATA', Path.home()))
    data_dir = app_data / "BOT Busca NFE"
else:
    data_dir = Path(__file__).parent

db_path = data_dir / "notas.db"

if not db_path.exists():
    print(f"❌ Banco de dados não encontrado: {db_path}")
    sys.exit(1)

print(f"📂 Conectando ao banco: {db_path}\n")

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 1. Lista todos os CNPJs de certificados
print("=" * 80)
print("📜 CERTIFICADOS CADASTRADOS")
print("=" * 80)
cursor.execute("SELECT cnpj_cpf, informante, cUF_autor FROM certificados")
certificados = cursor.fetchall()

for cnpj, informante, cuf in certificados:
    print(f"  • CNPJ: {cnpj} | Informante: {informante} | UF: {cuf}")

print(f"\n✅ Total de certificados: {len(certificados)}\n")

# 2. Conta total de notas
print("=" * 80)
print("📊 ESTATÍSTICAS GERAIS")
print("=" * 80)

cursor.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE xml_status != 'EVENTO'")
total_notas = cursor.fetchone()[0]
print(f"  Total de notas no banco: {total_notas}")

cursor.execute("SELECT COUNT(DISTINCT cnpj_emitente) FROM notas_detalhadas WHERE xml_status != 'EVENTO'")
total_emitentes = cursor.fetchone()[0]
print(f"  Total de emitentes diferentes: {total_emitentes}\n")

# 3. Verifica notas EMITIDAS por cada certificado
print("=" * 80)
print("🏢 NOTAS EMITIDAS PELA EMPRESA (por certificado)")
print("=" * 80)

cnpjs_certificados = [c[0] for c in certificados]
total_emitidas = 0

for cnpj in cnpjs_certificados:
    cursor.execute("""
        SELECT COUNT(*), tipo 
        FROM notas_detalhadas 
        WHERE cnpj_emitente = ? AND xml_status != 'EVENTO'
        GROUP BY tipo
    """, (cnpj,))
    
    resultados = cursor.fetchall()
    
    if resultados:
        print(f"\n  📌 CNPJ {cnpj}:")
        for count, tipo in resultados:
            print(f"     - {tipo}: {count} notas")
            total_emitidas += count
    else:
        print(f"\n  ⚠️  CNPJ {cnpj}: NENHUMA nota emitida encontrada")

print(f"\n✅ Total de notas EMITIDAS pela empresa: {total_emitidas}\n")

# 4. Verifica notas RECEBIDAS
print("=" * 80)
print("📥 NOTAS RECEBIDAS (por informante)")
print("=" * 80)

for cnpj in cnpjs_certificados:
    cursor.execute("""
        SELECT COUNT(*), tipo 
        FROM notas_detalhadas 
        WHERE informante = ? AND cnpj_emitente != ? AND xml_status != 'EVENTO'
        GROUP BY tipo
    """, (cnpj, cnpj))
    
    resultados = cursor.fetchall()
    
    if resultados:
        print(f"\n  📌 Informante {cnpj}:")
        for count, tipo in resultados:
            print(f"     - {tipo}: {count} notas")

# 5. Mostra exemplos de CNPJs emitentes
print("\n" + "=" * 80)
print("🔍 EXEMPLOS DE CNPJs EMITENTES (primeiros 20)")
print("=" * 80)

cursor.execute("""
    SELECT DISTINCT cnpj_emitente, nome_emitente, COUNT(*) as total
    FROM notas_detalhadas 
    WHERE xml_status != 'EVENTO'
    GROUP BY cnpj_emitente
    ORDER BY total DESC
    LIMIT 20
""")

for cnpj_emit, nome, total in cursor.fetchall():
    # Marca se é da empresa
    marca = "🏢 EMPRESA" if cnpj_emit in cnpjs_certificados else "🏭 Terceiro"
    print(f"  {marca} | {cnpj_emit} | {nome[:40]:40} | {total} notas")

print("\n" + "=" * 80)

conn.close()
print("\n✅ Análise concluída!")
