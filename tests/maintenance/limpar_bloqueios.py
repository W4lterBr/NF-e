import sqlite3
from datetime import datetime

conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

print("\n" + "=" * 80)
print("🧹 LIMPEZA DE BLOQUEIOS")
print("=" * 80)

# 1. Limpar TODOS os registros da erro_656 (estão com timezone errado)
cursor.execute("SELECT COUNT(*) FROM erro_656")
count_before = cursor.fetchone()[0]
print(f"\n📊 Registros antes da limpeza: {count_before}")

cursor.execute("DELETE FROM erro_656")
conn.commit()
print(f"✅ Todos os {count_before} bloqueios foram removidos\n")

# 2. Verificar se a tabela sem_documentos existe
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='sem_documentos'
""")

if not cursor.fetchone():
    print("⚠️  Tabela sem_documentos não existe. Criando...")
    cursor.execute("""
        CREATE TABLE sem_documentos (
            informante TEXT PRIMARY KEY,
            registrado_em TEXT NOT NULL
        )
    """)
    conn.commit()
    print("✅ Tabela sem_documentos criada com sucesso!\n")
else:
    # Limpar registros antigos (>1h)
    cursor.execute("SELECT COUNT(*) FROM sem_documentos")
    count_sem_docs = cursor.fetchone()[0]
    if count_sem_docs > 0:
        print(f"📊 Registros sem_documentos antes da limpeza: {count_sem_docs}")
        cursor.execute("DELETE FROM sem_documentos")
        conn.commit()
        print(f"✅ Tabela sem_documentos limpa ({count_sem_docs} registros removidos)\n")

print("=" * 80)
print("✅ LIMPEZA CONCLUÍDA")
print("=" * 80)
print()
print("📋 ESTADO ATUAL:")
print()

cursor.execute("SELECT COUNT(*) FROM erro_656")
print(f"   • Bloqueios erro_656: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM sem_documentos")
print(f"   • Registros sem_documentos: {cursor.fetchone()[0]}")

print()
print("💡 Agora você pode executar o sistema novamente sem cooldowns!")
print()

conn.close()
