import sqlite3
import os
from datetime import datetime

db_path = os.path.join(os.environ.get('APPDATA'), 'Busca XML', 'notas.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Cria uma nota de TESTE com status RESUMO
chave_teste = '99999999999999999999999999999999999999999999'
cur.execute("""
    INSERT OR REPLACE INTO notas_detalhadas 
    (chave, numero, nome_emitente, cnpj_emitente, data_emissao, tipo, valor, status, xml_status, informante)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    chave_teste,
    '999999',
    'EMPRESA TESTE RESUMO LTDA',
    '00000000000000',
    datetime.now().strftime('%Y-%m-%d'),
    'NFe',
    '1000.00',
    'Autorizado o uso da NF-e',
    'RESUMO',  # Status RESUMO (cinza)
    '01773924000193'
))

conn.commit()
print('✅ Nota de TESTE criada com status RESUMO!')
print(f'   Chave: {chave_teste}')
print(f'   Número: 999999')
print(f'   Emissor: EMPRESA TESTE RESUMO LTDA')
print(f'   xml_status: RESUMO (será exibida com fundo CINZA)\n')
print('Agora atualize a interface (F5) para ver a nota cinza!')

conn.close()
