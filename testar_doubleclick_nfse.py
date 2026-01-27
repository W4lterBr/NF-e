"""
Teste: Verificar se double-click em NFS-e funciona corretamente
"""

import sqlite3
from pathlib import Path

# Simula busca de uma NFS-e
conn = sqlite3.connect('notas.db')
cursor = conn.execute('''
    SELECT chave, numero, tipo, informante, data_emissao, nome_emitente
    FROM notas_detalhadas
    WHERE tipo = 'NFS-e'
    LIMIT 3
''')

print('📋 NFS-e na interface:\n')
print(f'{"Número":<20} {"Tipo":<10} {"Chave":<50} {"PDF existe?":<15}')
print('-'*100)

for row in cursor.fetchall():
    chave = row[0]
    numero = row[1]
    tipo = row[2]
    informante = row[3]
    data_emissao = row[4][:10] if row[4] else ''
    emitente = row[5]
    
    # Tenta localizar PDF (mesma lógica do código)
    year_month = data_emissao[:7] if len(data_emissao) >= 7 else None
    
    pdf_encontrado = False
    pdf_path = None
    
    if year_month:
        # Estrutura: xmls/{CNPJ}/{ANO-MES}/{TIPO}/{CHAVE}.pdf
        tipo_normalizado = tipo.upper().replace('-', '')  # NFS-e -> NFSE
        specific_path = Path(f'xmls/{informante}/{year_month}/{tipo_normalizado}/{chave}.pdf')
        
        if specific_path.exists():
            pdf_encontrado = True
            pdf_path = specific_path
        else:
            # Tenta estrutura sem tipo
            old_path = Path(f'xmls/{informante}/{year_month}/{chave}.pdf')
            if old_path.exists():
                pdf_encontrado = True
                pdf_path = old_path
            else:
                # Tenta com tipo original (NFS-e)
                alt_path = Path(f'xmls/{informante}/{year_month}/{tipo}/{chave}.pdf')
                if alt_path.exists():
                    pdf_encontrado = True
                    pdf_path = alt_path
    
    status = f'✅ {pdf_path}' if pdf_encontrado else '❌ NÃO'
    print(f'{numero:<20} {tipo:<10} {chave[:48]:<50} {status:<15}')

print('\n🔍 DIAGNÓSTICO:')
print('Se aparecer ❌, significa que o double-click NÃO vai funcionar.')
print('Possíveis problemas:')
print('1. PDF não existe (só tem XML)')
print('2. Estrutura de pastas diferente')
print('3. Tipo "NFS-e" vs "NFSE" vs "NFSe"')

conn.close()
