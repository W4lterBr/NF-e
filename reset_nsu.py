from nfse_search import NFSeDatabase

db = NFSeDatabase()
db.conn.execute('UPDATE nsu_nfse SET ult_nsu = 0 WHERE informante = "33251845000109"')
db.conn.commit()
print('NSU resetado para 0')
