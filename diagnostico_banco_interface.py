"""
Script para diagnosticar qual banco a interface está usando e o que contém
"""
from pathlib import Path
import sys
import os
import sqlite3

print("="*70)
print("DIAGNOSTICO DE BANCO DE DADOS DA INTERFACE")
print("="*70)

# Simula lógica da interface
def get_data_dir():
    if getattr(sys, 'frozen', False):
        app_data = Path(os.environ.get('APPDATA', Path.home()))
        data_dir = app_data / "Busca XML"
    else:
        data_dir = Path(__file__).parent
    return data_dir

DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "notas.db"

print(f"\nModo: {'COMPILADO' if getattr(sys, 'frozen', False) else 'DESENVOLVIMENTO'}")
print(f"DATA_DIR: {DATA_DIR}")
print(f"DB_PATH: {DB_PATH}")
print(f"DB existe: {DB_PATH.exists()}")

if DB_PATH.exists():
    tamanho_kb = DB_PATH.stat().st_size / 1024
    print(f"Tamanho: {tamanho_kb:.1f} KB")
    
    # Verifica conteúdo
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    # Total por tipo
    c.execute("SELECT tipo, COUNT(*) FROM notas_detalhadas GROUP BY tipo")
    print("\nDocumentos no banco:")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    # Verifica NFS-e
    c.execute("SELECT COUNT(*) FROM notas_detalhadas WHERE tipo='NFS-e'")
    total_nfse = c.fetchone()[0]
    
    if total_nfse > 0:
        print(f"\nOK {total_nfse} NFS-e encontradas no banco")
        c.execute("SELECT numero, nome_emitente, valor FROM notas_detalhadas WHERE tipo='NFS-e' LIMIT 3")
        print("\nAmostra:")
        for r in c.fetchall():
            print(f"  N: {r[0]}, Emit: {r[1][:30] if r[1] else 'N/A'}, Valor: {r[2]}")
    else:
        print("\nXX Nenhuma NFS-e encontrada!")
    
    conn.close()
else:
    print("\nXX Banco nao existe!")

print("\n" + "="*70)

# Lista todos os .db na pasta
print("\nTodos os bancos na pasta:")
for db in Path('.').glob('*.db'):
    if 'backup' not in db.name.lower():
        tamanho = db.stat().st_size / 1024
        print(f"  {db.name}: {tamanho:.1f} KB")
