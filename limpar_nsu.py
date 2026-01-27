import sqlite3

conn = sqlite3.connect('nfe_data.db')
cursor = conn.cursor()

# Remove registros com NSU_
cursor.execute("DELETE FROM nfse_baixadas WHERE numero_nfse LIKE 'NSU_%'")
deleted = cursor.rowcount

# Reseta NSU
cursor.execute('UPDATE nsu_nfse SET ult_nsu = 0')

conn.commit()
conn.close()

print(f'{deleted} registros removidos')
print('NSU resetado para 0')
