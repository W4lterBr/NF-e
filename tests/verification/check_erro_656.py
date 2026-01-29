import sqlite3
from datetime import datetime

conn = sqlite3.connect('notas.db')
cursor = conn.cursor()

print("\n" + "=" * 80)
print("📋 TABELA erro_656 - Bloqueios Ativos")
print("=" * 80)

cursor.execute('''
    SELECT informante, ultimo_erro, 
           datetime(ultimo_erro, 'localtime'), 
           (julianday('now', 'localtime') - julianday(ultimo_erro)) * 24 * 60 as minutos_desde,
           nsu_bloqueado
    FROM erro_656
''')

rows = cursor.fetchall()

if rows:
    print(f"\n📊 Total de bloqueios registrados: {len(rows)}\n")
    
    for row in rows:
        cnpj = row[0]
        ultimo_erro_utc = row[1]
        ultimo_erro_local = row[2]
        minutos_desde = row[3]
        nsu = row[4]
        
        status = "⏰ ATIVO (bloqueado)" if minutos_desde < 65 else "✅ EXPIRADO (pode limpar)"
        
        print(f"🔒 CNPJ: {cnpj}")
        print(f"   📅 Bloqueado em: {ultimo_erro_local}")
        print(f"   ⏱️  Faz {minutos_desde:.1f} minutos")
        print(f"   📊 NSU bloqueado: {nsu}")
        print(f"   {status}")
        print()
else:
    print("\n✅ Nenhum bloqueio registrado na tabela erro_656\n")

# Verificar também sem_documentos
print("\n" + "=" * 80)
print("📋 TABELA sem_documentos - Registros de Sincronização")
print("=" * 80)

cursor.execute('''
    SELECT informante, registrado_em,
           datetime(registrado_em, 'localtime'),
           (julianday('now', 'localtime') - julianday(registrado_em)) * 24 * 60 as minutos_desde
    FROM sem_documentos
''')

rows = cursor.fetchall()

if rows:
    print(f"\n📊 Total de registros: {len(rows)}\n")
    
    for row in rows:
        cnpj = row[0]
        registrado_em_utc = row[1]
        registrado_em_local = row[2]
        minutos_desde = row[3]
        
        status = "⏰ ATIVO (aguardando 1h)" if minutos_desde < 60 else "✅ EXPIRADO (pode consultar)"
        
        print(f"⏸️  CNPJ: {cnpj}")
        print(f"   📅 Registrado em: {registrado_em_local}")
        print(f"   ⏱️  Faz {minutos_desde:.1f} minutos")
        print(f"   {status}")
        print()
else:
    print("\n✅ Nenhum registro na tabela sem_documentos\n")

conn.close()

print("=" * 80)
print("💡 RECOMENDAÇÃO:")
print("=" * 80)
print()
print("Se houver bloqueios EXPIRADOS (>65min), execute:")
print("   DELETE FROM erro_656 WHERE ultimo_erro < datetime('now', '-65 minutes');")
print()
print("Se houver registros sem_documentos EXPIRADOS (>60min), execute:")
print("   DELETE FROM sem_documentos WHERE registrado_em < datetime('now', '-60 minutes');")
print()
