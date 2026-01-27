import sqlite3

conn = sqlite3.connect('notas_test.db')
conn.execute("DELETE FROM notas_detalhadas WHERE tipo='NFSe'")
conn.execute("DELETE FROM xmls_baixados WHERE chave LIKE '43%' OR chave LIKE '31%'")
conn.commit()
print('✅ NFS-e antigas removidas do banco')
conn.close()
