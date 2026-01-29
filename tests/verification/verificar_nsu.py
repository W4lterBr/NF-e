#!/usr/bin/env python3
"""Script para verificar NSUs no banco de dados"""
import sqlite3

conn = sqlite3.connect('notas.db')
c = conn.cursor()

# Total de notas
c.execute('SELECT COUNT(*) FROM notas_detalhadas')
total = c.fetchone()[0]

# Notas COM NSU
c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE nsu IS NOT NULL AND nsu != ''")
com_nsu = c.fetchone()[0]

# Notas SEM NSU
c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE nsu IS NULL OR nsu = ''")
sem_nsu = c.fetchone()[0]

# NSUs únicos
c.execute("SELECT COUNT(DISTINCT nsu) FROM notas_detalhadas WHERE nsu IS NOT NULL AND nsu != ''")
nsus_unicos = c.fetchone()[0]

# Últimos 5 registros com NSU
c.execute("SELECT chave, numero, nsu, data_emissao FROM notas_detalhadas WHERE nsu IS NOT NULL AND nsu != '' ORDER BY nsu DESC LIMIT 5")
ultimos = c.fetchall()

conn.close()

print("="*80)
print("VERIFICAÇÃO DE NSU NO BANCO DE DADOS")
print("="*80)
print(f"\n📊 ESTATÍSTICAS:")
print(f"   Total de notas: {total:,}")
print(f"   Notas COM NSU: {com_nsu:,} ({com_nsu/total*100:.1f}%)" if total > 0 else "N/A")
print(f"   Notas SEM NSU: {sem_nsu:,} ({sem_nsu/total*100:.1f}%)" if total > 0 else "N/A")
print(f"   NSUs únicos: {nsus_unicos:,}")

print(f"\n📄 ÚLTIMOS 5 DOCUMENTOS COM NSU:")
for idx, (chave, numero, nsu, data) in enumerate(ultimos, 1):
    print(f"   {idx}. NSU {nsu} - Nota {numero} - Chave {chave[:10]}... - Data {data}")

if sem_nsu > 0:
    print(f"\n⚠️  ATENÇÃO: {sem_nsu} nota(s) SEM NSU detectada(s)!")
    print(f"   Isso pode indicar notas antigas ou erro no processamento.")
else:
    print(f"\n✅ PERFEITO: Todas as notas têm NSU registrado!")

print("="*80)
