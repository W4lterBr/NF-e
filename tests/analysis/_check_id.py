id_val = 'ID2102105025104226387000010155001000999785116232015101'
print(f'Tamanho total: {len(id_val)}')
print(f'ID: {id_val[0:2]}')
print(f'tpEvento: {id_val[2:8]}')
print(f'Chave: {id_val[8:52]} ({len(id_val[8:52])} digitos)')
print(f'Seq: {id_val[52:54]}')
if len(id_val) > 54:
    print(f'EXTRA (problema): {id_val[54:]}')
else:
    print('OK - 54 caracteres corretos')
